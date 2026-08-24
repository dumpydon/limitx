# Render backend deployment

Limit X keeps its matching engine in Python/FastAPI. Create the production backend manually in
Render with these settings:

| Setting | Value |
|---|---|
| Service type | Web Service |
| Repository | `dumpydon/limitx` |
| Branch | `main` |
| Root directory | `backend` |
| Runtime | Python 3 |
| Instance type | Free |
| Build command | `pip install .` |
| Start command | `uvicorn limitx.api.main:app --host 0.0.0.0 --port $PORT` |
| Health check path | `/health` |

Render supplies `PORT`; do not hard-code it in the dashboard. The project requires Python 3.12 or
newer through `backend/pyproject.toml`. The existing `backend/Dockerfile` remains useful for local
Docker development, but the Render service can use the native Python runtime above.

Set this environment variable in Render:

```text
LIMITX_CORS_ORIGINS=https://limitx.dumpydon.workers.dev
```

The backend always also permits the two local origins from its defaults:
`http://localhost:3000` and `http://127.0.0.1:3000`. It exposes `GET /health`, REST endpoints under
`/api`, and `wss://limitx-8hns.onrender.com/ws/market/<symbol>` after deployment.

The current Render service URL is `https://limitx-8hns.onrender.com`. Build the Cloudflare Worker
with that URL in the browser bundle:

```bash
cd frontend
NEXT_PUBLIC_API_URL=https://limitx-8hns.onrender.com npm run deploy
```

`frontend/lib/api.ts` preserves local fallback to `http://localhost:8000` and derives `ws://` or
`wss://` from the configured API scheme. The OpenNext Worker remains named `limitx` and is configured
for `https://limitx.dumpydon.workers.dev`.

`OPENAI_API_KEY` is not required. The shipped Replay Analyst is deterministic and read-only; it does
not import or call an OpenAI API. The core service starts without an AI credential.
