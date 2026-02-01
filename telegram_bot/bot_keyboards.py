"""
bot_keyboards.py - ملف لوحات المفاتيح الموحد
Unified Keyboards File for Telegram Bot

يحتوي على قسمين:
- القسم الأول: Reply Keyboards (لوحات المفاتيح العادية)
- القسم الثاني: Inline Keyboards (الأزرار تحت الرسائل)

═══════════════════════════════════════════════════════════════════════════════
                              فهرس الكيبوردات
═══════════════════════════════════════════════════════════════════════════════

Reply Keyboards:
1. create_main_user_keyboard()      - الكيبورد الرئيسي للمستخدم
2. create_balance_keyboard()        - كيبورد قائمة الرصيد
3. create_admin_keyboard()          - الكيبورد الرئيسي للآدمن
4. create_orders_menu_keyboard()    - كيبورد إدارة الطلبات
5. create_money_menu_keyboard()     - كيبورد إدارة الأموال
6. create_referrals_menu_keyboard() - كيبورد الإحالات
7. create_settings_menu_keyboard()  - كيبورد إعدادات الآدمن
8. create_user_settings_keyboard()  - كيبورد إعدادات المستخدم
9. get_remove_keyboard()            - إزالة لوحة المفاتيح

Inline Keyboards:
10. create_back_button()             - زر رجوع
11. create_confirmation_keyboard()   - تأكيد/إلغاء
12. create_yes_no_keyboard()         - نعم/لا
13. create_language_selection_keyboard() - اختيار اللغة
14. create_paginated_keyboard()      - كيبورد مقسم لصفحات
15. create_country_keyboard()        - اختيار الدولة
16. create_state_keyboard()          - اختيار الولاية
17. create_payment_methods_keyboard() - طرق الدفع
18. create_order_actions_keyboard()  - إجراءات الطلب
19. create_user_management_keyboard() - إدارة المستخدم
20. create_faq_keyboard()            - الأسئلة الشائعة
21. create_proxy_type_keyboard()     - اختيار نوع البروكسي
22. create_duration_keyboard()       - اختيار المدة
23. create_quantity_keyboard()       - اختيار الكمية
24. build_inline_keyboard()          - بناء كيبورد مخصص
25. build_inline_keyboard_with_urls() - كيبورد مع روابط

Functions (دوال مساعدة):
26. restore_admin_keyboard()         - إعادة تفعيل كيبورد الآدمن

═══════════════════════════════════════════════════════════════════════════════
"""

from telegram import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove
)
from telegram.ext import ContextTypes
from typing import Optional, List, Dict, Tuple, Any

from config import MESSAGES


# ═══════════════════════════════════════════════════════════════════════════════
#                القسم الأول: Reply Keyboards (لوحات المفاتيح العادية)
# ═══════════════════════════════════════════════════════════════════════════════

