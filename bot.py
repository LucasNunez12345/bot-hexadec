import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from config import TOKEN, ADMIN_CHAT_ID, PRECIOS, HORARIO
from utils.alerts import send_alert_to_admin

# --- Validación de Teléfono ---
def is_valid_phone(phone: str) -> bool:
    return re.match(r'^(\+?56|0)[9]\d{8}$', phone.strip()) is not None

# --- Menú Principal ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name
    keyboard = [
        [InlineKeyboardButton("🔧 Programación", callback_data="servicio_programacion")],
        [InlineKeyboardButton("🔓 Desbloqueo", callback_data="servicio_desbloqueo")],
        [InlineKeyboardButton("💡 Asesoría/Compra", callback_data="servicio_asesoria")]
    ]
    await update.message.reply_text(
        f"👋 ¡Hola *{user_name}*! Bienvenido a *Hexadec Radiocomunicaciones*.\n\n"
        "¿En qué podemos ayudarte hoy?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# --- Handler de Servicios ---
async def handle_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    service = query.data.split("_")[1]
    context.user_data["service"] = service
    
    if service == "programacion":
        await query.edit_message_text(
            "✍️ Por favor, indícanos *cuántos equipos* necesitas programar (Ej: 5):",
            parse_mode="Markdown"
        )
        context.user_data["step"] = "ask_quantity"
    
    elif service == "desbloqueo":
        keyboard = [
            [InlineKeyboardButton("Motorola", callback_data="marca_motorola")],
            [InlineKeyboardButton("Otra marca", callback_data="marca_otra")]
        ]
        await query.edit_message_text(
            "📻 ¿Qué *marca* de equipos necesitas desbloquear?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    
    else:  # Asesoría/Compra
        await query.edit_message_text(
            "📝 Por favor, compártenos los siguientes datos:\n\n"
            "1. *Nombre completo*.\n"
            "2. *Teléfono* (Ej: +56912345678).\n"
            "3. *Detalles* de tu solicitud.\n\n"
            "⚠️ Envíalos *en un solo mensaje* para agilizar el proceso.",
            parse_mode="Markdown"
        )
        context.user_data["step"] = "ask_contact"

# --- Handler de Mensajes ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    
    if "step" not in user_data:
        await update.message.reply_text("ℹ️ Usa /start para comenzar.")
        return
    
    # Paso 1: Validar datos de contacto
    if user_data["step"] == "ask_contact":
        if "contact_info" not in user_data:
            user_data["contact_info"] = text
            await update.message.reply_text("🔢 Ahora, ingresa tu *teléfono* (Ej: +56987654321):", parse_mode="Markdown")
        else:
            if is_valid_phone(text):
                user_data["phone"] = text
                await update.message.reply_text(
                    "✅ ¡Gracias! Un ejecutivo te contactará pronto.\n\n"
                    f"📋 *Resumen:*\n"
                    f"• Nombre: {user_data['contact_info']}\n"
                    f"• Teléfono: {text}\n\n"
                    "¿Necesitas ayuda con algo más? (Usa /start)",
                    parse_mode="Markdown"
                )
                await send_alert_to_admin(
                    "Nueva solicitud de " + user_data["service"],
                    f"📞 Contacto: {user_data['contact_info']}\n"
                    f"📱 Teléfono: {text}\n"
                    f"📄 Mensaje: {user_data.get('last_msg', 'N/A')}"
                )
                user_data.clear()
            else:
                await update.message.reply_text("❌ Teléfono inválido. Ingresa uno válido (Ej: +56912345678).")
    
    # Paso 2: Validar cantidad de equipos (programación)
    elif user_data["step"] == "ask_quantity":
        try:
            cantidad = int(text)
            precio = PRECIOS["programacion"]["bulk"] if cantidad >= 10 else PRECIOS["programacion"]["unitario"]
            total = cantidad * precio
            user_data["presupuesto"] = total
            keyboard = [
                [InlineKeyboardButton("✅ Aceptar", callback_data="presupuesto_aceptar")],
                [InlineKeyboardButton("❌ Rechazar", callback_data="presupuesto_rechazar")]
            ]
            await update.message.reply_text(
                f"💰 *Presupuesto:* ${total} CLP (${precio} x {cantidad} equipos).\n\n"
                "¿Aceptas este presupuesto?",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            user_data["step"] = "confirm_presupuesto"
        except:
            await update.message.reply_text("❌ Por favor, ingresa un *número válido* (Ej: 5).", parse_mode="Markdown")

# --- Handler de Botones (Desbloqueo / Presupuesto) ---
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data.startswith("marca_"):
        brand = data.split("_")[1]
        if brand == "motorola":
            await query.edit_message_text("¿Cuántos equipos *Motorola* necesitas desbloquear? (Ej: 3):", parse_mode="Markdown")
            context.user_data["step"] = "ask_quantity"
            context.user_data["brand"] = "motorola"
        else:
            await query.edit_message_text(
                "⚠️ Para equipos de *otra marca*, un ejecutivo te contactará.\n\n"
                "Por favor, envía:\n1. Tu nombre.\n2. Teléfono.\n3. Marca/modelo.",
                parse_mode="Markdown"
            )
            context.user_data["step"] = "ask_contact"
    
    elif data.startswith("presupuesto_"):
        action = data.split("_")[1]
        if action == "aceptar":
            await query.edit_message_text(
                "🎉 ¡Perfecto! Un ejecutivo se pondrá en contacto contigo *de inmediato*.\n\n"
                "¿Necesitas ayuda con algo más? (Usa /start)",
                parse_mode="Markdown"
            )
            await send_alert_to_admin(
                "Presupuesto ACEPTADO",
                f"💰 Monto: ${context.user_data['presupuesto']} CLP\n"
                f"👤 Chat ID: {update.effective_chat.id}"
            )
        else:
            await query.edit_message_text(
                "📝 Por favor, indícanos el *motivo* por el que rechazas el presupuesto:\n"
                "(Ej: Precio alto, otra alternativa, etc.)",
                parse_mode="Markdown"
            )
            context.user_data["step"] = "ask_rechazo"
        context.user_data.clear()

# --- Iniciar Bot ---
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logging.info("Bot activo 🚀")
    app.run_polling()

if __name__ == "__main__":
    main()
