#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
non_voip_unified.py - Compatibility Layer (Wrapper for SMSPool)

هذا الملف يعمل كـ compatibility layer بين الكود القديم (NonVoip) والكود الجديد (SMSPool)
جميع الدوال هنا تقوم بتوجيه الطلبات إلى SMSPool مع الحفاظ على نفس الواجهة

⚠️ هذا الملف للتوافق فقط - الوظائف الفعلية موجودة في smspool_service.py
"""

import logging
from typing import Optional, List, Dict, Any

# استيراد جميع الوظائف من SMSPool
from smspool_service import (
    SMSPoolAPI,
    SMSPoolDB,
    smspool_db,
    get_db_connection,
    get_syria_time,
    get_error_code_from_message,
    get_user_language,
    get_user_balance,
    update_user_balance,
    # Async handlers
    smspool_main_menu,
    handle_smspool_callback,
    smspool_admin_menu,
    handle_smspool_admin_callback,
    # Helper functions
    get_country_flag,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# COMPATIBILITY LAYER - توجيه الدوال القديمة إلى SMSPool
# ═══════════════════════════════════════════════════════════════════════════

# Alias للـ API classes
NonVoipAPI = SMSPoolAPI
NonVoipDB = SMSPoolDB

# Alias للـ database instance
nonvoip_db = smspool_db

# دوال مساعدة متوافقة
def log_nonvoip_operation(*args, **kwargs):
    """Wrapper for smspool_db.log_operation"""
    return smspool_db.log_operation(*args, **kwargs)


def log_refund_operation(order_id: int, user_id: int, operation_type: str, 
                         refund_amount: float, reason: str, status: str = 'success', details: str = None):
    """Compatibility wrapper for refund logging"""
    return smspool_db.log_operation(
        user_id=user_id,
        operation_type=operation_type,
        operation_category='refund',
        order_id=str(order_id),
        amount=refund_amount,
        status=status,
        details=f"{reason} | {details if details else ''}"
    )


def calculate_renewal_price(sale_price, order_type: str = 'long_term') -> float:
    """
    للتوافق مع NonVoip - في SMSPool نظام التمديد مختلف
    هذه الدالة تُرجع نفس السعر الأصلي
    """
    try:
        return float(sale_price)
    except (ValueError, TypeError):
        return 0.0


def format_expiration_time(seconds: int, lang: str = 'ar') -> str:
    """تحويل الثواني إلى نص مفهوم"""
    if seconds <= 0:
        return 'منتهي' if lang == 'ar' else 'Expired'
    
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    
    if days > 0:
        return f"{days} يوم" if lang == 'ar' else f"{days} day{'s' if days > 1 else ''}"
    elif hours > 0:
        return f"{hours} ساعة" if lang == 'ar' else f"{hours} hour{'s' if hours > 1 else ''}"
    else:
        return f"{minutes} min"


def should_show_cancel_button(order_type: str) -> bool:
    """جميع أرقام SMSPool قابلة للإلغاء قبل استقبال SMS"""
    return True


def build_cancel_refund_markup(order_id: int, lang: str = 'ar'):
    """إنشاء لوحة مفاتيح مع زر الإلغاء"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    cancel_keyboard = [[InlineKeyboardButton(
        "❌ إلغاء وإعادة الرصيد" if lang == "ar" else "❌ Cancel & Refund",
        callback_data=f"sp_cancel_{order_id}"
    )]]
    return InlineKeyboardMarkup(cancel_keyboard)


# Async handlers (إعادة تسمية لل compatibility)
async def show_nonvoip_menu(update, context):
    """Wrapper for smspool_main_menu"""
    return await smspool_main_menu(update, context)


async def handle_nonvoip_callback(update, context):
    """Wrapper for handle_smspool_callback"""
    return await handle_smspool_callback(update, context)


async def nonvoip_admin_menu(update, context):
    """Wrapper for smspool_admin_menu"""
    return await smspool_admin_menu(update, context)


async def handle_nonvoip_admin_callback(update, context):
    """Wrapper for handle_smspool_admin_callback"""
    return await handle_smspool_admin_callback(update, context)


