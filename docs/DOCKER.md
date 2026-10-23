# Running RiskWise in Docker

The backend image is self-contained. It carries the trained credit models, the retrieval index, the
knowledge corpus, the market snapshots and the drift baseline, and it creates its own database on first
start. Nothing is bind-mounted from the host, so a friend's laptop needs only Docker.
API keys are optional. Without them the copilot runs in its documented offline mode.

## Why the earlier setup failed on another machine

- `artifacts/models/*`, `Dataset/`, `data/processed/*` and the vector index are gitignored, so a fresh clone does not have them.
- The old compose file mounted `./artifacts` and `./data` over the image, so the container saw those empty folders.
- The old image did not copy `ml/`, which the credit service imports, and a new database had no instruments or prices.

## Option 1: send the prebuilt images (recommended for a friend)

On your machine, where the model files exist:

```powershell
docker compose build
docker save -o riskwise-docker.tar riskwise-backend:latest riskwise-frontend:latest
```

Send `riskwise-docker.tar` and `docker-compose.yml`. The tar contains the cleaned borrower-level credit data
used for drift monitoring, so share it privately and do not push the images to a public registry.

On your friend's machine:

```bash
docker load -i riskwise-docker.tar
docker compose up -d
```

## Option 2: build from a checkout

You need these gitignored paths in the checkout: `artifacts/models/` (the `credit_*.joblib` files) and
`data/processed/credit_indian_cleaned.csv`. Copy them over from your machine. The build stops with a clear
message if the model files are missing.

```bash
docker compose up -d --build
```

The `Dataset/*.xlsx` files are only needed to retrain, never to run.

## Using it

- App: http://localhost:3000
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

The first start takes a few extra seconds while the database is created and seeded. Data lives in the
`riskwise-db` and `riskwise-runs` volumes. `docker compose down` keeps it and `docker compose down -v` wipes it.

Optional LLM keys: put `OPENAI_API_KEY=...` or `ANTHROPIC_API_KEY=...` in a `.env` file next to
`docker-compose.yml`. Compose reads it for substitution, and it is never copied into an image.

If you open the app from another machine than the one running Docker, rebuild the frontend with
`NEXT_PUBLIC_API_URL=http://<host>:8000` and add that origin to `ALLOWED_ORIGINS`.

## Verification status

Docker was not installed on the machine this was written on, so the images have not been built here.
What was run: the start-up script (`docker/prepare.py`) against a brand-new database, which migrated it,
registered the credit model and seeded the market data, and then skipped the seeding on a second run.
Run `docker compose up -d --build` once yourself before sending anything to your friend.
