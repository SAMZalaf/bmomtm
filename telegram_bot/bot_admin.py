# ============================================
# bot_admin.py - وظائف الآدمن الشاملة
# يحتوي على: States + Admin Functions + Message Management
# ============================================

import os
import asyncio
import logging
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from telegram.constants import ParseMode

from config import (
    Config, DATABASE_FILE, MESSAGES,
    get_country_name, get_state_name, get_message
)

from bot_utils import (
    db, escape_html, escape_markdown_v2,
    get_syria_time, get_syria_time_str, log_with_syria_time,
    generate_order_id, get_detailed_proxy_type, get_current_price
)

# استيراد الكيبوردات الموحدة
from bot_keyboards import (
    create_main_user_keyboard, create_admin_keyboard,
    create_back_button, create_confirmation_keyboard
)

logger = logging.getLogger(__name__)

# ============================================
# قسم 1: حالات المحادثة (States) - من admin_states.py
# ============================================

(
    ADMIN_LOGIN, ADMIN_MENU, PROCESS_ORDER, 
    ENTER_PROXY_TYPE, ENTER_PROXY_ADDRESS, ENTER_PROXY_PORT,
    ENTER_COUNTRY, ENTER_STATE, ENTER_USERNAME, ENTER_PASSWORD,
    ENTER_THANK_MESSAGE, PAYMENT_PROOF, CUSTOM_MESSAGE,
    REFERRAL_AMOUNT, USER_LOOKUP, QUIET_HOURS, LANGUAGE_SELECTION,
    PAYMENT_METHOD_SELECTION, WITHDRAWAL_REQUEST, SET_PRICE_STATIC,
    SET_PRICE_SOCKS, ADMIN_ORDER_INQUIRY, BROADCAST_MESSAGE,
    BROADCAST_USERS, BROADCAST_CONFIRM, PACKAGE_MESSAGE, PACKAGE_CONFIRMATION,
    PACKAGE_ACTION_CHOICE, SET_PRICE_RESIDENTIAL, SET_PRICE_ISP,
    SET_PRICE_ISP_ATT, SET_PRICE_VERIZON, SET_PRICE_RESIDENTIAL_2,
    SET_PRICE_DAILY, SET_PRICE_WEEKLY, ADD_FREE_PROXY, DELETE_FREE_PROXY,
    ENTER_PROXY_QUANTITY, EDIT_SERVICES_MESSAGE_AR, EDIT_SERVICES_MESSAGE_EN, 
    EDIT_EXCHANGE_RATE_MESSAGE_AR, EDIT_EXCHANGE_RATE_MESSAGE_EN,
    BALANCE_RECHARGE_REQUEST, BALANCE_RECHARGE_PROOF, SET_POINT_PRICE,
    ENTER_RECHARGE_AMOUNT, CONFIRM_DELETE_ALL_ORDERS, ADMIN_RECHARGE_AMOUNT_INPUT,
    BAN_USER_CONFIRM, UNBAN_USER_CONFIRM, REMOVE_TEMP_BAN_CONFIRM,
    ADD_POINTS_AMOUNT, ADD_POINTS_MESSAGE, SUBTRACT_POINTS_AMOUNT, SUBTRACT_POINTS_MESSAGE,
    ADD_REFERRAL_USERNAME, DELETE_REFERRAL_SELECT, RESET_REFERRAL_CONFIRM,
    SINGLE_USER_BROADCAST_MESSAGE, MANAGE_USER_BANS,
    NONVOIP_MENU, NONVOIP_SELECT_TYPE, NONVOIP_SELECT_STATE, NONVOIP_SELECT_PRODUCT, NONVOIP_CONFIRM_ORDER,
    NONVOIP_HISTORY, NONVOIP_CONFIRM_RENEW,
    NONVOIP_ADMIN_MENU, NONVOIP_VIEW_BALANCE, NONVOIP_VIEW_PRODUCTS, NONVOIP_VIEW_ORDERS,
    SET_PRICE_NONVOIP,
    EDIT_TERMS_MESSAGE_AR, EDIT_TERMS_MESSAGE_EN
) = range(74)

# قاموس جميع الحالات للاستيراد السهل
ALL_STATES = {
    'ADMIN_LOGIN': ADMIN_LOGIN,
    'ADMIN_MENU': ADMIN_MENU,
    'PROCESS_ORDER': PROCESS_ORDER,
    'ENTER_PROXY_TYPE': ENTER_PROXY_TYPE,
    'ENTER_PROXY_ADDRESS': ENTER_PROXY_ADDRESS,
    'ENTER_PROXY_PORT': ENTER_PROXY_PORT,
    'ENTER_COUNTRY': ENTER_COUNTRY,
    'ENTER_STATE': ENTER_STATE,
    'ENTER_USERNAME': ENTER_USERNAME,
    'ENTER_PASSWORD': ENTER_PASSWORD,
    'ENTER_THANK_MESSAGE': ENTER_THANK_MESSAGE,
    'PAYMENT_PROOF': PAYMENT_PROOF,
    'CUSTOM_MESSAGE': CUSTOM_MESSAGE,
    'REFERRAL_AMOUNT': REFERRAL_AMOUNT,
    'USER_LOOKUP': USER_LOOKUP,
    'QUIET_HOURS': QUIET_HOURS,
    'LANGUAGE_SELECTION': LANGUAGE_SELECTION,
    'PAYMENT_METHOD_SELECTION': PAYMENT_METHOD_SELECTION,
    'WITHDRAWAL_REQUEST': WITHDRAWAL_REQUEST,
    'SET_PRICE_STATIC': SET_PRICE_STATIC,
    'SET_PRICE_SOCKS': SET_PRICE_SOCKS,
    'ADMIN_ORDER_INQUIRY': ADMIN_ORDER_INQUIRY,
    'BROADCAST_MESSAGE': BROADCAST_MESSAGE,
    'BROADCAST_USERS': BROADCAST_USERS,
    'BROADCAST_CONFIRM': BROADCAST_CONFIRM,
    'PACKAGE_MESSAGE': PACKAGE_MESSAGE,
    'PACKAGE_CONFIRMATION': PACKAGE_CONFIRMATION,
    'PACKAGE_ACTION_CHOICE': PACKAGE_ACTION_CHOICE,
    'SET_PRICE_RESIDENTIAL': SET_PRICE_RESIDENTIAL,
    'SET_PRICE_ISP': SET_PRICE_ISP,
    'SET_PRICE_ISP_ATT': SET_PRICE_ISP_ATT,
    'SET_PRICE_VERIZON': SET_PRICE_VERIZON,
    'SET_PRICE_RESIDENTIAL_2': SET_PRICE_RESIDENTIAL_2,
    'SET_PRICE_DAILY': SET_PRICE_DAILY,
    'SET_PRICE_WEEKLY': SET_PRICE_WEEKLY,
    'ADD_FREE_PROXY': ADD_FREE_PROXY,
    'DELETE_FREE_PROXY': DELETE_FREE_PROXY,
    'ENTER_PROXY_QUANTITY': ENTER_PROXY_QUANTITY,
    'EDIT_SERVICES_MESSAGE_AR': EDIT_SERVICES_MESSAGE_AR,
    'EDIT_SERVICES_MESSAGE_EN': EDIT_SERVICES_MESSAGE_EN,
    'EDIT_EXCHANGE_RATE_MESSAGE_AR': EDIT_EXCHANGE_RATE_MESSAGE_AR,
    'EDIT_EXCHANGE_RATE_MESSAGE_EN': EDIT_EXCHANGE_RATE_MESSAGE_EN,
    'BALANCE_RECHARGE_REQUEST': BALANCE_RECHARGE_REQUEST,
    'BALANCE_RECHARGE_PROOF': BALANCE_RECHARGE_PROOF,
    'SET_POINT_PRICE': SET_POINT_PRICE,
    'ENTER_RECHARGE_AMOUNT': ENTER_RECHARGE_AMOUNT,
    'CONFIRM_DELETE_ALL_ORDERS': CONFIRM_DELETE_ALL_ORDERS,
    'ADMIN_RECHARGE_AMOUNT_INPUT': ADMIN_RECHARGE_AMOUNT_INPUT,
    'BAN_USER_CONFIRM': BAN_USER_CONFIRM,
    'UNBAN_USER_CONFIRM': UNBAN_USER_CONFIRM,
    'REMOVE_TEMP_BAN_CONFIRM': REMOVE_TEMP_BAN_CONFIRM,
    'ADD_POINTS_AMOUNT': ADD_POINTS_AMOUNT,
    'ADD_POINTS_MESSAGE': ADD_POINTS_MESSAGE,
    'SUBTRACT_POINTS_AMOUNT': SUBTRACT_POINTS_AMOUNT,
    'SUBTRACT_POINTS_MESSAGE': SUBTRACT_POINTS_MESSAGE,
    'ADD_REFERRAL_USERNAME': ADD_REFERRAL_USERNAME,
    'DELETE_REFERRAL_SELECT': DELETE_REFERRAL_SELECT,
    'RESET_REFERRAL_CONFIRM': RESET_REFERRAL_CONFIRM,
    'SINGLE_USER_BROADCAST_MESSAGE': SINGLE_USER_BROADCAST_MESSAGE,
    'MANAGE_USER_BANS': MANAGE_USER_BANS,
    'NONVOIP_MENU': NONVOIP_MENU,
    'NONVOIP_SELECT_TYPE': NONVOIP_SELECT_TYPE,
    'NONVOIP_SELECT_STATE': NONVOIP_SELECT_STATE,
    'NONVOIP_SELECT_PRODUCT': NONVOIP_SELECT_PRODUCT,
    'NONVOIP_CONFIRM_ORDER': NONVOIP_CONFIRM_ORDER,
    'NONVOIP_HISTORY': NONVOIP_HISTORY,
    'NONVOIP_CONFIRM_RENEW': NONVOIP_CONFIRM_RENEW,
    'NONVOIP_ADMIN_MENU': NONVOIP_ADMIN_MENU,
    'NONVOIP_VIEW_BALANCE': NONVOIP_VIEW_BALANCE,
    'NONVOIP_VIEW_PRODUCTS': NONVOIP_VIEW_PRODUCTS,
    'NONVOIP_VIEW_ORDERS': NONVOIP_VIEW_ORDERS,
    'SET_PRICE_NONVOIP': SET_PRICE_NONVOIP,
    'EDIT_TERMS_MESSAGE_AR': EDIT_TERMS_MESSAGE_AR,
    'EDIT_TERMS_MESSAGE_EN': EDIT_TERMS_MESSAGE_EN
}

