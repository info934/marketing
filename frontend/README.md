# Creative OS Chat Frontend

Next.js chat-first frontend for the ecommerce creative workflow. It keeps the existing FastAPI backend as the source of truth and proxies API calls through `/api/backend/*`.

## Stack

- Next.js App Router
- React
- TypeScript
- Tailwind CSS
- shadcn/ui-style local components
- Framer Motion

## Run Locally

Start the existing workflow backend:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:3000
```

If the backend runs elsewhere, set:

```powershell
$env:NEXT_PUBLIC_WORKFLOW_BACKEND_URL="http://127.0.0.1:8001"
```

## Data Flow

The chat UI collects text, URLs, pasted screenshots, uploaded files, avatar notes, and creative direction. Manual chips or the AI brief parser turn those chat items into the same `CampaignForm` fields that the current backend already accepts.

Generation still posts to `/generation-runs`; the Next API route proxies it to the FastAPI workflow backend.

## Native Workflow Modules

The new frontend includes native Next UI screens for the workflow modules that used to live only in the FastAPI React UI:

- Dashboard
- Avatar set
- Creative sets
- Prompt lab
- Analytics
- Settings

These screens use the same FastAPI endpoints through `/api/backend/*`, so avatar changes, creative ratings, performance imports, prompt overrides, and generation runs stay connected to the existing backend data.
