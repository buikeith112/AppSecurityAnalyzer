# Deployment Guide

This project has two deployable pieces:

- FastAPI backend: clones or extracts projects, runs the scanner, returns JSON.
- Static frontend: submits scans to the backend and displays the report.

Deploy the backend first. The frontend needs the backend URL.

## Backend Environment Variables

Required by most hosts:

```text
PORT=<set automatically by Render/Railway>
FRONTEND_ORIGINS=https://your-vercel-app.vercel.app
```

Optional LLM provider variables:

```text
LLM_PROVIDER=gemini
GEMINI_API_KEY=<your-key>
LLM_MODEL=gemini-2.5-flash-lite
```

Other supported provider keys:

```text
GROQ_API_KEY=<your-key>
OPENROUTER_API_KEY=<your-key>
OPENAI_API_KEY=<your-key>
LLM_API_KEY=<generic-provider-key>
LLM_BASE_URL=<custom-provider-or-self-hosted-ollama-url>
```

If no LLM key is configured, `--llm-analysis` and web LLM scans use the offline mock response.

## Backend on Render

1. Push this repository to GitHub.
2. In Render, create a new `Web Service`.
3. Connect the GitHub repository.
4. Use these settings:

```text
Runtime: Python
Build Command: pip install -r requirements.txt
Start Command: python -m backend.start
```

The repository includes `runtime.txt` to request Python 3.11 on hosts that support it.

5. Add environment variables:

```text
FRONTEND_ORIGINS=https://your-vercel-app.vercel.app
LLM_PROVIDER=gemini
GEMINI_API_KEY=<your-key>
LLM_MODEL=gemini-2.5-flash-lite
```

6. Deploy.
7. Check health:

```bash
curl https://your-render-service.onrender.com/health
```

Expected response:

```json
{"status":"ok"}
```

Render should provide `PORT` automatically. The backend reads it in `backend/start.py`.

## Backend on Railway

1. Push this repository to GitHub.
2. In Railway, create a new project from the GitHub repository.
3. Add environment variables:

```text
FRONTEND_ORIGINS=https://your-vercel-app.vercel.app
LLM_PROVIDER=gemini
GEMINI_API_KEY=<your-key>
LLM_MODEL=gemini-2.5-flash-lite
```

4. Use this start command if Railway does not detect the `Procfile`:

```bash
python -m backend.start
```

5. Deploy.
6. Check health:

```bash
curl https://your-railway-domain.up.railway.app/health
```

Railway should provide `PORT` automatically. The backend runs with `reload=False` for production.

## Frontend on Vercel

1. Deploy the backend first and copy its public URL.
2. In Vercel, create a new project from the same GitHub repository.
3. Set the project root directory to:

```text
frontend
```

4. Vercel will use `frontend/vercel.json`:

```text
Build Command: npm run build
Output Directory: dist
```

5. Add this Vercel environment variable:

```text
API_BASE_URL=https://your-backend-service.example.com
```

Do not include a trailing slash.

6. Deploy the frontend.
7. After Vercel gives you a frontend URL, add it to the backend:

```text
FRONTEND_ORIGINS=https://your-vercel-app.vercel.app
```

8. Redeploy or restart the backend so the CORS setting is active.

## Local Production Check

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the backend with the same production entry point used by hosts:

```bash
PORT=8000 python -m backend.start
```

Open:

```text
http://127.0.0.1:8000
```

Build the frontend like Vercel:

```bash
cd frontend
API_BASE_URL=http://127.0.0.1:8000 npm run build
```

The deployable static files will be in:

```text
frontend/dist
```

On Windows PowerShell:

```powershell
cd frontend
$env:API_BASE_URL="http://127.0.0.1:8000"
npm run build
```

## Notes

- GitHub URL scans require `git` to be available on the backend host.
- ZIP scans do not require `git`.
- For Vercel-hosted frontend plus hosted backend, set `FRONTEND_ORIGINS`; otherwise browser CORS will block `/scan`.
- Ollama is local by default. For hosted backend deployments, use Gemini, Groq, OpenRouter, OpenAI, or a separately hosted Ollama server.
