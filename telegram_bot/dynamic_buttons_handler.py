#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================
معالج الأزرار الديناميكية - dynamic_buttons_handler.py
============================================
يتولى معالجة callbacks الأزرار الديناميكية
وتتبع مسار المستخدم في الطلب
============================================
"""

import logging
import sqlite3
import time
import json
from typing import Dict, List, Optional, Tuple, Any
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from dynamic_buttons import dynamic_buttons_manager
from bot_keyboards import (
    create_dynamic_root_keyboard,
    create_dynamic_children_keyboard,
    create_dynamic_quantity_keyboard,
    create_quantity_input_keyboard,
    create_services_management_keyboard,
    create_admin_miniapp_keyboard,
    get_page_separator_message
)
from config import DB_PATH, ADMIN_IDS
from bot_utils import db, generate_order_id

logger = logging.getLogger(__name__)

# متغيرات عالمية للآدمن النشطين
ACTIVE_ADMINS = set()
ADMIN_CHAT_ID = None


def update_admin_globals(active_admins=None, admin_chat_id=None):
    """تحديث المتغيرات العالمية للآدمن من bot.py"""
    global ACTIVE_ADMINS, ADMIN_CHAT_ID
    
    if active_admins is not None:
        if isinstance(active_admins, (list, set)):
            ACTIVE_ADMINS = set(active_admins)
        else:
            ACTIVE_ADMINS = set()
    
    if admin_chat_id is not None:
        ADMIN_CHAT_ID = admin_chat_id
    
    logger.info(f"Updated admin globals: ACTIVE_ADMINS={ACTIVE_ADMINS}, ADMIN_CHAT_ID={ADMIN_CHAT_ID}")


def get_back_callback_for_button(button: Dict, language: str = 'ar') -> Tuple[str, Optional[int]]:
    """
    حساب callback الرجوع الصحيح لزر معين
    يتخطى فواصل الصفحات للعودة للقائمة الأب الفعلية
    
    Returns:
        Tuple[str, Optional[int]]: (callback_data, parent_menu_id)
        - callback_data: بيانات الرجوع للاستخدام في الزر
        - parent_menu_id: معرف القائمة الأب (لاستخدامه مع get_user_page)
    """
    parent_id = button.get('parent_id')
    
    if not parent_id:
        return "dyn_root", None
    
    # جلب الزر الأب
    parent_button = dynamic_buttons_manager.get_button_by_id(parent_id, language)
    
    if not parent_button:
        return "dyn_root", None
    
    # إذا كان الأب فاصل صفحة، نذهب للجد (القائمة التي تحتوي على الفاصل)
    if parent_button.get('button_type') == 'page_separator':
        grandparent_id = parent_button.get('parent_id')
        if grandparent_id:
            return f"dyn_{grandparent_id}", grandparent_id
        else:
            return "dyn_root", None
    
    # الأب عادي، نرجع إليه
    return f"dyn_{parent_id}", parent_id


async def send_dynamic_order_admin_notification(
    context: ContextTypes.DEFAULT_TYPE,
    order_id: str,
    user_id: int,
    user_first_name: str,
    user_last_name: str,
    username: str,
    service_name: str,
    path_display: str,
    quantity: int,
    unit_price: float,
    total_price: float,
    button_key: str
) -> None:
    """إرسال إشعار للآدمن عن طلب جديد من الأزرار الديناميكية"""
    global ACTIVE_ADMINS, ADMIN_CHAT_ID
    
    try:
        # جمع معرفات الآدمن من جميع المصادر
        admin_ids = set()
        
        # إضافة الآدمن من ADMIN_IDS في config
        if ADMIN_IDS:
            admin_ids.update(ADMIN_IDS)
        
        # إضافة الآدمن النشطين
        if ACTIVE_ADMINS:
            admin_ids.update(ACTIVE_ADMINS)
        
        # إضافة آدمن الدردشة
        if ADMIN_CHAT_ID:
            admin_ids.add(ADMIN_CHAT_ID)
        
        # الحصول على الآدمن من قاعدة البيانات
        if not admin_ids:
            try:
                admin_query = "SELECT value FROM settings WHERE key = 'admin_chat_id'"
                admin_result = db.execute_query(admin_query)
                if admin_result and admin_result[0][0]:
                    admin_ids.add(int(admin_result[0][0]))
            except Exception as e:
                logger.error(f"Error getting admin from database: {e}")
        
        if not admin_ids:
            logger.warning(f"No admins available - cannot send notification for order: {order_id}")
            return
        
        # إنشاء رسالة الإشعار
        username_display = f"@{username}" if username else "غير محدد"
        full_name = f"{user_first_name} {user_last_name or ''}".strip()
        
        admin_message = f"""🔔 <b>طلب جديد - خدمة ديناميكية</b>

━━━━━━━━━━━━━━━
👤 <b>بيانات المستخدم:</b>
📛 الاسم: {full_name}
📱 اسم المستخدم: {username_display}
🆔 معرف المستخدم: <code>{user_id}</code>

━━━━━━━━━━━━━━━
📦 <b>تفاصيل الطلب:</b>
🔗 رقم الطلب: <code>{order_id}</code>
🛒 الخدمة: {service_name}
🔑 مفتاح الزر: <code>{button_key}</code>

📍 <b>مسار الطلب:</b>
{path_display if path_display else "القائمة الرئيسية"}

━━━━━━━━━━━━━━━
💰 <b>تفاصيل الدفع:</b>
🔢 الكمية: {quantity}
💵 سعر الوحدة: ${unit_price:.2f}
💰 الإجمالي: <b>${total_price:.2f}</b>
⏳ الدفع: سيتم الخصم عند إرسال البيانات

