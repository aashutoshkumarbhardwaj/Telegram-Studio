# Heyaaashu Studio

AI + Tech + Career Content Operating System & Visual Telegram Content Studio.

---

## 🏗️ Architecture

```
                                  ┌────────────────────────┐
                                  │   Browser / Client     │
                                  └───────────┬────────────┘
                                              │  http://localhost
                                              ▼
                        ┌───────────────────────────────────────────┐
                        │      heyaaashu-studio-frontend (Nginx)    │
                        │   • Serves compiled React SPA             │
                        │   • Reverse proxies /api/* to backend     │
                        └─────────────┬─────────────────────────────┘
                                      │  /api/*
                                      ▼
                        ┌───────────────────────────────────────────┐
                        │        heyaaashu-studio-api (Python)      │
                        │   • REST API, PostSchema validation       │
                        │   • Live Telegram preview & formatting    │
                        │   • Direct Telegram channel publisher     │
                        └─────────────┬─────────────────────────────┘
                                      │
                                      ▼
                      ┌──────────────────────────────┐
                      │   studio_data (Docker Volume)│
                      │   Persistent SQLite Database │
                      └───────────────┬──────────────┘
                                      │
                                      ▲
                        ┌─────────────┴─────────────────────────────┐
                        │        heyaaashu-studio-bot (Python)      │
                        │   • Single dedicated polling bot receiver │
                        │   • /new, /research, /daily workflows     │
                        └───────────────────────────────────────────┘
```

---

## 🚀 Quickstart: Local Docker Deployment

### 1. Clone & Configure Environment
```bash
git clone <repository_url>
cd heyaaashu-studio
cp .env.example .env
nano .env  # or vim .env
```

Set your required environment variables in `.env`:
```env
TELEGRAM_BOT_TOKEN=8210460024:AAEd21ZYkRhdYYHETRzYFEa-SvLi697CZz4
TELEGRAM_CHANNEL_ID=-1003756584531
GEMINI_API_KEY=your_gemini_api_key_here
DATABASE_PATH=/app/data/studio.db
VITE_API_URL=/api
```

### 2. Start Full Stack
```bash
docker compose up -d --build
```

### 3. Open Studio in Browser
Navigate to:
```
http://localhost
```

---

## 🛠️ Docker Operations & Lifecycle Commands

| Action | Command | Notes |
|---|---|---|
| **View Status** | `docker compose ps` | Displays container health and port bindings |
| **Stream Logs** | `docker compose logs -f` | Live logs across frontend, api, and bot |
| **Restart Services** | `docker compose restart` | Preserves all persistent database state |
| **Graceful Stop** | `docker compose down` | Stops containers while keeping volumes safe |
| **Clean Wipe** | `docker compose down -v` | ⚠️ **DESTRUCTIVE**: Permanently deletes SQLite database volume! |

> [!WARNING]
> Running `docker compose down -v` removes the named Docker volume `studio_data` and will permanently delete all stored drafts and publishing history. Use standard `docker compose down` during normal maintenance.

---

## 🧪 Testing & Validation

### Backend & AI Unit Tests (Pytest)
```bash
pytest tests/ -v
```

### Frontend Studio Tests (Vitest)
```bash
cd apps/message-builder
npm run test
```

### Production Frontend Build Check
```bash
cd apps/message-builder
npm run build
```
