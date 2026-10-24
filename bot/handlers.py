"""Telegram handlers: main menu, add flows and the Ask queries."""

import logging

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    TypeHandler,
    filters,
)

from bot import budget, config, db

log = logging.getLogger(__name__)

BTN_EXPENSE = "➖ Add expense"
BTN_INCOME = "➕ Add money"
BTN_ASK = "❓ Ask"
BTN_INVEST = "📈 New investment"

MAIN_MENU = ReplyKeyboardMarkup(
    [[BTN_EXPENSE, BTN_INCOME], [BTN_ASK, BTN_INVEST]],
    resize_keyboard=True,
    is_persistent=True,
)

# Same options as buttons inside the message, always visible even if the
# keyboard under the text box is collapsed.
INLINE_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton(BTN_EXPENSE, callback_data="menu:expense"),
     InlineKeyboardButton(BTN_INCOME, callback_data="menu:income")],
    [InlineKeyboardButton(BTN_ASK, callback_data="menu:ask"),
     InlineKeyboardButton(BTN_INVEST, callback_data="menu:invest")],
])

# (callback key, button label, value stored in DB)
EXPENSE_CATEGORIES = [
    ("gaming", "🎮 Gaming", "Gaming"),
    ("food", "🍔 Food", "Food"),
    ("groceries", "🛒 Groceries", "Groceries"),
    ("clothes", "👕 Clothes", "Clothes"),
    ("life", "🏠 Life", "Life"),
    ("transport", "🚌 Transport", "Transport"),
    ("fun", "🎬 Entertainment", "Entertainment"),
    ("health", "💊 Health", "Health"),
    ("subs", "📺 Subscriptions", "Subscriptions"),
    ("gifts", "🎁 Gifts", "Gifts"),
    ("other", "📦 Other", "Other"),
]

INCOME_SOURCES = [
    ("grandma", "👵 Grandma", "Grandma"),
    ("parents", "👨‍👩‍👦 Parents", "Parents"),
    ("paycheck", "💼 Paycheck", "Paycheck"),
    ("bit", "📲 Bit", "Bit"),
    ("other", "📦 Other", "Other"),
]

ASK_OPTIONS = [
    ("invest", "💼 Total in investments"),
    ("left", "💸 Left to spend this month"),
    ("added", "📥 Money added this month"),
    ("spent", "📤 Money spent this month"),
]

EXPENSE_CATEGORY, EXPENSE_AMOUNT, INCOME_SOURCE, INCOME_AMOUNT, INVEST_AMOUNT = range(5)

MAX_AMOUNT = Decimal("1000000000")
MENU_BUTTONS = filters.Text([BTN_EXPENSE, BTN_INCOME, BTN_ASK, BTN_INVEST])
AMOUNT_TEXT = filters.TEXT & ~filters.COMMAND & ~MENU_BUTTONS


# ---------- helpers ----------

def now() -> datetime:
    return datetime.now(config.TZ)


def month_bounds(moment: datetime) -> tuple[datetime, datetime]:
    start = moment.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = (start + timedelta(days=32)).replace(day=1)
    return start, end


def money(amount: Decimal) -> str:
    if amount == amount.to_integral_value():
        return f"₪{amount:,.0f}"
    return f"₪{amount:,.2f}"


def fmt_date(moment: datetime) -> str:
    return moment.astimezone(config.TZ).strftime("%d/%m/%Y")


def parse_amount(text: str) -> Decimal | None:
    cleaned = text.replace("₪", "").replace(",", "").strip()
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    if not value.is_finite() or value <= 0 or value >= MAX_AMOUNT:
        return None
    return value.quantize(Decimal("0.01"))


