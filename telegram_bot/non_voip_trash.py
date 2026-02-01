#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
non_voip_trash.py - أرشيف الدوال القديمة من NonVoip

هذا الملف يحتوي على جميع الدوال التي كانت تُستخدم في non_voip_unified.py
والتي لم تعد مطلوبة بعد الانتقال إلى SMSPool.

تم نقلها هنا للحفاظ على الكود القديم كمرجع ولسهولة الرجوع إليها عند الحاجة.
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# ACTIVATION SYSTEM - لم يعد مطلوباً في SMSPool
# ══════════════════════════════════════════════════════════════════════════════

def activate_long_term_number(service: str, number: str) -> Dict[str, Any]:
    """
    تفعيل رقم طويل الأمد قبل استقبال SMS
    
    NON_VOIP ONLY - SMSPool لا يحتاج تفعيل يدوي
    
    في NonVoip، الأرقام طويلة الأمد (long_term/3days) تحتاج تفعيل يدوي
    قبل استقبال الرسائل. هذا غير موجود في SMSPool.
    """
    logger.warning("activate() - وظيفة غير مدعومة في SMSPool")
    return {"status": "error", "message": "Activation not required in SMSPool"}


def auto_activate_number_on_purchase(order_id: int, service: str, number: str) -> Dict[str, Any]:
    """
    تفعيل الرقم تلقائياً فور الشراء (NonVoip فقط)
    
    NON_VOIP ONLY
    
    في NonVoip: الأرقام الطويلة تحتاج تفعيل فورياً بعد الشراء
    في SMSPool: الأرقام تكون جاهزة فوراً بدون تفعيل
    """
    logger.warning("auto_activate - غير مطلوب في SMSPool")
    return {"status": "skipped", "message": "Auto-activation not needed in SMSPool"}


def check_expired_activations():
    """
    فحص انتهاء صلاحية التفعيلات (NonVoip فقط)
    
    NON_VOIP ONLY
    
    في NonVoip: التفعيل يستمر لمدة 10 دقائق ثم ينتهي
    في SMSPool: لا يوجد نظام تفعيل منفصل
    """
    logger.info("check_expired_activations - تم تخطيه (غير مطلوب في SMSPool)")
    return 0


def update_activation_status(order_id: int, activation_status: str, activated_until: str = None):
    """
    تحديث حالة التفعيل للرقم (NonVoip فقط)
    
    NON_VOIP ONLY
    
    حقول قاعدة البيانات:
    - activation_status: 'active' أو 'inactive'
    - activated_until: وقت انتهاء التفعيل
    - auto_activated: هل تم التفعيل تلقائياً
    """
    logger.warning("update_activation_status - غير مدعوم في SMSPool")
    pass


def get_activation_status(order_id: int) -> Dict[str, Any]:
    """
    الحصول على حالة التفعيل الحالية للرقم (NonVoip فقط)
    
    NON_VOIP ONLY
    """
    logger.warning("get_activation_status - غير مدعوم في SMSPool")
    return {'activation_status': 'not_applicable', 'activated_until': None, 'type': None}


def format_activation_time(activated_until: str, lang: str = 'ar') -> str:
    """
    حساب الوقت المتبقي للتفعيل (NonVoip فقط)
    
    NON_VOIP ONLY
    """
    return "غير مطلوب" if lang == 'ar' else "Not required"


# ══════════════════════════════════════════════════════════════════════════════
# RENEWAL SYSTEM - يُستبدل بـ extend_rental في SMSPool
# ══════════════════════════════════════════════════════════════════════════════