━━━━━━━━━━━━━━━
📊 الحالة: ⏳ <b>معلق - بانتظار المعالجة</b>
💡 <i>سيتم خصم الرصيد تلقائياً عند إرسال البروكسي للمستخدم</i>"""

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚡ معالجة الطلب", callback_data=f"process_{order_id}")],
            [InlineKeyboardButton("💬 محادثة المستخدم", url=f"tg://user?id={user_id}")]
        ])
        
        # إرسال الإشعار لجميع الآدمن وحفظ معرفات الرسائل
        sent_count = 0
        for admin_id in admin_ids:
            try:
                sent_message = await context.bot.send_message(
                    admin_id,
                    admin_message,
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
                sent_count += 1
                # حفظ معرف الرسالة لتحديثها لاحقاً عند إلغاء الطلب
                try:
                    db.save_order_admin_message(order_id, admin_id, sent_message.message_id)
                    logger.info(f"✅ Saved admin message ID {sent_message.message_id} for order: {order_id}")
                except Exception as save_err:
                    logger.error(f"Error saving admin message ID: {save_err}")
                logger.info(f"✅ Admin notification sent to {admin_id} for order: {order_id}")
            except Exception as e:
                logger.error(f"Error sending notification to admin {admin_id}: {e}")
        
        if sent_count > 0:
            logger.info(f"✅ Notification sent to {sent_count} admin(s) for dynamic order: {order_id}")
        else:
            logger.warning(f"⚠️ Failed to send notification to any admin for order: {order_id}")
            
    except Exception as e:
        logger.error(f"Error sending dynamic order admin notification: {e}")


def is_bot_running() -> bool:
    """التحقق من حالة تشغيل البوت"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # التحقق من حالة التشغيل
        cursor.execute(
            "SELECT setting_value FROM bot_settings WHERE setting_key = 'bot_running'"
        )
        result = cursor.fetchone()
        is_running = result[0] == 'true' if result else True
        
        # التحقق من مؤقت إعادة التشغيل
        if not is_running:
            cursor.execute(
                "SELECT setting_value FROM bot_settings WHERE setting_key = 'restart_at'"
            )
            restart_result = cursor.fetchone()
            if restart_result and restart_result[0] != 'null':
                restart_at = int(restart_result[0])
                current_time = int(time.time() * 1000)
                if current_time >= restart_at:
                    # انتهى وقت الإيقاف - إعادة التشغيل
                    cursor.execute(
                        "INSERT OR REPLACE INTO bot_settings (setting_key, setting_value, updated_at) VALUES ('bot_running', 'true', datetime('now'))"
                    )
                    cursor.execute(
                        "INSERT OR REPLACE INTO bot_settings (setting_key, setting_value, updated_at) VALUES ('restart_at', 'null', datetime('now'))"
                    )
                    conn.commit()
                    is_running = True
        
        conn.close()
        return is_running
    except Exception as e:
        logger.error(f"Error checking bot status: {e}")
        return True  # في حالة الخطأ، نفترض أن البوت يعمل


def is_user_admin(user_id: int) -> bool:
    """التحقق من أن المستخدم آدمن"""
    return user_id in ADMIN_IDS

USER_BUTTON_PATH: Dict[int, List[int]] = {}
USER_CURRENT_SERVICE: Dict[int, Dict] = {}
USER_PAGE_STATE: Dict[Tuple[int, int], int] = {}


def get_user_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """الحصول على لغة المستخدم من قاعدة البيانات"""
    user_id = update.effective_user.id
    try:
        result = db.execute_query("SELECT language FROM users WHERE user_id = ?", (user_id,))
        if result and result[0][0]:
            return result[0][0]
    except Exception as e:
        logger.error(f"Error getting user language: {e}")
    return 'ar'


def track_button_click(user_id: int, button_id: int, language: str = 'ar'):
    """
    تتبع نقرة الزر مع منع تكرار المسار
    
    عند النقر على زر:
    1. نتحقق من أن الزر الأب موجود في المسار
    2. إذا كان موجوداً، نقص المسار حتى الزر الأب ثم نضيف الزر الجديد
    3. هذا يمنع تكرار الأزرار الأبوية في المسار عند التنقل ذهاباً وإياباً
    """
    if user_id not in USER_BUTTON_PATH:
        USER_BUTTON_PATH[user_id] = []
    
    # الحصول على معلومات الزر لمعرفة الأب
    button = dynamic_buttons_manager.get_button_by_id(button_id, language)
    if not button:
        USER_BUTTON_PATH[user_id].append(button_id)
        return
    
    parent_id = button.get('parent_id')
    
    # إذا كان الزر له أب وهذا الأب موجود في المسار
    if parent_id and parent_id in USER_BUTTON_PATH[user_id]:
        # نبحث عن موقع الأب في المسار
        parent_index = USER_BUTTON_PATH[user_id].index(parent_id)
        # نقص المسار حتى الأب فقط (نزيل كل ما بعده)
        USER_BUTTON_PATH[user_id] = USER_BUTTON_PATH[user_id][:parent_index + 1]
    elif parent_id is None:
        # هذا زر جذري - نمسح المسار السابق
        USER_BUTTON_PATH[user_id] = []
    
    # نضيف الزر الجديد فقط إذا لم يكن موجوداً بالفعل في نهاية المسار
    if not USER_BUTTON_PATH[user_id] or USER_BUTTON_PATH[user_id][-1] != button_id:
        USER_BUTTON_PATH[user_id].append(button_id)


def get_button_path(user_id: int) -> List[int]:
    """الحصول على مسار الأزرار"""
    return USER_BUTTON_PATH.get(user_id, [])


def clear_button_path(user_id: int):
    """مسح مسار الأزرار"""
    if user_id in USER_BUTTON_PATH:
        del USER_BUTTON_PATH[user_id]
    if user_id in USER_CURRENT_SERVICE:
        del USER_CURRENT_SERVICE[user_id]
    clear_user_page_states(user_id)


def get_user_page(user_id: int, parent_id: int) -> int:
    """الحصول على رقم الصفحة الحالية للمستخدم لزر معين"""
    return USER_PAGE_STATE.get((user_id, parent_id), 0)


def set_user_page(user_id: int, parent_id: int, page: int):
    """تعيين رقم الصفحة الحالية للمستخدم لزر معين"""
    USER_PAGE_STATE[(user_id, parent_id)] = page


def clear_user_page_states(user_id: int):
    """مسح جميع حالات الصفحات للمستخدم"""
    keys_to_remove = [key for key in USER_PAGE_STATE if key[0] == user_id]
    for key in keys_to_remove:
        del USER_PAGE_STATE[key]


def get_path_display(user_id: int, language: str = 'ar') -> str:
    """الحصول على عرض المسار بتنسيق مرقم"""
    path = get_button_path(user_id)
    if not path:
        return ""
    
    path_lines = []
    for i, btn_id in enumerate(path, 1):
        btn = dynamic_buttons_manager.get_button_by_id(btn_id, language)
        if btn:
            path_lines.append(f"{i}. {btn['text']}")
    
    return "\n".join(path_lines)


