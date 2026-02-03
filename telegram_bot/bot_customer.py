# ============================================
# bot_customer.py - دوال الزبائن والمستخدمين
# تم استخراجه من bot.py - المرحلة الرابعة
# ============================================

import logging
import sqlite3
from datetime import datetime
from typing import Optional

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler
)

from config import (
    MESSAGES, DATABASE_FILE,
    STATIC_WEEKLY_LOCATIONS, STATIC_DAILY_LOCATIONS
)

from bot_utils import (
    db, generate_order_id,
    get_current_price, get_socks_prices
)

# استيراد الكيبوردات الموحدة
from bot_keyboards import (
    create_main_user_keyboard, create_balance_keyboard,
    create_profile_keyboard, create_back_button
)

SERVICES_MESSAGE = {
    'ar': 'هذه رسالة الخدمات الافتراضية. يمكن للإدارة تعديلها.',
    'en': 'This is the default services message. Admin can modify it.'
}

EXCHANGE_RATE_MESSAGE = {
    'ar': 'هذه رسالة سعر الصرف الافتراضية. يمكن للإدارة تعديلها.',
    'en': 'This is the default exchange rate message. Admin can modify it.'
}

logger = logging.getLogger(__name__)

ACTIVE_ADMINS = set()

nonvoip_main_menu = None
nonvoip_select_type = None
nonvoip_my_numbers = None
nonvoip_sync_numbers = None
nonvoip_history = None
nonvoip_view_number_messages = None

try:
    from non_voip_unified import (
        NonVoipAPI, NonVoipDB,
        nonvoip_main_menu as _nonvoip_main_menu,
        nonvoip_select_type as _nonvoip_select_type,
        nonvoip_my_numbers as _nonvoip_my_numbers,
        nonvoip_sync_numbers as _nonvoip_sync_numbers,
        nonvoip_history as _nonvoip_history,
        nonvoip_view_number_messages as _nonvoip_view_number_messages,
        get_user_language
    )
    nonvoip_main_menu = _nonvoip_main_menu
    nonvoip_select_type = _nonvoip_select_type
    nonvoip_my_numbers = _nonvoip_my_numbers
    nonvoip_sync_numbers = _nonvoip_sync_numbers
    nonvoip_history = _nonvoip_history
    nonvoip_view_number_messages = _nonvoip_view_number_messages
    NONVOIP_AVAILABLE = True
except ImportError:
    NONVOIP_AVAILABLE = False
    def get_user_language(user_id: int) -> str:
        try:
            result = db.execute_query("SELECT language FROM users WHERE user_id = ?", (user_id,))
            return result[0][0] if result else 'ar'
        except:
            return 'ar'


def get_referral_amount(order_amount: float = 0) -> float:
    """حساب قيمة الإحالة بناءً على نسبة مئوية من قيمة الطلب"""
    try:
        result = db.execute_query("SELECT value FROM settings WHERE key = 'referral_percentage'")
        percentage = float(result[0][0]) if result else 10.0
        return round((order_amount * percentage / 100), 2)
    except:
        return round((order_amount * 10.0 / 100), 2)


def get_referral_percentage() -> float:
    """الحصول على نسبة الإحالة المئوية من الإعدادات"""
    try:
        result = db.execute_query("SELECT value FROM settings WHERE key = 'referral_percentage'")
        return float(result[0][0]) if result else 10.0
    except:
        return 10.0


# تم نقل create_main_user_keyboard و create_balance_keyboard إلى bot_keyboards.py

