import os
import requests
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from dotenv import load_dotenv

load_dotenv()

# ====== CONFIG ======
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

USERS_IN_INSERT_MODE = set()

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

TABLE_URL = f"{SUPABASE_URL}/rest/v1/market_list"


# ====== SUPABASE REST HELPERS ======

def add_item(user_id: int, product_name: str):
    payload = {
        "telegram_user_id": user_id,
        "product_name": product_name
    }
    requests.post(TABLE_URL, json=payload, headers=HEADERS)


def get_items(user_id: int):
    url = (
        f"{TABLE_URL}"
        f"?telegram_user_id=eq.{user_id}"
        f"&order=created_at.asc"
    )
    response = requests.get(url, headers=HEADERS)
    return response.json()


def toggle_item_checked(item_id: str, checked: bool):
    url = f"{TABLE_URL}?id=eq.{item_id}"
    payload = {"checked": checked}
    requests.patch(url, json=payload, headers=HEADERS)


def clear_items(user_id: int):
    url = f"{TABLE_URL}?telegram_user_id=eq.{user_id}"
    requests.delete(url, headers=HEADERS)


# ====== COMMANDS ======

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛒 Olá, Dona Celina! Eu sou o Eugênio.\n\n"
        "Comandos:\n"
        "/lista → adicionar produtos\n"
        "/fim → finalizar lista\n"
        "/mercado → ver checklist\n"
        "/limpar → apagar lista"
    )


async def lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    USERS_IN_INSERT_MODE.add(update.effective_user.id)
    await update.message.reply_text(
        "📝 Modo lista ativado.\n"
        "O que a senhora deseja comprar dona Celina?.\n"
        "Quando terminar, envie /fim"
    )


async def fim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    USERS_IN_INSERT_MODE.discard(update.effective_user.id)
    await update.message.reply_text("✅ Lista salva com sucesso, dona Celina!")


async def receber_produto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in USERS_IN_INSERT_MODE:
        return

    produto = update.message.text.strip()
    add_item(user_id, produto)

    await update.message.reply_text(f"➕ {produto} adicionado")


async def mercado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    items = get_items(user_id)

    if not items:
        await update.message.reply_text("🛒 Sua lista está vazia.")
        return

    keyboard = []
    for item in items:
        check = "✅" if item["checked"] else "⬜"
        keyboard.append([
            InlineKeyboardButton(
                f"{check} {item['product_name']}",
                callback_data=f"toggle:{item['id']}"
            )
        ])

    await update.message.reply_text(
        "🛍️ Lista de mercado:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def toggle_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    item_id = query.data.split(":")[1]
    user_id = query.from_user.id

    items = get_items(user_id)
    item = next(i for i in items if i["id"] == item_id)

    new_value = not item["checked"]
    toggle_item_checked(item_id, new_value)

    # Atualiza teclado na hora
    items = get_items(user_id)
    keyboard = []

    for item in items:
        check = "✅" if item["checked"] else "⬜"
        keyboard.append([
            InlineKeyboardButton(
                f"{check} {item['product_name']}",
                callback_data=f"toggle:{item['id']}"
            )
        ])

    await query.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def limpar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    clear_items(user_id)
    await update.message.reply_text("🗑️ Lista apagada Dona Celina, pode criar outra!")


# ====== MAIN ======

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lista", lista))
    app.add_handler(CommandHandler("fim", fim))
    app.add_handler(CommandHandler("mercado", mercado))
    app.add_handler(CommandHandler("limpar", limpar))
    app.add_handler(CallbackQueryHandler(toggle_item))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_produto))

    print("🤖 Eugênio está rodando...")
    app.run_polling()


if __name__ == "__main__":
    main()