async def handle_dynamic_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    معالجة نقرة على زر ديناميكي
    
    Returns:
        True إذا تم معالجة الـ callback، False إذا لم يكن callback ديناميكي
    """
    query = update.callback_query
    if not query or not query.data:
        return False
    
    callback_data = query.data
    user_id = update.effective_user.id
    language = get_user_language(update, context)
    
    # التحقق من حالة البوت - إذا كان متوقفاً والمستخدم ليس آدمن، نرفض الطلب
    if not is_bot_running() and not is_user_admin(user_id):
        await query.answer(
            "⏸️ البوت متوقف مؤقتاً، يرجى المحاولة لاحقاً" if language == 'ar' 
            else "⏸️ Bot is temporarily stopped, please try again later",
            show_alert=True
        )
        return True  # نعيد True لمنع معالجة الـ callback
    
    if callback_data.startswith("dyn_qty_"):
        return await handle_quantity_selection(update, context)
    
    if callback_data.startswith("dyn_back_"):
        return await handle_back_button(update, context)
    
    if callback_data.startswith("dyn_page_"):
        return await handle_page_navigation(update, context)
    
    if callback_data.startswith("dyn_root_page_"):
        return await handle_root_page_navigation(update, context)
    
    if callback_data == "noop":
        await query.answer()
        return True
    
    # معالجة الرجوع للقائمة الرئيسية الديناميكية
    if callback_data == "dyn_root":
        return await handle_dyn_root(update, context)
    
    if callback_data.startswith("dyn_"):
        return await handle_button_click(update, context)
    
    if callback_data == "admin_open_miniapp":
        return await handle_admin_open_miniapp(update, context)
    
    if callback_data == "admin_view_services":
        return await handle_admin_view_services(update, context)
    
    if callback_data == "admin_manage_prices":
        return await handle_admin_manage_prices(update, context)
    
    if callback_data == "admin_export_buttons":
        return await handle_admin_export_buttons(update, context)
    
    if callback_data.startswith("manage_services"):
        return await handle_manage_services(update, context)
    
    return False


async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """معالجة نقرة على زر عادي"""
    query = update.callback_query
    
    callback_data = query.data
    user_id = update.effective_user.id
    language = get_user_language(update, context)
    
    try:
        button_id = int(callback_data.replace("dyn_", ""))
    except ValueError:
        await query.answer()
        return False
    
    button = dynamic_buttons_manager.get_button_by_id(button_id, language)
    if not button:
        await query.answer()
        await query.edit_message_text("❌ الزر غير موجود" if language == 'ar' else "❌ Button not found")
        return True
    
    # التحقق من أن الزر مفعّل - إذا كان معطلاً نعرض رسالة التعطيل
    if not button.get('is_enabled', True):
        disabled_message = button.get('disabled_message', '')
        logger.info(f"🔴 Button {button_id} is DISABLED. disabled_message from DB: '{disabled_message}'")
        if not disabled_message:
            disabled_message = "⏸️ هذه الخدمة معطلة مؤقتاً" if language == 'ar' else "⏸️ This service is temporarily disabled"
        logger.info(f"🔴 Sending disabled message to user: '{disabled_message}'")
        await query.answer()  # الرد على الـ callback لمنع التحميل
        await query.message.reply_text(disabled_message)  # إرسال رسالة عادية
        logger.info(f"✅ Disabled message sent successfully")
        return True
    
    # الزر مفعّل - نستدعي answer ونكمل المعالجة
    await query.answer()
    
    button_type = button.get('button_type', 'menu')
    
    # معالجة زر الرجوع - لا نتتبعه في المسار
    if button_type == 'back':
        # مسح حالة انتظار الكمية
        if 'awaiting_quantity' in context.user_data:
            del context.user_data['awaiting_quantity']
        
        # مسح الخدمة الحالية
        if user_id in USER_CURRENT_SERVICE:
            del USER_CURRENT_SERVICE[user_id]
        
        # الحصول على سلوك الرجوع
        back_behavior = button.get('back_behavior', 'step')
        
        if back_behavior == 'root':
            # الرجوع للقائمة الرئيسية ومسح المسار بالكامل
            clear_button_path(user_id)
            keyboard = create_dynamic_root_keyboard(language, page=0)
            message = "🌐 اختر نوع الخدمة:" if language == 'ar' else "🌐 Choose service type:"
            await query.edit_message_text(message, reply_markup=keyboard)
            return True
        
        # السلوك الافتراضي "step" - الرجوع خطوة واحدة
        # زر الرجوع هو ابن للقائمة الحالية، لذا يجب الذهاب للجد (أب القائمة الحالية)
        parent_id = button.get('parent_id')  # هذا هو القائمة الحالية التي يوجد فيها زر الرجوع
        
        if parent_id:
            parent_button = dynamic_buttons_manager.get_button_by_id(parent_id, language)
            if parent_button:
                # الحصول على جد زر الرجوع (أب القائمة الحالية)
                grandparent_id = parent_button.get('parent_id')
                
                # إزالة القائمة الحالية من المسار
                if user_id in USER_BUTTON_PATH and USER_BUTTON_PATH[user_id]:
                    USER_BUTTON_PATH[user_id].pop()
                
                if grandparent_id:
                    # الذهاب للجد وعرض أبناءه
                    grandparent_button = dynamic_buttons_manager.get_button_by_id(grandparent_id, language)
                    if grandparent_button:
                        great_grandparent_back, _ = get_back_callback_for_button(grandparent_button, language)
                        page = get_user_page(user_id, grandparent_id)
                        keyboard = create_dynamic_children_keyboard(grandparent_id, language, great_grandparent_back, page)
                        message = grandparent_button.get('message') or ("اختر من القائمة:" if language == 'ar' else "Choose from the list:")
                        
                        path_display = get_path_display(user_id, language)
                        if path_display:
                            path_header = "📍 تسلسل الطلب:\n" if language == 'ar' else "📍 Order Sequence:\n"
                            message = f"{path_header}{path_display}\n\n{message}"
                        
                        await query.edit_message_text(message, reply_markup=keyboard)
                        return True
                
                # لا يوجد جد - العودة للقائمة الرئيسية
                clear_user_page_states(user_id)
                clear_button_path(user_id)
                keyboard = create_dynamic_root_keyboard(language, page=0)
                message = "🌐 اختر نوع الخدمة:" if language == 'ar' else "🌐 Choose service type:"
                await query.edit_message_text(message, reply_markup=keyboard)
                return True
        
        # لا يوجد أب - العودة للقائمة الرئيسية
        clear_user_page_states(user_id)
        clear_button_path(user_id)
        keyboard = create_dynamic_root_keyboard(language, page=0)
        message = "🌐 اختر نوع الخدمة:" if language == 'ar' else "🌐 Choose service type:"
        await query.edit_message_text(message, reply_markup=keyboard)
        return True
    
    # معالجة زر الإلغاء - لا نتتبعه في المسار ونمسح كل المسار
    if button_type == 'cancel':
        # مسح حالة انتظار الكمية
        if 'awaiting_quantity' in context.user_data:
            del context.user_data['awaiting_quantity']
        
        # مسح المسار بالكامل
        clear_button_path(user_id)
        
        # رسالة الإلغاء
        if language == 'ar':
            cancel_message = "❌ تم إلغاء الطلب\n\n🔙 يمكنك البدء من جديد في أي وقت"
        else:
            cancel_message = "❌ Order cancelled\n\n🔙 You can start again anytime"
        
        keyboard = create_dynamic_root_keyboard(language, page=0)
        await query.edit_message_text(cancel_message, reply_markup=keyboard)
        return True
    
    # فقط للأزرار العادية - تتبع النقرة في المسار
    track_button_click(user_id, button_id, language)
    
    # فاصل الصفحة ليس زراً قابلاً للنقر - يجب تجاهله والعودة للقائمة الأب
    if button_type == 'page_separator':
        # إزالة فاصل الصفحة من المسار لأنه ليس اختياراً حقيقياً
        if user_id in USER_BUTTON_PATH and USER_BUTTON_PATH[user_id]:
            USER_BUTTON_PATH[user_id].pop()
        
        parent_id = button.get('parent_id')
        if parent_id:
            # العودة للقائمة الأب
            parent_button = dynamic_buttons_manager.get_button_by_id(parent_id, language)
            if parent_button:
                grandparent_id = parent_button.get('parent_id')
                back_callback = f"dyn_{grandparent_id}" if grandparent_id else "dyn_root"
                page = get_user_page(user_id, parent_id)
                keyboard = create_dynamic_children_keyboard(parent_id, language, back_callback, page)
                message = parent_button.get('message') or ("اختر من القائمة:" if language == 'ar' else "Choose from the list:")
                await query.edit_message_text(message, reply_markup=keyboard)
                return True
        # إذا لم يكن له أب، العودة للقائمة الرئيسية
        keyboard = create_dynamic_root_keyboard(language, page=0)
        message = "🌐 اختر نوع الخدمة:" if language == 'ar' else "🌐 Choose service type:"
        await query.edit_message_text(message, reply_markup=keyboard)
        return True
    
    # معالجة زر الرابط (link) - فتح رابط خارجي
    if button_type == 'link':
        link_url = button.get('message', '') or button.get('message_ar', '')
        logger.info(f"🔗 Link button clicked: button={button}, link_url='{link_url}'")
        
        if link_url:
            # إنشاء كيبورد مع زر الرابط وزر الرجوع
            back_callback, _ = get_back_callback_for_button(button, language)
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 " + button.get('text', 'فتح الرابط'), url=link_url)],
                [InlineKeyboardButton("🔙 رجوع" if language == 'ar' else "🔙 Back", callback_data=back_callback)]
            ])
            
            message_text = "🔗 اضغط على الزر أدناه لفتح الرابط:" if language == 'ar' else "🔗 Click the button below to open the link:"
            await query.edit_message_text(message_text, reply_markup=keyboard)
        else:
            # لا يوجد رابط - إظهار رسالة خطأ
            back_callback, _ = get_back_callback_for_button(button, language)
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع" if language == 'ar' else "🔙 Back", callback_data=back_callback)]
            ])
            error_msg = "⚠️ لم يتم تحديد رابط لهذا الزر" if language == 'ar' else "⚠️ No link specified for this button"
            await query.edit_message_text(error_msg, reply_markup=keyboard)
        return True
    
    # معالجة زر نوع "رسالة فقط" (message) - بدون إنشاء طلب إلا إذا كان خدمة مدفوعة
    if button_type == 'message' and not button['is_service']:
        # إرسال الرسالة فقط بدون إنشاء طلب
        message_text = button.get('message', '')
        if not message_text:
            message_text = button.get('text', '')
        
        # إنشاء كيبورد للرجوع - مع تخطي فواصل الصفحات
        back_callback, _ = get_back_callback_for_button(button, language)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع" if language == 'ar' else "🔙 Back", callback_data=back_callback)]
        ])
        
        await query.edit_message_text(message_text, reply_markup=keyboard, parse_mode='HTML')
        return True
    
    if button['is_service']:
        USER_CURRENT_SERVICE[user_id] = button
        
        if button['ask_quantity']:
            # الذهاب مباشرة للإدخال اليدوي بدلاً من عرض أزرار الكمية
            context.user_data['awaiting_quantity'] = button_id
            
            path_display = get_path_display(user_id, language)
            
            if language == 'ar':
                service_info = "📍 تسلسل الطلب:\n" + path_display + "\n\n" if path_display else ""
                service_info += f"🛒 الخدمة: {button['text']}\n"
                service_info += f"💰 السعر للوحدة: {button['price']:.2f}$\n\n"
                message = service_info + "🔢 أدخل الكمية المطلوبة (رقم من 1 إلى 99):"
            else:
                service_info = "📍 Order Sequence:\n" + path_display + "\n\n" if path_display else ""
                service_info += f"🛒 Service: {button['text']}\n"
                service_info += f"💰 Unit Price: ${button['price']:.2f}\n\n"
                message = service_info + "🔢 Enter the desired quantity (number from 1 to 99):"
            
            # إنشاء كيبورد مع أزرار الرجوع والإلغاء حسب الإعدادات
            show_back = button.get('show_back_on_quantity', True)
            show_cancel = button.get('show_cancel_on_quantity', True)
            keyboard = create_quantity_input_keyboard(button_id, language, show_back, show_cancel)
            
            await query.edit_message_text(message, reply_markup=keyboard)
        else:
            await process_service_order(update, context, button, button['default_quantity'])
        
        return True
    
    else:
        # جلب جميع الأزرار الفرعية (المفعلة والمعطلة) - التصفية ستتم في الكيبورد
        children = dynamic_buttons_manager.get_children(button_id, language, enabled_only=False)
        # تصفية الأزرار المخفية فقط
        children = [btn for btn in children if not btn.get('is_hidden', False)]
        
        if not children:
            await query.edit_message_text(
                "📭 لا توجد خيارات متاحة حالياً" if language == 'ar' else "📭 No options available currently"
            )
            return True
        
        # حساب callback الرجوع مع تخطي فواصل الصفحات
        back_callback, _ = get_back_callback_for_button(button, language)
        
        set_user_page(user_id, button_id, 0)
        keyboard = create_dynamic_children_keyboard(button_id, language, back_callback, page=0)
        
        # محاولة الحصول على رسالة فاصل الصفحة للصفحة الأولى (الأصغر ترتيباً)
        separator_message = get_page_separator_message(button_id, language, page=0)
        
        if separator_message:
            # استخدام رسالة فاصل الصفحة
            message = separator_message
        else:
            # استخدام رسالة الزر الأب أو رسالة افتراضية
            message = button['message'] if button['message'] else (
                "اختر من القائمة:" if language == 'ar' else "Choose from the list:"
            )
        
        path_display = get_path_display(user_id, language)
        if path_display:
            path_header = "📍 تسلسل الطلب:\n" if language == 'ar' else "📍 Order Sequence:\n"
            message = f"{path_header}{path_display}\n\n{message}"
        
        await query.edit_message_text(message, reply_markup=keyboard)
        return True


async def handle_quantity_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """معالجة اختيار الكمية"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    user_id = update.effective_user.id
    language = get_user_language(update, context)
    
    parts = callback_data.replace("dyn_qty_", "").split("_")
    if len(parts) < 2:
        return False
    
    try:
        button_id = int(parts[0])
        quantity_str = parts[1]
    except ValueError:
        return False
    
    if quantity_str == "manual":
        context.user_data['awaiting_quantity'] = button_id
        await query.edit_message_text(
            "🔢 أدخل الكمية المطلوبة (رقم من 1 إلى 99):" if language == 'ar' 
            else "🔢 Enter the desired quantity (number from 1 to 99):"
        )
        return True
    
    try:
        quantity = int(quantity_str)
    except ValueError:
        return False
    
    button = dynamic_buttons_manager.get_button_by_id(button_id, language)
    if not button:
        return False
    
    await process_service_order(update, context, button, quantity)
    return True