def create_main_user_keyboard(language: str) -> ReplyKeyboardMarkup:
    """
    إنشاء الكيبورد الرئيسي للمستخدم العادي
    Create main user keyboard
    
    جميع الأزرار الديناميكية (بما فيها static_proxy و socks_proxy) قابلة للتعديل والحذف والإخفاء
    
    Args:
        language: لغة المستخدم ('ar' أو 'en')
    
    Returns:
        ReplyKeyboardMarkup: لوحة المفاتيح الرئيسية
    """
    buttons = MESSAGES[language]['main_menu_buttons']
    
    # بناء الكيبورد النهائي
    keyboard = []
    
    # جلب جميع الأزرار الديناميكية الجذرية (بما فيها static_proxy و socks_proxy)
    try:
        from dynamic_buttons import dynamic_buttons_manager
        # جلب جميع الأزرار (المفعلة والمعطلة) - الأزرار المعطلة ستظهر لكن لن تعمل
        dynamic_root_buttons = dynamic_buttons_manager.get_root_buttons(language, enabled_only=False)
        
        # فلترة الأزرار المخفية فقط (is_hidden) - الأزرار المعطلة (is_enabled=False) تظهر
        visible_buttons = [btn for btn in dynamic_root_buttons if not btn.get('is_hidden', False)]
        
        # ترتيب حسب order_index
        visible_buttons.sort(key=lambda x: x.get('order_index', 999))
        
        # بناء صفوف الأزرار الديناميكية
        row = []
        for btn in visible_buttons:
            icon = btn.get('icon', '')
            text = btn.get('text', '')
            btn_text = f"{icon} {text}".strip() if icon else text
            button_size = btn.get('button_size', 'large')
            
            if button_size == 'large':
                # زر كبير - سطر كامل
                if row:
                    keyboard.append(row)
                    row = []
                keyboard.append([KeyboardButton(btn_text)])
            else:
                # زر صغير - نصف سطر
                row.append(KeyboardButton(btn_text))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
        
        # إضافة أي أزرار متبقية في الصف
        if row:
            keyboard.append(row)
            
    except Exception as e:
        # في حالة الخطأ، استخدم الأزرار الافتراضية
        keyboard.append([KeyboardButton(buttons[0]), KeyboardButton(buttons[1])])
    
    # إضافة الأزرار الثابتة الأخرى (غير الديناميكية)
    keyboard.extend([
        [KeyboardButton(buttons[6]), KeyboardButton(buttons[9])],  # شراء أرقام + سوكس يومي
        [KeyboardButton(buttons[3]), KeyboardButton(buttons[2])],  # الرصيد + بروكسيات مجانية
        [KeyboardButton(buttons[4]), KeyboardButton(buttons[5])],  # تذكري بطلباتي + الإعدادات
        [KeyboardButton(buttons[7]), KeyboardButton(buttons[8])]   # سعر الصرف + لمحة عن خدماتنا
    ])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def create_profile_keyboard(language: str) -> ReplyKeyboardMarkup:
    """
    إنشاء كيبورد قائمة الملف الشخصي
    Create profile menu keyboard
    
    Args:
        language: لغة المستخدم ('ar' أو 'en')
    
    Returns:
        ReplyKeyboardMarkup: لوحة مفاتيح الملف الشخصي
    """
    buttons = MESSAGES[language]['profile_menu_buttons']
    keyboard = [
        [KeyboardButton(buttons[0])],  # معلومات الملف الشخصي
        [KeyboardButton(buttons[1])],  # الرصيد
        [KeyboardButton(buttons[2])],  # الإحالات
        [KeyboardButton(buttons[3])],  # الدعم
        [KeyboardButton(buttons[4])]   # رجوع
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def create_balance_keyboard(language: str) -> ReplyKeyboardMarkup:
    """
    إنشاء كيبورد قائمة الرصيد
    Create balance menu keyboard
    
    Args:
        language: لغة المستخدم ('ar' أو 'en')
    
    Returns:
        ReplyKeyboardMarkup: لوحة مفاتيح الرصيد
    """
    buttons = MESSAGES[language]['balance_menu_buttons']
    keyboard = [
        [KeyboardButton(buttons[0])],  # شحن رصيد
        [KeyboardButton(buttons[1])],  # رصيدي
        [KeyboardButton(buttons[2])]   # رجوع
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def create_admin_keyboard(language: str) -> ReplyKeyboardMarkup:
    """
    إنشاء الكيبورد الرئيسي للآدمن
    Create main admin keyboard
    
    Args:
        language: لغة الآدمن ('ar' أو 'en')
    
    Returns:
        ReplyKeyboardMarkup: لوحة مفاتيح الآدمن الرئيسية
    """
    if language == 'ar':
        keyboard = [
            [KeyboardButton("📋 إدارة الطلبات")],
            [KeyboardButton("💰 إدارة الأموال"), KeyboardButton("👥 الإحالات")],
            [KeyboardButton("📢 البث"), KeyboardButton("🔍 استعلام عن مستخدم")],
            [KeyboardButton("🌐 إدارة الخدمات"), KeyboardButton("⚙️ الإعدادات")],
            [KeyboardButton("🚪 تسجيل الخروج")]
        ]
    else:
        keyboard = [
            [KeyboardButton("📋 Manage Orders")],
            [KeyboardButton("💰 Manage Finances"), KeyboardButton("👥 Referrals")],
            [KeyboardButton("📢 Broadcast"), KeyboardButton("🔍 User Inquiry")],
            [KeyboardButton("🌐 Manage Services"), KeyboardButton("⚙️ Settings")],
            [KeyboardButton("🚪 Logout")]
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def create_orders_menu_keyboard(language: str) -> ReplyKeyboardMarkup:
    """
    إنشاء كيبورد قائمة إدارة الطلبات
    Create orders management menu keyboard
    
    Args:
        language: لغة المستخدم ('ar' أو 'en')
    
    Returns:
        ReplyKeyboardMarkup: لوحة مفاتيح إدارة الطلبات
    """
    buttons = MESSAGES[language]['orders_menu_buttons']
    keyboard = [
        [KeyboardButton(buttons[0])],  # الطلبات المعلقة
        [KeyboardButton(buttons[1])],  # استعلام عن طلب
        [KeyboardButton(buttons[2])],  # حذف الطلبات المعالجة
        [KeyboardButton(buttons[3])],  # حذف جميع الطلبات
        [KeyboardButton(buttons[4])]   # العودة للقائمة الرئيسية
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def create_money_menu_keyboard(language: str) -> ReplyKeyboardMarkup:
    """
    إنشاء كيبورد قائمة إدارة الأموال
    Create money management menu keyboard
    
    Args:
        language: لغة المستخدم ('ar' أو 'en')
    
    Returns:
        ReplyKeyboardMarkup: لوحة مفاتيح إدارة الأموال
    """
    buttons = MESSAGES[language]['money_menu_buttons']
    keyboard = [
        [KeyboardButton(buttons[0])],  # إحصائيات المبيعات
        [KeyboardButton(buttons[1])],  # إحصائيات NonVoip
        [KeyboardButton(buttons[2])],  # إدارة الأسعار
        [KeyboardButton(buttons[3])]   # العودة للقائمة الرئيسية
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def create_referrals_menu_keyboard(language: str) -> ReplyKeyboardMarkup:
    """
    إنشاء كيبورد قائمة الإحالات
    Create referrals menu keyboard
    
    Args:
        language: لغة المستخدم ('ar' أو 'en')
    
    Returns:
        ReplyKeyboardMarkup: لوحة مفاتيح الإحالات
    """
    buttons = MESSAGES[language]['referrals_menu_buttons']
    keyboard = [
        [KeyboardButton(buttons[0])],  # تحديد مبلغ الإحالة
        [KeyboardButton(buttons[1])],  # إحصائيات المستخدمين
        [KeyboardButton(buttons[2])],  # إعادة تعيين رصيد المستخدم
        [KeyboardButton(buttons[3])]   # العودة للقائمة الرئيسية
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def create_settings_menu_keyboard(language: str) -> ReplyKeyboardMarkup:
    """
    إنشاء كيبورد قائمة الإعدادات للآدمن
    Create settings menu keyboard for admin
    
    Args:
        language: لغة المستخدم ('ar' أو 'en')
    
    Returns:
        ReplyKeyboardMarkup: لوحة مفاتيح الإعدادات
    """
    buttons = MESSAGES[language]['settings_menu_buttons']
    keyboard = [
        [KeyboardButton(buttons[0]), KeyboardButton(buttons[1])],  # تغيير اللغة + تغيير كلمة المرور
        [KeyboardButton(buttons[2]), KeyboardButton(buttons[3])],  # إدارة الإشعارات + تحرير رسالة الخدمات
        [KeyboardButton(buttons[4]), KeyboardButton(buttons[5])],  # تحرير رسالة سعر الصرف + تعديل الشروط
        [KeyboardButton(buttons[6])],  # إدارة قاعدة البيانات
        [KeyboardButton(buttons[7])]   # العودة للقائمة الرئيسية
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def create_user_settings_keyboard(language: str) -> ReplyKeyboardMarkup:
    """
    إنشاء كيبورد إعدادات المستخدم العادي
    Create user settings keyboard
    
    Args:
        language: لغة المستخدم ('ar' أو 'en')
    
    Returns:
        ReplyKeyboardMarkup: لوحة مفاتيح إعدادات المستخدم
    """
    if language == 'ar':
        keyboard = [
            [KeyboardButton("🌐 تغيير اللغة")],
            [KeyboardButton("❓ الأسئلة الشائعة")],
            [KeyboardButton("↩️ العودة للقائمة الرئيسية")]
        ]
    else:
        keyboard = [
            [KeyboardButton("🌐 Change Language")],
            [KeyboardButton("❓ FAQ")],
            [KeyboardButton("↩️ Back to Main Menu")]
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_remove_keyboard() -> ReplyKeyboardRemove:
    """
    إزالة لوحة المفاتيح
    Remove keyboard
    
    Returns:
        ReplyKeyboardRemove: أمر إزالة لوحة المفاتيح
    """
    return ReplyKeyboardRemove()


# ═══════════════════════════════════════════════════════════════════════════════
#                 القسم الثاني: Inline Keyboards (الأزرار تحت الرسائل)
# ═══════════════════════════════════════════════════════════════════════════════

def create_back_button(callback_data: str, language: str = 'ar') -> InlineKeyboardMarkup:
    """
    إنشاء زر رجوع inline
    Create inline back button
    
    Args:
        callback_data: بيانات الـ callback
        language: لغة المستخدم ('ar' أو 'en')
    
    Returns:
        InlineKeyboardMarkup: زر الرجوع
    """
    text = "🔙 رجوع" if language == 'ar' else "🔙 Back"
    keyboard = [[InlineKeyboardButton(text, callback_data=callback_data)]]
    return InlineKeyboardMarkup(keyboard)


def create_confirmation_keyboard(
    confirm_callback: str,
    cancel_callback: str,
    language: str = 'ar'
) -> InlineKeyboardMarkup:
    """
    إنشاء كيبورد تأكيد/إلغاء
    Create confirmation/cancel keyboard
    
    Args:
        confirm_callback: بيانات callback التأكيد
        cancel_callback: بيانات callback الإلغاء
        language: لغة المستخدم ('ar' أو 'en')
    
    Returns:
        InlineKeyboardMarkup: كيبورد التأكيد
    """
    if language == 'ar':
        keyboard = [[
            InlineKeyboardButton("✅ تأكيد", callback_data=confirm_callback),
            InlineKeyboardButton("❌ إلغاء", callback_data=cancel_callback)
        ]]
    else:
        keyboard = [[
            InlineKeyboardButton("✅ Confirm", callback_data=confirm_callback),
            InlineKeyboardButton("❌ Cancel", callback_data=cancel_callback)
        ]]
    return InlineKeyboardMarkup(keyboard)


def create_yes_no_keyboard(
    yes_callback: str,
    no_callback: str,
    language: str = 'ar'
) -> InlineKeyboardMarkup:
    """
    إنشاء كيبورد نعم/لا
    Create yes/no keyboard
    
    Args:
        yes_callback: بيانات callback نعم
        no_callback: بيانات callback لا
        language: لغة المستخدم ('ar' أو 'en')
    
    Returns:
        InlineKeyboardMarkup: كيبورد نعم/لا
    """
    if language == 'ar':
        keyboard = [[
            InlineKeyboardButton("✅ نعم", callback_data=yes_callback),
            InlineKeyboardButton("❌ لا", callback_data=no_callback)
        ]]
    else:
        keyboard = [[
            InlineKeyboardButton("✅ Yes", callback_data=yes_callback),
            InlineKeyboardButton("❌ No", callback_data=no_callback)
        ]]
    return InlineKeyboardMarkup(keyboard)


def create_language_selection_keyboard() -> InlineKeyboardMarkup:
    """
    إنشاء كيبورد اختيار اللغة
    Create language selection keyboard
    
    Returns:
        InlineKeyboardMarkup: كيبورد اختيار اللغة
    """
    keyboard = [
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="set_language_ar")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="set_language_en")]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_paginated_keyboard(
    items: Dict[str, str],
    callback_prefix: str,
    page: int = 0,
    items_per_page: int = 8,
    language: str = 'ar',
    show_other: bool = True,
    back_callback: Optional[str] = None
) -> InlineKeyboardMarkup:
    """
    إنشاء كيبورد مقسم لصفحات مع أزرار التنقل
    Create paginated keyboard with navigation buttons
    
    Args:
        items: قاموس العناصر {code: name}
        callback_prefix: بادئة callback
        page: رقم الصفحة الحالية (يبدأ من 0)
        items_per_page: عدد العناصر في الصفحة
        language: لغة المستخدم ('ar' أو 'en')
        show_other: عرض زر "غير ذلك"
        back_callback: callback زر الرجوع (اختياري)
    
    Returns:
        InlineKeyboardMarkup: كيبورد مقسم لصفحات
    """
    keyboard = []
    
    if show_other:
        other_text = "🔧 غير ذلك" if language == 'ar' else "🔧 Other"
        keyboard.append([InlineKeyboardButton(other_text, callback_data=f"{callback_prefix}other")])
    
    items_list = list(items.items())
    start = page * items_per_page
    end = start + items_per_page
    page_items = items_list[start:end]
    has_more = len(items_list) > end
    
    for code, name in page_items:
        keyboard.append([InlineKeyboardButton(name, callback_data=f"{callback_prefix}{code}")])
    
    nav_buttons = []
    if page > 0:
        prev_text = "◀️ السابق" if language == 'ar' else "◀️ Previous"
        nav_buttons.append(InlineKeyboardButton(prev_text, callback_data=f"{callback_prefix}page_{page-1}"))
    if has_more:
        next_text = "التالي ▶️" if language == 'ar' else "Next ▶️"
        nav_buttons.append(InlineKeyboardButton(next_text, callback_data=f"{callback_prefix}page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    if back_callback:
        back_text = "🔙 رجوع" if language == 'ar' else "🔙 Back"
        keyboard.append([InlineKeyboardButton(back_text, callback_data=back_callback)])
    
    return InlineKeyboardMarkup(keyboard)


def create_country_keyboard(
    countries: Dict[str, Dict[str, str]],
    callback_prefix: str,
    language: str = 'ar',
    back_callback: Optional[str] = None
) -> InlineKeyboardMarkup:
    """
    إنشاء كيبورد اختيار الدولة
    Create country selection keyboard
    
    Args:
        countries: قاموس الدول {code: {'ar': name_ar, 'en': name_en}}
        callback_prefix: بادئة callback
        language: لغة المستخدم ('ar' أو 'en')
        back_callback: callback زر الرجوع (اختياري)
    
    Returns:
        InlineKeyboardMarkup: كيبورد اختيار الدولة
    """
    keyboard = []
    
    for code, names in countries.items():
        name = names.get(language, names.get('en', code))
        keyboard.append([InlineKeyboardButton(name, callback_data=f"{callback_prefix}{code}")])
    
    if back_callback:
        back_text = "🔙 رجوع" if language == 'ar' else "🔙 Back"
        keyboard.append([InlineKeyboardButton(back_text, callback_data=back_callback)])
    
    return InlineKeyboardMarkup(keyboard)


def create_state_keyboard(
    states: Dict[str, str],
    callback_prefix: str,
    language: str = 'ar',
    back_callback: Optional[str] = None,
    items_per_row: int = 2
) -> InlineKeyboardMarkup:
    """
    إنشاء كيبورد اختيار الولاية/المنطقة
    Create state/region selection keyboard
    
    Args:
        states: قاموس الولايات {code: name}
        callback_prefix: بادئة callback
        language: لغة المستخدم ('ar' أو 'en')
        back_callback: callback زر الرجوع (اختياري)
        items_per_row: عدد العناصر في الصف
    
    Returns:
        InlineKeyboardMarkup: كيبورد اختيار الولاية
    """
    keyboard = []
    row = []
    
    for code, name in states.items():
        row.append(InlineKeyboardButton(f"📍 {name}", callback_data=f"{callback_prefix}{code}"))
        if len(row) >= items_per_row:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    if back_callback:
        back_text = "🔙 رجوع" if language == 'ar' else "🔙 Back"
        keyboard.append([InlineKeyboardButton(back_text, callback_data=back_callback)])
    
    return InlineKeyboardMarkup(keyboard)


def create_payment_methods_keyboard(
    language: str = 'ar',
    balance_enabled: bool = True,
    user_balance: float = 0.0,
    order_amount: float = 0.0
) -> InlineKeyboardMarkup:
    """
    إنشاء كيبورد طرق الدفع
    Create payment methods keyboard
    
    Args:
        language: لغة المستخدم ('ar' أو 'en')
        balance_enabled: تفعيل الدفع من الرصيد
        user_balance: رصيد المستخدم
        order_amount: قيمة الطلب
    
    Returns:
        InlineKeyboardMarkup: كيبورد طرق الدفع
    """
    keyboard = []
    
    if balance_enabled and user_balance >= order_amount:
        if language == 'ar':
            keyboard.append([InlineKeyboardButton(f"💰 الدفع من الرصيد ({user_balance:.2f}$)", callback_data="pay_from_balance")])
        else:
            keyboard.append([InlineKeyboardButton(f"💰 Pay from Balance ({user_balance:.2f}$)", callback_data="pay_from_balance")])
    
    if language == 'ar':
        keyboard.append([InlineKeyboardButton("💳 USDT (TRC20)", callback_data="payment_usdt_trc20")])
        keyboard.append([InlineKeyboardButton("💵 سيرياتيل كاش", callback_data="payment_syriatel_cash")])
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="cancel_payment")])
    else:
        keyboard.append([InlineKeyboardButton("💳 USDT (TRC20)", callback_data="payment_usdt_trc20")])
        keyboard.append([InlineKeyboardButton("💵 Syriatel Cash", callback_data="payment_syriatel_cash")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="cancel_payment")])
    
    return InlineKeyboardMarkup(keyboard)


def create_order_actions_keyboard(
    order_id: str,
    language: str = 'ar',
    show_approve: bool = True,
    show_reject: bool = True,
    show_details: bool = True
) -> InlineKeyboardMarkup:
    """
    إنشاء كيبورد إجراءات الطلب للآدمن
    Create order actions keyboard for admin
    
    Args:
        order_id: معرف الطلب
        language: لغة المستخدم ('ar' أو 'en')
        show_approve: عرض زر الموافقة
        show_reject: عرض زر الرفض
        show_details: عرض زر التفاصيل
    
    Returns:
        InlineKeyboardMarkup: كيبورد إجراءات الطلب
    """
    keyboard = []
    
    if show_approve and show_reject:
        if language == 'ar':
            keyboard.append([
                InlineKeyboardButton("✅ موافقة", callback_data=f"approve_order_{order_id}"),
                InlineKeyboardButton("❌ رفض", callback_data=f"reject_order_{order_id}")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_order_{order_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_order_{order_id}")
            ])
    
    if show_details:
        if language == 'ar':
            keyboard.append([InlineKeyboardButton("📋 التفاصيل", callback_data=f"order_details_{order_id}")])
        else:
            keyboard.append([InlineKeyboardButton("📋 Details", callback_data=f"order_details_{order_id}")])
    
    return InlineKeyboardMarkup(keyboard)


def create_user_management_keyboard(
    user_id: int,
    language: str = 'ar'
) -> InlineKeyboardMarkup:
    """
    إنشاء كيبورد إدارة المستخدم للآدمن
    Create user management keyboard for admin
    
    Args:
        user_id: معرف المستخدم
        language: لغة المستخدم ('ar' أو 'en')
    
    Returns:
        InlineKeyboardMarkup: كيبورد إدارة المستخدم
    """
    if language == 'ar':
        keyboard = [
            [
                InlineKeyboardButton("👤 إدارة المستخدم", callback_data=f"manage_user_{user_id}"),
                InlineKeyboardButton("💰 إدارة النقاط", callback_data=f"manage_points_{user_id}")
            ],
            [
                InlineKeyboardButton("📢 بث لهذا المستخدم", callback_data=f"broadcast_user_{user_id}"),
                InlineKeyboardButton("👥 إدارة الإحالات", callback_data=f"manage_referrals_{user_id}")
            ],
            [
                InlineKeyboardButton("💬 انتقال للمحادثة", url=f"tg://user?id={user_id}"),
                InlineKeyboardButton("📊 تقارير مفصلة", callback_data=f"detailed_reports_{user_id}")
            ],
            [
                InlineKeyboardButton("🔙 رجوع لقائمة الأدمن", callback_data="back_to_admin_menu")
            ]
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton("👤 Manage User", callback_data=f"manage_user_{user_id}"),
                InlineKeyboardButton("💰 Manage Points", callback_data=f"manage_points_{user_id}")
            ],
            [
                InlineKeyboardButton("📢 Broadcast to User", callback_data=f"broadcast_user_{user_id}"),
                InlineKeyboardButton("👥 Manage Referrals", callback_data=f"manage_referrals_{user_id}")
            ],
            [
                InlineKeyboardButton("💬 Go to Chat", url=f"tg://user?id={user_id}"),
                InlineKeyboardButton("📊 Detailed Reports", callback_data=f"detailed_reports_{user_id}")
            ],
            [
                InlineKeyboardButton("🔙 Back to Admin Menu", callback_data="back_to_admin_menu")
            ]
        ]
    
    return InlineKeyboardMarkup(keyboard)


def create_faq_keyboard(language: str = 'ar') -> InlineKeyboardMarkup:
    """
    إنشاء كيبورد الأسئلة الشائعة
    Create FAQ keyboard
    
    Args:
        language: لغة المستخدم ('ar' أو 'en')
    
    Returns:
        InlineKeyboardMarkup: كيبورد الأسئلة الشائعة
    """
    if language == 'ar':
        keyboard = [[InlineKeyboardButton("❓ الأسئلة الشائعة", callback_data="faq_menu")]]
    else:
        keyboard = [[InlineKeyboardButton("❓ FAQ", callback_data="faq_menu")]]
    return InlineKeyboardMarkup(keyboard)


def create_proxy_type_keyboard(language: str = 'ar') -> InlineKeyboardMarkup:
    """
    إنشاء كيبورد اختيار نوع البروكسي
    Create proxy type selection keyboard
    
    Args:
        language: لغة المستخدم ('ar' أو 'en')
    
    Returns:
        InlineKeyboardMarkup: كيبورد اختيار نوع البروكسي
    """
    if language == 'ar':
        keyboard = [
            [InlineKeyboardButton("🏠 Residential", callback_data="proxy_type_residential")],
            [InlineKeyboardButton("🌐 ISP", callback_data="proxy_type_isp")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="cancel_proxy_request")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("🏠 Residential", callback_data="proxy_type_residential")],
            [InlineKeyboardButton("🌐 ISP", callback_data="proxy_type_isp")],
            [InlineKeyboardButton("🔙 Back", callback_data="cancel_proxy_request")]
        ]
    return InlineKeyboardMarkup(keyboard)


def create_duration_keyboard(
    durations: List[Tuple[str, str, str]],
    language: str = 'ar',
    back_callback: str = "cancel_duration"
) -> InlineKeyboardMarkup:
    """
    إنشاء كيبورد اختيار المدة
    Create duration selection keyboard
    
    Args:
        durations: قائمة المدد [(display_text, callback_data, price)]
        language: لغة المستخدم ('ar' أو 'en')
        back_callback: callback زر الرجوع
    
    Returns:
        InlineKeyboardMarkup: كيبورد اختيار المدة
    """
    keyboard = []
    
    for display_text, callback_data, price in durations:
        keyboard.append([InlineKeyboardButton(f"{display_text} - ${price}", callback_data=callback_data)])
    
    back_text = "🔙 رجوع" if language == 'ar' else "🔙 Back"
    keyboard.append([InlineKeyboardButton(back_text, callback_data=back_callback)])
    
    return InlineKeyboardMarkup(keyboard)


def create_quantity_keyboard(
    quantities: List[int],
    callback_prefix: str,
    language: str = 'ar',
    back_callback: Optional[str] = None
) -> InlineKeyboardMarkup:
    """
    إنشاء كيبورد اختيار الكمية
    Create quantity selection keyboard
    
    Args:
        quantities: قائمة الكميات المتاحة
        callback_prefix: بادئة callback
        language: لغة المستخدم ('ar' أو 'en')
        back_callback: callback زر الرجوع (اختياري)
    
    Returns:
        InlineKeyboardMarkup: كيبورد اختيار الكمية
    """
    keyboard = []
    row = []
    
    for qty in quantities:
        row.append(InlineKeyboardButton(str(qty), callback_data=f"{callback_prefix}{qty}"))
        if len(row) >= 4:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    manual_text = "✏️ إدخال يدوي" if language == 'ar' else "✏️ Manual Input"
    keyboard.append([InlineKeyboardButton(manual_text, callback_data=f"{callback_prefix}manual")])
    
    if back_callback:
        back_text = "🔙 رجوع" if language == 'ar' else "🔙 Back"
        keyboard.append([InlineKeyboardButton(back_text, callback_data=back_callback)])
    
    return InlineKeyboardMarkup(keyboard)


def create_separator_keyboard() -> InlineKeyboardMarkup:
    """
    إنشاء فاصل زخرفي
    Create decorative separator
    
    Returns:
        InlineKeyboardMarkup: كيبورد فاصل
    """
    keyboard = [[InlineKeyboardButton("━━━━━━━━━━━━━━━━━━━━━━━", callback_data="separator")]]
    return InlineKeyboardMarkup(keyboard)


def build_inline_keyboard(
    buttons: List[List[Tuple[str, str]]],
    add_back: bool = False,
    back_callback: str = "back",
    language: str = 'ar'
) -> InlineKeyboardMarkup:
    """
    بناء كيبورد inline مخصص من قائمة أزرار
    Build custom inline keyboard from button list
    
    Args:
        buttons: قائمة أزرار [[("text", "callback"), ...], ...]
        add_back: إضافة زر رجوع
        back_callback: callback زر الرجوع
        language: لغة المستخدم ('ar' أو 'en')
    
    Returns:
        InlineKeyboardMarkup: كيبورد inline مخصص
    """
    keyboard = []
    
    for row in buttons:
        keyboard_row = []
        for text, callback in row:
            keyboard_row.append(InlineKeyboardButton(text, callback_data=callback))
        keyboard.append(keyboard_row)
    
    if add_back:
        back_text = "🔙 رجوع" if language == 'ar' else "🔙 Back"
        keyboard.append([InlineKeyboardButton(back_text, callback_data=back_callback)])
    
    return InlineKeyboardMarkup(keyboard)


def build_inline_keyboard_with_urls(
    buttons: List[List[Dict[str, str]]]
) -> InlineKeyboardMarkup:
    """
    بناء كيبورد inline مع روابط URL
    Build inline keyboard with URL links
    
    Args:
        buttons: قائمة أزرار [[{"text": "", "callback": "" أو "url": ""}, ...], ...]
    
    Returns:
        InlineKeyboardMarkup: كيبورد inline مع روابط
    """
    keyboard = []
    
    for row in buttons:
        keyboard_row = []
        for btn in row:
            if 'url' in btn:
                keyboard_row.append(InlineKeyboardButton(btn['text'], url=btn['url']))
            else:
                keyboard_row.append(InlineKeyboardButton(btn['text'], callback_data=btn['callback']))
        keyboard.append(keyboard_row)
    
    return InlineKeyboardMarkup(keyboard)


# ═══════════════════════════════════════════════════════════════════════════════
#                    القسم الثالث: دوال مساعدة (Helper Functions)
# ═══════════════════════════════════════════════════════════════════════════════

async def restore_admin_keyboard(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    message: Optional[str] = None,
    language: Optional[str] = None,
    get_admin_language_func=None
):
    """
    إعادة تفعيل كيبورد الأدمن الرئيسي
    Restore admin main keyboard
    
    Args:
        context: سياق البوت
        chat_id: معرف المحادثة
        message: رسالة مخصصة (اختياري)
        language: لغة الآدمن (اختياري)
        get_admin_language_func: دالة للحصول على لغة الآدمن
    
    Note:
        يجب تمرير دالة get_admin_language_func للحصول على لغة الآدمن
    """
    if language is None and get_admin_language_func:
        language = get_admin_language_func(chat_id)
    elif language is None:
        language = 'ar'
    
    if language == 'ar':
        admin_keyboard = [
            [KeyboardButton("📋 إدارة الطلبات")],
            [KeyboardButton("💰 إدارة الأموال"), KeyboardButton("👥 الإحالات")],
            [KeyboardButton("📢 البث"), KeyboardButton("🔍 استعلام عن مستخدم")],
            [KeyboardButton("🌐 إدارة الخدمات"), KeyboardButton("⚙️ الإعدادات")],
            [KeyboardButton("🚪 تسجيل الخروج")]
        ]
        if message is None:
            message = "🔧 لوحة الأدمن جاهزة"
    else:
        admin_keyboard = [
            [KeyboardButton("📋 Manage Orders")],
            [KeyboardButton("💰 Manage Finances"), KeyboardButton("👥 Referrals")],
            [KeyboardButton("📢 Broadcast"), KeyboardButton("🔍 User Inquiry")],
            [KeyboardButton("🌐 Manage Services"), KeyboardButton("⚙️ Settings")],
            [KeyboardButton("🚪 Logout")]
        ]
        if message is None:
            message = "🔧 Admin Panel Ready"
    
    admin_reply_markup = ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True)
    
    await context.bot.send_message(
        chat_id,
        message,
        reply_markup=admin_reply_markup
    )


# ═══════════════════════════════════════════════════════════════════════════════
#                    القسم الرابع: دوال الأزرار الديناميكية
# ═══════════════════════════════════════════════════════════════════════════════

def format_button_text_with_price(text: str, price: float, language: str = 'ar') -> str:
    """
    تنسيق نص الزر مع السعر حسب اللغة
    Format button text with price based on language
    
    Args:
        text: نص الزر
        price: السعر
        language: لغة المستخدم ('ar' أو 'en')
    
    Returns:
        str: النص المنسق مع السعر
    """
    if not price or price <= 0:
        return text
    
    if language == 'ar':
        # للعربية: السعر في البداية (لأن النص يُقرأ من اليمين لليسار)
        return f"({price}$) {text}"
    else:
        # للإنجليزية: السعر في النهاية
        return f"{text} (${price})"


def get_button_children_count(button_id: int, language: str = 'ar') -> int:
    """
    حساب عدد العناصر الفرعية للزر (بما في ذلك أبناء فواصل الصفحات)
    Count the number of child items for a button (including children of page separators)
    
    Args:
        button_id: معرف الزر
        language: لغة المستخدم
    
    Returns:
        int: عدد العناصر الفرعية
    """
    from dynamic_buttons import dynamic_buttons_manager
    # جلب جميع الأزرار لحساب العدد الصحيح
    children = dynamic_buttons_manager.get_children(button_id, language, enabled_only=False)
    
    total_count = 0
    for child in children:
        if child.get('button_type') == 'page_separator':
            # فاصل الصفحة - نحسب أبناءه
            separator_children = dynamic_buttons_manager.get_children(child['id'], language, enabled_only=False)
            # نحسب فقط الأزرار غير فواصل الصفحات
            total_count += len([c for c in separator_children if c.get('button_type') != 'page_separator'])
        else:
            total_count += 1
    
    return total_count


def format_button_text_with_count(text: str, count: int, price: float, language: str = 'ar') -> str:
    """
    تنسيق نص الزر مع السعر فقط (عدد العناصر يظهر في واجهة الويب فقط)
    Format button text with price only (count is shown only in web UI)
    
    Args:
        text: نص الزر
        count: عدد العناصر الفرعية (غير مستخدم - للتوافق مع الأكواد القديمة)
        price: السعر
        language: لغة المستخدم
    
    Returns:
        str: النص المنسق مع السعر فقط
    """
    # لا نضيف العدد - يظهر فقط في واجهة الويب
    
    # إضافة السعر إذا وجد
    if price and price > 0:
        if language == 'ar':
            return f"({price}$) {text}"
        else:
            return f"{text} (${price})"
    
    return text


def create_dynamic_root_keyboard(language: str = 'ar', page: int = 0) -> InlineKeyboardMarkup:
    """
    إنشاء كيبورد الأزرار الجذرية الديناميكية مع دعم الترقيم
    Create dynamic root buttons keyboard with pagination support
    
    السلوك:
    - فواصل الصفحات تُستخدم كفواصل منطقية للترقيم فقط
    - لا تظهر فواصل الصفحات كأزرار inline
    - يتم التنقل بين الصفحات عبر أزرار السابق/التالي
    
    Args:
        language: لغة المستخدم ('ar' أو 'en')
        page: رقم الصفحة الحالية (يبدأ من 0)
    
    Returns:
        InlineKeyboardMarkup: كيبورد الأزرار الجذرية
    """
    from dynamic_buttons import dynamic_buttons_manager
    # جلب جميع الأزرار (المفعلة والمعطلة) - الأزرار المعطلة ستظهر لكن لن تعمل
    buttons = dynamic_buttons_manager.get_root_buttons(language, enabled_only=False)
    
    # فلترة الأزرار المخفية فقط (is_hidden) - الأزرار المعطلة (is_enabled=False) تظهر
    buttons = [btn for btn in buttons if not btn.get('is_hidden', False)]
    
    # ترتيب الأزرار حسب order_index (الرجوع 9998، الإلغاء 9999 في النهاية)
    buttons.sort(key=lambda x: x.get('order_index', 0))
    
    # تقسيم الأزرار إلى صفحات باستخدام فواصل الصفحات
    pages = []
    current_page_buttons = []
    
    for btn in buttons:
        if btn.get('button_type') == 'page_separator':
            # فاصل صفحة - نحفظ الصفحة الحالية ونبدأ صفحة جديدة
            if current_page_buttons:
                pages.append(current_page_buttons)
            current_page_buttons = []
        else:
            # زر عادي - نضيفه للصفحة الحالية
            current_page_buttons.append(btn)
    
    # إضافة الصفحة الأخيرة
    if current_page_buttons:
        pages.append(current_page_buttons)
    
    if not pages:
        pages = [[]]
    
    total_pages = len(pages)
    current_page = max(0, min(page, total_pages - 1))
    page_buttons = pages[current_page] if pages else []
    
    keyboard = []
    for btn in page_buttons:
        # تخطي فواصل الصفحات - لا تظهر كأزرار
        if btn.get('button_type') == 'page_separator':
            continue
        
        # تحديد نص الزر حسب نوعه
        btn_type = btn.get('button_type', 'menu')
        if btn_type == 'back':
            # زر الرجوع - استخدام النص الثابت مع الإيموجي
            btn_text = "🔙 رجوع" if language == 'ar' else "🔙 Back"
            # أزرار الرجوع داخل القائمة الرئيسية - نفس السلوك
            keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"dyn_{btn['id']}")])
            continue
        elif btn_type == 'cancel':
            # زر الإلغاء - استخدام النص الثابت مع الإيموجي
            btn_text = "❌ إلغاء" if language == 'ar' else "❌ Cancel"
        elif btn_type == 'link':
            # زر الرابط - يفتح رابط خارجي
            btn_text = format_button_text_with_price(btn['text'], btn.get('price', 0), language)
            link_url = btn.get('message', '') or btn.get('message_ar', '')
            if link_url:
                # إذا كان الرابط موجوداً، استخدام url لفتحه مباشرة
                keyboard.append([InlineKeyboardButton(text=btn_text, url=link_url)])
            else:
                # إذا لم يكن الرابط موجوداً، استخدام callback_data ليعالجه المعالج
                keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"dyn_{btn['id']}")])
            continue
        elif btn_type == 'menu':
            # للقوائم: إضافة عدد العناصر الفرعية
            children_count = get_button_children_count(btn['id'], language)
            btn_text = format_button_text_with_count(btn['text'], children_count, btn.get('price', 0), language)
        else:
            # للخدمات والأنواع الأخرى: إضافة السعر فقط
            btn_text = format_button_text_with_price(btn['text'], btn.get('price', 0), language)
        
        keyboard.append([InlineKeyboardButton(
            text=btn_text,
            callback_data=f"dyn_{btn['id']}"
        )])
    
    # أزرار التنقل بين الصفحات (حلقة - التالي من الأخيرة يعود للأولى)
    if total_pages > 1:
        nav_row = []
        prev_page = (current_page - 1) % total_pages
        nav_row.append(InlineKeyboardButton(
            text="⬅️",
            callback_data=f"dyn_root_page_{prev_page}"
        ))
        
        page_indicator = f"{current_page + 1}/{total_pages}"
        nav_row.append(InlineKeyboardButton(
            text=page_indicator,
            callback_data="noop"
        ))
        
        next_page = (current_page + 1) % total_pages
        nav_row.append(InlineKeyboardButton(
            text="➡️",
            callback_data=f"dyn_root_page_{next_page}"
        ))
        
        keyboard.append(nav_row)
    
    return InlineKeyboardMarkup(keyboard)


