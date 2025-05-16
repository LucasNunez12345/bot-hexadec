import re
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- Configuración Persistente ---
try:
    from sys import path
    path.append("/data/data/com.termux/files/home")
    from bot_config_secret import TOKEN, ADMIN_CHAT_ID, PRECIOS, HORARIO
except ImportError:
    logging.error("❌ Error: Archivo de configuración no encontrado.")
    exit(1)

# --- Validación de Datos ---
def is_valid_phone(phone: str) -> bool:
    """Valida formato de teléfono chileno: +56912345678 o 56912345678"""
    return re.match(r'^(\+?56|0)[9]\d{8}$', phone.strip()) is not None

# --- Notificaciones ---
async def notify_admin(message: str):
    """Envía notificaciones estructuradas al administrador"""
    bot = Bot(token=TOKEN)
    await bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"🔔 *Hexadec - Notificación*\n\n{message}",
        parse_mode="Markdown"
    )

# --- Flujo Conversacional Mejorado ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mensaje de inicio con botones grandes y descriptivos"""
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("📱 Programar Equipos", callback_data="serv_programacion")],
        [InlineKeyboardButton("🔓 Desbloquear Equipos", callback_data="serv_desbloqueo")],
        [InlineKeyboardButton("💬 Asesoría Personalizada", callback_data="serv_asesoria")]
    ]
    
    await update.message.reply_text(
        f"👋 ¡Hola *{user.first_name}*! Soy tu asistente de *Hexadec Radiocomunicaciones*.\n\n"
        "Selecciona el servicio que necesitas:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_service_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa la selección de servicio con confirmación visual"""
    query = update.callback_query
    await query.answer()  # Importante para evitar timeouts
    
    service = query.data.split("_")[1]
    context.user_data.clear()
    context.user_data["service"] = service
    
    if service == "programacion":
        await query.edit_message_text(
            "✍️ *Programación de Equipos*\n\n"
            "Por favor, ingresa la *cantidad de equipos* a programar:\n"
            "(Ejemplo: 5)",
            parse_mode="Markdown"
        )
        context.user_data["step"] = "cantidad_equipos"
    
    elif service == "desbloqueo":
        # Menú de marcas con botones
        keyboard = [
            [InlineKeyboardButton("Motorola", callback_data="marca_motorola")],
            [InlineKeyboardButton("Otra Marca", callback_data="marca_otra")]
        ]
        await query.edit_message_text(
            "📻 *Desbloqueo de Equipos*\n\n"
            "Selecciona la marca de tus equipos:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    
    else:  # Asesoría
        await query.edit_message_text(
            "💼 *Asesoría Personalizada*\n\n"
            "Por favor, compártenos:\n\n"
            "1. Tu *nombre completo*\n"
            "2. *Teléfono* de contacto (Ej: +56912345678)\n"
            "3. *Detalles* de lo que necesitas\n\n"
            "⚠️ Envíalo todo en *un solo mensaje* así:\n"
            "• Nombre: Juan Pérez\n"
            "• Teléfono: +56987654321\n"
            "• Detalles: Necesito asesoría para compra de 10 radios",
            parse_mode="Markdown"
        )
        context.user_data["step"] = "datos_contacto"

async def handle_marca_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa selección de marca para desbloqueo"""
    query = update.callback_query
    await query.answer()
    
    marca = query.data.split("_")[1]
    
    if marca == "motorola":
        await query.edit_message_text(
            "📟 *Desbloqueo Motorola*\n\n"
            "Ingresa la *cantidad de equipos* a desbloquear:\n"
            "(Ejemplo: 3)",
            parse_mode="Markdown"
        )
        context.user_data["step"] = "cantidad_equipos"
        context.user_data["marca"] = "motorola"
    else:
        await query.edit_message_text(
            "🛠️ *Desbloqueo Otras Marcas*\n\n"
            "Un especialista se contactará contigo. Por favor envíanos:\n\n"
            "1. Tu *nombre completo*\n"
            "2. *Teléfono* de contacto\n"
            "3. *Marca/Modelo* de los equipos",
            parse_mode="Markdown"
        )
        context.user_data["step"] = "datos_contacto"

async def handle_user_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa todas las respuestas de texto del usuario"""
    user_data = context.user_data
    text = update.message.text
    
    # Flujo para programación/desbloqueo Motorola
    if user_data.get("step") == "cantidad_equipos":
        try:
            cantidad = int(text)
            if user_data["service"] == "programacion":
                precio = PRECIOS["programacion"]["bulk"] if cantidad >= 10 else PRECIOS["programacion"]["unitario"]
                total = cantidad * precio
                user_data["presupuesto"] = total
                
                keyboard = [
                    [InlineKeyboardButton("✅ Aceptar Presupuesto", callback_data="accion_aceptar")],
                    [InlineKeyboardButton("❌ Rechazar Presupuesto", callback_data="accion_rechazar")]
                ]
                
                await update.message.reply_text(
                    f"💰 *Presupuesto para {cantidad} equipos*\n\n"
                    f"• Precio unitario: ${precio} CLP\n"
                    f"• *Total:* ${total} CLP\n\n"
                    "¿Deseas aceptar este presupuesto?",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
                user_data["step"] = "confirmar_presupuesto"
            
            elif user_data.get("marca") == "motorola":
                total = cantidad * PRECIOS["desbloqueo_motorola"]
                await update.message.reply_text(
                    f"🔓 *Desbloqueo Motorola*\n\n"
                    f"• Equipos: {cantidad}\n"
                    f"• *Total:* ${total} CLP\n\n"
                    "Un ejecutivo se contactará para coordinar el servicio.",
                    parse_mode="Markdown"
                )
                await notify_admin(
                    f"Nuevo servicio de desbloqueo Motorola\n\n"
                    f"• Equipos: {cantidad}\n"
                    f"• Total: ${total} CLP\n"
                    f"• Cliente: @{update.effective_user.username}"
                )
                user_data.clear()
        
        except ValueError:
            await update.message.reply_text(
                "❌ Por favor ingresa solo números (Ej: 5)",
                parse_mode="Markdown"
            )
    
    # Flujo para datos de contacto
    elif user_data.get("step") == "datos_contacto":
        if "datos_cliente" not in user_data:
            user_data["datos_cliente"] = text
            await update.message.reply_text(
                "📋 *Verificación de Datos*\n\n"
                "Por favor confirma que esta información es correcta:\n\n"
                f"{text}\n\n"
                "Responde *SI* o *NO*",
                parse_mode="Markdown"
            )
            user_data["step"] = "confirmar_datos"
        else:
            await update.message.reply_text(
                "ℹ️ Ya hemos registrado tu información. "
                "Un ejecutivo se contactará contigo pronto.",
                parse_mode="Markdown"
            )
    
    # Confirmación de datos
    elif user_data.get("step") == "confirmar_datos":
        if text.lower() in ["si", "sí"]:
            await update.message.reply_text(
                "✅ ¡Perfecto! Hemos registrado tu solicitud.\n\n"
                "Horario de contacto:\n"
                f"{HORARIO}\n\n"
                "¿Necesitas ayuda con algo más? (Usa /start)",
                parse_mode="Markdown"
            )
            await notify_admin(
                f"Nueva solicitud de {user_data['service']}\n\n"
                f"Datos del cliente:\n{user_data['datos_cliente']}\n\n"
                f"Usuario: @{update.effective_user.username}"
            )
            user_data.clear()
        else:
            await update.message.reply_text(
                "🔄 Por favor, vuelve a enviarnos tus datos:\n\n"
                "1. Nombre completo\n"
                "2. Teléfono\n"
                "3. Detalles de tu solicitud",
                parse_mode="Markdown"
            )
            user_data["step"] = "datos_contacto"
            del user_data["datos_cliente"]

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa confirmación/rechazo de presupuestos"""
    query = update.callback_query
    await query.answer()
    
    action = query.data.split("_")[1]
    user_data = context.user_data
    
    if action == "aceptar":
        await query.edit_message_text(
            "🎉 *¡Presupuesto Aceptado!*\n\n"
            "Un ejecutivo se contactará contigo *dentro de los próximos 15 minutos*.\n\n"
            "Horario de atención:\n"
            f"{HORARIO}\n\n"
            "¿Necesitas algo más? (Usa /start)",
            parse_mode="Markdown"
        )
        await notify_admin(
            f"🚨 PRESUPUESTO ACEPTADO\n\n"
            f"• Servicio: {user_data['service']}\n"
            f"• Monto: ${user_data['presupuesto']} CLP\n"
            f"• Cliente: @{update.effective_user.username}\n\n"
            f"Contactar urgentemente!"
        )
    else:
        await query.edit_message_text(
            "📝 Por favor, indícanos el motivo del rechazo:\n"
            "(Ej: Precio elevado, encontré otra opción, etc.)",
            parse_mode="Markdown"
        )
        user_data["step"] = "motivo_rechazo"
    
    user_data.clear()

# --- Inicialización del Bot ---
def main():
    app = Application.builder().token(TOKEN).build()
    
    # Handlers principales
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_service_selection, pattern="^serv_"))
    app.add_handler(CallbackQueryHandler(handle_marca_selection, pattern="^marca_"))
    app.add_handler(CallbackQueryHandler(handle_confirmation, pattern="^accion_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_response))
    
    # Notificación de inicio
    async def post_init(application: Application):
        await notify_admin(
            f"⚡ Bot iniciado correctamente\n\n"
            f"🔄 Última actualización: {os.popen('git log -1 --pretty="%cr"').read().strip()}"
        )
    
    app.add_handler(CommandHandler("status", lambda u,c: notify_admin("El bot está activo ✅")))
    app.post_init = post_init
    
    logging.info("Bot Hexadec iniciado 🚀")
    app.run_polling()

if __name__ == "__main__":
    main()
