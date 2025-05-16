import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from config import TOKEN, ADMIN_CHAT_ID, PRECIOS, HORARIO
from utils.alerts import send_alert_to_admin

# --- Menú del Bot ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔧 Programación", callback_data="servicio_programacion")],
        [InlineKeyboardButton("🔓 Desbloqueo", callback_data="servicio_desbloqueo")],
        [InlineKeyboardButton("💡 Asesoría/Compra", callback_data="servicio_asesoria")]
    ]
    await update.message.reply_text(
        "📻 *Hexadec Radiocomunicaciones*\n¿En qué podemos ayudarte?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- Respuestas ---
async def handle_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    service = query.data.split("_")[1]
    context.user_data["service"] = service
    
    if service == "programacion":
        await query.edit_message_text("¿Cuántos equipos necesitas programar? (Ej: 5)")
        context.user_data["step"] = "ask_quantity"
    elif service == "desbloqueo":
        await query.edit_message_text("¿Es para equipos Motorola? (Sí/No)")
        context.user_data["step"] = "ask_brand"
    else:
        await query.edit_message_text(
            f"🔔 *Un ejecutivo te contactará pronto.*\n\n"
            f"Horario:\n{HORARIO}\n\n"
            "Por favor, envía:\n1. Tu nombre.\n2. Teléfono.\n3. Detalles de la solicitud."
        )
        context.user_data["step"] = "ask_contact"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    
    if "step" not in user_data:
        return
    
    if user_data["step"] == "ask_quantity":
        try:
            cantidad = int(text)
            precio = PRECIOS["programacion"]["bulk"] if cantidad >= 10 else PRECIOS["programacion"]["unitario"]
            total = cantidad * precio
            await update.message.reply_text(f"💰 *Presupuesto:* ${total} CLP")
            user_data.clear()
        except:
            await update.message.reply_text("❌ Ingresa un número válido.")
    
    elif user_data["step"] == "ask_brand":
        if "sí" in text.lower() or "si" in text.lower():
            await update.message.reply_text("¿Cuántos equipos Motorola? (Ej: 3)")
            user_data["step"] = "ask_quantity"
            user_data["brand"] = "motorola"
        else:
            await send_alert_to_admin(
                update.message.chat_id,
                "Desbloqueo (otra marca)",
                f"Mensaje: {text}"
            )
            await update.message.reply_text("✅ Un ejecutivo te contactará para cotizar.")
            user_data.clear()
    
    elif user_data["step"] == "ask_contact":
        if "contact_info" not in user_data:
            user_data["contact_info"] = text
            await update.message.reply_text("📝 Ahora envía tu teléfono:")
        else:
            await send_alert_to_admin(
                update.message.chat_id,
                user_data["service"],
                f"Contacto: {user_data['contact_info']}\nTeléfono: {text}"
            )
            await update.message.reply_text("¡Gracias! Te contactaremos en breve.")
            user_data.clear()

# --- Iniciar Bot ---
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_service))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logging.info("Bot activo 🚀")
    app.run_polling()

if __name__ == "__main__":
    main()