async def handle_back_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """معالجة زر الرجوع"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    user_id = update.effective_user.id
    language = get_user_language(update, context)
    
    # مسح حالة انتظار الكمية عند الضغط على رجوع
    if 'awaiting_quantity' in context.user_data:
        del context.user_data['awaiting_quantity']
    
    # مسح الخدمة الحالية
    if user_id in USER_CURRENT_SERVICE:
        del USER_CURRENT_SERVICE[user_id]
    
    try:
        button_id = int(callback_data.replace("dyn_back_", ""))
    except ValueError:
        return False
    
    button = dynamic_buttons_manager.get_button_by_id(button_id, language)
    if not button:
        return False
    
    # الحصول على سلوك الرجوع (step = خطوة واحدة، root = القائمة الرئيسية)
    back_behavior = button.get('back_behavior', 'step')
    
    # إذا كان السلوك "root"، الرجوع مباشرة للقائمة الرئيسية
    if back_behavior == 'root':
        # مسح مسار المستخدم بالكامل وحالات الصفحات
        if user_id in USER_BUTTON_PATH:
            USER_BUTTON_PATH[user_id] = []
        clear_user_page_states(user_id)
        
        keyboard = create_dynamic_root_keyboard(language, page=0)
        message = "🌐 اختر نوع الخدمة:" if language == 'ar' else "🌐 Choose service type:"
        await query.edit_message_text(message, reply_markup=keyboard)
        return True
    
    # السلوك الافتراضي "step" - الرجوع خطوة واحدة للخلف
    if user_id in USER_BUTTON_PATH and USER_BUTTON_PATH[user_id]:
        USER_BUTTON_PATH[user_id].pop()
    
    # استخدام الدالة المساعدة للحصول على callback الرجوع الصحيح
    back_callback, target_parent_id = get_back_callback_for_button(button, language)
    
    if target_parent_id:
        parent_button = dynamic_buttons_manager.get_button_by_id(target_parent_id, language)
        if parent_button:
            # حساب callback الرجوع للقائمة الأب
            grandparent_back, _ = get_back_callback_for_button(parent_button, language)
            
            page = get_user_page(user_id, target_parent_id)
            keyboard = create_dynamic_children_keyboard(target_parent_id, language, grandparent_back, page)
            
            # محاولة الحصول على رسالة فاصل الصفحة
            separator_message = get_page_separator_message(target_parent_id, language, page)
            
            if separator_message:
                message = separator_message
            else:
                message = parent_button['message'] if parent_button['message'] else (
                    "اختر من القائمة:" if language == 'ar' else "Choose from the list:"
                )
            
            await query.edit_message_text(message, reply_markup=keyboard)
            return True
    
    clear_user_page_states(user_id)
    keyboard = create_dynamic_root_keyboard(language, page=0)
    message = "🌐 اختر نوع الخدمة:" if language == 'ar' else "🌐 Choose service type:"
    await query.edit_message_text(message, reply_markup=keyboard)
    return True


async def handle_dyn_root(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """معالجة الرجوع للقائمة الرئيسية الديناميكية (dyn_root)"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(update, context)
    
    # مسح حالة انتظار الكمية عند الضغط على رجوع
    if 'awaiting_quantity' in context.user_data:
        del context.user_data['awaiting_quantity']
    
    # مسح الخدمة الحالية ومسار الأزرار وحالات الصفحات
    if user_id in USER_CURRENT_SERVICE:
        del USER_CURRENT_SERVICE[user_id]
    if user_id in USER_BUTTON_PATH:
        USER_BUTTON_PATH[user_id] = []
    clear_user_page_states(user_id)
    
    # الحصول على صفحة القائمة الرئيسية المحفوظة
    root_page = get_user_page(user_id, 0)  # استخدام 0 كمعرف للقائمة الرئيسية
    
    # عرض القائمة الرئيسية الديناميكية
    keyboard = create_dynamic_root_keyboard(language, page=root_page)
    message = "🌐 اختر نوع الخدمة:" if language == 'ar' else "🌐 Choose service type:"
    await query.edit_message_text(message, reply_markup=keyboard)
    return True


