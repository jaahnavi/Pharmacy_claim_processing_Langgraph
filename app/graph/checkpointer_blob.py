"""Checkpointer backed by Azure Blob Storage.

There is no official LangGraph checkpoint saver for Azure Blob Storage, so this
implements ``BaseCheckpointSaver`` directly against the Azure SDK. Layout:

  checkpoints/{thread_id}/{checkpoint_ns}/{checkpoint_id}.json
  writes/{thread_id}/{checkpoint_ns}/{checkpoint_id}/{task_id}/{idx}.json

Checkpoint ids assigned by LangGraph are time-ordered (UUID6-style), so a
lexical sort of blob names within a thread/namespace prefix is also a
chronological sort — the same property SqliteSaver/PostgresSaver rely on via
``ORDER BY checkpoint_id``.

Only sync methods talk to the Azure SDK directly; the async methods wrap them
with ``asyncio.to_thread`` since the rest of this app calls the graph
synchronously.
"""

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any, Iterator, Optional

from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    get_checkpoint_id,
)


class AzureBlobSaver(BaseCheckpointSaver):
    def __init__(self, container_client, *, serde=None) -> None:
        super().__init__(serde=serde)
        self._container = container_client

    @classmethod
    def from_connection_string(cls, connection_string: str, container_name: str) -> "AzureBlobSaver":
        from azure.core.exceptions import ResourceExistsError
        from azure.storage.blob import BlobServiceClient

        service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = service_client.get_container_client(container_name)
        try:
            container_client.create_container()
        except ResourceExistsError:
            pass
        return cls(container_client)

    # -- blob naming ---------------------------------------------------

    @staticmethod
    def _checkpoint_blob_name(thread_id: str, checkpoint_ns: str, checkpoint_id: str) -> str:
        return f"checkpoints/{thread_id}/{checkpoint_ns}/{checkpoint_id}.json"

    @staticmethod
    def _checkpoint_prefix(thread_id: str, checkpoint_ns: str) -> str:
        return f"checkpoints/{thread_id}/{checkpoint_ns}/"

    @staticmethod
    def _write_blob_name(thread_id: str, checkpoint_ns: str, checkpoint_id: str, task_id: str, idx: int) -> str:
        return f"writes/{thread_id}/{checkpoint_ns}/{checkpoint_id}/{task_id}/{idx}.json"

    @staticmethod
    def _writes_prefix(thread_id: str, checkpoint_ns: str, checkpoint_id: str) -> str:
        return f"writes/{thread_id}/{checkpoint_ns}/{checkpoint_id}/"

    # -- blob io ---------------------------------------------------------

    def _read_json_blob(self, blob_name: str) -> Optional[dict]:
        from azure.core.exceptions import ResourceNotFoundError

        try:
            data = self._container.download_blob(blob_name).readall()
        except ResourceNotFoundError:
            return None
        return json.loads(data)

    def _write_json_blob(self, blob_name: str, payload: dict) -> None:
        self._container.upload_blob(blob_name, json.dumps(payload), overwrite=True)

    def _latest_checkpoint_payload(self, thread_id: str, checkpoint_ns: str) -> Optional[dict]:
        prefix = self._checkpoint_prefix(thread_id, checkpoint_ns)
        names = sorted((b.name for b in self._container.list_blobs(name_starts_with=prefix)), reverse=True)
        if not names:
            return None
        return self._read_json_blob(names[0])

    def _load_pending_writes(self, thread_id: str, checkpoint_ns: str, checkpoint_id: str) -> list[tuple[str, str, Any]]:
        prefix = self._writes_prefix(thread_id, checkpoint_ns, checkpoint_id)
        rows: list[tuple[int, str, str, Any]] = []
        for blob in self._container.list_blobs(name_starts_with=prefix):
            payload = self._read_json_blob(blob.name)
            if payload is None:
                continue
            value = self.serde.loads_typed((payload["type"], base64.b64decode(payload["value_b64"])))
            rows.append((payload["idx"], payload["task_id"], payload["channel"], value))
        rows.sort(key=lambda r: r[0])
        return [(task_id, channel, value) for _idx, task_id, channel, value in rows]

    # -- BaseCheckpointSaver: sync ----------------------------------------

    def put(
        self,
        config: dict,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> dict:
        configurable = config["configurable"]
        thread_id = configurable["thread_id"]
        checkpoint_ns = configurable.get("checkpoint_ns", "")
        checkpoint_id = checkpoint["id"]
        parent_checkpoint_id = configurable.get("checkpoint_id")

        type_, serialized_checkpoint = self.serde.dumps_typed(checkpoint)
        metadata_type, serialized_metadata = self.serde.dumps_typed(metadata)

        payload = {
            "thread_id": thread_id,
            "checkpoint_ns": checkpoint_ns,
            "checkpoint_id": checkpoint_id,
            "parent_checkpoint_id": parent_checkpoint_id,
            "type": type_,
            "checkpoint_b64": base64.b64encode(serialized_checkpoint).decode("ascii"),
            "metadata_type": metadata_type,
            "metadata_b64": base64.b64encode(serialized_metadata).decode("ascii"),
        }
        self._write_json_blob(self._checkpoint_blob_name(thread_id, checkpoint_ns, checkpoint_id), payload)

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }

    def put_writes(
        self,
        config: dict,
        writes: list[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        configurable = config["configurable"]
        thread_id = configurable["thread_id"]
        checkpoint_ns = configurable.get("checkpoint_ns", "")
        checkpoint_id = configurable["checkpoint_id"]

        for idx, (channel, value) in enumerate(writes):
            type_, serialized_value = self.serde.dumps_typed(value)
            payload = {
                "task_id": task_id,
                "task_path": task_path,
                "idx": idx,
                "channel": channel,
                "type": type_,
                "value_b64": base64.b64encode(serialized_value).decode("ascii"),
            }
            blob_name = self._write_blob_name(thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
            self._write_json_blob(blob_name, payload)

    def get_tuple(self, config: dict) -> Optional[CheckpointTuple]:
        configurable = config["configurable"]
        thread_id = configurable["thread_id"]
        checkpoint_ns = configurable.get("checkpoint_ns", "")
        checkpoint_id = get_checkpoint_id(config)

        if checkpoint_id:
            payload = self._read_json_blob(self._checkpoint_blob_name(thread_id, checkpoint_ns, checkpoint_id))
        else:
            payload = self._latest_checkpoint_payload(thread_id, checkpoint_ns)
            if payload is not None:
                checkpoint_id = payload["checkpoint_id"]

        if payload is None:
            return None

        checkpoint = self.serde.loads_typed((payload["type"], base64.b64decode(payload["checkpoint_b64"])))
        metadata = self.serde.loads_typed((payload["metadata_type"], base64.b64decode(payload["metadata_b64"])))

        parent_checkpoint_id = payload.get("parent_checkpoint_id")
        parent_config = None
        if parent_checkpoint_id:
            parent_config = {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": parent_checkpoint_id,
                }
            }

        return CheckpointTuple(
            config={
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": checkpoint_id,
                }
            },
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=parent_config,
            pending_writes=self._load_pending_writes(thread_id, checkpoint_ns, checkpoint_id),
        )

    def list(
        self,
        config: Optional[dict],
        *,
        filter: Optional[dict[str, Any]] = None,
        before: Optional[dict] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointTuple]:
        if config is None:
            return
        configurable = config["configurable"]
        thread_id = configurable["thread_id"]
        checkpoint_ns = configurable.get("checkpoint_ns", "")

        prefix = self._checkpoint_prefix(thread_id, checkpoint_ns)
        names = sorted((b.name for b in self._container.list_blobs(name_starts_with=prefix)), reverse=True)

        before_id = None
        if before is not None:
            before_id = before["configurable"].get("checkpoint_id")

        count = 0
        for name in names:
            checkpoint_id = name.rsplit("/", 1)[-1].removesuffix(".json")
            if before_id is not None and checkpoint_id >= before_id:
                continue

            payload = self._read_json_blob(name)
            if payload is None:
                continue

            metadata = self.serde.loads_typed((payload["metadata_type"], base64.b64decode(payload["metadata_b64"])))
            if filter and not all(metadata.get(k) == v for k, v in filter.items()):
                continue

            checkpoint = self.serde.loads_typed((payload["type"], base64.b64decode(payload["checkpoint_b64"])))
            parent_checkpoint_id = payload.get("parent_checkpoint_id")
            parent_config = None
            if parent_checkpoint_id:
                parent_config = {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": parent_checkpoint_id,
                    }
                }

            yield CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": checkpoint_id,
                    }
                },
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config=parent_config,
                pending_writes=self._load_pending_writes(thread_id, checkpoint_ns, checkpoint_id),
            )
            count += 1
            if limit is not None and count >= limit:
                return

    # -- BaseCheckpointSaver: async (thread-wrapped) ----------------------

    async def aget_tuple(self, config: dict) -> Optional[CheckpointTuple]:
        return await asyncio.to_thread(self.get_tuple, config)

    async def aput(
        self,
        config: dict,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> dict:
        return await asyncio.to_thread(self.put, config, checkpoint, metadata, new_versions)

    async def aput_writes(
        self,
        config: dict,
        writes: list[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        await asyncio.to_thread(self.put_writes, config, writes, task_id, task_path)

    async def alist(
        self,
        config: Optional[dict],
        *,
        filter: Optional[dict[str, Any]] = None,
        before: Optional[dict] = None,
        limit: Optional[int] = None,
    ):
        items = await asyncio.to_thread(
            lambda: list(self.list(config, filter=filter, before=before, limit=limit))
        )
        for item in items:
            yield item
