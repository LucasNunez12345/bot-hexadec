import re
import logging
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# --- Configuración Persistente ---
try:
    from sys import path
    path.append("/data/data/com.termux/files/home")
    from bot_config_secret import TOKEN, ADMIN_CHAT_ID, PRECIOS, HORARIO
except ImportError:
    logging.error("❌ Error: Archivo de configuración no encontrado.")
    exit(1)

# --- Estados para Conversación de Admin ---
EDIT_PRICE, SET_DISCOUNT = range(2)

# --- Validación de Datos ---
def is_valid_phone(phone: str) -> bool:
    """Valida formato de teléfono chileno"""
    return re.match(r'^(\+?56|0)[9]\d{8}$', phone.strip()) is not None

# --- Notificaciones Mejoradas ---
async def notify_admin(message: str, urgent=False):
    """Envía notificaciones con formato profesional"""
    bot = Bot(token=TOKEN)
    prefix = "🚨 *URGENTE* " if urgent else "🔔 "
    await bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"{prefix}Hexadec Alertas\n\n{message}",
        parse_mode="Markdown"
    )

# --- Flujo de Presupuestos ---
async def handle_budget_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa aceptación/rechazo de presupuestos"""
    query = update.callback_query
    await query.answer()
    
    action = query.data.split("_")[1]
    user_data = context.user_data
    
    if action == "aceptar":
        await query.edit_message_text(
            "🎉 *¡Presupuesto Aceptado!*\n\n"
            "Un ejecutivo se contactará contigo *en menos de 15 minutos*.\n\n"
            f"Horario: {HORARIO}\n\n"
            "¿Necesitas algo más? /start",
            parse_mode="Markdown"
        )
        await notify_admin(
            f"💰 *Presupuesto ACEPTADO*\n\n"
            f"• Servicio: {user_data['service']}\n"
            f"• Monto: ${user_data['presupuesto']} CLP\n"
            f"• Cliente: @{update.effective_user.username}\n\n"
            f"CONTACTAR INMEDIATO",
            urgent=True
        )
    else:
        await query.edit_message_text(
            "📝 Por favor, indícanos el motivo del rechazo:\n"
            "(Ej: 'Es muy caro', 'Encontré otro proveedor', etc.)",
            parse_mode="Markdown"
        )
        user_data["step"] = "motivo_rechazo"
    
    return ConversationHandler.END

async def log_rejection_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registra el motivo de rechazo y notifica al admin"""
    reason = update.message.text
    user_data = context.user_data
    
    await notify_admin(
        f"🚫 *Presupuesto RECHAZADO*\n\n"
        f"• Servicio: {user_data['service']}\n"
        f"• Monto: ${user_data['presupuesto']} CLP\n"
        f"• Cliente: @{update.effective_user.username}\n"
        f"• Motivo: _{reason}_\n\n"
        f"💡 Oportunidad para mejorar!",
        urgent=True
    )
    
    await update.message.reply_text(
        "⚠️ Hemos registrado tu feedback. ¿Quieres que te contactemos con una alternativa?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Sí, por favor", callback_data="contactar_alternativa")],
            [InlineKeyboardButton("❌ No, gracias", callback_data="cerrar_conversacion")]
        ])
    )
    user_data.clear()
    return ConversationHandler.END