async def handle_root_page_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """معالجة التنقل بين صفحات القائمة الرئيسية"""
    query = update.callback_query
    
    try:
        await query.answer()
        
        callback_data = query.data
        user_id = update.effective_user.id
        language = get_user_language(update, context)
        
        try:
            page = int(callback_data.replace("dyn_root_page_", ""))
        except ValueError:
            page = 0
        
        # التأكد من أن رقم الصفحة صحيح (غير سالب)
        page = max(0, page)
        
        # حفظ رقم الصفحة الحالية للقائمة الرئيسية (نستخدم 0 كمعرف)
        set_user_page(user_id, 0, page)
        
        keyboard = create_dynamic_root_keyboard(language, page=page)
        message = "🌐 اختر نوع الخدمة:" if language == 'ar' else "🌐 Choose service type:"
        await query.edit_message_text(message, reply_markup=keyboard)
        return True
    except Exception as e:
        logger.error(f"Error in handle_root_page_navigation: {e}")
        try:
            await query.answer("حدث خطأ، حاول مرة أخرى" if language == 'ar' else "Error occurred, try again", show_alert=True)
        except:
            pass
        return True


async def handle_page_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """معالجة التنقل بين صفحات الأزرار"""
    query = update.callback_query
    language = 'ar'
    
    try:
        await query.answer()
        
        callback_data = query.data
        user_id = update.effective_user.id
        language = get_user_language(update, context)
        
        try:
            parts = callback_data.replace("dyn_page_", "").split("_")
            if len(parts) < 2:
                # العودة للقائمة الرئيسية في حالة بيانات غير صحيحة
                keyboard = create_dynamic_root_keyboard(language, page=0)
                message = "🌐 اختر نوع الخدمة:" if language == 'ar' else "🌐 Choose service type:"
                await query.edit_message_text(message, reply_markup=keyboard)
                return True
            
            parent_id = int(parts[0])
            page = int(parts[1])
        except ValueError:
            # العودة للقائمة الرئيسية في حالة خطأ
            keyboard = create_dynamic_root_keyboard(language, page=0)
            message = "🌐 اختر نوع الخدمة:" if language == 'ar' else "🌐 Choose service type:"
            await query.edit_message_text(message, reply_markup=keyboard)
            return True
        
        # التأكد من أن رقم الصفحة صحيح (غير سالب)
        page = max(0, page)
        
        set_user_page(user_id, parent_id, page)
        
        parent_button = dynamic_buttons_manager.get_button_by_id(parent_id, language)
        if not parent_button:
            # العودة للقائمة الرئيسية إذا لم يتم العثور على الزر
            keyboard = create_dynamic_root_keyboard(language, page=0)
            message = "🌐 اختر نوع الخدمة:" if language == 'ar' else "🌐 Choose service type:"
            await query.edit_message_text(message, reply_markup=keyboard)
            return True
        
        # حساب callback الرجوع مع تخطي فواصل الصفحات
        back_callback, _ = get_back_callback_for_button(parent_button, language)
        
        keyboard = create_dynamic_children_keyboard(parent_id, language, back_callback, page)
        
        # محاولة الحصول على رسالة فاصل الصفحة للصفحة الحالية
        separator_message = get_page_separator_message(parent_id, language, page)
        
        if separator_message:
            # استخدام رسالة فاصل الصفحة
            message = separator_message
        else:
            # استخدام رسالة الزر الأب أو رسالة افتراضية
            message = parent_button['message'] if parent_button['message'] else (
                "اختر من القائمة:" if language == 'ar' else "Choose from the list:"
            )
        
        path_display = get_path_display(user_id, language)
        if path_display:
            path_header = "📍 تسلسل الطلب:\n" if language == 'ar' else "📍 Order Sequence:\n"
            message = f"{path_header}{path_display}\n\n{message}"
        
        await query.edit_message_text(message, reply_markup=keyboard)
        return True
    except Exception as e:
        logger.error(f"Error in handle_page_navigation: {e}")
        try:
            await query.answer("حدث خطأ، حاول مرة أخرى" if language == 'ar' else "Error occurred, try again", show_alert=True)
        except:
            pass
        return True