def create_dynamic_children_keyboard(
    parent_id: int, 
    language: str = 'ar', 
    back_callback: str = 'dyn_root',
    page: int = 0
) -> InlineKeyboardMarkup:
    """
    إنشاء كيبورد الأزرار الفرعية الديناميكية مع دعم الترقيم
    Create dynamic children buttons keyboard with pagination support
    
    السلوك:
    - فواصل الصفحات تُستخدم كفواصل منطقية للترقيم فقط
    - لا تظهر فواصل الصفحات كأزرار inline
    - يتم عرض أبناء كل فاصل مباشرة
    - التنقل بين فواصل الصفحات عبر أزرار السابق/التالي
    
    Args:
        parent_id: معرف الزر الأب
        language: لغة المستخدم ('ar' أو 'en')
        back_callback: callback الرجوع
        page: رقم الصفحة الحالية (يبدأ من 0)
    
    Returns:
        InlineKeyboardMarkup: كيبورد الأزرار الفرعية
    """
    from dynamic_buttons import dynamic_buttons_manager
    # جلب جميع الأزرار الفرعية (المفعلة والمعطلة) - الأزرار المعطلة ستظهر لكن لن تعمل
    children = dynamic_buttons_manager.get_children(parent_id, language, enabled_only=False)
    
    # فلترة الأزرار المخفية فقط (is_hidden) - الأزرار المعطلة (is_enabled=False) تظهر
    children = [btn for btn in children if not btn.get('is_hidden', False)]
    
    # ترتيب الأزرار حسب order_index (الرجوع 9998، الإلغاء 9999 في النهاية)
    children.sort(key=lambda x: x.get('order_index', 0))
    
    page_separators = []
    non_separator_buttons = []
    
    for btn in children:
        if btn.get('button_type') == 'page_separator':
            page_separators.append(btn)
        else:
            non_separator_buttons.append(btn)
    
    page_separators.sort(key=lambda x: x.get('order_index', 0))
    
    pages = []
    
    if page_separators:
        # كل فاصل صفحة يُنشئ صفحة جديدة تحتوي على أبنائه مباشرة
        for separator in page_separators:
            # جلب جميع الأزرار (المفعلة والمعطلة) - الأزرار المعطلة ستظهر لكن لن تعمل
            separator_children = dynamic_buttons_manager.get_children(separator['id'], language, enabled_only=False)
            # تصفية فواصل الصفحات والأزرار المخفية من أبناء الفاصل
            child_buttons = [btn for btn in separator_children 
                           if btn.get('button_type') != 'page_separator' and not btn.get('is_hidden', False)]
            # ترتيب الأزرار حسب order_index (الرجوع 9998، الإلغاء 9999 في النهاية)
            child_buttons.sort(key=lambda x: x.get('order_index', 0))
            pages.append({'buttons': child_buttons, 'separator': separator})
    else:
        # لا توجد فواصل - عرض الأزرار العادية
        pages.append({'buttons': non_separator_buttons, 'separator': None})
    
    if not pages:
        pages = [{'buttons': [], 'separator': None}]
    
    total_pages = len(pages)
    current_page = max(0, min(page, total_pages - 1))
    page_data = pages[current_page] if pages else {'buttons': [], 'separator': None}
    page_buttons = page_data['buttons']
    
    keyboard = []
    for btn in page_buttons:
        # تخطي فواصل الصفحات - لا تظهر كأزرار
        if btn.get('button_type') == 'page_separator':
            continue
        
        # تحديد نص الزر حسب نوعه
        btn_type = btn.get('button_type', 'menu')
        if btn_type == 'back':
            # زر الرجوع - استخدام النص الثابت مع الإيموجي
            btn_text = "🔙 رجوع" if language == 'ar' else "🔙 Back"
            # أزرار الرجوع داخل فواصل الصفحات ترجع للقائمة الرئيسية
            back_behavior = btn.get('back_behavior', 'root')
            if back_behavior == 'root':
                keyboard.append([InlineKeyboardButton(text=btn_text, callback_data="dyn_root")])
            else:
                keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"dyn_{btn['id']}")])
            continue
        elif btn_type == 'cancel':
            # زر الإلغاء - استخدام النص الثابت مع الإيموجي
            btn_text = "❌ إلغاء" if language == 'ar' else "❌ Cancel"
        elif btn_type == 'link':
            # زر الرابط - يفتح رابط خارجي
            btn_text = format_button_text_with_price(btn['text'], btn.get('price', 0), language)
            link_url = btn.get('message', '') or btn.get('message_ar', '')
            if link_url:
                # إذا كان الرابط موجوداً، استخدام url لفتحه مباشرة
                keyboard.append([InlineKeyboardButton(text=btn_text, url=link_url)])
            else:
                # إذا لم يكن الرابط موجوداً، استخدام callback_data ليعالجه المعالج
                keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"dyn_{btn['id']}")])
            continue
        elif btn_type == 'menu':
            # للقوائم: إضافة عدد العناصر الفرعية
            children_count = get_button_children_count(btn['id'], language)
            btn_text = format_button_text_with_count(btn['text'], children_count, btn.get('price', 0), language)
        else:
            # للخدمات والأنواع الأخرى: إضافة السعر فقط
            btn_text = format_button_text_with_price(btn['text'], btn.get('price', 0), language)
        
        keyboard.append([InlineKeyboardButton(
            text=btn_text,
            callback_data=f"dyn_{btn['id']}"
        )])
    
    # أزرار التنقل بين الصفحات (حلقة - التالي من الأخيرة يعود للأولى)
    if total_pages > 1:
        nav_row = []
        prev_page = (current_page - 1) % total_pages
        nav_row.append(InlineKeyboardButton(
            text="⬅️",
            callback_data=f"dyn_page_{parent_id}_{prev_page}"
        ))
        
        page_indicator = f"{current_page + 1}/{total_pages}"
        nav_row.append(InlineKeyboardButton(
            text=page_indicator,
            callback_data="noop"
        ))
        
        next_page = (current_page + 1) % total_pages
        nav_row.append(InlineKeyboardButton(
            text="➡️",
            callback_data=f"dyn_page_{parent_id}_{next_page}"
        ))
        
        keyboard.append(nav_row)
    
    # لا يتم إضافة زر رجوع ثابت - أزرار الرجوع تأتي من الشجرة الديناميكية فقط
    return InlineKeyboardMarkup(keyboard)


