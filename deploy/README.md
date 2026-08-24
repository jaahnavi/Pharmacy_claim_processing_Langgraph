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

- SQLite checkpointer writes under `/home/vcap/app/data/`. For multi-instance HA, bind a Postgres service and swap the checkpointer (stretch).
- Educational demo only — synthetic data, no real PHI.
