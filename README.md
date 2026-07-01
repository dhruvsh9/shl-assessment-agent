# SHL Assessment Conversational Agent

FastAPI service for a stateless SHL assessment recommendation agent.

## Endpoints

- `GET /health` returns `{"status": "ok"}`.
- `POST /chat` accepts full conversation history and returns the required schema:

```json
{
  "reply": "string",
  "recommendations": [
    {"name": "string", "url": "string", "test_type": "string"}
  ],
  "end_of_conversation": false
}
```

## Run Locally

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Test:

```bash
pytest
```

Example request:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hiring a Java developer who works with stakeholders. Mid-level, around 4 years."}]}'
```

## Catalog

The app loads `app/data/shl_catalog.json` at startup. Recommendations are always selected from this file, and returned URLs are catalog URLs from that file.

Refresh the catalog when the SHL site is reachable:

```bash
python scripts/scrape_catalog.py
```

The included JSON catalog is an offline Individual Test Solutions snapshot used by the deployed service so recommendations remain deterministic and catalog-bounded even when the SHL website is unavailable or changes markup.

## Free Deployment

Recommended free option: Render Web Service or Hugging Face Spaces Docker/Gradio-less FastAPI.

Render settings:

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- No database required.
- No LLM key required.

## Design Notes

- Stateless: `/chat` reconstructs intent from the submitted messages only.
- Catalog-bounded: all recommendations come from local catalog data.
- Deterministic retrieval: keyword expansion plus type boosts for technical, personality, cognitive, behavioral, and language tests.
- Guardrails: refuses off-topic, legal/salary/interview-advice, and prompt-injection requests.
- Comparison: compares named catalog assessments using stored catalog descriptions.