def renew_long_term_number(service: str, number: str) -> Dict[str, Any]:
    """
    تجديد رقم طويل الأمد (long_term أو 3days)
    
    NON_VOIP: renew() API
    SMSPOOL: extend_rental() API (للأرقام المستأجرة فقط)
    
    الفرق:
    - NonVoip: التجديد يمدد الصلاحية لنفس الرقم المشترى
    - SMSPool: التمديد فقط للأرقام المستأجرة (Rentals)، الأرقام العادية غير قابلة للتمديد
    """
    logger.warning("renew() - استخدم extend_rental() في SMSPool للأرقام المستأجرة")
    return {"status": "error", "message": "Use extend_rental() for SMSPool rentals"}


def calculate_renewal_price(sale_price, order_type: str = 'long_term') -> float:
    """
    حساب سعر التجديد حسب نوع الرقم (NonVoip فقط)
    
    NON_VOIP ONLY:
    - short_term (15 دقيقة): نصف السعر (50%)
    - long_term & 3days: نفس السعر الأصلي (100%)
    
    SMSPOOL:
    - الأرقام العادية: غير قابلة للتجديد
    - Rentals: التمديد بسعر جديد حسب عدد الأيام
    """
    logger.warning("calculate_renewal_price - غير مطلوب في SMSPool")
    return 0.0


def should_show_renewal_button(order_type: str, expires_at: str) -> bool:
    """
    تحديد ما إذا كان يجب عرض زر التجديد (NonVoip فقط)
    
    NON_VOIP ONLY
    """
    return False


# ══════════════════════════════════════════════════════════════════════════════
# REUSE SYSTEM - غير موجود في SMSPool (يُستخدم resend بدلاً منه)
# ══════════════════════════════════════════════════════════════════════════════

def reuse_short_term_number(service: str, number: str) -> Dict[str, Any]:
    """
    إعادة استخدام رقم قصير الأمد مجاناً (NonVoip فقط)
    
    NON_VOIP ONLY: reuse() API
    SMSPOOL ALTERNATIVE: resend_sms() (ليس مجانياً بالضرورة)
    
    الفرق:
    - NonVoip: إعادة الاستخدام مجاناً لنفس الخدمة
    - SMSPool: resend_sms() يعيد طلب الرسالة من نفس الموقع (قد يكون له تكلفة)
    """
    logger.warning("reuse() - استخدم resend_sms() في SMSPool كبديل")
    return {"status": "error", "message": "Use resend_sms() in SMSPool"}


# ══════════════════════════════════════════════════════════════════════════════
# SPECIFIC ORDER TYPES - تم توحيدها في SMSPool
# ══════════════════════════════════════════════════════════════════════════════

def get_order_type_display(order_type: str, lang: str = 'ar') -> str:
    """
    عرض نوع الرقم بشكل مفهوم (NonVoip فقط)
    
    NON_VOIP:
    - short_term: 15 دقيقة
    - long_term: 30 يوم
    - 3days: 3 أيام
    
    SMSPOOL:
    - temporary: 20 دقيقة - 5 أيام (حسب Pool)
    - rental: شهري (قابل للتمديد)
    """
    order_types = {
        'short_term': '15 دقيقة' if lang == 'ar' else '15 minutes',
        'long_term': '30 يوم' if lang == 'ar' else '30 days',
        '3days': '3 أيام' if lang == 'ar' else '3 days'
    }
    return order_types.get(order_type, order_type)


def should_show_activate_button(order_type: str) -> bool:
    """
    تحديد ما إذا كان يجب عرض زر التفعيل (NonVoip فقط)
    
    NON_VOIP ONLY: فقط long_term و 3days
    SMSPOOL: لا يوجد زر تفعيل
    """
    return False


def build_activate_button_markup(order_id: int, order_type: str, 
                                  activation_status: str = 'inactive',
                                  activated_until: str = None, 
                                  lang: str = 'ar'):
    """
    إنشاء زر Active للأرقام طويلة المدى (NonVoip فقط)
    
    NON_VOIP ONLY
    """
    logger.warning("build_activate_button_markup - غير مدعوم في SMSPool")
    return None