def inline_grid(prefix: str, options: list[tuple], per_row: int = 3) -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(opt[1], callback_data=f"{prefix}:{opt[0]}") for opt in options]
    rows = [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]
    rows.append([InlineKeyboardButton("✖ Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)


async def reply(update: Update, text: str, **kwargs) -> None:
    """Reply to a text message or to a pressed inline button."""
    if update.callback_query:
        await update.callback_query.answer()
    await update.effective_message.reply_text(text, **kwargs)


def lookup(options: list[tuple], key: str) -> str | None:
    return next((opt[2] for opt in options if opt[0] == key), None)


async def budget_status() -> budget.BudgetStatus | None:
    budgets = await db.get_budgets()
    spent = await db.monthly_expense_totals()
    return budget.compute_status(now().date().replace(day=1), budgets, spent)


def left_to_spend_text(status: budget.BudgetStatus | None) -> str:
    if status is None:
        return "No monthly budget set yet. Use /setbudget <amount>, e.g. /setbudget 1500"
    return (
        f"Budget this month: {money(status.budget)}\n"
        f"Rolled over from last month: {money(status.carried_over)}\n"
        f"Spent so far: {money(status.spent)}\n"
        f"Left to spend: {money(status.remaining)}"
    )


def breakdown_text(title: str, rows: list[tuple[str, Decimal]]) -> str:
    if not rows:
        return f"{title}\nNothing yet this month."
    lines = [f"{name} - {money(amount)}" for name, amount in rows]
    total = sum((amount for _, amount in rows), Decimal(0))
    return f"{title}\n" + "\n".join(lines) + f"\n\nTotal: {money(total)}"


# ---------- access control ----------

async def block_strangers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None or user.id != config.ALLOWED_USER_ID:
        log.warning("Ignoring user %s (ALLOWED_USER_ID is %s)", user and user.id, config.ALLOWED_USER_ID)
        raise ApplicationHandlerStop
    if update.callback_query:
        log.info("Button pressed: %s", update.callback_query.data)
    elif update.effective_message and update.effective_message.text:
        log.info("Message received: %r", update.effective_message.text)


# ---------- commands ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Hi! 👋", reply_markup=MAIN_MENU)
    await update.message.reply_text("What would you like to do?", reply_markup=INLINE_MENU)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Cancelled.")
    else:
        await update.message.reply_text("Cancelled.", reply_markup=MAIN_MENU)
    return ConversationHandler.END


async def set_budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    amount = parse_amount(" ".join(context.args)) if context.args else None
    if amount is None:
        await update.message.reply_text("Usage: /setbudget <amount>, e.g. /setbudget 1500")
        return
    await db.set_budget(now().date().replace(day=1), amount)
    log.info("Budget set: %s", amount)
    await update.message.reply_text(
        f"Monthly budget set to {money(amount)} from this month on.\n\n"
        + left_to_spend_text(await budget_status()),
        reply_markup=MAIN_MENU,
    )


# ---------- add expense ----------

async def expense_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await reply(
        update,
        "What was this expense on?", reply_markup=inline_grid("exp", EXPENSE_CATEGORIES)
    )
    return EXPENSE_CATEGORY


async def expense_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    category = lookup(EXPENSE_CATEGORIES, query.data.split(":", 1)[1])
    context.user_data["category"] = category
    await query.edit_message_text(f"{category} - how much did it cost? (₪, or /cancel)")
    return EXPENSE_AMOUNT


async def expense_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    amount = parse_amount(update.message.text)
    if amount is None:
        await update.message.reply_text("Please send a positive number, e.g. 45 or 45.50")
        return EXPENSE_AMOUNT
    category = context.user_data.pop("category")
    created = await db.add_expense(category, amount)
    log.info("Expense saved: %s %s", category, amount)
    status = await budget_status()
    reply = f"✅ Saved {money(amount)} on {category} ({fmt_date(created)})."
    if status is not None:
        reply += f"\nLeft to spend this month: {money(status.remaining)}"
    await update.message.reply_text(reply, reply_markup=MAIN_MENU)
    return ConversationHandler.END


# ---------- add money ----------

async def income_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await reply(
        update,
        "Where did the money come from?", reply_markup=inline_grid("inc", INCOME_SOURCES)
    )
    return INCOME_SOURCE


async def income_source(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    source = lookup(INCOME_SOURCES, query.data.split(":", 1)[1])
    context.user_data["source"] = source
    await query.edit_message_text(f"{source} - how much? (₪, or /cancel)")
    return INCOME_AMOUNT


async def income_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    amount = parse_amount(update.message.text)
    if amount is None:
        await update.message.reply_text("Please send a positive number, e.g. 500")
        return INCOME_AMOUNT
    source = context.user_data.pop("source")
    created = await db.add_income(source, amount)
    log.info("Income saved: %s %s", source, amount)
    await update.message.reply_text(
        f"✅ Added {money(amount)} from {source} ({fmt_date(created)}).", reply_markup=MAIN_MENU
    )
    return ConversationHandler.END


# ---------- new investment ----------

async def invest_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await reply(update, "How much did you put in the investment? (₪, or /cancel)")
    return INVEST_AMOUNT


async def invest_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    amount = parse_amount(update.message.text)
    if amount is None:
        await update.message.reply_text("Please send a positive number, e.g. 1000")
        return INVEST_AMOUNT
    created = await db.add_investment(amount)
    log.info("Investment saved: %s", amount)
    total = await db.total_investments()
    await update.message.reply_text(
        f"✅ Invested {money(amount)} ({fmt_date(created)}).\nTotal in investments: {money(total)}",
        reply_markup=MAIN_MENU,
    )
    return ConversationHandler.END


# ---------- ask ----------

async def ask_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    buttons = [[InlineKeyboardButton(label, callback_data=f"ask:{key}")] for key, label in ASK_OPTIONS]
    await reply(update, "What do you want to know?", reply_markup=InlineKeyboardMarkup(buttons))
    return ConversationHandler.END


async def ask_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    key = query.data.split(":", 1)[1]
    start, end = month_bounds(now())
    month_name = start.strftime("%B %Y")

    if key == "invest":
        text = f"💼 Total in investments: {money(await db.total_investments())}"
    elif key == "left":
        text = "💸 " + left_to_spend_text(await budget_status())
    elif key == "added":
        text = breakdown_text(f"📥 Money added in {month_name}:", await db.incomes_by_source(start, end))
    else:
        text = breakdown_text(f"📤 Money spent in {month_name}:", await db.expenses_by_category(start, end))

    await query.message.reply_text(text, reply_markup=MAIN_MENU)


async def db_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        text = f"🟢 Connected to Postgres:\n{await db.connection_info()}"
    except Exception as exc:
        log.exception("Database check failed")
        text = f"🔴 Database check failed: {type(exc).__name__}"
    await update.message.reply_text(text)


async def stale_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer("This menu expired - pick an option from the main menu.")


# ---------- wiring ----------

def register(app: Application) -> None:
    app.add_handler(TypeHandler(Update, block_strangers), group=-1)

    menu_entries = [
        MessageHandler(filters.Text([BTN_EXPENSE]), expense_start),
        MessageHandler(filters.Text([BTN_INCOME]), income_start),
        MessageHandler(filters.Text([BTN_INVEST]), invest_start),
        MessageHandler(filters.Text([BTN_ASK]), ask_menu),
        CallbackQueryHandler(expense_start, pattern=r"^menu:expense$"),
        CallbackQueryHandler(income_start, pattern=r"^menu:income$"),
        CallbackQueryHandler(invest_start, pattern=r"^menu:invest$"),
        CallbackQueryHandler(ask_menu, pattern=r"^menu:ask$"),
        CommandHandler("start", start),
        CommandHandler("menu", start),
    ]
    app.add_handler(
        ConversationHandler(
            entry_points=menu_entries,
            states={
                EXPENSE_CATEGORY: [CallbackQueryHandler(expense_category, pattern=r"^exp:")],
                EXPENSE_AMOUNT: [MessageHandler(AMOUNT_TEXT, expense_amount)],
                INCOME_SOURCE: [CallbackQueryHandler(income_source, pattern=r"^inc:")],
                INCOME_AMOUNT: [MessageHandler(AMOUNT_TEXT, income_amount)],
                INVEST_AMOUNT: [MessageHandler(AMOUNT_TEXT, invest_amount)],
            },
            fallbacks=[
                CommandHandler("cancel", cancel),
                CallbackQueryHandler(cancel, pattern=r"^cancel$"),
            ],
            # Pressing another menu button mid-flow starts that flow instead.
            allow_reentry=True,
        )
    )
    app.add_handler(CommandHandler("setbudget", set_budget))
    app.add_handler(CommandHandler("dbstatus", db_status))
    app.add_handler(CallbackQueryHandler(ask_answer, pattern=r"^ask:"))
    app.add_handler(CallbackQueryHandler(stale_button))
