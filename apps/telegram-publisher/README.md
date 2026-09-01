<div align="center">

# 📢 Posting Post Bot

**Feature-rich Telegram bot for managing channel posts and publications**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)](https://python.org)
[![aiogram](https://img.shields.io/badge/aiogram-3.4%2B-2CA5E0?logo=telegram&logoColor=white)](https://aiogram.dev)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

*Media Files · Colored URL Buttons · Reaction Voting · Scheduled Posts · Post Editing*

</div>

---

## 🚀 What's New in Version 1.1.0

- **📊 Full Native Telegram Tables Support (RichBlockTable)**: Uses native `copy_message` to preserve pixel-perfect Telegram native tables and rich blocks.
- **🛡️ SQL Injection Protection**: Added strict whitelist field verification in `Database.update_post()`.
- **📄 MIT License**: Added `LICENSE` file.
- **🎬 Extended Content Support**: Full support for video notes (`video_note`), paid media, and interactive blocks.

---

## ✨ Features

### 📢 Channel Management
- **Interactive Channel Adding**: Pick a channel directly via the Telegram interface ("Share Channel" button). The bot automatically verifies administrator rights.
- **Unlimited Channels**: Connect as many channels as you need.
- **User Separation**: Each user only sees and manages their own connected channels.

---

### ✍️ Post Creator
- **Supported Content Formats**:
  - 📝 Text (with formatting)
  - 🖼️ Photo (with caption)
  - 🎬 Video (with caption)
  - 📎 Document / File
  - 🎵 Audio
  - 🎙️ Voice Message
  - 🎞️ GIF Animation
  - 🎭 Sticker

- **Smart Content Updating**: If you first send a photo and then send text, the bot sets it as the photo's caption without deleting the media file.

---

### 🎨 Text Formatting

The bot supports four markup modes:

| Mode | Description |
|------|-------------|
| **Auto Telegram** | Preserves formatting as-is from your Telegram client: **bold**, _italic_, `code`, ~~strikethrough~~, custom Premium emojis |
| **HTML** | Manual HTML tags: `<b>`, `<i>`, `<u>`, `<s>`, `<code>`, `<a href="...">` |
| **Markdown** | Standard Markdown: `*bold*`, `_italic_`, `` `code` `` |
| **MarkdownV2** | Advanced Markdown with special character escaping |

---

### 📊 Table Generation & Formatting

Create and cleanly format tables in your Telegram posts:

- **Automatic Conversion**: Send a Markdown table (e.g., `| Column 1 | Column 2 |`), and the bot will convert it into a clean monospaced box table.
- **Table Styles**:
  - 📦 **Unicode Box** (`┌──┬──┐`, `│  │  │`, `└──┴──┘`) — aesthetic solid line borders.
  - 📐 **ASCII** (`+--+--+`, `|  |  |`, `+--+--+`) — classic style with `+` and `-` characters.
- **Table Constructor**: Click "📊 Table" -> "➕ Insert New Table" and send data separated by `|`.

---

### 🔗 URL Buttons

Add link buttons below your posts:

**Input Format:**
```
Button Text - https://example.com
Button 1 - https://site.com | Button 2 - https://other.com - red
```

- Separate multiple buttons in the same row using `|`
- Each new line creates a new row of buttons

**🎨 Button Colors** (supported by Telegram Bot API 9.4+):

| Parameter | Alias | Color |
|-----------|-------|-------|
| `primary` | `blue` | 🔵 Blue (default) |
| `success` | `green` | 🟢 Green |
| `danger` | `red` | 🔴 Red |

Example: `Buy - https://shop.com - green`

---

### 👍 Reaction Voting Buttons

Add interactive reaction buttons below your posts:

- Enter up to **8 emojis** separated by spaces or commas: `👍 👎 🔥 ❤️`
- The bot tallies votes: each reader can cast **one vote**
- Results are displayed dynamically: `👍 12  👎 3`

---

### 📅 Publishing

- **🚀 Publish Now** — post is published immediately
- **⏰ Schedule Post** — enter publication date and time in the format `DD.MM.YYYY HH:MM` (Moscow Time, UTC+3)  
  _Example: `15.08.2026 14:30`_
- Built-in scheduler powered by **APScheduler** — runs in the background without needing external task queues

---

### 📜 Post History

- View recently published posts for each channel
- **Edit Published Posts**:
  - Update text/caption directly in the channel via Telegram Bot API
  - Update URL buttons under any published message
  - Support for **forwarded messages**: forward any message from your channel to the bot to automatically recognize and edit it

---

## 🛠️ Installation and Setup

### Requirements
- Python **3.9+**
- Bot token from [@BotFather](https://t.me/BotFather)
- Administrator rights in the target Telegram channel

### 1. Clone the repository

```bash
git clone https://github.com/novirx-tg/postingpost.git
cd postingpost
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env.template` to `.env` and set your token:

```env
BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ
```

### 4. Run the bot

```bash
python main.py
```

---

## 📁 Project Structure

```
postingpost/
├── main.py                    # Entry point, bot and dispatcher initialization
├── config.py                  # Environment config loading (.env)
├── database.py                # SQLite database management (channels, posts, votes)
├── requirements.txt
├── .env.template              # Environment configuration template
├── handlers/
│   ├── start.py               # /start, main menu, help
│   ├── channels.py            # Channel connection and management
│   ├── post_creator.py        # Post creation and preview FSM
│   ├── history.py             # Post history and live editing
│   └── scheduler.py           # Scheduled posts management
└── services/
    ├── post_service.py        # Post sending logic, keyboard builders
    ├── scheduler_service.py   # APScheduler job service
    └── table_service.py       # Table parsing, rendering, and rich blocks
```

---

## 🔒 Security

- The `.env` file containing the token is excluded via `.gitignore`
- The SQLite database `posting_bot.db` is also excluded from git commits
- Strict user-isolation ensuring users only manage their own channels and posts

---

## 📦 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `aiogram` | ≥ 3.4.0 | Asynchronous Telegram Bot API framework |
| `apscheduler` | ≥ 3.10.0 | Task scheduler |
| `python-dotenv` | ≥ 1.0.0 | Environment variable loader |
| `pydantic-settings` | ≥ 2.0.0 | Application configuration |
| `tzlocal` | ≥ 5.0 | Time zone utilities |

---

## 📄 License

MIT License — free to use and modify.