def get_page_separator_message(
    parent_id: int,
    language: str = 'ar',
    page: int = 0
) -> Optional[str]:
    """
    الحصول على رسالة فاصل الصفحة للصفحة المحددة
    Get page separator message for the specified page
    
    Args:
        parent_id: معرف الزر الأب
        language: لغة المستخدم ('ar' أو 'en')
        page: رقم الصفحة الحالية (يبدأ من 0)
    
    Returns:
        Optional[str]: رسالة فاصل الصفحة أو None
    """
    from dynamic_buttons import dynamic_buttons_manager
    # جلب جميع الأزرار لمعرفة فواصل الصفحات
    children = dynamic_buttons_manager.get_children(parent_id, language, enabled_only=False)
    
    page_separators = []
    
    for btn in children:
        if btn.get('button_type') == 'page_separator':
            page_separators.append(btn)
    
    if not page_separators:
        return None
    
    # ترتيب الفواصل حسب order_index
    page_separators.sort(key=lambda x: x.get('order_index', 0))
    
    # الحصول على رسالة الفاصل للصفحة المحددة
    current_page = max(0, min(page, len(page_separators) - 1))
    
    if current_page < len(page_separators):
        separator = page_separators[current_page]
        return separator.get('message', '')
    
    return None


def create_dynamic_quantity_keyboard(
    button_id: int, 
    language: str = 'ar',
    show_back: bool = True,
    show_cancel: bool = True
) -> InlineKeyboardMarkup:
    """
    إنشاء كيبورد اختيار الكمية للأزرار الديناميكية
    Create dynamic quantity selection keyboard
    
    Args:
        button_id: معرف الزر
        language: لغة المستخدم ('ar' أو 'en')
        show_back: عرض زر الرجوع
        show_cancel: عرض زر الإلغاء
    
    Returns:
        InlineKeyboardMarkup: كيبورد اختيار الكمية
    """
    quantities = [1, 2, 3, 5, 10]
    keyboard = []
    row = []
    for qty in quantities:
        row.append(InlineKeyboardButton(
            text=str(qty),
            callback_data=f"dyn_qty_{button_id}_{qty}"
        ))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton(
        text="✏️ إدخال يدوي" if language == 'ar' else "✏️ Manual Input",
        callback_data=f"dyn_qty_{button_id}_manual"
    )])
    
    nav_row = []
    if show_back:
        nav_row.append(InlineKeyboardButton(
            text="🔙 رجوع" if language == 'ar' else "🔙 Back",
            callback_data=f"dyn_back_{button_id}"
        ))
    if show_cancel:
        nav_row.append(InlineKeyboardButton(
            text="❌ إلغاء" if language == 'ar' else "❌ Cancel",
            callback_data="cancel_user_proxy_request"
        ))
    if nav_row:
        keyboard.append(nav_row)
    
    return InlineKeyboardMarkup(keyboard)


