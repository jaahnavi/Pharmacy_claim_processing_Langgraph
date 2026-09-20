# Azure Cloud Foundry deployment guide
# (Tanzu Application Service / Azure Spring Apps CF-compatible spaces)

## Prerequisites

1. Install CF CLI: https://docs.cloudfoundry.org/cf-cli/install-go-cli.html
2. Log in to your Azure Cloud Foundry org/space:

```bash
cf login -a https://api.<your-cf-domain>
```

3. Copy `.env.example` values into CF env vars (do **not** commit secrets):

```bash
cf set-env pharmacy-claim-orchestration OPENAI_API_KEY "sk-..."
# or for Azure OpenAI:
cf set-env pharmacy-claim-orchestration LLM_PROVIDER azure
cf set-env pharmacy-claim-orchestration AZURE_OPENAI_API_KEY "..."
cf set-env pharmacy-claim-orchestration AZURE_OPENAI_ENDPOINT "https://....openai.azure.com/"
cf set-env pharmacy-claim-orchestration AZURE_OPENAI_DEPLOYMENT "gpt-4o-mini"
cf set-env pharmacy-claim-orchestration AZURE_OPENAI_API_VERSION "2024-08-01-preview"

# Optional LangSmith
cf set-env pharmacy-claim-orchestration LANGCHAIN_TRACING_V2 true
cf set-env pharmacy-claim-orchestration LANGCHAIN_API_KEY "..."

# Azure Cosmos DB — finalized claims are upserted here once a run reaches finalize_claim
cf set-env pharmacy-claim-orchestration AZURE_COSMOS_ENDPOINT "https://your-cosmos-account.documents.azure.com:443/"
cf set-env pharmacy-claim-orchestration AZURE_COSMOS_KEY "..."
cf set-env pharmacy-claim-orchestration AZURE_COSMOS_DATABASE pharmacy_claims
cf set-env pharmacy-claim-orchestration AZURE_COSMOS_CONTAINER claims
```

## Deploy

From the repository root:

```bash
cf push -f deploy/manifest.yml
```

The Python buildpack installs `requirements.txt`. The process starts via:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Verify

```bash
cf apps
cf logs pharmacy-claim-orchestration --recent
curl https://<app-route>/health
```

Import `postman/Pharmacy_Claim_Orchestration.postman_collection.json` and set `baseUrl` to the CF route.

## Notes

- SQLite checkpointer writes under `/home/vcap/app/data/` and is **single-instance only** (local file + WAL, wiped on restage).
- Educational demo only — synthetic data, no real PHI.

## Durable / multi-instance checkpointer (Azure Blob Storage)

For HA (`instances: 2+`) and checkpoints that survive restarts, use the Azure Blob Storage checkpointer:

```bash
cf set-env pharmacy-claim-orchestration CHECKPOINT_BACKEND blob
cf set-env pharmacy-claim-orchestration AZURE_STORAGE_CONNECTION_STRING "DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net"
# optional
cf set-env pharmacy-claim-orchestration AZURE_STORAGE_CHECKPOINT_CONTAINER langgraph-checkpoints
cf restage pharmacy-claim-orchestration
```

- Implemented in `app/graph/checkpointer_blob.py` (`AzureBlobSaver`) — there is no official LangGraph Azure Blob checkpointer package, so it talks to the `azure-storage-blob` SDK directly. Each checkpoint and pending write is stored as its own blob; the container is created automatically on first use.
- `GET /health` reports the active `checkpoint_backend`.

## Finalized claim persistence (Azure Cosmos DB)

Every terminal path through the graph (fan-in failure, human reject/changes-requested,
or a successful submission) routes through a `finalize_claim` node that upserts the
final claim document into Cosmos DB (`app/clients/cosmos_client.py`), partitioned by
`claim_id`. Set `AZURE_COSMOS_ENDPOINT` and `AZURE_COSMOS_KEY` to enable it — if unset,
`finalize_claim` logs a warning and skips persistence rather than failing the run.
