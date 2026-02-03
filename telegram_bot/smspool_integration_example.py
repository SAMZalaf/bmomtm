#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مثال على كيفية التكامل مع smspool_service.py في البوت الرئيسي

هذا الملف يوضح كيفية إضافة handlers لـ SMSPool في bot.py أو bot_admin.py
"""

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    InlineQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters
)

# استيراد دوال SMSPool
from smspool_service import (
    # دوال العملاء
    smspool_main_menu,
    handle_smspool_callback,
    handle_smspool_inline_query,
    
    # دوال الآدمن
    smspool_admin_menu,
    handle_smspool_admin_callback,
    handle_admin_api_key_input,
    handle_admin_margin_input,
    
    # قاعدة البيانات
    SMSPoolDB
)

# States للـ ConversationHandler
SMSPOOL_SET_KEY = 100
SMSPOOL_SET_MARGIN = 101


def setup_smspool_customer_handlers(application: Application):
    """
    إضافة handlers للعملاء
    يجب استدعاء هذه الدالة في bot.py
    """
    # Callback handler لجميع callbacks التي تبدأ بـ sp_
    application.add_handler(
        CallbackQueryHandler(
            handle_smspool_callback,
            pattern=r'^sp_'
        )
    )
    
    # Inline query handler للبحث عن الدول والخدمات
    application.add_handler(
        InlineQueryHandler(
            handle_smspool_inline_query
        )
    )
    
    print("✅ تم تسجيل handlers العملاء لـ SMSPool")


def setup_smspool_admin_handlers(application: Application):
    """
    إضافة handlers للآدمن - الطريقة 1: باستخدام ConversationHandler (مُوصى بها)
    يجب استدعاء هذه الدالة في bot_admin.py أو bot.py
    """
    smspool_admin_conv = ConversationHandler(
        entry_points=[
            # نقطة الدخول الأساسية
            CallbackQueryHandler(
                handle_smspool_admin_callback,
                pattern=r'^sp_admin_'
            )
        ],
        states={
            # حالة إدخال مفتاح API
            SMSPOOL_SET_KEY: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_admin_api_key_input
                )
            ],
            # حالة إدخال نسبة الربح
            SMSPOOL_SET_MARGIN: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_admin_margin_input
                )
            ],
        },
        fallbacks=[
            # العودة إلى القائمة الرئيسية
            CallbackQueryHandler(
                handle_smspool_admin_callback,
                pattern=r'^sp_admin_menu$'
            )
        ],
        allow_reentry=True,
        conversation_timeout=180,  # 3 دقائق
        name='smspool_admin_conversation'
    )
    
    application.add_handler(smspool_admin_conv)
    print("✅ تم تسجيل handlers الآدمن لـ SMSPool (ConversationHandler)")


def setup_smspool_admin_handlers_alternative(application: Application):
    """
    إضافة handlers للآدمن - الطريقة 2: بدون ConversationHandler
    استخدم هذه الطريقة إذا كان البوت لا يستخدم ConversationHandler
    """
    # Callback handler للآدمن
    application.add_handler(
        CallbackQueryHandler(
            handle_smspool_admin_callback,
            pattern=r'^sp_admin_'
        )
    )
    
    # Message handler لإدخال البيانات
    # ملاحظة: يجب إضافة منطق للتحقق من context.user_data
    # في دالة منفصلة تتحقق من الحالة الحالية
    
    print("✅ تم تسجيل handlers الآدمن لـ SMSPool (بدون ConversationHandler)")


def add_smspool_button_to_main_menu(keyboard: list, language: str = 'ar'):
    """
    إضافة زر SMSPool إلى القائمة الرئيسية للعملاء
    
    Args:
        keyboard: القائمة الحالية
        language: اللغة
    
    Returns:
        keyboard مع الزر الجديد
    """
    from telegram import InlineKeyboardButton
    
    button_text = "📱 سيرڤر US only (1) | Server 2 🆕" if language == 'ar' else "📱 SMS Numbers"
    
    keyboard.append([
        InlineKeyboardButton(
            button_text,
            callback_data="sp_main"
        )
    ])
    
    return keyboard


def add_smspool_button_to_admin_menu(keyboard: list, language: str = 'ar'):
    """
    إضافة زر إدارة SMSPool إلى قائمة الآدمن
    
    Args:
        keyboard: القائمة الحالية
        language: اللغة
    
    Returns:
        keyboard مع الزر الجديد
    """
    from telegram import InlineKeyboardButton
    
    button_text = "📱 إدارة SMSPool" if language == 'ar' else "📱 Manage SMSPool"
    
    keyboard.append([
        InlineKeyboardButton(
            button_text,
            callback_data="sp_admin_menu"
        )
    ])
    
    return keyboard


def check_smspool_database():
    """
    التحقق من إعداد قاعدة البيانات لـ SMSPool
    """
    try:
        db = SMSPoolDB()
        
        # التحقق من الإعدادات
        api_key = db.get_api_key()
        enabled = db.is_enabled()
        margin = db.get_margin_percent()
        
        print("📊 حالة SMSPool:")
        print(f"   🔑 API Key: {'✅ مُعيّن' if api_key else '❌ غير مُعيّن'}")
        print(f"   📊 الخدمة: {'✅ مفعّلة' if enabled else '❌ معطّلة'}")
        print(f"   💹 نسبة الربح: {margin}%")
        
        return True
    except Exception as e:
        print(f"❌ خطأ في قاعدة البيانات: {e}")
        return False


def test_smspool_api():
    """
    اختبار الاتصال بـ SMSPool API
    """
    try:
        from smspool_service import SMSPoolAPI
        
        db = SMSPoolDB()
        api_key = db.get_api_key()
        
        if not api_key:
            print("⚠️ مفتاح API غير مُعيّن")
            return False
        
        api = SMSPoolAPI(api_key)
        is_ok, status_msg, balance = api.test_connection()
        
        if is_ok:
            print(f"✅ الاتصال ناجح!")
            print(f"💰 الرصيد: ${balance}")
            return True
        else:
            print(f"❌ فشل الاتصال: {status_msg}")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في الاختبار: {e}")
        return False


# مثال على التكامل الكامل
def main_integration_example():
    """
    مثال كامل على كيفية التكامل في الملف الرئيسي للبوت
    """
    print("=" * 50)
    print("مثال التكامل مع SMSPool Service")
    print("=" * 50)
    
    # 1. التحقق من قاعدة البيانات
    print("\n1️⃣ التحقق من قاعدة البيانات:")
    check_smspool_database()
    
    # 2. اختبار API (إن كان المفتاح موجوداً)
    print("\n2️⃣ اختبار API:")
    test_smspool_api()
    
    # 3. مثال على إضافة handlers
    print("\n3️⃣ مثال على إضافة handlers:")
    print("""
    في bot.py أو main.py:
    
    from smspool_integration_example import (
        setup_smspool_customer_handlers,
        setup_smspool_admin_handlers,
        add_smspool_button_to_main_menu
    )
    
    # بعد إنشاء application
    application = Application.builder().token(TOKEN).build()
    
    # إضافة handlers للعملاء
    setup_smspool_customer_handlers(application)
    
    # إضافة handlers للآدمن
    setup_smspool_admin_handlers(application)
    
    # إضافة زر في القائمة الرئيسية
    keyboard = []
    add_smspool_button_to_main_menu(keyboard, language='ar')
    """)
    
    print("\n✅ جاهز للاستخدام!")
    print("=" * 50)


if __name__ == "__main__":
    # تشغيل المثال
    main_integration_example()
    
    print("\n" + "=" * 50)
    print("ملاحظات مهمة:")
    print("=" * 50)
    print("""
    1. تأكد من إضافة smspool_service.py في نفس المجلد
    2. تأكد من تثبيت جميع المكتبات المطلوبة
    3. قم بتعيين مفتاح API من قائمة الآدمن
    4. تأكد من تفعيل Inline Mode في BotFather
    5. تأكد من تشغيل job_queue للمراقبة التلقائية
    
    للمزيد من المعلومات، راجع SMSPOOL_FIXES_README.md
    """)