# حالة خاصة لتعديل الرسائل
WAITING_NEW_TEXT = 'WAITING_NEW_TEXT'

# ============================================
# قسم 2: المتغيرات العامة للآدمن
# ============================================

ACTIVE_ADMINS: List[int] = []
ADMIN_CHAT_ID: Optional[int] = None
pending_unban_notifications: List[int] = []

if hasattr(Config, 'ADMIN_PASSWORD'):
    ADMIN_PASSWORD = Config.ADMIN_PASSWORD
else:
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "sohilSOHIL")

# ============================================
# قسم 3: دوال الوصول للمتغيرات العامة
# ============================================

def get_active_admins() -> List[int]:
    """الحصول على قائمة الآدمن النشطين"""
    return ACTIVE_ADMINS

def add_active_admin(user_id: int) -> None:
    """إضافة آدمن نشط"""
    global ACTIVE_ADMINS
    if user_id not in ACTIVE_ADMINS:
        ACTIVE_ADMINS.append(user_id)

def remove_active_admin(user_id: int) -> None:
    """إزالة آدمن من النشطين"""
    global ACTIVE_ADMINS
    if user_id in ACTIVE_ADMINS:
        ACTIVE_ADMINS.remove(user_id)

def is_admin_active(user_id: int) -> bool:
    """التحقق من نشاط آدمن"""
    return user_id in ACTIVE_ADMINS

def is_admin(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """التحقق من أن المستخدم آدمن"""
    return context.user_data.get('is_admin', False) or user_id in ACTIVE_ADMINS

# ============================================
# قسم 4: دوال مساعدة للآدمن
# ============================================

def get_admin_language(user_id: int) -> str:
    """الحصول على لغة الآدمن (منفصلة عن لغة المستخدم العادي)"""
    try:
        result = db.execute_query("SELECT language FROM users WHERE user_id = ?", (user_id,))
        return result[0][0] if result and result[0][0] else 'ar'
    except:
        return 'ar'

def set_admin_language(user_id: int, language: str) -> None:
    """تعيين لغة الآدمن"""
    try:
        db.execute_query("UPDATE users SET language = ? WHERE user_id = ?", (language, user_id))
    except Exception as e:
        logger.error(f"خطأ في تعيين لغة الآدمن: {e}")

def get_user_language(user_id: int) -> str:
    """الحصول على لغة المستخدم"""
    try:
        result = db.execute_query("SELECT language FROM users WHERE user_id = ?", (user_id,))
        return result[0][0] if result and result[0][0] else 'ar'
    except:
        return 'ar'

def clean_user_data_preserve_admin(context: ContextTypes.DEFAULT_TYPE) -> None:
    """تنظيف البيانات المؤقتة مع الحفاظ على حالة الأدمن"""
    is_admin = context.user_data.get('is_admin', False)
    context.user_data.clear()
    if is_admin:
        context.user_data['is_admin'] = True

async def restore_admin_keyboard(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message: Optional[str] = None, language: Optional[str] = None):
    """إعادة تفعيل كيبورد الأدمن الرئيسي - تستخدم الكيبورد من bot_keyboards"""
    if language is None:
        language = get_admin_language(chat_id)
    
    reply_markup = create_admin_keyboard(language)
    
    if message:
        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            reply_markup=reply_markup
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=MESSAGES[language]['admin_welcome'],
            reply_markup=reply_markup
        )

# ============================================
# قسم 5: إشعارات الحظر للآدمن
# ============================================

async def notify_admin_ban(context, user_id: int, ban_type: str, username: str = ""):
    """إخبار الآدمن النشطين عن حظر مستخدم"""
    try:
        global ACTIVE_ADMINS
        
        if not ACTIVE_ADMINS:
            return
            
        ban_messages = {
            "warning": "تحذير مستخدم",
            "ban_10_min": "حظر 10 دقائق", 
            "ban_2_hours": "حظر ساعتين",
            "ban_24_hours": "حظر 24 ساعة"
        }
        
        ban_text = ban_messages.get(ban_type, ban_type)
        user_text = f"@{username}" if username else f"ID: {user_id}"
        message = f"🚨 تم {ban_text} للمستخدم {user_text}\n⚠️ السبب: نشاط تخريبي (نقرات متكررة)"
        
        for admin_id in ACTIVE_ADMINS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=message
                )
            except Exception as e:
                logger.error(f"Error sending ban notification to admin {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error notifying admins about ban: {e}")

