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
                        │   • Security headers & reverse proxy      │
                        └─────────────┬─────────────────────────────┘
                                      │  /api/* (Internal Docker Network)
                                      ▼
                        ┌───────────────────────────────────────────┐
                        │        heyaaashu-studio-api (Python)      │
                        │   • Authenticated REST API & Publishing   │
                        │   • Live Telegram preview & formatting    │
                        └─────────────┬─────────────────────────────┘
                                      │
                                      ▼
                      ┌──────────────────────────────┐
                      │   studio_data (Docker Volume)│
                      │   Isolated SQLite Database   │
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

Set your configuration in `.env`:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHANNEL_ID=-100xxxxxxxxxx
STUDIO_AUTH_TOKEN=your_secure_studio_password_or_token
SESSION_SECRET=your_random_32_character_session_secret
GEMINI_API_KEY=your_gemini_api_key_here
DATABASE_PATH=/app/data/studio.db
VITE_API_URL=/api
ALLOWED_ORIGINS=http://localhost,http://127.0.0.1
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

## 🔒 Security Best Practices

1. **Authentication**: Configure `STUDIO_AUTH_TOKEN` in `.env` to protect API endpoints from unauthorized publishing and draft modifications.
2. **Network Isolation**: Backend API (`heyaaashu-studio-api`) and SQLite database are isolated within the internal Docker bridge network and never exposed directly to the public internet.
3. **Security Headers**: Production Nginx includes `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`, `Referrer-Policy`, and CSP headers.
4. **Secrets Sanitization**: Never commit `.env` or session files to version control.

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