def save_dynamic_order(user_id: int, order_data: Dict, language: str) -> bool:
    """
    حفظ طلب الخدمة الديناميكية في قاعدة البيانات
    مع تسجيل مسار الأزرار الكامل للآدمن
    """
    try:
        order_id = order_data['order_id']
        service_name = order_data['service_name']
        path_display = order_data['path']
        quantity = order_data['quantity']
        unit_price = order_data['unit_price']
        total_price = order_data['total_price']
        button_id = order_data['button_id']
        button_key = order_data['button_key']
        button_path = order_data.get('button_path', [])
        
        # تحويل مسار الأزرار إلى JSON للحفظ
        button_path_json = json.dumps(button_path, ensure_ascii=False)
        
        # إنشاء وصف مفصل للطلب يظهر للآدمن
        order_details = {
            'service_name': service_name,
            'path': path_display,
            'button_id': button_id,
            'button_key': button_key,
            'button_path': button_path,
            'unit_price': unit_price,
            'quantity': quantity,
            'total_price': total_price,
            'language': language
        }
        order_details_json = json.dumps(order_details, ensure_ascii=False)
        
        # حفظ الطلب في جدول orders
        # proxy_type = 'dynamic_service' للتمييز
        # country = مسار الأزرار
        # state = اسم الخدمة
        # payment_method = 'balance'
        # payment_proof = تفاصيل الطلب JSON
        
        query = '''
            INSERT INTO orders (
                id, user_id, proxy_type, country, state, 
                payment_method, payment_amount, quantity, 
                status, payment_proof, static_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        db.execute_query(query, (
            order_id,
            user_id,
            'dynamic_service',  # نوع الطلب
            path_display,       # المسار الكامل
            service_name,       # اسم الخدمة
            'balance',          # طريقة الدفع
            total_price,        # المبلغ الإجمالي
            str(quantity),      # الكمية
            'pending',          # الحالة
            order_details_json, # تفاصيل الطلب كاملة
            button_key          # مفتاح الزر
        ))
        
        logger.info(f"Dynamic order saved: {order_id} for user {user_id} - Service: {service_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving dynamic order: {e}")
        return False


async def process_service_order(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE, 
    button: Dict, 
    quantity: int
):
    """
    معالجة طلب الخدمة - آلية اقتطاع الرصيد الآمنة:
    
    المرحلة 1: التحقق من كفاية الرصيد (هنا)
    المرحلة 2: إنشاء الطلب بدون اقتطاع (هنا)
    المرحلة 3: اقتطاع الرصيد عند إرسال الأدمن للبروكسي (في bot.py)
    
    هذا يضمن:
    - حق المستخدم: لا يتم اقتطاع الرصيد إلا عند استلام الخدمة
    - حق الأدمن: التحقق المسبق من كفاية الرصيد قبل إنشاء الطلب
    - منع الاقتطاع المزدوج
    """
    query = update.callback_query
    user_id = update.effective_user.id
    language = get_user_language(update, context)
    
    path_display = get_path_display(user_id, language)
    total_price = button['price'] * quantity
    
    # ============================================
    # المرحلة 1: التحقق من كفاية الرصيد
    # ============================================
    user_balance = db.get_user_balance(user_id)
    current_balance = user_balance['total_balance']
    
    if current_balance < total_price:
        if language == 'ar':
            insufficient_message = f"""❌ رصيد غير كافي

💰 التكلفة الإجمالية: ${total_price:.2f}
📊 الكمية: {quantity}
💵 سعر الوحدة: ${button['price']:.2f}
💳 رصيدك الحالي: ${current_balance:.2f}
📉 المبلغ الناقص: ${(total_price - current_balance):.2f}

💡 يرجى شحن رصيدك أولاً من القائمة الرئيسية"""
        else:
            insufficient_message = f"""❌ Insufficient Balance

💰 Total Cost: ${total_price:.2f}
📊 Quantity: {quantity}
💵 Unit Price: ${button['price']:.2f}
💳 Your Current Balance: ${current_balance:.2f}
📉 Amount Needed: ${(total_price - current_balance):.2f}

💡 Please recharge your balance first from the main menu"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 شحن الرصيد" if language == 'ar' else "💰 Recharge Balance", callback_data="recharge_balance")],
            [InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية" if language == 'ar' else "🔙 Back to Main Menu", callback_data="cancel_user_proxy_request")]
        ])
        await query.edit_message_text(insufficient_message, reply_markup=keyboard)
        return
    
    # ============================================
    # المرحلة 2: إنشاء الطلب بدون اقتطاع الرصيد
    # الرصيد سيتم اقتطاعه عند إرسال الأدمن للبروكسي
    # ============================================
    order_id = generate_order_id()
    
    # حفظ بيانات الطلب
    order_data = {
        'order_id': order_id,
        'button_id': button['id'],
        'button_key': button['button_key'],
        'service_name': button['text'],
        'path': path_display,
        'quantity': quantity,
        'unit_price': button['price'],
        'total_price': total_price,
        'button_path': get_button_path(user_id).copy()
    }
    context.user_data['pending_order'] = order_data
    
    # إنشاء الطلب في قاعدة البيانات (بدون اقتطاع الرصيد)
    try:
        save_dynamic_order(user_id, order_data, language)
        logger.info(f"✅ Dynamic order created (balance NOT deducted yet): {order_id} - Total: ${total_price:.2f}")
    except Exception as e:
        logger.error(f"Error saving dynamic order: {e}")
        error_msg = "❌ حدث خطأ في إنشاء الطلب. يرجى المحاولة مرة أخرى." if language == 'ar' else "❌ Error creating order. Please try again."
        await query.edit_message_text(error_msg)
        return
    
    # إرسال إشعار للآدمن عن الطلب الجديد
    try:
        user = update.effective_user
        await send_dynamic_order_admin_notification(
            context=context,
            order_id=order_id,
            user_id=user_id,
            user_first_name=user.first_name or "",
            user_last_name=user.last_name or "",
            username=user.username or "",
            service_name=button['text'],
            path_display=path_display,
            quantity=quantity,
            unit_price=button['price'],
            total_price=total_price,
            button_key=button['button_key']
        )
        logger.info(f"Admin notification sent for dynamic order: {order_id}")
    except Exception as e:
        logger.error(f"Error sending admin notification for dynamic order: {e}")
    
    # رسالة النجاح للمستخدم (مختصرة)
    if language == 'ar':
        path_section = f"📍 {path_display}\n" if path_display else ""
        success_message = f"""✅ تم إنشاء الطلب بنجاح!

📋 رقم الطلب: <code>{order_id}</code>
{path_section}🛒 {button['text']} × {quantity}
💵 الإجمالي: {total_price:.2f}$

⏳ سيتم معالجة طلبك قريباً.
💳 سيتم اقتطاع الرصيد عند نجاح الطلب واستلامك الخدمة."""
    else:
        path_section = f"📍 {path_display}\n" if path_display else ""
        success_message = f"""✅ Order Created Successfully!

📋 Order ID: <code>{order_id}</code>
{path_section}🛒 {button['text']} × {quantity}
💵 Total: ${total_price:.2f}

⏳ Your order will be processed soon.
💳 Balance will be deducted upon order success and service delivery."""
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 القائمة الرئيسية" if language == 'ar' else "🏠 Main Menu", callback_data="cancel_user_proxy_request")]
    ])
    
    await query.edit_message_text(success_message, reply_markup=keyboard, parse_mode='HTML')


async def handle_manage_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """معالجة إدارة الخدمات"""
    query = update.callback_query
    await query.answer()
    
    language = get_user_language(update, context)
    keyboard = create_services_management_keyboard(language)
    
    message = "🎛️ إدارة الخدمات والأزرار:" if language == 'ar' else "🎛️ Manage Services & Buttons:"
    await query.edit_message_text(message, reply_markup=keyboard)
    return True


async def handle_admin_open_miniapp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """فتح Mini App للآدمن"""
    query = update.callback_query
    await query.answer()
    
    language = get_user_language(update, context)
    
    from config import MINIAPP_URL
    miniapp_url = MINIAPP_URL
    
    keyboard = create_admin_miniapp_keyboard(miniapp_url, language)
    
    message = (
        "🎛️ اضغط على الزر أدناه لفتح لوحة إدارة الأزرار:" if language == 'ar'
        else "🎛️ Click the button below to open the button management panel:"
    )
    
    await query.edit_message_text(message, reply_markup=keyboard)
    return True


async def handle_admin_view_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """عرض جميع الخدمات للآدمن"""
    query = update.callback_query
    await query.answer()
    
    language = get_user_language(update, context)
    services = dynamic_buttons_manager.get_all_services(language, enabled_only=False)
    
    if not services:
        message = "📭 لا توجد خدمات مسجلة" if language == 'ar' else "📭 No services registered"
        await query.edit_message_text(message)
        return True
    
    if language == 'ar':
        message = "📊 **جميع الخدمات:**\n━━━━━━━━━━━━━━━\n\n"
    else:
        message = "📊 **All Services:**\n━━━━━━━━━━━━━━━\n\n"
    
    for service in services:
        status = "✅" if service['is_enabled'] else "❌"
        path_names = [p['text'] for p in service['path']]
        path_str = " → ".join(path_names)
        
        message += f"{status} **{service['text']}**\n"
        message += f"   📍 {path_str}\n"
        message += f"   💰 ${service['price']:.2f}\n"
        message += f"   🔢 كمية: {'سؤال' if service['ask_quantity'] else service['default_quantity']}\n\n"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 رجوع" if language == 'ar' else "🔙 Back", callback_data="manage_services")]
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
    return True


async def handle_admin_manage_prices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """إدارة الأسعار للآدمن"""
    query = update.callback_query
    await query.answer()
    
    language = get_user_language(update, context)
    services = dynamic_buttons_manager.get_all_services(language, enabled_only=False)
    
    if not services:
        message = "📭 لا توجد خدمات" if language == 'ar' else "📭 No services"
        await query.edit_message_text(message)
        return True
    
    keyboard = []
    for service in services:
        keyboard.append([
            InlineKeyboardButton(
                f"{service['text']} - ${service['price']:.2f}",
                callback_data=f"edit_price_{service['id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            "🔙 رجوع" if language == 'ar' else "🔙 Back",
            callback_data="manage_services"
        )
    ])
    
    message = "💲 اختر الخدمة لتعديل السعر:" if language == 'ar' else "💲 Select service to edit price:"
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    return True


async def handle_admin_export_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """تصدير الأزرار للآدمن"""
    query = update.callback_query
    await query.answer()
    
    language = get_user_language(update, context)
    
    try:
        export_data = dynamic_buttons_manager.export_tree()
        
        filename = "buttons_export.json"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(export_data)
        
        await query.message.reply_document(
            document=open(filename, 'rb'),
            filename=filename,
            caption="📥 تصدير الأزرار" if language == 'ar' else "📥 Buttons Export"
        )
        
        import os
        os.remove(filename)
        
    except Exception as e:
        logger.error(f"Export error: {e}")
        await query.edit_message_text(
            "❌ فشل التصدير" if language == 'ar' else "❌ Export failed"
        )
    
    return True


async def show_dynamic_services_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة الخدمات الديناميكية"""
    user_id = update.effective_user.id
    language = get_user_language(update, context)
    
    clear_button_path(user_id)
    
    keyboard = create_dynamic_root_keyboard(language, page=0)
    message = "🌐 اختر نوع الخدمة:" if language == 'ar' else "🌐 Choose service type:"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(message, reply_markup=keyboard)
    else:
        await update.message.reply_text(message, reply_markup=keyboard)


async def handle_manual_quantity_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """معالجة الإدخال اليدوي للكمية"""
    if 'awaiting_quantity' not in context.user_data:
        return False
    
    text = update.message.text.strip()
    language = get_user_language(update, context)
    button_id = context.user_data.get('awaiting_quantity')
    
    try:
        quantity = int(text)
        if quantity < 1 or quantity > 99:
            raise ValueError("Invalid quantity")
    except ValueError:
        # الحصول على إعدادات الزر لعرض أزرار الرجوع/الإلغاء
        button = dynamic_buttons_manager.get_button_by_id(button_id, language) if button_id else None
        show_back = button.get('show_back_on_quantity', True) if button else True
        show_cancel = button.get('show_cancel_on_quantity', True) if button else True
        keyboard = create_quantity_input_keyboard(button_id, language, show_back, show_cancel)
        
        await update.message.reply_text(
            "❌ الرجاء إدخال رقم صحيح بين 1 و 99" if language == 'ar'
            else "❌ Please enter a valid number between 1 and 99",
            reply_markup=keyboard
        )
        return True
    
    button_id = context.user_data.pop('awaiting_quantity')
    button = dynamic_buttons_manager.get_button_by_id(button_id, language)
    
    if not button:
        await update.message.reply_text(
            "❌ الخدمة غير موجودة" if language == 'ar' else "❌ Service not found"
        )
        return True
    
    class FakeQuery:
        def __init__(self, message):
            self.message = message
            self.data = ""
        
        async def answer(self):
            pass
        
        async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
            await self.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    
    class FakeUpdate:
        def __init__(self, update):
            self.effective_user = update.effective_user
            self.callback_query = FakeQuery(update.message)
    
    fake_update = FakeUpdate(update)
    await process_service_order(fake_update, context, button, quantity)
    return True


async def show_dynamic_menu_by_key(update: Update, context: ContextTypes.DEFAULT_TYPE, button_key: str) -> bool:
    """
    عرض قائمة الأزرار الديناميكية بناءً على مفتاح الزر
    يُستخدم من القائمة الرئيسية لعرض أزرار ستاتيك أو سوكس
    
    Args:
        update: كائن التحديث
        context: سياق المحادثة
        button_key: مفتاح الزر (مثل 'static_proxy' أو 'socks_proxy')
    
    Returns:
        True إذا تم العرض بنجاح، False إذا لم يُوجد الزر
    """
    user_id = update.effective_user.id
    # الحصول على لغة المستخدم من قاعدة البيانات (ليس من context.user_data)
    language = get_user_language(update, context)
    
    # الحصول على الزر الرئيسي بالمفتاح
    button = dynamic_buttons_manager.get_button_by_key(button_key, language)
    if not button:
        await update.message.reply_text(
            "❌ الخدمة غير متاحة حالياً" if language == 'ar' else "❌ Service not available currently"
        )
        return False
    
    # التحقق من أن الزر مفعّل
    if not button.get('is_enabled', True):
        # استخدام رسالة الإيقاف المخصصة من الزر إذا كانت موجودة
        disabled_message = button.get('disabled_message', '')
        if not disabled_message:
            disabled_message = "⏸️ هذه الخدمة معطلة مؤقتاً" if language == 'ar' else "⏸️ This service is temporarily disabled"
        await update.message.reply_text(disabled_message)
        return False
    
    # مسح المسار السابق وبدء مسار جديد
    clear_button_path(user_id)
    track_button_click(user_id, button['id'], language)
    
    # الحصول على الأزرار الفرعية (المفعلة والمعطلة)
    children = dynamic_buttons_manager.get_children(button['id'], language, enabled_only=False)
    # تصفية الأزرار المخفية فقط
    children = [btn for btn in children if not btn.get('is_hidden', False)]
    
    if not children:
        await update.message.reply_text(
            "📭 لا توجد خيارات متاحة حالياً" if language == 'ar' else "📭 No options available currently"
        )
        return True
    
    # استخدام دالة إنشاء الكيبورد التي تتعامل مع فواصل الصفحات بشكل صحيح
    set_user_page(user_id, button['id'], 0)
    reply_markup = create_dynamic_children_keyboard(
        button['id'], 
        language, 
        back_callback="cancel_user_proxy_request",
        page=0
    )
    
    # محاولة الحصول على رسالة فاصل الصفحة
    separator_message = get_page_separator_message(button['id'], language, page=0)
    
    if separator_message:
        message = separator_message
    else:
        # عرض الرسالة مع الأزرار
        message = button.get('message') or button['text']
        if not message or message == button['text']:
            message = "اختر من القائمة:" if language == 'ar' else "Choose from the list:"
    
    await update.message.reply_text(message, reply_markup=reply_markup)
    
    # حفظ نوع البروكسي في سياق المستخدم
    if button_key == 'static_proxy':
        context.user_data['proxy_type'] = 'static'
    elif button_key == 'socks_proxy':
        context.user_data['proxy_type'] = 'socks'
    
    return True