async def notify_admin_unban(context_or_app, user_id: int, username: str = ""):
    """إخبار الآدمن النشطين عن رفع حظر مستخدم"""
    try:
        global ACTIVE_ADMINS
        
        if not ACTIVE_ADMINS:
            return
            
        user_text = f"@{username}" if username else f"ID: {user_id}"
        message = f"✅ تم رفع الحظر عن المستخدم {user_text}"
        
        for admin_id in ACTIVE_ADMINS:
            try:
                if hasattr(context_or_app, 'bot'):
                    await context_or_app.bot.send_message(
                        chat_id=admin_id,
                        text=message
                    )
                else:
                    await context_or_app.bot.send_message(
                        chat_id=admin_id,
                        text=message
                    )
            except Exception as e:
                logger.error(f"Error sending unban notification to admin {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error notifying admins about unban: {e}")

async def notify_user_unban(context_or_app, chat_id: int):
    """إخبار المستخدم عن رفع الحظر"""
    try:
        if hasattr(context_or_app, 'bot'):
            await context_or_app.bot.send_message(
                chat_id=chat_id,
                text="✅ تم رفع الحظر عنك، يمكنك الآن استخدام البوت بشكل طبيعي"
            )
        else:
            await context_or_app.bot.send_message(
                chat_id=chat_id,
                text="✅ تم رفع الحظر عنك، يمكنك الآن استخدام البوت بشكل طبيعي"
            )
    except Exception as e:
        logger.error(f"Error notifying user about unban: {e}")

async def process_pending_unban_notifications(application):
    """معالجة الإشعارات المعلقة لرفع الحظر"""
    global pending_unban_notifications
    
    if not pending_unban_notifications:
        return
    
    notifications_to_process = pending_unban_notifications.copy()
    pending_unban_notifications.clear()
    
    for user_id in notifications_to_process:
        try:
            user_result = db.execute_query("SELECT username FROM users WHERE user_id = ?", (user_id,))
            username = user_result[0][0] if user_result and user_result[0][0] else ""
            
            try:
                await notify_user_unban(application, user_id)
            except Exception as e:
                logger.error(f"Failed to notify user {user_id} about unban: {e}")
            
            try:
                await notify_admin_unban(application, user_id, username)
            except Exception as e:
                logger.error(f"Failed to notify admin about user {user_id} unban: {e}")
                
        except Exception as e:
            logger.error(f"Error processing unban notification for user {user_id}: {e}")

# ============================================
# قسم 6: تسجيل دخول الآدمن
# ============================================

async def admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """تسجيل دخول الأدمن"""
    language = get_user_language(update.effective_user.id)
    await update.message.reply_text(MESSAGES[language]['admin_login_prompt'])
    return ADMIN_LOGIN

async def handle_admin_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """التحقق من كلمة مرور الأدمن"""
    global ADMIN_PASSWORD, ACTIVE_ADMINS
    if update.message.text == ADMIN_PASSWORD:
        user_id = update.effective_user.id
        context.user_data['is_admin'] = True
        
        if user_id not in ACTIVE_ADMINS:
            ACTIVE_ADMINS.append(user_id)
        
        try:
            db.log_action(user_id, "admin_login_success")
        except Exception as log_error:
            logger.error(f"Error logging admin login: {log_error}")
        
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
        except Exception as e:
            print(f"تعذر حذف رسالة كلمة المرور: {e}")
        
        original_language = get_user_language(user_id)
        context.user_data['original_user_language'] = original_language
        
        db.update_user_language(user_id, 'ar')
        admin_language = 'ar'
        logger.info(f"تم ضبط اللغة العربية للأدمن {user_id} عند تسجيل الدخول (اللغة الأصلية: {original_language})")
        
        await restore_admin_keyboard(context, user_id, None, admin_language)
        return ConversationHandler.END
    else:
        await update.message.reply_text("كلمة المرور غير صحيحة!")
        return ConversationHandler.END

async def change_admin_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء عملية تغيير كلمة مرور الأدمن"""
    user_language = get_user_language(update.effective_user.id)
    
    if user_language == 'ar':
        message = "🔐 تغيير كلمة المرور\n\nيرجى إدخال كلمة المرور الحالية أولاً:"
    else:
        message = "🔐 Change Password\n\nPlease enter current password first:"
    
    back_text = "🔙 رجوع" if user_language == 'ar' else "🔙 Back"
    keyboard = [[InlineKeyboardButton(back_text, callback_data="cancel_password_change")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, reply_markup=reply_markup)
    context.user_data['password_change_step'] = 'current'
    return ADMIN_LOGIN

async def handle_password_change(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة تغيير كلمة المرور"""
    global ADMIN_PASSWORD
    step = context.user_data.get('password_change_step', 'current')
    user_language = get_user_language(update.effective_user.id)
    
    if step == 'current':
        if update.message.text == ADMIN_PASSWORD:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=update.message.message_id
                )
            except Exception as e:
                print(f"تعذر حذف رسالة كلمة المرور الحالية: {e}")
            
            context.user_data['password_change_step'] = 'new'
            if user_language == 'ar':
                keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_password_change")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text("✅ كلمة المرور صحيحة\n\nيرجى إدخال كلمة المرور الجديدة:", reply_markup=reply_markup)
            else:
                keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="cancel_password_change")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text("✅ Password correct\n\nPlease enter new password:", reply_markup=reply_markup)
            return ADMIN_LOGIN
        else:
            if user_language == 'ar':
                await update.message.reply_text("❌ كلمة المرور غير صحيحة!")
            else:
                await update.message.reply_text("❌ Invalid password!")
            context.user_data.pop('password_change_step', None)
            return ConversationHandler.END
    
    elif step == 'new':
        new_password = update.message.text
        ADMIN_PASSWORD = new_password
        
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
        except Exception as e:
            print(f"تعذر حذف رسالة كلمة المرور الجديدة: {e}")
        
        db.execute_query(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            ("admin_password", new_password)
        )
        
        if user_language == 'ar':
            await update.message.reply_text("✅ تم تغيير كلمة المرور بنجاح!")
        else:
            await update.message.reply_text("✅ Password changed successfully!")
        
        context.user_data.pop('password_change_step', None)
        return ConversationHandler.END
    
    return ConversationHandler.END

