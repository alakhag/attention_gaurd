# Deploy

## Local

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## Render

1. Push repo to GitHub.
2. Render → New → Web Service.
3. Root directory: `backend`
4. Build command:

```bash
pip install -r requirements.txt
```

5. Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

6. Environment variables:

```text
CLASSIFIER_PROVIDER=mock
DB_PATH=/tmp/attention_guard.db
```

This uses ephemeral storage. Fine for prototype. Use a disk/Postgres later.