# --- Verificación con Botones ---
async def confirm_user_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reemplaza la confirmación por texto con botones interactivos"""
    user_data = context.user_data
    await update.message.reply_text(
        "🔍 *Verifica tus datos*:\n\n"
        f"{user_data['datos_cliente']}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Todo Correcto", callback_data="datos_confirmados")],
            [InlineKeyboardButton("✏️ Corregir Información", callback_data="datos_incorrectos")]
        ]),
        parse_mode="Markdown"
    )

# --- Panel de Administración Completo ---
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menú de administración con todas las funciones"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return
    
    await update.message.reply_text(
        "🛠️ *PANEL DE ADMINISTRACIÓN* 🛠️\n\n"
        "Selecciona una opción:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Precios Actuales", callback_data="admin_precios")],
            [InlineKeyboardButton("✏️ Modificar Precios", callback_data="admin_edit_precios")],
            [InlineKeyboardButton("🎟️ Ofertas Temporales", callback_data="admin_ofertas")],
            [InlineKeyboardButton("📈 Estadísticas", callback_data="admin_stats")]
        ]),
        parse_mode="Markdown"
    )

async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestiona todas las acciones del panel admin"""
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")[1]
    
    if data == "precios":
        precios_text = "💰 *PRECIOS ACTUALES*\n\n"
        for servicio, valores in PRECIOS.items():
            precios_text += f"• {servicio.capitalize()}: ${valores['precio']} CLP"
            if valores.get("oferta"):
                precios_text += f" (🎟️ Oferta: ${valores['oferta']['precio_oferta']} hasta {valores['oferta']['valido_hasta']})"
            precios_text += "\n"
        
        await query.edit_message_text(
            precios_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Volver", callback_data="admin_back")]
            ])
        )
    
    elif data == "edit_precios":
        await query.edit_message_text(
            "✏️ *MODIFICAR PRECIOS*\n\n"
            "Selecciona el servicio a actualizar:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Programación", callback_data="edit_programacion")],
                [InlineKeyboardButton("Desbloqueo Motorola", callback_data="edit_motorola")],
                [InlineKeyboardButton("🔙 Volver", callback_data="admin_back")]
            ]),
            parse_mode="Markdown"
        )
        return EDIT_PRICE

# --- Handlers de Conversación para Admin ---
async def edit_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    service = query.data.split("_")[1]
    context.user_data["edit_service"] = service
    
    await query.edit_message_text(
        f"✏️ Ingresa el nuevo precio para *{service}* (solo números):",
        parse_mode="Markdown"
    )
    return SET_DISCOUNT

async def set_new_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_price = int(update.message.text)
        service = context.user_data["edit_service"]
        PRECIOS[service]["precio"] = new_price
        
        # Guardar cambios persistentes
        with open("/data/data/com.termux/files/home/bot_config_secret.py", "w") as f:
            f.write(f"TOKEN = '{TOKEN}'\nADMIN_CHAT_ID = '{ADMIN_CHAT_ID}'\n\nPRECIOS = {PRECIOS}\nHORARIO = '{HORARIO}'")
        
        await update.message.reply_text(
            f"✅ Precio de *{service}* actualizado a *${new_price} CLP*",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Ingresa solo números (Ej: 15000)")
        return SET_DISCOUNT

# --- Inicialización del Bot ---
def main():
    app = Application.builder().token(TOKEN).build()
    
    # Handlers principales
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    
    # Conversación para presupuestos
    budget_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_budget_response, pattern="^presupuesto_")],
        states={
            "motivo_rechazo": [MessageHandler(filters.TEXT & ~filters.COMMAND, log_rejection_reason)]
        },
        fallbacks=[]
    )
    app.add_handler(budget_handler)
    
    # Conversación para administración
    admin_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_admin_actions, pattern="^admin_")],
        states={
            EDIT_PRICE: [CallbackQueryHandler(edit_price, pattern="^edit_")],
            SET_DISCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_new_price)]
        },
        fallbacks=[CallbackQueryHandler(admin_panel, pattern="^admin_back")]
    )
    app.add_handler(admin_conversation)
    
    # Notificación de inicio
    async def post_init(application: Application):
        await notify_admin(
            f"⚡ *Bot iniciado correctamente*\n\n"
            f"🔄 Última actualización: {os.popen('git log -1 --pretty="%cr"').read().strip()}\n"
            f"📅 Hora del servidor: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
    
    app.post_init = post_init
    logging.info("Bot Hexadec iniciado 🚀")
    app.run_polling()

if __name__ == "__main__":
    main()