# ══════════════════════════════════════════════════════════════════════════════
# US-SPECIFIC FEATURES - غير مطلوبة في SMSPool (نظام دولي)
# ══════════════════════════════════════════════════════════════════════════════

def get_us_state_from_area_code(area_code: str) -> Optional[str]:
    """
    الحصول على الولاية الأمريكية من area code (NonVoip فقط)
    
    NON_VOIP ONLY - ميزة خاصة بالأرقام الأمريكية
    SMSPOOL: نظام دولي لا يركز على US فقط
    """
    logger.warning("get_us_state_from_area_code - ميزة US غير مطلوبة في SMSPool")
    return None


def filter_by_us_state(products: list, state_code: str) -> list:
    """
    تصفية المنتجات حسب الولاية الأمريكية (NonVoip فقط)
    
    NON_VOIP ONLY
    """
    logger.warning("filter_by_us_state - غير مدعوم في SMSPool")
    return []


# ══════════════════════════════════════════════════════════════════════════════
# AUCTION SYSTEM - غير موجود في SMSPool
# ══════════════════════════════════════════════════════════════════════════════

def place_auction_order(product_id: int, auction_percentage: int) -> Dict[str, Any]:
    """
    وضع عرض في المزاد للحصول على رقم (NonVoip فقط)
    
    NON_VOIP ONLY: auction parameter in order() API
    نسبة العرض للمزاد (10-2000%) للأرقام الأمريكية عند عدم التوفر
    
    SMSPOOL: لا يوجد نظام مزاد، النظام مباشر (شراء فوري)
    """
    logger.warning("auction - غير مدعوم في SMSPool")
    return {"status": "error", "message": "Auction not available in SMSPool"}


# ══════════════════════════════════════════════════════════════════════════════
# BALANCE NOTIFICATION SYSTEM - سيتم إعادة تطبيقه لـ SMSPool
# ══════════════════════════════════════════════════════════════════════════════

def check_nonvoip_balance_and_notify():
    """
    فحص رصيد NonVoip وإرسال إشعارات تدريجية للآدمن
    
    سيتم إعادة تطبيق هذا النظام لـ SMSPool في smspool_service.py
    """
    logger.info("check_nonvoip_balance - سيتم استبداله بـ check_smspool_balance")
    pass


# ══════════════════════════════════════════════════════════════════════════════
# NOTES للمطورين المستقبليين
# ══════════════════════════════════════════════════════════════════════════════

"""
ملاحظات مهمة للانتقال من NonVoip إلى SMSPool:

1. نظام الأرقام:
   NonVoip: short_term (15min), long_term (30days), 3days
   SMSPool: temporary (variable duration), rentals (monthly)

2. التفعيل:
   NonVoip: يحتاج activate() قبل الاستخدام للأرقام الطويلة
   SMSPool: تلقائي، لا يحتاج تفعيل

3. التجديد:
   NonVoip: renew() لتمديد الصلاحية
   SMSPool: extend_rental() للأرقام المستأجرة فقط

4. إعادة الاستخدام:
   NonVoip: reuse() مجاني للأرقام قصيرة الأمد
   SMSPool: resend_sms() لإعادة طلب الرسالة

5. الإلغاء:
   NonVoip: reject() قبل استقبال SMS فقط
   SMSPool: cancel_sms() في أي وقت قبل استقبال SMS

6. API Authentication:
   NonVoip: Email + Password
   SMSPool: API Key (32 characters)

7. الحالات:
   NonVoip: pending, reserved, active, delivered, success, expired, refunded
   SMSPool: pending (1), received (2), cancelled (3), expired (4)

8. الميزات الإضافية في SMSPool:
   - Rentals API (أرقام طويلة منفصلة)
   - Pool System (اختيار جودة الأرقام)
   - Archive Orders
   - Resend SMS

تم الاحتفاظ بهذا الملف للرجوع إليه عند الحاجة.
"""

logger.info("non_voip_trash.py loaded - جميع الدوال القديمة محفوظة هنا")