async def handle_nonvoip_inline_query(update, context):
    """
    معالج Inline Query للأرقام
    
    في NonVoip كان يعرض قائمة المنتجات
    في SMSPool نعرض الخدمات والدول المتاحة
    """
    from telegram import InlineQueryResultArticle, InputTextMessageContent
    
    query = update.inline_query.query.lower()
    user_id = update.effective_user.id
    
    results = []
    
    # عرض قائمة الخدمات المشهورة
    popular_services = [
        {'name': 'Google', 'icon': '📧'},
        {'name': 'Facebook', 'icon': '📘'},
        {'name': 'WhatsApp', 'icon': '💬'},
        {'name': 'Telegram', 'icon': '✈️'},
        {'name': 'Instagram', 'icon': '📷'},
        {'name': 'Twitter', 'icon': '🐦'},
        {'name': 'TikTok', 'icon': '🎵'},
        {'name': 'Amazon', 'icon': '🛒'},
    ]
    
    for idx, service in enumerate(popular_services):
        if query in service['name'].lower() or not query:
            results.append(
                InlineQueryResultArticle(
                    id=str(idx),
                    title=f"{service['icon']} {service['name']}",
                    description="اضغط لشراء رقم للتحقق",
                    input_message_content=InputTextMessageContent(
                        f"🛒 شراء رقم {service['name']}\n\n"
                        f"اختر الدولة من القائمة التالية..."
                    )
                )
            )
    
    await update.inline_query.answer(results[:10], cache_time=60)


# Dummy functions للدوال المحذوفة (التفعيل، التجديد، إلخ)
def check_expired_activations():
    """
    دالة فارغة للتوافق - SMSPool لا يحتاج تفعيل
    """
    logger.info("check_expired_activations - skipped (not needed in SMSPool)")
    return 0


def check_nonvoip_balance_and_notify():
    """
    فحص رصيد SMSPool وإرسال إشعارات للآدمن
    
    TODO: تطبيق نظام مماثل لـ NonVoip
    """
    try:
        api_key = smspool_db.get_api_key()
        if not api_key:
            return
        
        api = SMSPoolAPI(api_key)
        result = api.get_balance()
        
        if result.get('status') == 'success':
            balance = float(result.get('balance', 0))
            logger.info(f"💰 SMSPool Balance: ${balance}")
            
            # TODO: إرسال تنبيهات تدريجية للآدمن عند انخفاض الرصيد
            # مثل NonVoip: عند $50, $30, $20, $10, $5
            
        else:
            logger.warning(f"⚠️ فشل جلب رصيد SMSPool: {result.get('message')}")
            
    except Exception as e:
        logger.error(f"❌ خطأ في فحص رصيد SMSPool: {e}")


# Service icons و display names
def get_service_icon(service_name: str) -> str:
    """الحصول على أيقونة الخدمة"""
    icons = {
        'google': '📧',
        'facebook': '📘',
        'whatsapp': '💬',
        'telegram': '✈️',
        'instagram': '📷',
        'twitter': '🐦',
        'tiktok': '🎵',
        'amazon': '🛒',
        'discord': '🎮',
        'uber': '🚗',
        'netflix': '🎬',
        'spotify': '🎵',
        'paypal': '💳',
        'microsoft': '🪟',
        'yahoo': '📮',
    }
    return icons.get(service_name.lower(), '📱')


def get_display_service_name(service_name: str, lang: str = 'ar') -> str:
    """الحصول على اسم الخدمة للعرض"""
    # معظم الخدمات تستخدم نفس الاسم بالإنجليزية
    return service_name.title()


# معلومات إضافية
logger.info("✅ non_voip_unified.py loaded as SMSPool compatibility layer")
logger.info("All NonVoip calls will be redirected to SMSPool automatically")

# تصدير جميع الدوال المطلوبة
__all__ = [
    # Classes
    'NonVoipAPI',
    'NonVoipDB',
    'nonvoip_db',
    # Database functions
    'get_db_connection',
    'get_syria_time',
    # Logging
    'log_nonvoip_operation',
    'log_refund_operation',
    # Pricing
    'calculate_renewal_price',
    # UI helpers
    'format_expiration_time',
    'should_show_cancel_button',
    'build_cancel_refund_markup',
    'get_service_icon',
    'get_display_service_name',
    # Async handlers
    'show_nonvoip_menu',
    'handle_nonvoip_callback',
    'nonvoip_admin_menu',
    'handle_nonvoip_admin_callback',
    'handle_nonvoip_inline_query',
    # System checks
    'check_expired_activations',
    'check_nonvoip_balance_and_notify',
    # User functions
    'get_user_language',
    'get_user_balance',
    'update_user_balance',
]