def create_quantity_input_keyboard(
    button_id: int,
    language: str = 'ar',
    show_back: bool = True,
    show_cancel: bool = True
) -> InlineKeyboardMarkup:
    """
    إنشاء كيبورد للإدخال اليدوي للكمية مع أزرار الرجوع والإلغاء
    Create keyboard for manual quantity input with back and cancel buttons
    
    Args:
        button_id: معرف الزر
        language: لغة المستخدم ('ar' أو 'en')
        show_back: عرض زر الرجوع
        show_cancel: عرض زر الإلغاء
    
    Returns:
        InlineKeyboardMarkup: كيبورد مع أزرار التنقل
    """
    keyboard = []
    nav_row = []
    
    if show_back:
        nav_row.append(InlineKeyboardButton(
            text="🔙 رجوع" if language == 'ar' else "🔙 Back",
            callback_data=f"dyn_back_{button_id}"
        ))
    if show_cancel:
        nav_row.append(InlineKeyboardButton(
            text="❌ إلغاء" if language == 'ar' else "❌ Cancel",
            callback_data="cancel_user_proxy_request"
        ))
    if nav_row:
        keyboard.append(nav_row)
    
    return InlineKeyboardMarkup(keyboard) if keyboard else None


def create_services_management_keyboard(language: str = 'ar') -> InlineKeyboardMarkup:
    """
    إنشاء كيبورد إدارة الخدمات للآدمن
    Create services management keyboard for admin
    
    Args:
        language: لغة المستخدم ('ar' أو 'en')
    
    Returns:
        InlineKeyboardMarkup: كيبورد إدارة الخدمات
    """
    if language == 'ar':
        keyboard = [
            [InlineKeyboardButton("🎛️ فتح لوحة التحكم", callback_data="admin_open_miniapp")],
            [InlineKeyboardButton("📋 عرض الخدمات", callback_data="admin_view_services")],
            [InlineKeyboardButton("💰 إدارة الأسعار", callback_data="admin_manage_prices")],
            [InlineKeyboardButton("📤 تصدير الأزرار", callback_data="admin_export_buttons")],
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("🎛️ Open Dashboard", callback_data="admin_open_miniapp")],
            [InlineKeyboardButton("📋 View Services", callback_data="admin_view_services")],
            [InlineKeyboardButton("💰 Manage Prices", callback_data="admin_manage_prices")],
            [InlineKeyboardButton("📤 Export Buttons", callback_data="admin_export_buttons")],
        ]
    return InlineKeyboardMarkup(keyboard)


def create_admin_miniapp_keyboard(
    miniapp_url: str, 
    language: str = 'ar'
) -> InlineKeyboardMarkup:
    """
    إنشاء كيبورد فتح Mini App للآدمن
    Create admin Mini App keyboard
    
    Args:
        miniapp_url: رابط الـ Mini App
        language: لغة المستخدم ('ar' أو 'en')
    
    Returns:
        InlineKeyboardMarkup: كيبورد Mini App
    """
    from telegram import WebAppInfo
    keyboard = [[InlineKeyboardButton(
        text="🎛️ فتح لوحة الإدارة" if language == 'ar' else "🎛️ Open Dashboard",
        web_app=WebAppInfo(url=miniapp_url)
    )]]
    return InlineKeyboardMarkup(keyboard)
