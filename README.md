# Money Management Telegram Bot

A personal Telegram bot for tracking expenses, income, investments and a monthly spending budget with rollover.
Data lives in **Supabase** (hosted PostgreSQL), and the bot runs on **Render**, so it works when your PC is off.

## Features
Main menu buttons:
- **➖ Add expense**: pick a category (Gaming, Food, Groceries, Clothes, Life, Transport, Entertainment, Health, Subscriptions, Gifts, Other), then send the amount. The bot replies with what's left to spend this month.
- **➕ Add money**: pick a source (Grandma, Parents, Paycheck, Bit, Other), then send the amount in ₪.
- **📈 New investment**: send the amount. The bot replies with your total invested.
- **❓ Ask**: total in investments · left to spend this month · money added this month by source · money spent this month by category.

Commands: `/start` shows the menu, `/cancel` stops the current action, and `/setbudget 1500` sets your monthly budget from this month on.

Dates are filled in automatically (Israel time).

**Budget rollover:** each month you get your budget plus whatever was left from last month. If you overspend, the next month starts from the plain budget; the overspend isn't carried as debt.

## Setup

### 1. Telegram
1. Open [@BotFather](https://t.me/BotFather), send `/newbot`, and copy the **token**.
2. Open [@userinfobot](https://t.me/userinfobot) to get your numeric **user ID**. The bot only answers this ID.

### 2. Supabase (database)
1. Create a free project at [supabase.com](https://supabase.com).
2. Go to **SQL Editor → New query**, paste the contents of [`schema.sql`](schema.sql), and click **Run**.
3. Go to **Connect** (top bar) and copy the **Session pooler** connection string. Replace `[YOUR-PASSWORD]` with your database password. This is your `DATABASE_URL`.

### 3. Run locally (optional, for testing)
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env   # then edit .env with your real values
python -m bot.main
```
With `WEBHOOK_URL` empty, the bot uses polling.
⚠️ Running locally with the same token as Render takes over Telegram's connection, and Render won't get messages until it restarts. Use a second test bot from BotFather for local runs.

Run the tests with `pytest`.

### 4. Deploy to Render (runs 24/7)
1. Push this repo to GitHub. `.env` is gitignored, so check with `git status` that it isn't listed.
2. On [render.com](https://render.com), go to **New → Blueprint**, pick the repo, and Render reads [`render.yaml`](render.yaml).
   (Or **New → Web Service**: runtime Python, build `pip install -r requirements.txt`, start `python -m bot.main`.)
3. Under **Environment**, set `BOT_TOKEN`, `DATABASE_URL` and `ALLOWED_USER_ID`.
4. Deploy. Render provides `RENDER_EXTERNAL_URL`, and the bot registers its webhook on startup.

**Free-tier note:** Render's free web services sleep after about 15 minutes with no traffic. The first message after a quiet period can take 30–60 seconds to get a reply. Telegram keeps retrying, so nothing is lost. To avoid the delay, upgrade the Render plan (~$7/month) or host on Railway or Fly.io.

## Secrets
Real keys go only in your local `.env` (gitignored) and in Render's environment settings. Never commit them. `.env.example` holds placeholders only.

## Project layout
```
bot/config.py    env settings
bot/db.py        Supabase/Postgres queries
bot/budget.py    rollover math (pure, tested)
bot/handlers.py  menus and conversations
bot/main.py      entry point (webhook or polling)
schema.sql       database tables
render.yaml      Render deployment
```