async def handle_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة قسم الإحالات"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    try:
        bot_info = await context.bot.get_me()
        bot_username = bot_info.username
    except:
        bot_username = "your_bot"
    
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    
    user = db.get_user(user_id)
    referral_balance = user[5] if user else 0.0
    
    query = "SELECT COUNT(*) FROM referrals WHERE referrer_id = ?"
    referral_count = db.execute_query(query, (user_id,))[0][0]
    
    if language == 'ar':
        message = f"""👥 نظام الإحالات

🔗 رابط الإحالة الخاص بك:
<code>{referral_link}</code>

💰 رصيدك: <code>{referral_balance:.2f}$</code>
👥 عدد إحالاتك: <code>{referral_count}</code>

━━━━━━━━━━━━━━━
شارك رابطك واحصل على {get_referral_percentage()}% من كل عملية شراء!
💡 يتم إضافة المكافأة عند كل عملية شراء ناجحة يقوم بها المُحال
الحد الأدنى للسحب: <code>1.0$</code>"""
    else:
        message = f"""👥 Referral System

🔗 Your referral link:
<code>{referral_link}</code>

💰 Your balance: <code>{referral_balance:.2f}$</code>
👥 Your referrals: <code>{referral_count}</code>

━━━━━━━━━━━━━━━
Share your link and earn {get_referral_percentage()}% from every purchase!
💡 Bonus is added for every successful purchase made by referred user
Minimum withdrawal: <code>1.0$</code>"""
    
    keyboard = [
        [InlineKeyboardButton("💸 سحب الرصيد" if language == 'ar' else "💸 Withdraw Balance", callback_data="withdraw_balance")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')


async def handle_profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة قائمة الملف الشخصي"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    profile_keyboard = create_profile_keyboard(language)
    await update.message.reply_text(
        MESSAGES[language]['profile_menu_title'],
        reply_markup=profile_keyboard
    )


async def handle_profile_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة عرض معلومات الملف الشخصي"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    user = db.get_user(user_id)
    
    if not user:
        if language == 'ar':
            await update.message.reply_text("❌ خطأ: لم يتم العثور على المستخدم")
        else:
            await update.message.reply_text("❌ Error: User not found")
        return
    
    user_name = user[2] if user[2] else ("غير متوفر" if language == 'ar' else "N/A")
    username = f"@{user[1]}" if user[1] else ("غير متوفر" if language == 'ar' else "N/A")
    user_id_str = str(user_id)
    balance = float(user[6]) if user[6] else 0.0
    is_banned = bool(user[7]) if len(user) > 7 else False
    
    if language == 'ar':
        ban_status = "🔴 محظور" if is_banned else "🟢 نشط"
        message = f"""👤 <b>معلومات الحساب</b>
━━━━━━━━━━━━━━━━━━━━
        
📝 <b>الاسم:</b> {user_name}
🏷️ <b>اسم المستخدم:</b> {username}
🆔 <b>المعرف:</b> <code>{user_id_str}</code>
💰 <b>الرصيد:</b> {balance:.2f} كريديت
📊 <b>حالة الحساب:</b> {ban_status}

━━━━━━━━━━━━━━━━━━━━"""
    else:
        ban_status = "🔴 Banned" if is_banned else "🟢 Active"
        message = f"""👤 <b>Account Information</b>
━━━━━━━━━━━━━━━━━━━━

📝 <b>Name:</b> {user_name}
🏷️ <b>Username:</b> {username}
🆔 <b>ID:</b> <code>{user_id_str}</code>
💰 <b>Balance:</b> {balance:.2f} credits
📊 <b>Account Status:</b> {ban_status}

━━━━━━━━━━━━━━━━━━━━"""
    
    await update.message.reply_text(message, parse_mode='HTML')


async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة زر الدعم - نفس وظيفة /help"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    if language == 'ar':
        message = (
            "ℹ️ <b>للتواصل مع الدعم:</b>\n\n"
            "<b>دعم البروكسيات Static:</b>\n"
            "@Static_support\n\n"
            "<b>دعم البروكسيات Socks:</b>\n"
            "@Socks_support\n\n"
            "<b>دعم الأرقام Non-Voip:</b>\n"
            "@Numbers_nv_support_bot"
        )
        keyboard = [[InlineKeyboardButton("❓ الأسئلة الشائعة", callback_data="faq_menu")]]
    else:
        message = (
            "ℹ️ <b>Contact Support:</b>\n\n"
            "<b>Static Proxy Support:</b>\n"
            "@Static_support\n\n"
            "<b>Socks Proxy Support:</b>\n"
            "@Socks_support\n\n"
            "<b>Non-Voip Numbers Support:</b>\n"
            "@Numbers_nv_support_bot"
        )
        keyboard = [[InlineKeyboardButton("❓ FAQ", callback_data="faq_menu")]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)


async def handle_back_to_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """العودة لقائمة الملف الشخصي من قائمة الرصيد"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    profile_keyboard = create_profile_keyboard(language)
    await update.message.reply_text(
        MESSAGES[language]['profile_menu_title'],
        reply_markup=profile_keyboard
    )


async def handle_balance_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة قائمة الرصيد الرئيسية"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    balance_keyboard = create_balance_keyboard(language)
    await update.message.reply_text(
        MESSAGES[language]['balance_menu_title'],
        reply_markup=balance_keyboard
    )


async def handle_my_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة عرض الرصيد الحالي"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    balance_data = db.get_user_balance(user_id)
    
    message = MESSAGES[language]['current_balance'].format(
        charged_balance=balance_data['charged_balance'],
        referral_balance=balance_data['referral_balance'],
        total_balance=balance_data['total_balance']
    )
    
    await update.message.reply_text(message, parse_mode='HTML')


async def handle_recharge_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة طلب شحن الرصيد"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    credit_price = db.get_credit_price()
    
    message = MESSAGES[language]['recharge_request'].format(credit_price=credit_price)
    
    if language == 'ar':
        keyboard = [[InlineKeyboardButton("↩️ رجوع للقائمة الرئيسية", callback_data="back_to_main_from_recharge")]]
    else:
        keyboard = [[InlineKeyboardButton("↩️ Back to Main Menu", callback_data="back_to_main_from_recharge")]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, parse_mode='HTML')
    await update.message.reply_text(MESSAGES[language]['enter_recharge_amount'], reply_markup=reply_markup)
    
    context.user_data['waiting_for_recharge_amount'] = True


async def handle_balance_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الإحالات من داخل قائمة الرصيد"""
    await handle_referrals(update, context)


async def handle_back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """العودة للقائمة الرئيسية من قائمة الرصيد"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    main_keyboard = create_main_user_keyboard(language)
    await update.message.reply_text(
        MESSAGES[language]['welcome'],
        reply_markup=main_keyboard
    )


async def handle_recharge_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة إدخال مبلغ الشحن"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    try:
        amount = float(update.message.text)
        if amount <= 0:
            await update.message.reply_text(MESSAGES[language]['invalid_recharge_amount'])
            return
        
        credit_price = db.get_credit_price()
        expected_credits = amount / credit_price
        
        order_id = generate_order_id()
        context.user_data['recharge_order_id'] = order_id
        context.user_data['recharge_amount'] = amount
        context.user_data['expected_credits'] = expected_credits
        context.user_data['waiting_for_recharge_amount'] = False
        context.user_data['waiting_for_recharge_payment_method'] = True
        
        if language == 'ar':
            keyboard = [
                [InlineKeyboardButton("💳 شام كاش", callback_data="recharge_payment_shamcash")],
                [InlineKeyboardButton("💳 سيرياتيل كاش", callback_data="recharge_payment_syriatel")],
                [InlineKeyboardButton("🪙 Coinex", callback_data="recharge_payment_coinex")],
                [InlineKeyboardButton("🪙 Binance", callback_data="recharge_payment_binance")],
                [InlineKeyboardButton("🪙 Payeer", callback_data="recharge_payment_payeer")],
                [InlineKeyboardButton("🔗 BEP20", callback_data="recharge_payment_bep20")],
                [InlineKeyboardButton("🔗 Litecoin", callback_data="recharge_payment_litecoin")],
                [InlineKeyboardButton("↩️ رجوع", callback_data="back_to_amount")]
            ]
            message = f"💰 مبلغ الشحن: {amount}$\n💎 النقاط المتوقعة: {expected_credits:.1f}\n\n💳 اختر طريقة الدفع المفضلة:"
        else:
            keyboard = [
                [InlineKeyboardButton("💳 Sham Cash", callback_data="recharge_payment_shamcash")],
                [InlineKeyboardButton("💳 Syriatel Cash", callback_data="recharge_payment_syriatel")],
                [InlineKeyboardButton("🪙 Coinex", callback_data="recharge_payment_coinex")],
                [InlineKeyboardButton("🪙 Binance", callback_data="recharge_payment_binance")],
                [InlineKeyboardButton("🪙 Payeer", callback_data="recharge_payment_payeer")],
                [InlineKeyboardButton("🔗 BEP20", callback_data="recharge_payment_bep20")],
                [InlineKeyboardButton("🔗 Litecoin", callback_data="recharge_payment_litecoin")],
                [InlineKeyboardButton("↩️ Back", callback_data="back_to_amount")]
            ]
            message = f"💰 Recharge Amount: {amount}$\n💎 Expected Points: {expected_credits:.1f}\n\n💳 Choose your preferred payment method:"
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup)
        
    except ValueError:
        await update.message.reply_text(MESSAGES[language]['invalid_recharge_amount'])


async def handle_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الإعدادات"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    keyboard = [
        [InlineKeyboardButton("🌐 العربية", callback_data="lang_ar"),
         InlineKeyboardButton("🌐 English", callback_data="lang_en")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "اختر اللغة / Choose Language:",
        reply_markup=reply_markup
    )


async def handle_language_change(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة تغيير اللغة"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    is_admin = context.user_data.get('is_admin', False) or user_id in ACTIVE_ADMINS
    
    if query.data in ["lang_ar", "admin_lang_ar"]:
        new_language = "ar"
        if is_admin:
            message = "تم تغيير اللغة إلى العربية ✅"
        else:
            message = """تم تغيير اللغة إلى العربية ✅
يرجى استخدام الأمر /start لإعادة تحميل القوائم

Language changed to Arabic ✅  
Please use /start command to reload menus"""
    else:
        new_language = "en"
        if is_admin:
            message = "Language changed to English ✅"
        else:
            message = """Language changed to English ✅
Please use /start command to reload menus

تم تغيير اللغة إلى الإنجليزية ✅
يرجى استخدام الأمر /start لإعادة تحميل القوائم"""
    
    db.update_user_language(user_id, new_language)
    db.log_action(user_id, "language_change", new_language)
    
    if is_admin:
        try:
            await query.delete_message()
        except:
            await query.edit_message_text(message)
        
        try:
            import bot as bot_module
            if hasattr(bot_module, 'restore_admin_keyboard'):
                await bot_module.restore_admin_keyboard(context, user_id, 
                                         "تم تحديث اللغة ✅" if new_language == 'ar' else "Language updated ✅",
                                         language=new_language)
            else:
                await context.bot.send_message(user_id, 
                    "تم تحديث اللغة ✅" if new_language == 'ar' else "Language updated ✅")
        except Exception as e:
            logger.warning(f"Could not restore admin keyboard: {e}")
            await context.bot.send_message(user_id, 
                "تم تحديث اللغة ✅" if new_language == 'ar' else "Language updated ✅")
    else:
        await query.edit_message_text(message)
        
        main_keyboard = create_main_user_keyboard(new_language)
        await context.bot.send_message(
            user_id,
            MESSAGES[new_language]['welcome'],
            reply_markup=main_keyboard
        )


async def show_services_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض رسالة لمحة عن الخدمات مباشرة - محدثة مع زر FAQ"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    try:
        result = db.execute_query("SELECT value FROM settings WHERE key = ?", (f'services_message_{language}',))
        services_msg = result[0][0] if result else SERVICES_MESSAGE[language]
    except:
        services_msg = SERVICES_MESSAGE[language]
    
    if language == 'ar':
        keyboard = [[InlineKeyboardButton("❓ الأسئلة الشائعة", callback_data="faq_menu")]]
    else:
        keyboard = [[InlineKeyboardButton("❓ FAQ", callback_data="faq_menu")]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(services_msg, parse_mode='HTML', reply_markup=reply_markup)


async def show_exchange_rate_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض رسالة سعر الصرف مباشرة - من الكيبورد الرئيسي"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    try:
        result = db.execute_query("SELECT value FROM settings WHERE key = ?", (f'exchange_rate_message_{language}',))
        exchange_msg = result[0][0] if result else EXCHANGE_RATE_MESSAGE[language]
    except:
        exchange_msg = EXCHANGE_RATE_MESSAGE[language]
    
    await update.message.reply_text(exchange_msg, parse_mode='HTML')


async def handle_free_proxy_trial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة طلب تجربة البروكسي المجاني"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    proxies = db.execute_query("SELECT id, message FROM free_proxies ORDER BY id")
    
    if not proxies:
        if language == 'ar':
            message = "😔 عذراً، لا توجد بروكسيات تجريبية متاحة حالياً\n\nيرجى المحاولة لاحقاً أو التواصل مع الأدمن"
        else:
            message = "😔 Sorry, no trial proxies are currently available\n\nPlease try again later or contact admin"
        
        await query.edit_message_text(message)
        return
    
    keyboard = []
    for proxy_id, message in proxies:
        if language == 'ar':
            button_text = f"بروكسي #{proxy_id}"
        else:
            button_text = f"Proxy #{proxy_id}"
        
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"use_free_proxy_{proxy_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if language == 'ar':
        message_text = "🎁 البروكسيات التجريبية المتاحة:\n\nاختر البروكسي الذي تريد تجربته:"
    else:
        message_text = "🎁 Available trial proxies:\n\nChoose the proxy you want to try:"
    
    await query.edit_message_text(message_text, reply_markup=reply_markup)


async def handle_use_free_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """إرسال البروكسي المجاني للمستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    proxy_id = int(query.data.split("_")[3])
    
    result = db.execute_query("SELECT message FROM free_proxies WHERE id = ?", (proxy_id,))
    
    if not result:
        if language == 'ar':
            error_msg = "❌ البروكسي غير متاح حالياً"
        else:
            error_msg = "❌ Proxy is not available currently"
        
        await query.edit_message_text(error_msg)
        return
    
    proxy_message = result[0][0]
    
    if language == 'ar':
        final_message = f"🎁 بروكسي مجاني #{proxy_id}\n\n{proxy_message}\n\n⏰ يرجى ملاحظة أن البروكسيات المجانية قد تكون أبطأ من المدفوعة"
    else:
        final_message = f"🎁 Free Proxy #{proxy_id}\n\n{proxy_message}\n\n⏰ Please note that free proxies may be slower than paid ones"
    
    await query.edit_message_text(final_message)


async def handle_buy_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج زر شراء الأرقام للمستخدمين"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    # التحقق من توفر SMSPool أولاً
    try:
        from smspool_service import handle_buy_sms, smspool_db as sp_db
        if sp_db.is_enabled():
            await handle_buy_sms(update, context)
            return
    except ImportError:
        pass

    if not NONVOIP_AVAILABLE or nonvoip_main_menu is None:
        message = "❌ خدمة الأرقام غير متاحة حالياً.\nيرجى التواصل مع الآدمن." if language == 'ar' else "❌ Numbers service is not available.\nPlease contact admin."
        await update.message.reply_text(message)
        return
    
    nonvoip_enabled = db.get_service_status('nonvoip', 'basic')
    if not nonvoip_enabled:
        message = "❌ خدمة الأرقام معطلة حالياً من قبل الإدارة.\nيرجى المحاولة لاحقاً." if language == 'ar' else "❌ Numbers service is currently disabled by administration.\nPlease try again later."
        await update.message.reply_text(message)
        return
    
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        await nonvoip_main_menu(update, context, conn)
        conn.close()
    except Exception as e:
        logger.error(f"خطأ في شراء الأرقام: {e}")
        await update.message.reply_text(f"❌ حدث خطأ: {str(e)}")


async def handle_nonvoip_user_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة callbacks شراء الأرقام للمستخدمين"""
    if not NONVOIP_AVAILABLE:
        return
        
    query = update.callback_query
    
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        
        if query.data == "nv_request_new" and nonvoip_select_type:
            await nonvoip_select_type(update, context, conn)
        elif query.data == "nv_country_usa" and nonvoip_select_type:
            await nonvoip_select_type(update, context, conn)
        elif query.data == "nv_my_numbers" and nonvoip_my_numbers:
            await nonvoip_my_numbers(update, context, conn)
        elif query.data == "nv_sync_numbers" and nonvoip_sync_numbers:
            await nonvoip_sync_numbers(update, context, conn)
        elif query.data == "nv_history" and nonvoip_history:
            await nonvoip_history(update, context, conn)
        elif query.data.startswith("nv_view_messages_") and nonvoip_view_number_messages:
            order_id = query.data.replace('nv_view_messages_', '')
            logger.info(f"📱 معالجة عرض رسائل الرقم - order_id: {order_id} من المستخدم {update.effective_user.id}")
            await nonvoip_view_number_messages(update, context, conn)
        elif query.data.startswith("nv_type_") and nonvoip_select_type:
            await nonvoip_select_type(update, context, conn)
        elif query.data.startswith("nv_state_") and nonvoip_select_type:
            await nonvoip_select_type(update, context, conn)
        elif query.data == "nv_all_states" and nonvoip_select_type:
            await nonvoip_select_type(update, context, conn)
        
        conn.close()
    except Exception as e:
        logger.error(f"خطأ في معالجة callback المستخدم: {e}")
        await query.answer("❌ حدث خطأ")