async def handle_cancel_password_change(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إلغاء تغيير كلمة المرور"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_language = get_user_language(user_id)
    is_admin_user = context.user_data.get('is_admin', False)
    
    if user_language == 'ar':
        await query.edit_message_text("❌ تم إلغاء تغيير كلمة المرور")
    else:
        await query.edit_message_text("❌ Password change cancelled")
    
    context.user_data.pop('password_change_step', None)
    
    if is_admin_user:
        await restore_admin_keyboard(context, user_id, "🔧 لوحة الأدمن جاهزة")
    
    return ConversationHandler.END

# ============================================
# قسم 7: قوائم لوحة التحكم
# ============================================

async def handle_admin_menu_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة إجراءات لوحة الأدمن"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "admin_referrals":
        await show_admin_referrals(query, context)
    
    elif query.data == "user_lookup":
        context.user_data['lookup_action'] = 'lookup'
        await query.edit_message_text("يرجى إرسال معرف المستخدم أو @username للبحث:")
        return USER_LOOKUP

async def show_admin_referrals(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض إحصائيات الإحالات للأدمن"""
    total_referrals = db.execute_query("SELECT COUNT(*) FROM referrals")[0][0]
    total_amount = db.execute_query("SELECT SUM(amount) FROM referrals")[0][0] or 0
    
    top_referrers = db.execute_query('''
        SELECT u.first_name, u.last_name, COUNT(r.id) as referral_count, SUM(r.amount) as total_earned
        FROM users u
        JOIN referrals r ON u.user_id = r.referrer_id
        GROUP BY u.user_id
        ORDER BY referral_count DESC
        LIMIT 5
    ''')
    
    message = f"📊 إحصائيات الإحالات\n\n"
    message += f"إجمالي الإحالات: {total_referrals}\n"
    message += f"إجمالي المبلغ: {total_amount:.2f}$\n\n"
    message += "أفضل المحيلين:\n"
    
    for i, referrer in enumerate(top_referrers, 1):
        message += f"{i}. {referrer[0]} {referrer[1]}: {referrer[2]} إحالة ({referrer[3]:.2f}$)\n"
    
    keyboard = [
        [InlineKeyboardButton("تحديد قيمة الإحالة", callback_data="set_referral_amount")],
        [InlineKeyboardButton("تصفير رصيد مستخدم", callback_data="reset_user_balance")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup)

async def handle_admin_orders_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة قائمة إدارة الطلبات للأدمن"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    buttons = MESSAGES[language]['orders_menu_buttons']
    keyboard = [
        [KeyboardButton(buttons[0])],
        [KeyboardButton(buttons[1])],
        [KeyboardButton(buttons[2]), KeyboardButton(buttons[3])],
        [KeyboardButton(buttons[4])]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        MESSAGES[language]['orders_menu_title'],
        reply_markup=reply_markup
    )

async def handle_admin_money_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة قائمة إدارة الأموال للأدمن"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    buttons = MESSAGES[language]['money_menu_buttons']
    keyboard = [
        [KeyboardButton(buttons[0])],
        [KeyboardButton(buttons[1])],
        [KeyboardButton(buttons[2])],
        [KeyboardButton(buttons[3])]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        MESSAGES[language]['money_menu_title'],
        reply_markup=reply_markup
    )

async def handle_admin_referrals_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة قائمة إدارة الإحالات للأدمن"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    buttons = MESSAGES[language]['referrals_menu_buttons']
    keyboard = [
        [KeyboardButton(buttons[0])],
        [KeyboardButton(buttons[1])],
        [KeyboardButton(buttons[2])],
        [KeyboardButton(buttons[3])]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        MESSAGES[language]['referrals_menu_title'],
        reply_markup=reply_markup
    )

async def handle_admin_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة قائمة إعدادات الأدمن"""
    user_id = update.effective_user.id
    language = get_admin_language(user_id)
    
    buttons = MESSAGES[language]['settings_menu_buttons']
    keyboard = [
        [KeyboardButton(buttons[0])],
        [KeyboardButton(buttons[1])],
        [KeyboardButton(buttons[2])],
        [KeyboardButton(buttons[3])],
        [KeyboardButton(buttons[4])],
        [KeyboardButton(buttons[5])],
        [KeyboardButton(buttons[6])],
        [KeyboardButton(buttons[7])]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        MESSAGES[language]['settings_menu_title'],
        reply_markup=reply_markup
    )

async def handle_admin_user_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة استعلام عن مستخدم"""
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_user_lookup")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🔍 استعلام عن مستخدم\n\nيرجى إرسال:\n- معرف المستخدم (رقم)\n- أو اسم المستخدم (@username)",
        reply_markup=reply_markup
    )
    return USER_LOOKUP

async def return_to_user_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """العودة لوضع المستخدم العادي"""
    context.user_data['is_admin'] = False
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    reply_markup = create_main_user_keyboard(language)
    
    await update.message.reply_text(
        MESSAGES[language]['welcome'],
        reply_markup=reply_markup
    )

async def return_to_admin_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """العودة للقائمة الرئيسية للأدمن"""
    user_id = update.effective_user.id
    await restore_admin_keyboard(context, user_id)

async def admin_logout_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تأكيد تسجيل خروج الأدمن"""
    keyboard = [
        [
            InlineKeyboardButton("✅ نعم", callback_data="confirm_admin_logout"),
            InlineKeyboardButton("❌ لا", callback_data="cancel_admin_logout")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "⚠️ هل تريد تسجيل الخروج من لوحة الأدمن؟",
        reply_markup=reply_markup
    )

async def handle_logout_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة تأكيد تسجيل الخروج"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if query.data == "confirm_admin_logout":
        global ACTIVE_ADMINS
        context.user_data['is_admin'] = False
        if user_id in ACTIVE_ADMINS:
            ACTIVE_ADMINS.remove(user_id)
        
        original_language = context.user_data.get('original_user_language', 'ar')
        db.update_user_language(user_id, original_language)
        
        language = get_user_language(user_id)
        reply_markup = create_main_user_keyboard(language)
        
        await query.edit_message_text("✅ تم تسجيل الخروج بنجاح")
        await context.bot.send_message(
            chat_id=user_id,
            text=MESSAGES[language]['welcome'],
            reply_markup=reply_markup
        )
    else:
        await query.edit_message_text("❌ تم إلغاء تسجيل الخروج")
        await restore_admin_keyboard(context, user_id)

async def handle_back_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """العودة للقائمة الرئيسية للأدمن من callback"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    await restore_admin_keyboard(context, user_id)

# ============================================
# قسم 8: إدارة الطلبات
# ============================================

async def show_pending_orders_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض الطلبات المعلقة للأدمن"""
    try:
        pending_orders = db.execute_query('''
            SELECT o.order_id, o.user_id, u.first_name, u.last_name, o.proxy_type, 
                   o.country, o.state, o.total_price, o.status, o.created_at
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.user_id
            WHERE o.status = 'pending'
            ORDER BY o.created_at DESC
            LIMIT 20
        ''')
        
        if not pending_orders:
            await update.message.reply_text("📋 لا توجد طلبات معلقة حالياً")
            return
        
        message = "📋 الطلبات المعلقة:\n\n"
        for order in pending_orders:
            order_id, user_id, first_name, last_name, proxy_type, country, state, price, status, created_at = order
            message += f"🔖 #{order_id}\n"
            message += f"👤 {first_name} {last_name or ''}\n"
            message += f"📦 {proxy_type} - {country}\n"
            message += f"💰 {price}$\n"
            message += f"📅 {created_at}\n"
            message += "─" * 20 + "\n"
        
        await update.message.reply_text(message)
        
    except Exception as e:
        logger.error(f"Error showing pending orders: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء جلب الطلبات")

async def delete_processed_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """حذف الطلبات المعالجة"""
    try:
        result = db.execute_query("DELETE FROM orders WHERE status IN ('completed', 'cancelled')")
        await update.message.reply_text("✅ تم حذف الطلبات المعالجة بنجاح")
    except Exception as e:
        logger.error(f"Error deleting processed orders: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء حذف الطلبات")

async def delete_all_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """تأكيد حذف جميع الطلبات"""
    keyboard = [
        [
            InlineKeyboardButton("✅ نعم، احذف الكل", callback_data="confirm_delete_all_orders"),
            InlineKeyboardButton("❌ إلغاء", callback_data="cancel_delete_all_orders")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "⚠️ تحذير!\n\nهل أنت متأكد من حذف جميع الطلبات؟\nهذا الإجراء لا يمكن التراجع عنه!",
        reply_markup=reply_markup
    )
    return CONFIRM_DELETE_ALL_ORDERS

async def admin_order_inquiry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء استعلام عن طلب"""
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_order_inquiry")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🔍 استعلام عن طلب\n\nيرجى إرسال رقم الطلب:",
        reply_markup=reply_markup
    )
    return ADMIN_ORDER_INQUIRY

# ============================================
# قسم 9: نظام البث
# ============================================

async def broadcast_referral_update(context: ContextTypes.DEFAULT_TYPE, new_percentage: float) -> None:
    """إرسال إشعار بتحديث نسبة الإحالة لجميع المستخدمين"""
    try:
        all_users = db.execute_query("SELECT user_id, language FROM users")
        
        for user_id, language in all_users:
            try:
                if language == 'ar':
                    message = f"📢 تحديث نظام الإحالات\n\nتم تحديث نسبة الإحالة إلى {new_percentage}%"
                else:
                    message = f"📢 Referral System Update\n\nReferral percentage updated to {new_percentage}%"
                
                await context.bot.send_message(chat_id=user_id, text=message)
            except Exception as e:
                logger.error(f"Failed to send referral update to {user_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error broadcasting referral update: {e}")

async def broadcast_price_update(context: ContextTypes.DEFAULT_TYPE, price_type: str, prices: dict) -> None:
    """إرسال إشعار بتحديث الأسعار لجميع المستخدمين"""
    try:
        all_users = db.execute_query("SELECT user_id, language FROM users")
        
        for user_id, language in all_users:
            try:
                if language == 'ar':
                    message = f"📢 تحديث الأسعار\n\nتم تحديث أسعار {price_type}"
                else:
                    message = f"📢 Price Update\n\n{price_type} prices have been updated"
                
                await context.bot.send_message(chat_id=user_id, text=message)
            except Exception as e:
                logger.error(f"Failed to send price update to {user_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error broadcasting price update: {e}")

async def show_broadcast_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض قائمة البث"""
    keyboard = [
        [InlineKeyboardButton("📢 بث للجميع", callback_data="broadcast_all")],
        [InlineKeyboardButton("👥 بث لمستخدمين محددين", callback_data="broadcast_selected")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📢 قائمة البث\n\nاختر نوع البث:",
        reply_markup=reply_markup
    )

async def handle_broadcast_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار نوع البث"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "broadcast_all":
        context.user_data['broadcast_type'] = 'all'
        await query.edit_message_text(
            "📢 بث للجميع\n\nأرسل الرسالة التي تريد بثها لجميع المستخدمين:\n\n"
            "يمكنك إرسال نص أو صورة مع نص."
        )
        return BROADCAST_MESSAGE
    
    elif query.data == "broadcast_selected":
        context.user_data['broadcast_type'] = 'selected'
        await query.edit_message_text(
            "👥 بث لمستخدمين محددين\n\n"
            "أرسل قائمة معرفات المستخدمين (كل معرف في سطر منفصل):\n\n"
            "مثال:\n123456789\n987654321\n@username"
        )
        return BROADCAST_USERS
    
    return ConversationHandler.END

async def handle_cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إلغاء البث"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("❌ تم إلغاء البث")
    
    broadcast_keys = ['broadcast_type', 'broadcast_message', 'broadcast_users_input', 'broadcast_valid_users', 'broadcast_photo']
    for key in broadcast_keys:
        context.user_data.pop(key, None)
    
    await restore_admin_keyboard(context, update.effective_user.id)
    return ConversationHandler.END

# ============================================
# قسم 10: إدارة الرسائل (من admin_message_management.py)
# ============================================

def set_selected_message(db_file: str, admin_id: int, message_id: int, chat_id: int, target_user_id: int = None):
    """تحديد رسالة للآدمن (إلغاء التحديد السابق إذا وجد)"""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM admin_selected_messages WHERE admin_id = ?", (admin_id,))
    
    try:
        cursor.execute("ALTER TABLE admin_selected_messages ADD COLUMN target_user_id INTEGER")
    except:
        pass
    
    cursor.execute("""
        INSERT INTO admin_selected_messages (admin_id, message_id, chat_id, target_user_id)
        VALUES (?, ?, ?, ?)
    """, (admin_id, message_id, chat_id, target_user_id))
    
    conn.commit()
    conn.close()

def get_selected_message(db_file: str, admin_id: int):
    """الحصول على الرسالة المحددة للآدمن"""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT message_id, chat_id, target_user_id FROM admin_selected_messages
            WHERE admin_id = ?
            ORDER BY selected_at DESC
            LIMIT 1
        """, (admin_id,))
        result = cursor.fetchone()
        conn.close()
        return result if result else (None, None, None)
    except:
        cursor.execute("""
            SELECT message_id, chat_id FROM admin_selected_messages
            WHERE admin_id = ?
            ORDER BY selected_at DESC
            LIMIT 1
        """, (admin_id,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return (result[0], result[1], None)
        return (None, None, None)

def clear_selected_message(db_file: str, admin_id: int):
    """إلغاء تحديد الرسالة للآدمن"""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM admin_selected_messages WHERE admin_id = ?", (admin_id,))
    
    conn.commit()
    conn.close()

def track_bot_message(db_file: str, original_message_id: int, original_chat_id: int, 
                     user_id: int, user_chat_id: int, user_message_id: int):
    """تتبع نسخة رسالة البوت المرسلة لمستخدم معين"""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO bot_message_copies 
        (original_message_id, original_chat_id, user_id, user_chat_id, user_message_id)
        VALUES (?, ?, ?, ?, ?)
    """, (original_message_id, original_chat_id, user_id, user_chat_id, user_message_id))
    
    conn.commit()
    conn.close()

def get_message_copies(db_file: str, original_message_id: int, original_chat_id: int):
    """الحصول على جميع نسخ رسالة البوت الموزعة للمستخدمين"""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT user_id, user_chat_id, user_message_id
        FROM bot_message_copies
        WHERE original_message_id = ? AND original_chat_id = ?
    """, (original_message_id, original_chat_id))
    
    results = cursor.fetchall()
    conn.close()
    
    return results

def get_user_id_by_username(db_file: str, username: str):
    """الحصول على user_id من username"""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None

def parse_target_user(text: str, db_file: str):
    """استخراج معرف المستخدم المستهدف من النص (إذا وجد)"""
    parts = text.strip().split()
    if len(parts) > 1:
        target = parts[1]
        if target.startswith('@'):
            username = target[1:]
            user_id = get_user_id_by_username(db_file, username)
            if user_id:
                return ('user_id', user_id)
            else:
                return ('username_not_found', username)
        elif target.isdigit():
            return ('user_id', int(target))
    return (None, None)

async def handle_msg_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /msg_options - يحدد رسالة للإدارة"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id, context):
        await update.message.reply_text("⛔ هذا الأمر متاح فقط للآدمن.")
        return
    
    if not update.message.reply_to_message:
        help_text = escape_markdown_v2("""📋 نظام إدارة رسائل البوت للآدمن

━━━━━━━━━━━━━━━━━━━━━━━━━━━

/msg_options (يُستخدم بالرد على رسالة)
├── /msg_delete - حذف الرسالة المحددة
├── /msg_edit - تعديل الرسالة المحددة
├── /msg_pin - تثبيت الرسالة المحددة
└── /msg_unpin - فك تثبيت الرسالة المحددة

/msg_clean (يمكن استخدامه بدون رد على رسالة)
└── حذف جميع رسائل البوت لدى جميع المستخدمين

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 القواعد الأساسية:
• /msg_options يتطلب الرد على رسالة
• /msg_clean لا يتطلب الرد على رسالة
• استخدام /msg_options مرتين، الثانية تلغي الأولى
• أي إدخال لا يبدأ بـ /msg يلغي التحديد تلقائياً""")
        
        await update.message.reply_text(help_text, parse_mode='MarkdownV2')
        return
    
    replied_msg = update.message.reply_to_message
    message_id = replied_msg.message_id
    chat_id = replied_msg.chat_id
    
    target_type, target_value = parse_target_user(update.message.text, DATABASE_FILE)
    
    if target_type == 'username_not_found':
        await update.message.reply_text(
            f"❌ المستخدم @{target_value} غير موجود في قاعدة البيانات.\n"
            "تأكد من أن المستخدم قد تفاعل مع البوت من قبل."
        )
        return
    
    target_user_id = target_value if target_type == 'user_id' else None
    
    try:
        set_selected_message(DATABASE_FILE, user_id, message_id, chat_id, target_user_id)
        
        target_info = ""
        if target_user_id:
            target_info = f" للمستخدم المحدد (ID: {target_user_id})"
        
        await update.message.reply_text(
            f"✅ تم تحديد الرسالة بنجاح{target_info}!\n\n"
            "يمكنك الآن استخدام أحد الأوامر التالية:\n"
            "• /msg_delete - حذف الرسالة\n"
            "• /msg_pin - تثبيت الرسالة\n"
            "• /msg_unpin - فك تثبيت الرسالة\n"
            "• /msg_edit - تعديل الرسالة (استخدم Edit Message)\n\n"
            "💡 ملاحظة: أي إدخال آخر سيلغي التحديد تلقائياً."
        )
    except Exception as e:
        logger.error(f"Error in handle_msg_options: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء تحديد الرسالة.")

async def handle_msg_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /msg_delete - حذف الرسالة المحددة"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id, context):
        await update.message.reply_text("⛔ هذا الأمر متاح فقط للآدمن.")
        return
    
    # 1. محاولة الحذف المباشر إذا كان رداً على رسالة
    if update.message.reply_to_message:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=update.message.reply_to_message.message_id
            )
            # حذف أمر الأدمن أيضاً لتنظيف الشات
            try:
                await update.message.delete()
            except:
                pass
            return
        except Exception as e:
            logger.error(f"Direct delete failed: {e}")

    # 2. إذا لم يكن حذفا مباشرا أو فشل، نلجأ لنظام التتبع
    message_id, chat_id, target_user_id = get_selected_message(DATABASE_FILE, user_id)
    
    if not message_id:
        if not update.message.reply_to_message:
            await update.message.reply_text(
                "❌ يجب الرد على رسالة لحذفها مباشرة، أو استخدام /msg_options أولاً للحذف الجماعي."
            )
        return
    
    try:
        copies = get_message_copies(DATABASE_FILE, message_id, chat_id)
        
        deleted_count = 0
        failed_count = 0
        
        for copy_user_id, copy_chat_id, copy_message_id in copies:
            if target_user_id and copy_user_id != target_user_id:
                continue
            
            if copy_user_id != user_id:
                try:
                    await context.bot.delete_message(
                        chat_id=copy_chat_id,
                        message_id=copy_message_id
                    )
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete message {copy_message_id} for user {copy_user_id}: {e}")
                    failed_count += 1
        
        target_info = ""
        if target_user_id:
            target_info = f" للمستخدم المحدد (ID: {target_user_id})"
        
        notification = f"✅ تم حذف الرسالة{target_info}!\n"
        notification += f"📊 تم الحذف لدى {deleted_count} مستخدم"
        
        if failed_count > 0:
            notification += f"\n⚠️ فشل الحذف لدى {failed_count} مستخدم"
        
        await update.message.reply_text(notification)
        clear_selected_message(DATABASE_FILE, user_id)
        
    except Exception as e:
        logger.error(f"Error in handle_msg_delete: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء حذف الرسالة.")

async def handle_msg_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /msg_pin - تثبيت الرسالة لدى المستخدمين المحددين"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id, context):
        await update.message.reply_text("⛔ هذا الأمر متاح فقط للآدمن.")
        return
    
    message_id, chat_id, target_user_id = get_selected_message(DATABASE_FILE, user_id)
    
    if not message_id:
        await update.message.reply_text(
            "❌ لا توجد رسالة محددة!\n"
            "يجب استخدام /msg_options أولاً بالرد على الرسالة المراد تثبيتها."
        )
        return
    
    try:
        await context.bot.pin_chat_message(
            chat_id=chat_id,
            message_id=message_id,
            disable_notification=True
        )
        
        copies = get_message_copies(DATABASE_FILE, message_id, chat_id)
        
        pinned_count = 0
        failed_count = 0
        
        for copy_user_id, copy_chat_id, copy_message_id in copies:
            if target_user_id and copy_user_id != target_user_id:
                continue
            
            try:
                await context.bot.pin_chat_message(
                    chat_id=copy_chat_id,
                    message_id=copy_message_id,
                    disable_notification=True
                )
                pinned_count += 1
            except Exception as e:
                logger.error(f"Failed to pin message {copy_message_id} for user {copy_user_id}: {e}")
                failed_count += 1
        
        target_info = ""
        if target_user_id:
            target_info = f" للمستخدم المحدد (ID: {target_user_id})"
            notification = f"✅ تم تثبيت الرسالة{target_info}!\n"
            notification += f"📊 تم التثبيت لدى {pinned_count} مستخدم"
        else:
            notification = f"✅ تم تثبيت الرسالة بنجاح!\n"
            notification += f"📊 تم التثبيت لدى {pinned_count + 1} مستخدم (بما فيك)"
        
        if failed_count > 0:
            notification += f"\n⚠️ فشل التثبيت لدى {failed_count} مستخدم"
        
        await update.message.reply_text(notification)
        
        clear_selected_message(DATABASE_FILE, user_id)
        
    except Exception as e:
        logger.error(f"Error in handle_msg_pin: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء تثبيت الرسالة.")

async def handle_msg_unpin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /msg_unpin - فك تثبيت الرسالة"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id, context):
        await update.message.reply_text("⛔ هذا الأمر متاح فقط للآدمن.")
        return
    
    message_id, chat_id, target_user_id = get_selected_message(DATABASE_FILE, user_id)
    
    if not message_id:
        await update.message.reply_text(
            "❌ لا توجد رسالة محددة!\n"
            "يجب استخدام /msg_options أولاً بالرد على الرسالة المراد فك تثبيتها."
        )
        return
    
    try:
        await context.bot.unpin_chat_message(
            chat_id=chat_id,
            message_id=message_id
        )
        
        copies = get_message_copies(DATABASE_FILE, message_id, chat_id)
        
        unpinned_count = 0
        failed_count = 0
        
        for copy_user_id, copy_chat_id, copy_message_id in copies:
            if target_user_id and copy_user_id != target_user_id:
                continue
            
            try:
                await context.bot.unpin_chat_message(
                    chat_id=copy_chat_id,
                    message_id=copy_message_id
                )
                unpinned_count += 1
            except Exception as e:
                logger.error(f"Failed to unpin message {copy_message_id} for user {copy_user_id}: {e}")
                failed_count += 1
        
        target_info = ""
        if target_user_id:
            target_info = f" للمستخدم المحدد (ID: {target_user_id})"
            notification = f"✅ تم فك تثبيت الرسالة{target_info}!\n"
            notification += f"📊 تم فك التثبيت لدى {unpinned_count} مستخدم"
        else:
            notification = f"✅ تم فك تثبيت الرسالة بنجاح!\n"
            notification += f"📊 تم فك التثبيت لدى {unpinned_count + 1} مستخدم (بما فيك)"
        
        if failed_count > 0:
            notification += f"\n⚠️ فشل فك التثبيت لدى {failed_count} مستخدم"
        
        await update.message.reply_text(notification)
        
        clear_selected_message(DATABASE_FILE, user_id)
        
    except Exception as e:
        logger.error(f"Error in handle_msg_unpin: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء فك تثبيت الرسالة.")

async def handle_msg_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /msg_edit - طلب نص جديد من الآدمن لتعديل الرسالة"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id, context):
        await update.message.reply_text("⛔ هذا الأمر متاح فقط للآدمن.")
        return ConversationHandler.END
    
    message_id, chat_id, target_user_id = get_selected_message(DATABASE_FILE, user_id)
    
    if not message_id:
        await update.message.reply_text(
            "❌ لا توجد رسالة محددة!\n"
            "يجب استخدام /msg_options أولاً بالرد على الرسالة المراد تعديلها."
        )
        return ConversationHandler.END
    
    target_info = ""
    if target_user_id:
        target_info = f" للمستخدم المحدد (ID: {target_user_id})"
    
    instructions = (
        f"✏️ *طرق تعديل الرسالة{target_info}:*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📌 *الطريقة الأولى:* Edit Message التقليدي\n"
        "• مناسب للرسائل التي أرسلتها أنت كآدمن\n"
        "• اضغط على الرسالة → Edit Message → عدّل النص\n"
        "• التعديل سيُطبق تلقائياً على الجميع\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📌 *الطريقة الثانية:* إرسال نص جديد (للبوت)\n"
        "• مناسب لرسائل البوت التي لا يمكنك تعديلها\n"
        "• أرسل النص الجديد الآن مباشرة\n"
        "• سيتم استبدال الرسالة القديمة بالنص الجديد لدى الجميع\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 *اختر الطريقة المناسبة:*\n"
        "• إذا كانت الرسالة من البوت ← أرسل النص الجديد الآن\n"
        "• إذا كانت رسالتك أنت ← استخدم Edit Message\n\n"
        "📝 *أرسل النص الجديد الآن، أو /cancel للإلغاء*"
    )
    
    await update.message.reply_text(
        instructions,
        parse_mode='Markdown'
    )
    
    context.user_data['edit_message_id'] = message_id
    context.user_data['edit_chat_id'] = chat_id
    context.user_data['edit_target_user_id'] = target_user_id
    
    return WAITING_NEW_TEXT

async def handle_new_text_for_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة النص الجديد لتعديل الرسالة لدى الجميع"""
    user_id = update.effective_user.id
    new_text = update.message.text
    
    if new_text == '/cancel':
        await update.message.reply_text("❌ تم إلغاء عملية التعديل.")
        context.user_data.pop('edit_message_id', None)
        return ConversationHandler.END
    
    message_id = context.user_data.get('edit_message_id')
    chat_id = context.user_data.get('edit_chat_id')
    target_user_id = context.user_data.get('edit_target_user_id')
    
    if not message_id:
        await update.message.reply_text("❌ انتهت صلاحية الجلسة، يرجى البدء من جديد.")
        return ConversationHandler.END
    
    try:
        # الحصول على نسخ الرسالة
        copies = get_message_copies(DATABASE_FILE, message_id, chat_id)
        
        edited_count = 0
        failed_count = 0
        
        # 1. محاولة تعديل الرسالة الأصلية أولاً
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=new_text,
                parse_mode='HTML'
            )
            edited_count += 1
        except Exception as e:
            logger.debug(f"Could not edit original message: {e}")
            # إذا فشل التعديل المباشر، نحاول الحذف والإرسال
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
                await context.bot.send_message(chat_id=chat_id, text=new_text, parse_mode='HTML')
                edited_count += 1
            except:
                pass

        # 2. تعديل كافة النسخ لدى المستخدمين
        for copy_user_id, copy_chat_id, copy_message_id in copies:
            if target_user_id and copy_user_id != target_user_id:
                continue
            
            if copy_user_id != user_id:
                try:
                    await context.bot.edit_message_text(
                        chat_id=copy_chat_id,
                        message_id=copy_message_id,
                        text=new_text,
                        parse_mode='HTML'
                    )
                    edited_count += 1
                except Exception as e:
                    logger.debug(f"Failed to edit copy for user {copy_user_id}: {e}")
                    # محاولة الحذف والإرسال كبديل
                    try:
                        await context.bot.delete_message(chat_id=copy_chat_id, message_id=copy_message_id)
                        await context.bot.send_message(chat_id=copy_chat_id, text=new_text, parse_mode='HTML')
                        edited_count += 1
                    except:
                        failed_count += 1
        
        target_info = ""
        if target_user_id:
            target_info = f" للمستخدم المحدد (ID: {target_user_id})"
        
        notification = f"✅ تم تعديل الرسالة{target_info} بنجاح!\n"
        notification += f"📊 تم التعديل لدى {edited_count} مستخدم"
        
        if failed_count > 0:
            notification += f"\n⚠️ فشل التعديل لدى {failed_count} مستخدم"
        
        await update.message.reply_text(notification)
        
        # تنظيف البيانات
        context.user_data.pop('edit_message_id', None)
        clear_selected_message(DATABASE_FILE, user_id)
        
    except Exception as e:
        logger.error(f"Error in handle_new_text_for_edit: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء تعديل الرسالة.")
        
    return ConversationHandler.END

async def handle_cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج إلغاء عملية التعديل"""
    context.user_data.pop('edit_message_id', None)
    context.user_data.pop('edit_chat_id', None)
    context.user_data.pop('edit_target_user_id', None)
    
    await update.message.reply_text("❌ تم إلغاء عملية التعديل.")
    
    return ConversationHandler.END

async def handle_msg_clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /msg_clean - حذف جميع رسائل البوت لدى جميع المستخدمين"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id, context):
        await update.message.reply_text("⛔ هذا الأمر متاح فقط للآدمن.")
        return
    
    target_type, target_value = parse_target_user(update.message.text, DATABASE_FILE)
    
    if target_type == 'username_not_found':
        await update.message.reply_text(
            f"❌ المستخدم @{target_value} غير موجود في قاعدة البيانات.\n"
            "تأكد من أن المستخدم قد تفاعل مع البوت من قبل."
        )
        return
    
    target_user_id = target_value if target_type == 'user_id' else None
    
    context.user_data['msg_clean_target_user_id'] = target_user_id
    
    target_info = ""
    if target_user_id:
        target_info = f" للمستخدم المحدد (ID: {target_user_id})"
    else:
        users_count = db.execute_query("SELECT COUNT(DISTINCT user_id) FROM users")
        total_users = users_count[0][0] if users_count else 0
        target_info = f" لدى جميع المستخدمين ({total_users} مستخدم)"
    
    keyboard = [
        [
            InlineKeyboardButton("✅ تأكيد الحذف", callback_data="confirm_msg_clean"),
            InlineKeyboardButton("❌ إلغاء", callback_data="cancel_msg_clean")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"⚠️ تحذير: أنت على وشك حذف جميع رسائل البوت{target_info}!\n\n"
        "هذا الإجراء لا يمكن التراجع عنه.\n\n"
        "هل أنت متأكد من المتابعة؟",
        reply_markup=reply_markup
    )

async def handle_msg_clean_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة تأكيد أو إلغاء حذف جميع الرسائل"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if not is_admin(user_id, context):
        await query.edit_message_text("⛔ هذا الأمر متاح فقط للآدمن.")
        return
    
    if query.data == "confirm_msg_clean":
        await query.edit_message_text("🗑️ جاري حذف جميع الرسائل...")
        
        target_user_id = context.user_data.get('msg_clean_target_user_id')
        
        try:
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            
            if target_user_id:
                cursor.execute("""
                    SELECT user_id, user_chat_id, user_message_id
                    FROM bot_message_copies
                    WHERE user_id = ?
                """, (target_user_id,))
            else:
                cursor.execute("""
                    SELECT user_id, user_chat_id, user_message_id
                    FROM bot_message_copies
                """)
            
            copies = cursor.fetchall()
            conn.close()
            
            deleted_count = 0
            failed_count = 0
            
            for copy_user_id, copy_chat_id, copy_message_id in copies:
                if copy_user_id == user_id:
                    continue
                
                try:
                    await context.bot.delete_message(
                        chat_id=copy_chat_id,
                        message_id=copy_message_id
                    )
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete message {copy_message_id} for user {copy_user_id}: {e}")
                    failed_count += 1
            
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            
            if target_user_id:
                cursor.execute("DELETE FROM bot_message_copies WHERE user_id = ?", (target_user_id,))
                cursor.execute("DELETE FROM admin_selected_messages WHERE admin_id = ? AND target_user_id = ?", (user_id, target_user_id))
            else:
                cursor.execute("DELETE FROM bot_message_copies")
                cursor.execute("DELETE FROM admin_selected_messages WHERE admin_id = ?", (user_id,))
            
            conn.commit()
            conn.close()
            
            target_info = ""
            if target_user_id:
                target_info = f" للمستخدم المحدد (ID: {target_user_id})"
            
            notification = f"✅ تم حذف جميع الرسائل{target_info}!\n\n"
            notification += f"📊 الإحصائيات:\n"
            notification += f"✅ تم الحذف: {deleted_count} رسالة\n"
            
            if failed_count > 0:
                notification += f"⚠️ فشل الحذف: {failed_count} رسالة"
            
            await query.edit_message_text(notification)
            
            context.user_data.pop('msg_clean_target_user_id', None)
            
        except Exception as e:
            logger.error(f"Error in handle_msg_clean_confirmation: {e}")
            await query.edit_message_text("❌ حدث خطأ أثناء حذف الرسائل.")
            
    elif query.data == "cancel_msg_clean":
        await query.edit_message_text("❌ تم إلغاء عملية الحذف.")
        
        context.user_data.pop('msg_clean_target_user_id', None)

async def handle_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج تعديلات الرسائل - يطبق التعديل على المستخدمين المحددين"""
    user_id = update.effective_user.id
    if not is_admin(user_id, context):
        return
    
    edited_msg = update.edited_message
    if not edited_msg:
        return
    
    message_id = edited_msg.message_id
    chat_id = edited_msg.chat_id
    new_text = edited_msg.text or edited_msg.caption
    
    if not new_text:
        return
    
    try:
        _, _, target_user_id = get_selected_message(DATABASE_FILE, user_id)
        
        copies = get_message_copies(DATABASE_FILE, message_id, chat_id)
        
        edited_count = 0
        failed_count = 0
        
        for copy_user_id, copy_chat_id, copy_message_id in copies:
            if target_user_id and copy_user_id != target_user_id:
                continue
            try:
                if edited_msg.text:
                    await context.bot.edit_message_text(
                        text=new_text,
                        chat_id=copy_chat_id,
                        message_id=copy_message_id
                    )
                elif edited_msg.caption:
                    await context.bot.edit_message_caption(
                        caption=new_text,
                        chat_id=copy_chat_id,
                        message_id=copy_message_id
                    )
                edited_count += 1
            except Exception as e:
                logger.error(f"Failed to edit message {copy_message_id} for user {copy_user_id}: {e}")
                failed_count += 1
        
        if edited_count > 0:
            logger.info(f"✅ تم تعديل الرسالة لدى {edited_count} مستخدم")
        
    except Exception as e:
        logger.error(f"Error in handle_edited_message: {e}")

async def check_and_clear_msg_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التحقق من إلغاء msg_options عند إدخال أي أمر لا يبدأ بـ msg"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id, context):
        return
    
    text = update.message.text if update.message else ""
    
    if text.startswith('/msg'):
        return
    
    message_id, _, _ = get_selected_message(DATABASE_FILE, user_id)
    
    if message_id:
        clear_selected_message(DATABASE_FILE, user_id)
        logger.info(f"تم إلغاء تحديد الرسالة للآدمن {user_id} تلقائياً")

# ============================================
# قسم 11: دالة تسجيل المعالجات للاستخدام من bot.py
# ============================================

def get_admin_handlers():
    """إرجاع قائمة بجميع المعالجات الخاصة بالآدمن"""
    return {
        'admin_login': admin_login,
        'handle_admin_password': handle_admin_password,
        'change_admin_password': change_admin_password,
        'handle_password_change': handle_password_change,
        'handle_cancel_password_change': handle_cancel_password_change,
        'handle_admin_menu_actions': handle_admin_menu_actions,
        'show_admin_referrals': show_admin_referrals,
        'handle_admin_orders_menu': handle_admin_orders_menu,
        'handle_admin_money_menu': handle_admin_money_menu,
        'handle_admin_referrals_menu': handle_admin_referrals_menu,
        'handle_admin_settings_menu': handle_admin_settings_menu,
        'handle_admin_user_lookup': handle_admin_user_lookup,
        'return_to_user_mode': return_to_user_mode,
        'return_to_admin_main': return_to_admin_main,
        'show_pending_orders_admin': show_pending_orders_admin,
        'delete_processed_orders': delete_processed_orders,
        'delete_all_orders': delete_all_orders,
        'admin_order_inquiry': admin_order_inquiry,
        'admin_logout_confirmation': admin_logout_confirmation,
        'handle_logout_confirmation': handle_logout_confirmation,
        'handle_back_to_admin': handle_back_to_admin,
        'broadcast_referral_update': broadcast_referral_update,
        'broadcast_price_update': broadcast_price_update,
        'show_broadcast_menu': show_broadcast_menu,
        'handle_broadcast_selection': handle_broadcast_selection,
        'handle_cancel_broadcast': handle_cancel_broadcast,
        'notify_admin_ban': notify_admin_ban,
        'notify_admin_unban': notify_admin_unban,
        'notify_user_unban': notify_user_unban,
        'process_pending_unban_notifications': process_pending_unban_notifications,
        'restore_admin_keyboard': restore_admin_keyboard,
        'create_main_user_keyboard': create_main_user_keyboard,
        'get_admin_language': get_admin_language,
        'set_admin_language': set_admin_language,
        'get_referral_amount': get_referral_amount,
        'get_referral_percentage': get_referral_percentage,
        'clean_user_data_preserve_admin': clean_user_data_preserve_admin,
        'set_selected_message': set_selected_message,
        'get_selected_message': get_selected_message,
        'clear_selected_message': clear_selected_message,
        'track_bot_message': track_bot_message,
        'get_message_copies': get_message_copies,
        'is_admin': is_admin,
        'handle_msg_options': handle_msg_options,
        'handle_msg_delete': handle_msg_delete,
        'handle_msg_pin': handle_msg_pin,
        'handle_msg_unpin': handle_msg_unpin,
        'handle_msg_edit': handle_msg_edit,
        'handle_new_text_for_edit': handle_new_text_for_edit,
        'handle_cancel_edit': handle_cancel_edit,
        'handle_msg_clean': handle_msg_clean,
        'handle_msg_clean_confirmation': handle_msg_clean_confirmation,
        'handle_edited_message': handle_edited_message,
        'check_and_clear_msg_options': check_and_clear_msg_options,
    }

# ConversationHandler لتعديل الرسائل
msg_edit_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("msg_edit", handle_msg_edit)],
    states={
        WAITING_NEW_TEXT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_text_for_edit)
        ],
    },
    fallbacks=[
        CommandHandler("cancel", handle_cancel_edit),
        MessageHandler(filters.Regex("^(إلغاء|الغاء|cancel)$"), handle_cancel_edit)
    ],
    per_message=False,
    per_chat=True,
    per_user=True,
    allow_reentry=True
)
