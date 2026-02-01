#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت تيليجرام لبيع البروكسيات
Simple Proxy Bot - Telegram Bot for Selling Proxies
"""

import os
import asyncio
import logging
import sqlite3
import json
import random
import string
import pandas as pd
import io
import csv
import openpyxl
import atexit
import platform
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pytz
import re

# استيراد fcntl فقط في أنظمة Unix/Linux
try:
    import fcntl
    FCNTL_AVAILABLE = True
except ImportError:
    FCNTL_AVAILABLE = False

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    WebAppInfo
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    InlineQueryHandler,
    filters,
    ContextTypes
)
from telegram.constants import ParseMode

# نظام الأسئلة الشائعة FAQ System
from config import (
    handle_faq_callback, show_faq_menu, init_faq_database, insert_faq_content,
    Config, DATABASE_FILE, MESSAGES, ADMIN_IDS,
    STATIC_COUNTRIES, SOCKS_COUNTRIES,
    US_STATES_SOCKS, US_STATES, UK_STATES,
    US_STATES_STATIC_VERIZON, US_STATES_STATIC_CROCKER,
    US_STATES_STATIC_LEVEL3, US_STATES_STATIC_FRONTIER,
    US_STATES_STATIC_RESIDENTIAL, US_STATES_STATIC_ISP,
    UK_STATES_STATIC_RESIDENTIAL, UK_RESIDENTIAL_ISP_SERVICES,
    US_RESIDENTIAL_ISP_SERVICES, ENGLAND_STATIC_NTT,
    RESIDENTIAL_4_COUNTRIES, STATIC_WEEKLY_LOCATIONS, STATIC_DAILY_LOCATIONS,
    DE_STATES, FR_STATES, IT_STATES, IN_STATES,
    US_STATE_AREA_CODES, POPULAR_US_STATES, US_STATE_NAMES_AR,
    get_country_name, get_state_name, get_message)

# استيراد الأدوات المساعدة وإدارة قاعدة البيانات
from bot_utils import (
    DatabaseManager, db,
    escape_markdown_v2, escape_html, escape_markdown,
    get_syria_time, get_syria_time_str, log_with_syria_time,
    get_res4_price, generate_order_id,
    track_user_click, is_user_banned, apply_progressive_ban,
    insert_or_update_ban, lift_user_ban, reset_user_clicks,
    get_residential_service_status, set_residential_service_status,
    get_current_price, get_static_prices, get_socks_prices,
    get_detailed_proxy_type, get_proxy_price,
    load_saved_prices, update_static_messages, update_socks_messages,
    get_bot_channel, set_bot_channel, is_forced_subscription_enabled,
    set_forced_subscription, update_user_subscription_status
)

# استيراد معالجات الأدمن
from bot_admin import msg_edit_conv_handler

# استيراد الكيبوردات الموحدة
from bot_keyboards import (
    create_main_user_keyboard, create_balance_keyboard,
    create_profile_keyboard, create_admin_keyboard, create_back_button,
    create_confirmation_keyboard, create_language_selection_keyboard,
    get_remove_keyboard
)

# استيراد معالج الأزرار الديناميكية
from dynamic_buttons_handler import show_dynamic_menu_by_key, handle_dynamic_button, handle_manual_quantity_input, is_bot_running, is_user_admin, clear_button_path, update_admin_globals

# استيراد دوال الزبائن
from bot_customer import (
    get_referral_amount, get_referral_percentage,
    handle_referrals, handle_balance_menu, handle_my_balance,
    handle_recharge_balance, handle_balance_referrals,
    handle_back_to_main_menu, handle_recharge_amount_input,
    handle_profile_menu, handle_profile_info, handle_support,
    handle_back_to_profile,
    handle_settings, handle_language_change,
    show_services_message, show_exchange_rate_message,
    handle_free_proxy_trial, handle_use_free_proxy,
    handle_buy_numbers, handle_nonvoip_user_callbacks,
    SERVICES_MESSAGE, EXCHANGE_RATE_MESSAGE
)

# متغيرات عالمية للحظر
TEMP_BANNED_USERS = {}

# تكوين اللوجينج (يجب أن يكون قبل استيراد الوحدات الأخرى)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# استيراد وحدة NonVoipUsNumber
try:
    from non_voip_unified import (
        NonVoipAPI, NonVoipDB, format_order_for_user, calculate_sale_price,
        handle_nonvoip_inline_query, handle_country_selection_callback, handle_buy_callback,
        handle_confirm_buy_callback, handle_cancel_order_callback, handle_activate_number_callback,
        handle_manual_check_callback,
        handle_sync_last3_callback,
        nonvoip_main_menu, nonvoip_select_type, nonvoip_confirm_order, nonvoip_process_order,
        nonvoip_my_numbers, nonvoip_sync_numbers, nonvoip_history, nonvoip_view_number_messages,
        nonvoip_renew_number, nonvoip_process_renew,
        nonvoip_admin_menu, nonvoip_admin_balance, nonvoip_admin_products,
        nonvoip_admin_all_orders, NONVOIP_MESSAGES, get_user_language,
        check_notification_sent, mark_notification_sent, cleanup_old_history_numbers
    )
    NONVOIP_AVAILABLE = True
except ImportError as e:
    NONVOIP_AVAILABLE = False
    logger.warning(f"وحدة non_voip_unified غير متاحة: {e}")

# استيراد ملف الإعدادات
try:
    from config import Config
    CONFIG_AVAILABLE = True
except ImportError as e:
    CONFIG_AVAILABLE = False
    logger.warning(f"ملف config.py غير متاح: {e}")

# وحدة 9Proxy معطلة مؤقتاً - تم استبدالها بـ PremSocks
# try:
#     from nineproxy_service import (
#         NineProxyAPI, NineProxyDB, nineproxy_db,
#         handle_9proxy_callback, nineproxy_admin_menu,
#         handle_9proxy_admin_callback, handle_9proxy_admin_input,
#         get_message as get_9proxy_message, get_country_flag
#     )
#     NINEPROXY_AVAILABLE = True
#     logger.info("✅ تم تحميل وحدة 9Proxy بنجاح")
# except ImportError as e:
#     NINEPROXY_AVAILABLE = False
#     logger.warning(f"وحدة nineproxy_service غير متاحة: {e}")
NINEPROXY_AVAILABLE = False

# استيراد وحدة PremSocks - سوكس يومي (الإصدار القديم - معطل)
PREMSOCKS_AVAILABLE = False

# استيراد وحدة Luxury Support - سوكس يومي (البديل الجديد)
try:
    from luxury_service import (
        LuxuryAPI, LuxuryDB, luxury_db,
        handle_luxury_callback, luxury_admin_menu, luxury_main_menu,
        handle_luxury_admin_callback, handle_luxury_admin_input,
        handle_luxury_inline_query, handle_luxury_inline_selection,
        get_luxury_message, get_country_flag_luxury
    )
    LUXURY_AVAILABLE = True
    logger.info("✅ تم تحميل وحدة Luxury Support بنجاح")
except ImportError as e:
    LUXURY_AVAILABLE = False
    logger.warning(f"وحدة luxury_service غير متاحة: {e}")

# استيراد وحدة SMSPool - خدمة أرقام SMS (بديل NonVoip)
try:
    from smspool_service import (
        SMSPoolAPI, SMSPoolDB, smspool_db,
        smspool_main_menu, handle_smspool_callback,
        smspool_admin_menu, handle_smspool_admin_callback,
        handle_admin_api_key_input, handle_admin_margin_input,
        get_smspool_message, get_user_language as get_smspool_user_language
    )
    SMSPOOL_AVAILABLE = True
    logger.info("✅ تم تحميل وحدة SMSPool بنجاح")
except ImportError as e:
    SMSPOOL_AVAILABLE = False
    logger.warning(f"وحدة smspool_service غير متاحة: {e}")

if NONVOIP_AVAILABLE:
    from non_voip_unified import get_service_icon, get_display_service_name
    
    class SMSMonitorService:
        """خدمة مراقبة الرسائل النصية - تعمل داخل البوت باستخدام JobQueue"""
        
        def __init__(self):
            """تهيئة خدمة المراقبة"""
            self.api = NonVoipAPI()
            self.db = NonVoipDB()
            logger.info("تم تهيئة خدمة مراقبة الرسائل")
        
        async def check_order_sms(self, context: ContextTypes.DEFAULT_TYPE, order: Dict) -> bool:
            """
            التحقق من وصول رسالة لطلب معين
            
            Args:
                order: بيانات الطلب من قاعدة البيانات
                
            Returns:
                True إذا وصلت رسالة جديدة
            """
            try:
                order_id = order.get('order_id')
                service = order.get('service')
                number = order.get('number')
                user_id = order.get('user_id')
                message_id = order.get('message_id')
                sms_sent = order.get('sms_sent', 0)
                
                if not number or not service:
                    logger.warning(f"الطلب {order_id} لا يحتوي على رقم أو خدمة")
                    return False
                
                if sms_sent:
                    logger.debug(f"تم إرسال الرسالة مسبقاً للطلب {order_id}")
                    return False
                
                result = self.api.get_sms(service=service, number=number, order_id=order_id)
                
                if result.get('status') == 'success' and result.get('sms'):
                    sms_text = result.get('sms')
                    pin_code = result.get('pin')
                    order_type = order.get('type', 'short_term')
                    
                    logger.info(f"✅ وصلت رسالة للطلب {order_id} - الرقم: {number}")
                    
                    self.db.update_order_sms(order_id=order_id, sms=sms_text, pin=pin_code)
                    
                    # إنشاء hash من المحتوى الثابت فقط (بدون تاريخ)
                    stable_content = f"{order_id}|{service}|{number}|{sms_text}|{pin_code or ''}"
                    
                    # التحقق من عدم إرسال نفس الرسالة سابقاً
                    if not check_notification_sent(order_id, 'sms', stable_content):
                        message_text = self._format_sms_message(order, sms_text, pin_code)
                        
                        if message_id:
                            await self._update_purchase_message(context, user_id, message_id, order, sms_text, pin_code)
                        
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=message_text,
                            parse_mode=ParseMode.MARKDOWN
                        )
                        
                        # تسجيل إرسال الرسالة بالمحتوى الثابت
                        mark_notification_sent(order_id, user_id, 'sms', stable_content)
                        logger.info(f"تم إرسال الرسالة للمستخدم {user_id}")
                    else:
                        logger.info(f"تم تجاهل إرسال رسالة مكررة للطلب {order_id}")
                    
                    conn = sqlite3.connect(self.db.db_file)
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE nonvoip_orders 
                        SET sms_sent = 1, updated_at = CURRENT_TIMESTAMP
                        WHERE order_id = ?
                    """, (order_id,))
                    conn.commit()
                    
                    # إخفاء الرقم من "My Numbers" للأرقام قصيرة الأمد (15 دقيقة) - مع الحفاظ على السجل في History
                    if order_type == 'short_term':
                        cursor.execute("""
                            UPDATE nonvoip_orders 
                            SET visible_in_my_numbers = 0, status = 'completed', updated_at = CURRENT_TIMESTAMP
                            WHERE order_id = ?
                        """, (order_id,))
                        conn.commit()
                        logger.info(f"✅ تم إخفاء الرقم {order_id} من My Numbers (short_term - تم استلام الرسالة، محفوظ في History)")
                    
                    conn.close()
                    
                    return True
                    
                return False
                
            except Exception as e:
                logger.error(f"خطأ في التحقق من الرسائل للطلب {order.get('order_id')}: {e}")
                return False
        
        def _format_sms_message(self, order: Dict, sms_text: str, pin_code: Optional[str]) -> str:
            """تنسيق رسالة SMS للإرسال للمستخدم مع دعم اللغات"""
            number = order.get('number', 'غير متوفر')
            service = order.get('service', 'غير متوفر')
            order_id = order.get('order_id', 'غير متوفر')
            user_id = order.get('user_id')
            
            icon = get_service_icon(service)
            display_service = get_display_service_name(service)
            
            # الحصول على لغة المستخدم
            conn = sqlite3.connect(self.db.db_file)
            lang = get_user_language(user_id, conn)
            conn.close()
            
            if lang == 'ar':
                message = f"✅ *وصلت رسالة جديدة!*\n\n"
                message += f"{icon} *الخدمة:* {display_service}\n"
                message += f"📱 *الرقم:* `{number}`\n"
                message += f"🆔 *رقم الطلب:* `{order_id}`\n\n"
                message += f"💬 *الرسالة:*\n`{sms_text}`\n"
                if pin_code:
                    message += f"\n🔐 *رمز التحقق:* `{pin_code}`"
                message += f"\n\n⏰ *الوقت:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            else:
                message = f"✅ *New message received!*\n\n"
                message += f"{icon} *Service:* {display_service}\n"
                message += f"📱 *Number:* `{number}`\n"
                message += f"🆔 *Order ID:* `{order_id}`\n\n"
                message += f"💬 *Message:*\n`{sms_text}`\n"
                if pin_code:
                    message += f"\n🔐 *Verification Code:* `{pin_code}`"
                message += f"\n\n⏰ *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            return message
        
        async def _update_purchase_message(self, context: ContextTypes.DEFAULT_TYPE,
                                          user_id: int, message_id: int, 
                                          order: Dict, sms_text: str, pin_code: Optional[str]) -> bool:
            """تحديث رسالة الشراء الأصلية بعد وصول الرسالة مع دعم اللغات"""
            try:
                number = order.get('number', 'غير متوفر')
                service = order.get('service', 'غير متوفر')
                order_id = order.get('order_id')
                expiration = order.get('expiration', 0)
                expires_at = order.get('expires_at', '')
                
                icon = get_service_icon(service)
                display_service = get_display_service_name(service)
                
                # الحصول على لغة المستخدم
                conn = sqlite3.connect(self.db.db_file)
                lang = get_user_language(user_id, conn)
                conn.close()
                
                if lang == 'ar':
                    updated_message = f"✅ *تم استلام الرسالة بنجاح!*\n\n"
                    updated_message += f"{icon} *الخدمة:* {display_service}\n"
                    updated_message += f"📱 *الرقم:* `{number}`\n"
                    updated_message += f"🆔 *رقم الطلب:* `{order_id}`\n\n"
                    updated_message += f"💬 *الرسالة:*\n`{sms_text}`\n"
                    if pin_code:
                        updated_message += f"\n🔐 *رمز التحقق:* `{pin_code}`"
                    if expires_at:
                        updated_message += f"\n📅 *صالح حتى:* {expires_at}"
                    updated_message += f"\n\n⏰ *وقت الاستلام:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    updated_message += f"\n\n🎉 *تم استهلاك الرقم بنجاح!*"
                    button_text = "📨 عرض الرسائل"
                else:
                    updated_message = f"✅ *Message received successfully!*\n\n"
                    updated_message += f"{icon} *Service:* {display_service}\n"
                    updated_message += f"📱 *Number:* `{number}`\n"
                    updated_message += f"🆔 *Order ID:* `{order_id}`\n\n"
                    updated_message += f"💬 *Message:*\n`{sms_text}`\n"
                    if pin_code:
                        updated_message += f"\n🔐 *Verification Code:* `{pin_code}`"
                    if expires_at:
                        updated_message += f"\n📅 *Valid until:* {expires_at}"
                    updated_message += f"\n\n⏰ *Received at:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    updated_message += f"\n\n🎉 *Number successfully used!*"
                    button_text = "📨 View Messages"
                
                keyboard = []
                keyboard.append([InlineKeyboardButton(
                    button_text,
                    callback_data=f"nv_view_messages_{order_id}"
                )])
                
                reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
                
                await context.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=message_id,
                    text=updated_message,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
                
                logger.info(f"تم تحديث رسالة الشراء للطلب {order_id}")
                return True
                
            except Exception as e:
                logger.error(f"خطأ في تحديث رسالة الشراء: {e}")
                return False
        
        async def check_expired_numbers(self, context: ContextTypes.DEFAULT_TYPE):
            """التحقق من الأرقام المنتهية صلاحيتها وإرسال إشعارات مع استرداد تلقائي للكريديت"""
            try:
                conn = sqlite3.connect(self.db.db_file)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM nonvoip_orders 
                    WHERE status IN ('pending', 'reserved', 'active', 'delivered')
                    AND expires_at IS NOT NULL
                    AND datetime(expires_at) <= datetime('now')
                    AND refunded = 0
                    AND status NOT IN ('cancelled')
                    AND (expired_notified = 0 OR expired_notified IS NULL)
                """)
                
                expired_orders = [dict(row) for row in cursor.fetchall()]
                conn.close()
                
                for order in expired_orders:
                    user_id = order.get('user_id')
                    order_id = order.get('order_id')
                    number = order.get('number')
                    service = order.get('service')
                    sms_received = order.get('sms_received')
                    sms_sent = order.get('sms_sent', 0)
                    refunded = order.get('refunded', 0)
                    order_type = order.get('type', 'short_term')
                    sale_price = order.get('sale_price', 0.0)
                    
                    conn = sqlite3.connect(self.db.db_file)
                    lang = get_user_language(user_id, conn)
                    cursor = conn.cursor()
                    
                    # التحقق من الاسترداد المسبق لمنع الاسترداد المزدوج
                    if refunded:
                        logger.info(f"⚠️ تم تجاهل الطلب {order_id} - تم استرداد الرصيد مسبقاً (منع الاسترداد المزدوج)")
                        from non_voip_unified import log_refund_operation
                        log_refund_operation(
                            order_id=order_id,
                            user_id=user_id,
                            operation_type='auto_expiry_skipped',
                            refund_amount=0.0,
                            reason='Already refunded - preventing double refund',
                            status='skipped',
                            details=f'Order already has refunded=1, Type: {order_type}'
                        )
                        # إخفاء من My Numbers مع الحفاظ على السجل في History
                        cursor.execute("""
                            UPDATE nonvoip_orders 
                            SET visible_in_my_numbers = 0, updated_at = CURRENT_TIMESTAMP
                            WHERE order_id = ?
                        """, (order_id,))
                        conn.commit()
                        logger.info(f"✅ تم إخفاء الرقم {order_id} من My Numbers (مكرر - محفوظ في History)")
                        conn.close()
                        continue
                    
                    # منع إرسال رسالة انتهاء الصلاحية للأرقام التي وصلت رسالتها
                    # ولأرقام 15 دقيقة: عدم استرداد الرصيد إذا وصلت رسالة
                    if sms_received or sms_sent:
                        logger.info(f"تم تجاهل إرسال إشعار انتهاء صلاحية للطلب {order_id} - تم استلام الرسالة")
                        from non_voip_unified import log_refund_operation
                        log_refund_operation(
                            order_id=order_id,
                            user_id=user_id,
                            operation_type='auto_expiry_no_refund',
                            refund_amount=0.0,
                            reason='Message received - no refund on expiry',
                            status='skipped',
                            details=f'SMS received/sent, Type: {order_type}, Service: {service}'
                        )
                        # ✅ نقل جميع الأرقام التي استلمت رسالة للـ History (إخفاء من My Numbers)
                        # ينطبق على جميع الأنواع: short_term, long_term, 3days
                        cursor.execute("""
                            UPDATE nonvoip_orders 
                            SET status = 'expired', expired_notified = 1, visible_in_my_numbers = 0, updated_at = CURRENT_TIMESTAMP
                            WHERE order_id = ?
                        """, (order_id,))
                        conn.commit()
                        logger.info(f"✅ تم نقل الرقم {order_id} للـ History - Type: {order_type}, استلم رسالة، محفوظ في History")
                        
                        # تنظيف History: حذف الأرقام الأقدم والاحتفاظ بآخر 5 فقط
                        cleanup_old_history_numbers(user_id, self.db, keep_last=5)
                        
                        conn.close()
                        continue
                    
                    # إنشاء hash من المحتوى الثابت لمنع التكرار
                    stable_content = f"{order_id}|{service}|{number}|expired|{sms_received or ''}|{sale_price}"
                    
                    # التحقق من عدم إرسال نفس الإشعار سابقاً
                    if check_notification_sent(order_id, 'expiry', stable_content):
                        logger.info(f"تم تجاهل إرسال إشعار انتهاء صلاحية مكرر للطلب {order_id}")
                        conn.close()
                        continue
                    
                    icon = get_service_icon(service)
                    display_service = get_display_service_name(service)
                    
                    # رسائل مختلفة حسب نوع الرقم واللغة
                    if order_type == 'short_term':
                        # أرقام 15 دقيقة - استرداد تلقائي للكريديت
                        if lang == 'ar':
                            message = f"⚠️ *انتهت صلاحية الرقم بدون استلام رسالة*\n\n"
                            message += f"{icon} *الخدمة:* {display_service}\n"
                            message += f"📱 *الرقم:* `{number}`\n"
                            message += f"🆔 *رقم الطلب:* `{order_id}`\n\n"
                            message += f"❌ لم تصل أي رسالة خلال فترة الصلاحية\n"
                            message += f"💰 *تم استرداد:* {sale_price} كريديت\n"
                            message += f"💡 يمكنك المحاولة مرة أخرى برقم جديد"
                        else:
                            message = f"⚠️ *Number expired without receiving message*\n\n"
                            message += f"{icon} *Service:* {display_service}\n"
                            message += f"📱 *Number:* `{number}`\n"
                            message += f"🆔 *Order ID:* `{order_id}`\n\n"
                            message += f"❌ No message received during validity period\n"
                            message += f"💰 *Refunded:* {sale_price} credits\n"
                            message += f"💡 You can try again with a new number"
                    else:
                        # أرقام 3 أيام و 30 يوم - رسالة مختلفة بدون "يمكنك المحاولة مرة أخرى"
                        if lang == 'ar':
                            message = f"⏰ *انتهت صلاحية الرقم*\n\n"
                            message += f"{icon} *الخدمة:* {display_service}\n"
                            message += f"📱 *الرقم:* `{number}`\n"
                            message += f"🆔 *رقم الطلب:* `{order_id}`\n\n"
                            message += f"📅 انتهت فترة الصلاحية للرقم"
                        else:
                            message = f"⏰ *Number expired*\n\n"
                            message += f"{icon} *Service:* {display_service}\n"
                            message += f"📱 *Number:* `{number}`\n"
                            message += f"🆔 *Order ID:* `{order_id}`\n\n"
                            message += f"📅 Validity period has ended"
                    
                    try:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=message,
                            parse_mode=ParseMode.MARKDOWN
                        )
                        
                        # تسجيل إرسال الإشعار بالمحتوى الثابت
                        mark_notification_sent(order_id, user_id, 'expiry', stable_content)
                        logger.info(f"تم إرسال إشعار انتهاء الصلاحية للطلب {order_id}")
                        
                        cursor = conn.cursor()
                        
                        # استرداد الكريديت تلقائياً للأرقام التي لم تستلم رسالة
                        if not sms_received:
                            cursor.execute("UPDATE users SET credits_balance = credits_balance + ? WHERE user_id = ?", 
                                         (sale_price, user_id))
                            logger.info(f"💰 تم استرداد {sale_price} كريديت للمستخدم {user_id} - الطلب {order_id}")
                            
                            # تسجيل عملية الاسترداد التلقائي في اللوغز
                            from non_voip_unified import log_refund_operation
                            log_refund_operation(
                                order_id=order_id,
                                user_id=user_id,
                                operation_type='auto_expiry_refund',
                                refund_amount=sale_price,
                                reason=f'Number expired without receiving message - Type: {order_type}',
                                status='success',
                                details=f'Service: {service}, Number: {number}, No SMS received'
                            )
                        
                        cursor.execute("""
                            UPDATE nonvoip_orders 
                            SET status = 'expired', refunded = 1, expired_notified = 1, visible_in_my_numbers = 0, updated_at = CURRENT_TIMESTAMP
                            WHERE order_id = ?
                        """, (order_id,))
                        conn.commit()
                        logger.info(f"✅ تم إخفاء الرقم {order_id} من My Numbers (منتهي - محفوظ في History)")
                        
                        # تنظيف History: حذف الأرقام الأقدم والاحتفاظ بآخر 5 فقط
                        cleanup_old_history_numbers(user_id, self.db, keep_last=5)
                        
                        conn.close()
                        
                    except Exception as e:
                        logger.error(f"خطأ في إرسال إشعار انتهاء الصلاحية: {e}")
                        conn.close()
                        
            except Exception as e:
                logger.error(f"خطأ في التحقق من الأرقام المنتهية: {e}")
        
        async def poll_pending_sms(self, context: ContextTypes.DEFAULT_TYPE):
            """وظيفة JobQueue: التحقق من الرسائل المعلقة (فقط الأرقام النشطة غير منتهية الصلاحية)"""
            try:
                # استخدام get_current_orders بدلاً من get_active_orders لتصفية الأرقام المنتهية
                current_orders = self.db.get_current_orders()
                
                pending_orders = []
                for order in current_orders:
                    # تخطي الطلبات التي استلمت SMS
                    if order.get('sms_received') or order.get('sms_sent'):
                        continue
                    
                    order_type = order.get('type', 'short_term')
                    
                    # أرقام 15 دقيقة: فحص تلقائي دائماً
                    if order_type == 'short_term':
                        pending_orders.append(order)
                    # أرقام 3 أيام و 30 يوم: فحص فقط إذا كانت مفعلة
                    elif order_type in ['3days', 'long_term']:
                        activation_status = order.get('activation_status', 'inactive')
                        if activation_status == 'active':
                            pending_orders.append(order)
                        else:
                            logger.debug(f"⏸ تخطي فحص الطلب {order.get('order_id')} - نوع {order_type} غير مفعل")
                    else:
                        # أنواع أخرى: فحص تلقائي
                        pending_orders.append(order)
                
                if pending_orders:
                    logger.info(f"📊 عدد الطلبات المعلقة للفحص: {len(pending_orders)}")
                    
                    for order in pending_orders:
                        await self.check_order_sms(context, order)
                        
            except Exception as e:
                logger.error(f"خطأ في التحقق من الرسائل المعلقة: {e}")
        
        async def poll_expired_numbers(self, context: ContextTypes.DEFAULT_TYPE):
            """وظيفة JobQueue: التحقق من الأرقام المنتهية"""
            try:
                await self.check_expired_numbers(context)
            except Exception as e:
                logger.error(f"خطأ في التحقق من الأرقام المنتهية: {e}")


    async def job_poll_sms(context: ContextTypes.DEFAULT_TYPE):
        """Job: التحقق الدوري من الرسائل"""
        service = SMSMonitorService()
        await service.poll_pending_sms(context)


    async def job_check_expired(context: ContextTypes.DEFAULT_TYPE):
        """Job: التحقق الدوري من الأرقام المنتهية"""
        service = SMSMonitorService()
        await service.poll_expired_numbers(context)

    async def job_check_activation_expiry(context: ContextTypes.DEFAULT_TYPE):
        """Job: التحقق الدوري من التفعيلات المنتهية"""
        from non_voip_unified import check_expired_activations
        await check_expired_activations(context)


    async def job_check_nonvoip_balance(context: ContextTypes.DEFAULT_TYPE):
        """Job: فحص رصيد NonVoip وإرسال إشعارات تدريجية للآدمن"""
        from non_voip_unified import check_nonvoip_balance_and_notify
        await check_nonvoip_balance_and_notify(context)
# إضافة معالج للأخطاء العامة
import asyncio
import time
from typing import Dict, Set
from functools import wraps

# تم إزالة timeout handler لتحسين الأداء والاستقرار

# الإعدادات الثابتة
if CONFIG_AVAILABLE:
    ADMIN_PASSWORD = Config.ADMIN_PASSWORD
    TOKEN = Config.TOKEN
    DATABASE_FILE = Config.DATABASE_FILE
else:
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "sohilSOHIL")
    TOKEN = os.getenv("TOKEN", "7751227560:AAHe4nZzMtI4JFJqx0HK84DiBfxztW5Y_jY")
    DATABASE_FILE = os.getenv("DATABASE_FILE", "proxy_bot.db")
ACTIVE_ADMINS = []  # قائمة معرفات الآدمن النشطين المسجلين دخولهم حالياً
ADMIN_CHAT_ID = None  # معرف دردشة الأدمن - يتم تحميله من قاعدة البيانات

# حالات المحادثة
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
    # حالات جديدة لإدارة المستخدمين المتقدمة
    BAN_USER_CONFIRM, UNBAN_USER_CONFIRM, REMOVE_TEMP_BAN_CONFIRM,
    ADD_POINTS_AMOUNT, ADD_POINTS_MESSAGE, SUBTRACT_POINTS_AMOUNT, SUBTRACT_POINTS_MESSAGE,
    ADD_REFERRAL_USERNAME, DELETE_REFERRAL_SELECT, RESET_REFERRAL_CONFIRM,
    SINGLE_USER_BROADCAST_MESSAGE, MANAGE_USER_BANS,
    # حالات جديدة لإدارة الأرقام
    NONVOIP_MENU, NONVOIP_SELECT_TYPE, NONVOIP_SELECT_STATE, NONVOIP_SELECT_PRODUCT, NONVOIP_CONFIRM_ORDER,
    NONVOIP_HISTORY, NONVOIP_CONFIRM_RENEW,
    NONVOIP_ADMIN_MENU, NONVOIP_VIEW_BALANCE, NONVOIP_VIEW_PRODUCTS, NONVOIP_VIEW_ORDERS,
    SET_PRICE_NONVOIP,
    # حالات جديدة لنظام الشروط والأحكام
    EDIT_TERMS_MESSAGE_AR, EDIT_TERMS_MESSAGE_EN

) = range(74)

# ===== دالة مساعدة لـ MarkdownV2 Escape =====
async def send_warning_message(context, chat_id: int):
    """إرسال رسالة التحذير للمستخدم مع إيقاف مؤقت"""
    import asyncio
    
    try:
        # إرسال الرسالة الأولى
        await context.bot.send_message(chat_id=chat_id, text="⚠️")
        
        # انتظار قصير
        await asyncio.sleep(1)
        
        # إرسال الرسالة الثانية
        await context.bot.send_message(
            chat_id=chat_id, 
            text="⚠️ لقد تم الاشتباه بنشاط تخريبي، الرجاء الحذر قد يؤدي الاستمرار في هذا النهج إلى حظرك"
        )
        
        # إيقاف الاستجابة 10 ثواني
        await asyncio.sleep(10)
        
    except Exception as e:
        logger.error(f"Error sending warning message to {chat_id}: {e}")

async def send_ban_message(context, chat_id: int, ban_type: str):
    """إرسال رسالة الحظر حسب النوع"""
    import asyncio
    
    try:
        if ban_type == "ban_10_min":
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ عذراً تم حظرك 10 دقائق، نعتذر في حال وجود خطأ ما، الرجاء مراجعة الدعم @Static_support"
            )
            
        elif ban_type == "ban_2_hours":
            # إرسال الرسالة الأولى
            await context.bot.send_message(chat_id=chat_id, text="🤨")
            
            # انتظار قصير
            await asyncio.sleep(1)
            
            # إرسال الرسالة الثانية
            await context.bot.send_message(
                chat_id=chat_id,
                text="ما بك ؟ 🤨\nهل تتقصد الإزعاج و التخريب؟...حسناً...إليك ساعتي حظر 😊"
            )
            
        elif ban_type == "ban_24_hours":
            await context.bot.send_message(
                chat_id=chat_id,
                text="عذرا عزيزي المستخدم تم تحديد نشاطك على إنه إزعاج مقصود، سنضطر لحظرك 24 ساعة...نهاراً سعيداً 👍"
            )
            
    except Exception as e:
        logger.error(f"Error sending ban message ({ban_type}) to {chat_id}: {e}")

async def notify_admin_ban(context, user_id: int, ban_type: str, username: str = ""):
    """إخبار الآدمن النشطين عن حظر مستخدم"""
    try:
        global ACTIVE_ADMINS
        
        # إذا لم يكن هناك آدمن نشطين، لا ترسل إشعارات
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
        
        # إرسال الإشعار لجميع الآدمن النشطين
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
        
        # إذا لم يكن هناك آدمن نشطين، لا ترسل إشعارات
        if not ACTIVE_ADMINS:
            return
            
        user_text = f"@{username}" if username else f"ID: {user_id}"
        message = f"✅ تم رفع الحظر عن المستخدم {user_text}"
        
        # إرسال الإشعار لجميع الآدمن النشطين
        for admin_id in ACTIVE_ADMINS:
            try:
                if hasattr(context_or_app, 'bot'):
                    # إذا كان context
                    await context_or_app.bot.send_message(
                        chat_id=admin_id,
                        text=message
                    )
                else:
                    # إذا كان application
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
            # إذا كان context
            await context_or_app.bot.send_message(
                chat_id=chat_id,
                text="✅ تم رفع الحظر عنك، يمكنك الآن استخدام البوت بشكل طبيعي"
            )
        else:
            # إذا كان application
            await context_or_app.bot.send_message(
                chat_id=chat_id,
                text="✅ تم رفع الحظر عنك، يمكنك الآن استخدام البوت بشكل طبيعي"
            )
    except Exception as e:
        logger.error(f"Error notifying user about unban: {e}")

async def check_user_ban_and_track_clicks(update, context) -> bool:
    """
    فحص حظر المستخدم وتتبع النقرات المتكررة
    إرجاع True إذا كان المستخدم محظوراً أو تم تطبيق إجراء (يجب إيقاف المعالجة)
    إرجاع False إذا كان بإمكان المتابعة بشكل طبيعي
    """
    try:
        user = update.effective_user
        if not user:
            return False
            
        user_id = user.id
        username = user.username or ""
        
        # فحص ما إذا كان المستخدم محظوراً حالياً
        is_banned_status, ban_level, ban_end_time = is_user_banned(user_id)
        
        if is_banned_status:
            # المستخدم محظور، لا نرد عليه
            logger.info(f"User {user_id} is banned until {ban_end_time}")
            return True
        
        # تتبع النقرات المتكررة
        click_count, elapsed_time = track_user_click(user_id)
        
        # فحص النقرات المتكررة (15-17 نقرة متتالية)
        if 15 <= click_count <= 17:
            ban_action = apply_progressive_ban(user_id, click_count)
            
            if ban_action == "warning":
                # إرسال تحذير
                await send_warning_message(context, user_id)
                await notify_admin_ban(context, user_id, "warning", username)
                return True  # إيقاف المعالجة
                
            elif ban_action == "ban_10_min":
                # حظر 10 دقائق
                await send_ban_message(context, user_id, "ban_10_min")
                await notify_admin_ban(context, user_id, "ban_10_min", username)
                return True  # إيقاف المعالجة
                
            elif ban_action == "ban_2_hours":
                # حظر ساعتين
                await send_ban_message(context, user_id, "ban_2_hours")
                await notify_admin_ban(context, user_id, "ban_2_hours", username)
                return True  # إيقاف المعالجة
                
            elif ban_action == "ban_24_hours":
                # حظر 24 ساعة
                await send_ban_message(context, user_id, "ban_24_hours")
                await notify_admin_ban(context, user_id, "ban_24_hours", username)
                return True  # إيقاف المعالجة
        
        # إعادة تعيين النقرات إذا مر وقت كافي (أكثر من 5 ثوان)
        elif elapsed_time > 5:
            reset_user_clicks(user_id)
        
        return False  # يمكن المتابعة بشكل طبيعي
        
    except Exception as e:
        logger.error(f"Error in check_user_ban_and_track_clicks: {e}")
        return False  # في حالة الخطأ، نسمح بالمتابعة

# متغير عام لتتبع الإشعارات المعلقة
pending_unban_notifications = []

async def process_pending_unban_notifications(application):
    """معالجة الإشعارات المعلقة لرفع الحظر"""
    global pending_unban_notifications
    
    if not pending_unban_notifications:
        return
    
    notifications_to_process = pending_unban_notifications.copy()
    pending_unban_notifications.clear()
    
    for user_id in notifications_to_process:
        try:
            # الحصول على معلومات المستخدم
            user_result = db.execute_query("SELECT username FROM users WHERE user_id = ?", (user_id,))
            username = user_result[0][0] if user_result and user_result[0][0] else ""
            
            # إشعار المستخدم
            try:
                await notify_user_unban(application, user_id)
            except Exception as e:
                logger.error(f"Failed to notify user {user_id} about unban: {e}")
            
            # إشعار الآدمن
            try:
                await notify_admin_unban(application, user_id, username)
            except Exception as e:
                logger.error(f"Failed to notify admin about user {user_id} unban: {e}")
                
        except Exception as e:
            logger.error(f"Error processing unban notification for user {user_id}: {e}")

async def check_expired_bans_periodically(application):
    """فحص دوري للحظر المنتهي (كل 5 دقائق)"""
    from datetime import datetime
    
    try:
        # العثور على المستخدمين المحظورين الذين انتهت مدة حظرهم
        current_time = datetime.now().isoformat()
        expired_bans_query = """
            SELECT user_id FROM user_bans 
            WHERE is_banned = TRUE AND ban_end_time <= ?
        """
        expired_bans = db.execute_query(expired_bans_query, (current_time,))
        
        for row in expired_bans:
            user_id = row[0]
            
            # رفع الحظر
            was_lifted = lift_user_ban(user_id)
            if was_lifted:
                # إضافة إلى قائمة الإشعارات المعلقة
                global pending_unban_notifications
                if user_id not in pending_unban_notifications:
                    pending_unban_notifications.append(user_id)
                    logger.info(f"Added user {user_id} to unban notification queue")
        
        # معالجة الإشعارات المعلقة
        await process_pending_unban_notifications(application)
        
    except Exception as e:
        logger.error(f"Error in periodic ban check: {e}")

# إنشاء مدير قاعدة البيانات
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

# تم نقل get_referral_amount و get_referral_percentage إلى bot_customer.py (استيراد من هناك)

def clean_user_data_preserve_admin(context: ContextTypes.DEFAULT_TYPE) -> None:
    """تنظيف البيانات المؤقتة مع الحفاظ على حالة الأدمن"""
    # حفظ حالة الأدمن
    is_admin = context.user_data.get('is_admin', False)
    
    # تنظيف جميع البيانات
    context.user_data.clear()
    
    # استعادة حالة الأدمن
    if is_admin:
        context.user_data['is_admin'] = True

async def restore_admin_keyboard(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message: str = None, language: str = None):
    """إعادة تفعيل كيبورد الأدمن الرئيسي"""
    # تحديد اللغة (استخدام لغة الآدمن المنفصلة)
    if language is None:
        language = get_admin_language(chat_id)
    
    # إنشاء الكيبورد حسب اللغة
    admin_reply_markup = create_admin_keyboard(language)
    
    if message is None:
        message = "🔧 لوحة الأدمن جاهزة" if language == 'ar' else "🔧 Admin Panel Ready"
    
    await context.bot.send_message(
        chat_id,
        message,
        reply_markup=admin_reply_markup
    )

def generate_transaction_number(transaction_type: str) -> str:
    """توليد رقم معاملة جديد"""
    # الحصول على آخر رقم معاملة من نفس النوع
    query = "SELECT MAX(id) FROM transactions WHERE transaction_type = ?"
    result = db.execute_query(query, (transaction_type,))
    
    last_id = 0
    if result and result[0][0]:
        last_id = result[0][0]
    
    # توليد الرقم الجديد
    new_id = last_id + 1
    
    if transaction_type == 'proxy':
        prefix = 'P'
    elif transaction_type == 'withdrawal':
        prefix = 'M'
    else:
        prefix = 'T'
    
    # تنسيق الرقم بـ 10 خانات
    transaction_number = f"{prefix}-{new_id:010d}"
    
    return transaction_number

def save_transaction(order_id: str, transaction_number: str, transaction_type: str, status: str = 'completed'):
    """حفظ بيانات المعاملة"""
    db.execute_query('''
        INSERT INTO transactions (order_id, transaction_number, transaction_type, status)
        VALUES (?, ?, ?, ?)
    ''', (order_id, transaction_number, transaction_type, status))

def update_order_status(order_id: str, status: str):
    """تحديث حالة الطلب"""
    if status == 'completed':
        db.execute_query('''
            UPDATE orders 
            SET status = 'completed', processed_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (order_id,))
    elif status == 'failed':
        db.execute_query('''
            UPDATE orders 
            SET status = 'failed', processed_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (order_id,))

async def handle_withdrawal_success(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة نجاح سحب الرصيد"""
    query = update.callback_query
    await query.answer()
    
    order_id = query.data.replace('withdrawal_success_', '')
    
    # توليد رقم المعاملة
    transaction_number = generate_transaction_number('withdrawal')
    save_transaction(order_id, transaction_number, 'withdrawal', 'completed')
    
    # تحديث حالة الطلب إلى مكتمل
    update_order_status(order_id, 'completed')
    
    # الحصول على بيانات المستخدم
    user_query = "SELECT user_id FROM orders WHERE id = ?"
    user_result = db.execute_query(user_query, (order_id,))
    
    if user_result:
        user_id = user_result[0][0]
        user = db.get_user(user_id)
        
        if user:
            user_language = get_user_language(user_id)
            withdrawal_amount = user[5]
            
            # تصفير رصيد المستخدم
            db.execute_query("UPDATE users SET referral_balance = 0 WHERE user_id = ?", (user_id,))
            
            # رسالة للمستخدم بلغته
            if user_language == 'ar':
                user_message = f"""✅ تم تسديد مكافأة الإحالة بنجاح!

💰 المبلغ: <code>{withdrawal_amount:.2f}$</code>
🆔 معرف الطلب: {order_id}
💳 رقم المعاملة: <code>{transaction_number}</code>

🎉 تم إيداع المبلغ بنجاح!"""
            else:
                user_message = f"""✅ Referral reward paid successfully!

💰 Amount: <code>{withdrawal_amount:.2f}$</code>
🆔 Order ID: {order_id}
💳 Transaction Number: <code>{transaction_number}</code>

🎉 Amount deposited successfully!"""
            
            await context.bot.send_message(user_id, user_message, parse_mode='HTML')
            
            # إنشاء رسالة للأدمن مع زر فتح المحادثة
            keyboard = [
                [InlineKeyboardButton("💬 فتح محادثة مع المستخدم", url=f"tg://user?id={user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            admin_message = f"""✅ تم تسديد مكافأة الإحالة بنجاح!

👤 المستخدم: {user[2]} {user[3]}
📱 اسم المستخدم: @{user[1] or 'غير محدد'}
🆔 معرف المستخدم: <code>{user_id}</code>
💰 المبلغ المدفوع: <code>{withdrawal_amount:.2f}$</code>
🔗 معرف الطلب: <code>{order_id}</code>
💳 رقم المعاملة: <code>{transaction_number}</code>

📋 تم نقل الطلب إلى الطلبات المكتملة."""
            
            await query.edit_message_text(admin_message, reply_markup=reply_markup, parse_mode='HTML')
            
            # إعادة تفعيل كيبورد الأدمن بعد فترة قصيرة
            import asyncio
            await asyncio.sleep(2)
            await restore_admin_keyboard(context, update.effective_chat.id)

async def handle_withdrawal_failed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة فشل سحب الرصيد"""
    query = update.callback_query
    await query.answer()
    
    order_id = query.data.replace('withdrawal_failed_', '')
    
    # توليد رقم المعاملة
    transaction_number = generate_transaction_number('withdrawal')
    save_transaction(order_id, transaction_number, 'withdrawal', 'failed')
    
    # تحديث حالة الطلب إلى فاشل
    update_order_status(order_id, 'failed')
    
    # الحصول على بيانات المستخدم
    user_query = "SELECT user_id FROM orders WHERE id = ?"
    user_result = db.execute_query(user_query, (order_id,))
    
    if user_result:
        user_id = user_result[0][0]
        user = db.get_user(user_id)
        
        if user:
            user_language = get_user_language(user_id)
            withdrawal_amount = user[5]
            
            # رسالة للمستخدم
            if user_language == 'ar':
                user_message = f"""❌ فشلت عملية تسديد مكافأة الإحالة

💰 المبلغ: <code>{withdrawal_amount:.2f}$</code>
🆔 معرف الطلب: {order_id}
💳 رقم المعاملة: <code>{transaction_number}</code>

📞 يرجى التواصل مع الإدارة لمعرفة السبب."""
            else:
                user_message = f"""❌ Referral reward payment failed

💰 Amount: <code>{withdrawal_amount:.2f}$</code>
🆔 Order ID: {order_id}
💳 Transaction Number: <code>{transaction_number}</code>

📞 Please contact admin to know the reason."""
            
            await context.bot.send_message(user_id, user_message, parse_mode='HTML')
            
            # رسالة للأدمن
            admin_message = f"""❌ فشلت عملية تسديد مكافأة الإحالة

👤 المستخدم: {user[2]} {user[3]}
🆔 معرف المستخدم: <code>{user_id}</code>
💰 المبلغ: <code>{withdrawal_amount:.2f}$</code>
🔗 معرف الطلب: <code>{order_id}</code>
💳 رقم المعاملة: <code>{transaction_number}</code>

📋 تم نقل الطلب إلى الطلبات الفاشلة."""
            
            await query.edit_message_text(admin_message, parse_mode='HTML')
            
            # إعادة تفعيل كيبورد الأدمن بعد فترة قصيرة
            import asyncio
            await asyncio.sleep(2)
            await restore_admin_keyboard(context, update.effective_chat.id)

async def handle_approve_recharge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """سؤال الآدمن عن قيمة الرصيد بالدولار قبل معالجة طلب الشحن"""
    try:
        query = update.callback_query
        await query.answer()
        
        # استخراج معرف الطلب من callback_data
        order_id = query.data.replace('approve_recharge_', '')
        
        # الحصول على بيانات الطلب
        order_query = "SELECT user_id, payment_amount, quantity FROM orders WHERE id = ? AND proxy_type = 'balance_recharge'"
        order_result = db.execute_query(order_query, (order_id,))
        
        if not order_result:
            await query.edit_message_text("❌ لم يتم العثور على طلب الشحن")
            return ConversationHandler.END
        
        user_id, user_amount, points_text = order_result[0]
        
        # حفظ بيانات الطلب في context للاستخدام لاحقاً
        context.user_data['recharge_order_id'] = order_id
        context.user_data['recharge_user_id'] = user_id
        context.user_data['recharge_user_amount'] = user_amount
        context.user_data['recharge_points_text'] = points_text
        
        # سؤال الآدمن عن قيمة الرصيد بالدولار
        try:
            await query.edit_message_text(
                f"""💰 <b>تحديد قيمة الرصيد</b>
                
🆔 معرف الطلب: <code>{order_id}</code>
💵 قيمة المستخدم: <code>${user_amount:.2f}</code>

❓ <b>ما هي قيمة الرصيد الفعلية بالدولار؟</b>

🔢 أدخل القيمة بالدولار (مثال: 25.50):""",
                parse_mode='HTML'
            )
        except Exception as edit_error:
            # إذا فشل التعديل (مثلاً الرسالة صورة)، إرسال رسالة جديدة
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"""💰 <b>تحديد قيمة الرصيد</b>
                
🆔 معرف الطلب: <code>{order_id}</code>
💵 قيمة المستخدم: <code>${user_amount:.2f}</code>

❓ <b>ما هي قيمة الرصيد الفعلية بالدولار؟</b>

🔢 أدخل القيمة بالدولار (مثال: 25.50):""",
                parse_mode='HTML'
            )
        
        return ADMIN_RECHARGE_AMOUNT_INPUT
        
    except Exception as e:
        logger.error(f"Error in handle_approve_recharge: {e}")
        try:
            await query.edit_message_text("❌ حدث خطأ أثناء معالجة طلب الشحن")
        except Exception as edit_error:
            logger.error(f"Failed to edit message after error: {edit_error}")
        return ConversationHandler.END

async def handle_admin_recharge_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إدخال الآدمن لقيمة الرصيد"""
    try:
        admin_amount = float(update.message.text)
        user_amount = context.user_data.get('recharge_user_amount', 0.0)
        order_id = context.user_data.get('recharge_order_id')
        
        # حفظ قيمة الآدمن
        context.user_data['admin_recharge_amount'] = admin_amount
        
        if abs(admin_amount - user_amount) < 0.01:  # نفس القيمة (تقريباً)
            # المتابعة مباشرة بإتمام الشحن
            return await complete_recharge_approval(update, context, admin_amount)
        else:
            # الحصول على صورة إثبات الشحن
            recharge_proof_query = "SELECT proof_image FROM orders WHERE id = ?"
            proof_result = db.execute_query(recharge_proof_query, (order_id,))
            proof_image = proof_result[0][0] if proof_result and proof_result[0][0] else None
            
            # حساب النقاط المتوقعة لكل قيمة
            credit_price = db.get_credit_price()
            admin_points = admin_amount / credit_price
            user_points = user_amount / credit_price
            
            # عرض خيارات للآدمن
            keyboard = [
                [InlineKeyboardButton(f"💰 اعتماد قيمة الآدمن (${admin_amount:.2f})", callback_data=f"use_admin_amount_{order_id}")],
                [InlineKeyboardButton(f"👤 اعتماد قيمة الزبون (${user_amount:.2f})", callback_data=f"use_user_amount_{order_id}")],
                [InlineKeyboardButton("⏹️ إيقاف المعالجة", callback_data=f"stop_processing_{order_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # إرسال الرسالة مع تفاصيل الاختلاف
            difference_message = f"""⚠️ <b>تنبيه: اختلاف في قيم الشحن</b>

🆔 معرف الطلب: <code>{order_id}</code>
👤 قيمة الزبون: <code>${user_amount:.2f}</code> (النقاط المتوقعة: {user_points:.2f})
💰 قيمة الآدمن: <code>${admin_amount:.2f}</code> (النقاط المتوقعة: {admin_points:.2f})
📊 الفرق: <code>${abs(admin_amount - user_amount):.2f}</code>

❓ <b>أي قيمة تريد اعتمادها؟</b>

📋 <b>خياراتك:</b>
💰 <b>قيمة الآدمن</b> - سيتم اعتماد <code>${admin_amount:.2f}</code> وإضافة <code>{admin_points:.2f}</code> نقطة
👤 <b>قيمة الزبون</b> - سيتم اعتماد <code>${user_amount:.2f}</code> وإضافة <code>{user_points:.2f}</code> نقطة  
⏹️ <b>إيقاف المعالجة</b> - لن يتم تصنيف الطلب كفاشل، سيبقى معلق للمراجعة لاحقاً"""

            # إرسال الرسالة أولاً
            await update.message.reply_text(
                difference_message,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
            # إرسال صورة إثبات الشحن إذا كانت متوفرة
            if proof_image:
                try:
                    await update.message.reply_photo(
                        photo=proof_image,
                        caption="📸 صورة إثبات الشحن المرفقة من الزبون"
                    )
                except Exception as photo_error:
                    logger.error(f"Error sending proof image: {photo_error}")
                    await update.message.reply_text("⚠️ لم يتم العثور على صورة إثبات الشحن أو حدث خطأ في عرضها")
            
            return ConversationHandler.END
            
    except ValueError:
        await update.message.reply_text(
            "❌ <b>قيمة غير صحيحة</b>\n\n🔢 أدخل رقماً صحيحاً (مثال: 25.50):",
            parse_mode='HTML'
        )
        return ADMIN_RECHARGE_AMOUNT_INPUT
    except Exception as e:
        logger.error(f"Error in handle_admin_recharge_amount_input: {e}")
        await update.message.reply_text("❌ حدث خطأ، تم إلغاء العملية")
        return ConversationHandler.END

async def complete_recharge_approval(update: Update, context: ContextTypes.DEFAULT_TYPE, final_amount: float) -> int:
    """إتمام قبول طلب الشحن مع القيمة النهائية"""
    try:
        order_id = context.user_data.get('recharge_order_id')
        user_id = context.user_data.get('recharge_user_id')
        points_text = context.user_data.get('recharge_points_text', '')
        
        # حساب النقاط بناءً على القيمة النهائية
        credit_price = db.get_credit_price()
        expected_credits = final_amount / credit_price
        
        # الحصول على بيانات المستخدم
        user = db.get_user(user_id)
        if not user:
            await update.message.reply_text("❌ لم يتم العثور على بيانات المستخدم")
            return ConversationHandler.END
        
        user_language = get_user_language(user_id)
        
        # إضافة النقاط لرصيد المستخدم
        current_balance = db.get_user_balance(user_id)
        current_points = current_balance['charged_balance']
        new_points = current_points + expected_credits
        
        # استخدام add_points لإضافة النقاط وتسجيل المعاملة
        db.add_credits(user_id, expected_credits, 'recharge', order_id, f"شحن رصيد بقيمة ${final_amount:.2f}")
        
        # توليد رقم المعاملة
        transaction_number = generate_transaction_number('recharge')
        save_transaction(order_id, transaction_number, 'recharge', 'completed')
        
        # تحديث حالة الطلب إلى مكتمل
        update_order_status(order_id, 'completed')
        
        # إرسال رسالة للمستخدم
        if user_language == 'ar':
            user_message = f"""✅ تم قبول طلب شحن الرصيد بنجاح!

💰 المبلغ: ${final_amount:.2f}
💎 النقاط المضافة: {expected_credits:.2f} نقطة
💯 رصيدك الحالي: {new_points:.2f} نقطة
🆔 معرف الطلب: {order_id}
💳 رقم المعاملة: <code>{transaction_number}</code>

🎉 تم إضافة النقاط لحسابك بنجاح!"""
        else:
            user_message = f"""✅ Balance recharge request approved successfully!

💰 Amount: ${final_amount:.2f}
💎 Points Added: {expected_credits:.2f} points
💯 Current Balance: {new_points:.2f} points
🆔 Order ID: {order_id}
💳 Transaction Number: <code>{transaction_number}</code>

🎉 Points have been added to your account successfully!"""
        
        await context.bot.send_message(user_id, user_message, parse_mode='HTML')
        
        # رسالة تأكيد للآدمن
        admin_message = f"""✅ تم إتمام شحن الرصيد بنجاح!

🆔 معرف الطلب: {order_id}
👤 المستخدم: {user[2]} {user[3] or ''}
💰 المبلغ النهائي: ${final_amount:.2f}
💎 النقاط المضافة: {expected_credits:.2f} نقطة
💳 رقم المعاملة: <code>{transaction_number}</code>"""
        
        await update.message.reply_text(admin_message, parse_mode='HTML')
        
        # إعادة تفعيل كيبورد الأدمن
        await restore_admin_keyboard(context, update.effective_chat.id)
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in complete_recharge_approval: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء إتمام الشحن")
        return ConversationHandler.END

async def handle_recharge_amount_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة اختيار قيمة الشحن من الأزرار الثلاثة"""
    query = update.callback_query
    await query.answer()
    
    try:
        if query.data.startswith("use_admin_amount_"):
            order_id = query.data.replace("use_admin_amount_", "")
            admin_amount = context.user_data.get('admin_recharge_amount', 0.0)
            await complete_recharge_approval_with_amount(update, context, order_id, admin_amount, "admin")
            
        elif query.data.startswith("use_user_amount_"):
            order_id = query.data.replace("use_user_amount_", "")
            user_amount = context.user_data.get('recharge_user_amount', 0.0)
            await complete_recharge_approval_with_amount(update, context, order_id, user_amount, "user")
            
        elif query.data.startswith("stop_processing_"):
            order_id = query.data.replace("stop_processing_", "")
            await stop_recharge_processing(update, context, order_id)
            
    except Exception as e:
        logger.error(f"Error in handle_recharge_amount_choice: {e}")
        await query.edit_message_text("❌ حدث خطأ أثناء معالجة الاختيار")

async def complete_recharge_approval_with_amount(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str, final_amount: float, amount_source: str) -> None:
    """إتمام قبول طلب الشحن مع القيمة المختارة"""
    try:
        query = update.callback_query
        
        # الحصول على بيانات الطلب
        order_query = "SELECT user_id, payment_amount FROM orders WHERE id = ? AND proxy_type = 'balance_recharge'"
        order_result = db.execute_query(order_query, (order_id,))
        
        if not order_result:
            await query.edit_message_text("❌ لم يتم العثور على طلب الشحن")
            return
        
        user_id = order_result[0][0]
        
        # حساب النقاط بناءً على القيمة النهائية
        credit_price = db.get_credit_price()
        expected_credits = final_amount / credit_price
        
        # الحصول على بيانات المستخدم
        user = db.get_user(user_id)
        if not user:
            await query.edit_message_text("❌ لم يتم العثور على بيانات المستخدم")
            return
        
        user_language = get_user_language(user_id)
        
        # إضافة النقاط لرصيد المستخدم
        current_balance = db.get_user_balance(user_id)
        current_points = current_balance['charged_balance']
        new_points = current_points + expected_credits
        
        # استخدام add_points لإضافة النقاط وتسجيل المعاملة
        source_text = "قيمة الآدمن" if amount_source == "admin" else "قيمة الزبون"
        db.add_credits(user_id, expected_credits, 'recharge', order_id, f"شحن رصيد بقيمة ${final_amount:.2f} ({source_text})")
        
        # توليد رقم المعاملة
        transaction_number = generate_transaction_number('recharge')
        save_transaction(order_id, transaction_number, 'recharge', 'completed')
        
        # تحديث حالة الطلب إلى مكتمل
        update_order_status(order_id, 'completed')
        
        # إرسال رسالة للمستخدم
        if user_language == 'ar':
            user_message = f"""✅ تم قبول طلب شحن الرصيد بنجاح!

💰 المبلغ: ${final_amount:.2f}
💎 النقاط المضافة: {expected_credits:.2f} نقطة
💯 رصيدك الحالي: {new_points:.2f} نقطة
🆔 معرف الطلب: {order_id}
💳 رقم المعاملة: <code>{transaction_number}</code>

🎉 تم إضافة النقاط لحسابك بنجاح!"""
        else:
            user_message = f"""✅ Balance recharge request approved successfully!

💰 Amount: ${final_amount:.2f}
💎 Points Added: {expected_credits:.2f} points
💯 Current Balance: {new_points:.2f} points
🆔 Order ID: {order_id}
💳 Transaction Number: <code>{transaction_number}</code>

🎉 Points have been added to your account successfully!"""
        
        await context.bot.send_message(user_id, user_message, parse_mode='HTML')
        
        # رسالة تأكيد للآدمن
        admin_message = f"""✅ تم إتمام شحن الرصيد بنجاح!

🆔 معرف الطلب: {order_id}
👤 المستخدم: {user[2]} {user[3] or ''}
💰 المبلغ النهائي: ${final_amount:.2f} ({source_text})
💎 النقاط المضافة: {expected_credits:.2f} نقطة
💳 رقم المعاملة: <code>{transaction_number}</code>"""
        
        await query.edit_message_text(admin_message, parse_mode='HTML')
        
        # إعادة تفعيل كيبورد الأدمن
        await restore_admin_keyboard(context, update.effective_chat.id)
        
    except Exception as e:
        logger.error(f"Error in complete_recharge_approval_with_amount: {e}")
        await query.edit_message_text("❌ حدث خطأ أثناء إتمام الشحن")

async def stop_recharge_processing(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str) -> None:
    """إيقاف معالجة طلب الشحن دون تصنيفه كفاشل"""
    try:
        query = update.callback_query
        
        # الحصول على بيانات الطلب للعرض
        order_query = "SELECT user_id, payment_amount FROM orders WHERE id = ? AND proxy_type = 'balance_recharge'"
        order_result = db.execute_query(order_query, (order_id,))
        
        if order_result:
            user_id = order_result[0][0]
            user = db.get_user(user_id)
            user_name = f"{user[2]} {user[3] or ''}" if user else "غير معروف"
            
            stop_message = f"""⏹️ تم إيقاف معالجة طلب الشحن

🆔 معرف الطلب: {order_id}
👤 المستخدم: {user_name}
📊 حالة الطلب: معلق (للمراجعة اليدوية)

ℹ️ لم يتم تصنيف الطلب كفاشل، ويمكن معالجته لاحقاً من قائمة الطلبات المعلقة."""
        else:
            stop_message = f"""⏹️ تم إيقاف معالجة الطلب

🆔 معرف الطلب: {order_id}
📊 حالة الطلب: معلق (للمراجعة اليدوية)"""
        
        await query.edit_message_text(stop_message, parse_mode='HTML')
        
        # إعادة تفعيل كيبورد الأدمن
        await restore_admin_keyboard(context, update.effective_chat.id)
        
    except Exception as e:
        logger.error(f"Error in stop_recharge_processing: {e}")
        await query.edit_message_text("❌ حدث خطأ أثناء إيقاف المعالجة")

async def handle_recharge_amount_choice_old(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة اختيار الآدمن لقيمة الرصيد"""
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("use_admin_amount_"):
            admin_amount = context.user_data.get('admin_recharge_amount', 0.0)
            await complete_recharge_approval(update, context, admin_amount)
        elif query.data.startswith("use_user_amount_"):
            user_amount = context.user_data.get('recharge_user_amount', 0.0)
            await complete_recharge_approval(update, context, user_amount)
        elif query.data.startswith("stop_processing_"):
            order_id = context.user_data.get('recharge_order_id')
            await query.edit_message_text(
                f"⏹️ تم إيقاف معالجة طلب الشحن\n\n🆔 معرف الطلب: <code>{order_id}</code>\n\n📝 يمكن العودة لمعالجته لاحقاً من قائمة الطلبات المعلقة.",
                parse_mode='HTML'
            )
            await restore_admin_keyboard(context, update.effective_chat.id)
        
    except Exception as e:
        logger.error(f"Error in handle_recharge_amount_choice: {e}")
        await query.edit_message_text("❌ حدث خطأ أثناء معالجة الاختيار")
        await restore_admin_keyboard(context, update.effective_chat.id)

async def handle_reject_recharge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة رفض طلب شحن الرصيد"""
    try:
        query = update.callback_query
        await query.answer()
        
        # استخراج معرف الطلب من callback_data
        order_id = query.data.replace('reject_recharge_', '')
        
        # الحصول على بيانات الطلب
        order_query = "SELECT user_id, payment_amount, quantity FROM orders WHERE id = ? AND proxy_type = 'balance_recharge'"
        order_result = db.execute_query(order_query, (order_id,))
        
        if not order_result:
            await query.edit_message_text("❌ لم يتم العثور على طلب الشحن")
            return
        
        user_id, amount, points_text = order_result[0]
        expected_credits = float(points_text.replace(' points', ''))
        
        # الحصول على بيانات المستخدم
        user = db.get_user(user_id)
        if not user:
            await query.edit_message_text("❌ لم يتم العثور على بيانات المستخدم")
            return
        
        user_language = get_user_language(user_id)
        
        # توليد رقم المعاملة
        transaction_number = generate_transaction_number('recharge')
        save_transaction(order_id, transaction_number, 'recharge', 'failed')
        
        # تحديث حالة الطلب إلى مرفوض
        update_order_status(order_id, 'failed')
        
        # إرسال رسالة للمستخدم
        if user_language == 'ar':
            user_message = f"""❌ تم رفض طلب شحن الرصيد

💰 المبلغ: ${amount:.2f}
💎 النقاط المطلوبة: {expected_credits:.2f} نقطة
🆔 معرف الطلب: {order_id}
💳 رقم المعاملة: <code>{transaction_number}</code>

📞 يرجى التواصل مع الإدارة لمعرفة سبب الرفض وتصحيح المشكلة."""
        else:
            user_message = f"""❌ Balance recharge request rejected

💰 Amount: ${amount:.2f}
💎 Requested Points: {expected_credits:.2f} points
🆔 Order ID: {order_id}
💳 Transaction Number: <code>{transaction_number}</code>

📞 Please contact admin to know the reason for rejection and fix the issue."""
        
        await context.bot.send_message(user_id, user_message, parse_mode='HTML')
        
        # الحصول على بيانات إضافية للعرض المتسق
        order_query_details = """SELECT payment_method, created_at FROM orders WHERE id = ? AND proxy_type = 'balance_recharge'"""
        order_details = db.execute_query(order_query_details, (order_id,))
        payment_method = order_details[0][0] if order_details else ''
        created_at = order_details[0][1] if order_details else 'غير محدد'
        
        # معالجة طريقة الدفع للعرض
        payment_method_display = {
            'shamcash': 'شام كاش 💳',
            'syriatel': 'سيرياتيل كاش 💳',
            'coinex': 'Coinex 🪙',
            'binance': 'Binance 🪙',
            'payeer': 'Payeer 🪙',
            'bep20': 'BEP20 🔗',
            'litecoin': 'Litecoin 🔗'
        }.get(payment_method or '', payment_method or 'غير محدد')
        
        # تحديث رسالة الآدمن لتصبح رسالة فشل مع زر فتح المحادثة فقط
        admin_message = f"""📋 تفاصيل طلب شحن الرصيد

🆔 معرف الطلب: {order_id}
📊 حالة الطلب: ❌ مرفوض

━━━━━━━━━━━━━━━
👤 بيانات المستخدم:
📝 الاسم: {user[2]} {user[3] or ''}
📱 اسم المستخدم: @{user[1] or 'غير محدد'}
🆔 المعرف: {user_id}

━━━━━━━━━━━━━━━
💰 تفاصيل الطلب:
💵 المبلغ: ${amount:.2f}
💎 النقاط المتوقعة: {expected_credits:.2f} نقطة
💳 طريقة الدفع: {payment_method_display}
📅 وقت الطلب: {created_at}

━━━━━━━━━━━━━━━
📸 إثبات الدفع: ✅ مرفق"""
        
        # إنشاء زر فتح المحادثة فقط
        keyboard = [[InlineKeyboardButton("💬 فتح محادثة مع المستخدم", url=f"tg://user?id={user_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # محاولة تعديل الرسالة (نص أو caption للصور)
        try:
            # محاولة تعديل النص أولاً
            await query.edit_message_text(admin_message, reply_markup=reply_markup, parse_mode='HTML')
        except Exception as text_edit_error:
            if "There is no text in the message to edit" in str(text_edit_error):
                # إذا كانت الرسالة تحتوي على صورة، استخدم editMessageCaption
                try:
                    await query.edit_message_caption(caption=admin_message, reply_markup=reply_markup, parse_mode='HTML')
                except Exception as caption_edit_error:
                    logger.error(f"Failed to edit message caption in reject: {caption_edit_error}")
                    # إذا فشل تعديل العنوان أيضاً، احذف الرسالة وأرسل رسالة جديدة
                    try:
                        await query.delete_message()
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=admin_message,
                            reply_markup=reply_markup,
                            parse_mode='HTML'
                        )
                    except Exception as new_message_error:
                        logger.error(f"Failed to send new message in reject: {new_message_error}")
            else:
                logger.error(f"Failed to edit message text in reject: {text_edit_error}")
                raise
        
        # إعادة تفعيل كيبورد الأدمن
        await restore_admin_keyboard(context, update.effective_chat.id)
        
    except Exception as e:
        logger.error(f"Error in handle_reject_recharge: {e}")
        try:
            await query.edit_message_text("❌ حدث خطأ أثناء معالجة طلب الشحن")
        except Exception as edit_error:
            logger.error(f"Failed to edit message after error: {edit_error}")
        await restore_admin_keyboard(context, update.effective_chat.id)

async def handle_view_recharge_details_with_id(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str, answered: bool = False) -> None:
    """معالجة عرض تفاصيل طلب شحن الرصيد مع معرف الطلب المحدد"""
    try:
        query = update.callback_query
        if not answered:
            await query.answer()
        
        # الحصول على بيانات الطلب
        order_query = """SELECT user_id, payment_amount, quantity, payment_method, payment_proof, created_at, status 
                        FROM orders WHERE id = ? AND proxy_type = 'balance_recharge'"""
        order_result = db.execute_query(order_query, (order_id,))
        
        if not order_result:
            await query.edit_message_text("❌ لم يتم العثور على طلب الشحن")
            return
        
        order_data = order_result[0]
        if len(order_data) < 7:
            await query.edit_message_text("❌ بيانات طلب الشحن غير كاملة")
            return
        
        user_id, amount, points_text, payment_method, payment_proof, created_at, status = order_data
        expected_credits = float(str(points_text).replace(' points', '')) if points_text else 0.0
        
        # الحصول على بيانات المستخدم
        user = db.get_user(user_id)
        if not user:
            await query.edit_message_text("❌ لم يتم العثور على بيانات المستخدم")
            return
        
        # معالجة طريقة الدفع للعرض
        payment_method_display = {
            'shamcash': 'شام كاش 💳',
            'syriatel': 'سيرياتيل كاش 💳',
            'coinex': 'Coinex 🪙',
            'binance': 'Binance 🪙',
            'payeer': 'Payeer 🪙',
            'bep20': 'BEP20 🔗',
            'litecoin': 'Litecoin 🔗'
        }.get(payment_method or '', payment_method or 'غير محدد')
        
        # معالجة حالة الطلب
        status_display = {
            'pending': '⏳ معلق',
            'completed': '✅ مكتمل',
            'failed': '❌ مرفوض'
        }.get(status, status)
        
        # تهريب بيانات المستخدم لـ MarkdownV2
        first_name = escape_markdown_v2(str(user[2]) if user[2] else '')
        last_name = escape_markdown_v2(str(user[3]) if user[3] else '')
        username = escape_markdown_v2(str(user[1]) if user[1] else 'غير محدد')
        escaped_order_id = escape_markdown_v2(str(order_id))
        escaped_user_id = escape_markdown_v2(str(user_id))
        escaped_payment_method = escape_markdown_v2(str(payment_method_display))
        escaped_created_at = escape_markdown_v2(str(created_at))
        
        # تهريب الأرقام العشرية (المبلغ والنقاط)
        escaped_amount = escape_markdown_v2(f"{amount:.2f}")
        escaped_credits = escape_markdown_v2(f"{expected_credits:.2f}")
        
        # تحقق من حالة الطلب لعرض رسالة مناسبة
        if status == 'completed':
            # رسالة نجاح للطلبات المكتملة مع زر فتح المحادثة فقط
            success_message = f"""📋 تفاصيل طلب شحن الرصيد

🆔 معرف الطلب: <code>{escaped_order_id}</code>
📊 حالة الطلب: ✅ مكتمل

━━━━━━━━━━━━━━━
👤 بيانات المستخدم:
📝 الاسم: {first_name} {last_name}
📱 اسم المستخدم: @{username}
🆔 المعرف: <code>{escaped_user_id}</code>

━━━━━━━━━━━━━━━
💰 تفاصيل الطلب:
💵 المبلغ: ${escaped_amount}
💎 النقاط المتوقعة: {escaped_credits} نقطة
💳 طريقة الدفع: {escaped_payment_method}
📅 وقت الطلب: {escaped_created_at}

━━━━━━━━━━━━━━━
📸 إثبات الدفع: ✅ مرفق"""
            
            # إنشاء زر فتح المحادثة فقط (إذا كان للمستخدم username)
            keyboard = []
            if username and username != 'غير محدد':
                keyboard.append([InlineKeyboardButton("💬 فتح محادثة مع المستخدم", url=f"https://t.me/{username}")])
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            
            # عرض رسالة النجاح مع زر فتح المحادثة (استخدام Markdown بدلاً من MarkdownV2)
            await query.edit_message_text(success_message, reply_markup=reply_markup, parse_mode='HTML')
            return
            
        elif status == 'failed':
            # رسالة رفض للطلبات المرفوضة مع زر فتح المحادثة فقط
            reject_message = f"""📋 تفاصيل طلب شحن الرصيد

🆔 معرف الطلب: <code>{escaped_order_id}</code>
📊 حالة الطلب: ❌ مرفوض

━━━━━━━━━━━━━━━
👤 بيانات المستخدم:
📝 الاسم: {first_name} {last_name}
📱 اسم المستخدم: @{username}
🆔 المعرف: <code>{escaped_user_id}</code>

━━━━━━━━━━━━━━━
💰 تفاصيل الطلب:
💵 المبلغ: ${escaped_amount}
💎 النقاط المطلوبة: {escaped_credits} نقطة
💳 طريقة الدفع: {escaped_payment_method}
📅 وقت الطلب: {escaped_created_at}

━━━━━━━━━━━━━━━
📸 إثبات الدفع: ✅ مرفق"""
            
            # إنشاء زر فتح المحادثة فقط (إذا كان للمستخدم username)
            keyboard = []
            if username and username != 'غير محدد':
                keyboard.append([InlineKeyboardButton("💬 فتح محادثة مع المستخدم", url=f"https://t.me/{username}")])
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            
            # عرض رسالة الرفض مع زر فتح المحادثة (استخدام Markdown بدلاً من MarkdownV2)
            await query.edit_message_text(reject_message, reply_markup=reply_markup, parse_mode='HTML')
            return
        
        # تهريب حالة الطلب
        escaped_status = escape_markdown_v2(str(status_display))
        
        # للطلبات المعلقة فقط - عرض التفاصيل مع الأزرار
        details_message = f"""📋 تفاصيل طلب شحن الرصيد

🆔 معرف الطلب: <code>{escaped_order_id}</code>
📊 حالة الطلب: {escaped_status}

━━━━━━━━━━━━━━━
👤 بيانات المستخدم:
📝 الاسم: {first_name} {last_name}
📱 اسم المستخدم: @{username}
🆔 المعرف: <code>{escaped_user_id}</code>

━━━━━━━━━━━━━━━
💰 تفاصيل الطلب:
💵 المبلغ: ${escaped_amount}
💎 النقاط المتوقعة: {escaped_credits} نقطة
💳 طريقة الدفع: {escaped_payment_method}
📅 وقت الطلب: {escaped_created_at}

━━━━━━━━━━━━━━━
📸 إثبات الدفع: {'✅ مرفق' if payment_proof else '❌ غير متوفر'}"""
        
        # إنشاء الأزرار للطلبات المعلقة فقط
        keyboard = [
            [
                InlineKeyboardButton("✅ قبول الطلب", callback_data=f"approve_recharge_{order_id}"),
                InlineKeyboardButton("❌ رفض الطلب", callback_data=f"reject_recharge_{order_id}")
            ]
        ]
        # إضافة زر فتح المحادثة فقط إذا كان للمستخدم username
        if user[1] and user[1] != 'غير محدد':
            keyboard.append([
                InlineKeyboardButton("💬 فتح محادثة مع المستخدم", url=f"https://t.me/{user[1]}")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # إرسال التفاصيل مع إثبات الدفع إذا كان متوفراً
        if payment_proof and payment_proof.startswith("photo:"):
            file_id = payment_proof.replace("photo:", "").strip()
            
            # التحقق من صحة file_id
            if file_id and len(file_id) > 10:
                try:
                    # إرسال صورة إثبات الدفع مع التفاصيل وأزرار التحكم
                    loading_message = await query.edit_message_text("📋 جاري تحميل تفاصيل الطلب...")
                    
                    await context.bot.send_photo(
                        query.message.chat_id,
                        photo=file_id,
                        caption=details_message,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
                    
                    # حذف رسالة التحميل لتجنب الفوضى في المحادثة
                    try:
                        await context.bot.delete_message(
                            chat_id=query.message.chat_id,
                            message_id=loading_message.message_id
                        )
                    except Exception as delete_error:
                        logger.warning(f"Could not delete loading message: {delete_error}")
                except Exception as photo_error:
                    logger.error(f"Failed to send photo (file_id: {file_id[:20]}...): {photo_error}")
                    # إذا فشل إرسال الصورة، أرسل التفاصيل بدون صورة
                    await query.edit_message_text(
                        details_message + "\n\n⚠️ فشل تحميل إثبات الدفع", 
                        reply_markup=reply_markup, 
                        parse_mode='HTML'
                    )
            else:
                # file_id غير صالح، أرسل التفاصيل بدون صورة
                await query.edit_message_text(details_message, reply_markup=reply_markup, parse_mode='HTML')
        else:
            # إرسال التفاصيل فقط بدون صورة
            await query.edit_message_text(details_message, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error in handle_view_recharge_details_with_id: {e}")
        await query.edit_message_text("❌ حدث خطأ أثناء عرض تفاصيل طلب الشحن")

async def handle_view_recharge_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة عرض تفاصيل طلب شحن الرصيد"""
    try:
        query = update.callback_query
        await query.answer()
        
        # استخراج معرف الطلب من callback_data
        order_id = query.data.replace('view_recharge_', '')
        
        # استدعاء الدالة المساعدة مع معرف الطلب
        await handle_view_recharge_details_with_id(update, context, order_id, answered=True)
        
    except Exception as e:
        logger.error(f"Error in handle_view_recharge_details: {e}")
        await query.edit_message_text("❌ حدث خطأ أثناء عرض تفاصيل طلب الشحن")

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
        # التحقق من كلمة المرور الحالية
        if update.message.text == ADMIN_PASSWORD:
            # حذف رسالة كلمة المرور الحالية من المحادثة لأسباب أمنية
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
        # تحديث كلمة المرور
        new_password = update.message.text
        ADMIN_PASSWORD = new_password
        
        # حذف رسالة كلمة المرور الجديدة من المحادثة لأسباب أمنية
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
        except Exception as e:
            print(f"تعذر حذف رسالة كلمة المرور الجديدة: {e}")
        
        # حفظ كلمة المرور الجديدة في قاعدة البيانات
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
    is_admin = context.user_data.get('is_admin', False)
    
    if user_language == 'ar':
        await query.edit_message_text("❌ تم إلغاء تغيير كلمة المرور")
    else:
        await query.edit_message_text("❌ Password change cancelled")
    
    # تنظيف البيانات المؤقتة
    context.user_data.pop('password_change_step', None)
    
    # إعادة الكيبورد المناسب
    if is_admin:
        await restore_admin_keyboard(context, user_id, "🔧 لوحة الأدمن جاهزة")
    else:
        # إعادة الكيبورد الرئيسي للمستخدم العادي
        await start(query, context)
    
    return ConversationHandler.END

def validate_ip_address(ip: str) -> bool:
    """التحقق من صحة عنوان IP"""
    import re
    # نمط للتحقق من الهيكل: 1-3 أرقام.1-3 أرقام.1-3 أرقام.1-3 أرقام
    pattern = r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$'
    return bool(re.match(pattern, ip))

def validate_port(port: str) -> bool:
    """التحقق من صحة رقم البورت"""
    # التحقق من أن المدخل رقمي وطوله 1-6 أرقام
    if not port.isdigit():
        return False
    
    port_int = int(port)
    # التحقق من أن الرقم بين 1 و 999999 (6 أرقام كحد أقصى)
    return 1 <= port_int <= 999999

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أمر المساعدة - محدث مع زر FAQ"""
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

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض معلومات حساب المستخدم"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    # جلب معلومات المستخدم
    user = db.get_user(user_id)
    
    if not user:
        if language == 'ar':
            await update.message.reply_text("❌ خطأ: لم يتم العثور على المستخدم")
        else:
            await update.message.reply_text("❌ Error: User not found")
        return
    
    # استخراج البيانات
    user_name = user[2] if user[2] else "غير متوفر" if language == 'ar' else "N/A"
    username = f"@{user[1]}" if user[1] else ("غير متوفر" if language == 'ar' else "N/A")
    user_id_str = str(user_id)
    balance = float(user[6]) if user[6] else 0.0
    is_banned = bool(user[7]) if len(user) > 7 else False
    
    # تنسيق الرسالة
    if language == 'ar':
        ban_status = "🔴 محظور" if is_banned else "🟢 نشط"
        message = f"""👤 <b>معلومات الحساب</b>
━━━━━━━━━━━━━━━━━━━━
        
📝 <b>الاسم:</b> {escape_html(user_name)}
🏷️ <b>اسم المستخدم:</b> {escape_html(username)}
🆔 <b>المعرف:</b> <code>{user_id_str}</code>
💰 <b>الرصيد:</b> {balance:.2f} كريديت
📊 <b>حالة الحساب:</b> {ban_status}

━━━━━━━━━━━━━━━━━━━━
🔧 <i>استخدم /start للرجوع للقائمة الرئيسية</i>"""
    else:
        ban_status = "🔴 Banned" if is_banned else "🟢 Active"
        message = f"""👤 <b>Account Information</b>
━━━━━━━━━━━━━━━━━━━━

📝 <b>Name:</b> {escape_html(user_name)}
🏷️ <b>Username:</b> {escape_html(username)}
🆔 <b>ID:</b> <code>{user_id_str}</code>
💰 <b>Balance:</b> {balance:.2f} credits
📊 <b>Account Status:</b> {ban_status}

━━━━━━━━━━━━━━━━━━━━
🔧 <i>Use /start to return to main menu</i>"""
    
    await update.message.reply_text(message, parse_mode='HTML')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أمر البداية - إلغاء جميع العمليات المعلقة وإعادة تعيين الحالة"""
    user = update.effective_user
    
    # التحقق من حالة تشغيل البوت - إذا كان متوقفاً، تجاهل المستخدمين العاديين
    if not is_bot_running() and user.id not in ADMIN_IDS:
        language = get_user_language(user.id)
        await update.message.reply_text(
            "⚠️ البوت متوقف حالياً للصيانة. يرجى المحاولة لاحقاً." if language == 'ar' else "⚠️ Bot is currently stopped for maintenance. Please try again later."
        )
        return
    
    # تنظيف جميع البيانات المؤقتة والعمليات المعلقة
    context.user_data.clear()
    
    # التحقق من وجود المستخدم مسبقاً
    existing_user = db.get_user(user.id)
    is_new_user = existing_user is None
    
    # إضافة المستخدم إلى قاعدة البيانات
    referred_by = None
    if context.args and is_new_user:
        try:
            referred_by = int(context.args[0])
            # التأكد من أن المحيل موجود
            referrer = db.get_user(referred_by)
            if not referrer:
                referred_by = None
        except ValueError:
            pass
    
    # تحديد اللغة الافتراضية للمستخدمين الجدد
    # كشف تلقائي للغة للمستخدمين العاديين من إعدادات Telegram
    # الأدمن يبقى دائماً بالعربية
    if is_new_user:
        # كشف اللغة تلقائياً من إعدادات حساب Telegram للمستخدمين العاديين
        detected_lang = user.language_code if hasattr(user, 'language_code') and user.language_code else None
        
        # تحويل كود اللغة إلى ar أو en
        if detected_lang:
            if detected_lang.startswith('ar'):
                auto_language = 'ar'
            elif detected_lang.startswith('en'):
                auto_language = 'en'
            else:
                # افتراضي عربي للغات الأخرى
                auto_language = 'ar'
        else:
            # افتراضي عربي إذا لم يتم الكشف
            auto_language = 'ar'
    else:
        auto_language = None
    
    db.add_user(user.id, user.username, user.first_name, user.last_name, referred_by, auto_language)
    
    # إضافة مكافأة الإحالة للمحيل
    if referred_by and is_new_user:
        await add_referral_bonus(referred_by, user.id)
        
        # إشعار المحيل (بدون كشف الهوية)
        try:
            await context.bot.send_message(
                referred_by,
                f"🎉 تهانينا! انضم مستخدم جديد عبر رابط الإحالة الخاص بك.\n💰 ستحصل على {get_referral_percentage()}% من قيمة كل عملية شراء يقوم بها!",
                parse_mode='HTML'
            )
        except:
            pass  # في حالة عدم إمكانية إرسال الرسالة
        
        # إشعار الأدمن بانضمام عضو جديد عبر الإحالة
        await send_referral_notification(context, referred_by, user)
    
    db.log_action(user.id, "start_command")
    
    language = get_user_language(user.id)
    
    # التحقق من الاشتراك في القناة (للمستخدمين غير الآدمن)
    if user.id not in ADMIN_IDS:
        is_subscribed, channel = await check_user_subscription(context.bot, user.id)
        if not is_subscribed:
            text = f"""
<b>{"⚠️ الاشتراك مطلوب" if language == 'ar' else "⚠️ Subscription Required"}</b>

{"يجب عليك الاشتراك في قناتنا لاستخدام البوت:" if language == 'ar' else "You must subscribe to our channel to use this bot:"}

📢 {channel}

{"بعد الاشتراك، اضغط على زر التحقق أدناه." if language == 'ar' else "After subscribing, click the verify button below."}
"""
            keyboard = [
                [InlineKeyboardButton(
                    "📢 " + ("اشترك في القناة" if language == 'ar' else "Subscribe"),
                    url=f"https://t.me/{channel.replace('@', '')}"
                )],
                [InlineKeyboardButton(
                    "✅ " + ("تحقق من الاشتراك" if language == 'ar' else "Verify"),
                    callback_data="verify_channel_subscription"
                )]
            ]
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            return ConversationHandler.END
    
    # رسالة ترحيب للمستخدمين الجدد
    if is_new_user:
        welcome_message = MESSAGES[language]['welcome']
        if referred_by:
            welcome_message += f"\n\n🎁 مرحباً بك! لقد انضممت عبر رابط إحالة وحصل صديقك على مكافأة!"
    else:
        welcome_message = MESSAGES[language]['welcome']
    
    # إنشاء الأزرار الرئيسية (6 أزرار كاملة)
    reply_markup = create_main_user_keyboard(language)
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup
    )
    
    # إرجاع ConversationHandler.END للتأكد من إنهاء أي محادثة نشطة
    return ConversationHandler.END

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
        
        # إضافة الآدمن لقائمة الآدمن النشطين إذا لم يكن موجوداً
        if user_id not in ACTIVE_ADMINS:
            ACTIVE_ADMINS.append(user_id)
        
        # تحديث المتغيرات العالمية في dynamic_buttons_handler
        update_admin_globals(active_admins=ACTIVE_ADMINS, admin_chat_id=ADMIN_CHAT_ID)
        
        # تسجيل تسجيل دخول الآدمن
        try:
            db.log_action(user_id, "admin_login_success")
        except Exception as log_error:
            logger.error(f"Error logging admin login: {log_error}")
        
        # حذف رسالة كلمة المرور من المحادثة لأسباب أمنية
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
        except Exception as e:
            print(f"تعذر حذف رسالة كلمة المرور: {e}")
        
        # حفظ اللغة الأصلية للمستخدم قبل تغييرها
        original_language = get_user_language(user_id)
        context.user_data['original_user_language'] = original_language
        
        # ضبط اللغة للعربي عند كل تسجيل دخول للأدمن
        db.update_user_language(user_id, 'ar')
        admin_language = 'ar'
        logger.info(f"تم ضبط اللغة العربية للأدمن {user_id} عند تسجيل الدخول (اللغة الأصلية: {original_language})")
        
        # عرض لوحة مفاتيح الآدمن حسب اللغة
        await restore_admin_keyboard(context, user_id, None, admin_language)
        return ConversationHandler.END  # إنهاء المحادثة لتمكين إعادة الاستخدام
    else:
        await update.message.reply_text("كلمة المرور غير صحيحة!")
        return ConversationHandler.END

async def handle_static_proxy_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة طلب البروكسي الستاتيك"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    # التحقق من حالة خدمات الستاتيك قبل المتابعة
    if not await check_service_availability('static', update, context, language):
        return
    
    # حفظ نوع البروكسي فقط بدون إنشاء معرف الطلب
    context.user_data['proxy_type'] = 'static'
    
    db.log_action(user_id, "static_proxy_request_started")
    
    # ✅ الحصول على جميع الأسعار (متغيرات ديناميكية)
    virgin_residential_price = get_current_price('virgin_residential')
    att_price = get_current_price('att')
    verizon_price = get_current_price('verizon')
    isp_price = get_current_price('isp')
    weekly_price = get_current_price('weekly')
    daily_price = get_current_price('daily')
    datacenter_price = get_current_price('datacenter')
    
    # عرض رسالة الحزمة مع الأسعار الفعلية (جميع البروكسيات السبعة)
    if language == 'ar':
        replacement_text = 'سيتم إنشاء معرف الطلب'
    else:
        replacement_text = 'Order ID will be generated'
    
    package_message = MESSAGES[language]['static_package'].format(
        virgin_price=virgin_residential_price,
        att_price=att_price,
        verizon_price=verizon_price,
        isp_price=isp_price,
        weekly_price=weekly_price,
        daily_price=daily_price,
        datacenter_price=datacenter_price,
        order_id=''
    ).replace('معرف الطلب: ' if language == 'ar' else 'Order ID: ', replacement_text)
    await update.message.reply_text(package_message)
    
    if language == 'ar':
        keyboard = [
            [InlineKeyboardButton(f"💎 ڤيرجين ريزيدنتال ({virgin_residential_price}$)", callback_data="virgin_residential_proxy")],
            [InlineKeyboardButton(f"🏢 ريزيدنتال ({att_price}$)", callback_data="quantity_package_static")],
            [InlineKeyboardButton("💎 ريزيدنتال مرن ⚡", callback_data="residential_4_dollar")],
            [InlineKeyboardButton(f"🌐 ISP ({isp_price}$)", callback_data="quantity_isp_static")],
            [InlineKeyboardButton(f"🔧 بروكسي داتا سينتر ({datacenter_price}$)", callback_data="datacenter_proxy")]
        ]
        quantity_text = "اختر نوع البروكسي المطلوب:"
    else:
        keyboard = [
            [InlineKeyboardButton(f"💎 Virgin Residential ({virgin_residential_price}$)", callback_data="virgin_residential_proxy")],
            [InlineKeyboardButton(f"🏢 Residential ({att_price}$)", callback_data="quantity_package_static")],
            [InlineKeyboardButton("💎 Flexible Residential ⚡", callback_data="residential_4_dollar")],
            [InlineKeyboardButton(f"🌐 ISP ({isp_price}$)", callback_data="quantity_isp_static")],
            [InlineKeyboardButton(f"🔧 Datacenter Proxy ({datacenter_price}$)", callback_data="datacenter_proxy")]
        ]
        quantity_text = "Choose the proxy type required:"
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(quantity_text, reply_markup=reply_markup)
    context.user_data['proxy_type'] = 'static'
    return

async def handle_socks_proxy_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة طلب بروكسي السوكس"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    # التحقق من حالة خدمات السوكس قبل المتابعة
    if not await check_service_availability('socks', update, context, language):
        return
    
    # حفظ نوع البروكسي فقط بدون إنشاء معرف الطلب
    context.user_data['proxy_type'] = 'socks'
    
    db.log_action(user_id, "socks_proxy_request_started")
    
    # الحصول على أسعار السوكس الديناميكية أولاً
    socks_prices = get_socks_prices()
    single_price = socks_prices.get('single_proxy', '0.15')
    double_price = socks_prices.get('double_proxy', '0.25')
    package5_price = socks_prices.get('5proxy', '0.4')
    package10_price = socks_prices.get('10proxy', '0.7')
    
    # عرض رسالة الحزمة مع الأسعار الفعلية
    if language == 'ar':
        replacement_text = 'سيتم إنشاء معرف الطلب'
    else:
        replacement_text = 'Order ID will be generated'
    
    package_message = MESSAGES[language]['socks_package'].format(
        single_price=single_price,
        double_price=double_price,
        five_price=package5_price,
        ten_price=package10_price,
        order_id=''
    ).replace('معرف الطلب: ' if language == 'ar' else 'Order ID: ', replacement_text)
    await update.message.reply_text(package_message)
    
    # عرض أزرار الكمية أولاً (مثل الستاتيك)
    if language == 'ar':
        keyboard = [
            [InlineKeyboardButton(f"🔸 بروكسي واحد ({single_price}$)", callback_data="quantity_one_socks")],
            [InlineKeyboardButton(f"🔸 بروكسيان اثنان ({double_price}$)", callback_data="quantity_two_socks")],
            [InlineKeyboardButton(f"📦 باكج 5 ({package5_price}$)", callback_data="quantity_single_socks")],
            [InlineKeyboardButton(f"📦 باكج 10 ({package10_price}$)", callback_data="quantity_package_socks")]
        ]
        quantity_text = "اختر الكمية المطلوبة:"
    else:
        keyboard = [
            [InlineKeyboardButton(f"🔸 One Proxy ({single_price}$)", callback_data="quantity_one_socks")],
            [InlineKeyboardButton(f"🔸 Two Proxies ({double_price}$)", callback_data="quantity_two_socks")],
            [InlineKeyboardButton(f"📦 Package 5 ({package5_price}$)", callback_data="quantity_single_socks")],
            [InlineKeyboardButton(f"📦 Package 10 ({package10_price}$)", callback_data="quantity_package_socks")]
        ]
        quantity_text = "Choose the required quantity:"
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(quantity_text, reply_markup=reply_markup)
    context.user_data['proxy_type'] = 'socks'
    return

async def handle_country_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة اختيار الدولة"""
    try:
        query = update.callback_query
        user_id = update.effective_user.id
        
        # تسجيل الإجراء
        logger.info(f"User {user_id} selected: {query.data}")
        
        try:
            await query.answer()
        except Exception as answer_error:
            logger.warning(f"Failed to answer country callback for user {user_id}: {answer_error}")
        
        language = get_user_language(user_id)
        
        # معالجة خاصة للستاتيك الأسبوعي
        if query.data.startswith("country_") and query.data.endswith("_weekly"):
            country_code = query.data.replace("country_", "").replace("_weekly", "")
            context.user_data['selected_country_code'] = country_code
            
            # تحديد اسم الدولة
            if country_code == 'US':
                country_name = 'الولايات المتحدة' if language == 'ar' else 'United States'
            else:
                country_name = country_code
                
            context.user_data['selected_country'] = country_name
            
            # أمريكا - عرض الولايات
            try:
                states = STATIC_WEEKLY_LOCATIONS[language][country_code]
                
                keyboard = []
                for state_code, state_name in states.items():
                    keyboard.append([InlineKeyboardButton(
                        f"📍 {state_name}", 
                        callback_data=f"state_{state_code}_weekly"
                    )])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                message = f"🏛️ اختر الولاية في {country_name}:" if language == 'ar' else f"🏛️ Choose state in {country_name}:"
                await query.edit_message_text(message, reply_markup=reply_markup)
            except Exception as e:
                logger.error(f"Error displaying weekly states for {country_code}: {e}")
                await query.edit_message_text("❌ خطأ في عرض الولايات" if language == 'ar' else "❌ Error displaying states")
            return
        
        # معالجة خاصة للستاتيك اليومي
        if query.data.startswith("country_") and query.data.endswith("_daily"):
            country_code = query.data.replace("country_", "").replace("_daily", "")
            context.user_data['selected_country_code'] = country_code
            
            # تحديد اسم الدولة
            if country_code == 'US':
                country_name = 'الولايات المتحدة' if language == 'ar' else 'United States'
            else:
                country_name = country_code
                
            context.user_data['selected_country'] = country_name
            
            # أمريكا - عرض الولايات (فيرجينيا فقط)
            try:
                states = STATIC_DAILY_LOCATIONS[language][country_code]
                
                keyboard = []
                for state_code, state_name in states.items():
                    keyboard.append([InlineKeyboardButton(
                        f"📍 {state_name}", 
                        callback_data=f"state_{state_code}_daily"
                    )])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                message = f"🏛️ اختر الولاية في {country_name}:" if language == 'ar' else f"🏛️ Choose state in {country_name}:"
                await query.edit_message_text(message, reply_markup=reply_markup)
            except Exception as e:
                logger.error(f"Error displaying daily states for {country_code}: {e}")
                await query.edit_message_text("❌ خطأ في عرض الولايات" if language == 'ar' else "❌ Error displaying states")
            return
            
        elif query.data.startswith("state_") and query.data.endswith("_weekly"):
            # معالجة اختيار الولاية للستاتيك الأسبوعي
            state_code = query.data.replace("state_", "").replace("_weekly", "")
            country_code = context.user_data.get('selected_country_code', 'US')
            
            try:
                # تحديد اسم الولاية
                states = STATIC_WEEKLY_LOCATIONS[language][country_code]
                state_name = states.get(state_code, state_code)
                
                # فحص توفر الولاية لهذه الخدمة
                if not db.get_service_status('static', 'weekly_crocker', country_code, state_code):
                    error_msg = f"🚫 عذراً، {state_name} غير متاحة حالياً في الستاتيك الأسبوعي\n\n⚠️ تم إيقاف هذه الولاية مؤقتاً من قبل الإدارة\nيُرجى اختيار ولاية أخرى" if language == 'ar' else f"🚫 Sorry, {state_name} is not available in Weekly Static\n\n⚠️ This state has been temporarily disabled\nPlease choose another state"
                    await query.edit_message_text(error_msg)
                    return
                
                context.user_data['selected_state'] = state_name
                context.user_data['selected_state_code'] = state_code
                
                # سؤال المستخدم عن الكمية قبل إنشاء الطلب
                await ask_static_proxy_quantity(query, context, language)
            except Exception as e:
                logger.error(f"Error handling weekly state selection: {e}")
                await query.edit_message_text("❌ خطأ في معالجة اختيار الولاية" if language == 'ar' else "❌ Error processing state selection")
            return
        
        elif query.data.startswith("state_") and query.data.endswith("_daily"):
            # معالجة اختيار الولاية للستاتيك اليومي
            state_code = query.data.replace("state_", "").replace("_daily", "")
            country_code = context.user_data.get('selected_country_code', 'US')
            
            try:
                # تحديد اسم الولاية
                states = STATIC_DAILY_LOCATIONS[language][country_code]
                state_name = states.get(state_code, state_code)
                
                # فحص توفر الولاية لهذه الخدمة
                if not db.get_service_status('static', 'daily_static', country_code, state_code):
                    error_msg = f"🚫 عذراً، {state_name} غير متاحة حالياً في الستاتيك اليومي\n\n⚠️ تم إيقاف هذه الولاية مؤقتاً من قبل الإدارة\nيُرجى اختيار ولاية أخرى" if language == 'ar' else f"🚫 Sorry, {state_name} is not available in Daily Static\n\n⚠️ This state has been temporarily disabled\nPlease choose another state"
                    await query.edit_message_text(error_msg)
                    return
                
                context.user_data['selected_state'] = state_name
                context.user_data['selected_state_code'] = state_code
                
                # سؤال المستخدم عن الكمية قبل إنشاء الطلب
                await ask_static_proxy_quantity(query, context, language)
            except Exception as e:
                logger.error(f"Error handling daily state selection: {e}")
                await query.edit_message_text("❌ خطأ في معالجة اختيار الولاية" if language == 'ar' else "❌ Error processing state selection")
            return
        
        # معالجة خاصة لاختيار أمريكا لـ Verizon
        elif query.data == "country_US_verizon":
            context.user_data['selected_country_code'] = 'US'
            context.user_data['selected_country'] = 'الولايات المتحدة' if language == 'ar' else 'United States'
            # عرض ولايات Verizon (NY, VA, WA)
            states = US_STATES_STATIC_VERIZON[language]
            keyboard = []
            for state_code, state_name in states.items():
                keyboard.append([InlineKeyboardButton(f"📍 {state_name}", callback_data=f"state_{state_code}_verizon")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            state_text = "اختر الولاية:" if language == 'ar' else "Choose state:"
            await query.edit_message_text(state_text, reply_markup=reply_markup)
            logger.info(f"=== VERIZON US COUNTRY SELECTED ===")
            return
        
        # معالجة خاصة لاختيار أمريكا لـ Crocker
        elif query.data == "country_US_crocker":
            context.user_data['selected_country_code'] = 'US'
            context.user_data['selected_country'] = 'الولايات المتحدة' if language == 'ar' else 'United States'
            # عرض ولاية Crocker (Massachusetts فقط)
            states = US_STATES_STATIC_CROCKER[language]
            keyboard = []
            for state_code, state_name in states.items():
                keyboard.append([InlineKeyboardButton(f"📍 {state_name}", callback_data=f"state_{state_code}_crocker")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            state_text = "اختر الولاية:" if language == 'ar' else "Choose state:"
            await query.edit_message_text(state_text, reply_markup=reply_markup)
            logger.info(f"=== CROCKER US COUNTRY SELECTED ===")
            return
        
        # معالجة Residential $4 - اختيار الولايات المتحدة
        elif query.data == "res4_country_US":
            logger.info(f"Processing RES4 USA selection for user {user_id}")
            context.user_data['proxy_type'] = 'static'
            context.user_data['selected_country_code'] = 'US'
            context.user_data['selected_country'] = 'الولايات المتحدة' if language == 'ar' else 'United States'
            context.user_data['quantity'] = '5'
            
            # استخدام السعر حسب المدة المختارة بدلاً من السعر الثابت
            duration_type = context.user_data.get('res4_duration_type', 'monthly')
            res4_price = get_res4_price(duration_type)
            verizon_price = res4_price
            if language == 'ar':
                keyboard = [
                    [InlineKeyboardButton(f"🏠 Verizon (4 ولايات)", callback_data="res4_service_verizon")],
                    [InlineKeyboardButton(f"🌐 Level 3 ISP (NY)", callback_data="res4_service_level3")],
                    [InlineKeyboardButton(f"🏢 Crocker Communication (MA)", callback_data="res4_service_crocker")],
                    [InlineKeyboardButton(f"📡 Frontier Communications (VT)", callback_data="res4_service_frontier")],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="residential_4_dollar")]
                ]
                service_text = f"🇺🇸 اختر مزود الخدمة - ${verizon_price}:"
            else:
                keyboard = [
                    [InlineKeyboardButton(f"🏠 Verizon (4 states)", callback_data="res4_service_verizon")],
                    [InlineKeyboardButton(f"🌐 Level 3 ISP (NY)", callback_data="res4_service_level3")],
                    [InlineKeyboardButton(f"🏢 Crocker Communication (MA)", callback_data="res4_service_crocker")],
                    [InlineKeyboardButton(f"📡 Frontier Communications (VT)", callback_data="res4_service_frontier")],
                    [InlineKeyboardButton("🔙 Back", callback_data="residential_4_dollar")]
                ]
                service_text = f"🇺🇸 Choose Service Provider - ${verizon_price}:"
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(service_text, reply_markup=reply_markup)
            logger.info(f"=== RES4 USA SERVICE MENU SHOWN ===")
            return
        
        # معالجة Residential $4 - اختيار إنجلترا
        elif query.data == "res4_country_England":
            logger.info(f"Processing RES4 England selection for user {user_id}")
            context.user_data['proxy_type'] = 'static'
            context.user_data['selected_country_code'] = 'England'
            context.user_data['selected_country'] = 'إنجلترا' if language == 'ar' else 'England'
            context.user_data['selected_state_code'] = 'ENG'
            context.user_data['selected_state'] = 'إنجلترا' if language == 'ar' else 'England'
            context.user_data['quantity'] = '5'
            context.user_data['static_type'] = 'residential_ntt'
            
            # حفظ السعر حسب المدة المختارة
            duration_type = context.user_data.get('res4_duration_type', 'monthly')
            res4_price = get_res4_price(duration_type)
            context.user_data['payment_amount'] = float(res4_price)
            logger.info(f"England RES4 price set: ${res4_price} for duration: {duration_type}")
            
            # سؤال عن الكمية مباشرة
            await ask_static_proxy_quantity(query, context, language)
            logger.info(f"=== RES4 ENGLAND NTT SELECTED ===")
            return
        
        # معالجة Residential $4 - خدمة Verizon
        elif query.data == "res4_service_verizon":
            logger.info(f"Processing RES4 Verizon service for user {user_id}")
            context.user_data['static_type'] = 'residential_verizon'
            states = US_STATES_STATIC_VERIZON[language]
            keyboard = []
            for state_code, state_name in states.items():
                keyboard.append([InlineKeyboardButton(f"📍 {state_name}", callback_data=f"res4_state_{state_code}_verizon")])
            keyboard.append([InlineKeyboardButton("🔙 رجوع" if language == 'ar' else "🔙 Back", callback_data="res4_country_US")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            state_text = "🏠 اختر الولاية - Verizon:" if language == 'ar' else "🏠 Choose State - Verizon:"
            await query.edit_message_text(state_text, reply_markup=reply_markup)
            logger.info(f"=== RES4 VERIZON STATES SHOWN ===")
            return
        
        # معالجة Residential $4 - خدمة Level 3 ISP
        elif query.data == "res4_service_level3":
            logger.info(f"Processing RES4 Level 3 ISP service for user {user_id}")
            context.user_data['static_type'] = 'residential_level3'
            states = US_STATES_STATIC_LEVEL3[language]
            keyboard = []
            for state_code, state_name in states.items():
                keyboard.append([InlineKeyboardButton(f"📍 {state_name}", callback_data=f"res4_state_{state_code}_level3")])
            keyboard.append([InlineKeyboardButton("🔙 رجوع" if language == 'ar' else "🔙 Back", callback_data="res4_country_US")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            state_text = "🌐 اختر الولاية - Level 3 ISP:" if language == 'ar' else "🌐 Choose State - Level 3 ISP:"
            await query.edit_message_text(state_text, reply_markup=reply_markup)
            logger.info(f"=== RES4 LEVEL3 STATES SHOWN ===")
            return
        
        # معالجة Residential $4 - خدمة Crocker Communication
        elif query.data == "res4_service_crocker":
            logger.info(f"Processing RES4 Crocker service for user {user_id}")
            context.user_data['static_type'] = 'residential_crocker'
            states = US_STATES_STATIC_CROCKER[language]
            keyboard = []
            for state_code, state_name in states.items():
                keyboard.append([InlineKeyboardButton(f"📍 {state_name}", callback_data=f"res4_state_{state_code}_crocker")])
            keyboard.append([InlineKeyboardButton("🔙 رجوع" if language == 'ar' else "🔙 Back", callback_data="res4_country_US")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            state_text = "🏢 اختر الولاية - Crocker:" if language == 'ar' else "🏢 Choose State - Crocker:"
            await query.edit_message_text(state_text, reply_markup=reply_markup)
            logger.info(f"=== RES4 CROCKER STATES SHOWN ===")
            return
        
        # معالجة Residential $4 - خدمة Frontier Communications
        elif query.data == "res4_service_frontier":
            logger.info(f"Processing RES4 Frontier service for user {user_id}")
            context.user_data['static_type'] = 'residential_frontier'
            states = US_STATES_STATIC_FRONTIER[language]
            keyboard = []
            for state_code, state_name in states.items():
                keyboard.append([InlineKeyboardButton(f"📍 {state_name}", callback_data=f"res4_state_{state_code}_frontier")])
            keyboard.append([InlineKeyboardButton("🔙 رجوع" if language == 'ar' else "🔙 Back", callback_data="res4_country_US")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            state_text = "📡 اختر الولاية - Frontier:" if language == 'ar' else "📡 Choose State - Frontier:"
            await query.edit_message_text(state_text, reply_markup=reply_markup)
            logger.info(f"=== RES4 FRONTIER STATES SHOWN ===")
            return
        
        # معالجة اختيار الولايات لخدمات Residential $4
        elif query.data.startswith("res4_state_"):
            logger.info(f"Processing RES4 state selection: {query.data} for user {user_id}")
            try:
                parts = query.data.replace("res4_state_", "").split("_")
                if len(parts) >= 2:
                    state_code = parts[0]
                    service_type = parts[1]
                    
                    context.user_data['selected_state_code'] = state_code
                    
                    if service_type == 'verizon':
                        state_name = US_STATES_STATIC_VERIZON[language].get(state_code, state_code)
                        context.user_data['static_type'] = 'residential_verizon'
                    elif service_type == 'level3':
                        state_name = US_STATES_STATIC_LEVEL3[language].get(state_code, state_code)
                        context.user_data['static_type'] = 'residential_level3'
                    elif service_type == 'crocker':
                        state_name = US_STATES_STATIC_CROCKER[language].get(state_code, state_code)
                        context.user_data['static_type'] = 'residential_crocker'
                    elif service_type == 'frontier':
                        state_name = US_STATES_STATIC_FRONTIER[language].get(state_code, state_code)
                        context.user_data['static_type'] = 'residential_frontier'
                    else:
                        state_name = state_code
                    
                    context.user_data['selected_state'] = state_name
                    
                    # حفظ السعر حسب المدة المختارة
                    duration_type = context.user_data.get('res4_duration_type', 'monthly')
                    res4_price = get_res4_price(duration_type)
                    context.user_data['payment_amount'] = float(res4_price)
                    logger.info(f"RES4 {service_type} price set: ${res4_price} for duration: {duration_type}")
                    
                    # سؤال عن الكمية
                    await ask_static_proxy_quantity(query, context, language)
                    logger.info(f"=== RES4 STATE SELECTED: {state_name} ({service_type}) ===")
            except Exception as e:
                logger.error(f"Error processing RES4 state selection: {e}")
                await query.edit_message_text("❌ خطأ في معالجة الاختيار" if language == 'ar' else "❌ Error processing selection")
            return
        
        if query.data.startswith("country_"):
            country_code = query.data.replace("country_", "")
            # حفظ اسم الدولة الكامل مع العلم بدلاً من الرمز فقط
            proxy_type = context.user_data.get('proxy_type')
            if proxy_type == 'socks':
                country_name = SOCKS_COUNTRIES[language].get(country_code, country_code)
            else:
                country_name = STATIC_COUNTRIES[language].get(country_code, country_code)
            context.user_data['selected_country'] = country_name
            context.user_data['selected_country_code'] = country_code
            
            # تحديد نوع البروكسي الفرعي للستاتيك
            proxy_subtype = 'residential'  # افتراضي للريزيدنتال
            static_type = ''
            if proxy_type == 'static':
                # التحقق من نوع الستاتيك المطلوب من context
                static_type = context.user_data.get('static_type', '')
                if static_type == 'isp':
                    proxy_subtype = 'isp'
                elif static_type == 'residential_verizon':
                    proxy_subtype = 'residential_verizon'
                else:
                    proxy_subtype = 'residential'  # للريزيدنتال العادي
            
            # فحص توفر الدولة المحددة لهذه الخدمة
            service_type_for_check = None
            if proxy_type == 'static':
                if static_type == 'isp':
                    service_type_for_check = 'isp_att'
                elif static_type == 'datacenter':
                    service_type_for_check = 'datacenter'
                elif static_type == 'residential_verizon':
                    service_type_for_check = 'monthly_verizon'
                elif static_type == 'virgin_residential':
                    service_type_for_check = 'monthly_residential'
                elif static_type == 'weekly':
                    service_type_for_check = 'weekly_crocker'
                elif static_type == 'daily':
                    service_type_for_check = 'daily_static'
                else:
                    service_type_for_check = 'monthly_residential'
            
            # التحقق من حالة الدولة
            if service_type_for_check and not db.get_service_status('static', service_type_for_check, country_code):
                error_msg = f"🚫 عذراً، {country_name} غير متاحة حالياً في هذه الخدمة\n\n⚠️ تم إيقاف هذه الدولة مؤقتاً من قبل الإدارة\nيُرجى اختيار دولة أخرى أو المحاولة لاحقاً" if language == 'ar' else f"🚫 Sorry, {country_name} is not available in this service\n\n⚠️ This country has been temporarily disabled by administration\nPlease choose another country or try again later"
                await query.edit_message_text(error_msg)
                return
            
            # Virgin Residential: تخطي الولايات والانتقال مباشرة للكمية
            if static_type == 'virgin_residential':
                context.user_data['selected_state'] = country_name
                context.user_data['selected_state_code'] = country_code
                await ask_static_proxy_quantity(query, context, language)
                return
            
            # فحص وجود ولايات للدولة
            states = get_states_for_country(country_code, proxy_type, proxy_subtype)
            if states:
                # عرض الولايات
                states_dict = states.get(language, states.get('ar', {}))
                keyboard = []
                for state_code, state_name in states_dict.items():
                    keyboard.append([InlineKeyboardButton(state_name, callback_data=f"state_{state_code}")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    MESSAGES[language]['select_state'],
                    reply_markup=reply_markup
                )
            else:
                # الانتقال لاختيار الكمية إذا لم تكن هناك ولايات
                context.user_data['selected_state'] = country_name
                context.user_data['selected_state_code'] = country_code
                
                # تحديد الكمية تلقائياً بناءً على نوع الطلب
                proxy_type = context.user_data.get('proxy_type')
                quantity_type = context.user_data.get('quantity', '5')  # افتراضي 5
                
                # تحويل الكمية من string إلى int
                if isinstance(quantity_type, str):
                    try:
                        context.user_data['quantity'] = int(quantity_type)
                    except (ValueError, TypeError):
                        context.user_data['quantity'] = 5  # افتراضي
                else:
                    context.user_data['quantity'] = quantity_type or 5
                
                # للبروكسي الستاتيك: الانتقال لسؤال الكمية قبل إنشاء الطلب
                if proxy_type == 'static':
                    await ask_static_proxy_quantity(query, context, language)
                else:
                    # إنشاء الطلب مباشرة للأنواع الأخرى
                    try:
                        order_id = await create_order_directly_from_callback(update, context, language)
                        
                        # إرسال رسالة تأكيد
                        if language == 'ar':
                            success_message = f"""✅ تم إرسال طلبك بنجاح!

🆔 معرف الطلب: <code>{order_id}</code>
⏰ سيتم مراجعة طلبك من قبل الإدارة وإرسال البيانات قريباً

📞 للاستفسار عن الطلب تواصل مع الدعم"""
                        else:
                            success_message = f"""✅ Your order has been sent successfully!

🆔 Order ID: <code>{order_id}</code>
⏰ Your order will be reviewed by management and data sent soon

📞 For inquiry contact support"""
                        
                        await query.edit_message_text(success_message, parse_mode='HTML')
                        return ConversationHandler.END
                        
                    except Exception as order_error:
                        logger.error(f"Error creating order from callback: {order_error}")
                        # التحقق من نوع الخطأ لعرض الرسالة المناسبة
                        error_message = str(order_error)
                        if "رصيد غير كافي" in error_message or "Insufficient balance" in error_message:
                            # عرض رسالة الرصيد غير الكافي
                            await query.edit_message_text(error_message, parse_mode='HTML')
                        else:
                            # عرض رسالة خطأ عامة
                            await query.edit_message_text(
                                "❌ حدث خطأ في إنشاء الطلب. يرجى المحاولة مرة أخرى أو التواصل مع الدعم.",
                                parse_mode='HTML'
                            )
                        return ConversationHandler.END
        
        elif query.data.endswith("_verizon") and query.data.startswith("state_"):
            # معالجة اختيار ولاية Verizon
            state_code = query.data.replace("state_", "").replace("_verizon", "")
            context.user_data['selected_country_code'] = 'US'
            context.user_data['selected_state_code'] = state_code
            state_name = US_STATES_STATIC_VERIZON[language].get(state_code, state_code)
            
            # فحص توفر الولاية لخدمة Verizon
            if not db.get_service_status('static', 'monthly_verizon', 'US', state_code):
                error_msg = f"🚫 عذراً، {state_name} غير متاحة حالياً في Verizon Residential\n\n⚠️ تم إيقاف هذه الولاية مؤقتاً من قبل الإدارة\nيُرجى اختيار ولاية أخرى" if language == 'ar' else f"🚫 Sorry, {state_name} is not available in Verizon Residential\n\n⚠️ This state has been temporarily disabled\nPlease choose another state"
                await query.edit_message_text(error_msg)
                return
            
            context.user_data['selected_state'] = state_name
            # الانتقال لسؤال الكمية
            await ask_static_proxy_quantity(query, context, language)
            logger.info(f"=== VERIZON STATE SELECTED: {state_code} ===")
            
        elif query.data.endswith("_crocker") and query.data.startswith("state_"):
            # معالجة اختيار ولاية Crocker
            state_code = query.data.replace("state_", "").replace("_crocker", "")
            context.user_data['selected_country_code'] = 'US'
            context.user_data['selected_state_code'] = state_code
            state_name = US_STATES_STATIC_CROCKER[language].get(state_code, state_code)
            
            # فحص توفر الولاية لخدمة Crocker (residential $4)
            if not db.get_service_status('static', 'monthly_verizon', 'US', state_code):
                error_msg = f"🚫 عذراً، {state_name} غير متاحة حالياً في Crocker Residential\n\n⚠️ تم إيقاف هذه الولاية مؤقتاً من قبل الإدارة\nيُرجى اختيار ولاية أخرى" if language == 'ar' else f"🚫 Sorry, {state_name} is not available in Crocker Residential\n\n⚠️ This state has been temporarily disabled\nPlease choose another state"
                await query.edit_message_text(error_msg)
                return
            
            context.user_data['selected_state'] = state_name
            # الانتقال لسؤال الكمية
            await ask_static_proxy_quantity(query, context, language)
            logger.info(f"=== CROCKER STATE SELECTED: {state_code} ===")
            
        elif query.data.startswith("state_"):
            # معالجة اختيار الولاية
            state_code = query.data.replace("state_", "")
            country_code = context.user_data.get('selected_country_code', '')
            
            # حفظ الولاية المختارة
            proxy_type = context.user_data.get('proxy_type')
            proxy_subtype = 'residential'
            service_type_for_check = None
            
            if proxy_type == 'static':
                static_type = context.user_data.get('static_type', '')
                if static_type == 'isp':
                    proxy_subtype = 'isp'
                    service_type_for_check = 'isp_att'
                elif static_type == 'datacenter':
                    service_type_for_check = 'datacenter'
                elif static_type == 'virgin_residential':
                    service_type_for_check = 'monthly_residential'
                else:
                    service_type_for_check = 'monthly_residential'
            
            states = get_states_for_country(country_code, proxy_type, proxy_subtype)
            if states:
                state_name = states.get(language, states.get('ar', {})).get(state_code, state_code)
                
                # فحص توفر الولاية لهذه الخدمة
                if service_type_for_check and not db.get_service_status('static', service_type_for_check, country_code, state_code):
                    error_msg = f"🚫 عذراً، {state_name} غير متاحة حالياً في هذه الخدمة\n\n⚠️ تم إيقاف هذه الولاية مؤقتاً من قبل الإدارة\nيُرجى اختيار ولاية أخرى" if language == 'ar' else f"🚫 Sorry, {state_name} is not available in this service\n\n⚠️ This state has been temporarily disabled\nPlease choose another state"
                    await query.edit_message_text(error_msg)
                    return
                
                context.user_data['selected_state'] = state_name
                context.user_data['selected_state_code'] = state_code
                
                # التأكد من حفظ اسم الدولة أيضاً (مهم للسوكس مع الولايات)
                if not context.user_data.get('selected_country'):
                    if proxy_type == 'socks':
                        country_name = SOCKS_COUNTRIES[language].get(country_code, country_code)
                    else:
                        country_name = STATIC_COUNTRIES[language].get(country_code, country_code)
                    context.user_data['selected_country'] = country_name
            
            # تحديد الكمية تلقائياً بناءً على نوع الطلب
            quantity_type = context.user_data.get('quantity', '5')  # افتراضي 5
            
            # تحويل الكمية من string إلى int
            if isinstance(quantity_type, str):
                try:
                    context.user_data['quantity'] = int(quantity_type)
                except (ValueError, TypeError):
                    context.user_data['quantity'] = 5  # افتراضي
            else:
                context.user_data['quantity'] = quantity_type or 5
            
            # للبروكسي الستاتيك: الانتقال لسؤال الكمية قبل إنشاء الطلب
            # للسوكس: الكمية محددة بالفعل، إنشاء الطلب مباشرة
            if proxy_type == 'static':
                await ask_static_proxy_quantity(query, context, language)
            else:
                # إنشاء الطلب مباشرة للأنواع الأخرى
                try:
                    order_id = await create_order_directly_from_callback(update, context, language)
                    
                    # إرسال رسالة تأكيد
                    if language == 'ar':
                        success_message = f"""✅ تم إرسال طلبك بنجاح!

🆔 معرف الطلب: {order_id}
⏰ سيتم مراجعة طلبك من قبل الإدارة وإرسال البيانات قريباً

📞 للاستفسار عن الطلب تواصل مع الدعم"""
                    else:
                        success_message = f"""✅ Your order has been sent successfully!

🆔 Order ID: {order_id}
⏰ Your order will be reviewed by management and data sent soon

📞 For inquiry contact support"""
                    
                    await query.edit_message_text(success_message, parse_mode='HTML')
                    return ConversationHandler.END
                    
                except Exception as order_error:
                    logger.error(f"Error creating order from callback: {order_error}")
                    # التحقق من نوع الخطأ لعرض الرسالة المناسبة
                    error_message = str(order_error)
                    if "رصيد غير كافي" in error_message or "Insufficient balance" in error_message:
                        # عرض رسالة الرصيد غير الكافي
                        await query.edit_message_text(error_message, parse_mode='HTML')
                    else:
                        # عرض رسالة خطأ عامة
                        await query.edit_message_text(
                            "❌ حدث خطأ في إنشاء الطلب. يرجى المحاولة مرة أخرى أو التواصل مع الدعم.",
                            parse_mode='HTML'
                        )
                    return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in show_payment_methods: {e}")
        
        try:
            # محاولة إرسال رسالة خطأ بسيطة
            await query.message.reply_text(
                "⚠️ حدث خطأ في عرض طرق الدفع. يرجى استخدام /start لإعادة المحاولة.",
                reply_markup=ReplyKeyboardRemove()
            )
        except Exception as recovery_error:
            logger.error(f"Failed to send error message in show_payment_methods: {recovery_error}")

async def handle_payment_method_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار طريقة الدفع"""
    try:
        query = update.callback_query
        user_id = update.effective_user.id
        
        # تسجيل الإجراء
        logger.info(f"User {user_id} selected payment method: {query.data}")
        
        try:
            await query.answer()
        except Exception as answer_error:
            logger.warning(f"Failed to answer payment callback for user {user_id}: {answer_error}")
        
        language = get_user_language(user_id)
        
        payment_method = query.data.replace("payment_", "")
        context.user_data['payment_method'] = payment_method
        
        # فحص نوع البروكسي - إذا كان سوكس، تخطى سؤال الكمية (تم تحديدها بالفعل)
        proxy_type = context.user_data.get('proxy_type')
        
        if proxy_type == 'socks':
            # للسوكس: الكمية محددة بالفعل، انتقل مباشرة لإثبات الدفع
            await query.edit_message_text(
                MESSAGES[language]['send_payment_proof']
            )
            return PAYMENT_PROOF
        else:
            # للستاتيك: اسأل عن الكمية كالمعتاد
            # إضافة زر الإلغاء
            if language == 'ar':
                keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_payment_proof")]]
            else:
                keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="cancel_payment_proof")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # تحديد الكمية تلقائياً بناءً على نوع الطلب
            quantity_type = context.user_data.get('quantity', '5')  # افتراضي 5
            
            # تحويل الكمية من string إلى int
            if isinstance(quantity_type, str):
                try:
                    context.user_data['quantity'] = int(quantity_type)
                except (ValueError, TypeError):
                    context.user_data['quantity'] = 5  # افتراضي
            else:
                context.user_data['quantity'] = quantity_type or 5
            
            # إنشاء الطلب مباشرة
            try:
                order_id = await create_order_directly_from_callback(update, context, language)
                
                # إرسال رسالة تأكيد
                if language == 'ar':
                    success_message = f"""✅ تم إرسال طلبك بنجاح!

🆔 معرف الطلب: <code>{order_id}</code>
⏰ سيتم مراجعة طلبك من قبل الإدارة وإرسال البيانات قريباً

📞 للاستفسار عن الطلب تواصل مع الدعم"""
                else:
                    success_message = f"""✅ Your order has been sent successfully!

🆔 Order ID: <code>{order_id}</code>
⏰ Your order will be reviewed by management and data sent soon

📞 For inquiry contact support"""
                
                await query.edit_message_text(success_message, parse_mode='HTML')
                return ConversationHandler.END
                
            except Exception as order_error:
                logger.error(f"Error creating order from callback in payment method: {order_error}")
                await query.edit_message_text(
                    "❌ حدث خطأ في إنشاء الطلب. يرجى المحاولة مرة أخرى أو التواصل مع الدعم.",
                    parse_mode='HTML'
                )
                return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in handle_payment_method_selection for user {user_id}: {e}")
        
        try:
            await update.callback_query.message.reply_text(
                "⚠️ حدث خطأ في معالجة طريقة الدفع. تم إعادة تعيين حالتك.\n"
                "يرجى استخدام /start لإعادة المحاولة.",
                reply_markup=ReplyKeyboardRemove()
            )
            # تنظيف البيانات المؤقتة
            context.user_data.clear()
            
        except Exception as recovery_error:
            logger.error(f"Failed to send error message in payment method selection: {recovery_error}")
        
        return ConversationHandler.END

async def ask_static_proxy_quantity(query, context: ContextTypes.DEFAULT_TYPE, language: str) -> None:
    """سؤال المستخدم عن كمية البروكسي الستاتيك (1-100)"""
    try:
        if language == 'ar':
            message = """🔢 اختر كمية البروكسي المطلوبة:

⚠️ يجب أن تكون الكمية من 1 إلى 100

📝 اكتب الرقم المطلوب:"""
        else:
            message = """🔢 Choose the required proxy quantity:

⚠️ Quantity must be between 1 and 100

📝 Enter the required number:"""
        
        # وضع علامة أننا في مرحلة انتظار الكمية
        context.user_data['waiting_for_static_quantity'] = True
        
        await query.edit_message_text(message, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error in ask_static_proxy_quantity: {e}")
        await query.edit_message_text(
            "❌ حدث خطأ في عرض خيارات الكمية. يرجى المحاولة مرة أخرى.",
            parse_mode='HTML'
        )

async def handle_static_quantity_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة إدخال كمية البروكسي الستاتيك"""
    try:
        user_id = update.effective_user.id
        language = get_user_language(user_id)
        
        # التحقق من أننا في انتظار كمية ستاتيك
        if not context.user_data.get('waiting_for_static_quantity'):
            return
        
        quantity_text = update.message.text.strip()
        
        # التحقق من أن النص يحتوي على رقم صحيح فقط
        if not quantity_text.isdigit():
            if language == 'ar':
                await update.message.reply_text(
                    "❌ يرجى إدخال رقم صحيح فقط (من 1 إلى 100)",
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text(
                    "❌ Please enter a valid number only (1 to 100)",
                    parse_mode='HTML'
                )
            return
        
        quantity = int(quantity_text)
        
        # التحقق من أن العدد بين 1 و 100
        if quantity < 1 or quantity > 100:
            if language == 'ar':
                await update.message.reply_text(
                    "❌ الكمية يجب أن تكون بين 1 و 100",
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text(
                    "❌ Quantity must be between 1 and 100",
                    parse_mode='HTML'
                )
            return
        
        # حفظ الكمية وإزالة علامة الانتظار
        context.user_data['quantity'] = quantity
        context.user_data.pop('waiting_for_static_quantity', None)
        
        # التحقق من الرصيد قبل إنشاء الطلب
        try:
            # حساب التكلفة الإجمالية
            proxy_type = context.user_data.get('proxy_type', 'static')
            selected_country = context.user_data.get('selected_country', 'US')
            selected_state = context.user_data.get('selected_state', '')
            static_type = context.user_data.get('static_type', '')
            
            # حساب سعر الوحدة
            # للخدمات Residential Super، استخدام السعر المحفوظ في payment_amount
            if 'payment_amount' in context.user_data and static_type in ['residential_ntt', 'residential_verizon', 'residential_crocker', 'residential_level3', 'residential_frontier']:
                unit_price = context.user_data['payment_amount']
                total_cost = unit_price * quantity
            else:
                unit_price = get_proxy_price(proxy_type, selected_country, selected_state, static_type, context.user_data.get("res4_duration_type", ""))
                if unit_price is None:
                    # إذا رجع None، استخدم payment_amount المحفوظ
                    unit_price = context.user_data.get('payment_amount', 4.0)
                total_cost = unit_price * quantity
            
            # الحصول على رصيد المستخدم الحالي
            user = db.get_user(user_id)
            if not user:
                raise ValueError("User not found")
            
            current_balance = float(user[6]) if user[6] else 0.0  # الرصيد في العمود السابع (points_balance)
            
            # التحقق من كفاية الرصيد
            if current_balance < total_cost:
                if language == 'ar':
                    insufficient_message = f"""❌ رصيد غير كافي

💰 التكلفة الإجمالية: <code>${total_cost:.2f}</code>
📊 الكمية: <code>{quantity}</code>
💵 سعر الوحدة: <code>${unit_price:.2f}</code>
💳 رصيدك الحالي: <code>${current_balance:.2f}</code>
📉 المطلوب إضافياً: <code>${(total_cost - current_balance):.2f}</code>

🔄 يرجى شحن رصيدك أولاً ثم إعادة المحاولة"""
                else:
                    insufficient_message = f"""❌ Insufficient balance

💰 Total cost: <code>${total_cost:.2f}</code>
📊 Quantity: <code>{quantity}</code>
💵 Unit price: <code>${unit_price:.2f}</code>
💳 Your current balance: <code>${current_balance:.2f}</code>
📉 Additional required: <code>${(total_cost - current_balance):.2f}</code>

🔄 Please recharge your balance first and try again"""
                
                await update.message.reply_text(insufficient_message, parse_mode='HTML')
                return
            
            # إظهار تأكيد التكلفة قبل المتابعة
            if language == 'ar':
                confirmation_message = f"""✅ تم التحقق من الرصيد بنجاح

💰 التكلفة الإجمالية: <code>${total_cost:.2f}</code>
📊 الكمية: <code>{quantity}</code>
💵 سعر الوحدة: <code>${unit_price:.2f}</code>
💳 رصيدك بعد الشراء: <code>${(current_balance - total_cost):.2f}</code>

⏳ جارِ إنشاء طلبك..."""
            else:
                confirmation_message = f"""✅ Balance verified successfully

💰 Total cost: <code>${total_cost:.2f}</code>
📊 Quantity: <code>{quantity}</code>
💵 Unit price: <code>${unit_price:.2f}</code>
💳 Your balance after purchase: <code>${(current_balance - total_cost):.2f}</code>

⏳ Creating your order..."""
            
            await update.message.reply_text(confirmation_message, parse_mode='HTML')
            
        except Exception as balance_error:
            logger.error(f"Error checking balance: {balance_error}")
            if language == 'ar':
                await update.message.reply_text(
                    """❌ خطأ في النظام المالي

🔄 فشل في التحقق من رصيدك الحالي
⚠️ قد يكون هناك مشكلة مؤقتة في قاعدة البيانات

🔧 الحلول الممكنة:
• انتظر دقيقة واحدة ثم حاول مرة أخرى
• استخدم /start لإعادة تشغيل البوت
• تواصل مع الدعم إذا استمرت المشكلة

📞 للمساعدة: @@Static_support""",
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text(
                    """❌ Financial System Error

🔄 Failed to check your current balance
⚠️ There may be a temporary database issue

🔧 Possible solutions:
• Wait one minute and try again
• Use /start to restart the bot
• Contact support if the problem persists

📞 For help: @@Static_support""",
                    parse_mode='HTML'
                )
            return
        
        # إنشاء الطلب الآن (بعد التحقق من الرصيد)
        try:
            order_id = await create_order_directly_from_message(update, context, language)
            
            # إرسال رسالة تأكيد
            if language == 'ar':
                success_message = f"""✅ تم إرسال طلبك بنجاح!

🆔 معرف الطلب: <code>{order_id}</code>
🔢 الكمية: {quantity}
⏰ سيتم مراجعة طلبك من قبل الإدارة وإرسال البيانات قريباً

📞 للاستفسار عن الطلب تواصل مع الدعم"""
            else:
                success_message = f"""✅ Your order has been sent successfully!

🆔 Order ID: <code>{order_id}</code>
🔢 Quantity: {quantity}
⏰ Your order will be reviewed by management and data sent soon

📞 For inquiry contact support"""
            
            await update.message.reply_text(success_message, parse_mode='HTML')
            
        except Exception as order_error:
            logger.error(f"Error creating order after quantity input: {order_error}")
            # التحقق من نوع الخطأ لعرض الرسالة المناسبة
            error_message = str(order_error)
            if "رصيد غير كافي" in error_message or "Insufficient balance" in error_message:
                # عرض رسالة الرصيد غير الكافي
                await update.message.reply_text(error_message, parse_mode='HTML')
            else:
                # عرض رسالة خطأ عامة
                await update.message.reply_text(
                    "❌ حدث خطأ في إنشاء الطلب. يرجى المحاولة مرة أخرى أو التواصل مع الدعم.",
                    parse_mode='HTML'
                )
        
    except Exception as e:
        logger.error(f"Error in handle_static_quantity_input: {e}")
        language = get_user_language(update.effective_user.id)
        if language == 'ar':
            await update.message.reply_text(
                "❌ حدث خطأ في معالجة الكمية. يرجى المحاولة مرة أخرى.",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "❌ Error processing quantity. Please try again.",
                parse_mode='HTML'
            )

async def create_order_directly_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, language: str) -> str:
    """إنشاء الطلب مباشرة من callback query بدون طرق الدفع وإثبات الدفع"""
    try:
        user_id = update.effective_user.id if update.effective_user else update.callback_query.from_user.id
        
        # التحقق من وجود البيانات المطلوبة
        if 'proxy_type' not in context.user_data:
            raise ValueError("Proxy type not found")

        # إنشاء معرف الطلب
        try:
            order_id = generate_order_id()
        except Exception as id_error:
            logger.error(f"Error generating order ID: {id_error}")
            raise ValueError(f"Failed to generate order ID: {id_error}")
        
        # جمع بيانات الطلب
        proxy_type = context.user_data.get('proxy_type', 'socks')
        quantity = context.user_data.get('quantity', 5)
        # التأكد من أن quantity هو int (إصلاح مشكلة سوكس أمريكا)
        if isinstance(quantity, str):
            try:
                quantity = int(quantity)
            except (ValueError, TypeError):
                quantity = 5
        selected_country = context.user_data.get('selected_country', '')
        selected_state = context.user_data.get('selected_state', '')
        payment_method = context.user_data.get('payment_method', 'balance')
        
        # التحقق من وجود البيانات الأساسية
        if not selected_country:
            raise ValueError("Country not selected. Please start the order process again.")
        
        # حساب السعر الإجمالي
        try:
            # للسوكس: استخدام السعر المحفوظ مسبقاً
            if proxy_type == 'socks' and 'socks_price' in context.user_data:
                unit_price = context.user_data['socks_price']
            else:
                # للستاتيك: استخدام get_proxy_price مع static_type
                static_type = context.user_data.get('static_type', '')
                # للخدمات Residential Super، استخدام السعر المحفوظ في payment_amount
                if 'payment_amount' in context.user_data and static_type in ['residential_ntt', 'residential_verizon', 'residential_crocker', 'residential_level3', 'residential_frontier']:
                    unit_price = context.user_data['payment_amount']
                else:
                    unit_price = get_proxy_price(proxy_type, selected_country, selected_state, static_type, context.user_data.get("res4_duration_type", ""))
                    if unit_price is None:
                        # إذا رجع None، استخدم payment_amount المحفوظ
                        unit_price = context.user_data.get('payment_amount', 4.0)
            
            # التحقق إذا كان باكج (لا يتم ضرب السعر بالكمية)
            is_package = context.user_data.get('is_package', False)
            if is_package:
                total_price = unit_price  # السعر للباكج كله بدون ضرب
            else:
                total_price = unit_price * quantity
        except Exception as price_error:
            logger.error(f"Error calculating price: {price_error}")
            logger.error(f"Price calculation params: proxy_type={proxy_type}, country={selected_country}, state={selected_state}")
            raise ValueError(f"Failed to calculate price: {price_error}")
        
        # التحقق من كفاية الرصيد قبل إنشاء الطلب
        try:
            user_balance = db.get_user_balance(user_id)
            available_points = user_balance['total_balance']  # استخدام المجموع الكامل
            
            if available_points < total_price:
                # رصيد غير كافي - منع إنشاء الطلب
                user_language = get_user_language(user_id) if 'get_user_language' in globals() else 'ar'
                if user_language == 'ar':
                    raise ValueError(f"❌ رصيد غير كافي!\n\n💰 النقاط المطلوبة: {total_price:.2f} نقطة\n💎 رصيدك الحالي: {available_points:.2f} نقطة\n\n📞 يرجى شحن رصيدك أو التواصل مع الإدارة.")
                else:
                    raise ValueError(f"❌ Insufficient balance!\n\n💰 Points required: {total_price:.2f} points\n💎 Current balance: {available_points:.2f} points\n\n📞 Please recharge your balance or contact admin.")
                    
        except Exception as balance_error:
            if "رصيد غير كافي" in str(balance_error) or "Insufficient balance" in str(balance_error):
                # إعادة رمي خطأ الرصيد غير الكافي
                raise balance_error
            else:
                logger.error(f"Error checking balance: {balance_error}")
                raise ValueError(f"خطأ في التحقق من الرصيد: {balance_error}")
        
        # إدخال الطلب في قاعدة البيانات
        try:
            db.execute_query(
                """
                INSERT INTO orders (
                    id, user_id, proxy_type, quantity, country, state, duration, 
                    payment_method, payment_amount, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (order_id, user_id, proxy_type, quantity, selected_country, 
                 selected_state, context.user_data.get('res4_duration', ''), payment_method, total_price, 'pending', datetime.now().isoformat())
            )
            
            logger.info(f"Order created successfully from callback: {order_id} for user {user_id}")
            
            # إرسال إشعار للأدمن باستخدام send_admin_notification_with_details
            try:
                user_language = get_user_language(user_id)
                static_type = context.user_data.get('static_type', '')
                
                await send_admin_notification_with_details(
                    context, order_id, user_id, proxy_type, selected_country,
                    selected_state, total_price, user_language, quantity, static_type, context.user_data.get("res4_duration", "")
                )
                
                logger.info(f"Admin notification sent for order: {order_id}")
                    
            except Exception as e:
                # تسجيل الخطأ فقط دون رفع Exception - الطلب تم إنشاؤه بنجاح
                logger.error(f"Error sending admin notification for order {order_id}: {e}")
                logger.error(f"Order data: proxy_type={proxy_type}, country={selected_country}, state={selected_state}")
            
            return order_id
            
        except Exception as db_error:
            logger.error(f"Database error creating order from callback: {db_error}")
            raise
            
    except Exception as e:
        # التحقق إذا كان الخطأ بسبب الرصيد غير الكافي - رفع Exception فقط في هذه الحالة
        if "رصيد غير كافي" in str(e) or "Insufficient balance" in str(e):
            raise
        # تسجيل الأخطاء الأخرى دون رفع Exception إذا كان الطلب تم إنشاؤه
        logger.error(f"Error in create_order_directly_from_callback: {e}")
        # إذا كان هناك order_id، الطلب تم إنشاؤه بنجاح
        if 'order_id' in locals():
            return order_id
        raise

async def create_order_directly_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE, language: str) -> str:
    """إنشاء الطلب مباشرة من رسالة نصية بدون طرق الدفع وإثبات الدفع"""
    try:
        user_id = update.effective_user.id
        
        # التحقق من وجود البيانات المطلوبة
        if 'proxy_type' not in context.user_data:
            raise ValueError("Proxy type not found")

        # إنشاء معرف الطلب
        try:
            order_id = generate_order_id()
        except Exception as id_error:
            logger.error(f"Error generating order ID: {id_error}")
            raise ValueError(f"Failed to generate order ID: {id_error}")
        context.user_data['current_order_id'] = order_id
        
        # جمع بيانات الطلب
        proxy_type = context.user_data.get('proxy_type')
        country = context.user_data.get('selected_country', 'manual')
        state = context.user_data.get('selected_state', 'manual')
        quantity = context.user_data.get('quantity', '1')
        
        # حساب سعر البروكسي
        # للسوكس: استخدام السعر المحفوظ مسبقاً
        if proxy_type == 'socks' and 'socks_price' in context.user_data:
            unit_price = context.user_data['socks_price']
        else:
            # للستاتيك: استخدام get_proxy_price مع static_type
            static_type = context.user_data.get('static_type', '')
            unit_price = get_proxy_price(proxy_type, country, state, static_type, context.user_data.get("res4_duration_type", ""))
        
        # تحويل الكمية إلى رقم صحيح
        try:
            quantity_int = int(quantity)
        except (ValueError, TypeError):
            quantity_int = 1
        
        # حساب التكلفة الإجمالية
        total_cost = unit_price * quantity_int
        
        # التحقق من الرصيد قبل إنشاء الطلب
        user = db.get_user(user_id)
        if not user:
            raise ValueError("User not found")
        
        current_balance = float(user[6]) if user[6] else 0.0
        
        # التحقق من كفاية الرصيد
        if current_balance < total_cost:
            if language == 'ar':
                insufficient_message = f"""❌ رصيد غير كافي

💰 التكلفة الإجمالية: ${total_cost:.2f}
📊 الكمية: {quantity_int}
💵 سعر الوحدة: ${unit_price:.2f}
💳 رصيدك الحالي: ${current_balance:.2f}
📉 المطلوب إضافياً: ${(total_cost - current_balance):.2f}

🔄 يرجى شحن رصيدك أولاً ثم إعادة المحاولة"""
            else:
                insufficient_message = f"""❌ Insufficient balance

💰 Total cost: ${total_cost:.2f}
📊 Quantity: {quantity_int}
💵 Unit price: ${unit_price:.2f}
💳 Your current balance: ${current_balance:.2f}
📉 Additional required: ${(total_cost - current_balance):.2f}

🔄 Please recharge your balance first and try again"""
            
            raise ValueError(insufficient_message)
        
        # استخدام total_cost بدلاً من payment_amount
        payment_amount = total_cost
        
        # إنشاء الطلب في قاعدة البيانات بدون payment_method (سيتم استخدام 'points' كقيمة افتراضية)
        # التحقق من وجود البيانات الكاملة
        if not all([order_id, user_id, proxy_type, country, state]):
            raise ValueError("Missing required order data")
        
        # استخدام create_order مع 'points' كطريقة الدفع الافتراضية
        db.create_order(order_id, user_id, proxy_type, country, state, 'points', payment_amount, str(quantity))
        
        # تحديث static_type إذا كان متوفراً
        if static_type:
            db.execute_query(
                "UPDATE orders SET static_type = ? WHERE id = ?",
                (static_type, order_id)
            )
        
        logger.info(f"Order created successfully: {order_id} for user {user_id}")

        # إرسال إشعار للأدمن
        try:
            global ACTIVE_ADMINS
            if ACTIVE_ADMINS:
                admin_message = create_admin_notification_message(order_id, user_id, proxy_type, country, state, payment_amount, language, quantity, static_type, context.user_data.get("res4_duration", ""))
                
                keyboard = [[InlineKeyboardButton("⚡ معالجة الطلب", callback_data=f"process_{order_id}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # إرسال الإشعار لجميع الآدمن النشطين
                for admin_id in ACTIVE_ADMINS:
                    try:
                        await context.bot.send_message(
                            admin_id,
                            admin_message,
                            reply_markup=reply_markup,
                            parse_mode='HTML'
                        )
                    except Exception as admin_error:
                        logger.error(f"Error sending notification to admin {admin_id}: {admin_error}")
                
                logger.info(f"Admin notification sent for order: {order_id}")
                
        except Exception as e:
            logger.error(f"Error sending admin notification for order {order_id}: {e}")
        
        # تسجيل العملية
        try:
            db.log_action(user_id, "order_created_directly", order_id)
        except Exception as e:
            logger.error(f"Error logging action for order {order_id}: {e}")

        # تنظيف البيانات المؤقتة وإنهاء المحادثة مع الحفاظ على حالة الأدمن
        clean_user_data_preserve_admin(context)
        
        return order_id
        
    except Exception as e:
        logger.error(f"Error in create_order_directly_from_message for user {user_id}: {e}")
        raise e

async def create_order_directly(query, context: ContextTypes.DEFAULT_TYPE, language: str) -> None:
    """إنشاء الطلب مباشرة بدون طرق الدفع وإثبات الدفع"""
    try:
        user_id = query.from_user.id
        
        # التحقق من وجود البيانات المطلوبة
        if 'proxy_type' not in context.user_data:
            await query.edit_message_text(
                "❌ خطأ: لم يتم العثور على نوع البروكسي. يرجى البدء من جديد بالضغط على /start" if language == 'ar' else 
                "❌ Error: Proxy type not found. Please start over with /start"
            )
            return

        # إنشاء معرف الطلب
        try:
            order_id = generate_order_id()
        except Exception as id_error:
            logger.error(f"Error generating order ID: {id_error}")
            raise ValueError(f"Failed to generate order ID: {id_error}")
        context.user_data['current_order_id'] = order_id
        
        # جمع بيانات الطلب
        proxy_type = context.user_data.get('proxy_type')
        country = context.user_data.get('selected_country', 'manual')
        state = context.user_data.get('selected_state', 'manual')
        quantity = context.user_data.get('quantity', '1')
        
        # حساب سعر البروكسي
        # للسوكس: استخدام السعر المحفوظ مسبقاً
        if proxy_type == 'socks' and 'socks_price' in context.user_data:
            unit_price = context.user_data['socks_price']
        else:
            # للستاتيك: استخدام get_proxy_price مع static_type
            static_type = context.user_data.get('static_type', '')
            unit_price = get_proxy_price(proxy_type, country, state, static_type, context.user_data.get("res4_duration_type", ""))
        
        # تحويل الكمية إلى رقم صحيح
        try:
            quantity_int = int(quantity)
        except (ValueError, TypeError):
            quantity_int = 1
        
        # حساب التكلفة الإجمالية
        total_cost = unit_price * quantity_int
        
        # التحقق من الرصيد قبل إنشاء الطلب
        try:
            user = db.get_user(user_id)
            if not user:
                await query.edit_message_text(
                    "❌ خطأ: لم يتم العثور على المستخدم" if language == 'ar' else 
                    "❌ Error: User not found"
                )
                return
            
            current_balance = float(user[6]) if user[6] else 0.0
            
            # التحقق من كفاية الرصيد
            if current_balance < total_cost:
                if language == 'ar':
                    insufficient_message = f"""❌ رصيد غير كافي

💰 التكلفة الإجمالية: <code>${total_cost:.2f}</code>
📊 الكمية: <code>{quantity_int}</code>
💵 سعر الوحدة: <code>${unit_price:.2f}</code>
💳 رصيدك الحالي: <code>${current_balance:.2f}</code>
📉 المطلوب إضافياً: <code>${(total_cost - current_balance):.2f}</code>

🔄 يرجى شحن رصيدك أولاً ثم إعادة المحاولة"""
                else:
                    insufficient_message = f"""❌ Insufficient balance

💰 Total cost: <code>${total_cost:.2f}</code>
📊 Quantity: <code>{quantity_int}</code>
💵 Unit price: <code>${unit_price:.2f}</code>
💳 Your current balance: <code>${current_balance:.2f}</code>
📉 Additional required: <code>${(total_cost - current_balance):.2f}</code>

🔄 Please recharge your balance first and try again"""
                
                await query.edit_message_text(insufficient_message, parse_mode='HTML')
                return
            
        except Exception as balance_error:
            logger.error(f"Error checking balance in create_order_directly: {balance_error}")
            if language == 'ar':
                error_message = """❌ خطأ في النظام المالي

🔄 فشل في التحقق من رصيدك قبل إنشاء الطلب
⚠️ قد يكون هناك مشكلة مؤقتة في قاعدة البيانات

🔧 الحلول الممكنة:
• انتظر دقيقة واحدة ثم حاول مرة أخرى
• استخدم /start لإعادة تشغيل البوت
• تواصل مع الدعم إذا استمرت المشكلة

📞 للمساعدة: @@Static_support"""
            else:
                error_message = """❌ Financial System Error

🔄 Failed to check your balance before creating order
⚠️ There may be a temporary database issue

🔧 Possible solutions:
• Wait one minute and try again
• Use /start to restart the bot
• Contact support if the problem persists

📞 For help: @@Static_support"""
            
            await query.edit_message_text(error_message, parse_mode='HTML')
            return
        
        # استخدام total_cost بدلاً من payment_amount
        payment_amount = total_cost
        
        # إنشاء الطلب في قاعدة البيانات بدون payment_method (سيتم استخدام 'points' كقيمة افتراضية)
        try:
            # التحقق من وجود البيانات الكاملة
            if not all([order_id, user_id, proxy_type, country, state]):
                raise ValueError("Missing required order data")
            
            # استخدام create_order مع 'points' كطريقة الدفع الافتراضية
            db.create_order(order_id, user_id, proxy_type, country, state, 'points', payment_amount, str(quantity))
            
            # تحديث static_type إذا كان متوفراً
            if static_type:
                db.execute_query(
                    "UPDATE orders SET static_type = ? WHERE id = ?",
                    (static_type, order_id)
                )
            
            logger.info(f"Order created successfully: {order_id} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            # إضافة معلومات debug أكثر
            logger.error(f"Order data: proxy_type={proxy_type}, country={country}, state={state}, quantity={quantity}")
            await query.edit_message_text(
                "❌ حدث خطأ في إنشاء الطلب. يرجى المحاولة مرة أخرى." if language == 'ar' else 
                "❌ Error creating order. Please try again."
            )
            return

        # إرسال إشعار للأدمن
        try:
            global ACTIVE_ADMINS
            if ACTIVE_ADMINS:
                admin_message = create_admin_notification_message(order_id, user_id, proxy_type, country, state, payment_amount, language, quantity, static_type, context.user_data.get("res4_duration", ""))
                
                keyboard = [[InlineKeyboardButton("⚡ معالجة الطلب", callback_data=f"process_{order_id}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # إرسال الإشعار لجميع الآدمن النشطين
                for admin_id in ACTIVE_ADMINS:
                    try:
                        await context.bot.send_message(
                            admin_id,
                            admin_message,
                            reply_markup=reply_markup,
                            parse_mode='HTML'
                        )
                    except Exception as admin_error:
                        logger.error(f"Error sending notification to admin {admin_id}: {admin_error}")
                
                logger.info(f"Admin notification sent for order: {order_id}")
                
        except Exception as e:
            logger.error(f"Error sending admin notification for order {order_id}: {e}")

        # إرسال رسالة تأكيد للمستخدم (مختصرة)
        if language == 'ar':
            user_message = f"""✅ تم إنشاء الطلب بنجاح!

📋 رقم الطلب: <code>{order_id}</code>
📦 {proxy_type} - {country}
🛒 الكمية: {quantity} × {payment_amount:.2f}$

⏳ سيتم معالجة طلبك قريباً.
💳 سيتم اقتطاع الرصيد عند نجاح الطلب واستلامك الخدمة."""
        else:
            user_message = f"""✅ Order Created Successfully!

📋 Order ID: <code>{order_id}</code>
📦 {proxy_type} - {country}
🛒 Quantity: {quantity} × ${payment_amount:.2f}

⏳ Your order will be processed soon.
💳 Balance will be deducted upon order success and service delivery."""

        await query.edit_message_text(user_message, parse_mode='HTML')
        
        # تسجيل العملية
        try:
            db.log_action(user_id, "order_created_directly", order_id)
        except Exception as e:
            logger.error(f"Error logging action for order {order_id}: {e}")

        # تنظيف البيانات المؤقتة وإنهاء المحادثة مع الحفاظ على حالة الأدمن
        clean_user_data_preserve_admin(context)
        
    except Exception as e:
        logger.error(f"Error in create_order_directly for user {user_id}: {e}")
        try:
            await query.edit_message_text(
                "❌ حدث خطأ أثناء إنشاء الطلب. يرجى المحاولة مرة أخرى أو التواصل مع الدعم." if language == 'ar' else
                "❌ Error occurred while creating order. Please try again or contact support."
            )
        except:
            pass

async def handle_payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إثبات الدفع"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    try:
        # التحقق من وجود البيانات المطلوبة
        if 'proxy_type' not in context.user_data:
            await update.message.reply_text(
                "❌ خطأ: لم يتم العثور على نوع البروكسي. يرجى البدء من جديد بالضغط على /start",
                parse_mode='HTML'
            )
            clean_user_data_preserve_admin(context)
            return ConversationHandler.END
        
        # إنشاء معرف الطلب الآن فقط عند إرسال إثبات الدفع
        order_id = generate_order_id()
        context.user_data['current_order_id'] = order_id
        
        # إنشاء الطلب في قاعدة البيانات
        proxy_type = context.user_data.get('proxy_type')
        country = context.user_data.get('selected_country', 'manual')
        state = context.user_data.get('selected_state', 'manual')
        payment_method = context.user_data.get('payment_method', 'unknown')
        
        # حساب سعر البروكسي
        static_type = context.user_data.get('static_type', '')
        payment_amount = get_proxy_price(proxy_type, country, state, static_type, context.user_data.get("res4_duration_type", ""))
        
        # التحقق من أن الرسالة تحتوي على صورة فقط أولاً
        if not update.message.photo:
            # رفض أي نوع آخر غير الصورة
            await update.message.reply_text(
                "❌ يُسمح بإرسال الصور فقط كإثبات للدفع!\n\n📸 يرجى إرسال صورة واضحة لإثبات الدفع\n\n⏳ البوت ينتظر صورة إثبات الدفع أو يمكنك الإلغاء",
                parse_mode='HTML'
            )
            return PAYMENT_PROOF  # البقاء في نفس الحالة

        # معالجة إثبات الدفع (صورة فقط)
        file_id = update.message.photo[-1].file_id
        payment_proof = f"photo:{file_id}"
        
        print(f"📸 تم استلام إثبات دفع (صورة) للطلب: {order_id}")
        
        # إنشاء الطلب في قاعدة البيانات فقط بعد التحقق من الصورة
        print(f"📝 إنشاء طلب جديد: {order_id}")
        db.create_order(order_id, user_id, proxy_type, country, state, payment_method, payment_amount, context.user_data.get("quantity", "5"))
        
        # حفظ نوع البروكسي المفصل للطلب
        if static_type:
            try:
                db.execute_query("UPDATE orders SET static_type = ? WHERE id = ?", (static_type, order_id))
                print(f"💾 تم حفظ نوع البروكسي المفصل: {static_type}")
            except Exception as e:
                print(f"خطأ في حفظ نوع البروكسي: {e}")
        
        # إرسال نسخة للمستخدم
        await update.message.reply_photo(
            photo=file_id,
            caption=f"📸 إثبات دفع للطلب بمعرف: <code>{order_id}</code>\n\n✅ تم حفظ إثبات الدفع بنجاح",
            parse_mode='HTML'
        )
        
        # حفظ إثبات الدفع في قاعدة البيانات
        if payment_proof:
            db.update_order_payment_proof(order_id, payment_proof)
            print(f"💾 تم حفظ إثبات الدفع في قاعدة البيانات للطلب: {order_id}")
        
        # إرسال نسخة من الطلب للمستخدم
        try:
            await send_order_copy_to_user(update, context, order_id)
            print(f"📋 تم إرسال نسخة الطلب للمستخدم: {order_id}")
        except Exception as e:
            print(f"⚠️ خطأ في إرسال نسخة الطلب للمستخدم {order_id}: {e}")
        
        # إرسال إشعار للأدمن مع زر المعالجة
        try:
            print(f"🔔 محاولة إرسال إشعار للأدمن للطلب: {order_id}")
            print(f"   نوع إثبات الدفع: {'صورة' if payment_proof and payment_proof.startswith('photo:') else 'نص' if payment_proof and payment_proof.startswith('text:') else 'غير معروف'}")
            await send_admin_notification(context, order_id, payment_proof)
            print(f"✅ تم إرسال إشعار الأدمن بنجاح للطلب: {order_id}")
        except Exception as e:
            print(f"❌ خطأ في إرسال إشعار الأدمن للطلب {order_id}: {e}")
            # محاولة تسجيل الخطأ
            try:
                db.log_action(user_id, "admin_notification_failed", f"Order: {order_id}, Error: {str(e)}")
            except:
                pass
        
        # إرسال رسالة تأكيد للمستخدم
        try:
            await update.message.reply_text(MESSAGES[language]['order_received'], parse_mode='HTML')
            print(f"✅ تم إرسال رسالة التأكيد للمستخدم للطلب: {order_id}")
        except Exception as e:
            print(f"⚠️ خطأ في إرسال رسالة التأكيد للطلب {order_id}: {e}")
        
        # تسجيل العملية
        try:
            db.log_action(user_id, "payment_proof_submitted", order_id)
            print(f"📊 تم تسجيل العملية في قاعدة البيانات للطلب: {order_id}")
        except Exception as e:
            print(f"⚠️ خطأ في تسجيل العملية للطلب {order_id}: {e}")
        
        # تنظيف البيانات المؤقتة وإنهاء المحادثة مع الحفاظ على حالة الأدمن
        clean_user_data_preserve_admin(context)
        print(f"🧹 تم تنظيف البيانات المؤقتة وإنهاء معالجة الطلب: {order_id}")
        
        return ConversationHandler.END
        
    except Exception as e:
        print(f"❌ خطأ عام في معالجة إثبات الدفع للمستخدم {user_id}: {e}")
        try:
            await update.message.reply_text(
                "❌ حدث خطأ أثناء معالجة إثبات الدفع. يرجى المحاولة مرة أخرى أو التواصل مع الدعم.",
                parse_mode='HTML'
            )
        except:
            pass
        
        # تنظيف البيانات في حالة الخطأ مع الحفاظ على حالة الأدمن
        clean_user_data_preserve_admin(context)
        return ConversationHandler.END

async def send_withdrawal_notification(context: ContextTypes.DEFAULT_TYPE, withdrawal_id: str, user: tuple) -> None:
    """إرسال إشعار طلب سحب للأدمن"""
    message = f"""💸 طلب سحب رصيد جديد

👤 الاسم: {user[2]} {user[3]}
📱 اسم المستخدم: @{user[1] or 'غير محدد'}
🆔 معرف المستخدم: <code>{user[0]}</code>

━━━━━━━━━━━━━━━
💰 المبلغ المطلوب: <code>{user[5]:.2f}$</code>
📊 نوع الطلب: سحب رصيد الإحالات

━━━━━━━━━━━━━━━
🔗 معرف الطلب: <code>{withdrawal_id}</code>
📅 تاريخ الطلب: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

    # زر معالجة طلب السحب
    keyboard = [[InlineKeyboardButton("💸 معالجة طلب السحب", callback_data=f"process_{withdrawal_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if ADMIN_CHAT_ID:
        try:
            await context.bot.send_message(
                ADMIN_CHAT_ID, 
                message, 
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        except Exception as e:
            print(f"خطأ في إرسال إشعار طلب السحب: {e}")
    
    # حفظ الإشعار في قاعدة البيانات
    db.log_action(user[0], "withdrawal_notification", f"New withdrawal: {withdrawal_id}")

async def check_and_add_referral_bonus(context: ContextTypes.DEFAULT_TYPE, user_id: int, order_id: str) -> None:
    """التحقق من إضافة رصيد الإحالة عند كل عملية شراء ناجحة للمُحال"""
    try:
        # التحقق من وجود إحالة لهذا المستخدم
        referral_query = "SELECT referrer_id FROM referrals WHERE referred_id = ?"
        referral_result = db.execute_query(referral_query, (user_id,))
        
        if referral_result:
            referrer_id = referral_result[0][0]
            
            # الحصول على مبلغ الطلب
            order_query = "SELECT payment_amount FROM orders WHERE id = ?"
            order_result = db.execute_query(order_query, (order_id,))
            payment_amount = order_result[0][0] if order_result and order_result[0][0] else 0.0
            
            # حساب قيمة الإحالة بناءً على نسبة مئوية من قيمة الطلب
            referral_bonus = get_referral_amount(payment_amount)
            db.execute_query(
                "UPDATE users SET referral_balance = referral_balance + ? WHERE user_id = ?",
                (referral_bonus, referrer_id)
            )
            
            # الحصول على بيانات المحيل والمُحال
            referrer = db.get_user(referrer_id)
            referred_user = db.get_user(user_id)
            
            if referrer and referred_user and ADMIN_CHAT_ID:
                # إشعار الأدمن بإضافة رصيد الإحالة
                admin_message = f"""💰 تم إضافة رصيد إحالة!

🎉 <b>عملية شراء ناجحة من المُحال</b>

👤 <b>المُحال:</b>
📝 الاسم: {referred_user[2]} {referred_user[3] or ''}
📱 اسم المستخدم: @{referred_user[1] or 'غير محدد'}
🆔 المعرف: <code>{user_id}</code>

━━━━━━━━━━━━━━━
👥 <b>المحيل:</b>
📝 الاسم: {referrer[2]} {referrer[3] or ''}
📱 اسم المستخدم: @{referrer[1] or 'غير محدد'}
🆔 المعرف: <code>{referrer_id}</code>

━━━━━━━━━━━━━━━
💵 <b>تم إضافة <code>{referral_bonus}$</code> لرصيد المحيل</b>
🔗 معرف الطلب: <code>{order_id}</code>
📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

                try:
                    await context.bot.send_message(
                        ADMIN_CHAT_ID,
                        admin_message,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    print(f"خطأ في إرسال إشعار رصيد الإحالة للأدمن: {e}")
            
            # إشعار المحيل بإضافة الرصيد
            try:
                referrer_language = get_user_language(referrer_id)
                if referrer_language == 'ar':
                    referrer_message = f"""🎉 تهانينا! تم إضافة رصيد الإحالة!

💰 تم إضافة <code>{referral_bonus}$</code> إلى رصيدك
🛍️ السبب: عملية شراء ناجحة للعضو المُحال

💵 يمكنك سحب رصيدك عند وصوله إلى <code>1.0$</code>"""
                else:
                    referrer_message = f"""🎉 Congratulations! Referral bonus added!

💰 <code>{referral_bonus}$</code> added to your balance
🛍️ Reason: Successful purchase by referred member

💵 You can withdraw when balance reaches <code>1.0$</code>"""
                
                await context.bot.send_message(
                    referrer_id,
                    referrer_message,
                    parse_mode='HTML'
                )
            except Exception as e:
                print(f"خطأ في إرسال إشعار رصيد الإحالة للمحيل: {e}")
            
            # تسجيل العملية
            db.log_action(referrer_id, "referral_bonus_added", f"Bonus: {referral_bonus}$ for order: {order_id}")
                
    except Exception as e:
        print(f"خطأ في معالجة رصيد الإحالة: {e}")

async def broadcast_referral_update(context: ContextTypes.DEFAULT_TYPE, new_percentage: float) -> None:
    """إرسال إشعار جماعي للمستخدمين بتحديث نسبة الإحالة المئوية"""
    try:
        # الحصول على جميع المستخدمين من قاعدة البيانات
        all_users_query = "SELECT user_id, language FROM users"
        users = db.execute_query(all_users_query)
        
        sent_count = 0
        failed_count = 0
        
        for user in users:
            user_id, language = user
            language = language or 'ar'  # افتراضي للعربية
            
            try:
                # تحديد الرسالة حسب اللغة
                if language == 'ar':
                    message = f"""📢 إشعار هام - تحديث نسبة الإحالة

💰 تم تحديث نسبة الإحالة إلى: {new_percentage}%

🎉 شارك رابط الإحالة الخاص بك واحصل على {new_percentage}% من كل عملية شراء!

👥 يمكنك مراجعة رصيدك من قسم "إحالاتي"

━━━━━━━━━━━━━━━
🔗 رابط الإحالة الخاص بك:
<code>https://t.me/{(await context.bot.get_me()).username}?start={user_id}</code>"""
                else:
                    message = f"""📢 Important Notice - Referral Percentage Update

💰 Referral percentage updated to: {new_percentage}%

🎉 Share your referral link and earn {new_percentage}% from every purchase!

👥 You can check your balance in "My Referrals" section

━━━━━━━━━━━━━━━
🔗 Your referral link:
<code>https://t.me/{(await context.bot.get_me()).username}?start={user_id}</code>"""
                
                await context.bot.send_message(
                    user_id,
                    message,
                    parse_mode='HTML'
                )
                sent_count += 1
                
                # توقف قصير لتجنب حدود التيليجرام
                await asyncio.sleep(0.05)  # 50ms delay
                
            except Exception as e:
                failed_count += 1
                print(f"فشل إرسال إشعار تحديث الإحالة للمستخدم {user_id}: {e}")
        
        # إرسال تقرير للأدمن
        if ADMIN_CHAT_ID:
            admin_report = f"""📊 تقرير إشعار تحديث الإحالة

✅ تم الإرسال بنجاح: {sent_count} مستخدم
❌ فشل الإرسال: {failed_count} مستخدم
💰 النسبة الجديدة: {new_percentage}%
📅 وقت التحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
            
            try:
                await context.bot.send_message(
                    ADMIN_CHAT_ID,
                    admin_report,
                    parse_mode='HTML'
                )
            except Exception as e:
                print(f"فشل إرسال تقرير الإشعار للأدمن: {e}")
        
        # تسجيل العملية في قاعدة البيانات
        db.log_action(ADMIN_CHAT_ID, "referral_update_broadcast", f"Percentage: {new_percentage}%, Sent: {sent_count}, Failed: {failed_count}")
        
    except Exception as e:
        print(f"خطأ في إرسال إشعار تحديث الإحالة: {e}")

async def broadcast_price_update(context: ContextTypes.DEFAULT_TYPE, price_type: str, prices: dict) -> None:
    """إرسال إشعار تحديث الأسعار - معطل"""
    logger.info(f"إشعار تحديث الأسعار معطل: {price_type}")
    return
    
async def broadcast_price_update_OLD(context: ContextTypes.DEFAULT_TYPE, price_type: str, prices: dict) -> None:
    """إرسال إشعار جماعي للمستخدمين بتحديث الأسعار - معطل حسب طلب الإدارة"""
    # تم تعطيل إرسال إشعارات تغيير الأسعار حسب طلب الإدارة
    logger.info(f"تم تجاهل إرسال إشعار تغيير الأسعار - النوع: {price_type}")
    return
    
    try:
        # الحصول على جميع المستخدمين من قاعدة البيانات
        all_users_query = "SELECT user_id, language FROM users"
        users = db.execute_query(all_users_query)
        
        sent_count = 0
        failed_count = 0
        
        for user in users:
            user_id, language = user
            language = language or 'ar'  # افتراضي للعربية
            
            try:
                # تحديد الرسالة حسب اللغة ونوع السعر
                if price_type == "static":
                    if language == 'ar':
                        prices_text = f"""
- Static ISP Risk0: <code>{prices.get('ISP', '3')}$</code>
- Static Residential Crocker: <code>{prices.get('Crocker', '4')}$</code>
- Static Residential: <code>{prices.get('ATT', '6')}$</code>"""
                        message = f"""📢 إشعار هام - تحديث أسعار البروكسي الستاتيك

💰 تم تحديث أسعار البروكسي الستاتيك:{prices_text}

🔄 الأسعار الجديدة سارية المفعول من الآن

🛒 يمكنك طلب بروكسي ستاتيك بالأسعار الجديدة"""
                    else:
                        prices_text = f"""
- Static ISP Risk0: <code>{prices.get('ISP', '3')}$</code>
- Static Residential Crocker: <code>{prices.get('Crocker', '4')}$</code>
- Static Residential: <code>{prices.get('ATT', '6')}$</code>"""
                        message = f"""📢 Important Notice - Static Proxy Prices Update

💰 Static proxy prices have been updated:{prices_text}

🔄 New prices are effective immediately

🛒 You can order static proxy with new prices"""
                        
                elif price_type == "static_individual":
                    type_name = prices.get('type_name', 'Static')
                    price_value = ""
                    for key, value in prices.items():
                        if key != 'type_name':
                            price_value = value
                            break
                    
                    if language == 'ar':
                        message = f"""📢 إشعار هام - تحديث سعر البروكسي الستاتيك

💰 تم تحديث سعر {type_name}: <code>{price_value}$</code>

🔄 السعر الجديد ساري المفعول من الآن

🛒 يمكنك طلب بروكسي ستاتيك بالسعر الجديد"""
                    else:
                        message = f"""📢 Important Notice - Static Proxy Price Update

💰 {type_name} price has been updated: <code>{price_value}$</code>

🔄 New price is effective immediately

🛒 You can order static proxy with new price"""
                
                elif price_type == "socks":
                    if language == 'ar':
                        prices_text = f"""
- باكج 5 بروكسيات يومية: <code>{prices.get('5proxy', '0.4')}$</code>
- باكج 10 بروكسيات يومية: <code>{prices.get('10proxy', '0.7')}$</code>"""
                        message = f"""📢 إشعار هام - تحديث أسعار بروكسي السوكس

💰 تم تحديث أسعار بروكسي السوكس:{prices_text}

🔄 الأسعار الجديدة سارية المفعول من الآن

🛒 يمكنك طلب بروكسي سوكس بالأسعار الجديدة"""
                    else:
                        prices_text = f"""
- 5 Daily Proxies Package: <code>{prices.get('5proxy', '0.4')}$</code>
- 10 Daily Proxies Package: <code>{prices.get('10proxy', '0.7')}$</code>"""
                        message = f"""📢 Important Notice - Socks Proxy Prices Update

💰 Socks proxy prices have been updated:{prices_text}

🔄 New prices are effective immediately

🛒 You can order socks proxy with new prices"""
                
                elif price_type == "socks_individual":
                    type_name = prices.get('type_name', 'Socks')
                    price_value = ""
                    for key, value in prices.items():
                        if key != 'type_name':
                            price_value = value
                            break
                    
                    if language == 'ar':
                        message = f"""📢 إشعار هام - تحديث سعر بروكسي السوكس

💰 تم تحديث سعر {type_name}: <code>{price_value}$</code>

🔄 السعر الجديد ساري المفعول من الآن

🛒 يمكنك طلب بروكسي سوكس بالسعر الجديد"""
                    else:
                        message = f"""📢 Important Notice - Socks Proxy Price Update

💰 {type_name} price has been updated: <code>{price_value}$</code>

🔄 New price is effective immediately

🛒 You can order socks proxy with new price"""
                
                await context.bot.send_message(
                    user_id,
                    message,
                    parse_mode='HTML'
                )
                sent_count += 1
                
                # توقف قصير لتجنب حدود التيليجرام
                await asyncio.sleep(0.05)  # 50ms delay
                
            except Exception as e:
                failed_count += 1
                print(f"فشل إرسال إشعار تحديث الأسعار للمستخدم {user_id}: {e}")
        
        # إرسال تقرير للأدمن
        if ADMIN_CHAT_ID:
            admin_report = f"""📊 تقرير إشعار تحديث الأسعار

📦 نوع الأسعار: {price_type}
✅ تم الإرسال بنجاح: {sent_count} مستخدم
❌ فشل الإرسال: {failed_count} مستخدم
📅 وقت التحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
            
            try:
                await context.bot.send_message(
                    ADMIN_CHAT_ID,
                    admin_report,
                    parse_mode='HTML'
                )
            except Exception as e:
                print(f"فشل إرسال تقرير الإشعار للأدمن: {e}")
        
        # تسجيل العملية في قاعدة البيانات
        db.log_action(ADMIN_CHAT_ID, f"{price_type}_price_update_broadcast", f"Sent: {sent_count}, Failed: {failed_count}")
        
    except Exception as e:
        print(f"خطأ في إرسال إشعار تحديث الأسعار: {e}")

async def send_referral_notification(context: ContextTypes.DEFAULT_TYPE, referrer_id: int, new_user) -> None:
    """إرسال إشعار للأدمن بانضمام عضو جديد عبر الإحالة"""
    # الحصول على بيانات المحيل
    referrer = db.get_user(referrer_id)
    
    if referrer:
        message = f"""👥 عضو جديد عبر الإحالة

🆕 العضو الجديد:
👤 الاسم: {new_user.first_name} {new_user.last_name or ''}
📱 اسم المستخدم: @{new_user.username or 'غير محدد'}
🆔 معرف المستخدم: <code>{new_user.id}</code>

━━━━━━━━━━━━━━━
👥 تم إحالته بواسطة:
👤 الاسم: {referrer[2]} {referrer[3]}
📱 اسم المستخدم: @{referrer[1] or 'غير محدد'}
🆔 معرف المحيل: <code>{referrer[0]}</code>

━━━━━━━━━━━━━━━
💰 سيتم إضافة {get_referral_percentage()}% من قيمة كل عملية شراء لرصيد المحيل
📅 تاريخ الانضمام: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        if ADMIN_CHAT_ID:
            try:
                await context.bot.send_message(
                    ADMIN_CHAT_ID, 
                    message,
                    parse_mode='HTML'
                )
            except Exception as e:
                print(f"خطأ في إرسال إشعار الإحالة: {e}")
        
        # حفظ الإشعار في قاعدة البيانات
        db.log_action(new_user.id, "referral_notification", f"Referred by: {referrer_id}")

async def send_order_copy_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str) -> None:
    """إرسال نسخة من الطلب للمستخدم"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    # الحصول على تفاصيل الطلب
    query = """
        SELECT o.*, u.first_name, u.last_name, u.username 
        FROM orders o 
        JOIN users u ON o.user_id = u.user_id 
        WHERE o.id = ?
    """
    result = db.execute_query(query, (order_id,))
    
    if result:
        order = result[0]
        
        # تحديد طريقة الدفع باللغة المناسبة
        payment_methods = {
            'ar': {
                'shamcash': 'شام كاش',
                'syriatel': 'سيرياتيل كاش', 
                'coinex': 'Coinex',
                'binance': 'Binance',
                'payeer': 'Payeer',
                'bep20': 'BEP20',
                'litecoin': 'Litecoin'
            },
            'en': {
                'shamcash': 'Sham Cash',
                'syriatel': 'Syriatel Cash',
                'coinex': 'Coinex', 
                'binance': 'Binance',
                'payeer': 'Payeer',
                'bep20': 'BEP20',
                'litecoin': 'Litecoin'
            }
        }
        
        payment_method = payment_methods[language].get(order[5], order[5])
        
        if language == 'ar':
            message = f"""📋 نسخة من طلبك
            
👤 الاسم: <code>{order[15]} {order[16] or ''}</code>
🆔 معرف المستخدم: <code>{order[1]}</code>

━━━━━━━━━━━━━━━
📦 تفاصيل الطلب:
📊 الكمية: {order[8]}
🔧 نوع البروكسي: {get_detailed_proxy_type(order[2], order[14] if len(order) > 14 else '', order[3] if len(order) > 3 else '')}
🌍 الدولة: {order[3]}
🏠 الولاية: {order[4]}
⏰ المدة: {order[14] if len(order) > 14 and order[14] else "غير محدد"}

━━━━━━━━━━━━━━━
💳 تفاصيل الدفع:
💰 طريقة الدفع: {payment_method}
💵 قيمة الطلب: <code>{order[6]}$</code>

━━━━━━━━━━━━━━━
🔗 معرف الطلب: <code>{order[0]}</code>
📅 تاريخ الطلب: {order[9]}
📊 الحالة: ⏳ تحت المراجعة

يرجى الاحتفاظ بمعرف الطلب للمراجعة المستقبلية."""
        else:
            message = f"""📋 Copy of Your Order
            
👤 Name: <code>{order[15]} {order[16] or ''}</code>
🆔 User ID: <code>{order[1]}</code>

━━━━━━━━━━━━━━━
📦 Order Details:
📊 Quantity: {order[8]}
🔧 Proxy Type: {order[2]}
🌍 Country: {order[3]}
🏠 State: {order[4]}

━━━━━━━━━━━━━━━
💳 Payment Details:
💰 Payment Method: {payment_method}
💵 Order Value: <code>{order[6]}$</code>

━━━━━━━━━━━━━━━
🔗 Order ID: <code>{order[0]}</code>
📅 Order Date: {order[9]}
📊 Status: ⏳ Under Review

Please keep the order ID for future reference."""
        
        await context.bot.send_message(user_id, message, parse_mode='HTML')

def create_admin_notification_message(order_id: str, user_id: int, proxy_type: str, country: str, state: str, payment_amount: float, language: str, quantity: int = 1, static_type: str = "", duration: str = "") -> str:
    """إنشاء رسالة إشعار للأدمن عن طلب جديد"""
    try:
        # الحصول على بيانات المستخدم
        user = db.get_user(user_id)
        if not user:
            escaped_user_id = escape_markdown_v2(str(user_id))
            return f"❌ خطأ: لم يتم العثور على بيانات المستخدم <code>{escaped_user_id}</code>"
        
        # تنسيق نوع البروكسي للعرض
        proxy_display = {
            'static': 'بروكسي ستاتيك 🌐',
            'socks': 'بروكسي سوكس'
        }.get(proxy_type, proxy_type)
        
        # تهريب البيانات لـ MarkdownV2
        escaped_proxy_display = escape_markdown_v2(str(proxy_display))
        escaped_first_name = escape_markdown_v2(str(user[2]) if user[2] else '')
        escaped_last_name = escape_markdown_v2(str(user[3]) if user[3] else '')
        escaped_username = escape_markdown_v2(str(user[1]) if user[1] else 'غير محدد')
        escaped_user_id = escape_markdown_v2(str(user_id))
        escaped_country = escape_markdown_v2(str(country))
        escaped_state = escape_markdown_v2(str(state))
        escaped_quantity = escape_markdown_v2(str(quantity))
        escaped_order_id = escape_markdown_v2(str(order_id))
        
        # تنسيق نوع الستاتيك إذا كان موجوداً
        static_display = ""
        if static_type:
            escaped_static_type = escape_markdown_v2(str(static_type))
            static_display = f"\n🔧 النوع: {escaped_static_type}"
        
        # تنسيق التاريخ والوقت
        date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        escaped_date = escape_markdown_v2(str(date_str))
        
        message = f"""🔔 طلب {proxy_display} جديد!

👤 الاسم: {user[2] or ''} {user[3] or ''}
📱 اسم المستخدم: @{user[1] or 'غير محدد'}
🆔 معرف المستخدم: <code>{user_id}</code>

━━━━━━━━━━━━━━━
📦 تفاصيل الطلب:
🌍 الدولة: {country}
🏛️ الولاية: {state}
📊 الكمية: {quantity}{' - النوع: ' + static_type if static_type else ''}
💰 السعر: {payment_amount:.2f}$
⏰ المدة: {duration or "غير محدد"}

━━━━━━━━━━━━━━━
🔗 معرف الطلب: <code>{order_id}</code>
📅 التاريخ: {date_str}

⚡ انقر على الزر أدناه لمعالجة الطلب"""
        
        return message
        
    except Exception as e:
        logger.error(f"Error creating admin notification message: {e}")
        escaped_order_id = escape_markdown_v2(str(order_id))
        return f"❌ خطأ في إنشاء رسالة الإشعار للطلب: <code>{escaped_order_id}</code>"

async def send_admin_notification(context: ContextTypes.DEFAULT_TYPE, order_id: str, payment_proof: str = None) -> None:
    """إرسال إشعار للآدمن بطلب جديد (يستخدم ACTIVE_ADMINS و ADMIN_CHAT_ID)"""
    global ACTIVE_ADMINS, ADMIN_CHAT_ID
    
    # جمع معرفات الآدمن من كلا المصدرين
    admin_ids = set()
    
    if ACTIVE_ADMINS:
        admin_ids.update(ACTIVE_ADMINS)
    
    if ADMIN_CHAT_ID:
        admin_ids.add(ADMIN_CHAT_ID)
    
    # إذا لم يكن هناك آدمن نشطين، جرب الحصول عليهم من قاعدة البيانات
    if not admin_ids:
        try:
            admin_query = "SELECT value FROM settings WHERE key = 'admin_chat_id'"
            admin_result = db.execute_query(admin_query)
            if admin_result and admin_result[0][0]:
                admin_ids.add(int(admin_result[0][0]))
                print(f"✅ تم الحصول على آدمن من قاعدة البيانات: {admin_result[0][0]}")
        except Exception as e:
            print(f"⚠️ خطأ في الحصول على آدمن من قاعدة البيانات: {e}")
    
    if not admin_ids:
        print(f"⚠️ لا يوجد آدمن متاح - لا يمكن إرسال إشعار للطلب: {order_id}")
        return
    
    # جلب تفاصيل الطلب لإضافتها للإشعار
    order_query = "SELECT quantity, proxy_type, country FROM orders WHERE id = ?"
    order_result = db.execute_query(order_query, (order_id,))
    
    if order_result:
        quantity, proxy_type, country = order_result[0]
        message = f"🔔 لديك طلب جديد\n\n🆔 معرف الطلب: <code>{order_id}</code>\n📊 الكمية: {quantity}\n🔧 النوع: {proxy_type}\n🌍 الدولة: {country}"
    else:
        message = f"🔔 لديك طلب جديد\n\n🆔 معرف الطلب: <code>{order_id}</code>"
    
    keyboard = [[InlineKeyboardButton("📋 عرض الطلب", callback_data=f"view_order_{order_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # إرسال الإشعار لجميع الآدمن المتاحين
    sent_count = 0
    for admin_id in admin_ids:
        try:
            await context.bot.send_message(
                admin_id, 
                message, 
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            sent_count += 1
            print(f"✅ تم إرسال إشعار للأدمن {admin_id} للطلب: {order_id}")
        except Exception as e:
            logger.error(f"Error sending admin notification to admin {admin_id}: {e}")
            print(f"❌ فشل إرسال إشعار للأدمن {admin_id}: {e}")
    
    if sent_count > 0:
        print(f"✅ تم إرسال إشعار ل {sent_count} آدمن للطلب: {order_id}")
    else:
        print(f"⚠️ فشل إرسال الإشعار لجميع الآدمن للطلب: {order_id}")

async def send_admin_notification_with_details(context: ContextTypes.DEFAULT_TYPE, order_id: str, user_id: int, proxy_type: str, country: str, state: str, payment_amount: float, language: str, quantity: int, static_type: str = "", duration: str = "") -> None:
    """إرسال إشعار للآدمن النشطين عن طلب بروكسي جديد مع جميع التفاصيل"""
    try:
        global ACTIVE_ADMINS, ADMIN_CHAT_ID
        
        # جمع معرفات الآدمن من كلا المصدرين
        admin_ids = set()
        
        if ACTIVE_ADMINS:
            admin_ids.update(ACTIVE_ADMINS)
        
        if ADMIN_CHAT_ID:
            admin_ids.add(ADMIN_CHAT_ID)
        
        # إذا لم يكن هناك آدمن نشطين، جرب الحصول عليهم من قاعدة البيانات
        if not admin_ids:
            try:
                admin_query = "SELECT value FROM settings WHERE key = 'admin_chat_id'"
                admin_result = db.execute_query(admin_query)
                if admin_result and admin_result[0][0]:
                    admin_ids.add(int(admin_result[0][0]))
                    print(f"✅ تم الحصول على آدمن من قاعدة البيانات: {admin_result[0][0]}")
            except Exception as e:
                print(f"⚠️ خطأ في الحصول على آدمن من قاعدة البيانات: {e}")
        
        if not admin_ids:
            print(f"⚠️ لا يوجد آدمن متاح - لا يمكن إرسال إشعار للطلب: {order_id}")
            return
        
        # إنشاء رسالة الإشعار باستخدام create_admin_notification_message
        admin_message = create_admin_notification_message(
            order_id, user_id, proxy_type, country, 
            state, payment_amount, language, quantity, static_type
        )
        
        keyboard = [[InlineKeyboardButton("⚡ معالجة الطلب", callback_data=f"process_{order_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # إرسال الإشعار لجميع الآدمن المتاحين
        sent_count = 0
        for admin_id in admin_ids:
            try:
                await context.bot.send_message(
                    admin_id,
                    admin_message,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
                sent_count += 1
                print(f"✅ تم إرسال إشعار للأدمن {admin_id} للطلب: {order_id}")
            except Exception as e:
                logger.error(f"Error sending notification to admin {admin_id}: {e}")
                print(f"❌ فشل إرسال إشعار للأدمن {admin_id}: {e}")
        
        if sent_count > 0:
            print(f"✅ تم إرسال إشعار ل {sent_count} آدمن للطلب: {order_id}")
        else:
            print(f"⚠️ فشل إرسال الإشعار لجميع الآدمن للطلب: {order_id}")
            
    except Exception as e:
        logger.error(f"Error sending admin notification with details for order {order_id}: {e}")
        print(f"❌ خطأ في إرسال إشعار مفصل للأدمن: {e}")

async def handle_view_order_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض تفاصيل الطلب مع التوثيق عند الضغط على زر عرض الطلب"""
    query = update.callback_query
    await query.answer()
    
    order_id = query.data.replace("view_order_", "")
    
    # الحصول على تفاصيل الطلب
    order_query = """
        SELECT o.*, u.first_name, u.last_name, u.username 
        FROM orders o 
        JOIN users u ON o.user_id = u.user_id 
        WHERE o.id = ?
    """
    result = db.execute_query(order_query, (order_id,))
    
    if not result:
        await query.edit_message_text("❌ لم يتم العثور على الطلب")
        return
    
    order = result[0]
    
    # التحقق من طول البيانات
    # جدول orders يحتوي على 16 حقل + 3 حقول من users = 19 حقل إجمالي
    # الأعمدة: id(0), user_id(1), proxy_type(2), country(3), state(4), payment_method(5), 
    # payment_amount(6), payment_proof(7), quantity(8), status(9), created_at(10), 
    # processed_at(11), proxy_details(12), truly_processed(13), duration(14), static_type(15)
    # ثم من جدول users: first_name(16), last_name(17), username(18)
    
    # تحديد طريقة الدفع باللغة العربية
    payment_methods_ar = {
        'shamcash': 'شام كاش',
        'syriatel': 'سيرياتيل كاش',
        'coinex': 'Coinex',
        'binance': 'Binance',
        'payeer': 'Payeer',
        'bep20': 'BEP20',
        'litecoin': 'Litecoin'
    }
    
    payment_method_ar = payment_methods_ar.get(order[5], order[5])
    
    # استخراج البيانات بطريقة آمنة
    # أعمدة المستخدم تبدأ من index 16 بعد 16 عمود من جدول orders
    user_first_name = order[16] if len(order) > 16 else 'غير محدد'
    user_last_name = order[17] if len(order) > 17 and order[17] else ''
    username = order[18] if len(order) > 18 and order[18] else 'غير محدد'
    static_type = order[15] if len(order) > 15 else ''
    
    # تهريب البيانات لـ MarkdownV2
    escaped_first_name = escape_markdown_v2(str(user_first_name))
    escaped_last_name = escape_markdown_v2(str(user_last_name))
    escaped_username = escape_markdown_v2(str(username))
    escaped_user_id = escape_markdown_v2(str(order[1]))
    escaped_quantity = escape_markdown_v2(str(order[8]))
    escaped_proxy_type = escape_markdown_v2(str(get_detailed_proxy_type(order[2], static_type, order[3] if len(order) > 3 else '')))
    escaped_country = escape_markdown_v2(str(order[3]))
    escaped_state = escape_markdown_v2(str(order[4]))
    escaped_payment_method = escape_markdown_v2(str(payment_method_ar))
    escaped_amount = escape_markdown_v2(str(order[6]))
    escaped_order_id = escape_markdown_v2(str(order_id))
    escaped_date = escape_markdown_v2(str(order[9]))
    
    message = f"""📋 تفاصيل الطلب مع التوثيق

👤 الاسم: {escaped_first_name} {escaped_last_name}
📱 اسم المستخدم: @{escaped_username}
🆔 معرف المستخدم: <code>{escaped_user_id}</code>

━━━━━━━━━━━━━━━
📦 تفاصيل الطلب:
📊 الكمية: {escaped_quantity}
🔧 نوع البروكسي: {escaped_proxy_type}
🌍 الدولة: {escaped_country}
🏠 الولاية: {escaped_state}
⏰ المدة: {escape_markdown_v2(str(order[14]) if len(order) > 14 and order[14] else "غير محدد")}

━━━━━━━━━━━━━━━
💳 تفاصيل الدفع:
💰 طريقة الدفع: {escaped_payment_method}
💵 قيمة الطلب: <code>{escaped_amount}$</code>
📄 إثبات الدفع: {"✅ مرفق" if order[7] else "❌ غير مرفق"}

━━━━━━━━━━━━━━━
🔗 معرف الطلب: <code>{escaped_order_id}</code>
📅 تاريخ الطلب: {escaped_date}
📊 الحالة: ⏳ معلق"""

    # إنشاء أزرار الإجراءات
    keyboard = [
        [InlineKeyboardButton("🔧 معالجة الطلب", callback_data=f"process_{order_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
    
    # إرسال إثبات الدفع كرد على رسالة الطلب إذا كان موجوداً
    if order[7]:  # payment_proof
        try:
            if order[7].startswith("photo:"):
                file_id = order[7].replace("photo:", "")
                await context.bot.send_photo(
                    update.effective_chat.id,
                    photo=file_id,
                    caption=f"📸 إثبات دفع للطلب بمعرف: <code>{escaped_order_id}</code>",
                    parse_mode='HTML',
                    reply_to_message_id=query.message.message_id
                )
            elif order[7].startswith("text:"):
                text_proof = order[7].replace("text:", "")
                escaped_text_proof = escape_markdown_v2(str(text_proof))
                await context.bot.send_message(
                    update.effective_chat.id,
                    f"📝 إثبات دفع للطلب بمعرف: <code>{escaped_order_id}</code>\n\nالنص:\n{escaped_text_proof}",
                    parse_mode='HTML',
                    reply_to_message_id=query.message.message_id
                )
        except Exception as e:
            print(f"خطأ في إرسال إثبات الدفع: {e}")

async def handle_view_pending_order_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض تفاصيل الطلب المعلق مع التوثيق"""
    query = update.callback_query
    await query.answer()
    
    order_id = query.data.replace("view_pending_order_", "")
    
    # فحص نوع الطلب أولاً
    proxy_type_query = "SELECT proxy_type FROM orders WHERE id = ?"
    proxy_type_result = db.execute_query(proxy_type_query, (order_id,))
    
    if proxy_type_result and proxy_type_result[0][0] == 'balance_recharge':
        # إذا كان طلب شحن رصيد، وجه إلى الدالة المناسبة
        # إنشاء update جديد مع callback_data الصحيح للتوافق مع معالج شحن الرصيد
        # تطبيق callback_data جديد دون تعديل الأصلي
        recharge_callback_data = f"view_recharge_{order_id}"
        
        # استدعاء المعالج مباشرة مع إرسال order_id
        await handle_view_recharge_details_with_id(update, context, order_id, answered=True)
        return
    
    # الحصول على تفاصيل الطلب للطلبات العادية
    order_query = """
        SELECT o.*, u.first_name, u.last_name, u.username 
        FROM orders o 
        JOIN users u ON o.user_id = u.user_id 
        WHERE o.id = ?
    """
    result = db.execute_query(order_query, (order_id,))
    
    if not result:
        await query.edit_message_text("❌ لم يتم العثور على الطلب")
        return
    
    order = result[0]
    
    # التحقق من طول البيانات لتجنب خطأ tuple index out of range
    # جدول orders يحتوي على 16 حقل + 3 حقول من users = 19 حقل إجمالي
    # الأعمدة: id(0), user_id(1), proxy_type(2), country(3), state(4), payment_method(5), 
    # payment_amount(6), payment_proof(7), quantity(8), status(9), created_at(10), 
    # processed_at(11), proxy_details(12), truly_processed(13), duration(14), static_type(15)
    # ثم من جدول users: first_name(16), last_name(17), username(18)
    if len(order) < 19:
        await query.edit_message_text("❌ بيانات الطلب غير كاملة. يرجى المحاولة مرة أخرى.")
        return
    
    # تحديد طريقة الدفع باللغة العربية
    payment_methods_ar = {
        'shamcash': 'شام كاش',
        'syriatel': 'سيرياتيل كاش',
        'coinex': 'Coinex',
        'binance': 'Binance',
        'payeer': 'Payeer',
        'bep20': 'BEP20',
        'litecoin': 'Litecoin'
    }
    
    payment_method_ar = payment_methods_ar.get(order[5] if len(order) > 5 else '', 'غير محدد')
    
    # استخراج البيانات بطريقة آمنة
    # أعمدة المستخدم تبدأ من index 16 بعد 16 عمود من جدول orders
    user_first_name = order[16] if len(order) > 16 else 'غير محدد'
    user_last_name = order[17] if len(order) > 17 else ''
    username = order[18] if len(order) > 18 else 'غير محدد'
    quantity = order[8] if len(order) > 8 else 'غير محدد'
    static_type = order[15] if len(order) > 15 else ''
    
    # تهريب البيانات لـ MarkdownV2
    escaped_first_name = escape_markdown_v2(str(user_first_name))
    escaped_last_name = escape_markdown_v2(str(user_last_name))
    escaped_username = escape_markdown_v2(str(username))
    escaped_user_id = escape_markdown_v2(str(order[1]))
    escaped_quantity = escape_markdown_v2(str(quantity))
    escaped_proxy_type = escape_markdown_v2(str(get_detailed_proxy_type(order[2], static_type, order[3] if len(order) > 3 else '')))
    escaped_country = escape_markdown_v2(str(order[3]))
    escaped_state = escape_markdown_v2(str(order[4]))
    escaped_payment_method = escape_markdown_v2(str(payment_method_ar))
    escaped_amount = escape_markdown_v2(str(order[6]))
    escaped_order_id = escape_markdown_v2(str(order_id))
    escaped_date = escape_markdown_v2(str(order[9]))
    
    message = f"""📋 تفاصيل الطلب الكاملة مع التوثيق

👤 الاسم: {escaped_first_name} {escaped_last_name}
📱 اسم المستخدم: @{escaped_username}
🆔 معرف المستخدم: <code>{escaped_user_id}</code>

━━━━━━━━━━━━━━━
📦 تفاصيل الطلب:
📊 الكمية: {escaped_quantity}
🔧 نوع البروكسي: {escaped_proxy_type}
🌍 الدولة: {escaped_country}
⏰ المدة: {escape_markdown_v2(str(order[14]) if len(order) > 14 and order[14] else "غير محدد")}
🏠 الولاية: {escaped_state}

━━━━━━━━━━━━━━━
💳 تفاصيل الدفع:
💰 طريقة الدفع: {escaped_payment_method}
💵 قيمة الطلب: <code>{escaped_amount}$</code>
📄 إثبات الدفع: {"✅ مرفق" if order[7] else "❌ غير مرفق"}

━━━━━━━━━━━━━━━
🔗 معرف الطلب: <code>{escaped_order_id}</code>
📅 تاريخ الطلب: {escaped_date}
📊 الحالة: ⏳ معلق"""

    # إنشاء أزرار الإجراءات (معالجة مع سؤال التحقق من الدفع)
    keyboard = [
        [InlineKeyboardButton("✅ معالجة الطلب", callback_data=f"process_{order_id}")],
        [InlineKeyboardButton("🔙 العودة للطلبات المعلقة", callback_data="back_to_pending_orders")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
    
    # إرسال إثبات الدفع كرد على رسالة الطلب إذا كان موجوداً
    if order[7]:  # payment_proof
        try:
            if order[7].startswith("photo:"):
                file_id = order[7].replace("photo:", "")
                await context.bot.send_photo(
                    update.effective_chat.id,
                    photo=file_id,
                    caption=f"📸 إثبات دفع للطلب بمعرف: <code>{escaped_order_id}</code>",
                    parse_mode='HTML',
                    reply_to_message_id=query.message.message_id
                )
            elif order[7].startswith("text:"):
                text_proof = order[7].replace("text:", "")
                escaped_text_proof = escape_markdown_v2(str(text_proof))
                await context.bot.send_message(
                    update.effective_chat.id,
                    f"📝 إثبات دفع للطلب بمعرف: <code>{escaped_order_id}</code>\n\nالنص:\n{escaped_text_proof}",
                    parse_mode='HTML',
                    reply_to_message_id=query.message.message_id
                )
        except Exception as e:
            print(f"خطأ في إرسال إثبات الدفع: {e}")

async def handle_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة قسم الإحالات"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    # إنشاء رابط الإحالة
    try:
        bot_info = await context.bot.get_me()
        bot_username = bot_info.username
    except:
        bot_username = "your_bot"  # fallback if bot info fails
    
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    
    # الحصول على رصيد الإحالة
    user = db.get_user(user_id)
    referral_balance = user[5] if user else 0.0
    
    # عدد الإحالات
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

# دوال معالجة قائمة الرصيد الجديدة
async def handle_balance_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة قائمة الرصيد الرئيسية"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    # إرسال قائمة الرصيد
    balance_keyboard = create_balance_keyboard(language)
    await update.message.reply_text(
        MESSAGES[language]['balance_menu_title'],
        reply_markup=balance_keyboard
    )

async def handle_my_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة عرض الرصيد الحالي"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    # الحصول على الرصيد
    balance_data = db.get_user_balance(user_id)
    
    # عرض الرصيد المفصل
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
    
    # الحصول على سعر النقطة
    credit_price = db.get_credit_price()
    
    # عرض رسالة طلب شحن الرصيد
    message = MESSAGES[language]['recharge_request'].format(credit_price=credit_price)
    
    # إنشاء زر الرجوع
    if language == 'ar':
        keyboard = [[InlineKeyboardButton("↩️ رجوع للقائمة الرئيسية", callback_data="back_to_main_from_recharge")]]
    else:
        keyboard = [[InlineKeyboardButton("↩️ Back to Main Menu", callback_data="back_to_main_from_recharge")]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, parse_mode='HTML')
    await update.message.reply_text(MESSAGES[language]['enter_recharge_amount'], reply_markup=reply_markup)
    
    # تعيين حالة انتظار المبلغ
    context.user_data['waiting_for_recharge_amount'] = True

async def handle_balance_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الإحالات من داخل قائمة الرصيد"""
    await handle_referrals(update, context)

async def handle_back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """العودة للقائمة الرئيسية من قائمة الرصيد"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    # إرسال القائمة الرئيسية
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
        
        # حساب النقاط المتوقعة
        credit_price = db.get_credit_price()
        expected_credits = amount / credit_price
        
        # حفظ بيانات الطلب في الذاكرة فقط (بدون حفظ في قاعدة البيانات حتى الآن)
        order_id = generate_order_id()
        context.user_data['recharge_order_id'] = order_id
        context.user_data['recharge_amount'] = amount
        context.user_data['expected_credits'] = expected_credits
        context.user_data['waiting_for_recharge_amount'] = False
        context.user_data['waiting_for_recharge_payment_method'] = True
        
        # ملاحظة: لن يتم حفظ الطلب في قاعدة البيانات حتى يتم إرسال إثبات الدفع
        
        # عرض طرق الدفع
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

async def handle_recharge_payment_method_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة اختيار طريقة الدفع لشحن الرصيد"""
    try:
        query = update.callback_query
        user_id = update.effective_user.id
        language = get_user_language(user_id)
        
        await query.answer()
        
        payment_method = query.data.replace("recharge_payment_", "")
        context.user_data['recharge_payment_method'] = payment_method
        context.user_data['waiting_for_recharge_payment_method'] = False
        context.user_data['waiting_for_recharge_proof'] = True
        
        amount = context.user_data.get('recharge_amount', 0)
        expected_credits = context.user_data.get('expected_credits', 0)
        credit_price = db.get_credit_price()
        
        payment_details = {
            'shamcash': {
                'ar': '💳 شام كاش\n\nالحساب: cc849f22d5117db0b8fe5667e6d4b758',
                'en': '💳 Sham Cash\n\nAccount: cc849f22d5117db0b8fe5667e6d4b758'
            },
            'syriatel': {
                'ar': '💳 سيرياتيل كاش\n\nالحساب: 55973911\nأو: 14227865',
                'en': '💳 Syriatel Cash\n\nAccount: 55973911\nOr: 14227865'
            },
            'coinex': {
                'ar': '🪙 Coinex\n\nالبريد: sohilskaf123@gmail.com',
                'en': '🪙 Coinex\n\nEmail: sohilskaf123@gmail.com'
            },
            'binance': {
                'ar': '🪙 Binance\n\nالمعرف: 1160407924',
                'en': '🪙 Binance\n\nID: 1160407924'
            },
            'payeer': {
                'ar': '🪙 Payeer\n\nالحساب: P1114452356',
                'en': '🪙 Payeer\n\nAccount: P1114452356'
            },
            'bep20': {
                'ar': '🔗 BEP20 (BSC)\n\n<b>العنوان:</b>\n<pre>0xd0d85b3c9df21947087cbb1df5c8bf443d7d17e4</pre>',
                'en': '🔗 BEP20 (BSC)\n\n<b>Address:</b>\n<pre>0xd0d85b3c9df21947087cbb1df5c8bf443d7d17e4</pre>'
            },
            'litecoin': {
                'ar': '🔗 Litecoin (LTC)\n\n<b>العنوان:</b>\n<pre>ltc1q4z6ncnp4sj58e96f2xnlhvr7txh53r3drfvjta</pre>',
                'en': '🔗 Litecoin (LTC)\n\n<b>Address:</b>\n<pre>ltc1q4z6ncnp4sj58e96f2xnlhvr7txh53r3drfvjta</pre>'
            }
        }
        
        if language == 'ar':
            message = f"""💳 شحن رصيد
            
💰 المبلغ: ${amount:.2f}
💎 النقاط المتوقعة: {expected_credits:.1f}
💵 سعر الكريديت: ${credit_price:.2f}

━━━━━━━━━━━━━━━
{payment_details.get(payment_method, {}).get('ar', '')}

━━━━━━━━━━━━━━━
📩 يرجى إرسال إثبات الدفع (صورة فقط)
⏱️ سيتم مراجعة الطلب من قبل الأدمن"""
        else:
            message = f"""💳 Balance Recharge
            
💰 Amount: ${amount:.2f}
💎 Expected Points: {expected_credits:.1f}
💵 Credit Price: ${credit_price:.2f}

━━━━━━━━━━━━━━━
{payment_details.get(payment_method, {}).get('en', '')}

━━━━━━━━━━━━━━━
📩 Please send payment proof (image only)
⏱️ Admin will review the request"""
        
        if language == 'ar':
            keyboard = [[InlineKeyboardButton("↩️ تغيير طريقة الدفع", callback_data="back_to_payment_method")]]
        else:
            keyboard = [[InlineKeyboardButton("↩️ Change Payment Method", callback_data="back_to_payment_method")]]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error in handle_recharge_payment_method_selection: {e}")
        await query.message.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى.")


async def handle_recharge_payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة إثبات دفع الشحن"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    order_id = context.user_data.get('recharge_order_id')
    amount = context.user_data.get('recharge_amount')
    expected_credits = context.user_data.get('expected_credits')
    payment_method = context.user_data.get('recharge_payment_method')
    
    if not order_id:
        await update.message.reply_text("❌ خطأ في النظام. يرجى إعادة المحاولة.")
        return
    
    # معالجة إثبات الدفع (صورة فقط مطلوبة)
    if not update.message.photo:
        if language == 'ar':
            await update.message.reply_text("❌ يرجى إرسال صورة إثبات الدفع فقط")
        else:
            await update.message.reply_text("❌ Please send payment proof image only")
        return
    
    file_id = update.message.photo[-1].file_id
    payment_proof = f"photo:{file_id}"
    
    print(f"📸 تم استلام إثبات دفع الشحن (صورة) للطلب: {order_id}")
    
    # إرسال نسخة للمستخدم
    if language == 'ar':
        caption = f"📸 إثبات دفع شحن الرصيد\n\n🆔 معرف الطلب: {order_id}\n💰 المبلغ: {amount}$\n💎 النقاط المتوقعة: {expected_credits:.1f}\n💳 طريقة الدفع: {payment_method}\n\n✅ تم حفظ إثبات الدفع بنجاح"
    else:
        caption = f"📸 Balance Recharge Payment Proof\n\n🆔 Order ID: {order_id}\n💰 Amount: {amount}$\n💎 Expected Points: {expected_credits:.1f}\n💳 Payment Method: {payment_method}\n\n✅ Payment proof saved successfully"
    
    await update.message.reply_photo(
        photo=file_id,
        caption=caption,
        parse_mode='HTML'
    )
    
    # الآن إنشاء الطلب في قاعدة البيانات مع إثبات الدفع (فقط بعد استلام الإثبات)
    db.create_recharge_order(order_id, user_id, amount, expected_credits)
    
    # تحديث الطلب بإثبات الدفع وطريقة الدفع
    db.execute_query(
        "UPDATE orders SET payment_proof = ?, payment_method = ?, status = 'pending' WHERE id = ? AND proxy_type = 'balance_recharge'",
        (payment_proof, payment_method, order_id)
    )
    print(f"💾 تم إنشاء الطلب وحفظ إثبات الدفع في قاعدة البيانات للطلب: {order_id}")
    
    # إرسال رسالة التأكيد
    message = MESSAGES[language]['recharge_order_created'].format(
        order_id=order_id,
        amount=amount,
        points=expected_credits
    )
    await update.message.reply_text(message, parse_mode='HTML')
    print(f"✅ تم إرسال رسالة التأكيد للمستخدم لطلب الشحن: {order_id}")
    
    # إرسال إشعار للأدمن
    try:
        print(f"🔔 محاولة إرسال إشعار للأدمن لطلب الشحن: {order_id}")
        await send_recharge_admin_notification(context, order_id, user_id, amount, expected_credits, payment_proof, payment_method)
        print(f"✅ تم إرسال إشعار الأدمن بنجاح لطلب الشحن: {order_id}")
    except Exception as e:
        print(f"⚠️ خطأ في إرسال إشعار الأدمن لطلب الشحن {order_id}: {e}")
    
    # تنظيف البيانات المؤقتة
    context.user_data.pop('recharge_order_id', None)
    context.user_data.pop('recharge_amount', None)
    context.user_data.pop('expected_credits', None)
    context.user_data.pop('waiting_for_recharge_proof', None)
    
    # العودة للقائمة الرئيسية
    await handle_back_to_main_menu(update, context)

async def handle_back_to_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الرجوع لإدخال المبلغ"""
    try:
        query = update.callback_query
        user_id = update.effective_user.id
        language = get_user_language(user_id)
        
        await query.answer()
        
        # حذف البيانات المؤقتة للعودة لإدخال المبلغ
        context.user_data.pop('recharge_order_id', None)
        context.user_data.pop('recharge_amount', None)
        context.user_data.pop('expected_credits', None)
        context.user_data.pop('waiting_for_recharge_payment_method', None)
        context.user_data['waiting_for_recharge_amount'] = True
        
        # عرض رسالة إدخال المبلغ مرة أخرى
        credit_price = db.get_credit_price()
        message = MESSAGES[language]['recharge_request'].format(credit_price=credit_price)
        
        # إنشاء زر الرجوع
        if language == 'ar':
            keyboard = [[InlineKeyboardButton("↩️ رجوع للقائمة الرئيسية", callback_data="back_to_main_from_recharge")]]
        else:
            keyboard = [[InlineKeyboardButton("↩️ Back to Main Menu", callback_data="back_to_main_from_recharge")]]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode='HTML')
        await query.message.reply_text(MESSAGES[language]['enter_recharge_amount'], reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in handle_back_to_amount: {e}")
        await query.edit_message_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى.")

async def handle_back_to_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الرجوع من صورة التأكيد إلى اختيار طريقة الدفع"""
    try:
        query = update.callback_query
        user_id = update.effective_user.id
        language = get_user_language(user_id)
        
        await query.answer()
        
        # استرجاع بيانات الطلب
        amount = context.user_data.get('recharge_amount')
        expected_credits = context.user_data.get('expected_credits')
        
        if not amount or not expected_credits:
            await query.edit_message_text("❌ خطأ في النظام. يرجى إعادة المحاولة.")
            return
        
        # إعادة تعيين الحالة
        context.user_data['waiting_for_recharge_proof'] = False
        context.user_data['waiting_for_recharge_payment_method'] = True
        context.user_data.pop('recharge_payment_method', None)
        
        # عرض طرق الدفع مرة أخرى
        if language == 'ar':
            keyboard = [
                [InlineKeyboardButton("💳 شام كاش", callback_data="recharge_payment_shamcash")],
                [InlineKeyboardButton("💳 سيرياتيل كاش", callback_data="recharge_payment_syriatel")],
                [InlineKeyboardButton("🪙 Coinex", callback_data="recharge_payment_coinex")],
                [InlineKeyboardButton("🪙 Binance", callback_data="recharge_payment_binance")],
                [InlineKeyboardButton("🔗 BEP20", callback_data="recharge_payment_bep20")],
                [InlineKeyboardButton("🔗 Litecoin", callback_data="recharge_payment_litecoin")],
                [InlineKeyboardButton("🪙 Payeer", callback_data="recharge_payment_payeer")],
                [InlineKeyboardButton("↩️ رجوع", callback_data="back_to_amount")]
            ]
            message = f"💰 مبلغ الشحن: {amount}$\n💎 النقاط المتوقعة: {expected_credits:.1f}\n\n💳 اختر طريقة الدفع المفضلة:"
        else:
            keyboard = [
                [InlineKeyboardButton("💳 Sham Cash", callback_data="recharge_payment_shamcash")],
                [InlineKeyboardButton("💳 Syriatel Cash", callback_data="recharge_payment_syriatel")],
                [InlineKeyboardButton("🪙 Coinex", callback_data="recharge_payment_coinex")],
                [InlineKeyboardButton("🪙 Binance", callback_data="recharge_payment_binance")],
                [InlineKeyboardButton("🔗 BEP20", callback_data="recharge_payment_bep20")],
                [InlineKeyboardButton("🔗 Litecoin", callback_data="recharge_payment_litecoin")],
                [InlineKeyboardButton("🪙 Payeer", callback_data="recharge_payment_payeer")],
                [InlineKeyboardButton("↩️ Back", callback_data="back_to_amount")]
            ]
            message = f"💰 Recharge Amount: {amount}$\n💎 Expected Points: {expected_credits:.1f}\n\n💳 Choose your preferred payment method:"
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in handle_back_to_payment_method: {e}")
        await query.edit_message_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى.")


async def handle_back_to_main_from_recharge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الرجوع للقائمة الرئيسية من شحن الرصيد"""
    try:
        query = update.callback_query
        user_id = update.effective_user.id
        language = get_user_language(user_id)
        
        await query.answer()
        
        # تنظيف جميع البيانات المؤقتة لشحن الرصيد
        context.user_data.pop('recharge_order_id', None)
        context.user_data.pop('recharge_amount', None)
        context.user_data.pop('expected_credits', None)
        context.user_data.pop('recharge_payment_method', None)
        context.user_data.pop('waiting_for_recharge_amount', None)
        context.user_data.pop('waiting_for_recharge_payment_method', None)
        context.user_data.pop('waiting_for_recharge_proof', None)
        
        # حذف الرسالة القديمة وإرسال القائمة الرئيسية الجديدة
        try:
            await query.delete_message()
        except:
            pass
        
        main_keyboard = create_main_user_keyboard(language)
        await context.bot.send_message(
            user_id,
            MESSAGES[language]['welcome'],
            reply_markup=main_keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in handle_back_to_main_from_recharge: {e}")
        try:
            await context.bot.send_message(
                update.effective_user.id,
                "❌ حدث خطأ، يرجى المحاولة مرة أخرى."
            )
        except:
            pass

async def handle_recharge_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة زر شحن الرصيد من تدفق الشراء (عند عدم كفاية الرصيد) - يستخدم نفس التدفق العادي"""
    try:
        query = update.callback_query
        user_id = update.effective_user.id
        language = get_user_language(user_id)
        
        await query.answer()
        
        # الحصول على سعر النقطة
        credit_price = db.get_credit_price()
        
        # عرض رسالة طلب شحن الرصيد
        message = MESSAGES[language]['recharge_request'].format(credit_price=credit_price)
        
        # إنشاء زر الرجوع
        if language == 'ar':
            keyboard = [[InlineKeyboardButton("↩️ رجوع للقائمة الرئيسية", callback_data="back_to_main_from_recharge")]]
        else:
            keyboard = [[InlineKeyboardButton("↩️ Back to Main Menu", callback_data="back_to_main_from_recharge")]]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # حذف الرسالة القديمة وإرسال رسائل جديدة
        try:
            await query.delete_message()
        except:
            pass
        
        await context.bot.send_message(user_id, message, parse_mode='HTML')
        await context.bot.send_message(user_id, MESSAGES[language]['enter_recharge_amount'], reply_markup=reply_markup)
        
        # تعيين حالة انتظار المبلغ
        context.user_data['waiting_for_recharge_amount'] = True
        
    except Exception as e:
        logger.error(f"Error in handle_recharge_balance_callback: {e}")
        try:
            await context.bot.send_message(
                update.effective_user.id,
                "❌ حدث خطأ، يرجى المحاولة مرة أخرى."
            )
        except:
            pass

async def send_recharge_admin_notification(context, order_id: str, user_id: int, amount: float, expected_credits: float, payment_proof: str, payment_method: str = "غير محدد"):
    """إرسال إشعار للآدمن النشطين عن طلب شحن رصيد جديد"""
    try:
        global ACTIVE_ADMINS
        
        if not ACTIVE_ADMINS:
            return
        
        user = db.get_user(user_id)
        if not user:
            return
        
        # معالجة طريقة الدفع للعرض
        payment_method_display = {
            'shamcash': 'شام كاش 💳',
            'syriatel': 'سيرياتيل كاش 💳',
            'coinex': 'Coinex 🪙',
            'binance': 'Binance 🪙',
            'payeer': 'Payeer 🪙'
        }.get(payment_method, payment_method or 'غير محدد')
        
        # رسالة مختصرة للإشعار - بدون تفاصيل
        first_name = str(user[2]) if user[2] else ''
        last_name = str(user[3]) if user[3] else ''
        username = str(user[1]) if user[1] else 'غير محدد'
        
        message = f"""🔔 طلب شحن رصيد جديد!

👤 {first_name} {last_name} (@{username})
💰 ${amount:.2f} → {expected_credits:.2f} نقطة
🆔 <code>{order_id}</code>"""

        keyboard = [
            [InlineKeyboardButton("📋 عرض تفاصيل الطلب", callback_data=f"view_recharge_{order_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # إرسال الإشعار لجميع الآدمن النشطين
        for admin_id in ACTIVE_ADMINS:
            try:
                await context.bot.send_message(
                    admin_id,
                    message,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Error sending recharge notification to admin {admin_id}: {e}")
    except Exception as e:
        logger.error(f"Error sending recharge admin notification: {e}")

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

async def handle_about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة أمر /about"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    # رسالة حول البوت
    about_message = MESSAGES[language]['about_bot']
    
    # إنشاء زر لإظهار النافذة المنبثقة
    if language == 'ar':
        button_text = "🧑‍💻 معلومات المطور"
        popup_text = """🧑‍💻 معلومات المطور

📦 بوت بيع البروكسي وإدارة البروكسي
🔢 الإصدار: 1.1.0

━━━━━━━━━━━━━━━
👨‍💻 طُور بواسطة: Mohamad Zalaf

📞 معلومات الاتصال:
📱 تليجرام: @MohamadZalaf
📧 البريد الإلكتروني:
   • MohamadZalaf@outlook.com
   • Mohamadzalaf2017@gmail.com

━━━━━━━━━━━━━━━
© Mohamad Zalaf 2025"""
    else:
        button_text = "🧑‍💻 Developer Info"
        popup_text = """🧑‍💻 Developer Information

📦 Proxy Sales & Management Bot
🔢 Version: 1.1.0

━━━━━━━━━━━━━━━
👨‍💻 Developed by: Mohamad Zalaf

📞 Contact Information:
📱 Telegram: @MohamadZalaf
📧 Email:
   • MohamadZalaf@outlook.com
   • Mohamadzalaf2017@gmail.com

━━━━━━━━━━━━━━━
© Mohamad Zalaf 2025"""
    
    keyboard = [[InlineKeyboardButton(button_text, callback_data="developer_info")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # إرسال الرسالة مع الزر
    await update.message.reply_text(
        about_message, 
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    # حفظ النص المنبثق في context للاستخدام لاحقاً
    context.user_data['popup_text'] = popup_text

async def handle_reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة أمر /reset لإعادة تعيين حالة المستخدم"""
    user_id = update.effective_user.id
    
    # تنظيف شامل للبيانات المؤقتة مع الحفاظ على حالة الأدمن
    clean_user_data_preserve_admin(context)
    
    # إنهاء أي محادثات نشطة
    try:
        return ConversationHandler.END
    except:
        pass
    
    # إعادة توجيه المستخدم بناءً على نوعه
    if context.user_data.get('is_admin', False) or user_id in ACTIVE_ADMINS:
        await restore_admin_keyboard(context, update.effective_chat.id, "🔄 تم إعادة تعيين حالة الأدمن")
    else:
        await start(update, context)
    
    await force_reset_user_state(update, context)

async def handle_cleanup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة أمر /cleanup لتنظيف العمليات المعلقة"""
    user_id = update.effective_user.id
    is_admin = context.user_data.get('is_admin', False) or user_id in ACTIVE_ADMINS
    
    try:
        # تنظيف البيانات المؤقتة أولاً مع الحفاظ على حالة الأدمن
        clean_user_data_preserve_admin(context)
        
        # إعادة توجيه المستخدم للحالة المناسبة
        if is_admin:
            await restore_admin_keyboard(context, update.effective_chat.id, "🧹 تم تنظيف العمليات بنجاح")
        else:
            await update.message.reply_text(
                "🧹 <b>تم تنظيف العمليات المعلقة بنجاح</b>\n\n"
                "✅ تم إزالة جميع البيانات المؤقتة\n"
                "✅ تم تنظيف المحادثات المعلقة\n"
                "✅ البوت جاهز للاستخدام بشكل طبيعي",
                parse_mode='HTML'
            )
            # إعادة إرسال القائمة الرئيسية للمستخدم العادي
            await start(update, context)
    except Exception as e:
        await update.message.reply_text(
            "⚠️ حدث خطأ أثناء التنظيف\n"
            "يرجى استخدام /reset لإعادة تعيين كاملة"
        )

async def handle_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة أمر /status لعرض حالة المستخدم الحالية"""
    user_id = update.effective_user.id
    
    # جمع معلومات الحالة
    user_data_keys = list(context.user_data.keys())
    is_admin = context.user_data.get('is_admin', False) or user_id in ACTIVE_ADMINS
    
    # تحديد العمليات النشطة
    active_operations = []
    
    if 'processing_order_id' in context.user_data:
        active_operations.append(f"🔄 معالجة طلب: {context.user_data['processing_order_id']}")
    
    if 'proxy_type' in context.user_data:
        active_operations.append(f"📦 طلب بروكسي: {context.user_data['proxy_type']}")
    
    if 'waiting_for' in context.user_data:
        active_operations.append(f"⏳ انتظار إدخال: {context.user_data['waiting_for']}")
    
    if 'broadcast_type' in context.user_data:
        active_operations.append(f"📢 إعداد بث: {context.user_data['broadcast_type']}")
    
    # إنشاء رسالة الحالة
    status_message = f"📊 <b>حالة المستخدم</b>\n\n"
    status_message += f"👤 المعرف: <code>{user_id}</code>\n"
    status_message += f"🔧 نوع المستخدم: {'أدمن' if is_admin else 'مستخدم عادي'}\n"
    status_message += f"💾 عدد البيانات المؤقتة: {len(user_data_keys)}\n\n"
    
    if active_operations:
        status_message += "🔄 <b>العمليات النشطة:</b>\n"
        for op in active_operations:
            status_message += f"• {op}\n"
    else:
        status_message += "✅ <b>لا توجد عمليات نشطة</b>\n"
    
    status_message += "\n📋 <b>الأوامر المتاحة:</b>\n"
    status_message += "• <code>/reset</code> - إعادة تعيين كاملة\n"
    status_message += "• <code>/cleanup</code> - تنظيف العمليات المعلقة\n"
    status_message += "• <code>/start</code> - العودة للقائمة الرئيسية"
    
    await update.message.reply_text(status_message, parse_mode='HTML')

async def handle_language_change(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة تغيير اللغة"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    is_admin = context.user_data.get('is_admin', False) or user_id in ACTIVE_ADMINS
    
    # تحديد اللغة الجديدة من نوع الزر
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
    
    # إذا كان آدمن، حذف الرسالة القديمة وإرسال لوحة الآدمن بدلاً من تعديلها
    if is_admin:
        try:
            await query.delete_message()
        except:
            await query.edit_message_text(message)
        
        await restore_admin_keyboard(context, user_id, 
                                     "تم تحديث اللغة ✅" if new_language == 'ar' else "Language updated ✅",
                                     language=new_language)
    else:
        # للمستخدمين العاديين، تعديل الرسالة وإرسال الكيبورد الرئيسي
        await query.edit_message_text(message)
        
        # إرسال القائمة الرئيسية بعد تغيير اللغة
        main_keyboard = create_main_user_keyboard(new_language)
        await context.bot.send_message(
            user_id,
            MESSAGES[new_language]['welcome'],
            reply_markup=main_keyboard
        )

async def handle_user_quantity_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة اختيار الكمية من قبل المستخدم"""
    try:
        query = update.callback_query
        user_id = update.effective_user.id
        
        # تسجيل مفصل لتتبع المشكلة
        logger.info(f"=== QUANTITY SELECTION START ===")
        logger.info(f"User ID: {user_id}")
        logger.info(f"Query data: {query.data}")
        logger.info(f"Current user_data: {context.user_data}")
        
        # تسجيل الإجراء
        logger.info(f"User {user_id} selected quantity: {query.data}")
        
        try:
            await query.answer()
        except Exception as answer_error:
            logger.warning(f"Failed to answer quantity callback for user {user_id}: {answer_error}")
        
        language = get_user_language(user_id)
        
        if query.data == "quantity_one_socks":
            logger.info(f"Processing ONE SOCKS PROXY for user {user_id}")
            
            # فحص فوري لحالة الخدمة
            if not db.get_service_status('socks', 'single'):
                if language == 'ar':
                    await query.edit_message_text("❌ خدمة السوكس الواحد غير متاحة حالياً\n\nيرجى اختيار خدمة أخرى أو المحاولة لاحقاً.")
                else:
                    await query.edit_message_text("❌ Single socks service is currently unavailable\n\nPlease choose another service or try again later.")
                return
            
            # الحصول على السعر الفعلي من قاعدة البيانات
            socks_prices = get_socks_prices()
            single_price = float(socks_prices.get('single_proxy', '0.15'))
            
            context.user_data['quantity'] = '1'  # كمية واحدة
            context.user_data['proxy_type'] = 'socks'
            context.user_data['socks_price'] = single_price
            # الانتقال لاختيار الدولة
            await show_country_selection_for_user(query, context, language)
            logger.info(f"=== QUANTITY SELECTION SUCCESS (one socks) ===")
            
        elif query.data == "quantity_two_socks":
            logger.info(f"Processing TWO SOCKS PROXIES for user {user_id}")
            
            # فحص فوري لحالة الخدمة
            if not db.get_service_status('socks', 'package_2'):
                if language == 'ar':
                    await query.edit_message_text("❌ خدمة السوكس اثنان غير متاحة حالياً\n\nيرجى اختيار خدمة أخرى أو المحاولة لاحقاً.")
                else:
                    await query.edit_message_text("❌ Two socks service is currently unavailable\n\nPlease choose another service or try again later.")
                return
            
            # الحصول على السعر الفعلي من قاعدة البيانات
            socks_prices = get_socks_prices()
            double_price = float(socks_prices.get('double_proxy', '0.25'))
            
            context.user_data['quantity'] = 1  # باكج واحد يحتوي على 2 بروكسي
            context.user_data['proxy_type'] = 'socks'
            context.user_data['socks_price'] = double_price
            # الانتقال لاختيار الدولة
            await show_country_selection_for_user(query, context, language)
            logger.info(f"=== QUANTITY SELECTION SUCCESS (two socks) ===")
            
        elif query.data == "quantity_verizon_static":
            logger.info(f"Processing RESIDENTIAL VERIZON for user {user_id}")
            
            # فحص فوري لحالة الخدمة
            if not db.get_service_status('static', 'monthly_verizon'):
                if language == 'ar':
                    await query.edit_message_text("❌ خدمة ريزيدنتال ڤيرايزون غير متاحة حالياً\n\nيرجى اختيار خدمة أخرى أو المحاولة لاحقاً.")
                else:
                    await query.edit_message_text("❌ Residential Verizon service is currently unavailable\n\nPlease choose another service or try again later.")
                return
            
            context.user_data['quantity'] = '5'
            context.user_data['static_type'] = 'residential_verizon'
            # عرض دولة أمريكا
            if language == 'ar':
                keyboard = [
                    [InlineKeyboardButton("🇺🇸 الولايات المتحدة", callback_data="country_US_verizon")]
                ]
                country_text = "اختر الدولة:"
            else:
                keyboard = [
                    [InlineKeyboardButton("🇺🇸 United States", callback_data="country_US_verizon")]
                ]
                country_text = "Choose country:"
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(country_text, reply_markup=reply_markup)
            logger.info(f"=== QUANTITY SELECTION SUCCESS (residential verizon) ===")
            
        elif query.data == "quantity_crocker_static":
            logger.info(f"Processing RESIDENTIAL CROCKER for user {user_id}")
            
            # فحص فوري لحالة الخدمة
            if not db.get_service_status('static', 'monthly_verizon'):
                if language == 'ar':
                    await query.edit_message_text("❌ خدمة ريزيدنتال كروكر غير متاحة حالياً\n\nيرجى اختيار خدمة أخرى أو المحاولة لاحقاً.")
                else:
                    await query.edit_message_text("❌ Residential Crocker service is currently unavailable\n\nPlease choose another service or try again later.")
                return
            
            context.user_data['quantity'] = '5'
            context.user_data['static_type'] = 'residential_crocker'
            # عرض دولة أمريكا
            if language == 'ar':
                keyboard = [
                    [InlineKeyboardButton("🇺🇸 الولايات المتحدة", callback_data="country_US_crocker")]
                ]
                country_text = "اختر الدولة:"
            else:
                keyboard = [
                    [InlineKeyboardButton("🇺🇸 United States", callback_data="country_US_crocker")]
                ]
                country_text = "Choose country:"
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(country_text, reply_markup=reply_markup)
            logger.info(f"=== QUANTITY SELECTION SUCCESS (residential crocker) ===")
        elif query.data == "residential_4_dollar":
            logger.info(f"Processing RESIDENTIAL $4 - Duration Selection for user {user_id}")
            
            # عرض خيارات المدة الزمنية أولاً
            if language == 'ar':
                weekly_price = get_res4_price('weekly')
                days15_price = get_res4_price('15days')
                monthly_price = get_res4_price('monthly')
                keyboard = [
                    [InlineKeyboardButton(f"📅 أسبوعي (7 أيام) - (${weekly_price})", callback_data="res4_duration_weekly")],
                    [InlineKeyboardButton(f"📅 15 يوماً - (${days15_price})", callback_data="res4_duration_15days")],
                    [InlineKeyboardButton(f"📅 شهري (30 يوم) - (${monthly_price})", callback_data="res4_duration_monthly")]
                ]
                choice_text = "⏰ اختر المدة الزمنية - ريزيدنتال مرن\n\n💡 الأسعار موضحة بجانب كل خيار"
            else:
                weekly_price = get_res4_price('weekly')
                days15_price = get_res4_price('15days')
                monthly_price = get_res4_price('monthly')
                keyboard = [
                    [InlineKeyboardButton(f"📅 Weekly (7 days) - (${weekly_price})", callback_data="res4_duration_weekly")],
                    [InlineKeyboardButton(f"📅 15 Days - (${days15_price})", callback_data="res4_duration_15days")],
                    [InlineKeyboardButton(f"📅 Monthly (30 days) - (${monthly_price})", callback_data="res4_duration_monthly")]
                ]
                choice_text = "⏰ Choose Duration - Flexible Residential\n\n💡 Prices are shown next to each option"
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(choice_text, reply_markup=reply_markup)
            logger.info(f"=== RESIDENTIAL $4 DURATION MENU SHOWN ===")
            
            
        
        # معالجات المدة الزمنية لـ Residential $4
        elif query.data.startswith("res4_duration_"):
            duration_type = query.data.replace("res4_duration_", "")
            logger.info(f"Processing RES4 Duration: {duration_type} for user {user_id}")
            
            # حفظ المدة المختارة
            duration_map = {
                'weekly': 'أسبوعي' if language == 'ar' else 'Weekly',
                '15days': '15 يوماً' if language == 'ar' else '15 Days',
                'monthly': 'شهري' if language == 'ar' else 'Monthly'
            }
            context.user_data['res4_duration'] = duration_map.get(duration_type, duration_type)
            context.user_data['res4_duration_type'] = duration_type  # حفظ نوع المدة لحساب السعر لاحقاً
            
            # جلب السعر حسب المدة المختارة
            price_by_duration = {
                'weekly': get_res4_price('weekly'),
                '15days': get_res4_price('15days'),
                'monthly': get_res4_price('monthly')
            }
            selected_price = price_by_duration.get(duration_type, get_res4_price('monthly'))
            
            # الآن عرض قائمة الدول المتاحة - 17 دولة
            if language == 'ar':
                keyboard = [
                    [InlineKeyboardButton("🇺🇸 الولايات المتحدة", callback_data="res4_country_US")],
                    [InlineKeyboardButton("🏴󠁧󠁢󠁥󠁮󠁧󠁿 إنجلترا (NTT)", callback_data="res4_country_England")],
                    [InlineKeyboardButton("🇦🇹 النمسا", callback_data="res4_country_Austria")],
                    [InlineKeyboardButton("🇨🇦 كندا", callback_data="res4_country_Canada")],
                    [InlineKeyboardButton("🇪🇸 إسبانيا", callback_data="res4_country_Spain")],
                    [InlineKeyboardButton("🇮🇹 إيطاليا", callback_data="res4_country_Italy")],
                    [InlineKeyboardButton("🇳🇱 هولندا", callback_data="res4_country_Netherlands")],
                    [InlineKeyboardButton("🇵🇱 بولندا", callback_data="res4_country_Poland")],
                    [InlineKeyboardButton("🇷🇴 رومانيا", callback_data="res4_country_Romania")],
                    [InlineKeyboardButton("🇹🇷 تركيا", callback_data="res4_country_Turkey")],
                    [InlineKeyboardButton("🇺🇦 أوكرانيا", callback_data="res4_country_Ukraine")],
                    [InlineKeyboardButton("🇮🇱 إسرائيل", callback_data="res4_country_Israel")],
                    [InlineKeyboardButton("🇮🇳 الهند", callback_data="res4_country_India")],
                    [InlineKeyboardButton("🇭🇰 هونغ كونغ", callback_data="res4_country_HongKong")],
                    [InlineKeyboardButton("🇹🇭 تايلاند", callback_data="res4_country_Thailand")],
                    [InlineKeyboardButton("🇸🇬 سنغافورة", callback_data="res4_country_Singapore")],
                    [InlineKeyboardButton("🇹🇼 تايوان", callback_data="res4_country_Taiwan")],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="residential_4_dollar")]
                ]
                choice_text = f"🌍 اختر الدولة - ريزيدنتال مرن (NTT)\n⏰ المدة: {context.user_data['res4_duration']}\n💰 السعر: (${selected_price})"
            else:
                keyboard = [
                    [InlineKeyboardButton("🇺🇸 United States", callback_data="res4_country_US")],
                    [InlineKeyboardButton("🏴󠁧󠁢󠁥󠁮󠁧󠁿 England (NTT)", callback_data="res4_country_England")],
                    [InlineKeyboardButton("🇦🇹 Austria", callback_data="res4_country_Austria")],
                    [InlineKeyboardButton("🇨🇦 Canada", callback_data="res4_country_Canada")],
                    [InlineKeyboardButton("🇪🇸 Spain", callback_data="res4_country_Spain")],
                    [InlineKeyboardButton("🇮🇹 Italy", callback_data="res4_country_Italy")],
                    [InlineKeyboardButton("🇳🇱 Netherlands", callback_data="res4_country_Netherlands")],
                    [InlineKeyboardButton("🇵🇱 Poland", callback_data="res4_country_Poland")],
                    [InlineKeyboardButton("🇷🇴 Romania", callback_data="res4_country_Romania")],
                    [InlineKeyboardButton("🇹🇷 Turkey", callback_data="res4_country_Turkey")],
                    [InlineKeyboardButton("🇺🇦 Ukraine", callback_data="res4_country_Ukraine")],
                    [InlineKeyboardButton("🇮🇱 Israel", callback_data="res4_country_Israel")],
                    [InlineKeyboardButton("🇮🇳 India", callback_data="res4_country_India")],
                    [InlineKeyboardButton("🇭🇰 Hong Kong", callback_data="res4_country_HongKong")],
                    [InlineKeyboardButton("🇹🇭 Thailand", callback_data="res4_country_Thailand")],
                    [InlineKeyboardButton("🇸🇬 Singapore", callback_data="res4_country_Singapore")],
                    [InlineKeyboardButton("🇹🇼 Taiwan", callback_data="res4_country_Taiwan")],
                    [InlineKeyboardButton("🔙 Back", callback_data="residential_4_dollar")]
                ]
                choice_text = f"🌍 Choose Country - Flexible Residential (NTT)\n⏰ Duration: {context.user_data['res4_duration']}\n💰 Price: (${selected_price})"
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(choice_text, reply_markup=reply_markup)
            logger.info(f"=== RESIDENTIAL $4 COUNTRY MENU SHOWN (Duration: {context.user_data['res4_duration']}) ===")
            
        elif query.data == "quantity_single_socks":
            logger.info(f"Processing SOCKS PACKAGE 5 for user {user_id}")
            
            # فحص فوري لحالة الخدمة
            if not db.get_service_status('socks', 'package_5'):
                if language == 'ar':
                    await query.edit_message_text("❌ خدمة السوكس باكج 5 غير متاحة حالياً\n\nيرجى اختيار خدمة أخرى أو المحاولة لاحقاً.")
                else:
                    await query.edit_message_text("❌ Socks package 5 service is currently unavailable\n\nPlease choose another service or try again later.")
                return
            
            # الحصول على السعر الفعلي من قاعدة البيانات
            socks_prices = get_socks_prices()
            package5_price = float(socks_prices.get('5proxy', '0.4'))
            
            context.user_data['quantity'] = 5  # 5 بروكسيات منفصلة
            context.user_data['proxy_type'] = 'socks'
            context.user_data['socks_price'] = package5_price  # السعر للباكج كله
            context.user_data['is_package'] = True  # علامة أن هذا باكج (لا يتم ضرب السعر بالكمية)
            # الانتقال لاختيار الدولة
            await show_country_selection_for_user(query, context, language)
            logger.info(f"=== QUANTITY SELECTION SUCCESS (socks package 5) ===")
            
        elif query.data == "quantity_package_static":
            logger.info(f"Processing RESIDENTIAL 6$ for user {user_id}")
            
            # فحص فوري لحالة الخدمة
            if not db.get_service_status('static', 'monthly_residential'):
                if language == 'ar':
                    await query.edit_message_text("❌ خدمة ريزيدنتال غير متاحة حالياً\n\n🔧 الآدمن أوقف هذه الخدمة مؤقتاً بسبب:\n• تعطل في السيرفرات\n• نفاد الكمية المتاحة\n\nيرجى اختيار خدمة أخرى أو المحاولة لاحقاً.")
                else:
                    await query.edit_message_text("❌ Residential service is currently unavailable\n\nPlease choose another service or try again later.")
                return
            
            # تعيين نوع البروكسي
            context.user_data['proxy_type'] = 'static'
            
            # عرض قائمة الدول المتاحة - USA و UK
            att_price = get_current_price('att')
            if language == 'ar':
                keyboard = [
                    [InlineKeyboardButton("🇺🇸 الولايات المتحدة", callback_data="res6_country_US")],
                    [InlineKeyboardButton("🇬🇧 المملكة المتحدة", callback_data="res6_country_UK")],
                    [InlineKeyboardButton("🇫🇷 فرنسا", callback_data="res6_country_FR")],
                    [InlineKeyboardButton("🇩🇪 ألمانيا", callback_data="res6_country_DE")],
                    [InlineKeyboardButton("🇦🇹 النمسا", callback_data="res6_country_AT")]
                ]
                choice_text = f"🌍 اختر الدولة - Residential ${att_price}:"
            else:
                keyboard = [
                    [InlineKeyboardButton("🇺🇸 United States", callback_data="res6_country_US")],
                    [InlineKeyboardButton("🇬🇧 United Kingdom", callback_data="res6_country_UK")],
                    [InlineKeyboardButton("🇫🇷 France", callback_data="res6_country_FR")],
                    [InlineKeyboardButton("🇩🇪 Germany", callback_data="res6_country_DE")],
                    [InlineKeyboardButton("🇦🇹 Austria", callback_data="res6_country_AT")]
                ]
                choice_text = f"🌍 Choose Country - Residential ${att_price}:"
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(choice_text, reply_markup=reply_markup)
            logger.info(f"=== RESIDENTIAL $6 COUNTRY MENU SHOWN ===")
            
        elif query.data == "quantity_package_socks":
            logger.info(f"Processing SOCKS PACKAGE 10 for user {user_id}")
            
            # فحص فوري لحالة الخدمة
            if not db.get_service_status('socks', 'package_10'):
                if language == 'ar':
                    await query.edit_message_text("❌ خدمة السوكس باكج 10 غير متاحة حالياً\n\nيرجى اختيار خدمة أخرى أو المحاولة لاحقاً.")
                else:
                    await query.edit_message_text("❌ Socks package 10 service is currently unavailable\n\nPlease choose another service or try again later.")
                return
            
            # الحصول على السعر الفعلي من قاعدة البيانات
            socks_prices = get_socks_prices()
            package10_price = float(socks_prices.get('10proxy', '0.7'))
            
            context.user_data['quantity'] = 10  # 10 بروكسيات منفصلة
            context.user_data['proxy_type'] = 'socks'
            context.user_data['socks_price'] = package10_price  # السعر للباكج كله
            context.user_data['is_package'] = True  # علامة أن هذا باكج (لا يتم ضرب السعر بالكمية)
            # الانتقال لاختيار الدولة
            await show_country_selection_for_user(query, context, language)
            logger.info(f"=== QUANTITY SELECTION SUCCESS (socks package 10) ===")
            
        elif query.data == "quantity_isp_static":
            logger.info(f"Processing ISP for user {user_id}")
            
            # فحص فوري لحالة الخدمة
            if not db.get_service_status('static', 'isp_att'):
                if language == 'ar':
                    await query.edit_message_text("❌ خدمة ISP غير متاحة حالياً\n\n🔧 الآدمن أوقف هذه الخدمة مؤقتاً بسبب:\n• تعطل في السيرفرات\n• نفاد الكمية المتاحة\n\nيرجى اختيار خدمة أخرى أو المحاولة لاحقاً.")
                else:
                    await query.edit_message_text("❌ ISP service is currently unavailable\n\nPlease choose another service or try again later.")
                return
            
            # إزالة الكمية الثابتة - سيتم سؤال المستخدم عنها لاحقاً
            context.user_data['static_type'] = 'isp'
            # الانتقال لاختيار الدولة
            await show_country_selection_for_user(query, context, language)
            logger.info(f"=== QUANTITY SELECTION SUCCESS (isp) ===")
            
        elif query.data == "datacenter_proxy":
            logger.info(f"Processing datacenter proxy for user {user_id}")
            
            # فحص فوري لحالة الخدمة
            if not db.get_service_status('static', 'datacenter'):
                if language == 'ar':
                    await query.edit_message_text("❌ خدمة بروكسي داتا سينتر غير متاحة حالياً\n\nيرجى اختيار خدمة أخرى أو المحاولة لاحقاً.")
                else:
                    await query.edit_message_text("❌ Datacenter proxy service is currently unavailable\n\nPlease choose another service or try again later.")
                return
            
            datacenter_price = get_current_price('datacenter')
            if language == 'ar':
                message = f"""🔧 بروكسي داتا سينتر

📦 باقة 100 بروكسي
📅 شهري
💰 السعر: {datacenter_price}$

📞 للطلب الرجاء التواصل مع الإدارة:
@Static_support"""
            else:
                message = f"""🔧 Datacenter Proxy

📦 Package: 100 proxies
📅 Monthly
💰 Price: {datacenter_price}$

📞 To place an order, please contact administration:
@Static_support"""
            await query.message.reply_text(message)
            return
            
        elif query.data == "virgin_residential_proxy":
            logger.info(f"Processing Virgin Residential proxy for user {user_id}")
            
            # فحص فوري لحالة الخدمة
            if not db.get_service_status('static', 'virgin_residential'):
                if language == 'ar':
                    await query.edit_message_text("❌ خدمة ڤيرجين ريزيدنتال غير متاحة حالياً\n\nيرجى اختيار خدمة أخرى أو المحاولة لاحقاً.")
                else:
                    await query.edit_message_text("❌ Virgin Residential service is currently unavailable\n\nPlease choose another service or try again later.")
                return
            
            # تعيين static_type فقط
            context.user_data['proxy_type'] = 'static'
            context.user_data['static_type'] = 'virgin_residential'
            # الانتقال لاختيار الدولة (أمريكا فقط، بدون ولايات)
            await show_country_selection_for_user(query, context, language)
            logger.info(f"=== PREMIUM RESIDENTIAL SELECTION SUCCESS ===")
            return
            
        elif query.data == "static_daily":
            logger.info(f"Processing static daily for user {user_id}")
            
            # فحص فوري لحالة الخدمة
            if not db.get_service_status('static', 'daily_static'):
                if language == 'ar':
                    await query.edit_message_text("❌ خدمة الستاتيك اليومي غير متاحة حالياً\n\nيرجى اختيار خدمة أخرى أو المحاولة لاحقاً.")
                else:
                    await query.edit_message_text("❌ Daily Static service is currently unavailable\n\nPlease choose another service or try again later.")
                return
            
            context.user_data['proxy_type'] = 'static'
            context.user_data['static_type'] = 'daily'
            
            # عرض الدول والولايات للستاتيك اليومي - أمريكا/فيرجينيا فقط
            if language == 'ar':
                message = "🌍 اختر الدولة المطلوبة:"
                keyboard = [
                    [InlineKeyboardButton("🇺🇸 الولايات المتحدة", callback_data="country_US_daily")]
                ]
            else:
                message = "🌍 Choose the required country:"
                keyboard = [
                    [InlineKeyboardButton("🇺🇸 United States", callback_data="country_US_daily")]
                ]
                
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)
            return
            
        elif query.data == "static_weekly":
            logger.info(f"Processing static weekly for user {user_id}")
            if language == 'ar':
                await query.message.reply_text("📅 ستاتيك اسبوعي\n🔄 ستتوفر الخدمة قريباً")
            else:
                await query.message.reply_text("📅 Static Weekly\n🔄 Service will be available soon")
            return
        elif query.data == "verizon_weekly":
            # معالج الستاتيك الأسبوعي الجديد
            logger.info(f"Processing verizon weekly for user {user_id}")
            
            # فحص فوري لحالة الخدمة
            if not db.get_service_status('static', 'weekly_crocker'):
                if language == 'ar':
                    await query.edit_message_text("❌ خدمة الستاتيك الأسبوعي Crocker غير متاحة حالياً\n\nيرجى اختيار خدمة أخرى أو المحاولة لاحقاً.")
                else:
                    await query.edit_message_text("❌ Weekly static Crocker service is currently unavailable\n\nPlease choose another service or try again later.")
                return
            
            context.user_data['proxy_type'] = 'static'
            context.user_data['static_type'] = 'verizon_weekly'
            # إزالة الكمية الثابتة - سيتم سؤال المستخدم عنها لاحقاً
            
            # عرض الدول والولايات للستاتيك الأسبوعي
            if language == 'ar':
                message = "🌍 اختر الدولة المطلوبة:"
                keyboard = [
                    [InlineKeyboardButton("🇺🇸 الولايات المتحدة", callback_data="country_US_weekly")]
                ]
            else:
                message = "🌍 Choose the required country:"
                keyboard = [
                    [InlineKeyboardButton("🇺🇸 United States", callback_data="country_US_weekly")]
                ]
                
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)
            return
        
        # ========== معالجات Residential $4 - إصلاح أزرار USA و England ==========
        elif query.data == "res4_country_US":
            logger.info(f"Processing RES4 USA selection for user {user_id}")
            context.user_data['proxy_type'] = 'static'
            context.user_data['selected_country_code'] = 'US'
            context.user_data['selected_country'] = 'الولايات المتحدة' if language == 'ar' else 'United States'
            context.user_data['quantity'] = '5'
            
            # استخدام السعر حسب المدة المختارة بدلاً من السعر الثابت
            duration_type = context.user_data.get('res4_duration_type', 'monthly')
            res4_price = get_res4_price(duration_type)
            verizon_price = res4_price
            if language == 'ar':
                keyboard = [
                    [InlineKeyboardButton(f"🏠 Verizon (4 ولايات)", callback_data="res4_service_verizon")],
                    [InlineKeyboardButton(f"🌐 Level 3 ISP (NY)", callback_data="res4_service_level3")],
                    [InlineKeyboardButton(f"🏢 Crocker Communication (MA)", callback_data="res4_service_crocker")],
                    [InlineKeyboardButton(f"📡 Frontier Communications (VT)", callback_data="res4_service_frontier")],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="residential_4_dollar")]
                ]
                service_text = f"🇺🇸 اختر مزود الخدمة - ${verizon_price}:"
            else:
                keyboard = [
                    [InlineKeyboardButton(f"🏠 Verizon (4 states)", callback_data="res4_service_verizon")],
                    [InlineKeyboardButton(f"🌐 Level 3 ISP (NY)", callback_data="res4_service_level3")],
                    [InlineKeyboardButton(f"🏢 Crocker Communication (MA)", callback_data="res4_service_crocker")],
                    [InlineKeyboardButton(f"📡 Frontier Communications (VT)", callback_data="res4_service_frontier")],
                    [InlineKeyboardButton("🔙 Back", callback_data="residential_4_dollar")]
                ]
                service_text = f"🇺🇸 Choose Service Provider - ${verizon_price}:"
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(service_text, reply_markup=reply_markup)
            logger.info(f"=== RES4 USA SERVICE MENU SHOWN ===")
            return
        
        elif query.data == "res4_country_England":
            logger.info(f"Processing RES4 England selection for user {user_id}")
            context.user_data['proxy_type'] = 'static'
            context.user_data['selected_country_code'] = 'England'
            context.user_data['selected_country'] = 'إنجلترا' if language == 'ar' else 'England'
            context.user_data['selected_state_code'] = 'ENG'
            context.user_data['selected_state'] = 'إنجلترا' if language == 'ar' else 'England'
            context.user_data['quantity'] = '5'
            context.user_data['static_type'] = 'residential_ntt'
            
            # حفظ السعر حسب المدة المختارة
            duration_type = context.user_data.get('res4_duration_type', 'monthly')
            res4_price = get_res4_price(duration_type)
            context.user_data['payment_amount'] = float(res4_price)
            logger.info(f"England RES4 price set: ${res4_price} for duration: {duration_type}")
            
            # سؤال عن الكمية مباشرة
            await ask_static_proxy_quantity(query, context, language)
            logger.info(f"=== RES4 ENGLAND NTT SELECTED ===")
            return
        
        elif query.data == "res4_service_verizon":
            logger.info(f"Processing RES4 Verizon service for user {user_id}")
            context.user_data['static_type'] = 'residential_verizon'
            states = US_STATES_STATIC_VERIZON[language]
            keyboard = []
            for state_code, state_name in states.items():
                keyboard.append([InlineKeyboardButton(f"📍 {state_name}", callback_data=f"res4_state_{state_code}_verizon")])
            keyboard.append([InlineKeyboardButton("🔙 رجوع" if language == 'ar' else "🔙 Back", callback_data="res4_country_US")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            state_text = "🏠 اختر الولاية - Verizon:" if language == 'ar' else "🏠 Choose State - Verizon:"
            await query.edit_message_text(state_text, reply_markup=reply_markup)
            logger.info(f"=== RES4 VERIZON STATES SHOWN ===")
            return
        
        elif query.data == "res4_service_level3":
            logger.info(f"Processing RES4 Level 3 ISP service for user {user_id}")
            context.user_data['static_type'] = 'residential_level3'
            states = US_STATES_STATIC_LEVEL3[language]
            keyboard = []
            for state_code, state_name in states.items():
                keyboard.append([InlineKeyboardButton(f"📍 {state_name}", callback_data=f"res4_state_{state_code}_level3")])
            keyboard.append([InlineKeyboardButton("🔙 رجوع" if language == 'ar' else "🔙 Back", callback_data="res4_country_US")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            state_text = "🌐 اختر الولاية - Level 3 ISP:" if language == 'ar' else "🌐 Choose State - Level 3 ISP:"
            await query.edit_message_text(state_text, reply_markup=reply_markup)
            logger.info(f"=== RES4 LEVEL3 STATES SHOWN ===")
            return
        
        elif query.data == "res4_service_crocker":
            logger.info(f"Processing RES4 Crocker service for user {user_id}")
            context.user_data['static_type'] = 'residential_crocker'
            states = US_STATES_STATIC_CROCKER[language]
            keyboard = []
            for state_code, state_name in states.items():
                keyboard.append([InlineKeyboardButton(f"📍 {state_name}", callback_data=f"res4_state_{state_code}_crocker")])
            keyboard.append([InlineKeyboardButton("🔙 رجوع" if language == 'ar' else "🔙 Back", callback_data="res4_country_US")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            state_text = "🏢 اختر الولاية - Crocker:" if language == 'ar' else "🏢 Choose State - Crocker:"
            await query.edit_message_text(state_text, reply_markup=reply_markup)
            logger.info(f"=== RES4 CROCKER STATES SHOWN ===")
            return
        
        elif query.data == "res4_service_frontier":
            logger.info(f"Processing RES4 Frontier service for user {user_id}")
            context.user_data['static_type'] = 'residential_frontier'
            states = US_STATES_STATIC_FRONTIER[language]
            keyboard = []
            for state_code, state_name in states.items():
                keyboard.append([InlineKeyboardButton(f"📍 {state_name}", callback_data=f"res4_state_{state_code}_frontier")])
            keyboard.append([InlineKeyboardButton("🔙 رجوع" if language == 'ar' else "🔙 Back", callback_data="res4_country_US")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            state_text = "📡 اختر الولاية - Frontier:" if language == 'ar' else "📡 Choose State - Frontier:"
            await query.edit_message_text(state_text, reply_markup=reply_markup)
            logger.info(f"=== RES4 FRONTIER STATES SHOWN ===")
            return
        
        elif query.data.startswith("res4_state_"):
            logger.info(f"Processing RES4 state selection: {query.data} for user {user_id}")
            try:
                parts = query.data.replace("res4_state_", "").split("_")
                if len(parts) >= 2:
                    state_code = parts[0]
                    service_type = parts[1]
                    
                    context.user_data['selected_state_code'] = state_code
                    
                    if service_type == 'verizon':
                        state_name = US_STATES_STATIC_VERIZON[language].get(state_code, state_code)
                        context.user_data['static_type'] = 'residential_verizon'
                    elif service_type == 'level3':
                        state_name = US_STATES_STATIC_LEVEL3[language].get(state_code, state_code)
                        context.user_data['static_type'] = 'residential_level3'
                    elif service_type == 'crocker':
                        state_name = US_STATES_STATIC_CROCKER[language].get(state_code, state_code)
                        context.user_data['static_type'] = 'residential_crocker'
                    elif service_type == 'frontier':
                        state_name = US_STATES_STATIC_FRONTIER[language].get(state_code, state_code)
                        context.user_data['static_type'] = 'residential_frontier'
                    else:
                        state_name = state_code
                    
                    context.user_data['selected_state'] = state_name
                    
                    # حفظ السعر حسب المدة المختارة
                    duration_type = context.user_data.get('res4_duration_type', 'monthly')
                    res4_price = get_res4_price(duration_type)
                    context.user_data['payment_amount'] = float(res4_price)
                    logger.info(f"RES4 {service_type} price set: ${res4_price} for duration: {duration_type}")
                    
                    # سؤال عن الكمية
                    await ask_static_proxy_quantity(query, context, language)
                    logger.info(f"=== RES4 STATE SELECTED: {state_name} ({service_type}) ===")
            except Exception as e:
                logger.error(f"Error processing RES4 state selection: {e}")
                await query.edit_message_text("❌ خطأ في معالجة الاختيار" if language == 'ar' else "❌ Error processing selection")
            return
        
        # ========== معالجات الدول الجديدة (15 دولة) ==========
        elif query.data in ["res4_country_Austria", "res4_country_Canada", "res4_country_Spain", 
                           "res4_country_Italy", "res4_country_Netherlands", "res4_country_Poland",
                           "res4_country_Romania", "res4_country_Turkey", "res4_country_Ukraine",
                           "res4_country_Israel", "res4_country_India", "res4_country_HongKong",
                           "res4_country_Thailand", "res4_country_Singapore", "res4_country_Taiwan"]:
            country_code = query.data.replace("res4_country_", "")
            logger.info(f"Processing RES4 {country_code} selection for user {user_id}")
            
            country_names_ar = {
                'Austria': 'النمسا', 'Canada': 'كندا', 'Spain': 'إسبانيا',
                'Italy': 'إيطاليا', 'Netherlands': 'هولندا', 'Poland': 'بولندا',
                'Romania': 'رومانيا', 'Turkey': 'تركيا', 'Ukraine': 'أوكرانيا',
                'Israel': 'إسرائيل', 'India': 'الهند', 'HongKong': 'هونغ كونغ',
                'Thailand': 'تايلاند', 'Singapore': 'سنغافورة', 'Taiwan': 'تايوان'
            }
            country_names_en = {
                'Austria': 'Austria', 'Canada': 'Canada', 'Spain': 'Spain',
                'Italy': 'Italy', 'Netherlands': 'Netherlands', 'Poland': 'Poland',
                'Romania': 'Romania', 'Turkey': 'Turkey', 'Ukraine': 'Ukraine',
                'Israel': 'Israel', 'India': 'India', 'HongKong': 'Hong Kong',
                'Thailand': 'Thailand', 'Singapore': 'Singapore', 'Taiwan': 'Taiwan'
            }
            
            context.user_data['proxy_type'] = 'static'
            context.user_data['selected_country_code'] = country_code
            context.user_data['selected_country'] = country_names_ar[country_code] if language == 'ar' else country_names_en[country_code]
            context.user_data['selected_state_code'] = country_code
            context.user_data['selected_state'] = country_names_ar[country_code] if language == 'ar' else country_names_en[country_code]
            context.user_data['quantity'] = '5'
            context.user_data['static_type'] = f'residential_{country_code.lower()}'
            
            await ask_static_proxy_quantity(query, context, language)
            logger.info(f"=== RES4 {country_code} SELECTED ===")
            return
        
        # ========== معالجات Residential $6 - USA و UK ==========
        elif query.data == "res6_country_US":
            logger.info(f"Processing RES6 USA selection for user {user_id}")
            context.user_data['proxy_type'] = 'static'
            context.user_data['selected_country_code'] = 'US'
            context.user_data['selected_country'] = 'الولايات المتحدة' if language == 'ar' else 'United States'
            
            att_price = get_current_price('att')
            if language == 'ar':
                keyboard = [
                    [InlineKeyboardButton("📍 Colorado - Elite Broadband", callback_data="res6_state_CO")],
                    [InlineKeyboardButton("📍 Virginia - Windstream", callback_data="res6_state_VA_windstream")],
                    [InlineKeyboardButton("📍 Virginia - Cox Communication", callback_data="res6_state_VA_cox")],
                    [InlineKeyboardButton("📍 Virginia - Frontier", callback_data="res6_state_VA_frontier")],
                    [InlineKeyboardButton("📍 Texas - JY Mobile", callback_data="res6_state_TX")],
                    [InlineKeyboardButton("📍 New York - WS Telcom", callback_data="res6_state_NY_wstelcom")],
                    [InlineKeyboardButton("📍 New York - Century Link", callback_data="res6_state_NY_century")],
                    [InlineKeyboardButton("📍 Illinois - Access Telcom", callback_data="res6_state_IL")],
                    [InlineKeyboardButton("📍 Arizona - JY Mobile", callback_data="res6_state_AZ")],
                    [InlineKeyboardButton("📍 Florida - WS Telcom", callback_data="res6_state_FL")],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="quantity_package_static")]
                ]
                state_text = f"🇺🇸 اختر الولاية والمزود - ${att_price}:"
            else:
                keyboard = [
                    [InlineKeyboardButton("📍 Colorado - Elite Broadband", callback_data="res6_state_CO")],
                    [InlineKeyboardButton("📍 Virginia - Windstream", callback_data="res6_state_VA_windstream")],
                    [InlineKeyboardButton("📍 Virginia - Cox Communication", callback_data="res6_state_VA_cox")],
                    [InlineKeyboardButton("📍 Virginia - Frontier", callback_data="res6_state_VA_frontier")],
                    [InlineKeyboardButton("📍 Texas - JY Mobile", callback_data="res6_state_TX")],
                    [InlineKeyboardButton("📍 New York - WS Telcom", callback_data="res6_state_NY_wstelcom")],
                    [InlineKeyboardButton("📍 New York - Century Link", callback_data="res6_state_NY_century")],
                    [InlineKeyboardButton("📍 Illinois - Access Telcom", callback_data="res6_state_IL")],
                    [InlineKeyboardButton("📍 Arizona - JY Mobile", callback_data="res6_state_AZ")],
                    [InlineKeyboardButton("📍 Florida - WS Telcom", callback_data="res6_state_FL")],
                    [InlineKeyboardButton("🔙 Back", callback_data="quantity_package_static")]
                ]
                state_text = f"🇺🇸 Choose State & Provider - ${att_price}:"
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(state_text, reply_markup=reply_markup)
            logger.info(f"=== RES6 USA STATES MENU SHOWN ===")
            return
        
        elif query.data == "res6_country_UK":
            logger.info(f"Processing RES6 UK selection for user {user_id}")
            context.user_data['proxy_type'] = 'static'
            context.user_data['selected_country_code'] = 'UK'
            context.user_data['selected_country'] = 'المملكة المتحدة' if language == 'ar' else 'United Kingdom'
            
            att_price = get_current_price('att')
            if language == 'ar':
                keyboard = [
                    [InlineKeyboardButton("📡 British Communications", callback_data="res6_uk_british")],
                    [InlineKeyboardButton("🏢 Proper Support LLP", callback_data="res6_uk_proper")],
                    [InlineKeyboardButton("🌐 UK Link Web Fiber ISP", callback_data="res6_uk_linkweb")],
                    [InlineKeyboardButton("📞 UK WS Telcom", callback_data="res6_uk_wstelcom")],
                    [InlineKeyboardButton("🏛️ UK Base Communication LLP", callback_data="res6_uk_base")],
                    [InlineKeyboardButton("📺 Virgin Media", callback_data="res6_uk_virgin")],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="quantity_package_static")]
                ]
                provider_text = f"🇬🇧 اختر المزود - ${att_price}:"
            else:
                keyboard = [
                    [InlineKeyboardButton("📡 British Communications", callback_data="res6_uk_british")],
                    [InlineKeyboardButton("🏢 Proper Support LLP", callback_data="res6_uk_proper")],
                    [InlineKeyboardButton("🌐 UK Link Web Fiber ISP", callback_data="res6_uk_linkweb")],
                    [InlineKeyboardButton("📞 UK WS Telcom", callback_data="res6_uk_wstelcom")],
                    [InlineKeyboardButton("🏛️ UK Base Communication LLP", callback_data="res6_uk_base")],
                    [InlineKeyboardButton("📺 Virgin Media", callback_data="res6_uk_virgin")],
                    [InlineKeyboardButton("🔙 Back", callback_data="quantity_package_static")]
                ]
                provider_text = f"🇬🇧 Choose Provider - ${att_price}:"
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(provider_text, reply_markup=reply_markup)
            logger.info(f"=== RES6 UK PROVIDERS MENU SHOWN ===")
            return
        
        # معالجات الدول الجديدة لـ Residential $6 - France, Germany, Austria
        elif query.data == "res6_country_FR":
            logger.info(f"Processing RES6 France selection for user {user_id}")
            context.user_data['proxy_type'] = 'static'
            context.user_data['selected_country_code'] = 'FR'
            context.user_data['selected_country'] = 'فرنسا' if language == 'ar' else 'France'
            context.user_data['selected_state_code'] = 'FR'
            context.user_data['selected_state'] = 'فرنسا' if language == 'ar' else 'France'
            context.user_data['static_type'] = 'residential_france'
            context.user_data['quantity'] = '10'
            
            await ask_static_proxy_quantity(query, context, language)
            logger.info(f"=== RES6 FRANCE SELECTED ===")
            return
        
        elif query.data == "res6_country_DE":
            logger.info(f"Processing RES6 Germany selection for user {user_id}")
            context.user_data['proxy_type'] = 'static'
            context.user_data['selected_country_code'] = 'DE'
            context.user_data['selected_country'] = 'ألمانيا' if language == 'ar' else 'Germany'
            context.user_data['selected_state_code'] = 'DE'
            context.user_data['selected_state'] = 'ألمانيا' if language == 'ar' else 'Germany'
            context.user_data['static_type'] = 'residential_germany'
            context.user_data['quantity'] = '10'
            
            await ask_static_proxy_quantity(query, context, language)
            logger.info(f"=== RES6 GERMANY SELECTED ===")
            return
        
        elif query.data == "res6_country_AT":
            logger.info(f"Processing RES6 Austria selection for user {user_id}")
            context.user_data['proxy_type'] = 'static'
            context.user_data['selected_country_code'] = 'AT'
            context.user_data['selected_country'] = 'النمسا' if language == 'ar' else 'Austria'
            context.user_data['selected_state_code'] = 'AT'
            context.user_data['selected_state'] = 'النمسا' if language == 'ar' else 'Austria'
            context.user_data['static_type'] = 'residential_austria'
            context.user_data['quantity'] = '10'
            
            await ask_static_proxy_quantity(query, context, language)
            logger.info(f"=== RES6 AUSTRIA SELECTED ===")
            return
        
        # معالجات الولايات الأمريكية لـ Residential $6
        elif query.data.startswith("res6_state_"):
            logger.info(f"Processing RES6 state selection: {query.data} for user {user_id}")
            
            state_providers = {
                'CO': ('Colorado', 'Elite Broadband', 'كولورادو', 'residential_elite'),
                'VA_windstream': ('Virginia', 'Windstream', 'فيرجينيا', 'residential_windstream'),
                'VA_cox': ('Virginia', 'Cox Communication', 'فيرجينيا', 'residential_cox'),
                'VA_frontier': ('Virginia', 'Frontier Communications', 'فيرجينيا', 'residential_frontier_va'),
                'TX': ('Texas', 'JY Mobile Communication', 'تكساس', 'residential_jymobile_tx'),
                'NY_wstelcom': ('New York', 'WS Telcom', 'نيويورك', 'residential_wstelcom_ny'),
                'NY_century': ('New York', 'Century Link', 'نيويورك', 'residential_century'),
                'IL': ('Illinois', 'Access Telcom', 'إلينوي', 'residential_access'),
                'AZ': ('Arizona', 'JY Mobile Communication', 'أريزونا', 'residential_jymobile_az'),
                'FL': ('Florida', 'WS Telcom', 'فلوريدا', 'residential_wstelcom_fl')
            }
            
            state_key = query.data.replace("res6_state_", "")
            if state_key in state_providers:
                state_en, provider_en, state_ar, static_type = state_providers[state_key]
                
                context.user_data['selected_state_code'] = state_key
                context.user_data['selected_state'] = state_ar if language == 'ar' else state_en
                context.user_data['selected_provider'] = provider_en
                context.user_data['static_type'] = static_type
                context.user_data['quantity'] = '10'
                
                await ask_static_proxy_quantity(query, context, language)
                logger.info(f"=== RES6 USA STATE SELECTED: {state_en} - {provider_en} ===")
            return
        
        # معالجات مزودي UK لـ Residential $6
        elif query.data.startswith("res6_uk_"):
            logger.info(f"Processing RES6 UK provider: {query.data} for user {user_id}")
            
            uk_providers = {
                'british': ('British Communications', 'residential_british'),
                'proper': ('Proper Support LLP', 'residential_proper'),
                'linkweb': ('UK Link Web Fiber ISP', 'residential_linkweb'),
                'wstelcom': ('UK WS Telcom', 'residential_uk_wstelcom'),
                'base': ('UK Base Communication LLP', 'residential_base'),
                'virgin': ('Virgin Media', 'residential_virgin_uk')
            }
            
            provider_key = query.data.replace("res6_uk_", "")
            if provider_key in uk_providers:
                provider_name, static_type = uk_providers[provider_key]
                
                context.user_data['selected_state_code'] = 'UK'
                context.user_data['selected_state'] = 'المملكة المتحدة' if language == 'ar' else 'United Kingdom'
                context.user_data['selected_provider'] = provider_name
                context.user_data['static_type'] = static_type
                context.user_data['quantity'] = '10'
                
                await ask_static_proxy_quantity(query, context, language)
                logger.info(f"=== RES6 UK PROVIDER SELECTED: {provider_name} ===")
            return
        
        else:
            # معالجة قيمة غير متوقعة
            logger.warning(f"Unknown quantity selection: {query.data} from user {user_id}")
            await query.message.reply_text(
                "⚠️ اختيار غير صالح. يرجى المحاولة مرة أخرى أو استخدام /start",
                reply_markup=ReplyKeyboardRemove()
            )
            # تنظيف البيانات والعودة للقائمة الرئيسية
            context.user_data.clear()
            
    except Exception as e:
        logger.error(f"Error in handle_user_quantity_selection for user {user_id}: {e}")
        
        try:
            await update.callback_query.message.reply_text(
                "⚠️ حدث خطأ في معالجة اختيارك. تم إعادة تعيين حالتك.\n"
                "يرجى استخدام /start لإعادة المحاولة.",
                reply_markup=ReplyKeyboardRemove()
            )
            # تنظيف البيانات المؤقتة
            context.user_data.clear()
        except Exception as recovery_error:
            logger.error(f"Failed to send error message in quantity selection: {recovery_error}")

async def show_country_selection_for_user(query, context: ContextTypes.DEFAULT_TYPE, language: str) -> None:
    """عرض اختيار الدولة للمستخدم مع زر إلغاء"""
    try:
        proxy_type = context.user_data.get('proxy_type')
        static_type = context.user_data.get('static_type', '')
        
        if proxy_type == 'socks':
            countries = SOCKS_COUNTRIES.get(language, SOCKS_COUNTRIES['ar'])
        else:
            # للستاتيك، عرض الدول المحددة فقط (بدون أسعار)
            if static_type == 'isp' or static_type == 'virgin_residential':
                # ISP و Virgin Residential: فقط الولايات المتحدة، بدون ولايات
                countries = {
                    'US': STATIC_COUNTRIES[language]['US']
                }
            else:
                # ريزيدنتال: الدول المدعومة فقط
                countries = STATIC_COUNTRIES.get(language, STATIC_COUNTRIES['ar'])
        
        keyboard = []
        for code, name in countries.items():
            keyboard.append([InlineKeyboardButton(name, callback_data=f"country_{code}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            MESSAGES[language]['select_country'],
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in show_country_selection_for_user: {e}")
        
        try:
            # محاولة إرسال رسالة خطأ بسيطة
            await query.message.reply_text(
                "⚠️ حدث خطأ في عرض قائمة الدول. يرجى استخدام /start لإعادة المحاولة.",
                reply_markup=ReplyKeyboardRemove()
            )
        except Exception as recovery_error:
            logger.error(f"Failed to send error message in show_country_selection_for_user: {recovery_error}")


async def handle_cancel_user_proxy_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة إلغاء طلب البروكسي من قبل المستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    is_admin = context.user_data.get('is_admin', False)
    
    # تنظيف البيانات المؤقتة مع الحفاظ على حالة الأدمن
    clean_user_data_preserve_admin(context)
    
    # مسح مسار الأزرار الديناميكية عند الإلغاء
    clear_button_path(user_id)
    
    # رسالة الإلغاء
    if language == 'ar':
        cancel_message = "❌ تم إلغاء طلب البروكسي\n\n🔙 يمكنك البدء من جديد في أي وقت"
    else:
        cancel_message = "❌ Proxy request cancelled\n\n🔙 You can start again anytime"
    
    await query.edit_message_text(cancel_message)
    
    # إعادة الكيبورد المناسب حسب نوع المستخدم
    if is_admin:
        await restore_admin_keyboard(context, user_id, "🔧 لوحة الأدمن جاهزة")
    else:
        # إرسال القائمة الرئيسية للمستخدم العادي (6 أزرار كاملة)
        reply_markup = create_main_user_keyboard(language)
        
        await context.bot.send_message(
            user_id,
            MESSAGES[language]['welcome'],
            reply_markup=reply_markup
        )

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الاستعلامات المرسلة مع حماية من التوقف"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # قائمة الأزرار التي تُعالج في ConversationHandlers - يجب تجاهلها هنا
    conversation_only_buttons = [
        'confirm_broadcast', 'cancel_broadcast',
        'cancel_order_inquiry',
        'cancel_referral_amount', 'cancel_balance_reset', 'cancel_payment_proof',
        'cancel_proxy_setup', 'cancel_user_lookup', 'cancel_password_change',
        'cancel_custom_message',
        # أزرار معالجة الطلبات
        'payment_success', 'payment_failed', 'cancel_processing',
        'quantity_single', 'quantity_package',
        # أزرار أخرى من ConversationHandlers
        'broadcast_all', 'broadcast_custom',
        # أزرار معالجة البروكسي
        'send_custom_message', 'no_custom_message', 'send_proxy_confirm', 'cancel_proxy_send',
        # أزرار أخرى متنوعة
        'quiet_8_18', 'quiet_22_6', 'quiet_12_14', 'quiet_20_22', 'quiet_24h',
        # أزرار البروكسيات المجانية
        'add_free_proxy', 'delete_free_proxy', 'cancel_add_proxy'
    ]
    
    # إذا كان الزر مُعالج في ConversationHandler، لا تتدخل هنا
    if query.data in conversation_only_buttons:
        return
    
    try:
        # التأكد من إجابة الاستعلام أولاً لتجنب تعليق الأزرار
        # استثناء للأزرار التي تعالج الإجابة بنفسها
        if not (query.data.startswith("show_more_") or 
                query.data.startswith("lang_") or 
                query.data.startswith("admin_lang_")):
            await query.answer()
    except Exception as answer_error:
        print(f"⚠️ خطأ في إجابة الاستعلام: {answer_error}")
    
    # فحص حالة الحظر وتتبع النقرات المتكررة
    ban_check_result = await check_user_ban_and_track_clicks(update, context)
    if ban_check_result:
        # المستخدم محظور أو تم تطبيق إجراء - إيقاف المعالجة
        return
    
    # التحقق من حالة تشغيل البوت - إذا كان متوقفاً، تجاهل callbacks المستخدمين العاديين
    is_admin = context.user_data.get('is_admin', False) or user_id in ADMIN_IDS
    if not is_bot_running() and not is_admin:
        language = get_user_language(user_id)
        await query.edit_message_text(
            "⚠️ البوت متوقف حالياً للصيانة. يرجى المحاولة لاحقاً." if language == 'ar' else "⚠️ Bot is currently stopped for maintenance. Please try again later."
        )
        return
    
    try:
        logger.info(f"Processing callback query: {query.data} from user {user_id}")
        
        if query.data.startswith("country_") or query.data.startswith("state_"):
            logger.info(f"Routing to country selection for user {user_id}")
            await handle_country_selection(update, context)
        elif query.data.startswith("payment_"):
            logger.info(f"Routing to payment selection for user {user_id}")
            await handle_payment_method_selection(update, context)
        elif query.data.startswith("recharge_payment_"):
            logger.info(f"Routing to recharge payment selection for user {user_id}")
            await handle_recharge_payment_method_selection(update, context)
        elif query.data.startswith("lang_") or query.data.startswith("admin_lang_"):
            logger.info(f"Routing to language change for user {user_id}")
            await handle_language_change(update, context)
        elif query.data in ["virgin_residential_proxy", "confirm_virgin_residential"]:
            logger.info(f"Routing to premium residential: {query.data} for user {user_id}")
            await handle_user_quantity_selection(update, context)
        elif query.data.startswith("quantity_") or query.data in ["static_daily", "static_weekly", "verizon_weekly", "datacenter_proxy", "residential_4_dollar"] or query.data.startswith("res4_") or query.data.startswith("res6_"):
            logger.info(f"Routing to quantity selection: {query.data} for user {user_id}")
            await handle_user_quantity_selection(update, context)
        elif query.data.startswith("view_pending_order_"):
            logger.info(f"Routing to pending order details for user {user_id}")
            await handle_view_pending_order_details(update, context)
        elif query.data.startswith("direct_process_"):
            logger.info(f"Routing to direct order processing for user {user_id}")
            await handle_direct_process_order(update, context)
        elif query.data == "back_to_pending_orders":
            logger.info(f"Routing back to pending orders for user {user_id}")
            await handle_back_to_pending_orders(update, context)
        elif query.data == "admin_main_menu":
            logger.info(f"Routing to admin main menu for user {user_id}")
            await query.answer()
            await restore_admin_keyboard(context, update.effective_chat.id, "🏠 العودة للقائمة الرئيسية")
        elif query.data.startswith("view_order_"):
            logger.info(f"Routing to order details for user {user_id}")
            await handle_view_order_details(update, context)
        elif query.data == "cancel_user_proxy_request":
            await handle_cancel_user_proxy_request(update, context)
        # تم نقل معالجة process_ إلى process_order_conv_handler
        # تم نقل معالجة payment_success و payment_failed إلى process_order_conv_handler
        # تم نقل معالجة proxy_type_ إلى process_order_conv_handler
        # تم نقل معالجة admin_country_ و admin_state_ إلى process_order_conv_handler
        elif query.data in ["admin_referrals", "user_lookup", "manage_money", "admin_settings", "reset_balance"]:
            await handle_admin_menu_actions(update, context)
        elif query.data == "withdraw_balance":
            await handle_withdrawal_request(update, context)
        # approve_recharge_ تم نقلها إلى recharge_approval_conv_handler
        elif query.data.startswith("reject_recharge_"):
            logger.info(f"Routing to recharge rejection for user {user_id}")
            await handle_reject_recharge(update, context)
        elif query.data.startswith("view_recharge_"):
            logger.info(f"Routing to recharge details for user {user_id}")
            await handle_view_recharge_details(update, context)
        elif query.data.startswith("use_admin_amount_") or query.data.startswith("use_user_amount_") or query.data.startswith("stop_processing_"):
            logger.info(f"Routing to recharge amount choice for user {user_id}")
            await handle_recharge_amount_choice(update, context)
        elif query.data in ["confirm_logout", "cancel_logout"]:
            await handle_logout_confirmation(update, context)
        elif query.data == "back_to_admin":
            await handle_back_to_admin(update, context)
        elif query.data == "show_bot_services":
            await handle_show_bot_services(update, context)
        elif query.data == "show_exchange_rate":
            await handle_show_exchange_rate(update, context)
        elif query.data == "send_proxy_confirm":
            thank_message = context.user_data.get('admin_thank_message', '')
            await send_proxy_to_user(update, context, thank_message)
            
            # إنشاء زر "تم إنهاء الطلب بنجاح"
            keyboard = [[InlineKeyboardButton("✅ تم إنهاء الطلب بنجاح", callback_data="order_completed_success")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "✅ تم إرسال البروكسي للمستخدم بنجاح!",
                reply_markup=reply_markup
            )
        elif query.data == "cancel_proxy_send":
            # إلغاء إرسال البروكسي وتنظيف البيانات
            order_id = context.user_data.get('processing_order_id')
            if order_id:
                # تنظيف البيانات المؤقتة
                admin_keys = [k for k in context.user_data.keys() if k.startswith('admin_')]
                for key in admin_keys:
                    context.user_data.pop(key, None)
                context.user_data.pop('processing_order_id', None)
            
            await query.edit_message_text(
                f"❌ تم إلغاء إرسال البروكسي\n\n🆔 معرف الطلب: {order_id}\n\n📋 الطلب لا يزال في حالة معلق ويمكن معالجته لاحقاً.",
                parse_mode='HTML'
            )
            
            # إعادة تفعيل كيبورد الأدمن الرئيسي
            await restore_admin_keyboard(context, update.effective_chat.id)
        elif query.data == "order_completed_success":
            # تمت معالجة هذا الزر في ConversationHandler - تجاهل هنا
            await query.answer("تم إنهاء الطلب بنجاح!")
        elif query.data == "developer_info":
            # إظهار نافذة منبثقة مع معلومات المطور
            user_id = update.effective_user.id
            language = get_user_language(user_id)
            
            # إنشاء النص بناءً على لغة المستخدم الحالية (مختصر للنافذة المنبثقة)
            if language == 'ar':
                popup_text = """🧑‍💻 معلومات المطور

📦 بوت بيع البروكسي v1.1.1
👨‍💻 طُور بواسطة: Mohamad Zalaf

📱 تليجرام: @MohamadZalaf
📧 MohamadZalaf@outlook.com

© Mohamad Zalaf 2025"""
            else:
                popup_text = """🧑‍💻 Developer Information

📦 Proxy Sales Bot v1.1.1
👨‍💻 Developed by: Mohamad Zalaf

📱 Telegram: @MohamadZalaf
📧 MohamadZalaf@outlook.com

© Mohamad Zalaf 2025"""
            
            try:
                await query.answer(text=popup_text, show_alert=True)
            except Exception as e:
                logger.error(f"Error showing popup: {e}")
                # محاولة بديلة - إرسال رسالة عادية
                await query.message.reply_text(popup_text)
        elif query.data == "manage_proxies":
            # إدارة البروكسيات للأدمن
            await handle_manage_free_proxies(update, context)
        elif query.data == "separator":
            # معالجة الفاصل - عدم القيام بأي شيء
            await query.answer("━━━━━━━━━━━━━━━━━━━━")
        elif query.data == "free_proxy_trial":
            # طلب بروكسي مجاني للمستخدم
            await handle_free_proxy_trial(update, context)
        elif query.data.startswith("use_free_proxy_") or query.data.startswith("get_free_proxy_"):
            # استخدام بروكسي مجاني محدد
            await handle_use_free_proxy(update, context)
        elif query.data == "back_to_manage_proxies":
            # العودة لقائمة إدارة البروكسيات
            await handle_back_to_manage_proxies(update, context)
        elif query.data == "back_to_admin_menu":
            # العودة لقائمة الأدمن الرئيسية
            await handle_back_to_admin_menu(update, context)
        
        # معالجات إعدادات قناة البوت
        elif query.data in ["admin_set_channel", "admin_toggle_forced_sub", "cancel_channel_setup", "back_to_admin_settings"]:
            await handle_channel_settings_callback(update, context)
        
        # التحقق من الاشتراك في القناة
        elif query.data == "verify_channel_subscription":
            user_id = update.effective_user.id
            language = get_user_language(user_id)
            is_subscribed, channel = await check_user_subscription(context.bot, user_id)
            if is_subscribed:
                await query.answer("✅ " + ("تم التحقق بنجاح!" if language == 'ar' else "Verified!"))
                # Show main menu
                reply_markup = create_main_user_keyboard(language)
                await query.message.delete()
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=MESSAGES[language]['welcome'],
                    reply_markup=reply_markup
                )
            else:
                await query.answer("❌ " + ("لم تشترك بعد!" if language == 'ar' else "Not subscribed!"), show_alert=True)
        
        # معالجات إدارة خدمات البروكسي الجديدة
        elif query.data == "manage_services":
            await handle_manage_services(update, context)
        elif query.data == "disable_all_countries":
            await handle_toggle_service(update, context)
        elif query.data == "enable_all_countries":
            await handle_toggle_service(update, context)
        elif query.data == "manage_nonvoip_services":
            await handle_manage_nonvoip_services(update, context)
        elif query.data == "manage_free_proxies_menu":
            await handle_manage_free_proxies_menu(update, context)
        elif query.data == "manage_external_proxies":
            await handle_manage_external_proxies(update, context)
        elif query.data == "manage_nonvoip_admin":
            await handle_manage_nonvoip_admin(update, context)
        elif query.data == "manage_coinex_admin":
            await handle_manage_coinex_admin(update, context)
        elif query.data == "manage_premsocks_admin" or query.data == "manage_luxury_admin":
            await handle_manage_luxury_admin(update, context)
        elif query.data.startswith("lx_admin"):
            await handle_luxury_admin_callbacks(update, context)
        elif query.data.startswith("lx_"):
            await handle_luxury_user_callbacks(update, context)
        elif query.data.startswith("coinex_"):
            await handle_coinex_admin_callbacks(update, context)
        elif query.data.startswith("nva_"):
            # معالجة أزرار إدارة الأرقام للآدمن
            await handle_nonvoip_admin_callbacks(update, context)
        elif query.data.startswith("nv_"):
            # معالجة أزرار شراء الأرقام للمستخدمين
            await handle_nonvoip_user_callbacks(update, context)
        elif query.data == "advanced_service_management":
            await handle_manage_services(update, context)
        elif query.data == "manage_external_proxy":
            await handle_manage_external_proxy(update, context)
        elif query.data.startswith("manage_detailed_static_"):
            await handle_manage_detailed_static(update, context)
        elif query.data.startswith("manage_countries_"):
            await handle_manage_service_countries(update, context)
        elif query.data.startswith("manage_states_"):
            await handle_manage_service_states(update, context)
        elif query.data == "static_services_report":
            await handle_static_services_report(update, context)
        elif (query.data.startswith("toggle_nonvoip_") or
              query.data.startswith("toggle_all_countries_") or
              query.data.startswith("toggle_all_svc_countries_") or
              query.data.startswith("toggle_svc_country_") or
              query.data.startswith("tsc_") or  # اختصار toggle_svc_country
              query.data.startswith("toggle_all_svc_states_") or
              query.data.startswith("toggle_svc_state_") or
              query.data.startswith("tss_")):  # اختصار toggle_svc_state
            await handle_toggle_service(update, context)
        elif query.data.endswith("_disable") or query.data.endswith("_enable"):
            # معالجة أزرار تعطيل/تفعيل الخدمات مثل toggle_socks_disable
            if query.data.startswith("toggle_"):
                await handle_service_toggle(update, context)
            
        elif query.data == "cancel_custom_message":
            # إلغاء إدخال الرسالة المخصصة والعودة لقائمة الأدمن
            clean_user_data_preserve_admin(context)
            await query.edit_message_text("❌ تم إلغاء إدخال الرسالة المخصصة.")
            
            # إعادة تفعيل كيبورد الأدمن الرئيسي
            await restore_admin_keyboard(context, update.effective_chat.id)
            
            return ConversationHandler.END

        elif query.data.startswith("quiet_"):
            await handle_quiet_hours_selection(update, context)
        elif query.data in ["confirm_clear_db", "cancel_clear_db"]:
            await handle_database_clear(update, context)
        elif query.data == "cancel_processing":
            await handle_cancel_processing(update, context)
        
        elif query.data == "cancel_direct_processing":
            await handle_cancel_direct_processing(update, context)
        elif query.data.startswith("withdrawal_success_"):
            await handle_withdrawal_success(update, context)
        elif query.data.startswith("withdrawal_failed_"):
            await handle_withdrawal_failed(update, context)
        elif query.data == "cancel_user_lookup":
            await handle_cancel_user_lookup(update, context)
        elif query.data == "cancel_referral_amount":
            await handle_cancel_referral_amount(update, context)
        elif query.data == "cancel_credit_price":
            await handle_cancel_credit_price(update, context)
        elif query.data == "cancel_order_inquiry":
            await handle_cancel_order_inquiry(update, context)
        elif query.data == "cancel_balance_reset":
            await handle_cancel_balance_reset(update, context)
        elif query.data == "cancel_payment_proof":
            await handle_cancel_payment_proof(update, context)
        elif query.data == "cancel_proxy_setup":
            await handle_cancel_proxy_setup(update, context)
        elif query.data.startswith("show_more_users_"):
            offset = int(query.data.replace("show_more_users_", ""))
            await query.answer()
            await show_user_statistics(update, context, offset)
        elif query.data.startswith("view_order_"):
            await handle_view_order_details(update, context)
        elif query.data.startswith("send_direct_message_"):
            await handle_send_direct_message(update, context)
        elif query.data == "retry_pending_orders":
            # إعادة محاولة تحميل الطلبات المعلقة
            await query.answer("🔄 جاري إعادة المحاولة...")
            await show_pending_orders_admin(update, context)
        elif query.data == "admin_database_menu":
            # انتقال لقائمة إدارة قاعدة البيانات
            await query.answer()
            await database_management_menu(update, context)
        elif query.data == "validate_database":
            # فحص سلامة قاعدة البيانات
            await query.answer("🔍 جاري فحص قاعدة البيانات...")
            await validate_database_status(update, context)
        elif query.data == "back_to_amount":
            await handle_back_to_amount(update, context)
        elif query.data == "back_to_payment_method":
            await handle_back_to_payment_method(update, context)
        elif query.data == "back_to_main_from_recharge":
            await handle_back_to_main_from_recharge(update, context)
        elif query.data == "recharge_balance":
            # معالجة زر شحن الرصيد من تدفق الشراء (عند عدم كفاية الرصيد)
            await handle_recharge_balance_callback(update, context)
        # معالجة أزرار أسعار السوكس الجديدة
        elif query.data in ["set_socks_single", "set_socks_double", "set_socks_package5", "set_socks_package10", "back_to_prices_menu"]:
            logger.info(f"Routing to SOCKS price handler: {query.data} for user {user_id}")
            await handle_socks_price_callback(update, context)
        # معالجة أزرار إدارة المستخدمين الجديدة
        elif query.data == "back_to_admin_menu":
            await query.answer()
            await restore_admin_keyboard(context, update.effective_chat.id, "🔧 تم العودة لقائمة الأدمن")
        elif query.data.startswith("manage_user_"):
            await handle_manage_user(update, context)
        elif query.data.startswith("manage_points_"):
            await handle_manage_points(update, context)
        elif query.data.startswith("broadcast_user_"):
            await handle_broadcast_user(update, context)
        elif query.data.startswith("manage_referrals_"):
            await handle_manage_referrals(update, context)
        elif query.data.startswith("detailed_reports_"):
            await handle_detailed_reports(update, context)
        # معالجة أحداث إدارة المستخدم المتقدمة
        elif query.data.startswith("ban_user_"):
            await handle_ban_user_action(update, context)
        elif query.data.startswith("unban_user_"):
            await handle_unban_user_action(update, context)
        elif query.data.startswith("remove_temp_ban_"):
            await handle_remove_temp_ban_action(update, context)
        elif query.data.startswith("add_points_"):
            await handle_add_points_action(update, context)
        elif query.data.startswith("subtract_points_"):
            await handle_subtract_points_action(update, context)
        elif query.data.startswith("add_referral_"):
            await handle_add_referral_action(update, context)
        elif query.data.startswith("delete_referral_"):
            await handle_delete_referral_action(update, context)
        elif query.data.startswith("reset_referral_balance_"):
            await handle_reset_referral_balance_action(update, context)
        elif query.data.startswith("send_text_"):
            await handle_single_user_broadcast_action(update, context)
        elif query.data.startswith("send_photo_"):
            await handle_single_user_broadcast_photo_action(update, context)
        elif query.data.startswith("quick_message_"):
            await handle_quick_message_action(update, context)
        elif query.data.startswith("important_notice_"):
            await handle_important_notice_action(update, context)
        elif query.data.startswith("back_to_profile_"):
            await handle_back_to_user_profile(update, context)
        # معالجة أحداث التأكيد الجديدة
        elif query.data.startswith("confirm_ban_"):
            await handle_confirm_ban_user(update, context)
        elif query.data.startswith("confirm_unban_"):
            await handle_confirm_unban_user(update, context)
        elif query.data.startswith("confirm_remove_temp_ban_"):
            await handle_confirm_remove_temp_ban(update, context)
        elif query.data.startswith("confirm_reset_referral_balance_"):
            await handle_confirm_reset_referral_balance(update, context)
        elif query.data.startswith("confirm_delete_referral_"):
            await handle_confirm_delete_referral(update, context)
        elif query.data.startswith("quick_template_"):
            await handle_quick_template_selection(update, context)
        # معالجة أزرار التقارير المتقدمة
        elif query.data.startswith("show_referred_"):
            await handle_show_referred_action(update, context)
        elif query.data.startswith("referral_earnings_"):
            await handle_referral_earnings_action(update, context)
        elif query.data.startswith("full_report_"):
            await handle_full_report_action(update, context)
        elif query.data.startswith("financial_report_"):
            await handle_financial_report_action(update, context)
        elif query.data.startswith("orders_report_"):
            await handle_orders_report_action(update, context)
        elif query.data.startswith("referrals_report_"):
            await handle_referrals_report_action(update, context)
        elif query.data.startswith("advanced_stats_"):
            await handle_advanced_stats_action(update, context)
        elif query.data.startswith("timeline_report_"):
            await handle_timeline_report_action(update, context)
        elif query.data.startswith("transaction_history_"):
            await handle_transaction_history_action(update, context)
        elif query.data.startswith("custom_balance_"):
            await handle_custom_balance_action(update, context)
        elif query.data.startswith("reset_stats_"):
            await handle_reset_stats_action(update, context)
        elif query.data.startswith("delete_user_data_"):
            await handle_delete_user_data_action(update, context)
        elif query.data.startswith("confirm_delete_user_"):
            await handle_confirm_delete_user_action(update, context)
        elif query.data.startswith("clear_referrals_"):
            await handle_clear_referrals_action(update, context)
        elif query.data == "noop":
            # معالجة أزرار الترقيم (no operation)
            await query.answer()
        elif query.data.startswith("dyn_") or query.data == "admin_open_miniapp" or query.data == "admin_view_services" or query.data == "admin_manage_prices" or query.data == "admin_export_buttons" or query.data.startswith("manage_services"):
            logger.info(f"Routing to dynamic button handler: {query.data} for user {user_id}")
            handled = await handle_dynamic_button(update, context)
            if not handled:
                logger.warning(f"Dynamic button handler returned False for: {query.data}")
        else:
            # معالجة الأزرار غير المعروفة أو المنتهية الصلاحية
            logger.warning(f"Unknown or expired callback action: {query.data} from user {user_id}")
            
            try:
                await query.answer("⚠️ هذا الزر منتهي الصلاحية أو غير صالح")
            except Exception as answer_error:
                logger.error(f"Failed to answer unknown callback: {answer_error}")
            
            # تنظيف البيانات المؤقتة لتجنب التعليق
            context.user_data.clear()
            
            # التحقق من نوع المستخدم وإعادة توجيهه للقائمة المناسبة
            if user_id in ACTIVE_ADMINS or context.user_data.get('is_admin'):
                # للأدمن - إعادة تفعيل كيبورد الأدمن
                await restore_admin_keyboard(context, update.effective_chat.id, 
                                           "⚠️ تم اكتشاف زر منتهي الصلاحية. عودة للقائمة الرئيسية...")
            else:
                # للمستخدم العادي - العودة للقائمة الرئيسية
                try:
                    await query.message.reply_text(
                        "⚠️ هذا الزر منتهي الصلاحية. تم إعادة توجيهك للقائمة الرئيسية.",
                        reply_markup=ReplyKeyboardRemove()
                    )
                    await start(update, context)
                except Exception as redirect_error:
                    logger.error(f"Failed to redirect user after unknown callback: {redirect_error}")
                    # محاولة أخيرة بسيطة
                    try:
                        await context.bot.send_message(
                            user_id,
                            "يرجى استخدام /start لإعادة تشغيل البوت"
                        )
                    except:
                        pass
            
    except Exception as e:
        logger.error(f"Error in handle_callback_query from user {update.effective_user.id}: {e}")
        print(f"❌ خطأ في معالجة callback query من المستخدم {update.effective_user.id}: {e}")
        print(f"   البيانات: {query.data}")
        
        # محاولة إجابة الاستعلام لتجنب تعليق الأزرار
        try:
            await query.answer("❌ حدث خطأ، جاري إعادة التوجيه...")
        except:
            pass
        
        # إعادة توجيه المستخدم مع تفاصيل الخطأ للآدمن
        try:
            user_id = update.effective_user.id
            if context.user_data.get('is_admin') or user_id in ACTIVE_ADMINS:
                error_details = f"❌ حدث خطأ في معالجة العملية\n\n🔍 التفاصيل التقنية:\n• نوع العملية: {query.data}\n• سبب الخطأ: {str(e)[:200]}...\n\n🔧 تم إعادة توجيهك للقائمة الرئيسية"
                await restore_admin_keyboard(context, update.effective_chat.id, error_details)
            else:
                await start(update, context)
        except Exception as redirect_error:
            logger.error(f"Failed to redirect after callback error: {redirect_error}")
            print(f"❌ فشل في إعادة التوجيه: {redirect_error}")
        
        # تنظيف البيانات المؤقتة في حالة الخطأ
        try:
            clean_user_data_preserve_admin(context)
        except:
            pass

async def handle_admin_country_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار الدولة من قبل الأدمن"""
    query = update.callback_query
    await query.answer()
    
    # معالجة التنقل بين الصفحات
    if query.data.startswith("admin_country_page_"):
        page = int(query.data.replace("admin_country_page_", ""))
        proxy_type = context.user_data.get('admin_proxy_type', 'static')
        countries = SOCKS_COUNTRIES['ar'] if proxy_type == 'socks' else STATIC_COUNTRIES['ar']
        
        reply_markup = create_paginated_keyboard(countries, "admin_country_", page, 8, 'ar')
        await query.edit_message_text("4️⃣ اختر الدولة:", reply_markup=reply_markup)
        return ENTER_COUNTRY
    
    # معالجة التنقل بين صفحات الولايات
    elif query.data.startswith("admin_state_page_"):
        page = int(query.data.replace("admin_state_page_", ""))
        country_code = context.user_data.get('current_country_code', '')
        # لدالة الأدمن، نستخدم المعايير الافتراضية
        proxy_type = context.user_data.get('admin_proxy_type', 'static')
        states = get_states_for_country(country_code, proxy_type, 'residential')
        
        if states:
            reply_markup = create_paginated_keyboard(states['ar'], "admin_state_", page, 8, 'ar')
            await query.edit_message_text("5️⃣ اختر الولاية:", reply_markup=reply_markup)
        return ENTER_STATE
    
    elif query.data == "admin_country_other":
        context.user_data['admin_input_state'] = ENTER_COUNTRY
        await query.edit_message_text("4️⃣ يرجى إدخال اسم الدولة:")
        return ENTER_COUNTRY
    
    elif query.data.startswith("admin_state_"):
        if query.data == "admin_state_other":
            context.user_data['admin_input_state'] = ENTER_STATE
            await query.edit_message_text("5️⃣ يرجى إدخال اسم الولاية:")
            return ENTER_STATE
        else:
            state_code = query.data.replace("admin_state_", "")
            country_code = context.user_data.get('current_country_code', '')
            proxy_type = context.user_data.get('admin_proxy_type', 'static')
            states = get_states_for_country(country_code, proxy_type, 'residential')
            
            if states:
                context.user_data['admin_proxy_state'] = states['ar'].get(state_code, state_code)
            else:
                context.user_data['admin_proxy_state'] = state_code
                
            context.user_data['admin_input_state'] = ENTER_USERNAME
            await query.edit_message_text("6️⃣ يرجى إدخال اسم المستخدم للبروكسي:")
            return ENTER_USERNAME
    
    else:
        country_code = query.data.replace("admin_country_", "")
        context.user_data['current_country_code'] = country_code
        
        # تحديد قائمة الدول المناسبة
        proxy_type = context.user_data.get('admin_proxy_type', 'static')
        if proxy_type == 'socks':
            context.user_data['admin_proxy_country'] = SOCKS_COUNTRIES['ar'].get(country_code, country_code)
        else:
            context.user_data['admin_proxy_country'] = STATIC_COUNTRIES['ar'].get(country_code, country_code)
        
        # عرض قائمة الولايات إذا كانت متوفرة
        proxy_type = context.user_data.get('admin_proxy_type', 'static')
        states = get_states_for_country(country_code, proxy_type, 'residential')
        
        if states:
            reply_markup = create_paginated_keyboard(states['ar'], "admin_state_", 0, 8, 'ar')
            await query.edit_message_text("5️⃣ اختر الولاية:", reply_markup=reply_markup)
            return ENTER_STATE
        else:
            # انتقل مباشرة لاسم المستخدم
            context.user_data['admin_input_state'] = ENTER_USERNAME
            await query.edit_message_text("6️⃣ يرجى إدخال اسم المستخدم للبروكسي:")
            return ENTER_USERNAME

async def handle_withdrawal_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة طلب سحب الرصيد"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    language = get_user_language(user_id)
    
    if user and float(user[5]) >= 1.0:  # الحد الأدنى 1 دولار
        # إنشاء معرف طلب السحب
        withdrawal_id = generate_order_id()
        
        # حفظ طلب السحب في قاعدة البيانات
        db.execute_query(
            "INSERT INTO orders (id, user_id, proxy_type, payment_amount, status) VALUES (?, ?, ?, ?, ?)",
            (withdrawal_id, user_id, 'withdrawal', user[5], 'pending')
        )
        
        if language == 'ar':
            message = f"""💸 تم إرسال طلب سحب الرصيد

💰 المبلغ المطلوب: <code>{user[5]:.2f}$</code>
🆔 معرف الطلب: <code>{withdrawal_id}</code>

تم إرسال طلبك للأدمن وسيتم معالجته في أقرب وقت ممكن."""
        else:
            message = f"""💸 Withdrawal request sent

💰 Amount: <code>{user[5]:.2f}$</code>
🆔 Request ID: <code>{withdrawal_id}</code>

Your request has been sent to admin and will be processed soon."""
        
        # إرسال إشعار طلب السحب للأدمن
        await send_withdrawal_notification(context, withdrawal_id, user)
        
        await query.edit_message_text(message, parse_mode='HTML')
    else:
        min_amount = 1.0
        current_balance = float(user[5]) if user else 0.0
        
        if language == 'ar':
            message = f"""❌ رصيد غير كافٍ للسحب

💰 رصيدك الحالي: <code>{current_balance:.2f}$</code>
📊 الحد الأدنى للسحب: <code>{min_amount:.1f}$</code>

يرجى دعوة المزيد من الأصدقاء لزيادة رصيدك!"""
        else:
            message = f"""❌ Insufficient balance for withdrawal

💰 Current balance: <code>{current_balance:.2f}$</code>
📊 Minimum withdrawal: <code>{min_amount:.1f}$</code>

Please invite more friends to increase your balance!"""
        
        await query.edit_message_text(message, parse_mode='HTML')

async def handle_custom_message_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار إرسال رسالة مخصصة"""
    query = update.callback_query
    await query.answer()
    
    order_id = context.user_data['processing_order_id']
    
    # التحقق من نوع الطلب (فشل أو نجاح)
    if query.data == "send_custom_message_failed":
        # تدفق الفشل - إرسال رسالة مخصصة بعد الرفض
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_custom_message")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("يرجى إدخال الرسالة المخصصة للمستخدم:", reply_markup=reply_markup)
        return CUSTOM_MESSAGE
        
    elif query.data == "no_custom_message_failed":
        # تدفق الفشل - عدم إرسال رسالة مخصصة
        # تنظيف البيانات المؤقتة
        context.user_data.pop('processing_order_id', None)
        context.user_data.pop('admin_processing_active', None)
        context.user_data.pop('waiting_for_admin_message', None)
        context.user_data.pop('direct_processing', None)
        context.user_data.pop('custom_mode', None)
        
        await query.edit_message_text(f"✅ تم رفض الطلب وإشعار المستخدم.\nمعرف الطلب: {order_id}")
        
        # إعادة تفعيل كيبورد الأدمن الرئيسي
        await restore_admin_keyboard(context, update.effective_chat.id)
        
        return ConversationHandler.END
    
    elif query.data == "send_custom_message":
        # كود قديم للتوافق (إذا كان موجوداً)
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_custom_message")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("يرجى إدخال الرسالة المخصصة للمستخدم:", reply_markup=reply_markup)
        return CUSTOM_MESSAGE
    else:
        # عدم إرسال رسالة مخصصة
        user_query = "SELECT user_id FROM orders WHERE id = ?"
        user_result = db.execute_query(user_query, (order_id,))
        
        if user_result:
            user_id = user_result[0][0]
            user_language = get_user_language(user_id)
            
            # إرسال رسالة فشل العملية مع معلومات الدعم
            failure_message = {
                'ar': f"""❌ تم رفض طلبك رقم <code>{order_id}</code>

إن كان لديك استفسار، يرجى التواصل مع الدعم:
@Static_support""",
                'en': f"""❌ Your order <code>{order_id}</code> has been rejected

If you have any questions, please contact support:
@Static_support"""
            }
            
            await context.bot.send_message(
                user_id,
                failure_message[user_language],
                parse_mode='HTML'
            )
        
        # جدولة حذف الطلب بعد 48 ساعة
        await schedule_order_deletion(context, order_id, user_id if user_result else None)
        
        # تنظيف البيانات المؤقتة مع الحفاظ على حالة الأدمن
        clean_user_data_preserve_admin(context)
        
        await query.edit_message_text(f"✅ تم إشعار المستخدم برفض الطلب.\nمعرف الطلب: {order_id}\n\n⏰ سيتم حذف الطلب تلقائياً بعد 48 ساعة")
        
        # إعادة تفعيل كيبورد الأدمن الرئيسي
        await restore_admin_keyboard(context, update.effective_chat.id)
        
        return ConversationHandler.END

async def handle_custom_message_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إدخال الرسالة المخصصة"""
    custom_message = update.message.text
    order_id = context.user_data.get('processing_order_id')
    
    if not order_id:
        await update.message.reply_text("❌ حدث خطأ في معرف الطلب")
        await restore_admin_keyboard(context, update.effective_chat.id)
        return ConversationHandler.END
    
    # حارس لمنع التداخل: التحقق من وضع الرسالة المخصصة
    custom_mode = context.user_data.get('custom_mode', 'success')
    
    # إذا كان الوضع "فشل" - معالجة رسالة مخصصة بعد الرفض
    if custom_mode == 'failed':
        # تدفق الفشل: إرسال الرسالة المخصصة فقط بدون خصم رصيد أو إتمام طلب
        user_query = "SELECT user_id FROM orders WHERE id = ?"
        user_result = db.execute_query(user_query, (order_id,))
        
        if user_result:
            user_id = user_result[0][0]
            
            # إرسال الرسالة المخصصة للمستخدم فقط
            admin_message_template = f"""📩 لديك رسالة من الأدمن

"{custom_message}"

━━━━━━━━━━━━━━━━━"""
            
            await context.bot.send_message(user_id, admin_message_template)
        
        # تنظيف البيانات المؤقتة
        context.user_data.pop('processing_order_id', None)
        context.user_data.pop('admin_processing_active', None)
        context.user_data.pop('waiting_for_admin_message', None)
        context.user_data.pop('direct_processing', None)
        context.user_data.pop('custom_mode', None)
        
        await update.message.reply_text(
            f"✅ تم إرسال الرسالة المخصصة للمستخدم.\nمعرف الطلب: {order_id}"
        )
        
        # إعادة تفعيل كيبورد الأدمن الرئيسي
        await restore_admin_keyboard(context, update.effective_chat.id)
        return ConversationHandler.END
    
    # تدفق النجاح: معالجة عادية
    # التحقق من أن هذا تدفق البروكسي الجديد (مباشرة بدون أزرار الكمية)
    if context.user_data.get('waiting_for_admin_message', False):
        # التدفق الجديد: إرسال البروكسي مع الرسالة المخصصة
        await send_proxy_with_custom_message(update, context, custom_message)
        return ConversationHandler.END
    else:
        # التدفق القديم: إرسال رسالة فشل
        user_query = "SELECT user_id FROM orders WHERE id = ?"
        user_result = db.execute_query(user_query, (order_id,))
        
        if user_result:
            user_id = user_result[0][0]
            user_language = get_user_language(user_id)
            
            # إرسال الرسالة المخصصة في قالب جاهز
            admin_message_template = f"""📩 لديك رسالة من الأدمن

"{custom_message}"

━━━━━━━━━━━━━━━━━"""
            
            await context.bot.send_message(user_id, admin_message_template)
            
            # إرسال رسالة فشل العملية
            failure_message = {
                'ar': f"""❌ تم رفض طلبك رقم <code>{order_id}</code>

إن كان لديك استفسار، يرجى التواصل مع الدعم:
@Static_support""",
                'en': f"""❌ Your order <code>{order_id}</code> has been rejected

If you have any questions, please contact support:
@Static_support"""
            }
            
            await context.bot.send_message(
                user_id,
                failure_message[user_language],
                parse_mode='HTML'
            )
            
            # جدولة حذف الطلب بعد 48 ساعة
            await schedule_order_deletion(context, order_id, user_id)
        
        # تنظيف البيانات المؤقتة مع الحفاظ على حالة الأدمن
        clean_user_data_preserve_admin(context)
        
        await update.message.reply_text(
            f"✅ تم إرسال الرسالة المخصصة ورسالة فشل العملية للمستخدم.\nمعرف الطلب: {order_id}\n\n⏰ سيتم حذف الطلب تلقائياً بعد 48 ساعة"
        )
        
        # إعادة تفعيل كيبورد الأدمن الرئيسي
        await restore_admin_keyboard(context, update.effective_chat.id)
        return ConversationHandler.END

async def send_proxy_with_custom_message(update: Update, context: ContextTypes.DEFAULT_TYPE, custom_message: str) -> None:
    """إرسال البروكسي مع الرسالة المخصصة مباشرة"""
    order_id = context.user_data['processing_order_id']
    
    # الحصول على معلومات المستخدم والطلب
    user_query = """
        SELECT o.user_id, u.first_name, u.last_name 
        FROM orders o 
        JOIN users u ON o.user_id = u.user_id 
        WHERE o.id = ?
    """
    user_result = db.execute_query(user_query, (order_id,))
    
    if user_result:
        user_id, first_name, last_name = user_result[0]
        user_full_name = f"{first_name} {last_name or ''}".strip()
        
        # معلومات البروكسي ستأتي من رسالة الأدمن المخصصة
        
        # الحصول على التاريخ والوقت الحاليين
        from datetime import datetime
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")
        
        # الحصول على لغة المستخدم وإنشاء رسالة البروكسي
        user_language = get_user_language(user_id)
        
        if user_language == 'ar':
            proxy_message = f"""✅ تم معالجة طلب {user_full_name}

🔐 تفاصيل البروكسي:
{custom_message}

━━━━━━━━━━━━━━━
🆔 معرف الطلب: {order_id}
📅 التاريخ: {current_date}
🕐 الوقت: {current_time}

━━━━━━━━━━━━━━━
✅ تم إنجاز طلبك بنجاح!"""
        else:
            proxy_message = f"""✅ Order processed for {user_full_name}

🔐 Proxy Details:
{custom_message}

━━━━━━━━━━━━━━━
🆔 Order ID: {order_id}
📅 Date: {current_date}
🕐 Time: {current_time}

━━━━━━━━━━━━━━━
✅ Your order has been completed successfully!"""
        
        # اقتطاع الرصيد من المستخدم عند إرسال البروكسي (هذا هو التوقيت الصحيح)
        order_query = "SELECT user_id, payment_amount, proxy_type FROM orders WHERE id = ?"
        order_result = db.execute_query(order_query, (order_id,))
        
        if order_result:
            order_user_id, payment_amount, proxy_type = order_result[0]
            
            # اقتطاع الرصيد (مع السماح بالرصيد السالب لمنع التحايل)
            try:
                db.deduct_credits(
                    order_user_id, 
                    payment_amount, 
                    'proxy_purchase', 
                    order_id, 
                    f"شراء بروكسي {proxy_type}",
                    allow_negative=True  # السماح بالرصيد السالب
                )
                logger.info(f"تم اقتطاع {payment_amount} نقطة من المستخدم {order_user_id} للطلب {order_id}")
            except Exception as deduct_error:
                logger.error(f"Error deducting points for order {order_id}: {deduct_error}")
        
        # إرسال البروكسي للمستخدم
        await context.bot.send_message(user_id, proxy_message, parse_mode='HTML')
        
        # تحديث حالة الطلب
        proxy_details = {
            'admin_message': custom_message,
            'processed_date': current_date,
            'processed_time': current_time
        }
        
        # تسجيل الطلب كمكتمل ومعالج فعلياً
        db.execute_query(
            "UPDATE orders SET status = 'completed', processed_at = CURRENT_TIMESTAMP, proxy_details = ?, truly_processed = TRUE WHERE id = ?",
            (json.dumps(proxy_details), order_id)
        )
        
        # التحقق من إضافة رصيد الإحالة لأول عملية شراء
        await check_and_add_referral_bonus(context, user_id, order_id)
        
        # رسالة تأكيد للأدمن
        admin_message = f"""✅ تم معالجة الطلب وإرسال البروكسي بنجاح!

🆔 معرف الطلب: {order_id}
👤 المستخدم: {user_full_name}

🔐 تفاصيل البروكسي المرسلة:
{custom_message}

━━━━━━━━━━━━━━━
✅ تم إنهاء معالجة الطلب بنجاح"""

        await update.message.reply_text(admin_message, parse_mode='HTML')
        
        # تنظيف البيانات المؤقتة
        clean_user_data_preserve_admin(context)
        
        # إعادة تفعيل كيبورد الأدمن الرئيسي
        await restore_admin_keyboard(context, update.effective_chat.id)

async def handle_admin_message_for_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة رسالة الأدمن التي تحتوي على معلومات البروكسي"""
    # التحقق من أن هناك طلب قيد المعالجة وانتظار رسالة
    if not context.user_data.get('processing_order_id') or not context.user_data.get('waiting_for_admin_message'):
        # في حالة فقدان السياق، محاولة الحصول على معرف الطلب من custom message input
        if context.user_data.get('processing_order_id'):
            custom_message = update.message.text
            await send_proxy_with_custom_message(update, context, custom_message)
            return ConversationHandler.END
        else:
            await update.message.reply_text("❌ لا يوجد طلب قيد المعالجة حالياً")
            await restore_admin_keyboard(context, update.effective_chat.id)
            return ConversationHandler.END
    
    custom_message = update.message.text
    order_id = context.user_data['processing_order_id']
    
    try:
        # استدعاء دالة إرسال البروكسي مع الرسالة المخصصة
        await send_proxy_with_custom_message(update, context, custom_message)
        
        # رسالة تأكيد للأدمن
        await update.message.reply_text(
            f"✅ تم إرسال البروكسي والرسالة للمستخدم بنجاح!\n\n🆔 معرف الطلب: {order_id}",
            parse_mode='HTML'
        )
        
        # إعادة تفعيل كيبورد الأدمن
        await restore_admin_keyboard(context, update.effective_chat.id)
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"خطأ في إرسال البروكسي: {e}")
        await update.message.reply_text(
            f"❌ حدث خطأ أثناء إرسال البروكسي\n\nالخطأ: {str(e)}"
        )
        return PROCESS_ORDER

async def schedule_order_deletion(context: ContextTypes.DEFAULT_TYPE, order_id: str, user_id: int = None) -> None:
    """جدولة حذف الطلب بعد 48 ساعة"""
    import asyncio
    
    async def delete_after_48_hours():
        # انتظار 48 ساعة (48 * 60 * 60 ثانية)
        await asyncio.sleep(48 * 60 * 60)
        
        try:
            # حذف الطلب من قاعدة البيانات
            db.execute_query("DELETE FROM orders WHERE id = ? AND status = 'failed'", (order_id,))
            
            # إشعار المستخدم بانتهاء صلاحية الطلب
            if user_id:
                user_language = get_user_language(user_id)
                failure_message = {
                    'ar': f"⏰ انتهت صلاحية الطلب <code>{order_id}</code> وتم حذفه من النظام.\n\n💡 يمكنك إنشاء طلب جديد في أي وقت.",
                    'en': f"⏰ Order <code>{order_id}</code> has expired and been deleted from the system.\n\n💡 You can create a new order anytime."
                }
                
                await context.bot.send_message(
                    user_id,
                    failure_message[user_language],
                    parse_mode='HTML'
                )
        except Exception as e:
            logger.error(f"Error deleting expired order {order_id}: {e}")
    
    # تشغيل المهمة في الخلفية
    context.application.create_task(delete_after_48_hours())

# إضافة المزيد من الوظائف المساعدة
async def add_referral_bonus(user_id: int, referred_user_id: int) -> None:
    """إضافة مكافأة الإحالة"""
    # الحصول على قيمة الإحالة من الإعدادات
    referral_amount_query = "SELECT value FROM settings WHERE key = 'referral_amount'"
    result = db.execute_query(referral_amount_query)
    referral_amount = float(result[0][0]) if result else 0.1
    
    # إضافة الإحالة
    db.execute_query(
        "INSERT INTO referrals (referrer_id, referred_id, amount) VALUES (?, ?, ?)",
        (user_id, referred_user_id, referral_amount)
    )

async def activate_referral_bonus_on_success(context, user_id: int) -> None:
    """تفعيل مكافأة الإحالة عند أول عملية شراء ناجحة"""
    # البحث عن إحالة غير مفعلة لهذا المستخدم
    query = """
        SELECT r.id, r.referrer_id, r.amount 
        FROM referrals r
        WHERE r.referred_id = ? 
        AND NOT EXISTS (
            SELECT 1 FROM orders o 
            WHERE o.user_id = r.referred_id 
            AND o.status = 'completed' 
            AND o.truly_processed = TRUE 
            AND o.created_at < (SELECT created_at FROM orders WHERE user_id = ? AND status = 'completed' AND truly_processed = TRUE ORDER BY created_at DESC LIMIT 1)
        )
        LIMIT 1
    """
    result = db.execute_query(query, (user_id, user_id))
    
    if result:
        referral_id, referrer_id, amount = result[0]
        
        # إضافة الرصيد للمحيل
        db.execute_query(
    #             "UPDATE users SET referral_balance = referral_balance + ? WHERE user_id = ?",
            (amount, referrer_id)
        )
        
        # إشعار المحيل
        try:
            await context.bot.send_message(
                referrer_id,
                parse_mode='HTML'
            )
        except:
            pass

    
    # تأجيل إضافة الرصيد حتى أول عملية شراء ناجحة
    db.execute_query(
    #         "UPDATE users SET referral_balance = referral_balance + ? WHERE user_id = ?",
    #         (referral_amount, user_id)
    )

async def cleanup_old_orders() -> None:
    """تنظيف الطلبات القديمة (48 ساعة)"""
    # حذف الطلبات الفاشلة القديمة (بعد 48 ساعة كما هو مطلوب في المواصفات)
    deleted_failed = db.execute_query("""
        DELETE FROM orders 
        WHERE status = 'failed' 
        AND created_at < datetime('now', '-48 hours')
    """)
    
    # تسجيل عدد الطلبات المحذوفة
    if deleted_failed:
        print(f"تم حذف {len(deleted_failed)} طلب فاشل قديم")
    
    # يمكن الاحتفاظ بالطلبات المكتملة للإحصائيات (لا نحذفها)



def create_requirements_file():
    """إنشاء ملف requirements.txt"""
    requirements = """python-telegram-bot==20.7
pandas>=1.3.0
openpyxl>=3.0.0"""
    
    with open("requirements.txt", "w", encoding="utf-8") as f:
        f.write(requirements)

async def export_database_excel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تصدير قاعدة البيانات إلى Excel"""
    try:
        # قراءة البيانات من قاعدة البيانات
        conn = sqlite3.connect(DATABASE_FILE)
        
        # إنشاء ملف Excel مع عدة أوراق
        with pd.ExcelWriter('database_export.xlsx', engine='openpyxl') as writer:
            # جدول المستخدمين
            users_df = pd.read_sql_query("SELECT * FROM users", conn)
            users_df.to_excel(writer, sheet_name='Users', index=False)
            
            # جدول الطلبات
            orders_df = pd.read_sql_query("SELECT * FROM orders", conn)
            orders_df.to_excel(writer, sheet_name='Orders', index=False)
            
            # جدول الإحالات
            referrals_df = pd.read_sql_query("SELECT * FROM referrals", conn)
            referrals_df.to_excel(writer, sheet_name='Referrals', index=False)
            
            # جدول السجلات
            logs_df = pd.read_sql_query("SELECT * FROM logs", conn)
            logs_df.to_excel(writer, sheet_name='Logs', index=False)
        
        conn.close()
        
        # إرسال الملف
        with open('database_export.xlsx', 'rb') as file:
            await update.message.reply_document(
                document=file,
                filename=f"database_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                caption="📊 تم تصدير قاعدة البيانات بصيغة Excel"
            )
        
        # حذف الملف المؤقت
        os.remove('database_export.xlsx')
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ في تصدير Excel: {str(e)}")

async def export_database_csv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تصدير قاعدة البيانات إلى CSV"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        
        # تصدير جدول المستخدمين
        users_df = pd.read_sql_query("SELECT * FROM users", conn)
        users_df.to_csv('users_export.csv', index=False, encoding='utf-8-sig')
        
        # تصدير جدول الطلبات
        orders_df = pd.read_sql_query("SELECT * FROM orders", conn)
        orders_df.to_csv('orders_export.csv', index=False, encoding='utf-8-sig')
        
        conn.close()
        
        # إرسال الملفات
        with open('users_export.csv', 'rb') as file:
            await update.message.reply_document(
                document=file,
                filename=f"users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                caption="👥 بيانات المستخدمين - CSV"
            )
        
        with open('orders_export.csv', 'rb') as file:
            await update.message.reply_document(
                document=file,
                filename=f"orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                caption="📋 بيانات الطلبات - CSV"
            )
        
        # حذف الملفات المؤقتة
        os.remove('users_export.csv')
        os.remove('orders_export.csv')
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ في تصدير CSV: {str(e)}")

async def export_database_sqlite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تصدير ملف قاعدة البيانات الأصلي"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"proxy_bot_backup_{timestamp}.db"
        
        # نسخ ملف قاعدة البيانات
        import shutil
        shutil.copy2(DATABASE_FILE, backup_filename)
        
        # إرسال الملف
        with open(backup_filename, 'rb') as file:
            await update.message.reply_document(
                document=file,
                filename=backup_filename,
                caption="🗃️ نسخة احتياطية من قاعدة البيانات - SQLite"
            )
        
        # حذف الملف المؤقت
        os.remove(backup_filename)
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ في تصدير قاعدة البيانات: {str(e)}")

async def export_database_json_mix(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تصدير قاعدة البيانات إلى JSON مع لاحقة .mix"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        
        # قراءة جميع الجداول وتحويلها إلى JSON
        database_data = {}
        
        # جدول المستخدمين
        users_df = pd.read_sql_query("SELECT * FROM users", conn)
        database_data['users'] = users_df.to_dict('records')
        
        # جدول الطلبات
        orders_df = pd.read_sql_query("SELECT * FROM orders", conn)
        database_data['orders'] = orders_df.to_dict('records')
        
        # جدول الإحالات
        referrals_df = pd.read_sql_query("SELECT * FROM referrals", conn)
        database_data['referrals'] = referrals_df.to_dict('records')
        
        # جدول السجلات
        logs_df = pd.read_sql_query("SELECT * FROM logs", conn)
        database_data['logs'] = logs_df.to_dict('records')
        
        conn.close()
        
        # إنشاء اسم الملف بلاحقة .mix
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"database_export_{timestamp}.mix"
        
        # كتابة البيانات إلى ملف JSON
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(database_data, file, ensure_ascii=False, indent=2, default=str)
        
        # إرسال الملف
        with open(filename, 'rb') as file:
            await update.message.reply_document(
                document=file,
                filename=filename,
                caption="🔧 تم التصدير بصيغة mix"
            )
        
        # حذف الملف المؤقت
        os.remove(filename)
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ في تصدير JSON: {str(e)}")

def create_readme_file():
    """إنشاء ملف README.md"""
    readme_content = """# بوت بيع البروكسيات - Proxy Sales Bot

## تثبيت المتطلبات

```bash
pip install -r requirements.txt
```

## إعداد البوت

1. احصل على TOKEN من BotFather على تيليجرام
2. ضع التوكن في متغير TOKEN في الكود
3. قم بتشغيل البوت:

```bash
python simpl_bot.py
```

## الميزات

- طلب البروكسيات (Static/Socks)
- نظام دفع متعدد الطرق
- إدارة أدمن متكاملة
- نظام إحالات
- دعم اللغتين العربية والإنجليزية
- قاعدة بيانات SQLite محلية

## أوامر الأدمن

- <code>/admin_login</code> - تسجيل دخول الأدمن
- كلمة المرور: <code>sohilSOHIL</code>

## البنية

- <code>simpl_bot.py</code> - الملف الرئيسي للبوت
- <code>proxy_bot.db</code> - قاعدة البيانات (تُنشأ تلقائياً)
- <code>requirements.txt</code> - متطلبات Python
"""
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)

async def handle_process_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة الطلب من قبل الأدمن"""
    query = update.callback_query
    await query.answer()
    
    # التحقق من وجود طلب قيد المعالجة (إنهاء الطلب السابق تلقائياً)
    current_processing_order = context.user_data.get('processing_order_id')
    if current_processing_order:
        # تنظيف الطلب السابق تلقائياً
        try:
            # إعادة الطلب السابق إلى حالة pending إذا لم يكتمل
            db.execute_query(
                "UPDATE orders SET status = 'pending' WHERE id = ? AND status != 'completed'",
                (current_processing_order,)
            )
            
            # تنظيف البيانات المؤقتة للطلب السابق
            context.user_data.pop('waiting_for_direct_admin_message', None)
            context.user_data.pop('waiting_for_admin_message', None)
            context.user_data.pop('direct_processing', None)
            
            await query.answer(f"تم إنهاء الطلب السابق {current_processing_order[:8]}... تلقائياً", show_alert=False)
        except Exception as e:
            print(f"خطأ في تنظيف الطلب السابق: {e}")
    
    order_id = query.data.replace("process_", "")
    
    # التحقق من وجود الطلب - قد يكون الزبون ألغاه
    order_check = db.execute_query("SELECT id, status FROM orders WHERE id = ?", (order_id,))
    if not order_check:
        await query.edit_message_text(
            f"❌ <b>تم إلغاء هذا الطلب</b>\n\n"
            f"🆔 معرف الطلب: <code>{order_id}</code>\n\n"
            f"⚠️ تم إلغاء هذا الطلب من قبل الزبون.",
            parse_mode='HTML'
        )
        return ConversationHandler.END
    
    # التحقق من حالة الطلب - قد يكون ملغى أو مكتمل
    order_status = order_check[0][1]
    if order_status == 'cancelled':
        await query.edit_message_text(
            f"❌ <b>تم إلغاء هذا الطلب</b>\n\n"
            f"🆔 معرف الطلب: <code>{order_id}</code>\n\n"
            f"⚠️ تم إلغاء هذا الطلب من قبل الزبون.",
            parse_mode='HTML'
        )
        return ConversationHandler.END
    elif order_status == 'completed':
        await query.edit_message_text(
            f"✅ <b>تم معالجة هذا الطلب مسبقاً</b>\n\n"
            f"🆔 معرف الطلب: <code>{order_id}</code>",
            parse_mode='HTML'
        )
        return ConversationHandler.END
    
    # تسجيل بداية معالجة طلب جديد
    context.user_data['processing_order_id'] = order_id
    context.user_data['admin_processing_active'] = True
    
    keyboard = [
        [InlineKeyboardButton("نعم", callback_data="payment_success")],
        [InlineKeyboardButton("رفض", callback_data="payment_failed")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="cancel_processing")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # حفظ الرسالة الأصلية قبل التعديل
    context.user_data['original_order_message'] = query.message.text
    
    await query.edit_message_text(
        f"🔄 <b>بدء معالجة الطلب</b>\n\n"
        f"🆔 معرف الطلب: {order_id}\n\n"
        f"✅ <b>المتابعة مع معالجة الطلب:</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    return PROCESS_ORDER

async def handle_direct_process_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الطلب مباشرة بدون سؤال التحقق من الدفع"""
    try:
        query = update.callback_query
        await query.answer()
        
        # التحقق من وجود طلب قيد المعالجة (إنهاء الطلب السابق تلقائياً)
        current_processing_order = context.user_data.get('processing_order_id')
        if current_processing_order:
            # تنظيف الطلب السابق تلقائياً
            try:
                # إعادة الطلب السابق إلى حالة pending إذا لم يكتمل
                db.execute_query(
                    "UPDATE orders SET status = 'pending' WHERE id = ? AND status != 'completed'",
                    (current_processing_order,)
                )
                
                # تنظيف البيانات المؤقتة للطلب السابق
                context.user_data.pop('waiting_for_direct_admin_message', None)
                context.user_data.pop('waiting_for_admin_message', None)
                context.user_data.pop('direct_processing', None)
                context.user_data.pop('admin_processing_active', None)
                
                logger.info(f"تم تنظيف الطلب السابق {current_processing_order} تلقائياً لبدء طلب جديد")
            except Exception as e:
                logger.error(f"خطأ في تنظيف الطلب السابق: {e}")
                
            # إشعار بسيط للأدمن (اختياري)
            await query.answer(f"تم إنهاء الطلب السابق {current_processing_order[:8]}... تلقائياً", show_alert=False)
        
        order_id = query.data.replace("direct_process_", "")
        
        # التحقق من صحة معرف الطلب
        if not order_id:
            await query.edit_message_text("❌ خطأ: معرف الطلب غير صحيح")
            await restore_admin_keyboard(context, update.effective_chat.id)
            return
        
        # التحقق من وجود الطلب في قاعدة البيانات - قد يكون الزبون ألغاه
        order_check = db.execute_query("SELECT id, status FROM orders WHERE id = ?", (order_id,))
        if not order_check:
            await query.edit_message_text(
                f"❌ <b>تم إلغاء هذا الطلب</b>\n\n"
                f"🆔 معرف الطلب: <code>{order_id}</code>\n\n"
                f"⚠️ تم إلغاء هذا الطلب من قبل الزبون.",
                parse_mode='HTML'
            )
            await restore_admin_keyboard(context, update.effective_chat.id)
            return
        
        # التحقق من حالة الطلب - قد يكون ملغى أو مكتمل
        order_status = order_check[0][1]
        if order_status == 'cancelled':
            await query.edit_message_text(
                f"❌ <b>تم إلغاء هذا الطلب</b>\n\n"
                f"🆔 معرف الطلب: <code>{order_id}</code>\n\n"
                f"⚠️ تم إلغاء هذا الطلب من قبل الزبون.",
                parse_mode='HTML'
            )
            await restore_admin_keyboard(context, update.effective_chat.id)
            return
        elif order_status == 'completed':
            await query.edit_message_text(
                f"✅ <b>تم معالجة هذا الطلب مسبقاً</b>\n\n"
                f"🆔 معرف الطلب: <code>{order_id}</code>",
                parse_mode='HTML'
            )
            await restore_admin_keyboard(context, update.effective_chat.id)
            return
        
        # تسجيل بداية معالجة طلب جديد
        context.user_data['processing_order_id'] = order_id
        context.user_data['admin_processing_active'] = True
        context.user_data['direct_processing'] = True  # علامة للمعالجة المباشرة
        
        # حفظ الرسالة الأصلية قبل التعديل
        context.user_data['original_order_message'] = query.message.text
        
        # معالجة مباشرة للطلب بدون conversation handler
        await handle_direct_payment_success(update, context)
        
    except Exception as e:
        logger.error(f"خطأ في handle_direct_process_order: {e}")
        try:
            error_details = f"❌ حدث خطأ في معالجة الطلب مباشرة\n\n🔍 التفاصيل التقنية:\n• معرف الطلب: {query.data.replace('direct_process_', '') if hasattr(query, 'data') else 'غير معروف'}\n• سبب الخطأ: {str(e)[:200]}...\n\n🔧 تم إعادة توجيهك للقائمة الرئيسية"
            await restore_admin_keyboard(context, update.effective_chat.id, error_details)
        except Exception as fallback_error:
            logger.error(f"خطأ في fallback لـ handle_direct_process_order: {fallback_error}")
            await restore_admin_keyboard(context, update.effective_chat.id)

async def handle_direct_payment_success(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة نجاح الدفع للمعالجة المباشرة (بدون conversation handler)"""
    query = update.callback_query
    
    order_id = context.user_data['processing_order_id']
    
    # توليد رقم المعاملة وحفظها (بدون تحديث حالة الطلب)
    transaction_number = generate_transaction_number('proxy')
    save_transaction(order_id, transaction_number, 'proxy', 'completed')
    
    # إرسال رسالة للمستخدم أن الطلب قيد المعالجة
    order_query = "SELECT user_id, proxy_type, payment_amount FROM orders WHERE id = ?"
    order_result = db.execute_query(order_query, (order_id,))
    if order_result:
        user_id = order_result[0][0]
        order_type = order_result[0][1]
        payment_amount = order_result[0][2] if len(order_result[0]) > 2 else 0.0
        user_language = get_user_language(user_id)
        
        # التحقق من كفاية الرصيد قبل خصم النقاط
        try:
            user_balance = db.get_user_balance(user_id)
            available_points = user_balance['charged_balance']
            
            if available_points < payment_amount:
                # رصيد غير كافي - تصنيف الطلب كفاشل
                db.execute_query("UPDATE orders SET status = 'failed' WHERE id = ?", (order_id,))
                
                # إشعار للمستخدم بالرفض
                if user_language == 'ar':
                    failure_message = f"""⚠️ مشكلة في خصم النقاط!

🆔 معرف الطلب: {order_id}
👤 معرف المستخدم: {user_id}
💰 النقاط المطلوبة: {payment_amount:.2f}
❌ السبب: رصيد غير كافي

الرجاء مراجعة الطلب."""
                else:
                    failure_message = f"""❌ Insufficient points balance!

💰 Points required: {payment_amount:.2f} points
🆔 Order ID: {order_id}

📞 Please recharge your balance or contact admin."""
                
                await context.bot.send_message(user_id, failure_message, parse_mode='HTML')
                
                # إشعار للأدمن
                admin_message = f"⚠️ مشكلة في خصم النقاط!\n\n🆔 معرف الطلب: {order_id}\n👤 معرف المستخدم: {user_id}\n💰 النقاط المطلوبة: {payment_amount:.2f}\n❌ السبب: رصيد غير كافي\n\nالرجاء مراجعة الطلب."
                await query.edit_message_text(admin_message, parse_mode='HTML')
                return
                
            # خصم النقاط من رصيد المستخدم
            db.deduct_credits(user_id, payment_amount, 'purchase', order_id, f"شراء {order_type}")
            logger.info(f"تم خصم {payment_amount} نقطة من المستخدم {user_id} للطلب {order_id}")
            
        except Exception as deduction_error:
            # خطأ في خصم النقاط - تصنيف الطلب كفاشل
            logger.error(f"خطأ في خصم النقاط للطلب {order_id}: {deduction_error}")
            db.execute_query("UPDATE orders SET status = 'failed' WHERE id = ?", (order_id,))
            
            # إشعار للأدمن
            admin_error_message = f"❌ خطأ في خصم النقاط!\n\n🆔 معرف الطلب: {order_id}\n👤 معرف المستخدم: {user_id}\n💰 النقاط المطلوبة: {payment_amount:.2f}\n🚫 خطأ: {str(deduction_error)}\n\nتم تصنيف الطلب كفاشل."
            await query.edit_message_text(admin_error_message, parse_mode='HTML')
            return
        
        # رسالة للمستخدم مع رقم المعاملة
        if user_language == 'ar':
            user_message = f"""✅ تم قبول معاملتك بنجاح!

🆔 معرف الطلب: {order_id}
💳 رقم المعاملة: <code>{transaction_number}</code>
📦 نوع الباكج: {order_type}
💰 قيمة الطلب: <code>{payment_amount}$</code>

🔄 سيتم معالجة طلبك وإرسال البيانات قريباً.
💎 سيتم خصم الكريديت عند إرسال بيانات البروكسي"""
        else:
            user_message = f"""✅ Your transaction has been accepted successfully!

🆔 Order ID: {order_id}
💳 Transaction Number: <code>{transaction_number}</code>
📦 Package Type: {order_type}
💰 Order Value: <code>{payment_amount}$</code>

🔄 Your order will be processed and data sent soon.
💎 Credits will be deducted when proxy data is sent"""
        
        await context.bot.send_message(user_id, user_message, parse_mode='HTML')
        
        # التحقق من نوع الطلب
        if order_type == 'withdrawal':
            # معالجة طلب السحب
            await handle_withdrawal_approval_direct(query, context, order_id, user_id)
            return
    
    # رسالة للأدمن مع رقم المعاملة ونوع البروكسي
    static_type = context.user_data.get('static_type', '')
    if order_type == "static":
        if static_type == 'residential_verizon':
            proxy_type_ar = "ريزيدنتال Crocker (4$)"
        elif static_type == 'residential_att':
            proxy_type_ar = "ريزيدنتال"
        elif static_type == 'isp':
            proxy_type_ar = "ISP (3$)"
        else:
            proxy_type_ar = "بروكسي ستاتيك"
    elif order_type == "socks":
        proxy_type_ar = "بروكسي سوكس"
    else:
        proxy_type_ar = order_type
    
    admin_message = f"""✅ تم قبول الدفع للطلب

🆔 معرف الطلب: {order_id}
💳 رقم المعاملة: <code>{transaction_number}</code>
👤 معرف المستخدم: <code>{user_id}</code>
📝 الطلب: {proxy_type_ar}
💰 قيمة الطلب: <code>{payment_amount}$</code>

📋 الطلب جاهز للمعالجة والإرسال للمستخدم."""
    
    # تحضير رسالة انتظار الأدمن بدون conversation handler
    keyboard = [
        [InlineKeyboardButton("🔙 رجوع", callback_data="cancel_direct_processing")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # استخدام الرسالة الأصلية مع إضافة معلومات الدفع وتحضير للرد المباشر
    original_message = context.user_data.get('original_order_message', '')
    combined_message = f"{original_message}\n\n━━━━━━━━━━━━━━━\n{admin_message}\n\n━━━━━━━━━━━━━━━\n📝 <b>اكتب رسالتك الآن للمستخدم:</b>\n\n⬇️ *اكتب رسالة نصية وسيتم إرسالها للمستخدم مع تفاصيل البروكسي*"
    
    # التحقق من طول الرسالة
    if len(combined_message) > 4000:  # حد أمان أقل من حد Telegram (4096)
        # استخدام رسالة مختصرة
        combined_message = f"✅ تم قبول الدفع للطلب\n\n🆔 معرف الطلب: {order_id}\n💰 قيمة الطلب: <code>{payment_amount}$</code>\n\n📋 الطلب جاهز للمعالجة والإرسال للمستخدم.\n\n━━━━━━━━━━━━━━━\n📝 <b>اكتب رسالتك الآن للمستخدم:</b>\n\n⬇️ *اكتب رسالة نصية وسيتم إرسالها للمستخدم مع تفاصيل البروكسي*"
    
    try:
        await query.edit_message_text(
            combined_message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    except Exception as e:
        # محاولة بديلة بدون parse_mode
        try:
            await query.edit_message_text(
                combined_message,
                reply_markup=reply_markup
            )
        except Exception as e2:
            print(f"❌ خطأ في المحاولة البديلة: {e2}")
    
    # تعيين علامة انتظار رسالة الأدمن للمعالجة المباشرة
    context.user_data['waiting_for_direct_admin_message'] = True

async def handle_withdrawal_approval_direct(query, context: ContextTypes.DEFAULT_TYPE, order_id: str, user_id: int) -> None:
    """معالجة طلب السحب مع خيارات النجاح/الفشل للمعالجة المباشرة"""
    
    # إنشاء أزرار النجاح والفشل
    keyboard = [
        [InlineKeyboardButton("✅ تم التسديد", callback_data=f"withdrawal_success_{order_id}")],
        [InlineKeyboardButton("❌ فشلت المعاملة", callback_data=f"withdrawal_failed_{order_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"💰 معالجة طلب سحب الرصيد\n\n🆔 معرف الطلب: {order_id}\n\nاختر حالة المعاملة:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def handle_back_to_pending_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """العودة إلى قائمة الطلبات المعلقة"""
    try:
        query = update.callback_query
        await query.answer()
        
        # إعادة عرض الطلبات المعلقة
        pending_orders = db.get_pending_orders()
        
        if not pending_orders:
            await query.edit_message_text("✅ لا توجد طلبات معلقة حالياً.")
            return
        
        total_orders = len(pending_orders)
        
        # إنشاء أزرار لعرض تفاصيل كل طلب
        keyboard = []
        for i, order in enumerate(pending_orders[:20], 1):  # عرض أول 20 طلب لتجنب تجاوز حدود التيليجرام
            try:
                # التحقق من صحة بيانات الطلب قبل المعالجة
                order_id = str(order[0]) if order[0] else "unknown"
                proxy_type = str(order[2]) if len(order) > 2 and order[2] else "unknown"
                amount = str(order[6]) if len(order) > 6 and order[6] else "0"
                
                # عرض معلومات مختصرة في النص
                button_text = f"{i}. {order_id[:8]}... ({proxy_type} - {amount}$)"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"view_pending_order_{order_id}")])
            except Exception as order_error:
                logger.error(f"Error processing pending order {i} in back navigation: {order_error}")
                # إضافة زر للطلب التالف مع معلومات أساسية
                keyboard.append([InlineKeyboardButton(f"{i}. طلب تالف - إصلاح مطلوب", callback_data=f"fix_order_{i}")])
        
        # إضافة زر لعرض المزيد إذا كان هناك أكثر من 20 طلب
        if total_orders > 20:
            keyboard.append([InlineKeyboardButton(f"عرض المزيد... ({total_orders - 20} طلب إضافي)", callback_data="show_more_pending")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"📋 <b>الطلبات المعلقة</b> - المجموع: {total_orders} طلب\n\n🔽 اختر طلباً لعرض تفاصيله الكاملة مع إثبات الدفع:"
        
        await query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in handle_back_to_pending_orders: {e}")
        print(f"❌ خطأ في العودة للطلبات المعلقة: {e}")
        
        # محاولة إرسال رسالة خطأ مع خيارات
        try:
            # التحقق من صحة البيانات المطلوبة
            if not query or not hasattr(query, 'edit_message_text'):
                raise Exception("Query object is invalid")
                
            keyboard = [
                [InlineKeyboardButton("🔄 إعادة المحاولة", callback_data="retry_pending_orders")],
                [InlineKeyboardButton("🗃️ إدارة قاعدة البيانات", callback_data="admin_database_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "❌ حدث خطأ في تحميل الطلبات المعلقة\n\n"
                "الرجاء اختيار إجراء:",
                reply_markup=reply_markup
            )
        except Exception as msg_error:
            logger.error(f"Failed to send error message in back navigation: {msg_error}")
            # محاولة إرسال رسالة بسيطة بدون أزرار
            try:
                await query.edit_message_text("❌ حدث خطأ في تحميل الطلبات المعلقة")
                await asyncio.sleep(2)
                await restore_admin_keyboard(context, update.effective_chat.id)
            except Exception as final_error:
                logger.error(f"Final fallback failed: {final_error}")
                # العودة للوحة الأدمن الرئيسية كحل أخير
                await restore_admin_keyboard(context, update.effective_chat.id, "❌ حدث خطأ في النظام. تم إعادة تعيين الواجهة.")

async def handle_payment_success(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة نجاح الدفع والبدء في جمع معلومات البروكسي"""
    query = update.callback_query
    await query.answer()
    
    order_id = context.user_data['processing_order_id']
    
    # الحصول على تفاصيل الطلب أولاً
    order_query = "SELECT user_id, proxy_type, payment_amount FROM orders WHERE id = ?"
    order_result = db.execute_query(order_query, (order_id,))
    if not order_result:
        await query.edit_message_text("❌ خطأ: لم يتم العثور على الطلب")
        return ConversationHandler.END
        
    user_id = order_result[0][0]
    order_type = order_result[0][1]
    payment_amount = order_result[0][2] if order_result[0][2] else 0.0
    user_language = get_user_language(user_id)
    
    # فحص كفاية الرصيد قبل البدء في المعالجة (للبروكسيات فقط)
    if order_type in ['static', 'socks']:
        balance = db.get_user_balance(user_id)
        total_balance = balance['total_balance']
        
        if total_balance < payment_amount:
            # فشل الطلب بسبب عدم كفاية الرصيد
            db.execute_query("UPDATE orders SET status = 'failed' WHERE id = ?", (order_id,))
            
            # إشعار المستخدم بفشل الطلب
            if user_language == 'ar':
                insufficient_message = f"""❌ فشل في معالجة طلبك بسبب عدم كفاية الرصيد!

💰 رصيدك الحالي: {total_balance:.2f} نقطة
💵 المطلوب: {payment_amount:.2f} نقطة
🆔 معرف الطلب: {order_id}

📞 يرجى شحن رصيدك أولاً ثم إعادة الطلب."""
            else:
                insufficient_message = f"""❌ Order failed due to insufficient balance!

💰 Your current balance: {total_balance:.2f} points
💵 Required: {payment_amount:.2f} points
🆔 Order ID: {order_id}

📞 Please recharge your balance first and try again."""
            
            await context.bot.send_message(user_id, insufficient_message, parse_mode='HTML')
            
            # إشعار الأدمن بفشل الطلب
            admin_message = f"""❌ فشل طلب بسبب عدم كفاية الرصيد

🆔 معرف الطلب: {order_id}
👤 معرف المستخدم: {user_id}
💰 رصيد المستخدم: {total_balance:.2f} نقطة
💵 المطلوب: {payment_amount:.2f} نقطة

تم إلغاء الطلب تلقائياً."""
            
            await query.edit_message_text(admin_message, parse_mode='HTML')
            return ConversationHandler.END
    
    # توليد رقم المعاملة وحفظها (بدون تحديث حالة الطلب)
    transaction_number = generate_transaction_number('proxy')
    save_transaction(order_id, transaction_number, 'proxy', 'completed')
    
    # رسالة للمستخدم مع رقم المعاملة
    if user_language == 'ar':
        user_message = f"""✅ تم قبول معاملتك بنجاح!

🆔 معرف الطلب: {order_id}
💳 رقم المعاملة: <code>{transaction_number}</code>
📦 نوع الباكج: {order_type}
💰 قيمة الطلب: <code>{payment_amount}$</code>

🔄 سيتم معالجة طلبك وإرسال البيانات قريباً.
💎 سيتم خصم الكريديت عند إرسال بيانات البروكسي"""
    else:
        user_message = f"""✅ Your transaction has been accepted successfully!

🆔 Order ID: {order_id}
💳 Transaction Number: <code>{transaction_number}</code>
📦 Package Type: {order_type}
💰 Order Value: <code>{payment_amount}$</code>

🔄 Your order will be processed and data sent soon.
💎 Credits will be deducted when proxy data is sent"""
    
    await context.bot.send_message(user_id, user_message, parse_mode='HTML')
    
    # ملاحظة: تم نقل خصم النقاط لتتم عند إرسال بيانات البروكسي فقط
    
    # التحقق من نوع الطلب
    if order_type == 'withdrawal':
        # معالجة طلب السحب
        await handle_withdrawal_approval(query, context, order_id, user_id)
        return ConversationHandler.END
    
    # رسالة للأدمن مع رقم المعاملة ونوع البروكسي
    static_type = context.user_data.get('static_type', '')
    if order_type == "static":
        if static_type == 'residential_verizon':
            proxy_type_ar = "ريزيدنتال Crocker (4$)"
        elif static_type == 'residential_att':
            proxy_type_ar = "ريزيدنتال"
        elif static_type == 'isp':
            proxy_type_ar = "ISP (3$)"
        else:
            proxy_type_ar = "بروكسي ستاتيك"
    elif order_type == "socks":
        proxy_type_ar = "بروكسي سوكس"
    else:
        proxy_type_ar = order_type
    
    admin_message = f"""✅ تم قبول الدفع للطلب

🆔 معرف الطلب: {order_id}
💳 رقم المعاملة: <code>{transaction_number}</code>
👤 معرف المستخدم: <code>{user_id}</code>
📝 الطلب: {proxy_type_ar}
💰 قيمة الطلب: <code>{payment_amount}$</code>

📋 الطلب جاهز للمعالجة والإرسال للمستخدم."""
    
    # تجاوز أزرار الكمية والانتقال مباشرة لانتظار رسالة الأدمن
    keyboard = [
        [InlineKeyboardButton("🔙 رجوع", callback_data="cancel_processing")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # استخدام الرسالة الأصلية مع إضافة معلومات الدفع وتحضير للرد المباشر
    original_message = context.user_data.get('original_order_message', '')
    combined_message = f"{original_message}\n\n━━━━━━━━━━━━━━━\n{admin_message}\n\n━━━━━━━━━━━━━━━\n📝 <b>اكتب رسالتك الآن للمستخدم:</b>\n\n⬇️ *اكتب رسالة نصية وسيتم إرسالها للمستخدم مع تفاصيل البروكسي*"
    
    # التحقق من طول الرسالة
    print(f"📏 طول الرسالة: {len(combined_message)} حرف")
    if len(combined_message) > 4000:  # حد أمان أقل من حد Telegram (4096)
        print("⚠️ الرسالة طويلة جداً، سيتم تقصيرها")
        # استخدام رسالة مختصرة
        combined_message = f"✅ تم قبول الدفع للطلب\n\n🆔 معرف الطلب: <code>{context.user_data['processing_order_id']}</code>\n💰 قيمة الطلب: <code>{payment_amount}$</code>\n\n📋 الطلب جاهز للمعالجة والإرسال للمستخدم.\n\n━━━━━━━━━━━━━━━\n📝 <b>اكتب رسالتك الآن للمستخدم:</b>\n\n⬇️ *اكتب رسالة نصية وسيتم إرسالها للمستخدم مع تفاصيل البروكسي*"
    
    try:
        print(f"🔄 محاولة تحديث الرسالة")
        await query.edit_message_text(
            combined_message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        print(f"✅ تم تحديث الرسالة بنجاح - ينتظر رسالة الأدمن")
    except Exception as e:
        print(f"❌ خطأ في تحديث الرسالة: {e}")
        # محاولة بديلة بدون parse_mode
        try:
            await query.edit_message_text(
                combined_message,
                reply_markup=reply_markup
            )
            print(f"✅ تم تحديث الرسالة بنجاح بدون parse_mode - ينتظر رسالة الأدمن")
        except Exception as e2:
            print(f"❌ خطأ في المحاولة البديلة: {e2}")
    
    # الانتقال مباشرة لحالة انتظار رسالة الأدمن
    context.user_data['waiting_for_admin_message'] = True
    # تعيين الوضع كـ "نجاح" لمنع التداخل مع تدفق الفشل
    context.user_data['custom_mode'] = 'success'
    return CUSTOM_MESSAGE

async def handle_send_direct_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إرسال رسالة مباشرة للمستخدم"""
    query = update.callback_query
    await query.answer()
    
    order_id = query.data.replace("send_direct_message_", "")
    context.user_data['direct_message_order_id'] = order_id
    
    # تحديث الرسالة لإظهار حالة انتظار الرسالة
    await query.edit_message_text(
        f"💬 إرسال رسالة مباشرة للمستخدم\n\n🆔 معرف الطلب: {order_id}\n\n📝 اكتب رسالتك الآن وسيتم إرسالها مباشرة للمستخدم:",
        parse_mode='HTML'
    )
    
    # تحديد حالة انتظار رسالة الأدمن
    context.user_data['waiting_for_admin_message'] = True
    
    return PROCESS_ORDER

async def handle_withdrawal_approval(query, context: ContextTypes.DEFAULT_TYPE, order_id: str, user_id: int) -> None:
    """معالجة طلب السحب مع خيارات النجاح/الفشل"""
    
    # إنشاء أزرار النجاح والفشل
    keyboard = [
        [InlineKeyboardButton("✅ تم التسديد", callback_data=f"withdrawal_success_{order_id}")],
        [InlineKeyboardButton("❌ فشلت المعاملة", callback_data=f"withdrawal_failed_{order_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"💰 معالجة طلب سحب الرصيد\n\n🆔 معرف الطلب: {order_id}\n\nاختر حالة المعاملة:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def handle_payment_failed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة فشل الدفع"""
    query = update.callback_query
    await query.answer()
    
    order_id = context.user_data['processing_order_id']
    
    # التحقق من أن الطلب لم يعد معالجاً من قبل
    check_query = "SELECT truly_processed FROM orders WHERE id = ?"
    check_result = db.execute_query(check_query, (order_id,))
    if check_result and check_result[0][0]:  # إذا كان معالجاً من قبل
        await query.edit_message_text(f"❌ الطلب {order_id} تم معالجته بالفعل ولا يمكن تعديله.")
        await restore_admin_keyboard(context, update.effective_chat.id)
        return ConversationHandler.END
    
    # توليد رقم المعاملة وحفظها
    transaction_number = generate_transaction_number('proxy')
    save_transaction(order_id, transaction_number, 'proxy', 'failed')
    
    # تحديث حالة الطلب إلى فاشل وتسجيله كمعالج فعلياً (الحالة الوحيدة للفشل: ضغط زر "لا")
    update_order_status(order_id, 'failed')
    
    # تسجيل الطلب كمعالج فعلياً لأن الأدمن أكد أن الدفع غير حقيقي أو فاشل
    db.execute_query(
        "UPDATE orders SET truly_processed = TRUE WHERE id = ?",
        (order_id,)
    )
    
    # إرسال رسالة للمستخدم
    order_query = "SELECT user_id, proxy_type FROM orders WHERE id = ?"
    order_result = db.execute_query(order_query, (order_id,))
    if order_result:
        user_id = order_result[0][0]
        order_type = order_result[0][1]
        user_language = get_user_language(user_id)
        
        # رسالة للمستخدم مع رقم المعاملة
        if user_language == 'ar':
            user_message = f"""❌ تم رفض دفعتك

🆔 معرف الطلب: {order_id}
💳 رقم المعاملة: <code>{transaction_number}</code>
📦 نوع الباكج: {order_type}

📞 يرجى التواصل مع الإدارة لمعرفة سبب الرفض."""
        else:
            user_message = f"""❌ Your payment has been rejected

🆔 Order ID: {order_id}
💳 Transaction Number: <code>{transaction_number}</code>
📦 Package Type: {order_type}

📞 Please contact admin to know the reason for rejection."""
        
        await context.bot.send_message(user_id, user_message, parse_mode='HTML')
        
        # رسالة للأدمن مع رقم المعاملة ونوع البروكسي
        proxy_type_ar = "بروكسي ستاتيك" if order_type == "static" else "بروكسي سوكس" if order_type == "socks" else order_type
        
        admin_message = f"""❌ تم رفض الدفع للطلب

🆔 معرف الطلب: {order_id}
💳 رقم المعاملة: <code>{transaction_number}</code>
👤 معرف المستخدم: <code>{user_id}</code>
📝 الطلب: {proxy_type_ar}

📋 تم نقل الطلب إلى الطلبات الفاشلة وإشعار المستخدم بالرفض."""
    
    # تنظيف البيانات المؤقتة
    context.user_data.pop('processing_order_id', None)
    context.user_data.pop('admin_processing_active', None)
    context.user_data.pop('waiting_for_admin_message', None)
    context.user_data.pop('direct_processing', None)
    context.user_data.pop('custom_mode', None)
    
    await query.edit_message_text(
        admin_message,
        parse_mode='HTML'
    )
    
    # إعادة تفعيل كيبورد الأدمن الرئيسي
    await restore_admin_keyboard(context, update.effective_chat.id)
    
    return ConversationHandler.END

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
    # إحصائيات الإحالات
    total_referrals = db.execute_query("SELECT COUNT(*) FROM referrals")[0][0]
    total_amount = db.execute_query("SELECT SUM(amount) FROM referrals")[0][0] or 0
    
    # أفضل المحيلين
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

async def handle_proxy_details_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إدخال تفاصيل البروكسي خطوة بخطوة"""
    query = update.callback_query
    
    if query:
        await query.answer()
        
        if query.data.startswith("proxy_type_"):
            proxy_type = query.data.replace("proxy_type_", "")
            context.user_data['admin_proxy_type'] = proxy_type
            context.user_data['admin_input_state'] = ENTER_PROXY_ADDRESS
            
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_proxy_setup")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message = await query.edit_message_text("2️⃣ يرجى إدخال عنوان البروكسي:", reply_markup=reply_markup)
            # حفظ معرف الرسالة الحالية للتحديث لاحقاً
            context.user_data['last_cancel_message_id'] = message.message_id
            return ENTER_PROXY_ADDRESS
    
    else:
        # معالجة النص المدخل
        text = update.message.text
        

        
        current_state = context.user_data.get('admin_input_state', ENTER_PROXY_ADDRESS)
        
        if current_state == ENTER_PROXY_ADDRESS:
            # التحقق من صحة عنوان IP
            if not validate_ip_address(text):
                keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_proxy_setup")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                message = await update.message.reply_text(
                    "❌ عنوان IP غير صحيح!\n\n"
                    "✅ الشكل المطلوب: xxx.xxx.xxx.xxx\n"
                    "✅ مثال صحيح: 192.168.1.1 أو 62.1.2.1\n"
                    "✅ يُقبل من 1-3 أرقام لكل جزء\n\n"
                    "يرجى إعادة إدخال عنوان IP:",
                    reply_markup=reply_markup
                )
                # حفظ معرف رسالة الخطأ أيضاً
                context.user_data['last_cancel_message_id'] = message.message_id
                return ENTER_PROXY_ADDRESS
            
            context.user_data['admin_proxy_address'] = text
            context.user_data['admin_input_state'] = ENTER_PROXY_PORT
            
            # تحديث الرسالة السابقة لإزالة زر الإلغاء
            try:
                last_message_id = context.user_data.get('last_cancel_message_id')
                if last_message_id:
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=last_message_id,
                        text="2️⃣ ✅ تم حفظ عنوان البروكسي: " + text
                    )
            except:
                # في حالة فشل التحديث، إرسال رسالة تأكيد منفصلة
                await update.message.reply_text("✅ تم حفظ عنوان البروكسي: " + text)
            
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_proxy_setup")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message = await update.message.reply_text("3️⃣ يرجى إدخال البورت:", reply_markup=reply_markup)
            # حفظ معرف الرسالة الجديدة
            context.user_data['last_cancel_message_id'] = message.message_id
            return ENTER_PROXY_PORT
        
        elif current_state == ENTER_PROXY_PORT:
            # التحقق من صحة البورت
            if not validate_port(text):
                keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_proxy_setup")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                message = await update.message.reply_text(
                    "❌ رقم البورت غير صحيح!\n\n"
                    "✅ يجب أن يكون رقماً فقط\n"
                    "✅ حد أقصى 6 أرقام\n"
                    "✅ مثال صحيح: 80, 8080, 123456\n\n"
                    "يرجى إعادة إدخال رقم البورت:",
                    reply_markup=reply_markup
                )
                # حفظ معرف رسالة الخطأ أيضاً
                context.user_data['last_cancel_message_id'] = message.message_id
                return ENTER_PROXY_PORT
            
            context.user_data['admin_proxy_port'] = text
            
            # تحديث الرسالة السابقة لإزالة زر الإلغاء
            try:
                last_message_id = context.user_data.get('last_cancel_message_id')
                if last_message_id:
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=last_message_id,
                        text="3️⃣ ✅ تم حفظ البورت: " + text
                    )
            except:
                # في حالة فشل التحديث، إرسال رسالة تأكيد منفصلة
                await update.message.reply_text("✅ تم حفظ البورت: " + text)
            
            # تحديد نوع البروكسي المختار لعرض الدول المناسبة
            proxy_type = context.user_data.get('admin_proxy_type', 'static')
            if proxy_type == 'socks':
                countries = SOCKS_COUNTRIES['ar']
            else:
                countries = STATIC_COUNTRIES['ar']
            
            # عرض قائمة الدول مقسمة
            reply_markup = create_paginated_keyboard(countries, "admin_country_", 0, 8, 'ar')
            await update.message.reply_text("4️⃣ اختر الدولة:", reply_markup=reply_markup)
            return ENTER_COUNTRY
        
        elif current_state == ENTER_COUNTRY:
            # معالجة إدخال الدولة يدوياً
            context.user_data['admin_proxy_country'] = text
            context.user_data['admin_input_state'] = ENTER_STATE
            
            # تأكيد حفظ الدولة
            try:
                await update.message.reply_text("✅ تم حفظ الدولة: " + text)
            except:
                pass
            
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_proxy_setup")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message = await update.message.reply_text("5️⃣ يرجى إدخال اسم الولاية:", reply_markup=reply_markup)
            # حفظ معرف الرسالة الجديدة
            context.user_data['last_cancel_message_id'] = message.message_id
            return ENTER_STATE
        
        elif current_state == ENTER_STATE:
            # معالجة إدخال الولاية يدوياً
            context.user_data['admin_proxy_state'] = text
            context.user_data['admin_input_state'] = ENTER_USERNAME
            
            # تحديث الرسالة السابقة لإزالة زر الإلغاء
            try:
                last_message_id = context.user_data.get('last_cancel_message_id')
                if last_message_id:
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=last_message_id,
                        text="5️⃣ ✅ تم حفظ الولاية: " + text
                    )
            except:
                # في حالة فشل التحديث، إرسال رسالة تأكيد منفصلة
                await update.message.reply_text("✅ تم حفظ الولاية: " + text)
            
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_proxy_setup")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message = await update.message.reply_text("6️⃣ يرجى إدخال اسم المستخدم للبروكسي:", reply_markup=reply_markup)
            # حفظ معرف الرسالة الجديدة
            context.user_data['last_cancel_message_id'] = message.message_id
            return ENTER_USERNAME
        
        elif current_state == ENTER_USERNAME:
            context.user_data['admin_proxy_username'] = text
            context.user_data['admin_input_state'] = ENTER_PASSWORD
            
            # تحديث الرسالة السابقة لإزالة زر الإلغاء
            try:
                last_message_id = context.user_data.get('last_cancel_message_id')
                if last_message_id:
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=last_message_id,
                        text="6️⃣ ✅ تم حفظ اسم المستخدم: " + text
                    )
            except:
                # في حالة فشل التحديث، إرسال رسالة تأكيد منفصلة
                await update.message.reply_text("✅ تم حفظ اسم المستخدم: " + text)
            
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_proxy_setup")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message = await update.message.reply_text("7️⃣ يرجى إدخال كلمة المرور:", reply_markup=reply_markup)
            # حفظ معرف الرسالة الجديدة
            context.user_data['last_cancel_message_id'] = message.message_id
            return ENTER_PASSWORD
        
        elif current_state == ENTER_PASSWORD:
            context.user_data['admin_proxy_password'] = text
            context.user_data['admin_input_state'] = ENTER_THANK_MESSAGE
            
            # تحديث الرسالة السابقة لإزالة زر الإلغاء
            try:
                last_message_id = context.user_data.get('last_cancel_message_id')
                if last_message_id:
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=last_message_id,
                        text="7️⃣ ✅ تم حفظ كلمة المرور بنجاح"
                    )
            except:
                # في حالة فشل التحديث، إرسال رسالة تأكيد منفصلة
                await update.message.reply_text("✅ تم حفظ كلمة المرور بنجاح")
            
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_proxy_setup")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message = await update.message.reply_text("8️⃣ يرجى إدخال رسالة شكر قصيرة:", reply_markup=reply_markup)
            # حفظ معرف الرسالة الجديدة
            context.user_data['last_cancel_message_id'] = message.message_id
            return ENTER_THANK_MESSAGE
        
        elif current_state == ENTER_THANK_MESSAGE:
            thank_message = text
            context.user_data['admin_thank_message'] = thank_message
            
            # تحديث الرسالة السابقة لإزالة زر الإلغاء
            try:
                last_message_id = context.user_data.get('last_cancel_message_id')
                if last_message_id:
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=last_message_id,
                        text="8️⃣ ✅ تم حفظ رسالة الشكر بنجاح"
                    )
            except:
                # في حالة فشل التحديث، إرسال رسالة تأكيد منفصلة
                await update.message.reply_text("✅ تم حفظ رسالة الشكر بنجاح")
            
            # عرض المعلومات للمراجعة قبل الإرسال
            await show_proxy_preview(update, context)
            return ENTER_THANK_MESSAGE
    
    return current_state

async def send_proxy_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE, thank_message: str = None) -> None:
    """إرسال تفاصيل البروكسي للمستخدم"""
    order_id = context.user_data['processing_order_id']
    
    # الحصول على معلومات المستخدم والطلب
    user_query = """
        SELECT o.user_id, u.first_name, u.last_name 
        FROM orders o 
        JOIN users u ON o.user_id = u.user_id 
        WHERE o.id = ?
    """
    user_result = db.execute_query(user_query, (order_id,))
    
    if user_result:
        user_id, first_name, last_name = user_result[0]
        user_full_name = f"{first_name} {last_name or ''}".strip()
        
        # الحصول على التاريخ والوقت الحاليين
        from datetime import datetime
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")
        
        # إنشاء رسالة البروكسي للمستخدم
        proxy_message = f"""✅ تم معالجة طلب {user_full_name}

🔐 تفاصيل البروكسي:
📡 العنوان: <code>{context.user_data['admin_proxy_address']}</code>
🔌 البورت: <code>{context.user_data['admin_proxy_port']}</code>
🌍 الدولة: {context.user_data.get('admin_proxy_country', 'غير محدد')}
🏠 الولاية: {context.user_data.get('admin_proxy_state', 'غير محدد')}
👤 اسم المستخدم: <code>{context.user_data['admin_proxy_username']}</code>
🔑 كلمة المرور: <code>{context.user_data['admin_proxy_password']}</code>

━━━━━━━━━━━━━━━
🆔 معرف الطلب: {order_id}
📅 التاريخ: {current_date}
🕐 الوقت: {current_time}

━━━━━━━━━━━━━━━
💬 {thank_message}"""
        
        # ============================================
        # اقتطاع الرصيد عند إرسال البروكسي (المرحلة 3)
        # ============================================
        order_query = "SELECT user_id, payment_amount, proxy_type FROM orders WHERE id = ?"
        order_result = db.execute_query(order_query, (order_id,))
        
        if order_result:
            order_user_id, payment_amount, proxy_type = order_result[0]
            
            # اقتطاع الرصيد (مع السماح بالرصيد السالب لمنع التحايل)
            try:
                db.deduct_credits(
                    order_user_id, 
                    payment_amount, 
                    'proxy_purchase', 
                    order_id, 
                    f"شراء بروكسي {proxy_type}",
                    allow_negative=True  # السماح بالرصيد السالب
                )
                logger.info(f"✅ تم اقتطاع {payment_amount} نقطة من المستخدم {order_user_id} للطلب {order_id}")
            except Exception as deduct_error:
                logger.error(f"Error deducting points for order {order_id}: {deduct_error}")
        
        # إرسال البروكسي للمستخدم
        await context.bot.send_message(user_id, proxy_message, parse_mode='HTML')
        
        # تحديث حالة الطلب
        proxy_details = {
            'address': context.user_data['admin_proxy_address'],
            'port': context.user_data['admin_proxy_port'],
            'country': context.user_data.get('admin_proxy_country', ''),
            'state': context.user_data.get('admin_proxy_state', ''),
            'username': context.user_data['admin_proxy_username'],
            'password': context.user_data['admin_proxy_password']
        }
        
        # تسجيل الطلب كمكتمل ومعالج فعلياً (الشرط الثاني: إرسال البيانات الكاملة للمستخدم)
        db.execute_query(
            "UPDATE orders SET status = 'completed', processed_at = CURRENT_TIMESTAMP, proxy_details = ?, truly_processed = TRUE WHERE id = ?",
            (json.dumps(proxy_details), order_id)
        )
        
        # التحقق من إضافة رصيد الإحالة لأول عملية شراء
        await check_and_add_referral_bonus(context, user_id, order_id)
        
        # رسالة تأكيد للأدمن
        admin_message = f"""✅ تم معالجة طلب {user_full_name}

🔐 تفاصيل البروكسي المرسلة:
📡 العنوان: <code>{context.user_data['admin_proxy_address']}</code>
🔌 البورت: <code>{context.user_data['admin_proxy_port']}</code>
🌍 الدولة: {context.user_data.get('admin_proxy_country', 'غير محدد')}
🏠 الولاية: {context.user_data.get('admin_proxy_state', 'غير محدد')}
👤 اسم المستخدم: <code>{context.user_data['admin_proxy_username']}</code>
🔑 كلمة المرور: <code>{context.user_data['admin_proxy_password']}</code>

━━━━━━━━━━━━━━━
🆔 معرف الطلب: {order_id}
📅 التاريخ: {current_date}
🕐 الوقت: {current_time}

━━━━━━━━━━━━━━━
💬 {thank_message}"""

        await update.message.reply_text(admin_message, parse_mode='HTML')
        
        # تنظيف البيانات المؤقتة
        admin_keys = [k for k in context.user_data.keys() if k.startswith('admin_')]
        for key in admin_keys:
            del context.user_data[key]
        
        # إزالة معرف الطلب قيد المعالجة لضمان إمكانية معالجة طلبات جديدة
        context.user_data.pop('processing_order_id', None)
        context.user_data.pop('admin_processing_active', None)

async def send_proxy_to_user_direct(update: Update, context: ContextTypes.DEFAULT_TYPE, thank_message: str = None) -> None:
    """إرسال تفاصيل البروكسي للمستخدم مباشرة"""
    order_id = context.user_data['processing_order_id']
    
    # الحصول على معلومات المستخدم والطلب
    user_query = """
        SELECT o.user_id, u.first_name, u.last_name 
        FROM orders o 
        JOIN users u ON o.user_id = u.user_id 
        WHERE o.id = ?
    """
    user_result = db.execute_query(user_query, (order_id,))
    
    if user_result:
        user_id, first_name, last_name = user_result[0]
        user_full_name = f"{first_name} {last_name or ''}".strip()
        
        # الحصول على التاريخ والوقت الحاليين
        from datetime import datetime
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")
        
        # إنشاء رسالة البروكسي للمستخدم
        proxy_message = f"""✅ تم معالجة طلب {user_full_name}

🔐 تفاصيل البروكسي:
📡 العنوان: <code>{context.user_data['admin_proxy_address']}</code>
🔌 البورت: <code>{context.user_data['admin_proxy_port']}</code>
🌍 الدولة: {context.user_data.get('admin_proxy_country', 'غير محدد')}
🏠 الولاية: {context.user_data.get('admin_proxy_state', 'غير محدد')}
👤 اسم المستخدم: <code>{context.user_data['admin_proxy_username']}</code>
🔑 كلمة المرور: <code>{context.user_data['admin_proxy_password']}</code>

━━━━━━━━━━━━━━━
🆔 معرف الطلب: {order_id}
📅 التاريخ: {current_date}
🕐 الوقت: {current_time}

━━━━━━━━━━━━━━━
💬 {thank_message}"""
        
        # اقتطاع الرصيد من المستخدم عند إرسال البروكسي (هذا هو التوقيت الصحيح)
        order_query = "SELECT user_id, payment_amount, proxy_type FROM orders WHERE id = ?"
        order_result = db.execute_query(order_query, (order_id,))
        
        if order_result:
            order_user_id, payment_amount, proxy_type = order_result[0]
            
            # اقتطاع الرصيد (مع السماح بالرصيد السالب لمنع التحايل)
            try:
                db.deduct_credits(
                    order_user_id, 
                    payment_amount, 
                    'proxy_purchase', 
                    order_id, 
                    f"شراء بروكسي {proxy_type}",
                    allow_negative=True  # السماح بالرصيد السالب
                )
                logger.info(f"تم اقتطاع {payment_amount} نقطة من المستخدم {order_user_id} للطلب {order_id}")
            except Exception as deduct_error:
                logger.error(f"Error deducting points for order {order_id}: {deduct_error}")
        
        # إرسال البروكسي للمستخدم
        await context.bot.send_message(user_id, proxy_message, parse_mode='HTML')
        
        # تحديث حالة الطلب
        proxy_details = {
            'address': context.user_data['admin_proxy_address'],
            'port': context.user_data['admin_proxy_port'],
            'country': context.user_data.get('admin_proxy_country', ''),
            'state': context.user_data.get('admin_proxy_state', ''),
            'username': context.user_data['admin_proxy_username'],
            'password': context.user_data['admin_proxy_password']
        }
        
        # تسجيل الطلب كمكتمل ومعالج فعلياً (الشرط الثاني: إرسال البيانات الكاملة للمستخدم)
        db.execute_query(
            "UPDATE orders SET status = 'completed', processed_at = CURRENT_TIMESTAMP, proxy_details = ?, truly_processed = TRUE WHERE id = ?",
            (json.dumps(proxy_details), order_id)
        )
        
        # التحقق من إضافة رصيد الإحالة لأول عملية شراء
        await check_and_add_referral_bonus(context, user_id, order_id)
        
        # تنظيف البيانات المؤقتة (مطلوب لضمان عدم تعليق البوت)
        admin_keys = [k for k in context.user_data.keys() if k.startswith('admin_')]
        for key in admin_keys:
            context.user_data.pop(key, None)
        
        # إزالة معرف الطلب قيد المعالجة لضمان إمكانية معالجة طلبات جديدة
        context.user_data.pop('processing_order_id', None)
        context.user_data.pop('admin_processing_active', None)

async def handle_user_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة البحث عن مستخدم"""
    search_term = update.message.text
    
    # البحث بالمعرف أو اسم المستخدم
    if search_term.startswith('@'):
        username = search_term[1:]
        query = "SELECT * FROM users WHERE username = ?"
        user_result = db.execute_query(query, (username,))
    else:
        try:
            user_id = int(search_term)
            query = "SELECT * FROM users WHERE user_id = ?"
            user_result = db.execute_query(query, (user_id,))
        except ValueError:
            # إعادة تفعيل كيبورد الأدمن
            await update.message.reply_text("معرف المستخدم غير صحيح!")
            await restore_admin_keyboard(context, update.effective_chat.id, "🔧 لوحة الأدمن جاهزة")
            return ConversationHandler.END
    
    if not user_result:
        # إعادة تفعيل كيبورد الأدمن
        await update.message.reply_text("المستخدم غير موجود!")
        await restore_admin_keyboard(context, update.effective_chat.id, "🔧 لوحة الأدمن جاهزة")
        return ConversationHandler.END
    
    user = user_result[0]
    user_id = user[0]
    
    # إحصائيات المستخدم
    successful_orders = db.execute_query(
        "SELECT COUNT(*), SUM(payment_amount) FROM orders WHERE user_id = ? AND status = 'completed'",
        (user_id,)
    )[0]
    
    failed_orders = db.execute_query(
        "SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = 'failed'",
        (user_id,)
    )[0][0]
    
    pending_orders = db.execute_query(
        "SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = 'pending'",
        (user_id,)
    )[0][0]
    
    # إحصائيات إضافية للتشخيص
    all_orders = db.execute_query(
        "SELECT COUNT(*) FROM orders WHERE user_id = ?",
        (user_id,)
    )[0][0]
    
    # فحص الطلبات بحسب الحالة (للتشخيص)
    try:
        orders_by_status = db.execute_query(
            "SELECT status, COUNT(*), COALESCE(SUM(payment_amount), 0) FROM orders WHERE user_id = ? GROUP BY status",
            (user_id,)
        ) or []
    except:
        orders_by_status = []
    
    referral_count = db.execute_query(
        "SELECT COUNT(*) FROM referrals WHERE referrer_id = ?",
        (user_id,)
    )[0][0]
    
    last_successful_order = db.execute_query(
        "SELECT created_at FROM orders WHERE user_id = ? AND status = 'completed' ORDER BY created_at DESC LIMIT 1",
        (user_id,)
    )
    
    # الحصول على معلومات إضافية عن المستخدم
    # الرصيد الحالي (points)
    current_balance = float(user[6]) if user[6] else 0.0
    
    # الرصيد الإجمالي المكتسب من الإحالات
    referral_earned = float(user[5]) if user[5] else 0.0
    
    # إجمالي النقاط المشحونة (حساب بديل)
    try:
        total_recharged_result = db.execute_query(
            "SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = 'completed'",
            (user_id,)
        )
        total_recharged = 0.0  # يمكن حسابها لاحقاً من بيانات أخرى
    except:
        total_recharged = 0.0
    
    # إجمالي النقاط المستخدمة (حساب بديل)
    try:
        total_spent_result = db.execute_query(
            "SELECT COALESCE(SUM(payment_amount), 0) FROM orders WHERE user_id = ? AND status = 'completed'",
            (user_id,)
        )
        total_spent = float(total_spent_result[0][0]) if total_spent_result and total_spent_result[0] else 0.0
    except:
        total_spent = 0.0
    
    # تحديد حالة المستخدم
    status_text = "🟢 نشط" if current_balance > 0 or all_orders > 0 else "🟡 غير نشط"
    
    report = f"""📊 ملف المستخدم الشامل

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>البيانات الشخصية</b>
• الاسم: {user[2]} {user[3]}
• اسم المستخدم: @{user[1] or 'غير محدد'}  
• المعرف: <code>{user[0]}</code>
• الحالة: {status_text}
• تاريخ الانضمام: {user[7]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 <b>النظام المالي</b>
• الرصيد الحالي: <code>${current_balance:.2f}</code>
• إجمالي الشحن: <code>${total_recharged:.2f}</code>
• إجمالي الإنفاق: <code>${total_spent:.2f}</code>
• رصيد الإحالات: <code>${referral_earned:.2f}</code>
• صافي الحساب: <code>${(current_balance + referral_earned):.2f}</code>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 <b>إحصائيات الطلبات</b>
• إجمالي الطلبات: <code>{all_orders}</code>
• الطلبات الناجحة: <code>{successful_orders[0]}</code> (${successful_orders[1] or 0:.2f})
• الطلبات الفاشلة: <code>{failed_orders}</code>
• الطلبات المعلقة: <code>{pending_orders}</code>
• آخر شراء ناجح: {last_successful_order[0][0] if last_successful_order else 'لا يوجد'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👥 <b>نظام الإحالات</b>
• عدد المُحالين: <code>{referral_count}</code> شخص
• أرباح الإحالات: <code>${referral_earned:.2f}</code>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 <b>تفصيل الطلبات حسب الحالة:</b>
{chr(10).join([f"📌 <b>{status}</b>: {count} طلب → ${amount or 0:.2f}" for status, count, amount in orders_by_status]) if orders_by_status else "لا توجد طلبات"}"""

    # حفظ معرف المستخدم للعمليات التالية
    context.user_data['selected_user_id'] = user_id
    context.user_data['selected_user_data'] = user
    
    # إنشاء أزرار الإدارة
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
            InlineKeyboardButton("📊 تقارير مفصلة", callback_data=f"detailed_reports_{user_id}")
        ],
        [
            InlineKeyboardButton("🔙 رجوع لقائمة الأدمن", callback_data="back_to_admin_menu")
        ]
    ]
    
    # إضافة زر المحادثة فقط إذا كان للمستخدم username
    if user[1]:  # user[1] هو username
        keyboard.insert(2, [
            InlineKeyboardButton("💬 فتح محادثة", url=f"https://t.me/{user[1]}")
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(report, reply_markup=reply_markup, parse_mode='HTML')
    return ConversationHandler.END

# دوال إدارة المستخدمين الجديدة
async def handle_manage_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة إدارة المستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("🚫 حظر المستخدم", callback_data=f"ban_user_{user_id}"),
            InlineKeyboardButton("✅ فك حظر المستخدم", callback_data=f"unban_user_{user_id}")
        ],
        [
            InlineKeyboardButton("🛠️ رفع الحظر المؤقت", callback_data=f"remove_temp_ban_{user_id}"),
            InlineKeyboardButton("📊 إعادة تعيين الإحصائيات", callback_data=f"reset_stats_{user_id}")
        ],
        [
            InlineKeyboardButton("🗑️ مسح البيانات", callback_data=f"delete_user_data_{user_id}"),
            InlineKeyboardButton("🔙 رجوع للملف", callback_data=f"back_to_profile_{user_id}")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    
    message = f"""👤 إدارة المستخدم

📋 المستخدم: {first_name} {last_name}
🆔 المعرف: {user_id}

⚙️ عمليات الإدارة المتاحة:
• حظر/فك حظر المستخدم
• رفع الحظر المؤقت (بسبب العمليات التخريبية)
• مسح بيانات المستخدم
• إعادة تعيين الإحصائيات

⚠️ تحذير: هذه العمليات لا يمكن التراجع عنها"""
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

async def handle_manage_points(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة إدارة النقاط"""
    query = update.callback_query
    await query.answer()
    
    # تنظيف أي عمليات معلقة
    context.user_data.pop('awaiting_points_input', None)
    context.user_data.pop('points_action', None)
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    # user_data structure: [0]=user_id, [1]=username, [2]=first_name, [3]=last_name, 
    # [4]=language, [5]=referral_balance, [6]=credits_balance, [7]=referred_by, [8]=join_date, [9]=is_admin
    current_balance = float(user_data[6]) if user_data[6] else 0.0
    
    keyboard = [
        [
            InlineKeyboardButton("➕ إضافة نقاط", callback_data=f"add_points_{user_id}"),
            InlineKeyboardButton("➖ خصم نقاط", callback_data=f"subtract_points_{user_id}")
        ],
        [
            InlineKeyboardButton("🗑️ تصفير الرصيد", callback_data=f"reset_balance_{user_id}"),
            InlineKeyboardButton("💰 تعديل مخصص", callback_data=f"custom_balance_{user_id}")
        ],
        [
            InlineKeyboardButton("📊 سجل المعاملات", callback_data=f"transaction_history_{user_id}")
        ],
        [
            InlineKeyboardButton("🔙 رجوع للملف", callback_data=f"back_to_profile_{user_id}")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    
    # استخدام نص بسيط بدون Markdown لتجنب أخطاء parsing
    message = f"""💰 إدارة النقاط

📋 المستخدم: {first_name} {last_name}
🆔 المعرف: {user_id}
💳 الرصيد الحالي: ${current_balance:.2f}

⚠️ تنبيه مهم: جميع القيم تُدخل بالنقاط وليس بالدولار!

⚙️ عمليات إدارة النقاط:
• إضافة أو خصم نقاط مع رسائل مخصصة
• تصفير الرصيد بالكامل
• تعديل الرصيد لقيمة مخصصة
• عرض سجل المعاملات

💬 الرسائل: يمكنك اختيار رسالة مخصصة أو قالب جاهز"""
    
    await query.edit_message_text(message, reply_markup=reply_markup)

async def handle_broadcast_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة البث للمستخدم المحدد"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("📝 رسالة نصية", callback_data=f"send_text_{user_id}"),
            InlineKeyboardButton("🖼️ رسالة مع صورة", callback_data=f"send_photo_{user_id}")
        ],
        [
            InlineKeyboardButton("⚡ رسالة سريعة", callback_data=f"quick_message_{user_id}"),
            InlineKeyboardButton("📢 إشعار هام", callback_data=f"important_notice_{user_id}")
        ],
        [
            InlineKeyboardButton("🔙 رجوع للملف", callback_data=f"back_to_profile_{user_id}")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    username = escape_markdown(user_data[1] or "غير محدد")
    
    message = f"""📢 <b>بث رسالة للمستخدم</b>

📋 <b>المستخدم:</b> {first_name} {last_name}
🆔 <b>المعرف:</b> <code>{user_id}</code>
📱 <b>اسم المستخدم:</b> @{username}

📤 <b>أنواع الرسائل المتاحة:</b>
• رسالة نصية عادية
• رسالة مع صورة مرفقة
• رسالة سريعة (قوالب جاهزة)
• إشعار هام (عالي الأولوية)"""
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

async def handle_manage_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة إدارة الإحالات"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    # الحصول على إحصائيات الإحالات
    referral_count = db.execute_query(
        "SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,)
    )[0][0]
    
    referral_earnings = float(user_data[5]) if user_data[5] else 0.0
    
    keyboard = [
        [
            InlineKeyboardButton("👥 عرض المُحالين", callback_data=f"show_referred_{user_id}"),
            InlineKeyboardButton("💰 سجل الأرباح", callback_data=f"referral_earnings_{user_id}")
        ],
        [
            InlineKeyboardButton("➕ إدراج إحالة", callback_data=f"add_referral_{user_id}"),
            InlineKeyboardButton("❌ حذف إحالة", callback_data=f"delete_referral_{user_id}")
        ],
        [
            InlineKeyboardButton("🗑️ تصفير رصيد الإحالة", callback_data=f"reset_referral_balance_{user_id}"),
            InlineKeyboardButton("🔄 مسح جميع الإحالات", callback_data=f"clear_referrals_{user_id}")
        ],
        [
            InlineKeyboardButton("🔙 رجوع للملف", callback_data=f"back_to_profile_{user_id}")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    
    message = f"""👥 <b>إدارة الإحالات</b>

📋 <b>المستخدم:</b> {first_name} {last_name}
🆔 <b>المعرف:</b> <code>{user_id}</code>

📊 <b>إحصائيات الإحالات:</b>
• عدد المُحالين: <code>{referral_count}</code> شخص
• إجمالي الأرباح: <code>${referral_earnings:.2f}</code>

⚙️ <b>عمليات إدارة الإحالات:</b>
• عرض قائمة المستخدمين المُحالين
• عرض سجل أرباح الإحالات
• إدراج إحالة جديدة يدوياً
• حذف إحالة محددة (مع عرض أسماء المحالين)
• تصفير رصيد الإحالة فقط
• مسح جميع الإحالات"""
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

async def handle_detailed_reports(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة التقارير المفصلة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("📊 تقرير شامل", callback_data=f"full_report_{user_id}"),
            InlineKeyboardButton("💰 تقرير مالي", callback_data=f"financial_report_{user_id}")
        ],
        [
            InlineKeyboardButton("📦 تقرير الطلبات", callback_data=f"orders_report_{user_id}"),
            InlineKeyboardButton("👥 تقرير الإحالات", callback_data=f"referrals_report_{user_id}")
        ],
        [
            InlineKeyboardButton("📈 إحصائيات متقدمة", callback_data=f"advanced_stats_{user_id}"),
            InlineKeyboardButton("📅 تقرير زمني", callback_data=f"timeline_report_{user_id}")
        ],
        [
            InlineKeyboardButton("🔙 رجوع للملف", callback_data=f"back_to_profile_{user_id}")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    
    message = f"""📊 <b>التقارير المفصلة</b>

📋 <b>المستخدم:</b> {first_name} {last_name}
🆔 <b>المعرف:</b> <code>{user_id}</code>

📈 <b>أنواع التقارير المتاحة:</b>
• تقرير شامل لجميع البيانات
• تقرير مالي (رصيد، معاملات، إنفاق)
• تقرير الطلبات (تفصيلي حسب النوع والحالة)
• تقرير الإحالات والأرباح
• إحصائيات متقدمة ورسوم بيانية
• تقرير زمني لنشاط المستخدم"""
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

async def handle_user_lookup_unified(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالج موحد للبحث عن المستخدمين وتصفير الرصيد"""
    # التحقق من السياق لتحديد العملية المطلوبة
    user_data_action = context.user_data.get('lookup_action', 'lookup')
    
    if user_data_action == 'reset_balance':
        return await handle_balance_reset(update, context)
    else:
        return await handle_user_lookup(update, context)

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
        [KeyboardButton(buttons[7])],
        [KeyboardButton(buttons[8])]
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
    
    # إنشاء الأزرار الرئيسية للمستخدم
    reply_markup = create_main_user_keyboard(language)
    
    await update.message.reply_text(
        MESSAGES[language]['welcome'],
        reply_markup=reply_markup
    )

async def show_pending_orders_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض الطلبات المعلقة للأدمن مع إمكانية اختيار الطلب لعرض التفاصيل"""
    try:
        pending_orders = db.get_pending_orders()
        
        if not pending_orders:
            await update.message.reply_text("✅ لا توجد طلبات معلقة حالياً.")
            return
        
        total_orders = len(pending_orders)
        
        await update.message.reply_text(f"📋 <b>الطلبات المعلقة</b> - المجموع: {total_orders} طلب\n\n🔽 اختر طلباً لعرض تفاصيله الكاملة مع إثبات الدفع:", parse_mode='HTML')
        
        # إنشاء أزرار لعرض تفاصيل كل طلب
        keyboard = []
        for i, order in enumerate(pending_orders[:20], 1):  # عرض أول 20 طلب لتجنب تجاوز حدود التيليجرام
            try:
                # التحقق من صحة بيانات الطلب قبل المعالجة
                order_id = str(order[0]) if order[0] else "unknown"
                proxy_type = str(order[2]) if len(order) > 2 and order[2] else "unknown"
                amount = str(order[6]) if len(order) > 6 and order[6] else "0"
                
                # عرض معلومات مختصرة في النص
                button_text = f"{i}. {order_id[:8]}... ({proxy_type} - {amount}$)"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"view_pending_order_{order_id}")])
            except Exception as order_error:
                logger.error(f"Error processing pending order {i}: {order_error}")
                # إضافة زر للطلب التالف مع معلومات أساسية
                keyboard.append([InlineKeyboardButton(f"{i}. طلب تالف - إصلاح مطلوب", callback_data=f"fix_order_{i}")])
        
        # إضافة زر لعرض المزيد إذا كان هناك أكثر من 20 طلب
        if total_orders > 20:
            keyboard.append([InlineKeyboardButton(f"عرض المزيد... ({total_orders - 20} طلب إضافي)", callback_data="show_more_pending")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("📋 <b>قائمة الطلبات المعلقة:</b>", parse_mode='HTML', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in show_pending_orders_admin: {e}")
        print(f"❌ خطأ في عرض الطلبات المعلقة: {e}")
        
        # إرسال رسالة خطأ للأدمن مع خيارات
        try:
            # التحقق من صحة البيانات المطلوبة
            if not update or not hasattr(update, 'message') or not update.message:
                raise Exception("Update or message object is invalid")
                
            keyboard = [
                [InlineKeyboardButton("🔄 إعادة المحاولة", callback_data="retry_pending_orders")],
                [InlineKeyboardButton("🗃️ إدارة قاعدة البيانات", callback_data="admin_database_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "❌ حدث خطأ في تحميل الطلبات المعلقة\n\n"
                "قد يكون السبب:\n"
                "• مشكلة في قاعدة البيانات\n"
                "• بيانات تالفة في الطلبات\n"
                "• نفاد الذاكرة\n\n"
                "الرجاء اختيار إجراء:",
                reply_markup=reply_markup
            )
        except Exception as msg_error:
            logger.error(f"Failed to send error message: {msg_error}")
            # محاولة إرسال رسالة بسيطة بدون أزرار
            try:
                await update.message.reply_text("❌ حدث خطأ في تحميل الطلبات المعلقة")
                await asyncio.sleep(2)
                await restore_admin_keyboard(context, update.effective_chat.id)
            except Exception as final_error:
                logger.error(f"Final fallback failed in show_pending_orders: {final_error}")
                # العودة للوحة الأدمن الرئيسية كحل أخير
                await restore_admin_keyboard(context, update.effective_chat.id, "❌ حدث خطأ في النظام. تم إعادة تعيين الواجهة.")

async def delete_processed_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """حذف الطلبات المعالجة (المكتملة والفاشلة)"""
    # عد الطلبات المعالجة (المكتملة والفاشلة)
    count_query = """
        SELECT COUNT(*) FROM orders 
        WHERE status IN ('completed', 'failed')
    """
    count_result = db.execute_query(count_query, ())
    count_before = count_result[0][0] if count_result else 0
    
    # عد الطلبات المكتملة والفاشلة بشكل منفصل للتقرير
    completed_count = db.execute_query("SELECT COUNT(*) FROM orders WHERE status = 'completed'")[0][0] if db.execute_query("SELECT COUNT(*) FROM orders WHERE status = 'completed'") else 0
    failed_count = db.execute_query("SELECT COUNT(*) FROM orders WHERE status = 'failed'")[0][0] if db.execute_query("SELECT COUNT(*) FROM orders WHERE status = 'failed'") else 0
    
    # حذف الطلبات المعالجة (المكتملة والفاشلة)
    delete_query = """
        DELETE FROM orders 
        WHERE status IN ('completed', 'failed')
    """
    db.execute_query(delete_query, ())
    
    await update.message.reply_text(
        f"🗑️ تم حذف {count_before} طلب معالج:\n\n"
        f"✅ طلبات مكتملة: {completed_count}\n"
        f"❌ طلبات فاشلة: {failed_count}\n\n"
        f"📋 تم الاحتفاظ بالطلبات المعلقة."
    )

async def delete_all_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """حذف جميع الطلبات مع رسالة تأكيد"""
    user_id = update.effective_user.id
    
    # عرض رسالة التأكيد
    # عد جميع الطلبات بحسب الحالة
    pending_count = db.execute_query("SELECT COUNT(*) FROM orders WHERE status = 'pending'")[0][0] if db.execute_query("SELECT COUNT(*) FROM orders WHERE status = 'pending'") else 0
    completed_count = db.execute_query("SELECT COUNT(*) FROM orders WHERE status = 'completed'")[0][0] if db.execute_query("SELECT COUNT(*) FROM orders WHERE status = 'completed'") else 0
    failed_count = db.execute_query("SELECT COUNT(*) FROM orders WHERE status = 'failed'")[0][0] if db.execute_query("SELECT COUNT(*) FROM orders WHERE status = 'failed'") else 0
    total_count = pending_count + completed_count + failed_count
    
    # حفظ معرف الأدمن للتأكيد
    context.user_data['delete_all_orders_user_id'] = user_id
    context.user_data['delete_all_orders_counts'] = {
        'pending': pending_count,
        'completed': completed_count, 
        'failed': failed_count,
        'total': total_count
    }
    
    confirmation_message = f"""⚠️ <b>تحذير: حذف جميع الطلبات</b>

هل أنت متأكد من حذف <b>جميع الطلبات</b> من قاعدة البيانات؟

📊 <b>إحصائيات الطلبات الحالية:</b>
⏳ طلبات معلقة: {pending_count}
✅ طلبات مكتملة: {completed_count}
❌ طلبات فاشلة: {failed_count}
📋 <b>المجموع الكلي: {total_count} طلب</b>

🚨 <b>تحذير:</b> هذا الإجراء غير قابل للتراجع!

أكتب "نعم أحذف الجميع" للتأكيد أو أي شيء آخر للإلغاء."""
    
    await update.message.reply_text(confirmation_message, parse_mode='HTML')
    
    return CONFIRM_DELETE_ALL_ORDERS

async def handle_confirm_delete_all_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة تأكيد حذف جميع الطلبات"""
    user_text = update.message.text.strip()
    
    if user_text == "نعم أحذف الجميع":
        # تنفيذ حذف جميع الطلبات
        counts = context.user_data.get('delete_all_orders_counts', {})
        
        # حذف جميع الطلبات
        db.execute_query("DELETE FROM orders", ())
        
        # إرسال تقرير الحذف
        report_message = f"""✅ <b>تم حذف جميع الطلبات بنجاح</b>

📊 <b>تقرير الحذف:</b>
⏳ طلبات معلقة محذوفة: {counts.get('pending', 0)}
✅ طلبات مكتملة محذوفة: {counts.get('completed', 0)}
❌ طلبات فاشلة محذوفة: {counts.get('failed', 0)}

🗑️ <b>المجموع المحذوف: {counts.get('total', 0)} طلب</b>

📋 قاعدة البيانات الآن خالية من جميع الطلبات."""

        await update.message.reply_text(report_message, parse_mode='HTML')
        
        # تنظيف البيانات المؤقتة
        context.user_data.pop('delete_all_orders_user_id', None)
        context.user_data.pop('delete_all_orders_counts', None)
        
        # العودة للوحة الأدمن
        await restore_admin_keyboard(context, update.effective_chat.id, "🔧 لوحة الأدمن جاهزة")
        
    else:
        # إلغاء العملية
        await update.message.reply_text("❌ تم إلغاء عملية حذف جميع الطلبات.\n\n✅ لم يتم حذف أي طلب.")
        
        # تنظيف البيانات المؤقتة
        context.user_data.pop('delete_all_orders_user_id', None)
        context.user_data.pop('delete_all_orders_counts', None)
        
        # العودة للوحة الأدمن
        await restore_admin_keyboard(context, update.effective_chat.id, "🔧 لوحة الأدمن جاهزة")
    
    return ConversationHandler.END

async def show_sales_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض إحصائيات المبيعات"""
    # إحصائيات المبيعات الناجحة
    stats = db.execute_query("""
        SELECT COUNT(*), SUM(payment_amount) 
        FROM orders 
        WHERE status = 'completed' AND proxy_type != 'withdrawal'
    """)[0]
    
    # إحصائيات السحوبات
    withdrawals = db.execute_query("""
        SELECT COUNT(*), SUM(payment_amount)
        FROM orders 
        WHERE proxy_type = 'withdrawal' AND status = 'completed'
    """)[0]
    
    total_orders = stats[0] or 0
    total_revenue = stats[1] or 0.0
    withdrawal_count = withdrawals[0] or 0
    withdrawal_amount = withdrawals[1] or 0.0
    
    message = f"""📊 إحصائيات المبيعات

💰 المبيعات الناجحة:
📦 عدد الطلبات: {total_orders}
💵 إجمالي الإيرادات: <code>{total_revenue:.2f}$</code>

💸 السحوبات:
📋 عدد الطلبات: {withdrawal_count}
💰 إجمالي المسحوب: <code>{withdrawal_amount:.2f}$</code>

━━━━━━━━━━━━━━━
📈 صافي الربح: <code>{total_revenue - withdrawal_amount:.2f}$</code>"""
    
    await update.message.reply_text(message, parse_mode='HTML')

async def show_nonvoip_sales_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض إحصائيات مبيعات NonVoipUsNumber المفصلة"""
    try:
        if not NONVOIP_AVAILABLE:
            await update.message.reply_text("❌ وحدة NonVoip غير متاحة حالياً")
            return
        
        from non_voip_unified import NonVoipDB
        from datetime import datetime
        nvdb = NonVoipDB()
        
        # الحصول على جميع الطلبات
        all_orders = nvdb.get_all_orders() or []
        
        # الحصول على سعر الكريديت بالدولار
        credit_price = db.get_credit_price()
        
        # تصنيف الطلبات
        current_month = datetime.now().strftime('%Y-%m')
        
        # إحصائيات كاملة
        total_completed = [o for o in all_orders if o.get('status') == 'completed']
        total_pending = [o for o in all_orders if o.get('status') == 'pending']
        total_failed = [o for o in all_orders if o.get('status') in ['failed', 'cancelled', 'refunded']]
        
        # إحصائيات الشهر الحالي
        monthly_orders = [o for o in all_orders if o.get('created_at', '').startswith(current_month)]
        monthly_completed = [o for o in monthly_orders if o.get('status') == 'completed']
        monthly_pending = [o for o in monthly_orders if o.get('status') == 'pending']
        monthly_failed = [o for o in monthly_orders if o.get('status') in ['failed', 'cancelled', 'refunded']]
        
        # تصنيف حسب النوع الزمني (للطلبات المكتملة)
        def count_by_type(orders_list):
            short_term = [o for o in orders_list if o.get('type') == 'short_term']
            long_term = [o for o in orders_list if o.get('type') == 'long_term']
            three_days = [o for o in orders_list if o.get('type') == '3days']
            
            short_revenue = sum(float(o.get('sale_price', 0)) for o in short_term)
            long_revenue = sum(float(o.get('sale_price', 0)) for o in long_term)
            three_revenue = sum(float(o.get('sale_price', 0)) for o in three_days)
            
            return {
                'short_term': {'count': len(short_term), 'revenue': short_revenue},
                'long_term': {'count': len(long_term), 'revenue': long_revenue},
                '3days': {'count': len(three_days), 'revenue': three_revenue}
            }
        
        total_by_type = count_by_type(total_completed)
        monthly_by_type = count_by_type(monthly_completed)
        
        # حساب الإيرادات
        total_revenue_credits = sum(float(o.get('sale_price', 0)) for o in total_completed)
        total_revenue_dollars = total_revenue_credits * credit_price
        
        monthly_revenue_credits = sum(float(o.get('sale_price', 0)) for o in monthly_completed)
        monthly_revenue_dollars = monthly_revenue_credits * credit_price
        
        # حساب التكاليف والأرباح (التكلفة الأصلية من API)
        total_cost_dollars = sum(float(o.get('cost_price', 0)) for o in total_completed)
        total_profit_dollars = total_revenue_dollars - total_cost_dollars
        
        monthly_cost_dollars = sum(float(o.get('cost_price', 0)) for o in monthly_completed)
        monthly_profit_dollars = monthly_revenue_dollars - monthly_cost_dollars
        
        message = f"""📱 إحصائيات مبيعات NonVoipUsNumber

━━━ 📊 الإحصائيات الكاملة ━━━

📦 إجمالي الطلبات: {len(all_orders)}

✅ طلبات مكتملة: {len(total_completed)}
💰 إيرادات: <code>{total_revenue_credits:.2f}</code> كريديت (<code>${total_revenue_dollars:.2f}</code>)

  📱 Short-term: {total_by_type['short_term']['count']} طلب | {total_by_type['short_term']['revenue']:.2f} كريديت
  📱 Long-term: {total_by_type['long_term']['count']} طلب | {total_by_type['long_term']['revenue']:.2f} كريديت
  📱 3 Days: {total_by_type['3days']['count']} طلب | {total_by_type['3days']['revenue']:.2f} كريديت

⏳ طلبات معلقة: {len(total_pending)}
❌ طلبات فاشلة/ملغاة: {len(total_failed)}

💵 التكلفة: <code>${total_cost_dollars:.2f}</code>
💎 الأرباح: <code>${total_profit_dollars:.2f}</code>

━━━ 📅 إحصائيات الشهر الحالي ━━━

📦 طلبات الشهر: {len(monthly_orders)}

✅ طلبات مكتملة: {len(monthly_completed)}
💰 إيرادات: <code>{monthly_revenue_credits:.2f}</code> كريديت (<code>${monthly_revenue_dollars:.2f}</code>)

  📱 Short-term: {monthly_by_type['short_term']['count']} طلب | {monthly_by_type['short_term']['revenue']:.2f} كريديت
  📱 Long-term: {monthly_by_type['long_term']['count']} طلب | {monthly_by_type['long_term']['revenue']:.2f} كريديت
  📱 3 Days: {monthly_by_type['3days']['count']} طلب | {monthly_by_type['3days']['revenue']:.2f} كريديت

⏳ طلبات معلقة: {len(monthly_pending)}
❌ طلبات فاشلة/ملغاة: {len(monthly_failed)}

💵 التكلفة: <code>${monthly_cost_dollars:.2f}</code>
💎 الأرباح: <code>${monthly_profit_dollars:.2f}</code>"""
        
        await update.message.reply_text(message, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error showing NonVoip statistics: {e}")
        await update.message.reply_text(f"❌ حدث خطأ في عرض الإحصائيات: {str(e)}")

async def show_bot_channel_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض إعدادات قناة البوت"""
    channel = get_bot_channel()
    forced_sub = is_forced_subscription_enabled()
    
    channel_display = channel if channel else "غير محدد"
    status_emoji = "🟢" if forced_sub else "🔴"
    status_text = "مفعّل" if forced_sub else "معطّل"
    
    text = f"""
<b>📢 إعدادات قناة البوت</b>

<b>📋 التعليمات:</b>
1️⃣ أضف البوت كـ <b>آدمن</b> في قناتك
2️⃣ القناة يجب أن تكون <b>عامة (Public)</b>
3️⃣ أرسل رابط القناة أو اليوزرنيم (مثال: @channel أو https://t.me/channel)

<b>📍 القناة الحالية:</b> {channel_display}
<b>🔐 الاشتراك الإجباري:</b> {status_emoji} {status_text}

⚠️ <b>ملاحظة:</b> عند تفعيل الاشتراك الإجباري، لن يتمكن المستخدمون من استخدام البوت إلا بعد الاشتراك في القناة.
"""
    
    keyboard = [
        [InlineKeyboardButton("📝 تغيير القناة", callback_data="admin_set_channel")],
        [InlineKeyboardButton(
            f"{'🔴 تعطيل' if forced_sub else '🟢 تفعيل'} الاشتراك الإجباري",
            callback_data="admin_toggle_forced_sub"
        )],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin_settings")]
    ]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def handle_channel_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة callbacks إعدادات القناة"""
    query = update.callback_query
    data = query.data
    
    if data == "admin_set_channel":
        await query.answer()
        context.user_data['waiting_bot_channel'] = True
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="cancel_channel_setup")]]
        await query.edit_message_text(
            "📢 أرسل رابط القناة أو اليوزرنيم:\n\n"
            "مثال:\n"
            "• @mychannel\n"
            "• https://t.me/mychannel",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data == "admin_toggle_forced_sub":
        channel = get_bot_channel()
        if not channel:
            await query.answer("❌ يجب تحديد قناة أولاً!", show_alert=True)
            return
        
        current = is_forced_subscription_enabled()
        set_forced_subscription(not current)
        await query.answer(f"تم {'تعطيل' if current else 'تفعيل'} الاشتراك الإجباري")
        
        # Refresh menu
        forced_sub = not current
        channel_display = channel if channel else "غير محدد"
        status_emoji = "🟢" if forced_sub else "🔴"
        status_text = "مفعّل" if forced_sub else "معطّل"
        
        text = f"""
<b>📢 إعدادات قناة البوت</b>

<b>📋 التعليمات:</b>
1️⃣ أضف البوت كـ <b>آدمن</b> في قناتك
2️⃣ القناة يجب أن تكون <b>عامة (Public)</b>
3️⃣ أرسل رابط القناة أو اليوزرنيم (مثال: @channel أو https://t.me/channel)

<b>📍 القناة الحالية:</b> {channel_display}
<b>🔐 الاشتراك الإجباري:</b> {status_emoji} {status_text}

⚠️ <b>ملاحظة:</b> عند تفعيل الاشتراك الإجباري، لن يتمكن المستخدمون من استخدام البوت إلا بعد الاشتراك في القناة.
"""
        
        keyboard = [
            [InlineKeyboardButton("📝 تغيير القناة", callback_data="admin_set_channel")],
            [InlineKeyboardButton(
                f"{'🔴 تعطيل' if forced_sub else '🟢 تفعيل'} الاشتراك الإجباري",
                callback_data="admin_toggle_forced_sub"
            )],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin_settings")]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    
    elif data == "cancel_channel_setup":
        await query.answer()
        context.user_data.pop('waiting_bot_channel', None)
        await query.edit_message_text("❌ تم إلغاء تغيير القناة")
    
    elif data == "back_to_admin_settings":
        await query.answer()
        await query.message.delete()


async def handle_bot_channel_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """معالجة إدخال قناة البوت"""
    if not context.user_data.get('waiting_bot_channel'):
        return False
    
    text = update.message.text.strip()
    context.user_data.pop('waiting_bot_channel', None)
    
    # Extract channel username from link or direct input
    channel = text
    if channel.startswith('https://t.me/'):
        channel = '@' + channel.replace('https://t.me/', '').split('/')[0]
    elif channel.startswith('t.me/'):
        channel = '@' + channel.replace('t.me/', '').split('/')[0]
    elif not channel.startswith('@'):
        channel = '@' + channel
    
    # Verify bot is admin in the channel
    try:
        chat = await context.bot.get_chat(channel)
        bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
        
        if bot_member.status not in ['administrator', 'creator']:
            await update.message.reply_text(
                "❌ البوت ليس آدمن في هذه القناة!\n\n"
                "📋 الخطوات:\n"
                "1. أضف البوت للقناة\n"
                "2. اجعله آدمن\n"
                "3. أعد المحاولة"
            )
            return True
        
        set_bot_channel(channel)
        await update.message.reply_text(
            f"✅ تم تعيين القناة بنجاح: {channel}\n\n"
            f"📢 اسم القناة: {chat.title}"
        )
    except Exception as e:
        logger.error(f"Error setting channel: {e}")
        await update.message.reply_text(
            "❌ تعذر الوصول للقناة!\n\n"
            "تأكد من:\n"
            "• القناة عامة (Public)\n"
            "• البوت آدمن في القناة\n"
            "• الرابط صحيح"
        )
    return True


async def check_user_subscription(bot, user_id: int) -> tuple:
    """
    التحقق من اشتراك المستخدم في القناة
    Returns: (is_subscribed: bool, channel: str or None)
    """
    if not is_forced_subscription_enabled():
        return True, None
    
    channel = get_bot_channel()
    if not channel:
        return True, None
    
    try:
        member = await bot.get_chat_member(channel, user_id)
        is_subscribed = member.status in ['member', 'administrator', 'creator']
        # Update database
        update_user_subscription_status(user_id, is_subscribed)
        return is_subscribed, channel
    except Exception as e:
        logger.error(f"Error checking subscription for user {user_id}: {e}")
        # If error, allow access to avoid blocking users due to API issues
        return True, channel


async def database_management_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """قائمة إدارة قاعدة البيانات"""
    keyboard = [
        [KeyboardButton("🔍 فحص قاعدة البيانات")],
        [KeyboardButton("📊 تحميل قاعدة البيانات")],
        [KeyboardButton("🗑️ تفريغ قاعدة البيانات")],
        [KeyboardButton("🔙 العودة للقائمة الرئيسية")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    message_text = "🗃️ إدارة قاعدة البيانات\nاختر العملية المطلوبة:"
    
    # التعامل مع كلا الحالتين: رسالة عادية أو callback
    if update.message:
        await update.message.reply_text(message_text, reply_markup=reply_markup)
    else:
        # إذا كانت من callback، أرسل رسالة جديدة
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message_text,
            reply_markup=reply_markup
        )

async def database_export_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """قائمة تصدير قاعدة البيانات"""
    keyboard = [
        [KeyboardButton("📊 Excel"), KeyboardButton("📄 CSV")],
        [KeyboardButton("🗃️ SQLite Database"), KeyboardButton("🔧 Export Mix")],
        [KeyboardButton("🔙 العودة للقائمة الرئيسية")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    message_text = "📊 تحميل قاعدة البيانات\nاختر صيغة التصدير:"
    
    # التعامل مع كلا الحالتين: رسالة عادية أو callback
    if update.message:
        await update.message.reply_text(message_text, reply_markup=reply_markup)
    else:
        # إذا كانت من callback، أرسل رسالة جديدة
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message_text,
            reply_markup=reply_markup
        )

async def return_to_admin_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """العودة للقائمة الرئيسية للأدمن"""
    await restore_admin_keyboard(context, update.effective_chat.id, "🔧 لوحة الأدمن الرئيسية\nاختر الخدمة المطلوبة:")

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الرسائل النصية"""
    # التحقق من وجود رسالة نصية
    if not update.message or not update.message.text:
        return
    # التحقق من إلغاء msg_options عند أي إدخال لا يبدأ بـ /msg
    await check_and_clear_msg_options(update, context)
    
    # فحص حالة الحظر وتتبع النقرات المتكررة
    ban_check_result = await check_user_ban_and_track_clicks(update, context)
    if ban_check_result:
        # المستخدم محظور أو تم تطبيق إجراء - إيقاف المعالجة
        return
        
    try:
        text = update.message.text
        user_id = update.effective_user.id
        
        # فحص طول الرسالة لتجنب المشاكل
        if len(text) > 1000:  # رسالة طويلة جداً
            await update.message.reply_text(
                "⚠️ الرسالة طويلة جداً. يرجى إرسال رسالة أقصر.",
                reply_markup=ReplyKeyboardRemove()
            )
            return
        
        # فحص الرسائل المكررة أو المشبوهة
        if len(text) > 10 and text.count(text[0]) > len(text) * 0.8:  # رسالة مكررة
            logger.warning(f"Suspicious repeated message from user {user_id}")
            await update.message.reply_text(
                "⚠️ يرجى عدم إرسال رسائل مكررة.",
                reply_markup=ReplyKeyboardRemove()
            )
            return
        
        language = get_user_language(user_id)
        is_admin = context.user_data.get('is_admin', False) or user_id in ADMIN_IDS
        
        # التحقق من حالة تشغيل البوت - إذا كان متوقفاً، تجاهل رسائل المستخدمين العاديين
        if not is_bot_running() and not is_admin:
            await update.message.reply_text(
                "⚠️ البوت متوقف حالياً للصيانة. يرجى المحاولة لاحقاً." if language == 'ar' else "⚠️ Bot is currently stopped for maintenance. Please try again later."
            )
            return
    except Exception as e:
        logger.error(f"Error in handle_text_messages initialization: {e}")
        try:
            await update.message.reply_text("⚠️ حدث خطأ. استخدم /start لإعادة التشغيل.")
        except:
            pass
        return
    
    try:
        # معالجة أمر حذف الرسالة الجماعي (للآدمن فقط)
        if is_admin and context.user_data.get('delete_message_mode') and update.message.reply_to_message:
            if text.lower().strip() == 'delete':
                await handle_delete_message_broadcast(update, context)
                return
        
        # معالجة إدخال الرصيد المخصص للأدمن
        if is_admin and context.user_data.get('awaiting_custom_balance'):
            await handle_custom_balance_input(update, context)
            return
        
        # معالجة إدخال النقاط (إضافة/خصم)
        if is_admin and context.user_data.get('awaiting_points_input'):
            await handle_points_input(update, context)
            return
        
        # معالجة إدخال بيانات CoinEx API
        if is_admin and context.user_data.get('coinex_waiting_for'):
            await handle_coinex_input(update, context)
            return
        
        # معالجة إدخالات إدارة Luxury Support (السعر ومفتاح API)
        if is_admin and (context.user_data.get('waiting_lx_price_daily') or context.user_data.get('waiting_lx_price_hourly') or context.user_data.get('waiting_lx_apikey')):
            handled = await handle_luxury_admin_input(update, context)
            if handled:
                return
        
        # معالجة اختيارات inline query لـ Luxury Support (الدول، الولايات، المدن)
        if LUXURY_AVAILABLE and text.startswith("/select_"):
            handled = await handle_luxury_inline_selection(update, context)
            if handled:
                return
        
        # معالجة رسائل البث الفردية للمستخدم (نصية أو صورة)
        if is_admin and context.user_data.get('broadcast_type') and context.user_data.get('target_user_id'):
            await handle_single_user_broadcast_message(update, context)
            return
        
        # التحقق من الأوامر الخاصة للتنظيف وإعادة التعيين
        if text.lower() in ['/reset', '🔄 إعادة تعيين', 'reset']:
            await handle_reset_command(update, context)
            return
        elif text.lower() in ['/cleanup', '🧹 تنظيف', 'cleanup']:
            await handle_cleanup_command(update, context)
            return
        elif text.lower() in ['/status', '📊 الحالة', 'status']:
            await handle_status_command(update, context)
            return
        elif text.lower() in ['إلغاء', 'cancel', 'خروج', 'exit', 'stop']:
            # تنظيف العمليات المعلقة والعودة للقائمة الرئيسية
            is_admin = context.user_data.get('is_admin', False) or user_id in ACTIVE_ADMINS
            clean_user_data_preserve_admin(context)
            
            if is_admin:
                await update.message.reply_text("✅ تم إلغاء العملية")
                await restore_admin_keyboard(context, update.effective_chat.id, "🔄 العودة للقائمة الرئيسية")
            else:
                await update.message.reply_text("✅ تم إلغاء العملية والعودة للقائمة الرئيسية")
                await start(update, context)
            return
        
        # معالجة إدخال كمية الخدمات الديناميكية
        if context.user_data.get('awaiting_quantity'):
            handled = await handle_manual_quantity_input(update, context)
            if handled:
                return
        
        # معالجة إدخال كمية البروكسي الستاتيك
        if context.user_data.get('waiting_for_static_quantity'):
            await handle_static_quantity_input(update, context)
            return
        
        # التحقق من حالة انتظار رسالة مباشرة من الأدمن (للمعالجة المباشرة)
        if is_admin and context.user_data.get('waiting_for_direct_admin_message'):
            order_id = context.user_data.get('processing_order_id')
            if order_id:
                try:
                    # استدعاء دالة إرسال البروكسي مع الرسالة المخصصة
                    await send_proxy_with_custom_message_direct(update, context, text)
                    
                    # رسالة تأكيد للأدمن
                    await update.message.reply_text(
                        f"✅ تم إرسال البروكسي والرسالة للمستخدم بنجاح!\n\n🆔 معرف الطلب: {order_id}",
                        parse_mode='HTML'
                    )
                    
                    # إعادة تفعيل كيبورد الأدمن
                    await restore_admin_keyboard(context, update.effective_chat.id)
                    
                except Exception as e:
                    logger.error(f"خطأ في إرسال البروكسي: {e}")
                    await update.message.reply_text(
                        f"❌ حدث خطأ أثناء إرسال البروكسي\n\nالخطأ: {str(e)}"
                    )
                return
        
        # التحقق من حالة انتظار رسالة أدمن عادية
        if is_admin and context.user_data.get('waiting_for_admin_message'):
            try:
                await handle_admin_message_for_proxy(update, context)
                return
            except Exception as e:
                logger.error(f"خطأ في معالجة رسالة الأدمن المخصصة: {e}")
                await update.message.reply_text(
                    f"❌ حدث خطأ أثناء معالجة رسالتك\n\nالخطأ: {str(e)}"
                )
                await restore_admin_keyboard(context, update.effective_chat.id)
                return
        
        # أزرار الأدمن
        if is_admin:
            # القوائم الرئيسية للأدمن
            if text in ["📋 إدارة الطلبات", "📋 Manage Orders"]:
                await handle_admin_orders_menu(update, context)
            elif text in ["💰 إدارة الأموال", "💰 Manage Finances"]:
                await handle_admin_money_menu(update, context)
            elif text in ["👥 الإحالات", "👥 Referrals"]:
                await handle_admin_referrals_menu(update, context)
            elif text in ["🌐 إدارة الخدمات", "🌐 إدارة البروكسيات", "🌐 Manage Services"]:
                await handle_manage_proxies(update, context)
            elif text in ["⚙️ الإعدادات", "⚙️ Settings"]:
                await handle_admin_settings_menu(update, context)
            elif text in ["🚪 تسجيل الخروج", "🚪 Logout"]:
                await admin_logout_confirmation(update, context)
            
            # إدارة الطلبات
            elif text in ["📋 الطلبات المعلقة", "📋 Pending Orders"]:
                await show_pending_orders_admin(update, context)
            elif text in ["🔍 استعلام عن طلب", "🔍 Order Inquiry"]:
                await admin_order_inquiry(update, context)
            elif text in ["🗑️ حذف الطلبات المعالجة", "🗑️ Delete Processed Orders"]:
                await delete_processed_orders(update, context)
            
            # إدارة الأموال
            elif text in ["📊 إحصائيات المبيعات", "📊 Sales Statistics"]:
                await show_sales_statistics(update, context)
            elif text in ["📱 إحصائيات NonVoipUsNumber", "📱 NonVoipUsNumber Statistics"]:
                await show_nonvoip_sales_statistics(update, context)
            elif text in ["💲 إدارة الأسعار", "💲 Manage Prices"]:
                await manage_prices_menu(update, context)
            elif text in ["💰 تعديل سعر النقطة", "💰 Set Credit Price"]:
                await set_credit_price(update, context)
            elif text in ["📱 تعديل سعر رقم Non-Voip", "📱 Set Non-Voip Price"]:
                await set_nonvoip_price(update, context)
            elif text in ["🌐 تعديل سعر سوكس يومي", "🌐 Set Daily Socks Price"]:
                await set_luxury_price(update, context)
            
            # إدارة الإحالات
            elif text in ["💵 تحديد مبلغ الإحالة", "💵 Set Referral Amount"]:
                await set_referral_amount(update, context)
            elif text in ["📊 إحصائيات المستخدمين", "📊 User Statistics"]:
                await show_user_statistics(update, context)
            elif text in ["🗑️ إعادة تعيين رصيد المستخدم", "🗑️ Reset User Balance"]:
                await reset_user_balance(update, context)
            
            # إعدادات الأدمن
            elif text in ["🌐 تغيير اللغة", "🌐 Change Language"]:
                await handle_settings(update, context)
            elif text in ["🔐 تغيير كلمة المرور", "🔐 Change Password"]:
                await change_admin_password(update, context)
            elif text in ["🔔 إدارة الإشعارات", "🔔 Manage Notifications"]:
                await set_quiet_hours(update, context)
            elif text in ["🗃️ إدارة قاعدة البيانات", "🗃️ Database Management"]:
                await database_management_menu(update, context)
            elif text in ["📢 قناة البوت", "📢 Bot Channel"]:
                await show_bot_channel_settings(update, context)
            
            # معالجة إدارة قاعدة البيانات
            elif text == "🔍 فحص قاعدة البيانات":
                await validate_database_status(update, context)
            elif text in ["📊 تحميل قاعدة البيانات", "📊 Download Database"]:
                await database_export_menu(update, context)
            elif text in ["🗑️ تفريغ قاعدة البيانات", "🗑️ Clear Database"]:
                await confirm_database_clear(update, context)
            
            # معالجة تصدير قاعدة البيانات (نفس الأسماء في اللغتين)
            elif text in ["📊 Excel"]:
                await export_database_excel(update, context)
            elif text in ["📄 CSV"]:
                await export_database_csv(update, context)
            elif text in ["🗃️ SQLite Database"]:
                await export_database_sqlite(update, context)
            elif text in ["🔧 Export Mix"]:
                await export_database_json_mix(update, context)
            
            # العودة للقائمة الرئيسية
            elif text in ["🔙 العودة للقائمة الرئيسية", "🔙 Back to Main Menu"]:
                user_language = get_user_language(update.effective_user.id)
                msg = "🔧 لوحة الأدمن الرئيسية\nاختر الخدمة المطلوبة:" if user_language == 'ar' else "🔧 Main Admin Panel\nChoose the required service:"
                await restore_admin_keyboard(context, update.effective_chat.id, msg)
            
            # إذا وصلنا هنا فالنص لا يتطابق مع أي زر أدمن معروف
            # لا نفعل شيئاً - تماماً كما في proxy_bot.py
            return
        
        # معالجة جميع الأزرار الديناميكية الجذرية (بما فيها static_proxy و socks_proxy)
        # جميع الأزرار الآن قابلة للتعديل والحذف والإخفاء
        try:
            from dynamic_buttons import dynamic_buttons_manager
            dynamic_root_buttons = dynamic_buttons_manager.get_root_buttons(language, enabled_only=True)
            
            for btn in dynamic_root_buttons:
                # تخطي الأزرار المخفية
                if btn.get('is_hidden', False):
                    continue
                    
                icon = btn.get('icon', '')
                btn_text_db = btn.get('text', '')
                btn_text = f"{icon} {btn_text_db}".strip() if icon else btn_text_db
                
                if text == btn_text or text == btn_text_db:
                    await show_dynamic_menu_by_key(update, context, btn.get('button_key'))
                    return
        except Exception as e:
            logger.error(f"Error checking dynamic buttons: {e}")
        
        # التحقق من الأزرار الافتراضية (للتوافق مع الإصدارات القديمة)
        if text == MESSAGES[language]['main_menu_buttons'][0]:  # طلب بروكسي ستاتيك (الافتراضي)
            await show_dynamic_menu_by_key(update, context, 'static_proxy')
            return
        elif text == MESSAGES[language]['main_menu_buttons'][1]:  # طلب بروكسي سوكس (الافتراضي)
            await show_dynamic_menu_by_key(update, context, 'socks_proxy')
            return
        elif text == MESSAGES[language]['main_menu_buttons'][2]:  # تجربة ستاتيك مجانا
            await handle_free_static_trial(update, context)
            return
        elif text == MESSAGES[language]['main_menu_buttons'][3]:  # ملفي الشخصي
            await handle_profile_menu(update, context)
            return
        elif text == MESSAGES[language]['main_menu_buttons'][4]:  # طلباتي
            await handle_my_orders_menu(update, context)
            return
        elif text == MESSAGES[language]['main_menu_buttons'][5]:  # الإعدادات
            await handle_settings(update, context)
            return
        elif text == MESSAGES[language]['main_menu_buttons'][6]:  # شراء أرقام
            await handle_buy_numbers(update, context)
            return
        elif text == MESSAGES[language]['main_menu_buttons'][7]:  # سعر الصرف
            await show_exchange_rate_message(update, context)
            return
        elif text == MESSAGES[language]['main_menu_buttons'][8]:  # لمحة عن خدماتنا
            await show_services_message(update, context)
            return
        elif text == MESSAGES[language]['main_menu_buttons'][9]:  # سوكس يومي
            await handle_daily_socks_menu(update, context)
            return
        
        # معالجة أزرار قائمة الملف الشخصي
        if text == MESSAGES[language]['profile_menu_buttons'][0]:  # معلومات الملف الشخصي
            await handle_profile_info(update, context)
            return
        elif text == MESSAGES[language]['profile_menu_buttons'][1]:  # الرصيد
            await handle_balance_menu(update, context)
            return
        elif text == MESSAGES[language]['profile_menu_buttons'][2]:  # الإحالات
            await handle_referrals(update, context)
            return
        elif text == MESSAGES[language]['profile_menu_buttons'][3]:  # الدعم
            await handle_support(update, context)
            return
        elif text == MESSAGES[language]['profile_menu_buttons'][4]:  # رجوع
            await handle_back_to_main_menu(update, context)
            return
        
        # معالجة أزرار قائمة الرصيد الفرعية
        if text == MESSAGES[language]['balance_menu_buttons'][0]:  # شحن رصيد
            await handle_recharge_balance(update, context)
            return
        elif text == MESSAGES[language]['balance_menu_buttons'][1]:  # رصيدي  
            await handle_my_balance(update, context)
            return
        elif text == MESSAGES[language]['balance_menu_buttons'][2]:  # رجوع للملف الشخصي
            await handle_back_to_profile(update, context)
            return
        
        # معالجة إدخال مبلغ الشحن
        if context.user_data.get('waiting_for_recharge_amount'):
            await handle_recharge_amount_input(update, context)
            return
        
        # معالجة إثبات دفع الشحن
        if context.user_data.get('waiting_for_recharge_proof'):
            await handle_recharge_payment_proof(update, context)
            return
        
        # معالجة أزرار الأدمن
        if is_admin:
            if text in ["📝 تحرير رسالة الخدمات", "📝 Edit Services Message"]:
                await handle_edit_services_message(update, context)
                return
            
            if text in ["💱 تحرير رسالة سعر الصرف", "💱 Edit Exchange Rate Message"]:
                await handle_edit_exchange_rate_message(update, context)
                return
                
        # إذا وصلنا هنا فالنص لا يتطابق مع أي زر معروف
        # لا نفعل شيئاً - تماماً كما في proxy_bot.py
        
    except Exception as e:
        logger.error(f"Error in handle_text_messages: {e}")
        print(f"❌ خطأ في معالجة رسالة نصية من المستخدم {user_id}: {e}")
        print(f"   النص: {text}")
        
        # معالجة الخطأ فقط في حالة حدوث استثناء حقيقي
        try:
            user_id = update.effective_user.id
            language = get_user_language(user_id)
            
            if context.user_data.get('is_admin') or user_id in ACTIVE_ADMINS:
                error_details = f"❌ حدث خطأ في معالجة الرسالة النصية\n\n🔍 التفاصيل التقنية:\n• النص المُرسل: {text[:100]}...\n• سبب الخطأ: {str(e)[:200]}...\n\n🔧 تم إعادة توجيهك للقائمة الرئيسية"
                await restore_admin_keyboard(context, update.effective_chat.id, error_details)
            else:
                # إنشاء الكيبورد من جديد بدلاً من إزالته
                reply_markup = create_main_user_keyboard(language)
                
                if language == 'ar':
                    await update.message.reply_text(
                        "❌ حدث خطأ في معالجة طلبك.\n\n🔄 تم إعادة إنشاء الأزرار. يرجى المحاولة مرة أخرى:",
                        reply_markup=reply_markup
                    )
                else:
                    await update.message.reply_text(
                        "❌ An error occurred while processing your request.\n\n🔄 Buttons have been recreated. Please try again:",
                        reply_markup=reply_markup
                    )
        except Exception as redirect_error:
            logger.error(f"Failed to redirect user after text message error: {redirect_error}")
            # محاولة أخيرة بسيطة
            try:
                await context.bot.send_message(
                    user_id,
                    "❌ حدث خطأ. يرجى استخدام /start لإعادة تشغيل البوت"
                )
            except:
                pass
        
        # تنظيف البيانات المؤقتة في حالة الخطأ فقط
        try:
            clean_user_data_preserve_admin(context)
        except:
            pass

async def handle_photo_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الصور المرسلة من المستخدمين"""
    # فحص حالة الحظر وتتبع النقرات المتكررة
    ban_check_result = await check_user_ban_and_track_clicks(update, context)
    if ban_check_result:
        # المستخدم محظور أو تم تطبيق إجراء - إيقاف المعالجة
        return
    
    try:
        user_id = update.effective_user.id
        language = get_user_language(user_id)
        
        # معالجة إثبات دفع الشحن
        if context.user_data.get('waiting_for_recharge_proof'):
            await handle_recharge_payment_proof(update, context)
            return
        
        # معالجة إثبات الدفع العادي
        if context.user_data.get('waiting_for_payment_proof'):
            # تطبيق المنطق الموجود في handle_text_messages للصور
            file_id = update.message.photo[-1].file_id
            context.user_data['payment_proof'] = f"photo:{file_id}"
            
            # متابعة المعالجة العادية كما في handle_text_messages
            await handle_payment_proof_processing(update, context)
            return
        
        # إذا لم تكن هناك حالة انتظار محددة، إرسال رسالة توضيحية
        if language == 'ar':
            await update.message.reply_text("📷 تم استلام الصورة. إذا كنت تريد إرسال إثبات دفع، يرجى اختيار الخدمة أولاً.")
        else:
            await update.message.reply_text("📷 Image received. If you want to send payment proof, please select the service first.")
            
    except Exception as e:
        logger.error(f"Error in handle_photo_messages: {e}")
        print(f"❌ خطأ في معالجة صورة من المستخدم {user_id}: {e}")

async def handle_document_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة المستندات المرسلة من المستخدمين"""
    # فحص حالة الحظر وتتبع النقرات المتكررة
    ban_check_result = await check_user_ban_and_track_clicks(update, context)
    if ban_check_result:
        # المستخدم محظور أو تم تطبيق إجراء - إيقاف المعالجة
        return
    
    try:
        user_id = update.effective_user.id
        language = get_user_language(user_id)
        
        # إرسال رسالة توضيحية للمستندات
        if language == 'ar':
            await update.message.reply_text("📄 تم استلام المستند. لإثبات الدفع، يرجى إرسال صورة بدلاً من مستند.")
        else:
            await update.message.reply_text("📄 Document received. For payment proof, please send an image instead of a document.")
            
    except Exception as e:
        logger.error(f"Error in handle_document_messages: {e}")
        print(f"❌ خطأ في معالجة مستند من المستخدم {user_id}: {e}")

async def validate_database_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض تقرير فحص سلامة قاعدة البيانات مع معلومات المساحة"""
    import os
    import shutil
    
    try:
        # إجراء فحص سلامة قاعدة البيانات
        validation_results = db.validate_database_integrity()
        
        # تكوين الرسالة
        status_icon = "✅" if all([
            validation_results['database_accessible'],
            validation_results['tables_exist'], 
            validation_results['data_integrity']
        ]) else "❌"
        
        message = f"""{status_icon} <b>تقرير فحص قاعدة البيانات</b>

🔍 <b>حالة قاعدة البيانات:</b>
{"✅" if validation_results['database_accessible'] else "❌"} إمكانية الوصول: {"متاحة" if validation_results['database_accessible'] else "غير متاحة"}
{"✅" if validation_results['tables_exist'] else "❌"} الجداول: {"موجودة" if validation_results['tables_exist'] else "مفقودة"}
{"✅" if validation_results['data_integrity'] else "❌"} سلامة البيانات: {"سليمة" if validation_results['data_integrity'] else "تالفة"}

"""
        
        if validation_results['errors']:
            message += f"⚠️ <b>الأخطاء المكتشفة:</b>\n"
            for i, error in enumerate(validation_results['errors'][:5], 1):  # عرض أول 5 أخطاء
                message += f"{i}. {error}\n"
            
            if len(validation_results['errors']) > 5:
                message += f"... و {len(validation_results['errors']) - 5} خطأ إضافي\n"
        else:
            message += "🎉 <b>لا توجد أخطاء!</b> قاعدة البيانات تعمل بشكل طبيعي"
        
        message += f"\n📊 <b>إحصائيات سريعة:</b>"
        
        try:
            # إحصائيات سريعة
            stats = {
                'users': db.execute_query("SELECT COUNT(*) FROM users"),
                'orders': db.execute_query("SELECT COUNT(*) FROM orders"),
                'pending_orders': db.execute_query("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
            }
            
            message += f"""
👥 المستخدمين: {stats['users'][0][0] if stats['users'] else 'غير معروف'}
📦 إجمالي الطلبات: {stats['orders'][0][0] if stats['orders'] else 'غير معروف'}
⏳ الطلبات المعلقة: {stats['pending_orders'][0][0] if stats['pending_orders'] else 'غير معروف'}"""
        except:
            message += "\n⚠️ تعذر الحصول على الإحصائيات"
        
        # إضافة معلومات المساحة
        try:
            message += "\n\n💾 <b>معلومات المساحة:</b>"
            
            # حجم قاعدة البيانات
            if os.path.exists(DATABASE_FILE):
                db_size_bytes = os.path.getsize(DATABASE_FILE)
                db_size_mb = db_size_bytes / (1024 * 1024)
                message += f"\n📁 حجم قاعدة البيانات: <code>{db_size_mb:.2f} MB</code>"
            
            # معلومات القرص
            disk_info = shutil.disk_usage('/')
            total_gb = disk_info.total / (1024**3)
            used_gb = disk_info.used / (1024**3)
            free_gb = disk_info.free / (1024**3)
            used_percent = (disk_info.used / disk_info.total) * 100
            
            message += f"""
🖥️ <b>معلومات القرص:</b>
📊 إجمالي المساحة: <code>{total_gb:.2f} GB</code>
✅ المساحة المتاحة: <code>{free_gb:.2f} GB</code>
📈 المساحة المستخدمة: <code>{used_gb:.2f} GB ({used_percent:.1f}%)</code>"""
            
            # تحذير إذا كانت المساحة منخفضة
            if used_percent > 90:
                message += "\n⚠️ <b>تنبيه:</b> المساحة المتاحة منخفضة جداً!"
            elif used_percent > 80:
                message += "\n⚠️ <b>تنبيه:</b> المساحة المتاحة قليلة"
                
        except Exception as space_error:
            logger.error(f"Error getting disk space info: {space_error}")
        
        # إنشاء أزرار الإجراءات
        keyboard = []
        
        if not all([validation_results['database_accessible'], validation_results['tables_exist']]):
            keyboard.append([InlineKeyboardButton("🔧 إصلاح قاعدة البيانات", callback_data="repair_database")])
        
        keyboard.extend([
            [InlineKeyboardButton("🔄 إعادة الفحص", callback_data="validate_database")],
            [InlineKeyboardButton("📊 تحميل قاعدة البيانات", callback_data="admin_db_export")],
            [InlineKeyboardButton("🔙 العودة", callback_data="admin_database_menu")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
        else:
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
            
    except Exception as e:
        error_message = f"""❌ <b>فشل فحص قاعدة البيانات</b>

حدث خطأ أثناء محاولة فحص قاعدة البيانات:
<code>{str(e)}</code>

هذا قد يشير إلى مشكلة خطيرة في النظام."""
        
        keyboard = [
            [InlineKeyboardButton("🔄 إعادة المحاولة", callback_data="validate_database")],
            [InlineKeyboardButton("🔙 العودة", callback_data="admin_database_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(error_message, reply_markup=reply_markup, parse_mode='HTML')
        else:
            await update.message.reply_text(error_message, reply_markup=reply_markup, parse_mode='HTML')

# ==== الوظائف المفقودة ====

async def manage_prices_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """قائمة إدارة الأسعار"""
    keyboard = [
        [KeyboardButton("💰 تعديل سعر النقطة")],
        [KeyboardButton("📱 تعديل سعر رقم Non-Voip")],
        [KeyboardButton("🌐 تعديل سعر سوكس يومي")],
        [KeyboardButton("🔙 العودة للقائمة الرئيسية")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "💲 إدارة الأسعار\nاختر نوع الخدمة لتعديل أسعارها:",
        reply_markup=reply_markup
    )

async def set_referral_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """تحديد نسبة الإحالة المئوية"""
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_referral_amount")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "💵 تحديد نسبة الإحالة المئوية\n\nيرجى إرسال النسبة المئوية (مثال: <code>10</code> للحصول على 10%):",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    return REFERRAL_AMOUNT

async def handle_referral_amount_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة تحديث نسبة الإحالة المئوية"""

    
    try:
        percentage = float(update.message.text)
        
        # التحقق من أن النسبة بين 0 و 100
        if percentage < 0 or percentage > 100:
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_referral_amount")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("❌ يرجى إرسال نسبة بين 0 و 100!", reply_markup=reply_markup)
            return REFERRAL_AMOUNT
        
        # حفظ في قاعدة البيانات
        db.execute_query(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            ("referral_percentage", str(percentage))
        )
        
        await update.message.reply_text(f"✅ تم تحديث نسبة الإحالة إلى {percentage}%\n\n📢 سيتم إشعار جميع المستخدمين بالتحديث...", parse_mode='HTML')
        
        # إشعار جميع المستخدمين بالتحديث
        await broadcast_referral_update(context, percentage)
        
        # إعادة تفعيل كيبورد الأدمن الرئيسي
        await restore_admin_keyboard(context, update.effective_chat.id, f"✅ تم تحديث نسبة الإحالة إلى {percentage}% بنجاح")
        
    except ValueError:
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_referral_amount")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("❌ يرجى إرسال رقم صحيح للنسبة المئوية!", reply_markup=reply_markup)
        return REFERRAL_AMOUNT
    
    return ConversationHandler.END

async def set_credit_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """تحديد سعر النقطة الواحدة"""
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_credit_price")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "💰 تعديل سعر النقطة الواحدة\n\nيرجى إرسال السعر الجديد للنقطة الواحدة (مثال: <code>0.1</code>):",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    return SET_POINT_PRICE

async def handle_credit_price_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة تحديث سعر النقطة الواحدة"""
    
    try:
        price = float(update.message.text)
        
        # التحقق من أن السعر إيجابي
        if price <= 0:
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_credit_price")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("❌ يرجى إرسال سعر إيجابي!", reply_markup=reply_markup)
            return SET_POINT_PRICE
        
        # حفظ في قاعدة البيانات
        db.execute_query(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            ("credit_price", str(price))
        )
        
        await update.message.reply_text(f"✅ تم تحديث سعر النقطة الواحدة إلى ${price}", parse_mode='HTML')
        
        # إعادة تفعيل كيبورد الأدمن الرئيسي
        await restore_admin_keyboard(context, update.effective_chat.id, f"✅ تم تحديث سعر النقطة الواحدة إلى ${price} بنجاح")
        
    except ValueError:
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_credit_price")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("❌ يرجى إرسال رقم صحيح للسعر!", reply_markup=reply_markup)
        return SET_POINT_PRICE
    
    return ConversationHandler.END

async def set_quiet_hours(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إدارة الإشعارات"""
    # الحصول على الإعداد الحالي لساعات الهدوء
    current_setting = db.execute_query("SELECT value FROM settings WHERE key = 'quiet_hours'")
    current = current_setting[0][0] if current_setting else "24h"
    
    # الحصول على حالة إشعارات انخفاض رصيد NonVoip
    nonvoip_notif_setting = db.execute_query("SELECT value FROM settings WHERE key = 'nonvoip_balance_notifications_enabled'")
    nonvoip_notif_enabled = nonvoip_notif_setting[0][0] == '1' if nonvoip_notif_setting else True
    
    keyboard = [
        [InlineKeyboardButton(f"{'✅' if current == '8_18' else '🔕'} 08:00 - 18:00", callback_data="quiet_8_18")],
        [InlineKeyboardButton(f"{'✅' if current == '22_6' else '🔕'} 22:00 - 06:00", callback_data="quiet_22_6")],
        [InlineKeyboardButton(f"{'✅' if current == '12_14' else '🔕'} 12:00 - 14:00", callback_data="quiet_12_14")],
        [InlineKeyboardButton(f"{'✅' if current == '20_22' else '🔕'} 20:00 - 22:00", callback_data="quiet_20_22")],
        [InlineKeyboardButton(f"{'✅' if current == '24h' else '🔊'} 24 ساعة مع صوت", callback_data="quiet_24h")],
        [InlineKeyboardButton("━━━━━━━━━━━━━━━━━━", callback_data="separator")],
        [InlineKeyboardButton(
            f"{'🔔 مفعّلة' if nonvoip_notif_enabled else '🔕 معطّلة'} إشعارات انخفاض رصيد NonVoip", 
            callback_data="toggle_nonvoip_balance_notif"
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔔 إدارة الإشعارات\n\n"
        "⏰ ساعات الهدوء - اختر الفترة التي تريد فيها إشعارات صامتة:\n"
        "(خارج هذه الفترات ستصل الإشعارات بصوت)\n\n"
        "💰 إشعارات رصيد NonVoip - تفعيل/تعطيل إشعارات انخفاض الرصيد عند 20$, 10$, 5$",
        reply_markup=reply_markup
    )
    return QUIET_HOURS

async def handle_quiet_hours_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار إعدادات الإشعارات"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    # معالجة زر separator (لا يفعل شيء)
    if callback_data == "separator":
        return QUIET_HOURS
    
    # معالجة تبديل إشعارات انخفاض رصيد NonVoip
    if callback_data == "toggle_nonvoip_balance_notif":
        # الحصول على الحالة الحالية
        current_setting = db.execute_query("SELECT value FROM settings WHERE key = 'nonvoip_balance_notifications_enabled'")
        current_enabled = current_setting[0][0] == '1' if current_setting else True
        
        # تبديل الحالة
        new_state = '0' if current_enabled else '1'
        db.execute_query(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            ('nonvoip_balance_notifications_enabled', new_state)
        )
        
        # رسالة التأكيد
        status_text = "🔔 مفعّلة" if new_state == '1' else "🔕 معطّلة"
        message = f"{status_text} إشعارات انخفاض رصيد NonVoip\n\n"
        if new_state == '1':
            message += "✅ سيتم إرسال إشعارات عند انخفاض الرصيد تحت:\n• $20 (تنبيه)\n• $10 (تحذير)\n• $5 (خطر)"
        else:
            message += "⚠️ لن يتم إرسال إشعارات انخفاض الرصيد حتى يتم التفعيل مجدداً"
        
        await query.edit_message_text(message, parse_mode='HTML')
        
        # إعادة تفعيل كيبورد الأدمن
        import asyncio
        await asyncio.sleep(1.5)
        await restore_admin_keyboard(context, update.effective_chat.id)
        
        return ConversationHandler.END
    
    # معالجة اختيار ساعات الهدوء
    quiet_period = callback_data.replace("quiet_", "")
    
    # حفظ في قاعدة البيانات
    db.execute_query(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ("quiet_hours", quiet_period)
    )
    
    if quiet_period == "24h":
        message = "🔊 تم تعيين الإشعارات بصوت لمدة 24 ساعة"
    else:
        start_hour, end_hour = quiet_period.split("_")
        message = f"🔕 تم تعيين ساعات الهدوء للإشعارات: <code>{start_hour}:00 - {end_hour}:00</code>"
    
    await query.edit_message_text(message, parse_mode='HTML')
    
    # إعادة تفعيل كيبورد الأدمن بعد فترة قصيرة
    import asyncio
    await asyncio.sleep(1)
    await restore_admin_keyboard(context, update.effective_chat.id)
    
    return ConversationHandler.END

async def admin_logout_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """طلب تأكيد تسجيل خروج الأدمن"""
    keyboard = [
        [InlineKeyboardButton("✅ نعم، تسجيل الخروج", callback_data="confirm_logout")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="cancel_logout")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🚪 <b>تأكيد تسجيل الخروج</b>\n\nهل أنت متأكد من رغبتك في تسجيل الخروج من لوحة الأدمن؟",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def handle_logout_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة تأكيد تسجيل الخروج"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_logout":
        # تسجيل الخروج وتنظيف جميع البيانات الخاصة بالأدمن
        global ACTIVE_ADMINS
        user_id = update.effective_user.id
        
        # استعادة اللغة الأصلية للمستخدم إذا كانت محفوظة
        original_language = context.user_data.get('original_user_language')
        if original_language:
            db.update_user_language(user_id, original_language)
            logger.info(f"تم استعادة اللغة الأصلية {original_language} للمستخدم {user_id} بعد الخروج من وضع الأدمن")
        
        # إزالة الآدمن من قائمة النشطين
        if user_id in ACTIVE_ADMINS:
            ACTIVE_ADMINS.remove(user_id)
        
        context.user_data['is_admin'] = False
        context.user_data.pop('is_admin', None)
        
        # تنظيف أي بيانات أخرى خاصة بالأدمن
        admin_keys = [k for k in context.user_data.keys() if k.startswith('admin_')]
        for key in admin_keys:
            context.user_data.pop(key, None)
        
        # تنظيف اللغة الأصلية المحفوظة
        context.user_data.pop('original_user_language', None)
        
        # تنظيف أي طلب قيد المعالجة
        context.user_data.pop('processing_order_id', None)
        context.user_data.pop('admin_processing_active', None)
        
        # إنشاء كيبورد المستخدم العادي
        user_id = update.effective_user.id
        language = get_user_language(user_id)
        
        reply_markup = create_main_user_keyboard(language)
        
        await query.edit_message_text(
            "✅ <b>تم تسجيل الخروج بنجاح</b>\n\n👋 مرحباً بعودتك كمستخدم عادي\nيمكنك الآن استخدام جميع خدمات البوت",
            parse_mode='HTML'
        )
        
        await context.bot.send_message(
            update.effective_chat.id,
            "🎯 القائمة الرئيسية\nاختر الخدمة المطلوبة:",
            reply_markup=reply_markup
        )
        
    elif query.data == "cancel_logout":
        await query.edit_message_text(
            "❌ <b>تم إلغاء تسجيل الخروج</b>\n\n🔧 لا تزال في لوحة الأدمن\nيمكنك المتابعة في استخدام أدوات الإدارة",
            parse_mode='HTML'
        )
        
        # إعادة تفعيل كيبورد الأدمن الرئيسي
        await restore_admin_keyboard(context, update.effective_chat.id)

async def handle_back_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """العودة للقائمة الرئيسية للأدمن من الأزرار inline"""
    query = update.callback_query
    await query.answer()
    
    # التأكد من أن المستخدم أدمن
    if not context.user_data.get('is_admin', False):
        await query.edit_message_text("❌ هذه الخدمة مخصصة للأدمن فقط!")
        return
    
    await query.edit_message_text("🔧 <b>تم العودة للقائمة الرئيسية</b>")
    await restore_admin_keyboard(context, update.effective_chat.id, "🔧 لوحة الأدمن الرئيسية\nاختر الخدمة المطلوبة:")



async def admin_order_inquiry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """الاستعلام عن طلب"""
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_order_inquiry")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🔍 الاستعلام عن طلب\n\nيرجى إرسال معرف الطلب (<code>16</code> خانة):",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    return ADMIN_ORDER_INQUIRY

async def handle_order_inquiry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة الاستعلام عن طلب"""
    order_id = update.message.text.strip()
    

    
    # التحقق من صحة معرف الطلب
    if len(order_id) != 16:
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_order_inquiry")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "❌ معرف الطلب يجب أن يكون <code>16</code> خانة\n\nيرجى إعادة إدخال معرف الطلب:", 
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        return ADMIN_ORDER_INQUIRY
    
    # البحث عن الطلب
    query = """
        SELECT o.*, u.first_name, u.last_name, u.username 
        FROM orders o 
        JOIN users u ON o.user_id = u.user_id 
        WHERE o.id = ?
    """
    result = db.execute_query(query, (order_id,))
    
    if not result:
        # إعادة تفعيل كيبورد الأدمن
        await update.message.reply_text(f"❌ لم يتم العثور على طلب بالمعرف: {order_id}")
        await restore_admin_keyboard(context, update.effective_chat.id, "🔧 لوحة الأدمن جاهزة")
        return ConversationHandler.END
    
    order = result[0]
    status = order[9]  # حالة الطلب (العمود العاشر: 0-indexed)
    
    # إنشاء رسالة تفاصيل الطلب
    user_name = f"{order[14]} {order[15] or ''}".strip()
    username = order[16] or 'غير محدد'
    
    # تحديد طريقة الدفع
    payment_methods_ar = {
        'shamcash': 'شام كاش',
        'syriatel': 'سيرياتيل كاش',
        'coinex': 'Coinex',
        'binance': 'Binance',
        'payeer': 'Payeer',
        'bep20': 'BEP20',
        'litecoin': 'Litecoin'
    }
    payment_method_ar = payment_methods_ar.get(order[5], order[5])
    
    # تحديد حالة الطلب
    status_text = {
        'pending': '⏳ معلق',
        'completed': '✅ مكتمل',
        'failed': '❌ فاشل'
    }.get(status, status)
    
    order_details = f"""📋 تفاصيل الطلب: <code>{order_id}</code>

👤 المستخدم:
📝 الاسم: {user_name}
📱 اسم المستخدم: @{username}
🆔 معرف المستخدم: <code>{order[1]}</code>

━━━━━━━━━━━━━━━
📦 تفاصيل الطلب:
📊 الكمية: {order[8]}
⏰ المدة: {order[14] if len(order) > 14 and order[14] else "غير محدد"}
🔧 نوع البروكسي: {get_detailed_proxy_type(order[2], order[14] if len(order) > 14 else '', order[3] if len(order) > 3 else '')}
🌍 الدولة: {order[3]}
🏠 الولاية: {order[4]}

━━━━━━━━━━━━━━━
💳 تفاصيل الدفع:
💰 طريقة الدفع: {payment_method_ar}
💵 قيمة الطلب: <code>{order[6]}$</code>
📄 إثبات الدفع: {"✅ مرفق" if order[7] else "❌ غير مرفق"}

━━━━━━━━━━━━━━━
📊 الحالة: {status_text}
📅 تاريخ الطلب: {order[10]}"""

    if status == 'completed' and order[11]:  # processed_at
        order_details += f"\n⏰ تاريخ المعالجة: {order[11]}"
    
    await update.message.reply_text(order_details, parse_mode='HTML', reply_markup=ReplyKeyboardRemove())
    
    if status == 'pending':
        # إعادة إرسال الطلب مع إثبات الدفع
        await resend_order_notification(update, context, order)
        await update.message.reply_text("✅ تم إعادة إرسال الطلب للأدمن مع زر المعالجة")
    
    # تنظيف البيانات المؤقتة مع الحفاظ على حالة الأدمن
    clean_user_data_preserve_admin(context)
    await restore_admin_keyboard(context, update.effective_chat.id, "✅ تم الانتهاء من الاستعلام")
    
    return ConversationHandler.END

async def resend_order_notification(update: Update, context: ContextTypes.DEFAULT_TYPE, order: tuple) -> None:
    """إعادة إرسال إشعار الطلب"""
    order_id = order[0]
    
    # تحديد طريقة الدفع باللغة العربية
    payment_methods_ar = {
        'shamcash': 'شام كاش',
        'syriatel': 'سيرياتيل كاش',
        'coinex': 'Coinex',
        'binance': 'Binance',
        'payeer': 'Payeer',
        'bep20': 'BEP20',
        'litecoin': 'Litecoin'
    }
    
    payment_method_ar = payment_methods_ar.get(order[5], order[5])
    
    message = f"""🔔 طلب معاد إرساله

👤 الاسم: <code>{order[15]} {order[16] or ''}</code>
📱 اسم المستخدم: @{order[17] or 'غير محدد'}
🆔 معرف المستخدم: <code>{order[1]}</code>

━━━━━━━━━━━━━━━
📦 تفاصيل الطلب:
⏰ المدة: {order[14] if len(order) > 14 and order[14] else "غير محدد"}
📊 الكمية: {order[8]}
🔧 نوع البروكسي: {get_detailed_proxy_type(order[2], order[14] if len(order) > 14 else '', order[3] if len(order) > 3 else '')}
🌍 الدولة: {order[3]}
🏠 الولاية: {order[4]}

━━━━━━━━━━━━━━━
💳 تفاصيل الدفع:
💰 طريقة الدفع: {payment_method_ar}
📄 إثبات الدفع: {"✅ مرفق" if order[7] else "❌ غير مرفق"}

━━━━━━━━━━━━━━━
🔗 معرف الطلب: <code>{order_id}</code>
📅 تاريخ الطلب: {order[9]}
📊 الحالة: ⏳ معلق"""

    keyboard = [[InlineKeyboardButton("🔧 معالجة الطلب", callback_data=f"process_{order_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    main_msg = await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
    
    # إرسال إثبات الدفع كرد على رسالة الطلب
    if order[7]:  # payment_proof
        if order[7].startswith("photo:"):
            file_id = order[7].replace("photo:", "")
            await context.bot.send_photo(
                update.effective_chat.id,
                photo=file_id,
                caption=f"📸 إثبات دفع للطلب بمعرف: <code>{order_id}</code>",
                parse_mode='HTML',
                reply_to_message_id=main_msg.message_id
            )
        elif order[7].startswith("text:"):
            text_proof = order[7].replace("text:", "")
            await context.bot.send_message(
                update.effective_chat.id,
                f"📝 إثبات دفع للطلب بمعرف: <code>{order_id}</code>\n\nالنص:\n{text_proof}",
                parse_mode='HTML',
                reply_to_message_id=main_msg.message_id
            )

async def set_nonvoip_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """طلب تعديل سعر رقم Non-Voip"""
    try:
        from non_voip_unified import NonVoipDB
        db = NonVoipDB()
        settings = db.get_service_price_settings("NonVoipUsNumber")
        
        if settings:
            current_percentage = settings.get('price_percentage', 0.0)
            credit_value = settings.get('credit_value', 1.0)
        else:
            current_percentage = 0.0
            credit_value = 1.0
    except:
        current_percentage = 0.0
        credit_value = 1.0
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_nonvoip_price")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📱 *تعديل سعر رقم Non-Voip* (NonVoipUsNumber)\n\n"
        f"💰 النسبة المئوية الحالية: {current_percentage}%\n"
        f"💵 قيمة الكريديت: ${credit_value}\n\n"
        f"📝 يرجى إدخال النسبة المئوية الجديدة:\n"
        f"مثال: 20 (يعني 20% زيادة على سعر الدولار)\n"
        f"مثال: 0 (بدون زيادة)\n"
        f"مثال: 50 (50% زيادة)\n\n"
        f"💡 ملاحظة: هذه النسبة تُضاف على السعر بالدولار ثم يتم التحويل للكريديت",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    return SET_PRICE_NONVOIP

async def handle_nonvoip_price_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة تحديث سعر Non-Voip"""
    price_text = update.message.text
    
    def validate_price(price_str):
        """التحقق من صحة السعر (يجب أن يكون رقم صحيح أو عشري)"""
        try:
            price = float(price_str.strip())
            return price >= 0
        except ValueError:
            return False
    
    # التحقق من صحة السعر المدخل
    if not validate_price(price_text):
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_nonvoip_price")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"❌ يرجى إدخال رقم صحيح فقط (مثال: 1.5)\n\nيرجى إعادة إدخال السعر:",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        return SET_PRICE_NONVOIP

    try:
        new_percentage = float(price_text.strip())
        
        # حفظ النسبة المئوية في قاعدة البيانات
        from non_voip_unified import NonVoipDB
        nvdb = NonVoipDB()
        nvdb.set_service_price_settings(
            service_name="NonVoipUsNumber",
            price_percentage=new_percentage
        )
        
        await update.message.reply_text(
            f"✅ تم تحديث نسبة سعر أرقام Non-Voip بنجاح!\n"
            f"💰 النسبة المئوية الجديدة: {new_percentage}%\n\n"
            f"💡 سيتم إضافة {new_percentage}% على السعر بالدولار ثم تحويله للكريديت\n"
            f"📱 المصدر: NonVoipUsNumber.com"
        )
        
        # إعادة تفعيل كيبورد الأدمن الرئيسي
        await restore_admin_keyboard(context, update.effective_chat.id)
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ في تحديث السعر: {str(e)}")
        
        # إعادة تفعيل كيبورد الأدمن الرئيسي حتى في حالة الخطأ
        await restore_admin_keyboard(context, update.effective_chat.id)
    
    return ConversationHandler.END

async def handle_cancel_nonvoip_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إلغاء تعديل سعر Non-Voip"""
    query = update.callback_query
    await query.answer()
    
    # تنظيف البيانات المؤقتة مع الحفاظ على حالة الأدمن
    clean_user_data_preserve_admin(context)
    
    await query.edit_message_text("❌ تم إلغاء تعديل سعر Non-Voip")
    
    # إعادة تفعيل كيبورد الأدمن الرئيسي
    await restore_admin_keyboard(context, update.effective_chat.id)
    
    return ConversationHandler.END

def get_nonvoip_price():
    """الحصول على سعر Non-Voip من قاعدة البيانات"""
    result = db.execute_query("SELECT value FROM settings WHERE key = 'nonvoip_price'")
    if result and result[0]:
        return float(result[0][0])
    return 1.0  # السعر الافتراضي

async def set_luxury_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """طلب تعديل سعر سوكس يومي (Luxury)"""
    if not LUXURY_AVAILABLE:
        await update.message.reply_text("❌ خدمة سوكس يومي غير متاحة حالياً")
        return
    
    current_price = luxury_db.get_proxy_price()
    
    keyboard = [
        [InlineKeyboardButton("💵 تعديل السعر الثابت", callback_data="lx_admin_price")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="lx_admin_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🌐 *تعديل سعر سوكس يومي* (Luxury Support)\n\n"
        f"💵 السعر الحالي للبروكسي: {current_price} كريديت\n\n"
        f"اختر ما تريد تعديله:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def reset_user_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """تصفير رصيد مستخدم"""
    context.user_data['lookup_action'] = 'reset_balance'
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_balance_reset")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🗑️ تصفير رصيد مستخدم\n\nيرجى إرسال معرف المستخدم أو @username:",
        reply_markup=reply_markup
    )
    return USER_LOOKUP

async def handle_balance_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة تصفير الرصيد"""
    search_term = update.message.text
    
    # البحث عن المستخدم
    if search_term.startswith('@'):
        username = search_term[1:]
        query = "SELECT * FROM users WHERE username = ?"
        user_result = db.execute_query(query, (username,))
    else:
        try:
            user_id = int(search_term)
            query = "SELECT * FROM users WHERE user_id = ?"
            user_result = db.execute_query(query, (user_id,))
        except ValueError:
            # إعادة تفعيل كيبورد الأدمن
            await update.message.reply_text("❌ معرف المستخدم غير صحيح!")
            await restore_admin_keyboard(context, update.effective_chat.id, "🔧 لوحة الأدمن جاهزة")
            return ConversationHandler.END
    
    if not user_result:
        # إعادة تفعيل كيبورد الأدمن
        await update.message.reply_text("❌ المستخدم غير موجود!")
        await restore_admin_keyboard(context, update.effective_chat.id, "🔧 لوحة الأدمن جاهزة")
        return ConversationHandler.END
    
    user = user_result[0]
    user_id = user[0]
    old_balance = user[5]
    
    # تصفير الرصيد
    db.execute_query("UPDATE users SET referral_balance = 0 WHERE user_id = ?", (user_id,))
    
    # إعادة تفعيل كيبورد الأدمن
    await update.message.reply_text(
        f"✅ تم تصفير رصيد المستخدم بنجاح!\n\n"
        f"👤 الاسم: {user[2]} {user[3] or ''}\n"
        f"💰 الرصيد السابق: {old_balance:.2f}$\n"
        f"💰 الرصيد الجديد: 0.00$"
    )
    await restore_admin_keyboard(context, update.effective_chat.id, "🔧 لوحة الأدمن جاهزة")
    
    return ConversationHandler.END

async def handle_my_orders_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض قائمة طلباتي مع الأزرار الفرعية"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    if language == 'ar':
        title = """📋 <b>طلباتي</b>

اختر العملية المطلوبة:"""
        keyboard = [
            [InlineKeyboardButton("🔔 تذكير الأدمن بطلباتي", callback_data="user_order_reminder")],
            [InlineKeyboardButton("⏳ عرض طلباتي المعلقة", callback_data="user_pending_orders")],
            [InlineKeyboardButton("✅ عرض الطلبات السابقة", callback_data="user_previous_orders")],
            [InlineKeyboardButton("🏠 الرجوع للقائمة الرئيسية", callback_data="user_back_main_menu")]
        ]
    else:
        title = """📋 <b>My Orders</b>

Choose the required operation:"""
        keyboard = [
            [InlineKeyboardButton("🔔 Remind Admin About My Orders", callback_data="user_order_reminder")],
            [InlineKeyboardButton("⏳ View My Pending Orders", callback_data="user_pending_orders")],
            [InlineKeyboardButton("✅ View Previous Orders", callback_data="user_previous_orders")],
            [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="user_back_main_menu")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(title, reply_markup=reply_markup, parse_mode='HTML')


async def handle_my_orders_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة callbacks قائمة طلباتي"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    callback_data = query.data
    
    if callback_data == "user_order_reminder":
        await handle_order_reminder_callback(update, context)
    elif callback_data == "user_pending_orders":
        await show_user_pending_orders(update, context)
    elif callback_data == "user_previous_orders":
        await show_user_previous_orders(update, context)
    elif callback_data == "user_back_main_menu":
        if language == 'ar':
            await query.edit_message_text("🏠 تم الرجوع للقائمة الرئيسية")
        else:
            await query.edit_message_text("🏠 Returned to main menu")
    elif callback_data == "user_back_orders_menu":
        # الرجوع لقائمة طلباتي
        if language == 'ar':
            title = """📋 <b>طلباتي</b>

اختر العملية المطلوبة:"""
            keyboard = [
                [InlineKeyboardButton("🔔 تذكير الأدمن بطلباتي", callback_data="user_order_reminder")],
                [InlineKeyboardButton("⏳ عرض طلباتي المعلقة", callback_data="user_pending_orders")],
                [InlineKeyboardButton("✅ عرض الطلبات السابقة", callback_data="user_previous_orders")],
                [InlineKeyboardButton("🏠 الرجوع للقائمة الرئيسية", callback_data="user_back_main_menu")]
            ]
        else:
            title = """📋 <b>My Orders</b>

Choose the required operation:"""
            keyboard = [
                [InlineKeyboardButton("🔔 Remind Admin About My Orders", callback_data="user_order_reminder")],
                [InlineKeyboardButton("⏳ View My Pending Orders", callback_data="user_pending_orders")],
                [InlineKeyboardButton("✅ View Previous Orders", callback_data="user_previous_orders")],
                [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="user_back_main_menu")]
            ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(title, reply_markup=reply_markup, parse_mode='HTML')


async def handle_order_reminder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة تذكير الطلبات من الـ callback"""
    query = update.callback_query
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    # التحقق من آخر استخدام للتذكير
    last_reminder = context.user_data.get('last_reminder', 0)
    current_time = datetime.now().timestamp()
    
    # التحقق من مرور 3 ساعات على آخر استخدام
    if current_time - last_reminder < 10800:  # 3 ساعات
        remaining_time = int((10800 - (current_time - last_reminder)) / 60)
        back_btn = InlineKeyboardButton("🔙 رجوع" if language == 'ar' else "🔙 Back", callback_data="user_back_orders_menu")
        if language == 'ar':
            await query.edit_message_text(
                f"⏰ يمكنك استخدام التذكير مرة أخرى بعد {remaining_time} دقيقة",
                reply_markup=InlineKeyboardMarkup([[back_btn]])
            )
        else:
            await query.edit_message_text(
                f"⏰ You can use the reminder again after {remaining_time} minutes",
                reply_markup=InlineKeyboardMarkup([[back_btn]])
            )
        return
    
    # البحث عن الطلبات المعلقة للمستخدم
    pending_orders = db.execute_query(
        "SELECT id, created_at FROM orders WHERE user_id = ? AND status = 'pending'",
        (user_id,)
    )
    
    back_btn = InlineKeyboardButton("🔙 رجوع" if language == 'ar' else "🔙 Back", callback_data="user_back_orders_menu")
    
    if not pending_orders:
        if language == 'ar':
            await query.edit_message_text(
                "📭 لا توجد لديك طلبات معلقة حالياً.",
                reply_markup=InlineKeyboardMarkup([[back_btn]])
            )
        else:
            await query.edit_message_text(
                "📭 You currently have no pending orders.",
                reply_markup=InlineKeyboardMarkup([[back_btn]])
            )
        return
    
    # تحديث وقت آخر استخدام
    context.user_data['last_reminder'] = current_time
    
    # إرسال تذكير للأدمن لكل طلب معلق
    user = db.get_user(user_id)
    
    for order in pending_orders:
        order_id = order[0]
        await send_reminder_to_admin(context, order_id, user)
    
    if language == 'ar':
        await query.edit_message_text(
            f"✅ تم إرسال تذكير للأدمن بخصوص <code>{len(pending_orders)}</code> طلب معلق",
            reply_markup=InlineKeyboardMarkup([[back_btn]]),
            parse_mode='HTML'
        )
    else:
        await query.edit_message_text(
            f"✅ Reminder sent to admin about <code>{len(pending_orders)}</code> pending order(s)",
            reply_markup=InlineKeyboardMarkup([[back_btn]]),
            parse_mode='HTML'
        )


async def show_user_pending_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض الطلبات المعلقة للمستخدم كأزرار"""
    query = update.callback_query
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    # جلب الطلبات المعلقة
    pending_orders = db.execute_query(
        """SELECT id, proxy_type, payment_amount, created_at, state 
           FROM orders WHERE user_id = ? AND status = 'pending' 
           ORDER BY created_at DESC LIMIT 10""",
        (user_id,)
    )
    
    back_btn = InlineKeyboardButton("🔙 رجوع" if language == 'ar' else "🔙 Back", callback_data="user_back_orders_menu")
    
    if not pending_orders:
        if language == 'ar':
            await query.edit_message_text(
                "📭 لا توجد لديك طلبات معلقة حالياً.",
                reply_markup=InlineKeyboardMarkup([[back_btn]])
            )
        else:
            await query.edit_message_text(
                "📭 You currently have no pending orders.",
                reply_markup=InlineKeyboardMarkup([[back_btn]])
            )
        return
    
    # إنشاء أزرار للطلبات مع معرفات مختصرة
    keyboard = []
    for i, order in enumerate(pending_orders, 1):
        order_id, proxy_type, amount, created_at, state = order
        service_name = escape_html(str(state if state else proxy_type))
        # اختصار معرف الطلب للعرض
        short_id = order_id[:8] if len(order_id) > 8 else order_id
        btn_text = f"{i}. 📦 {service_name} | ${amount:.2f} | #{short_id}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"user_view_order_{order_id}")])
    
    # إضافة زر الرجوع
    keyboard.append([back_btn])
    
    if language == 'ar':
        message = f"⏳ <b>طلباتك المعلقة ({len(pending_orders)})</b>\n\nاختر طلباً لعرض تفاصيله:"
    else:
        message = f"⏳ <b>Your Pending Orders ({len(pending_orders)})</b>\n\nSelect an order to view details:"
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def show_user_order_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض تفاصيل طلب واحد للمستخدم مع إمكانية الإلغاء"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    order_id = query.data.replace("user_view_order_", "")
    
    # جلب تفاصيل الطلب
    order = db.execute_query(
        """SELECT id, proxy_type, payment_amount, created_at, state, payment_method 
           FROM orders WHERE id = ? AND user_id = ? AND status = 'pending'""",
        (order_id, user_id)
    )
    
    back_btn = InlineKeyboardButton("🔙 رجوع" if language == 'ar' else "🔙 Back", callback_data="user_pending_orders")
    
    if not order:
        if language == 'ar':
            await query.edit_message_text(
                "❌ الطلب غير موجود أو تم معالجته.",
                reply_markup=InlineKeyboardMarkup([[back_btn]])
            )
        else:
            await query.edit_message_text(
                "❌ Order not found or already processed.",
                reply_markup=InlineKeyboardMarkup([[back_btn]])
            )
        return
    
    order_id, proxy_type, amount, created_at, state, payment_method = order[0]
    service_name = escape_html(str(state if state else proxy_type))
    payment_display = escape_html(str(payment_method)) if payment_method else ('غير محدد' if language == 'ar' else 'Not specified')
    
    if language == 'ar':
        message = f"""📋 <b>تفاصيل الطلب</b>

🆔 المعرف: <code>{order_id}</code>
📦 الخدمة: {service_name}
💰 المبلغ: ${amount:.2f}
💳 طريقة الدفع: {payment_display}
📅 التاريخ: {created_at}
📊 الحالة: معلق"""
        
        keyboard = [
            [InlineKeyboardButton("❌ إلغاء الطلب", callback_data=f"user_cancel_order_{order_id}")],
            [back_btn]
        ]
    else:
        message = f"""📋 <b>Order Details</b>

🆔 ID: <code>{order_id}</code>
📦 Service: {service_name}
💰 Amount: ${amount:.2f}
💳 Payment: {payment_display}
📅 Date: {created_at}
📊 Status: Pending"""
        
        keyboard = [
            [InlineKeyboardButton("❌ Cancel Order", callback_data=f"user_cancel_order_{order_id}")],
            [back_btn]
        ]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def handle_user_cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تأكيد إلغاء الطلب قبل الحذف"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    order_id = query.data.replace("user_cancel_order_", "")
    
    # التحقق من وجود الطلب
    order = db.execute_query(
        "SELECT id FROM orders WHERE id = ? AND user_id = ? AND status = 'pending'",
        (order_id, user_id)
    )
    
    back_btn = InlineKeyboardButton("🔙 رجوع" if language == 'ar' else "🔙 Back", callback_data=f"user_view_order_{order_id}")
    
    if not order:
        if language == 'ar':
            await query.edit_message_text(
                "❌ الطلب غير موجود أو تم معالجته.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="user_pending_orders")]])
            )
        else:
            await query.edit_message_text(
                "❌ Order not found or already processed.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="user_pending_orders")]])
            )
        return
    
    if language == 'ar':
        message = f"""⚠️ <b>تأكيد إلغاء الطلب</b>

🆔 المعرف: <code>{order_id}</code>

هل أنت متأكد من إلغاء هذا الطلب؟
سيتم حذف الطلب نهائياً."""
        
        keyboard = [
            [InlineKeyboardButton("✅ نعم، إلغاء الطلب", callback_data=f"user_confirm_cancel_{order_id}")],
            [back_btn]
        ]
    else:
        message = f"""⚠️ <b>Confirm Order Cancellation</b>

🆔 ID: <code>{order_id}</code>

Are you sure you want to cancel this order?
The order will be permanently deleted."""
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Cancel Order", callback_data=f"user_confirm_cancel_{order_id}")],
            [back_btn]
        ]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def confirm_user_cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تنفيذ إلغاء الطلب وتحديث حالته إلى ملغي"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    order_id = query.data.replace("user_confirm_cancel_", "")
    
    # التحقق من وجود الطلب قبل الإلغاء
    order = db.execute_query(
        "SELECT id, proxy_type, payment_amount, state FROM orders WHERE id = ? AND user_id = ? AND status = 'pending'",
        (order_id, user_id)
    )
    
    back_btn = InlineKeyboardButton("🔙 رجوع للطلبات" if language == 'ar' else "🔙 Back to Orders", callback_data="user_pending_orders")
    
    if not order:
        if language == 'ar':
            await query.edit_message_text(
                "❌ الطلب غير موجود أو تم معالجته.",
                reply_markup=InlineKeyboardMarkup([[back_btn]])
            )
        else:
            await query.edit_message_text(
                "❌ Order not found or already processed.",
                reply_markup=InlineKeyboardMarkup([[back_btn]])
            )
        return
    
    order_data = order[0]
    proxy_type = order_data[1]
    payment_amount = order_data[2]
    state = order_data[3]
    service_name = state if state else proxy_type
    
    try:
        # تحديث حالة الطلب إلى ملغي بدلاً من حذفه
        db.execute_query(
            "UPDATE orders SET status = 'cancelled', processed_at = ? WHERE id = ? AND user_id = ?",
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), order_id, user_id)
        )
        
        # تسجيل العملية
        db.log_action(user_id, "order_cancelled_by_user", f"Order {order_id} cancelled by user")
        
        # إشعار الآدمن بإلغاء الطلب من قبل الزبون
        await notify_admin_order_cancelled(context, order_id, user_id, service_name, payment_amount)
        
        if language == 'ar':
            await query.edit_message_text(
                f"✅ تم إلغاء الطلب بنجاح!\n\n🆔 المعرف: <code>{order_id}</code>",
                reply_markup=InlineKeyboardMarkup([[back_btn]]),
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text(
                f"✅ Order cancelled successfully!\n\n🆔 ID: <code>{order_id}</code>",
                reply_markup=InlineKeyboardMarkup([[back_btn]]),
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error cancelling order {order_id}: {e}")
        if language == 'ar':
            await query.edit_message_text(
                "❌ حدث خطأ أثناء إلغاء الطلب. يرجى المحاولة لاحقاً.",
                reply_markup=InlineKeyboardMarkup([[back_btn]])
            )
        else:
            await query.edit_message_text(
                "❌ An error occurred while cancelling the order. Please try again later.",
                reply_markup=InlineKeyboardMarkup([[back_btn]])
            )


async def notify_admin_order_cancelled(context: ContextTypes.DEFAULT_TYPE, order_id: str, user_id: int, service_name: str, payment_amount: float) -> None:
    """تحديث رسالة الإشعار الأصلية للآدمن عند إلغاء الطلب من قبل الزبون"""
    
    # الحصول على بيانات المستخدم
    user = db.get_user(user_id)
    username = f"@{user[1]}" if user and user[1] else "غير محدد"
    full_name = f"{user[2] or ''} {user[3] or ''}".strip() if user else "غير معروف"
    
    # رسالة الإلغاء المحدثة
    updated_message = f"""❌ <b>طلب ملغي - خدمة ديناميكية</b>

━━━━━━━━━━━━━━━
👤 <b>بيانات المستخدم:</b>
📛 الاسم: {full_name}
📱 اسم المستخدم: {username}
🆔 معرف المستخدم: <code>{user_id}</code>

━━━━━━━━━━━━━━━
📦 <b>تفاصيل الطلب:</b>
🔗 رقم الطلب: <code>{order_id}</code>
🛒 الخدمة: {service_name}
💰 المبلغ: ${payment_amount:.2f}

━━━━━━━━━━━━━━━
📊 الحالة: ❌ <b>ملغي من قبل الزبون</b>
📅 تاريخ الإلغاء: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💡 <i>لا يلزم اتخاذ أي إجراء - الطلب ملغي تلقائياً</i>"""
    
    # محاولة تحديث الرسائل الأصلية أولاً
    admin_messages = db.get_order_admin_messages(order_id)
    updated_count = 0
    
    if admin_messages:
        for admin_id, message_id in admin_messages:
            try:
                await context.bot.edit_message_text(
                    chat_id=admin_id,
                    message_id=message_id,
                    text=updated_message,
                    parse_mode='HTML'
                )
                updated_count += 1
                logger.info(f"✅ Updated admin notification for order {order_id} (admin: {admin_id}, msg: {message_id})")
            except Exception as e:
                logger.error(f"Error updating admin message {message_id} for admin {admin_id}: {e}")
        
        # حذف السجلات بعد التحديث
        db.delete_order_admin_messages(order_id)
        
        if updated_count > 0:
            logger.info(f"✅ Successfully updated {updated_count} admin notification(s) for cancelled order: {order_id}")
            return
    
    # إذا لم تكن هناك رسائل مخزنة، أرسل إشعار جديد
    global ACTIVE_ADMINS, ADMIN_CHAT_ID
    admin_ids = set()
    if ACTIVE_ADMINS:
        admin_ids.update(ACTIVE_ADMINS)
    if ADMIN_CHAT_ID:
        admin_ids.add(ADMIN_CHAT_ID)
    
    if not admin_ids:
        try:
            admin_query = "SELECT value FROM settings WHERE key = 'admin_chat_id'"
            admin_result = db.execute_query(admin_query)
            if admin_result and admin_result[0][0]:
                admin_ids.add(int(admin_result[0][0]))
        except Exception as e:
            logger.error(f"Error getting admin from database: {e}")
    
    if not admin_ids:
        logger.warning(f"No admin available to notify about cancelled order: {order_id}")
        return
    
    # إرسال إشعار جديد إذا لم يتم تحديث أي رسالة
    for admin_id in admin_ids:
        try:
            await context.bot.send_message(
                admin_id,
                updated_message,
                parse_mode='HTML'
            )
            logger.info(f"Sent new cancellation notification to admin {admin_id} for order {order_id}")
        except Exception as e:
            logger.error(f"Error sending cancellation notification to admin {admin_id}: {e}")


async def show_user_previous_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض الطلبات السابقة (المكتملة والفاشلة والملغاة) للمستخدم كأزرار"""
    query = update.callback_query
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    # جلب آخر 5 طلبات سابقة (مكتملة أو فاشلة أو ملغاة)
    previous_orders = db.execute_query(
        """SELECT id, proxy_type, payment_amount, created_at, status, state 
           FROM orders WHERE user_id = ? AND status IN ('completed', 'failed', 'cancelled') 
           ORDER BY created_at DESC LIMIT 5""",
        (user_id,)
    )
    
    back_btn = InlineKeyboardButton("🔙 رجوع" if language == 'ar' else "🔙 Back", callback_data="user_back_orders_menu")
    
    if not previous_orders:
        if language == 'ar':
            await query.edit_message_text(
                "📭 لا توجد لديك طلبات سابقة.",
                reply_markup=InlineKeyboardMarkup([[back_btn]])
            )
        else:
            await query.edit_message_text(
                "📭 You have no previous orders.",
                reply_markup=InlineKeyboardMarkup([[back_btn]])
            )
        return
    
    status_icons = {
        'completed': '✅',
        'failed': '⚠️',
        'cancelled': '❌'
    }
    
    status_names_ar = {
        'completed': 'مكتمل',
        'failed': 'فاشل',
        'cancelled': 'ملغي'
    }
    
    status_names_en = {
        'completed': 'Completed',
        'failed': 'Failed',
        'cancelled': 'Cancelled'
    }
    
    # إنشاء أزرار للطلبات السابقة
    keyboard = []
    for i, order in enumerate(previous_orders, 1):
        order_id, proxy_type, amount, created_at, status, state = order
        service_name = escape_html(str(state if state else proxy_type))
        status_icon = status_icons.get(status, '📋')
        short_id = order_id[:8] if len(order_id) > 8 else order_id
        
        if language == 'ar':
            status_name = status_names_ar.get(status, status)
        else:
            status_name = status_names_en.get(status, status)
        
        btn_text = f"{i}. {status_icon} {service_name} | ${amount:.2f} | #{short_id}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"user_prev_order_{order_id}")])
    
    # إضافة زر الرجوع
    keyboard.append([back_btn])
    
    if language == 'ar':
        message = f"✅ <b>طلباتك السابقة (آخر {len(previous_orders)})</b>\n\nاختر طلباً لعرض تفاصيله:"
    else:
        message = f"✅ <b>Your Previous Orders (Last {len(previous_orders)})</b>\n\nSelect an order to view details:"
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def show_user_previous_order_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض تفاصيل طلب سابق للمستخدم مع رد الآدمن"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    order_id = query.data.replace("user_prev_order_", "")
    
    # جلب تفاصيل الطلب مع رد الآدمن
    order = db.execute_query(
        """SELECT id, proxy_type, payment_amount, created_at, status, state, proxy_details, processed_at
           FROM orders WHERE id = ? AND user_id = ?""",
        (order_id, user_id)
    )
    
    back_btn = InlineKeyboardButton("🔙 رجوع للطلبات" if language == 'ar' else "🔙 Back to Orders", callback_data="user_previous_orders")
    
    if not order:
        if language == 'ar':
            await query.edit_message_text(
                "❌ لم يتم العثور على الطلب.",
                reply_markup=InlineKeyboardMarkup([[back_btn]])
            )
        else:
            await query.edit_message_text(
                "❌ Order not found.",
                reply_markup=InlineKeyboardMarkup([[back_btn]])
            )
        return
    
    order_id, proxy_type, amount, created_at, status, state, proxy_details, processed_at = order[0]
    service_name = escape_html(str(state if state else proxy_type))
    
    status_icons = {'completed': '✅', 'cancelled': '❌'}
    status_names_ar = {'completed': 'مكتمل', 'cancelled': 'ملغي'}
    status_names_en = {'completed': 'Completed', 'cancelled': 'Cancelled'}
    
    status_icon = status_icons.get(status, '📋')
    
    # استخراج رد الآدمن من proxy_details
    admin_response = ""
    if proxy_details and status == 'completed':
        try:
            details_json = json.loads(proxy_details)
            admin_response = details_json.get('details', '')
            # تقليم الرد إذا كان طويلاً جداً (حد 500 حرف لتجنب مشاكل الرسائل الطويلة)
            max_response_length = 500
            if len(admin_response) > max_response_length:
                admin_response = admin_response[:max_response_length] + "..."
        except (json.JSONDecodeError, TypeError):
            admin_response = str(proxy_details)[:500] if proxy_details else ""
    
    # تنظيف رد الآدمن من أحرف HTML الخاصة لتجنب أخطاء التنسيق
    if admin_response:
        admin_response = escape_html(str(admin_response))
    
    if language == 'ar':
        status_name = status_names_ar.get(status, status)
        message = f"{status_icon} <b>تفاصيل الطلب</b>\n\n"
        message += f"🆔 المعرف: <code>{order_id}</code>\n"
        message += f"📦 الخدمة: {service_name}\n"
        message += f"💰 المبلغ: ${amount:.2f}\n"
        message += f"📊 الحالة: {status_name}\n"
        message += f"📅 تاريخ الطلب: {created_at}\n"
        
        if status == 'completed':
            if processed_at:
                message += f"✅ تاريخ المعالجة: {processed_at}\n"
            if admin_response:
                message += f"\n📝 <b>رد الآدمن:</b>\n<code>{admin_response}</code>"
        elif status == 'cancelled':
            message += f"\n❌ تم إلغاء هذا الطلب من قبلك"
    else:
        status_name = status_names_en.get(status, status)
        message = f"{status_icon} <b>Order Details</b>\n\n"
        message += f"🆔 ID: <code>{order_id}</code>\n"
        message += f"📦 Service: {service_name}\n"
        message += f"💰 Amount: ${amount:.2f}\n"
        message += f"📊 Status: {status_name}\n"
        message += f"📅 Order Date: {created_at}\n"
        
        if status == 'completed':
            if processed_at:
                message += f"✅ Processed Date: {processed_at}\n"
            if admin_response:
                message += f"\n📝 <b>Admin Response:</b>\n<code>{admin_response}</code>"
        elif status == 'cancelled':
            message += f"\n❌ This order was cancelled by you"
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup([[back_btn]]),
        parse_mode='HTML'
    )


async def handle_order_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة تذكير الطلبات - للتوافق مع الكود القديم"""
    await handle_my_orders_menu(update, context)

async def send_reminder_to_admin(context: ContextTypes.DEFAULT_TYPE, order_id: str, user: tuple) -> None:
    """إرسال تذكير للأدمن"""
    message = f"""🔔 تذكير بطلب معلق
    
👤 الاسم: <code>{user[2]} {user[3] or ''}</code>
📱 اسم المستخدم: @{user[1] or 'غير محدد'}
🆔 معرف المستخدم: <code>{user[0]}</code>

💬 مرحباً، لدي طلب معلق بانتظار المعالجة

🔗 معرف الطلب: <code>{order_id}</code>
📅 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

    keyboard = [[InlineKeyboardButton("🔧 معالجة الطلب", callback_data=f"process_{order_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if ADMIN_CHAT_ID:
        try:
            await context.bot.send_message(
                ADMIN_CHAT_ID,
                message,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        except Exception as e:
            print(f"خطأ في إرسال التذكير: {e}")

async def confirm_database_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تأكيد تفريغ قاعدة البيانات"""
    keyboard = [
        [InlineKeyboardButton("✅ نعم، تفريغ البيانات", callback_data="confirm_clear_db")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="cancel_clear_db")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ تحذير!\n\nهل أنت متأكد من تفريغ قاعدة البيانات؟\n\n🗑️ سيتم حذف:\n- جميع الطلبات\n- جميع الإحالات\n- جميع السجلات\n\n✅ سيتم الاحتفاظ ب:\n- بيانات المستخدمين\n- بيانات الأدمن\n- إعدادات النظام",
        reply_markup=reply_markup
    )

async def handle_database_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة تفريغ قاعدة البيانات"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_clear_db":
        try:
            # حذف البيانات مع الاحتفاظ ببيانات المستخدمين والأدمن
            db.execute_query("DELETE FROM orders")
            db.execute_query("DELETE FROM referrals") 
            db.execute_query("DELETE FROM logs")
            
            await query.edit_message_text(
                "✅ تم تفريغ قاعدة البيانات بنجاح!\n\n🗑️ تم حذف:\n- جميع الطلبات\n- جميع الإحالات\n- جميع السجلات\n\n✅ تم الاحتفاظ ببيانات المستخدمين والإعدادات"
            )
            
            # إعادة تفعيل كيبورد الأدمن بعد فترة قصيرة
            import asyncio
            await asyncio.sleep(2)
            await restore_admin_keyboard(context, update.effective_chat.id)
        except Exception as e:
            await query.edit_message_text(f"❌ خطأ في تفريغ قاعدة البيانات: {str(e)}")
    
    elif query.data == "cancel_clear_db":
        await query.edit_message_text("❌ تم إلغاء عملية تفريغ قاعدة البيانات")
        
        # إعادة تفعيل كيبورد الأدمن الرئيسي
        await restore_admin_keyboard(context, update.effective_chat.id)

async def handle_cancel_processing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إلغاء معالجة الطلب مؤقتاً"""
    query = update.callback_query
    await query.answer()
    
    order_id = context.user_data.get('processing_order_id')
    if order_id:
        # الحصول على بيانات المستخدم
        user_query = "SELECT user_id FROM orders WHERE id = ?"
        user_result = db.execute_query(user_query, (order_id,))
        
        if user_result:
            user_id = user_result[0][0]
            user_language = get_user_language(user_id)
            
            # إرسال رسالة للمستخدم
            if user_language == 'ar':
                message = f"⏸️ تم توقيف معالجة طلبك مؤقتاً رقم <code>{order_id}</code>\n\nسيتم استئناف المعالجة لاحقاً من قبل الأدمن."
            else:
                message = f"⏸️ Processing of your order <code>{order_id}</code> has been temporarily stopped\n\nProcessing will resume later by admin."
            
            await context.bot.send_message(user_id, message, parse_mode='HTML')
        
        # رسالة للأدمن
        await query.edit_message_text(
            f"⏸️ تم إلغاء معالجة الطلب مؤقتاً\n\n🆔 معرف الطلب: {order_id}\n\n📋 الطلب لا يزال في حالة معلق ويمكن استئناف معالجته لاحقاً",
            parse_mode='HTML'
        )
        
        # تنظيف البيانات المؤقتة
        # إعادة الطلب إلى حالة pending (لا نجاح ولا فشل)
        db.execute_query(
            "UPDATE orders SET status = 'pending' WHERE id = ?",
            (order_id,)
        )

        # تنظيف حالة انتظار رسالة الأدمن
        context.user_data.pop('waiting_for_admin_message', None)
        
        clean_user_data_preserve_admin(context)
        
        # إعادة تفعيل كيبورد الأدمن الرئيسي
        await restore_admin_keyboard(context, update.effective_chat.id)
        
    else:
        await query.edit_message_text("❌ لم يتم العثور على طلب لإلغاء معالجته")
        
        # إعادة تفعيل كيبورد الأدمن الرئيسي حتى في حالة الخطأ
        await restore_admin_keyboard(context, update.effective_chat.id)
    
    return ConversationHandler.END

async def handle_cancel_direct_processing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة إلغاء المعالجة المباشرة"""
    query = update.callback_query
    await query.answer()
    
    order_id = context.user_data.get('processing_order_id')
    if order_id:
        # الحصول على بيانات المستخدم
        user_query = "SELECT user_id FROM orders WHERE id = ?"
        user_result = db.execute_query(user_query, (order_id,))
        
        if user_result:
            user_id = user_result[0][0]
            user_language = get_user_language(user_id)
            
            # إرسال رسالة للمستخدم
            if user_language == 'ar':
                message = f"⏸️ تم توقيف معالجة طلبك مؤقتاً رقم <code>{order_id}</code>\n\nسيتم استئناف المعالجة لاحقاً من قبل الأدمن."
            else:
                message = f"⏸️ Processing of your order <code>{order_id}</code> has been temporarily stopped\n\nProcessing will resume later by admin."
            
            await context.bot.send_message(user_id, message, parse_mode='HTML')
        
        # رسالة للأدمن
        await query.edit_message_text(
            f"⏸️ تم إلغاء معالجة الطلب مؤقتاً\n\n🆔 معرف الطلب: {order_id}\n\n📋 الطلب لا يزال في حالة معلق ويمكن استئناف معالجته لاحقاً",
            parse_mode='HTML'
        )
        
        # تنظيف البيانات المؤقتة
        # إعادة الطلب إلى حالة pending (لا نجاح ولا فشل)
        db.execute_query(
            "UPDATE orders SET status = 'pending' WHERE id = ?",
            (order_id,)
        )

        # تنظيف حالة انتظار رسالة الأدمن
        context.user_data.pop('waiting_for_direct_admin_message', None)
        context.user_data.pop('direct_processing', None)
        
        clean_user_data_preserve_admin(context)
        
        # إعادة تفعيل كيبورد الأدمن
        await restore_admin_keyboard(context, update.effective_chat.id)
    
    else:
        await query.edit_message_text("❌ لم يتم العثور على طلب لإلغاء معالجته")
        
        # إعادة تفعيل كيبورد الأدمن الرئيسي حتى في حالة الخطأ
        await restore_admin_keyboard(context, update.effective_chat.id)

async def send_proxy_with_custom_message_direct(update: Update, context: ContextTypes.DEFAULT_TYPE, custom_message: str) -> None:
    """إرسال البروكسي مع الرسالة المخصصة للمعالجة المباشرة"""
    order_id = context.user_data['processing_order_id']
    
    # الحصول على معلومات المستخدم والطلب
    user_query = """
        SELECT o.user_id, u.first_name, u.last_name 
        FROM orders o 
        JOIN users u ON o.user_id = u.user_id 
        WHERE o.id = ?
    """
    user_result = db.execute_query(user_query, (order_id,))
    
    if user_result:
        user_id, first_name, last_name = user_result[0]
        user_full_name = f"{first_name} {last_name or ''}".strip()
        
        # الحصول على التاريخ والوقت الحاليين
        from datetime import datetime
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")
        
        # الحصول على لغة المستخدم وإنشاء رسالة البروكسي
        user_language = get_user_language(user_id)
        
        if user_language == 'ar':
            proxy_message = f"""✅ تم معالجة طلب {user_full_name}

🔐 تفاصيل البروكسي:
{custom_message}

━━━━━━━━━━━━━━━
🆔 معرف الطلب: {order_id}
📅 التاريخ: {current_date}
🕐 الوقت: {current_time}

━━━━━━━━━━━━━━━
✅ تم إنجاز طلبك بنجاح!"""
        else:
            proxy_message = f"""✅ Order processed for {user_full_name}

🔐 Proxy Details:
{custom_message}

━━━━━━━━━━━━━━━
🆔 Order ID: {order_id}
📅 Date: {current_date}
🕐 Time: {current_time}

━━━━━━━━━━━━━━━
✅ Your order has been completed successfully!"""
        
        # اقتطاع الرصيد من المستخدم عند إرسال البروكسي (هذا هو التوقيت الصحيح)
        order_query = "SELECT user_id, payment_amount, proxy_type FROM orders WHERE id = ?"
        order_result = db.execute_query(order_query, (order_id,))
        
        if order_result:
            order_user_id, payment_amount, proxy_type = order_result[0]
            
            # اقتطاع الرصيد (مع السماح بالرصيد السالب لمنع التحايل)
            try:
                db.deduct_credits(
                    order_user_id, 
                    payment_amount, 
                    'proxy_purchase', 
                    order_id, 
                    f"شراء بروكسي {proxy_type}",
                    allow_negative=True  # السماح بالرصيد السالب
                )
                logger.info(f"تم اقتطاع {payment_amount} نقطة من المستخدم {order_user_id} للطلب {order_id}")
            except Exception as deduct_error:
                logger.error(f"Error deducting points for order {order_id}: {deduct_error}")
        
        # إرسال البروكسي للمستخدم
        await context.bot.send_message(user_id, proxy_message, parse_mode='HTML')
        
        # تحديث حالة الطلب
        proxy_details = {
            'admin_message': custom_message,
            'processed_date': current_date,
            'processed_time': current_time
        }
        
        # تسجيل الطلب كمكتمل ومعالج فعلياً
        db.execute_query(
            "UPDATE orders SET status = 'completed', processed_at = CURRENT_TIMESTAMP, proxy_details = ?, truly_processed = TRUE WHERE id = ?",
            (json.dumps(proxy_details), order_id)
        )
        
        # التحقق من إضافة رصيد الإحالة لأول عملية شراء
        await check_and_add_referral_bonus(context, user_id, order_id)
        
        # تنظيف البيانات المؤقتة
        context.user_data.pop('waiting_for_direct_admin_message', None)
        context.user_data.pop('direct_processing', None)
        clean_user_data_preserve_admin(context)
        
        # إرسال رسالة تأكيد للأدمن مع خيار العودة للطلبات المعلقة
        keyboard = [
            [InlineKeyboardButton("🔄 معالجة طلب آخر", callback_data="back_to_pending_orders")],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="admin_main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        success_message = f"""✅ <b>تم إنجاز الطلب بنجاح!</b>

🆔 معرف الطلب: {order_id}
👤 المستخدم: {user_full_name}
📅 التاريخ: {current_date} - {current_time}

━━━━━━━━━━━━━━━
✅ تم إرسال البروكسي للمستخدم بنجاح
✅ تم تحديث حالة الطلب إلى مكتمل
✅ تمت معالجة رصيد الإحالة (إن وجد)

🎯 <b>جاهز لمعالجة المزيد من الطلبات!</b>

💡 <b>نصيحة:</b> يمكنك الآن معالجة عدة طلبات متتالية بسرعة دون قيود!"""

        await update.message.reply_text(
            success_message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

async def handle_cancel_user_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إلغاء البحث عن مستخدم"""
    query = update.callback_query
    await query.answer()
    
    # تنظيف بيانات المستخدم
    context.user_data.pop('lookup_action', None)
    
    await query.edit_message_text("❌ تم إلغاء البحث عن المستخدم")
    
    # إعادة تفعيل كيبورد الأدمن الرئيسي
    await restore_admin_keyboard(context, update.effective_chat.id)
    
    return ConversationHandler.END

async def handle_cancel_referral_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إلغاء تحديد قيمة الإحالة"""
    query = update.callback_query
    await query.answer()
    
    # تنظيف البيانات المؤقتة مع الحفاظ على حالة الأدمن
    clean_user_data_preserve_admin(context)
    
    await query.edit_message_text("❌ تم إلغاء تحديد قيمة الإحالة")
    
    # إعادة تفعيل كيبورد الأدمن الرئيسي
    await restore_admin_keyboard(context, update.effective_chat.id)
    
    return ConversationHandler.END

async def handle_cancel_credit_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إلغاء تحديد سعر النقطة"""
    query = update.callback_query
    await query.answer()
    
    # تنظيف البيانات المؤقتة مع الحفاظ على حالة الأدمن
    clean_user_data_preserve_admin(context)
    
    await query.edit_message_text("❌ تم إلغاء تحديد سعر النقطة")
    
    # إعادة تفعيل كيبورد الأدمن الرئيسي
    await restore_admin_keyboard(context, update.effective_chat.id)
    
    return ConversationHandler.END

async def handle_cancel_order_inquiry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إلغاء الاستعلام عن طلب"""
    query = update.callback_query
    await query.answer()
    
    # تنظيف البيانات المؤقتة مع الحفاظ على حالة الأدمن
    clean_user_data_preserve_admin(context)
    
    await query.edit_message_text("❌ تم إلغاء الاستعلام عن الطلب")
    
    # إعادة تفعيل كيبورد الأدمن الرئيسي
    await restore_admin_keyboard(context, update.effective_chat.id)
    
    return ConversationHandler.END

async def handle_cancel_static_prices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إلغاء تعديل أسعار الستاتيك"""
    query = update.callback_query
    await query.answer()
    
    # تنظيف البيانات المؤقتة مع الحفاظ على حالة الأدمن
    clean_user_data_preserve_admin(context)
    
    await query.edit_message_text("❌ تم إلغاء تعديل أسعار الستاتيك")
    
    # إعادة تفعيل كيبورد الأدمن الرئيسي
    await restore_admin_keyboard(context, update.effective_chat.id)
    
    return ConversationHandler.END

async def handle_cancel_socks_prices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إلغاء تعديل أسعار السوكس"""
    query = update.callback_query
    await query.answer()
    
    # تنظيف البيانات المؤقتة مع الحفاظ على حالة الأدمن
    clean_user_data_preserve_admin(context)
    
    await query.edit_message_text("❌ تم إلغاء تعديل أسعار السوكس")
    
    # إعادة تفعيل كيبورد الأدمن الرئيسي
    await restore_admin_keyboard(context, update.effective_chat.id)
    
    return ConversationHandler.END

async def handle_cancel_balance_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إلغاء تصفير الرصيد"""
    query = update.callback_query
    await query.answer()
    
    # تنظيف البيانات المؤقتة مع الحفاظ على حالة الأدمن
    clean_user_data_preserve_admin(context)
    
    await query.edit_message_text("❌ تم إلغاء تصفير رصيد المستخدم")
    
    # إعادة تفعيل كيبورد الأدمن الرئيسي
    await restore_admin_keyboard(context, update.effective_chat.id)
    
    return ConversationHandler.END

async def handle_cancel_payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إلغاء إرسال إثبات الدفع"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        language = get_user_language(user_id)
        
        print(f"🚫 المستخدم {user_id} ألغى إرسال إثبات الدفع")
        
        # تسجيل العملية
        try:
            db.log_action(user_id, "payment_proof_cancelled", "User cancelled payment proof submission")
        except:
            pass
        
        # تنظيف البيانات المؤقتة مع الحفاظ على حالة الأدمن (إذا كان أدمن)
        clean_user_data_preserve_admin(context)
        
        if language == 'ar':
            message = "❌ تم إلغاء إرسال إثبات الدفع\n\n🔄 يمكنك البدء من جديد في أي وقت"
        else:
            message = "❌ Payment proof submission cancelled\n\n🔄 You can start again anytime"
        
        await query.edit_message_text(message, parse_mode='HTML')
        
        # انتظار قليل قبل إعادة التوجيه
        await asyncio.sleep(1)
        
        # للمستخدم العادي - إعادة توجيه للقائمة الرئيسية
        try:
            await start(update, context)
            print(f"✅ تم إعادة توجيه المستخدم {user_id} للقائمة الرئيسية بعد الإلغاء")
        except Exception as e:
            print(f"⚠️ خطأ في إعادة التوجيه للمستخدم {user_id}: {e}")
        
        return ConversationHandler.END
        
    except Exception as e:
        print(f"❌ خطأ في معالجة إلغاء إثبات الدفع للمستخدم {update.effective_user.id}: {e}")
        try:
            # تنظيف البيانات على أي حال مع الحفاظ على حالة الأدمن
            clean_user_data_preserve_admin(context)
            await update.callback_query.answer("❌ تم الإلغاء")
        except:
            pass
        return ConversationHandler.END

async def handle_order_completed_success(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إنهاء الطلب بنجاح وإنهاء ConversationHandler"""
    query = update.callback_query
    await query.answer()
    
    order_id = context.user_data.get('processing_order_id')
    if order_id:
        # تنظيف جميع البيانات المؤقتة مع الحفاظ على حالة الأدمن
        clean_user_data_preserve_admin(context)
    
    await query.edit_message_text(
        f"✅ تم إنهاء الطلب بنجاح!\n\n🆔 معرف الطلب: {order_id}\n\n📋 تم نقل الطلب إلى الطلبات المكتملة.\n\n🔄 يمكنك الآن معالجة طلبات أخرى.",
        parse_mode='HTML'
    )
    
    # إعادة تفعيل كيبورد الأدمن الرئيسي
    await restore_admin_keyboard(context, update.effective_chat.id)
    
    # إنهاء ConversationHandler بشكل صحيح
    return ConversationHandler.END

async def handle_cancel_custom_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إلغاء إرسال الرسالة المخصصة"""
    query = update.callback_query
    await query.answer()
    
    # تنظيف البيانات المؤقتة مع الحفاظ على حالة الأدمن
    clean_user_data_preserve_admin(context)
    
    await query.edit_message_text("❌ تم إلغاء إرسال الرسالة المخصصة")
    
    # إعادة تفعيل كيبورد الأدمن الرئيسي
    await restore_admin_keyboard(context, update.effective_chat.id)
    
    return ConversationHandler.END

async def handle_cancel_proxy_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إلغاء إعداد البروكسي"""
    query = update.callback_query
    await query.answer()
    
    # تنظيف البيانات المؤقتة مع الحفاظ على حالة الأدمن
    clean_user_data_preserve_admin(context)
    
    await query.edit_message_text("❌ تم إلغاء إعداد البروكسي")
    
    # إعادة تفعيل كيبورد الأدمن الرئيسي
    await restore_admin_keyboard(context, update.effective_chat.id)
    
    return ConversationHandler.END

async def cleanup_incomplete_operations(context: ContextTypes.DEFAULT_TYPE, user_id: int, operation_type: str = "all") -> bool:
    """
    تنظيف العمليات المعلقة وغير المكتملة لمنع توقف الكيبورد أو البوت
    
    Args:
        context: سياق البوت
        user_id: معرف المستخدم
        operation_type: نوع العملية للتنظيف ("all", "admin", "user", "conversation")
    
    Returns:
        bool: True إذا تم التنظيف بنجاح
    """
    try:
        cleaned_operations = []
        
        # تنظيف عمليات الأدمن المعلقة
        if operation_type in ["all", "admin"]:
            admin_keys = [
                'processing_order_id', 'admin_processing_active', 'admin_proxy_type',
                'admin_proxy_address', 'admin_proxy_port', 'admin_proxy_country',
                'admin_proxy_state', 'admin_proxy_username', 'admin_proxy_password',
                'admin_thank_message', 'admin_input_state', 'current_country_code'
            ]
            for key in admin_keys:
                if context.user_data.pop(key, None) is not None:
                    cleaned_operations.append(f"admin_{key}")
        
        # تنظيف عمليات المستخدم المعلقة
        if operation_type in ["all", "user"]:
            user_keys = [
                'proxy_type', 'selected_country', 'selected_country_code',
                'selected_state', 'payment_method', 'current_order_id',
                'waiting_for', 'last_reminder'
            ]
            for key in user_keys:
                if context.user_data.pop(key, None) is not None:
                    cleaned_operations.append(f"user_{key}")
        
        # تنظيف عمليات المحادثة المعلقة
        if operation_type in ["all", "conversation"]:
            conversation_keys = [
                'password_change_step', 'lookup_action', 'popup_text',
                'broadcast_type', 'broadcast_message', 'broadcast_users_input',
                'broadcast_valid_users'
            ]
            for key in conversation_keys:
                if context.user_data.pop(key, None) is not None:
                    cleaned_operations.append(f"conversation_{key}")
        
        # تسجيل العمليات المنظفة في السجل
        if cleaned_operations:
            db.log_action(user_id, "cleanup_incomplete_operations", 
                         f"Cleaned: {', '.join(cleaned_operations)}")
            logger.info(f"Cleaned {len(cleaned_operations)} incomplete operations for user {user_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error cleaning incomplete operations for user {user_id}: {e}")
        return False

async def force_reset_user_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    إعادة تعيين حالة المستخدم بالكامل في حالة الطوارئ
    يمكن استخدامها عند توقف الكيبورد أو البوت
    """
    user_id = update.effective_user.id
    
    try:
        # تنظيف جميع البيانات المؤقتة
        context.user_data.clear()  # تبسيط التنظيف
        
        # التحقق من نوع المستخدم وإعادة تفعيل الكيبورد المناسب
        is_admin = context.user_data.get('is_admin', False) or user_id in ACTIVE_ADMINS
        
        if is_admin:
            # إعادة تفعيل كيبورد الأدمن
            context.user_data['is_admin'] = True
            await restore_admin_keyboard(context, update.effective_chat.id, 
                                       "🔧 تم إعادة تعيين حالة الأدمن بنجاح")
        else:
            # إعادة تفعيل كيبورد المستخدم العادي
            language = get_user_language(user_id)
            reply_markup = create_main_user_keyboard(language)
            
            await context.bot.send_message(
                update.effective_chat.id,
                "🔄 تم إعادة تعيين حالة البوت بنجاح\n\n" + MESSAGES[language]['welcome'],
                reply_markup=reply_markup
            )
        
        # تسجيل العملية
        db.log_action(user_id, "force_reset_user_state", "Emergency state reset completed")
        logger.info(f"Force reset completed for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in force reset for user {user_id}: {e}")
        
        # في حالة فشل كل شيء، أرسل رسالة بسيطة
        try:
            await context.bot.send_message(
                update.effective_chat.id,
                "❌ حدث خطأ في إعادة التعيين. يرجى استخدام /start لإعادة تشغيل البوت"
            )
        except:
            pass

async def handle_stuck_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    معالجة المحادثات العالقة التي لا تستجيب
    """
    user_id = update.effective_user.id
    is_admin = context.user_data.get('is_admin', False) or user_id in ACTIVE_ADMINS
    
    try:
        logger.warning(f"Stuck conversation detected for user {user_id}")
        
        # تنظيف العمليات المعلقة مع الحفاظ على حالة الأدمن
        clean_user_data_preserve_admin(context)
        
        # إرسال رسالة توضيحية وإعادة الكيبورد المناسب
        if update.message:
            await update.message.reply_text(
                "🔄 تم اكتشاف محادثة عالقة وتم تنظيفها\n"
                "يمكنك الآن المتابعة بشكل طبيعي",
                reply_markup=ReplyKeyboardRemove()
            )
        elif update.callback_query:
            await update.callback_query.answer("تم إعادة تعيين الحالة")
            await update.callback_query.message.reply_text(
                "🔄 تم اكتشاف محادثة عالقة وتم تنظيفها\n"
                "يمكنك الآن المتابعة بشكل طبيعي"
            )
        
        # إعادة الكيبورد المناسب حسب نوع المستخدم
        if is_admin:
            await restore_admin_keyboard(context, update.effective_chat.id, "🔄 تم إعادة التعيين")
        else:
            await start(update, context)
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error handling stuck conversation for user {user_id}: {e}")
        try:
            clean_user_data_preserve_admin(context)
            if update.message:
                await update.message.reply_text("⚠️ حدث خطأ. يرجى استخدام /start لإعادة التشغيل")
        except:
            pass
        return ConversationHandler.END

async def auto_cleanup_expired_operations(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    تنظيف تلقائي للعمليات المنتهية الصلاحية (يعمل كل ساعة)
    """
    try:
        # الحصول على جميع المستخدمين النشطين
        active_users = db.execute_query("""
            SELECT DISTINCT user_id 
            FROM logs 
            WHERE timestamp > datetime('now', '-24 hours')
        """)
        
        cleanup_count = 0
        
        for user_tuple in active_users:
            user_id = user_tuple[0]
            
            # تحقق من وجود عمليات معلقة قديمة (أكثر من 30 دقيقة)
            old_operations = db.execute_query("""
                SELECT COUNT(*) FROM logs 
                WHERE user_id = ? 
                AND action LIKE '%_started' 
                AND timestamp < datetime('now', '-30 minutes')
                AND user_id NOT IN (
                    SELECT user_id FROM logs 
                    WHERE action LIKE '%_completed' 
                    AND timestamp > datetime('now', '-30 minutes')
                )
            """, (user_id,))
            
            if old_operations and old_operations[0][0] > 0:
                # تنظيف البيانات المعلقة
                # ملاحظة: هذا يتطلب الوصول لـ user_data الخاص بالمستخدم
                # في التطبيق الحقيقي، يمكن حفظ البيانات في قاعدة البيانات
                cleanup_count += 1
                db.log_action(user_id, "auto_cleanup_expired", "Cleaned expired operations")
        
        if cleanup_count > 0:
            logger.info(f"Auto-cleaned expired operations for {cleanup_count} users")
            
    except Exception as e:
        logger.error(f"Error in auto cleanup: {e}")


async def show_user_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE, offset: int = 0) -> None:
    """عرض إحصائيات المستخدمين مرتبة حسب عدد الإحالات مع دعم التصفح"""
    # الحصول على العدد الإجمالي للمستخدمين
    total_count_query = "SELECT COUNT(*) FROM users"
    total_users = db.execute_query(total_count_query)[0][0]
    
    # حجم الصفحة الواحدة
    page_size = 20
    
    stats_query = """
        SELECT u.first_name, u.last_name, u.username, u.user_id,
               COUNT(r.id) as referral_count, u.referral_balance
        FROM users u
        LEFT JOIN referrals r ON u.user_id = r.referrer_id
        GROUP BY u.user_id
        ORDER BY referral_count DESC
        LIMIT ? OFFSET ?
    """
    
    users_stats = db.execute_query(stats_query, (page_size, offset))
    
    if not users_stats:
        if offset == 0:
            await update.message.reply_text("لا توجد إحصائيات متاحة")
        else:
            await update.message.reply_text("📊 هذا كل شيء!\n\n✅ تم عرض جميع المستخدمين في قاعدة البيانات")
        return
    
    # تحديد رقم الصفحة الحالية
    current_page = (offset // page_size) + 1
    total_pages = (total_users + page_size - 1) // page_size
    
    message = f"📊 إحصائيات المستخدمين (الصفحة {current_page} من {total_pages})\n"
    message += f"👥 المستخدمون {offset + 1} إلى {min(offset + page_size, total_users)} من أصل {total_users}\n\n"
    
    for i, user_stat in enumerate(users_stats, 1):
        global_index = offset + i
        name = f"{user_stat[0]} {user_stat[1] or ''}"
        username = f"@{user_stat[2]}" if user_stat[2] else "بدون معرف"
        referral_count = user_stat[4]
        balance = user_stat[5]
        
        message += f"{global_index}. {name}\n"
        message += f"   👤 {username}\n"
        message += f"   👥 الإحالات: {referral_count}\n"
        message += f"   💰 الرصيد: {balance:.2f}$\n\n"
    
    # إضافة زر "عرض المزيد" إذا كان هناك مستخدمون أكثر
    keyboard = []
    if offset + page_size < total_users:
        keyboard.append([InlineKeyboardButton("📄 عرض المزيد", callback_data=f"show_more_users_{offset + page_size}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    # فحص إذا كانت الرسالة من callback query أو message عادية
    if update.callback_query:
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message, reply_markup=reply_markup)

# وظائف التقسيم والتنقل
def paginate_items(items, page=0, items_per_page=8):
    """تقسيم القوائم لصفحات"""
    start = page * items_per_page
    end = start + items_per_page
    return list(items.items())[start:end], len(items) > end

def create_paginated_keyboard(items, callback_prefix, page=0, items_per_page=8, language='ar'):
    """إنشاء كيبورد مقسم بأزرار التنقل"""
    keyboard = []
    
    # إضافة زر "غير ذلك" في المقدمة مع إيموجي مميز
    other_text = "🔧 غير ذلك" if language == 'ar' else "🔧 Other"
    keyboard.append([InlineKeyboardButton(other_text, callback_data=f"{callback_prefix}other")])
    
    # الحصول على العناصر للصفحة الحالية
    page_items, has_more = paginate_items(items, page, items_per_page)
    
    # إضافة عناصر الصفحة الحالية
    for code, name in page_items:
        keyboard.append([InlineKeyboardButton(name, callback_data=f"{callback_prefix}{code}")])
    
    # إضافة أزرار التنقل
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ السابق" if language == 'ar' else "◀️ Previous", 
                                               callback_data=f"{callback_prefix}page_{page-1}"))
    if has_more:
        nav_buttons.append(InlineKeyboardButton("التالي ▶️" if language == 'ar' else "Next ▶️", 
                                               callback_data=f"{callback_prefix}page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    return InlineKeyboardMarkup(keyboard)

def get_states_for_country(country_code, proxy_type='static', proxy_subtype='residential'):
    """الحصول على قائمة الولايات/المناطق للدولة المحددة حسب نوع البروكسي"""
    
    # للبروكسي الستاتيك
    if proxy_type == 'static':
        if proxy_subtype == 'residential':
            # الستاتيك الريزيدنتال: الولايات المتحدة والمملكة المتحدة لها ولايات/مزودات
            if country_code == 'US':
                return US_STATES_STATIC_RESIDENTIAL
            elif country_code == 'UK':
                return UK_STATES_STATIC_RESIDENTIAL
            else:
                return None  # فرنسا، ألمانيا بدون ولايات
        elif proxy_subtype == 'residential_verizon':
            # الستاتيك Verizon ريزيدنتال: الولايات المتحدة فقط مع ولايات محددة
            if country_code == 'US':
                return US_STATES_STATIC_VERIZON
            else:
                return None
        elif proxy_subtype == 'residential_crocker':
            # الستاتيك Crocker ريزيدنتال: الولايات المتحدة فقط مع ولاية واحدة
            if country_code == 'US':
                return US_STATES_STATIC_CROCKER
            else:
                return None
        elif proxy_subtype == 'isp':
            # الستاتيك ISP: الولايات المتحدة فقط
            if country_code == 'US':
                return US_STATES_STATIC_ISP
            else:
                return None
    
    # للبروكسي السوكس (النظام القديم)
    elif proxy_type == 'socks':
        states_map = {
            'US': US_STATES,
            'UK': UK_STATES,
            'DE': DE_STATES,
            'FR': FR_STATES,
            'CA': CA_STATES,
            'AU': AU_STATES,
            'AT': AT_STATES,
            'IT': IT_STATES,
            'ES': ES_STATES,
            'NL': NL_STATES,
            'BE': BE_STATES,
            'CH': CH_STATES,
            'RU': RU_STATES,
            'JP': JP_STATES,
            'BR': BR_STATES,
            'MX': MX_STATES,
            'IN': IN_STATES
        }
        return states_map.get(country_code, None)
    
    return None

async def show_proxy_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض معاينة البروكسي للأدمن قبل الإرسال"""
    order_id = context.user_data['processing_order_id']
    
    # الحصول على معلومات المستخدم والطلب
    user_query = """
        SELECT o.user_id, u.first_name, u.last_name, u.username
        FROM orders o 
        JOIN users u ON o.user_id = u.user_id 
        WHERE o.id = ?
    """
    user_result = db.execute_query(user_query, (order_id,))
    
    if user_result:
        user_id, first_name, last_name, username = user_result[0]
        user_full_name = f"{first_name} {last_name or ''}".strip()
        
        # الحصول على التاريخ والوقت الحاليين
        from datetime import datetime
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")
        
        # إنشاء رسالة المعاينة
        preview_message = f"""📋 مراجعة البروكسي قبل الإرسال

👤 <b>المستخدم:</b>
الاسم: {user_full_name}
اسم المستخدم: @{username or 'غير محدد'}
المعرف: <code>{user_id}</code>

🔐 <b>تفاصيل البروكسي:</b>
العنوان: <code>{context.user_data['admin_proxy_address']}</code>
البورت: <code>{context.user_data['admin_proxy_port']}</code>
الدولة: {context.user_data.get('admin_proxy_country', 'غير محدد')}
الولاية: {context.user_data.get('admin_proxy_state', 'غير محدد')}
اسم المستخدم: <code>{context.user_data['admin_proxy_username']}</code>
كلمة المرور: <code>{context.user_data['admin_proxy_password']}</code>

📅 <b>التاريخ والوقت:</b>
التاريخ: {current_date}
الوقت: {current_time}

💬 <b>رسالة الشكر:</b>
{context.user_data['admin_thank_message']}

━━━━━━━━━━━━━━━
🆔 معرف الطلب: {order_id}

تم إرسال البروكسي للمستخدم تلقائياً."""

        # إرسال البروكسي للمستخدم مباشرة
        await send_proxy_to_user_direct(update, context, context.user_data.get('admin_thank_message', ''))
        
        # زر واحد لإنهاء الطلب
        keyboard = [
            [InlineKeyboardButton("✅ تم إنجاز الطلب بنجاح!", callback_data="order_completed_success")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(preview_message, reply_markup=reply_markup, parse_mode='HTML')

async def handle_delete_message_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة حذف رسالة جماعياً لدى جميع المستخدمين"""
    try:
        replied_message = update.message.reply_to_message
        message_text = replied_message.text or replied_message.caption or ""
        
        # الحصول على جميع المستخدمين
        all_users = db.execute_query("SELECT user_id FROM users")
        
        deleted_count = 0
        failed_count = 0
        
        # محاولة حذف الرسالة لدى كل مستخدم
        for user in all_users:
            user_id = user[0]
            try:
                # محاولة حذف الرسالة بنفس معرف الرسالة
                await context.bot.delete_message(
                    chat_id=user_id,
                    message_id=replied_message.message_id
                )
                deleted_count += 1
                await asyncio.sleep(0.05)  # تأخير صغير لتجنب حدود Telegram
            except Exception as e:
                failed_count += 1
                logger.debug(f"فشل حذف الرسالة للمستخدم {user_id}: {e}")
        
        # إرسال تقرير للآدمن
        report = f"""✅ تم حذف الرسالة الجماعي
        
🗑️ تم الحذف بنجاح: {deleted_count} مستخدم
❌ فشل الحذف: {failed_count} مستخدم

📝 نص الرسالة المحذوفة:
{message_text[:100]}{'...' if len(message_text) > 100 else ''}

⚠️ ملاحظة: تم إيقاف وضع حذف الرسائل. يجب تفعيله مرة أخرى للحذف التالي."""
        
        await update.message.reply_text(report)
        
        # إيقاف وضع حذف الرسائل
        context.user_data['delete_message_mode'] = False
        
        # تسجيل العملية
        db.log_action(update.effective_user.id, "delete_message_broadcast", f"Deleted: {deleted_count}, Failed: {failed_count}")
        
    except Exception as e:
        logger.error(f"خطأ في حذف الرسالة الجماعي: {e}")
        await update.message.reply_text(f"❌ حدث خطأ أثناء حذف الرسالة: {str(e)}")

async def show_broadcast_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض قائمة البث"""
    keyboard = [
        [InlineKeyboardButton("📢 إرسال للجميع", callback_data="broadcast_all")],
        [InlineKeyboardButton("👥 إرسال لمستخدمين مخصصين", callback_data="broadcast_custom")],
        [InlineKeyboardButton("🗑️ حذف رسالة", callback_data="broadcast_delete_message")],
        [InlineKeyboardButton("🔙 العودة", callback_data="back_to_admin")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📢 قائمة البث\n\nاختر نوع الإرسال:",
        reply_markup=reply_markup
    )

async def handle_broadcast_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار نوع البث"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "broadcast_all":
        context.user_data['broadcast_type'] = 'all'
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_broadcast")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📢 إرسال إعلان للجميع\n\nيرجى كتابة الرسالة التي تريد إرسالها لجميع المستخدمين:",
            reply_markup=reply_markup
        )
        return BROADCAST_MESSAGE
    
    elif query.data == "broadcast_custom":
        context.user_data['broadcast_type'] = 'custom'
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_broadcast")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "👥 إرسال لمستخدمين مخصصين\n\nيرجى إدخال معرفات المستخدمين أو أسماء المستخدمين:\n\n"
            "الشكل المطلوب:\n"
            "• مستخدم واحد: 123456789 أو @username\n"
            "• عدة مستخدمين: 123456789 - @user1 - 987654321\n\n"
            "⚠️ ملاحظة: استخدم  -  (مسافة قبل وبعد الشرطة) للفصل بين المستخدمين",
            reply_markup=reply_markup
        )
        return BROADCAST_USERS
    
    elif query.data == "broadcast_delete_message":
        context.user_data['delete_message_mode'] = True
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_broadcast")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🗑️ حذف رسالة جماعياً\n\n"
            "قم بالرد على أي رسالة سبق وأن تم إرسالها بكلمة:\n"
            "<code>delete</code>\n\n"
            "سيتم حذف الرسالة لدى جميع المستخدمين.\n\n"
            "⚠️ ملاحظة:\n"
            "• الأمر غير حساس لحالة الأحرف (DELETE، delete، Delete)\n"
            "• يجب الرد على الرسالة المراد حذفها\n"
            "• لن يعمل الأمر إلا بعد تفعيل هذا الوضع",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return ConversationHandler.END
    
    return ConversationHandler.END

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إدخال رسالة البث (نص أو صورة مع نص)"""
    
    # فحص إذا كانت الرسالة تحتوي على صورة
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        context.user_data['broadcast_photo'] = file_id
        # استخدام caption_markdown_v2 للحصول على التنسيق
        message_text = update.message.caption_markdown_v2 or update.message.caption or ""
        context.user_data['broadcast_message'] = message_text
    elif update.message.text:
        # استخدام text_markdown_v2 للحصول على التنسيق
        message_text = update.message.text_markdown_v2 or update.message.text
        context.user_data['broadcast_message'] = message_text
        context.user_data['broadcast_photo'] = None
    else:
        await update.message.reply_text("❌ يرجى إرسال رسالة نصية أو صورة مع نص!")
        return BROADCAST_MESSAGE
    
    broadcast_type = context.user_data.get('broadcast_type', 'all')
    
    if broadcast_type == 'all':
        # عرض المعاينة للإرسال للجميع
        user_count = db.execute_query("SELECT COUNT(*) FROM users")[0][0]
        
        preview_text = f"""📢 *معاينة الإعلان*

👥 المستقبلون: جميع المستخدمين \({user_count} مستخدم\)

📝 *الرسالة:*
{message_text}

━━━━━━━━━━━━━━━
هل تريد إرسال هذا الإعلان؟"""

        keyboard = [
            [InlineKeyboardButton("✅ إرسال", callback_data="confirm_broadcast")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="cancel_broadcast")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(preview_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)
        return BROADCAST_CONFIRM

    
    elif broadcast_type == 'custom':
        # للمستخدمين المخصصين - استخدام handle_broadcast_custom_message
        return await handle_broadcast_custom_message(update, context)
    
    return ConversationHandler.END

async def handle_broadcast_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إدخال المستخدمين المخصصين"""
    users_input = update.message.text
    context.user_data['broadcast_users_input'] = users_input
    
    # تحليل المدخلات
    users_list = [user.strip() for user in users_input.split(' - ')]
    valid_users = []
    invalid_users = []
    
    for user in users_list:
        if user.startswith('@'):
            # البحث باسم المستخدم
            username = user[1:]
            user_result = db.execute_query("SELECT user_id, first_name FROM users WHERE username = ?", (username,))
            if user_result:
                valid_users.append((user_result[0][0], user_result[0][1], user))
            else:
                invalid_users.append(user)
        else:
            try:
                # البحث بالمعرف
                user_id = int(user)
                user_result = db.execute_query("SELECT first_name FROM users WHERE user_id = ?", (user_id,))
                if user_result:
                    valid_users.append((user_id, user_result[0][0], user))
                else:
                    invalid_users.append(user)
            except ValueError:
                invalid_users.append(user)
    
    context.user_data['broadcast_valid_users'] = valid_users
    
    if not valid_users:
        keyboard = [[InlineKeyboardButton("🔙 إلغاء والرجوع", callback_data="cancel_broadcast")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "❌ لم يتم العثور على أي مستخدم صحيح.\n\nيرجى المحاولة مرة أخرى أو الإلغاء.",
            reply_markup=reply_markup
        )
        return BROADCAST_USERS
    
    # عرض قائمة المستخدمين الصحيحين والخاطئين
    preview_text = f"👥 <b>المستخدمون المختارون:</b>\n\n"
    
    if valid_users:
        preview_text += "✅ <b>مستخدمون صحيحون:</b>\n"
        for user_id, name, original in valid_users:
            preview_text += f"• {name} ({original})\n"
    
    if invalid_users:
        preview_text += f"\n❌ <b>مستخدمون غير موجودون:</b>\n"
        for user in invalid_users:
            preview_text += f"• {user}\n"
    
    preview_text += f"\nيرجى كتابة الرسالة التي تريد إرسالها لـ {len(valid_users)} مستخدم:"
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="cancel_broadcast")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(preview_text, reply_markup=reply_markup)
    return BROADCAST_MESSAGE

async def handle_broadcast_custom_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة رسالة البث للمستخدمين المخصصين"""
    message_text = update.message.text
    context.user_data['broadcast_message'] = message_text
    
    valid_users = context.user_data.get('broadcast_valid_users', [])
    
    # عرض المعاينة النهائية
    preview_text = f"""📢 *معاينة الإعلان المخصص*

👥 المستقبلون: {len(valid_users)} مستخدم

📝 *الرسالة:*
{message_text}

━━━━━━━━━━━━━━━
هل تريد إرسال هذا الإعلان؟"""

    keyboard = [
        [InlineKeyboardButton("✅ إرسال", callback_data="confirm_broadcast")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="cancel_broadcast")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(preview_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)
    return BROADCAST_CONFIRM


async def handle_broadcast_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة تأكيد أو إلغاء البث"""
    import asyncio
    
    query = update.callback_query
    await query.answer()
    

    
    if query.data == "confirm_broadcast":
        broadcast_type = context.user_data.get('broadcast_type', 'all')
        message_text = context.user_data.get('broadcast_message', '')
        broadcast_photo = context.user_data.get('broadcast_photo')
        
        # التحقق من وجود رسالة أو صورة
        if not message_text and not broadcast_photo:
            await query.edit_message_text("❌ خطأ: لم يتم العثور على رسالة أو صورة للبث. يرجى المحاولة مرة أخرى.")
            await restore_admin_keyboard(context, update.effective_chat.id)
            return ConversationHandler.END
        
        await query.edit_message_text("📤 جاري إرسال الإعلان...")
        
        # ========== إضافة جديدة: إرسال نسخة للأدمن كـ "original message" ==========
        admin_id = update.effective_user.id
        admin_chat_id = update.effective_chat.id
        original_message = None
        
        try:
            if broadcast_photo:
                original_message = await context.bot.send_photo(
                    chat_id=admin_chat_id,
                    photo=broadcast_photo,
                    caption=f"📢 نسخة البث \\(للتتبع\\):\n\n{message_text if message_text else ''}",
                    parse_mode=ParseMode.MARKDOWN_V2
                )
            else:
                original_message = await context.bot.send_message(
                    chat_id=admin_chat_id,
                    text=f"📢 نسخة البث \\(للتتبع\\):\n\n{message_text}",
                    parse_mode=ParseMode.MARKDOWN_V2
                )
        except Exception as e:
            logger.error(f"فشل إرسال نسخة البث للأدمن: {e}")
        
        original_message_id = original_message.message_id if original_message else None
        # ========== نهاية الإضافة ==========
        
        success_count = 0
        failed_count = 0
        
        if broadcast_type == 'all':
            # إرسال للجميع
            all_users = db.execute_query("SELECT user_id FROM users")
            for user_tuple in all_users:
                user_id = user_tuple[0]
                
                # ========== إضافة: تخطي الأدمن ==========
                if user_id == admin_id:
                    continue
                # ========== نهاية الإضافة ==========
                
                try:
                    sent_message = None  # ========== إضافة ==========
                    
                    if broadcast_photo:
                        # إرسال صورة مع نص مع دعم MarkdownV2
                        sent_message = await context.bot.send_photo(
                            chat_id=user_id,
                            photo=broadcast_photo,
                            caption=message_text if message_text else "",
                            parse_mode=ParseMode.MARKDOWN_V2
                        )
                    else:
                        # إرسال نص فقط مع دعم MarkdownV2
                        sent_message = await context.bot.send_message(
                            chat_id=user_id,
                            text=message_text,
                            parse_mode=ParseMode.MARKDOWN_V2
                        )
                    
                    # ========== إضافة جديدة: تتبع الرسالة ==========
                    if sent_message and original_message_id:
                        track_bot_message(
                            DATABASE_FILE,
                            original_message_id,
                            admin_chat_id,
                            user_id,
                            user_id,
                            sent_message.message_id
                        )
                    # ========== نهاية الإضافة ==========
                    
                    success_count += 1
                    # توقف قصير لتجنب حدود التيليجرام
                    await asyncio.sleep(0.05)
                except Exception as e:
                    failed_count += 1
                    print(f"فشل إرسال البث للمستخدم {user_id}: {e}")
        else:
            # إرسال للمستخدمين المخصصين
            valid_users = context.user_data.get('broadcast_valid_users', [])
            for user_id, name, original in valid_users:
                
                # ========== إضافة: تخطي الأدمن ==========
                if user_id == admin_id:
                    continue
                # ========== نهاية الإضافة ==========
                
                try:
                    sent_message = None  # ========== إضافة ==========
                    
                    if broadcast_photo:
                        # إرسال صورة مع نص مع دعم MarkdownV2
                        sent_message = await context.bot.send_photo(
                            chat_id=user_id,
                            photo=broadcast_photo,
                            caption=message_text if message_text else "",
                            parse_mode=ParseMode.MARKDOWN_V2
                        )
                    else:
                        # إرسال نص فقط مع دعم MarkdownV2
                        sent_message = await context.bot.send_message(
                            chat_id=user_id,
                            text=message_text,
                            parse_mode=ParseMode.MARKDOWN_V2
                        )
                    
                    # ========== إضافة جديدة: تتبع الرسالة ==========
                    if sent_message and original_message_id:
                        track_bot_message(
                            DATABASE_FILE,
                            original_message_id,
                            admin_chat_id,
                            user_id,
                            user_id,
                            sent_message.message_id
                        )
                    # ========== نهاية الإضافة ==========
                    
                    success_count += 1
                except Exception as e:
                    failed_count += 1
                    print(f"فشل إرسال البث للمستخدم {user_id}: {e}")
        
        result_message = f"""✅ تم إرسال الإعلان

📊 الإحصائيات:
✅ نجح الإرسال: {success_count}
❌ فشل الإرسال: {failed_count}
📊 المجموع: {success_count + failed_count}"""

        await query.edit_message_text(result_message)
        
        # تنظيف البيانات المؤقتة
        broadcast_keys = ['broadcast_type', 'broadcast_message', 'broadcast_users_input', 'broadcast_valid_users', 'broadcast_photo']
        for key in broadcast_keys:
            context.user_data.pop(key, None)
        
        # إعادة تفعيل كيبورد الأدمن
        await restore_admin_keyboard(context, update.effective_chat.id, "📊 تم إرسال البث بنجاح")
            
    elif query.data == "cancel_broadcast":
        await query.edit_message_text("❌ تم إلغاء الإعلان.")
        
        # تنظيف البيانات المؤقتة
        broadcast_keys = ['broadcast_type', 'broadcast_message', 'broadcast_users_input', 'broadcast_valid_users', 'broadcast_photo']
        for key in broadcast_keys:
            context.user_data.pop(key, None)
        
        # إعادة تفعيل كيبورد الأدمن
        await restore_admin_keyboard(context, update.effective_chat.id)
    
    return ConversationHandler.END


async def handle_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء عملية البث"""
    # التحقق من صلاحيات الأدمن
    if not context.user_data.get('is_admin', False):
        await update.message.reply_text("❌ هذه الخدمة مخصصة للأدمن فقط!")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("📢 إرسال للجميع", callback_data="broadcast_all")],
        [InlineKeyboardButton("👥 إرسال لمستخدمين مخصصين", callback_data="broadcast_custom")],
        [InlineKeyboardButton("🔙 العودة", callback_data="back_to_admin")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📢 قائمة البث\n\nاختر نوع الإرسال:",
        reply_markup=reply_markup
    )
    
    return BROADCAST_MESSAGE  # الانتقال لحالة انتظار اختيار نوع البث

async def handle_cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إلغاء البث"""
    query = update.callback_query
    await query.answer()
    
    # تنظيف البيانات المؤقتة مع الحفاظ على حالة الأدمن
    clean_user_data_preserve_admin(context)
    
    await query.edit_message_text("❌ تم إلغاء عملية البث")
    
    # إعادة تفعيل كيبورد الأدمن الرئيسي
    await restore_admin_keyboard(context, update.effective_chat.id, "🔧 لوحة الأدمن جاهزة للاستخدام")
    
    return ConversationHandler.END

# ===== معالج الأخطاء الشامل =====

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج شامل للأخطاء"""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    
    try:
        # تنظيف البيانات المؤقتة
        if hasattr(context, 'user_data') and context.user_data:
            clean_user_data_preserve_admin(context)
        
        # محاولة إرسال رسالة للمستخدم
        if update and hasattr(update, 'effective_chat') and update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ حدث خطأ تقني. يرجى استخدام /start لإعادة تشغيل البوت",
                    reply_markup=ReplyKeyboardRemove()
                )
            except Exception as send_error:
                logger.error(f"Could not send error message: {send_error}")
        
        # تسجيل تفاصيل الخطأ
        if update and hasattr(update, 'effective_user'):
            user_id = update.effective_user.id
            try:
                db.log_action(user_id, "error_occurred", str(context.error))
            except Exception as log_error:
                logger.error(f"Could not log error: {log_error}")
        
    except Exception as handler_error:
        logger.error(f"Error in error handler: {handler_error}")

# ===== نظام مراقبة صحة البوت =====

class BotHealthMonitor:
    """نظام مراقبة صحة البوت"""
    
    def __init__(self):
        self.stuck_users: Dict[int, float] = {}  # user_id -> timestamp
        self.conversation_timeouts: Dict[int, float] = {}
        self.error_count: int = 0
        self.last_activity: float = time.time()
        
    def mark_user_activity(self, user_id: int):
        """تسجيل نشاط المستخدم"""
        self.stuck_users.pop(user_id, None)
        self.conversation_timeouts.pop(user_id, None)
        self.last_activity = time.time()
        
    def mark_user_stuck(self, user_id: int, conversation_state: str):
        """تسجيل مستخدم عالق"""
        self.stuck_users[user_id] = time.time()
        logger.warning(f"User {user_id} stuck in state: {conversation_state}")
        
    def mark_conversation_timeout(self, user_id: int):
        """تسجيل انتهاء مهلة المحادثة"""
        self.conversation_timeouts[user_id] = time.time()
        
    def increment_error(self):
        """زيادة عداد الأخطاء"""
        self.error_count += 1
        
    def get_stuck_users(self, timeout_minutes: int = 30) -> Set[int]:
        """الحصول على المستخدمين العالقين"""
        current_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        return {
            user_id for user_id, timestamp in self.stuck_users.items()
            if current_time - timestamp > timeout_seconds
        }
        
    def cleanup_stuck_users(self, timeout_minutes: int = 30):
        """تنظيف المستخدمين العالقين"""
        stuck_users = self.get_stuck_users(timeout_minutes)
        
        for user_id in stuck_users:
            try:
                db.log_action(user_id, "auto_unstuck", "System auto-cleanup")
                self.stuck_users.pop(user_id, None)
                logger.info(f"Auto-cleaned stuck user: {user_id}")
            except Exception as e:
                logger.error(f"Failed to cleanup stuck user {user_id}: {e}")
                
    def get_health_status(self) -> Dict:
        """الحصول على حالة صحة البوت"""
        return {
            "stuck_users_count": len(self.stuck_users),
            "timeout_conversations": len(self.conversation_timeouts),
            "error_count": self.error_count,
            "last_activity": datetime.fromtimestamp(self.last_activity),
            "uptime_minutes": (time.time() - self.last_activity) / 60
        }
    
    async def start_monitoring(self):
        """بدء مراقبة صحة البوت"""
        logger.info("Starting bot health monitoring...")
        
        # تشغيل روتين الفحص في الخلفية
        asyncio.create_task(health_check_routine())
        
        # تسجيل بداية المراقبة
        self.last_activity = time.time()
        logger.info("Bot health monitoring started successfully")

# إنشاء مراقب الصحة
# تم إزالة health_monitor لحل مشكلة تسجيل الخروج التلقائي

# تم إزالة دالة health_check_routine لحل مشكلة تسجيل الخروج التلقائي

async def initialize_cleanup_scheduler(application):
    """تهيئة جدولة التنظيف التلقائي"""
    try:
        async def scheduled_cleanup():
            while True:
                await asyncio.sleep(3600)
                try:
                    logger.info("Running scheduled cleanup...")
                    await cleanup_old_orders()
                except Exception as e:
                    logger.error(f"Error in scheduled cleanup: {e}")
        
        application.create_task(scheduled_cleanup())
        logger.info("Cleanup scheduler initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize cleanup scheduler: {e}")

def setup_bot():
    """إعداد البوت بدون تشغيله"""
    print("🔧 فحص إعدادات البوت...")
    
    if not TOKEN:
        print("❌ التوكن غير موجود!")
        print("يرجى إضافة التوكن في بداية الملف!")
        print("1. اذهب إلى @BotFather على تيليجرام")
        print("2. أنشئ بوت جديد وانسخ التوكن")
        print("3. ضع التوكن في متغير TOKEN في بداية الملف")
        return None
    
    print(f"✅ التوكن موجود: {TOKEN[:10]}...{TOKEN[-10:]}")
    print("🔧 بدء تهيئة البوت...")
    
    # تحميل الأسعار المحفوظة عند بدء التشغيل
    load_saved_prices()
    
    # تحميل معرف الأدمن من آخر تسجيل دخول ناجح
    try:
        global ADMIN_CHAT_ID
        admin_logs = db.execute_query("SELECT user_id FROM logs WHERE action = 'admin_login_success' ORDER BY timestamp DESC LIMIT 1")
        if admin_logs:
            ADMIN_CHAT_ID = admin_logs[0][0]
            print(f"✅ تم تحميل معرف الأدمن: {ADMIN_CHAT_ID}")
            # تحديث المتغيرات العالمية في dynamic_buttons_handler عند بدء البوت
            update_admin_globals(active_admins=ACTIVE_ADMINS, admin_chat_id=ADMIN_CHAT_ID)
        else:
            print("⚠️ لم يتم العثور على تسجيل دخول أدمن سابق")
    except Exception as e:
        print(f"⚠️ خطأ في تحميل معرف الأدمن: {e}")
    
    # إنشاء ملفات المساعدة
    print("📁 إنشاء ملفات المساعدة...")
    create_requirements_file()
    create_readme_file()
    print("✅ تم إنشاء ملفات المساعدة")
    
    # إنشاء التطبيق
    print("⚡ إنشاء تطبيق التيليجرام...")
    try:
        application = Application.builder().token(TOKEN).build()
        print("✅ تم إنشاء التطبيق بنجاح")
        
        # اختبار الاتصال مع تيليجرام
        print("🌐 اختبار الاتصال مع خوادم تيليجرام...")
        print("🌐 سيتم اختبار الاتصال عند بدء التشغيل...")
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء التطبيق أو الاتصال: {e}")
        return None
    
    # المعالجات ستتم إضافتها في setup_bot()
    
    print("📊 قاعدة البيانات جاهزة")
    print("⚡ البوت يعمل الآن!")
    print(f"🔑 التوكن: {TOKEN[:10]}...")
    print("💡 في انتظار الرسائل...")
    print("✅ البوت جاهز للتشغيل!")
    
    return application
    
    
async def handle_quantity_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار الكمية من قبل الأدمن"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "quantity_single":
        context.user_data["quantity"] = "5"
        # الانتقال لاختيار نوع البروكسي العادي
        keyboard = [
            [InlineKeyboardButton("Static ISP", callback_data="proxy_type_static_isp")],
            [InlineKeyboardButton("Static Residential", callback_data="proxy_type_static_residential")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="cancel_processing")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # الحفاظ على المعلومات الأصلية مع إضافة سؤال نوع البروكسي
        original_message = context.user_data.get('original_order_message', '')
        combined_message = f"{original_message}\n\n━━━━━━━━━━━━━━━\n✅ تم قبول الدفع للطلب\n\n🆔 معرف الطلب: <code>{context.user_data['processing_order_id']}</code>\n📝 الطلب: بروكسي ستاتيك\n\n📋 الطلب جاهز للمعالجة والإرسال للمستخدم.\n\n━━━━━━━━━━━━━━━\n2️⃣ اختر نوع البروكسي:"
        
        await query.edit_message_text(
            combined_message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        return PROCESS_ORDER
        
    elif query.data == "quantity_package_socks":
        context.user_data["quantity"] = "10"
        
        # إرسال رسالة منفصلة لوضع الباكج مع زر إلغاء المعالجة
        package_keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="cancel_processing")]
        ]
        package_reply_markup = InlineKeyboardMarkup(package_keyboard)
        
        package_instruction_message = f"""📦 <b>وضع الباكج</b>

🆔 معرف الطلب: <code>{context.user_data['processing_order_id']}</code>
📝 نوع الطلب: باكج

━━━━━━━━━━━━━━━
يرجى كتابة الرسالة المخصصة التي تريد إرسالها للمستخدم:

💡 يمكنك تضمين جميع تفاصيل البروكسي في رسالة واحدة
💡 الرسالة ستُرسل كما تكتبها بدون تعديل
💡 يمكنك استخدام أي تنسيق تريده"""
        
        # إرسال رسالة منفصلة للباكج
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=package_instruction_message,
            reply_markup=package_reply_markup,
            parse_mode="Markdown"
        )
        
        # تحديث الرسالة الأصلية لإبقاء زر العودة لاختيار الكمية
        original_keyboard = [
            [InlineKeyboardButton("🔙 العودة لاختيار الكمية", callback_data="back_to_quantity")]
        ]
        original_reply_markup = InlineKeyboardMarkup(original_keyboard)
        
        # الحفاظ على المعلومات الأصلية مع تحديث الحالة
        original_message = context.user_data.get('original_order_message', '')
        updated_message = f"{original_message}\n\n━━━━━━━━━━━━━━━\n✅ تم قبول الدفع للطلب\n📝 الطلب: باكج\n📋 الطلب جاهز للمعالجة والإرسال للمستخدم"
        
        await query.edit_message_text(
            updated_message,
            reply_markup=original_reply_markup,
            parse_mode="Markdown"
        )
        return PACKAGE_MESSAGE

async def handle_package_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة رسالة الباكج المخصصة"""
    if update.message and update.message.text:
        package_message = update.message.text
        context.user_data["package_message"] = package_message
        
        # عرض معاينة الرسالة مع خيارات التأكيد
        await show_package_preview_confirmation(update, context, package_message)
        return PACKAGE_CONFIRMATION
    
    return PACKAGE_MESSAGE

async def show_package_preview_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, package_message: str) -> None:
    """عرض معاينة رسالة الباكج مع خيارات التأكيد"""
    order_id = context.user_data.get("processing_order_id", "غير معروف")
    
    preview_message = f"""📋 <b>معاينة رسالة الباكج</b>

🆔 معرف الطلب: {order_id}
📦 نوع الطلب: باكج

━━━━━━━━━━━━━━━
<b>الرسالة التي ستُرسل للمستخدم:</b>

{package_message}
━━━━━━━━━━━━━━━

❓ هل تريد إرسال هذه الرسالة للمستخدم وإتمام الطلب؟"""
    
    keyboard = [
        [InlineKeyboardButton("✅ إرسال وإتمام الطلب", callback_data="confirm_send_package")],
        [InlineKeyboardButton("❌ لا", callback_data="decline_send_package")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        preview_message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_package_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة تأكيد إرسال الباكج"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_send_package":
        # إرسال الباكج للمستخدم وإتمام الطلب
        package_message = context.user_data.get("package_message", "")
        await send_package_to_user_from_confirmation(query, context, package_message)
        return ConversationHandler.END
        
    elif query.data == "decline_send_package":
        # عرض خيارات ماذا تريد أن تفعل
        await show_package_action_choices(query, context)
        return PACKAGE_ACTION_CHOICE
    
    return PACKAGE_CONFIRMATION

async def show_package_action_choices(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض خيارات العمل بعد رفض إرسال الباكج"""
    message = """❓ <b>ماذا تريد أن تفعل؟</b>

يمكنك اختيار أحد الخيارات التالية:"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 إعادة تصميم الباكج", callback_data="redesign_package")],
        [InlineKeyboardButton("📋 مراجعة الطلب لاحقاً", callback_data="review_later")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_package_action_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار العمل بعد رفض الباكج"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "redesign_package":
        # إرسال رسالة منفصلة لإعادة تصميم الباكج
        package_keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="cancel_processing")]
        ]
        package_reply_markup = InlineKeyboardMarkup(package_keyboard)
        
        redesign_message = f"""📦 <b>إعادة تصميم الباكج</b>

🆔 معرف الطلب: <code>{context.user_data['processing_order_id']}</code>

━━━━━━━━━━━━━━━
يرجى كتابة الرسالة المخصصة الجديدة التي تريد إرسالها للمستخدم:

💡 يمكنك تضمين جميع تفاصيل البروكسي في رسالة واحدة
💡 الرسالة ستُرسل كما تكتبها بدون تعديل
💡 يمكنك استخدام أي تنسيق تريده"""
        
        # إرسال رسالة منفصلة لإعادة التصميم
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=redesign_message,
            reply_markup=package_reply_markup,
            parse_mode="Markdown"
        )
        
        # حذف رسالة المعاينة السابقة
        await query.delete_message()
        
        return PACKAGE_MESSAGE
        
    elif query.data == "review_later":
        # الخروج من الحلقة دون تصنيف الطلب
        order_id = context.user_data.get("processing_order_id", "غير معروف")
        
        await query.edit_message_text(
            f"📋 <b>مراجعة لاحقاً</b>\n\n🆔 معرف الطلب: {order_id}\n\n✅ تم الخروج من معالجة الطلب\n❗ الطلب لا يزال في حالة معلق ويمكن معالجته لاحقاً\n\n💡 لن يتم تصنيف الطلب كناجح أو فاشل",
            parse_mode="Markdown"
        )
        
        # تنظيف البيانات المؤقتة مع الحفاظ على حالة الأدمن
        clean_user_data_preserve_admin(context)
        await restore_admin_keyboard(context, update.effective_chat.id, "🔧 لوحة الأدمن جاهزة للاستخدام")
        
        return ConversationHandler.END
    
    return PACKAGE_ACTION_CHOICE

async def send_package_to_user_from_confirmation(query, context: ContextTypes.DEFAULT_TYPE, package_message: str) -> None:
    """إرسال الباكج للمستخدم من صفحة التأكيد"""
    order_id = context.user_data.get("processing_order_id", "")
    
    # الحصول على معلومات المستخدم والطلب
    user_query = """
        SELECT o.user_id, u.first_name, u.last_name 
        FROM orders o 
        JOIN users u ON o.user_id = u.user_id 
        WHERE o.id = ?
    """
    user_result = db.execute_query(user_query, (order_id,))
    
    if user_result:
        user_id, first_name, last_name = user_result[0]
        user_full_name = f"{first_name} {last_name or ''}".strip()
        
        # إرسال الباكج للمستخدم
        final_message = f"""✅ تم معالجة طلب {user_full_name}

🆔 معرف الطلب: {order_id}
📦 نوع الطلب: باكج

━━━━━━━━━━━━━━━
{package_message}
━━━━━━━━━━━━━━━

📅 التاريخ: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"""
        
        await context.bot.send_message(user_id, final_message, parse_mode="Markdown")
        
        # تحديث حالة الطلب
        db.execute_query(
            "UPDATE orders SET status = 'completed', processed_at = CURRENT_TIMESTAMP, proxy_details = ?, truly_processed = TRUE WHERE id = ?",
            (package_message, order_id)
        )
        
        # التحقق من إضافة رصيد الإحالة لأول عملية شراء
        await check_and_add_referral_bonus(context, user_id, order_id)
        
        # رسالة تأكيد للأدمن
        admin_message = f"""✅ <b>تم إرسال الباكج بنجاح وإتمام الطلب</b>

👤 المستخدم: {user_full_name}
🆔 معرف الطلب: {order_id}
📦 نوع الطلب: باكج

📝 الرسالة المرسلة:
{package_message}

🎉 تم تصنيف الطلب كناجح ونقله للطلبات المكتملة"""

        await query.edit_message_text(admin_message, parse_mode="Markdown")
        
        # تنظيف البيانات المؤقتة مع الحفاظ على حالة الأدمن
        clean_user_data_preserve_admin(context)
        await restore_admin_keyboard(context, query.message.chat_id, "🔧 لوحة الأدمن جاهزة للاستخدام")

async def handle_back_to_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة العودة لاختيار الكمية"""
    query = update.callback_query
    await query.answer()
    
    # تحديد لغة الأدمن (افتراضياً العربية للأدمن)
    admin_language = get_user_language(query.from_user.id)
    
    # إعادة عرض خيارات الكمية
    if admin_language == 'ar':
        keyboard = [
            [InlineKeyboardButton("📦باكج 5", callback_data="quantity_single")],
            [InlineKeyboardButton("📦10 باكج", callback_data="quantity_package")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="cancel_processing")]
        ]
        quantity_text = "1️⃣ اختر الكمية المطلوبة:"
    else:
        keyboard = [
            [InlineKeyboardButton("📦 Package 5", callback_data="quantity_single")],
            [InlineKeyboardButton("📦 Package 10", callback_data="quantity_package")],
            [InlineKeyboardButton("🔙 Back Processing", callback_data="cancel_processing")]
        ]
        quantity_text = "1️⃣ Choose the required quantity:"
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        quantity_text,
        reply_markup=reply_markup
    )
    
    return ENTER_PROXY_QUANTITY

async def handle_proxy_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إدخال كمية البروكسيات"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    try:
        quantity_text = update.message.text.strip()
        
        # التحقق من أن النص يحتوي على رقم صحيح فقط
        if not quantity_text.isdigit():
            await update.message.reply_text(MESSAGES[language]['invalid_quantity'], parse_mode='HTML')
            return ENTER_PROXY_QUANTITY
        
        quantity = int(quantity_text)
        
        # التحقق من أن العدد بين 1 و 100
        if quantity < 1 or quantity > 100:
            await update.message.reply_text(MESSAGES[language]['invalid_quantity'], parse_mode='HTML')
            return ENTER_PROXY_QUANTITY
        
        # حفظ الكمية
        context.user_data['quantity'] = quantity
        
        # إنشاء الطلب مباشرة بدون طرق الدفع
        try:
            # محاولة إنشاء الطلب مباشرة
            user_id = update.effective_user.id
            order_id = await create_order_directly_from_message(update, context, language)
            
            # إرسال رسالة تأكيد
            if language == 'ar':
                success_message = f"""✅ تم إرسال طلبك بنجاح!

🆔 معرف الطلب: {order_id}
⏰ سيتم مراجعة طلبك من قبل الإدارة وإرسال البيانات قريباً

📞 للاستفسار عن الطلب تواصل مع الدعم"""
            else:
                success_message = f"""✅ Your order has been sent successfully!

🆔 Order ID: {order_id}
⏰ Your order will be reviewed by management and data sent soon

📞 For inquiry contact support"""
            
            await update.message.reply_text(success_message, parse_mode='HTML')
            return ConversationHandler.END
            
        except Exception as order_error:
            logger.error(f"Error creating order from message: {order_error}")
            await update.message.reply_text(
                "❌ حدث خطأ في إنشاء الطلب. يرجى المحاولة مرة أخرى أو التواصل مع الدعم.",
                parse_mode='HTML'
            )
            return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in handle_proxy_quantity: {e}")
        await update.message.reply_text(MESSAGES[language]['invalid_quantity'], parse_mode='HTML')
        return ENTER_PROXY_QUANTITY

async def handle_edit_services_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء تعديل رسالة الخدمات - طلب النص العربي أولاً"""
    if not context.user_data.get('is_admin'):
        return ConversationHandler.END
    
    keyboard = [[KeyboardButton("🔙 رجوع")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "📝 <b>خطوة 1 من 2</b>\n\nأدخل رسالة الخدمات بالعربية:\n\n💡 يمكنك استخدام تنسيق Markdown للتنسيق",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    return EDIT_SERVICES_MESSAGE_AR

async def handle_services_message_ar_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إدخال رسالة الخدمات العربية"""
    if not context.user_data.get('is_admin'):
        return ConversationHandler.END
    
    if update.message.text == "🔙 رجوع":
        await handle_admin_settings_menu(update, context)
        return ConversationHandler.END
    
    # حفظ النص العربي مؤقتاً
    context.user_data['temp_services_ar'] = update.message.text
    
    await update.message.reply_text(
        "✅ تم حفظ النص العربي!\n\n📝 <b>خطوة 2 من 2</b>\n\nالآن أدخل رسالة الخدمات بالإنجليزية:\n\n💡 يمكنك استخدام تنسيق Markdown للتنسيق",
        parse_mode='HTML'
    )
    return EDIT_SERVICES_MESSAGE_EN

async def handle_services_message_en_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إدخال رسالة الخدمات الإنجليزية وحفظ كلا النصين"""
    if not context.user_data.get('is_admin'):
        return ConversationHandler.END
    
    if update.message.text == "🔙 رجوع":
        await handle_admin_settings_menu(update, context)
        return ConversationHandler.END
    
    ar_message = context.user_data.get('temp_services_ar', '')
    en_message = update.message.text
    
    # حفظ الرسالتين للغتين
    try:
        db.execute_query("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('services_message_ar', ar_message))
        db.execute_query("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('services_message_en', en_message))
        
        await update.message.reply_text(
            f"✅ تم تحديث رسالة الخدمات بنجاح للغتين!\n\n🇸🇦 <b>النص العربي:</b>\n{ar_message}\n\n🇺🇸 <b>النص الإنجليزي:</b>\n{en_message}",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error saving services message: {e}")
        await update.message.reply_text(
            "❌ حدث خطأ في حفظ الرسالة. يرجى المحاولة مرة أخرى."
        )
    
    # تنظيف البيانات المؤقتة
    context.user_data.pop('temp_services_ar', None)
    
    # إعادة تفعيل كيبورد الأدمن
    await handle_admin_settings_menu(update, context)
    return ConversationHandler.END

# معالج معالجة الطلبات للأدمن
process_order_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(handle_process_order, pattern="^process_")],
    states={
        PROCESS_ORDER: [
            CallbackQueryHandler(handle_payment_success, pattern="^payment_success$"),
            CallbackQueryHandler(handle_payment_failed, pattern="^payment_failed$"),
            CallbackQueryHandler(handle_quantity_selection, pattern="^quantity_"),
            CallbackQueryHandler(handle_proxy_details_input, pattern="^proxy_type_"),
            CallbackQueryHandler(handle_back_to_quantity, pattern="^back_to_quantity$"),
            CallbackQueryHandler(handle_cancel_processing, pattern="^cancel_processing$"),
            # معالج الرسائل النصية عندما ينتظر البوت رسالة الأدمن
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_message_for_proxy)
        ],
        ENTER_PROXY_TYPE: [
            CallbackQueryHandler(handle_proxy_details_input, pattern="^proxy_type_"),
            CallbackQueryHandler(handle_cancel_processing, pattern="^cancel_processing$")
        ],
        ENTER_PROXY_ADDRESS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_proxy_details_input),
            CallbackQueryHandler(handle_cancel_proxy_setup, pattern="^cancel_proxy_setup$"),
            CallbackQueryHandler(handle_cancel_processing, pattern="^cancel_processing$")
        ],
        ENTER_PROXY_PORT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_proxy_details_input),
            CallbackQueryHandler(handle_cancel_proxy_setup, pattern="^cancel_proxy_setup$"),
            CallbackQueryHandler(handle_cancel_processing, pattern="^cancel_processing$")
        ],
        ENTER_COUNTRY: [
            CallbackQueryHandler(handle_admin_country_selection, pattern="^admin_country_"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_proxy_details_input),
            CallbackQueryHandler(handle_cancel_proxy_setup, pattern="^cancel_proxy_setup$"),
            CallbackQueryHandler(handle_cancel_processing, pattern="^cancel_processing$")
        ],
        ENTER_STATE: [
            CallbackQueryHandler(handle_admin_country_selection, pattern="^admin_state_"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_proxy_details_input),
            CallbackQueryHandler(handle_cancel_proxy_setup, pattern="^cancel_proxy_setup$"),
            CallbackQueryHandler(handle_cancel_processing, pattern="^cancel_processing$")
        ],
        ENTER_USERNAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_proxy_details_input),
            CallbackQueryHandler(handle_cancel_proxy_setup, pattern="^cancel_proxy_setup$"),
            CallbackQueryHandler(handle_cancel_processing, pattern="^cancel_processing$")
        ],
        ENTER_PASSWORD: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_proxy_details_input),
            CallbackQueryHandler(handle_cancel_proxy_setup, pattern="^cancel_proxy_setup$"),
            CallbackQueryHandler(handle_cancel_processing, pattern="^cancel_processing$")
        ],
        ENTER_THANK_MESSAGE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_proxy_details_input),
            CallbackQueryHandler(handle_cancel_proxy_setup, pattern="^cancel_proxy_setup$"),
            CallbackQueryHandler(handle_order_completed_success, pattern="^order_completed_success$"),
            CallbackQueryHandler(handle_cancel_processing, pattern="^cancel_processing$")
        ],
        CUSTOM_MESSAGE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_message_for_proxy),
            CallbackQueryHandler(handle_custom_message_choice, pattern="^(send_custom_message|no_custom_message|send_custom_message_failed|no_custom_message_failed)$"),
            CallbackQueryHandler(handle_cancel_custom_message, pattern="^cancel_custom_message$"),
            CallbackQueryHandler(handle_cancel_processing, pattern="^cancel_processing$")
        ],
        PACKAGE_MESSAGE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_package_message),
            CallbackQueryHandler(handle_cancel_processing, pattern="^cancel_processing$"),
            CallbackQueryHandler(handle_back_to_quantity, pattern="^back_to_quantity$")
        ],
        PACKAGE_CONFIRMATION: [
            CallbackQueryHandler(handle_package_confirmation, pattern="^(confirm_send_package|decline_send_package)$"),
            CallbackQueryHandler(handle_cancel_processing, pattern="^cancel_processing$")
        ],
        PACKAGE_ACTION_CHOICE: [
            CallbackQueryHandler(handle_package_action_choice, pattern="^(redesign_package|review_later)$"),
            CallbackQueryHandler(handle_cancel_processing, pattern="^cancel_processing$")
        ]
    },
    fallbacks=[
        # الأوامر الأساسية
        CommandHandler("start", start),
        CommandHandler("cancel", lambda u, c: ConversationHandler.END),
        CommandHandler("reset", handle_reset_command),
        CommandHandler("cleanup", handle_cleanup_command),
        CommandHandler("help", help_command),
        # معالجة كلمات الإلغاء
        MessageHandler(filters.Regex("^(إلغاء|cancel|خروج|exit|stop)$"), handle_stuck_conversation),
        # معالجة أي callback query غير متوقع
        CallbackQueryHandler(handle_stuck_conversation),
        # معالجة أي رسالة نصية أو أمر غير متوقع
        MessageHandler(filters.TEXT | filters.COMMAND, handle_stuck_conversation),
        # معالجة الملفات والوسائط غير المرغوبة
        MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.AUDIO, handle_stuck_conversation)
    ]
)

# معالج تغيير كلمة المرور
password_change_conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^🔐 تغيير كلمة المرور$"), change_admin_password)],
    states={
        ADMIN_LOGIN: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password_change),
            CallbackQueryHandler(handle_cancel_password_change, pattern="^cancel_password_change$")
        ],
    },
    fallbacks=[
        # الأوامر الأساسية
        CommandHandler("start", start),
        CommandHandler("cancel", lambda u, c: ConversationHandler.END),
        CommandHandler("reset", handle_reset_command),
        CommandHandler("cleanup", handle_cleanup_command),
        CommandHandler("help", help_command),
        # معالجة كلمات الإلغاء
        MessageHandler(filters.Regex("^(إلغاء|cancel|خروج|exit|stop)$"), handle_stuck_conversation),
        # معالجة أي callback query غير متوقع
        CallbackQueryHandler(handle_stuck_conversation),
        # معالجة أي رسالة نصية أو أمر غير متوقع
        MessageHandler(filters.TEXT | filters.COMMAND, handle_stuck_conversation),
        # معالجة الملفات والوسائط غير المرغوبة
        MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.AUDIO, handle_stuck_conversation)
    ]
)

    # معالج شامل لجميع وظائف الأدمن (يدعم العربية والإنجليزية)
admin_functions_conv_handler = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex("^(🔍 استعلام عن مستخدم|🔍 User Inquiry)$"), handle_admin_user_lookup),
        MessageHandler(filters.Regex("^(🗑️ إعادة تعيين رصيد المستخدم|🗑️ Reset User Balance)$"), reset_user_balance),
        MessageHandler(filters.Regex("^(💵 تحديد مبلغ الإحالة|💵 Set Referral Amount)$"), set_referral_amount),
        MessageHandler(filters.Regex("^(💰 تعديل سعر النقطة|💰 Set Credit Price)$"), set_credit_price),
        MessageHandler(filters.Regex("^(📱 تعديل سعر رقم Non-Voip|📱 Set Non-Voip Price)$"), set_nonvoip_price),
        MessageHandler(filters.Regex("^(🔍 استعلام عن طلب|🔍 Order Inquiry)$"), admin_order_inquiry),
        MessageHandler(filters.Regex("^(🔕 إدارة الإشعارات|🔕 Manage Notifications)$"), set_quiet_hours),
        MessageHandler(filters.Regex("^(🗑️ حذف جميع الطلبات|🗑️ Delete All Orders)$"), delete_all_orders),
    ],
    states={
        USER_LOOKUP: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_lookup_unified),
            CallbackQueryHandler(handle_cancel_user_lookup, pattern="^cancel_user_lookup$"),
            CallbackQueryHandler(handle_cancel_balance_reset, pattern="^cancel_balance_reset$")
        ],
        REFERRAL_AMOUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_referral_amount_update),
            CallbackQueryHandler(handle_cancel_referral_amount, pattern="^cancel_referral_amount$")
        ],
        SET_PRICE_NONVOIP: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_nonvoip_price_update),
            CallbackQueryHandler(handle_cancel_nonvoip_price, pattern="^cancel_nonvoip_price$")
        ],
        SET_POINT_PRICE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_credit_price_update),
            CallbackQueryHandler(handle_cancel_credit_price, pattern="^cancel_credit_price$")
        ],
        ADMIN_ORDER_INQUIRY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_order_inquiry),
            CallbackQueryHandler(handle_cancel_order_inquiry, pattern="^cancel_order_inquiry$")
        ],
        QUIET_HOURS: [CallbackQueryHandler(handle_quiet_hours_selection, pattern="^quiet_")],
        CONFIRM_DELETE_ALL_ORDERS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_confirm_delete_all_orders)
        ]
    },
    fallbacks=[
        # الأوامر الأساسية
        CommandHandler("start", start),
        CommandHandler("cancel", lambda u, c: ConversationHandler.END),
        CommandHandler("reset", handle_reset_command),
        CommandHandler("cleanup", handle_cleanup_command),
        CommandHandler("help", help_command),
        # معالجة كلمات الإلغاء
        MessageHandler(filters.Regex("^(إلغاء|cancel|خروج|exit|stop)$"), handle_stuck_conversation),
        # معالجة أي callback query غير متوقع
        CallbackQueryHandler(handle_stuck_conversation),
        # معالجة أي رسالة نصية أو أمر غير متوقع
        MessageHandler(filters.TEXT | filters.COMMAND, handle_stuck_conversation),
        # معالجة الملفات والوسائط غير المرغوبة
        MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.AUDIO, handle_stuck_conversation)
    ]
)

admin_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("admin_login", admin_login)],
    states={
        ADMIN_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_password)],
        ADMIN_MENU: [CallbackQueryHandler(handle_admin_menu_actions)],
        USER_LOOKUP: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_lookup_unified),
            CallbackQueryHandler(handle_cancel_user_lookup, pattern="^cancel_user_lookup$")
        ]
    },
    fallbacks=[
        # الأوامر الأساسية
        CommandHandler("start", start),
        CommandHandler("cancel", lambda u, c: ConversationHandler.END),
        CommandHandler("reset", handle_reset_command),
        CommandHandler("cleanup", handle_cleanup_command),
        CommandHandler("help", help_command),
        # معالجة كلمات الإلغاء
        MessageHandler(filters.Regex("^(إلغاء|cancel|خروج|exit|stop)$"), handle_stuck_conversation),
        # معالجة أي callback query غير متوقع
        CallbackQueryHandler(handle_stuck_conversation),
        # معالجة أي رسالة نصية أو أمر غير متوقع
        MessageHandler(filters.TEXT | filters.COMMAND, handle_stuck_conversation),
        # معالجة الملفات والوسائط غير المرغوبة
        MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.AUDIO, handle_stuck_conversation)
    ]
)
    
    # معالج إثبات الدفع
payment_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(handle_payment_method_selection, pattern="^payment_")],
    states={
        ENTER_PROXY_QUANTITY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_proxy_quantity),
            CallbackQueryHandler(handle_cancel_payment_proof, pattern="^cancel_payment_proof$")
        ],
        PAYMENT_PROOF: [
            MessageHandler(filters.ALL & ~filters.COMMAND, handle_payment_proof),
            CallbackQueryHandler(handle_cancel_payment_proof, pattern="^cancel_payment_proof$")
        ],
    },
    fallbacks=[
        # الأوامر الأساسية
        CommandHandler("start", start),
        CommandHandler("cancel", lambda u, c: ConversationHandler.END),
        CommandHandler("reset", handle_reset_command),
        CommandHandler("cleanup", handle_cleanup_command),
        CommandHandler("help", help_command),
        # معالجة كلمات الإلغاء
        MessageHandler(filters.Regex("^(إلغاء|cancel|خروج|exit|stop)$"), handle_stuck_conversation),
        # معالجة أي callback query غير متوقع
        CallbackQueryHandler(handle_stuck_conversation),
        # معالجة أي رسالة نصية أو أمر غير متوقع
        MessageHandler(filters.TEXT | filters.COMMAND, handle_stuck_conversation),
        # معالجة الملفات والوسائط غير المرغوبة
        MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.AUDIO, handle_stuck_conversation)
    ]
)
    
    # معالج البث
broadcast_conv_handler = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex("^(📢 البث|📢 Broadcast)$"), handle_broadcast_start),
        CallbackQueryHandler(handle_broadcast_selection, pattern="^(broadcast_all|broadcast_custom)$")
    ],
    states={
        BROADCAST_MESSAGE: [
            CallbackQueryHandler(handle_broadcast_selection, pattern="^(broadcast_all|broadcast_custom)$"),
            MessageHandler((filters.TEXT & ~filters.COMMAND) | filters.PHOTO, handle_broadcast_message),
            CallbackQueryHandler(handle_cancel_broadcast, pattern="^cancel_broadcast$")
        ],
        BROADCAST_USERS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_users),
            CallbackQueryHandler(handle_cancel_broadcast, pattern="^cancel_broadcast$")
        ],
        BROADCAST_CONFIRM: [CallbackQueryHandler(handle_broadcast_confirmation, pattern="^(confirm_broadcast|cancel_broadcast)$")],

    },
    fallbacks=[
        # الأوامر الأساسية
        CommandHandler("start", start),
        CommandHandler("cancel", lambda u, c: ConversationHandler.END),
        CommandHandler("reset", handle_reset_command),
        CommandHandler("cleanup", handle_cleanup_command),
        CommandHandler("help", help_command),
        # معالجة كلمات الإلغاء
        MessageHandler(filters.Regex("^(إلغاء|cancel|خروج|exit|stop)$"), handle_stuck_conversation),
        # معالجة أي callback query غير متوقع
        CallbackQueryHandler(handle_stuck_conversation),
        # معالجة أي رسالة نصية أو أمر غير متوقع
        MessageHandler(filters.TEXT | filters.COMMAND, handle_stuck_conversation),
        # معالجة الملفات والوسائط غير المرغوبة
        MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.AUDIO, handle_stuck_conversation)
    ]
)

# معالج تعديل رسالة الخدمات
services_message_conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^(📝 تحرير رسالة الخدمات|📝 Edit Services Message)$"), handle_edit_services_message)],
    states={
        EDIT_SERVICES_MESSAGE_AR: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_services_message_ar_input),
        ],
        EDIT_SERVICES_MESSAGE_EN: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_services_message_en_input),
        ],
    },
    fallbacks=[
        CommandHandler("start", start),
        CommandHandler("cancel", lambda u, c: ConversationHandler.END),
        CommandHandler("reset", handle_reset_command),
        MessageHandler(filters.Regex("^(🔙 رجوع|🔙 Back)$"), lambda u, c: ConversationHandler.END),
        CallbackQueryHandler(lambda u, c: ConversationHandler.END),
        MessageHandler(filters.TEXT | filters.COMMAND, lambda u, c: ConversationHandler.END),
    ],
    per_message=False
)

async def handle_edit_exchange_rate_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء تعديل رسالة سعر الصرف - طلب النص العربي أولاً"""
    if not context.user_data.get('is_admin'):
        return ConversationHandler.END
    
    keyboard = [[KeyboardButton("🔙 رجوع")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "📝 <b>خطوة 1 من 2</b>\n\nأدخل رسالة سعر الصرف بالعربية:\n\n💡 يمكنك استخدام تنسيق Markdown للتنسيق",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    return EDIT_EXCHANGE_RATE_MESSAGE_AR


async def handle_exchange_rate_message_ar_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إدخال رسالة سعر الصرف العربية"""
    if not context.user_data.get('is_admin'):
        return ConversationHandler.END
    
    if update.message.text == "🔙 رجوع":
        await handle_admin_settings_menu(update, context)
        return ConversationHandler.END
    
    # حفظ النص العربي مؤقتاً
    context.user_data['temp_exchange_ar'] = update.message.text
    
    await update.message.reply_text(
        "✅ تم حفظ النص العربي!\n\n📝 <b>خطوة 2 من 2</b>\n\nالآن أدخل رسالة سعر الصرف بالإنجليزية:\n\n💡 يمكنك استخدام تنسيق Markdown للتنسيق",
        parse_mode='HTML'
    )
    return EDIT_EXCHANGE_RATE_MESSAGE_EN

async def handle_exchange_rate_message_en_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إدخال رسالة سعر الصرف الإنجليزية وحفظ كلا النصين"""
    if not context.user_data.get('is_admin'):
        return ConversationHandler.END
    
    if update.message.text == "🔙 رجوع":
        await handle_admin_settings_menu(update, context)
        return ConversationHandler.END
    
    ar_message = context.user_data.get('temp_exchange_ar', '')
    en_message = update.message.text
    
    # حفظ الرسالتين للغتين
    try:
        db.execute_query("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('exchange_rate_message_ar', ar_message))
        db.execute_query("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('exchange_rate_message_en', en_message))
        
        await update.message.reply_text(
            f"✅ تم تحديث رسالة سعر الصرف بنجاح للغتين!\n\n🇸🇦 <b>النص العربي:</b>\n{ar_message}\n\n🇺🇸 <b>النص الإنجليزي:</b>\n{en_message}",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error saving exchange rate message: {e}")
        await update.message.reply_text(
            "❌ حدث خطأ في حفظ الرسالة. يرجى المحاولة مرة أخرى."
        )
    
    # تنظيف البيانات المؤقتة
    context.user_data.pop('temp_exchange_ar', None)
    
    # إعادة تفعيل كيبورد الأدمن
    await handle_admin_settings_menu(update, context)
    return ConversationHandler.END


# معالج تعديل رسالة سعر الصرف
exchange_rate_message_conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^(💱 تحرير رسالة سعر الصرف|💱 Edit Exchange Rate Message)$"), handle_edit_exchange_rate_message)],
    states={
        EDIT_EXCHANGE_RATE_MESSAGE_AR: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_exchange_rate_message_ar_input),
        ],
        EDIT_EXCHANGE_RATE_MESSAGE_EN: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_exchange_rate_message_en_input),
        ],
    },
    fallbacks=[
        CommandHandler("start", start),
        CommandHandler("cancel", lambda u, c: ConversationHandler.END),
        CommandHandler("reset", handle_reset_command),
        MessageHandler(filters.Regex("^(🔙 رجوع|🔙 Back)$"), lambda u, c: ConversationHandler.END),
        CallbackQueryHandler(lambda u, c: ConversationHandler.END),
        MessageHandler(filters.TEXT | filters.COMMAND, lambda u, c: ConversationHandler.END),
    ],
    per_message=False
)

# ===== نظام الشروط والأحكام =====

async def get_terms_message(language='ar'):
    """الحصول على رسالة الشروط والأحكام من قاعدة البيانات أو استخدام الافتراضية"""
    try:
        result = db.execute_query("SELECT value FROM settings WHERE key = ?", (f'terms_message_{language}',))
        return result[0][0] if result and len(result) > 0 and result[0][0] else TERMS_MESSAGE[language]
    except Exception as e:
        logger.error(f"Error getting terms message: {e}")
        return TERMS_MESSAGE[language]

async def terms_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة أمر /terms - للمستخدمين العاديين والآدمن"""
    user_id = update.effective_user.id
    is_admin = context.user_data.get('is_admin', False)
    
    language = get_user_language(user_id)
    terms_message = await get_terms_message(language)
    
    if is_admin:
        keyboard = [[InlineKeyboardButton("✏️ تعديل" if language == 'ar' else "✏️ Edit", callback_data="edit_terms")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(terms_message, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(terms_message, parse_mode='HTML')

async def edit_terms_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة الضغط على زر تعديل الشروط والأحكام (من inline button أو من قائمة الإعدادات)"""
    query = update.callback_query
    if query:
        await query.answer()
        user_id = query.from_user.id
    else:
        user_id = update.effective_user.id
    
    if not context.user_data.get('is_admin'):
        return ConversationHandler.END
    
    keyboard = [[KeyboardButton("🔙 رجوع")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    message_text = "📝 <b>خطوة 1 من 2</b>\n\nأدخل رسالة الشروط والأحكام بالعربية:\n\n💡 يمكنك استخدام تنسيق HTML للتنسيق"
    
    if query:
        await query.edit_message_text(text=message_text, parse_mode='HTML')
        await context.bot.send_message(chat_id=user_id, text="📝 أرسل رسالة الشروط والأحكام بالعربية:", reply_markup=reply_markup)
    else:
        await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='HTML')
    
    return EDIT_TERMS_MESSAGE_AR

async def handle_edit_terms_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء تعديل رسالة الشروط والأحكام من قائمة الإعدادات"""
    if not context.user_data.get('is_admin'):
        return ConversationHandler.END
    
    keyboard = [[KeyboardButton("🔙 رجوع")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "📝 <b>خطوة 1 من 2</b>\n\nأدخل رسالة الشروط والأحكام بالعربية:\n\n💡 يمكنك استخدام تنسيق HTML للتنسيق",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    return EDIT_TERMS_MESSAGE_AR

async def handle_terms_message_ar_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إدخال رسالة الشروط والأحكام العربية"""
    if not context.user_data.get('is_admin'):
        return ConversationHandler.END
    
    if update.message.text == "🔙 رجوع":
        await handle_admin_settings_menu(update, context)
        return ConversationHandler.END
    
    context.user_data['temp_terms_ar'] = update.message.text
    
    await update.message.reply_text(
        "✅ تم حفظ النص العربي!\n\n📝 <b>خطوة 2 من 2</b>\n\nالآن أدخل رسالة الشروط والأحكام بالإنجليزية:\n\n💡 يمكنك استخدام تنسيق HTML للتنسيق",
        parse_mode='HTML'
    )
    return EDIT_TERMS_MESSAGE_EN

async def handle_terms_message_en_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إدخال رسالة الشروط والأحكام الإنجليزية وحفظ كلا النصين"""
    if not context.user_data.get('is_admin'):
        return ConversationHandler.END
    
    if update.message.text == "🔙 رجوع":
        await handle_admin_settings_menu(update, context)
        return ConversationHandler.END
    
    ar_message = context.user_data.get('temp_terms_ar', '')
    en_message = update.message.text
    
    try:
        db.execute_query("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('terms_message_ar', ar_message))
        db.execute_query("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('terms_message_en', en_message))
        
        await update.message.reply_text(
            f"✅ تم تحديث رسالة الشروط والأحكام بنجاح للغتين!\n\n🇸🇦 <b>النص العربي:</b>\n{ar_message}\n\n🇺🇸 <b>النص الإنجليزي:</b>\n{en_message}",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error saving terms message: {e}")
        await update.message.reply_text(
            "❌ حدث خطأ في حفظ الرسالة. يرجى المحاولة مرة أخرى."
        )
    
    context.user_data.pop('temp_terms_ar', None)
    
    await handle_admin_settings_menu(update, context)
    return ConversationHandler.END

terms_message_conv_handler = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex("^📜 تعديل رسالة الشروط والأحكام$"), handle_edit_terms_message),
        CallbackQueryHandler(edit_terms_callback, pattern="^edit_terms$"),
        CallbackQueryHandler(edit_terms_callback, pattern="^admin_edit_terms$")
    ],
    states={
        EDIT_TERMS_MESSAGE_AR: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_terms_message_ar_input),
        ],
        EDIT_TERMS_MESSAGE_EN: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_terms_message_en_input),
        ],
    },
    fallbacks=[
        CommandHandler("start", start),
        CommandHandler("cancel", lambda u, c: ConversationHandler.END),
        CommandHandler("reset", handle_reset_command),
        MessageHandler(filters.Regex("^(🔙 رجوع|🔙 Back)$"), lambda u, c: ConversationHandler.END),
        CallbackQueryHandler(lambda u, c: ConversationHandler.END),
        MessageHandler(filters.TEXT | filters.COMMAND, lambda u, c: ConversationHandler.END),
    ],
    per_message=False
)

# ===== معالج الأخطاء الشامل =====
async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج شامل لجميع الأخطاء غير المتوقعة"""
    try:
        user_id = None
        error_context = "unknown"
        
        # محاولة الحصول على معرف المستخدم
        if isinstance(update, Update):
            if update.effective_user:
                user_id = update.effective_user.id
                error_context = f"user_{user_id}"
            elif update.callback_query and update.callback_query.from_user:
                user_id = update.callback_query.from_user.id
                error_context = f"callback_{user_id}"
            elif update.message and update.message.from_user:
                user_id = update.message.from_user.id
                error_context = f"message_{user_id}"
        
        # معالجة خاصة للأخطاء الشائعة
        error_str = str(context.error)
        
        # خطأ التعارض في getUpdates
        if "Conflict: terminated by other getUpdates request" in error_str:
            logger.warning("Detected multiple bot instances conflict. Bot will continue with retry logic.")
            return
        
        # أخطاء الشبكة (httpx.ReadError وما شابه)
        if any(error_type in error_str for error_type in [
            "httpx.ReadError", "ReadError", "ConnectionError", "TimeoutError", 
            "ReadTimeout", "ConnectTimeout", "PoolTimeout", "RemoteDisconnected"
        ]):
            logger.warning(f"Network error detected: {error_str}")
            # لا نرسل رسالة للمستخدم لأن هذه أخطاء شبكة مؤقتة
            if user_id:
                # فقط تنظيف البيانات المؤقتة بدون إرسال رسالة
                context.user_data.clear()
            return
            
        # تسجيل الخطأ
        error_msg = f"Global error in {error_context}: {context.error}"
        logger.error(error_msg, exc_info=context.error)
        
        # تنظيف البيانات المؤقتة للمستخدم إذا كان معروف
        if user_id:
            # تم إزالة health_monitor.mark_user_stuck
            
            # تنظيف البيانات المؤقتة للمستخدم
            context.user_data.clear()
            
            # محاولة إرسال رسالة للمستخدم
            try:
                if isinstance(update, Update) and update.effective_chat:
                    await context.bot.send_message(
                        update.effective_chat.id,
                        "⚠️ حدث خطأ غير متوقع. تم إعادة تعيين حالتك.\n"
                        "يرجى استخدام /start لإعادة تشغيل البوت.",
                        reply_markup=ReplyKeyboardRemove()
                    )
            except Exception as send_error:
                logger.error(f"Failed to send error message to user {user_id}: {send_error}")
        
        # إحصائيات الأخطاء
        error_type = type(context.error).__name__
        if not hasattr(global_error_handler, 'error_stats'):
            global_error_handler.error_stats = {}
        
        global_error_handler.error_stats[error_type] = global_error_handler.error_stats.get(error_type, 0) + 1
        
        # إذا كان هناك أكثر من 10 أخطاء من نفس النوع، أرسل تنبيه للأدمن
        if global_error_handler.error_stats[error_type] == 10:
            try:
                await context.bot.send_message(
                    ADMIN_CHAT_ID,
                    f"🚨 تحذير: تم تسجيل 10 أخطاء من نوع {error_type}\n"
                    f"آخر خطأ: {str(context.error)[:200]}..."
                )
            except:
                pass
                
    except Exception as handler_error:
        # إذا فشل معالج الأخطاء نفسه
        logger.critical(f"Error in global error handler: {handler_error}", exc_info=handler_error)

# تم حذف النظام القديم - يتم استخدام دوال Database.get_service_status و Database.set_service_status بدلاً منه

async def handle_manage_external_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة إدارة بروكسي خارجي - مؤقتاً بدون وظيفة"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton("🔙 رجوع لإدارة البروكسيات", callback_data="back_to_manage_proxies")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = """🌐 <b>إدارة بروكسي خارجي</b>

⚠️ هذه الميزة قيد التطوير حالياً

🚧 <b>قريباً ستتمكن من:</b>
• إضافة خوادم بروكسي خارجية
• إدارة اتصالات مع مزودي خدمة خارجيين
• مراقبة حالة الخوادم الخارجية
• تكوين إعدادات الاتصال المتقدمة

💡 سيتم تفعيل هذه الميزة في التحديث القادم"""
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

async def handle_detailed_static_management(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة إدارة تفصيلية للخدمات الثابتة"""
    query = update.callback_query
    await query.answer()
    
    service_type = query.data.replace("manage_detailed_static_", "")
    
    keyboard = [
        [
            InlineKeyboardButton("🔴 تعطيل الخدمة", callback_data=f"toggle_{service_type}_disable"),
            InlineKeyboardButton("🟢 تفعيل الخدمة", callback_data=f"toggle_{service_type}_enable")
        ],
        [
            InlineKeyboardButton("🔙 رجوع للإدارة المتقدمة", callback_data="advanced_service_management")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = f"""⚙️ <b>إدارة تفصيلية - {service_type}</b>

🎯 يمكنك تفعيل أو تعطيل هذه الخدمة المحددة

⚠️ <b>ملاحظة:</b> عند التعطيل، سيتم إشعار جميع المستخدمين تلقائياً

📊 <b>الحالة الحالية:</b> قيد التحديث..."""
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

# وظائف إدارة البروكسيات المجانية والمدفوعة

async def handle_manage_free_proxies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة زر إدارة البروكسيات الشامل - يشمل المجانية والمدفوعة"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # التحقق من أن المستخدم هو أدمن
    if not context.user_data.get('is_admin', False):
        await query.edit_message_text("❌ ليس لديك صلاحية للوصول لهذا القسم")
        return
    
    keyboard = [
        # قسم إدارة البروكسيات المجانية
        [InlineKeyboardButton("🎁 إدارة البروكسيات المجانية", callback_data="manage_free_proxies_menu")],
        [InlineKeyboardButton("🌐 إدارة بروكسي خارجي", callback_data="manage_external_proxy")],
        [InlineKeyboardButton("➕ إضافة ستاتيك مجاني", callback_data="add_free_proxy")],
        [InlineKeyboardButton("🗑 حذف بروكسي مجاني", callback_data="delete_free_proxy")],
        
        # العودة
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🌐 إدارة البروكسيات\n\n"
        "يمكنك إدارة البروكسيات المجانية من هنا:\n\n"
        "اختر الإجراء المطلوب:",
        reply_markup=reply_markup
    )

async def handle_free_proxy_trial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة طلب تجربة البروكسي المجاني"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    # جلب جميع البروكسيات المجانية المتاحة
    proxies = db.execute_query("SELECT id, message FROM free_proxies ORDER BY id")
    
    if not proxies:
        if language == 'ar':
            message = "😔 عذراً، لا توجد بروكسيات تجريبية متاحة حالياً\n\nيرجى المحاولة لاحقاً أو التواصل مع الأدمن"
        else:
            message = "😔 Sorry, no trial proxies are currently available\n\nPlease try again later or contact admin"
        
        await query.edit_message_text(message)
        return
    
    # إنشاء أزرار البروكسيات المتاحة
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
    
    # جلب بيانات البروكسي
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

async def handle_manage_proxies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة زر إدارة الخدمات (البروكسيات سابقاً)"""
    user_id = update.effective_user.id
    
    # التحقق من أن المستخدم هو أدمن
    if not context.user_data.get('is_admin', False):
        await update.message.reply_text("❌ ليس لديك صلاحية للوصول لهذا القسم")
        return
    
    # رابط لوحة التحكم Mini App
    from config import MINIAPP_URL
    miniapp_url = MINIAPP_URL
    
    # بناء الأزرار - تجاوز زر Web App إذا كان الرابط HTTP (تيليجرام يتطلب HTTPS)
    keyboard = []
    
    # إضافة زر لوحة الإدارة فقط إذا كان الرابط HTTPS
    if miniapp_url and miniapp_url.startswith("https://"):
        keyboard.append([InlineKeyboardButton("🎛️ لوحة إدارة الأزرار", web_app=WebAppInfo(url=miniapp_url))])
    elif miniapp_url:
        # إذا كان الرابط HTTP، نعرض رابط عادي للفتح في المتصفح
        keyboard.append([InlineKeyboardButton("🎛️ لوحة إدارة الأزرار (افتح في المتصفح)", url=miniapp_url)])
    
    keyboard.extend([
        [InlineKeyboardButton("⚙️ تشغيل / إيقاف الخدمات", callback_data="manage_services")],
        [InlineKeyboardButton("🎁 إدارة البروكسيات المجانية", callback_data="manage_free_proxies_menu")],
        [InlineKeyboardButton("🌍 إدارة الخدمات الخارجية", callback_data="manage_external_proxies")],
        [InlineKeyboardButton("❌ رجوع", callback_data="back_to_admin_menu")]
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🛠️ إدارة الخدمات\n\nاختر الإجراء المطلوب:",
        reply_markup=reply_markup
    )

async def handle_manage_free_proxies_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة قائمة إدارة البروكسيات المجانية الفرعية"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # التحقق من أن المستخدم هو أدمن
    if not context.user_data.get('is_admin', False):
        await query.edit_message_text("❌ ليس لديك صلاحية للوصول لهذا القسم")
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ إضافة ستاتيك مجاني", callback_data="add_free_proxy")],
        [InlineKeyboardButton("🗑 حذف بروكسي مجاني", callback_data="delete_free_proxy")],
        [InlineKeyboardButton("🔙 رجوع لإدارة البروكسيات", callback_data="back_to_manage_proxies")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🎁 إدارة البروكسيات المجانية\n\nاختر الإجراء المطلوب:",
        reply_markup=reply_markup
    )

async def handle_manage_external_proxies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة إدارة الخدمات الخارجية"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # التحقق من أن المستخدم هو أدمن
    if not context.user_data.get('is_admin', False):
        await query.edit_message_text("❌ ليس لديك صلاحية للوصول لهذا القسم")
        return
    
    keyboard = [
        [InlineKeyboardButton("📱 إدارة SMSPool (أرقام SMS)", callback_data="manage_smspool_admin")],
        [InlineKeyboardButton("🌐 إدارة سوكس يومي (Luxury)", callback_data="manage_luxury_admin")],
        [InlineKeyboardButton("💰 إدارة CoinEx", callback_data="manage_coinex_admin")],
        [InlineKeyboardButton("📱 إدارة Non-Voip (قديم)", callback_data="manage_nonvoip_admin")],
        [InlineKeyboardButton("🔙 رجوع لإدارة الخدمات", callback_data="back_to_manage_proxies")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🌍 إدارة الخدمات الخارجية\n\nاختر الخدمة التي تريد إدارتها:",
        reply_markup=reply_markup
    )

async def handle_manage_smspool_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة إدارة SMSPool - أرقام SMS"""
    if not SMSPOOL_AVAILABLE:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("❌ وحدة SMSPool غير متاحة حالياً")
        return
    
    await smspool_admin_menu(update, context)

async def handle_smspool_admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    """معالجة callbacks آدمن SMSPool"""
    if not SMSPOOL_AVAILABLE:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("❌ وحدة SMSPool غير متاحة حالياً")
        return None
    
    return await handle_smspool_admin_callback(update, context)

async def handle_smspool_user_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة callbacks المستخدم لـ SMSPool"""
    if not SMSPOOL_AVAILABLE:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("❌ هذه الخدمة غير متاحة حالياً")
        return
    
    await handle_smspool_callback(update, context)

async def handle_manage_luxury_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة إدارة Luxury Support - سوكس يومي"""
    if not LUXURY_AVAILABLE:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("❌ وحدة Luxury Support غير متاحة حالياً")
        return
    
    await luxury_admin_menu(update, context)

async def handle_luxury_admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة callbacks آدمن Luxury Support"""
    if not LUXURY_AVAILABLE:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("❌ وحدة Luxury Support غير متاحة حالياً")
        return
    
    await handle_luxury_admin_callback(update, context)

async def handle_luxury_user_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة callbacks المستخدم لـ Luxury Support"""
    if not LUXURY_AVAILABLE:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("❌ هذه الخدمة غير متاحة حالياً")
        return
    
    await handle_luxury_callback(update, context)

async def handle_manage_coinex_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة إدارة CoinEx"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # التحقق من أن المستخدم هو أدمن
    if not context.user_data.get('is_admin', False):
        await query.edit_message_text("❌ ليس لديك صلاحية للوصول لهذا القسم")
        return
    
    try:
        from CoinEx.coinex_payment import get_coinex_settings, init_coinex_tables, CoinExPaymentService
        
        # تهيئة الجداول إذا لم تكن موجودة
        init_coinex_tables()
        
        # جلب الإعدادات
        settings = get_coinex_settings()
        access_id = settings.get('coinex_access_id', '')
        
        # التحقق من حالة الاتصال
        if access_id:
            try:
                service = CoinExPaymentService()
                is_connected, status_msg = service.test_connection()
                connection_status = "✅ متصل" if is_connected else f"❌ غير متصل: {status_msg}"
            except Exception as e:
                connection_status = f"❌ خطأ: {str(e)[:30]}"
        else:
            connection_status = "⚠️ غير مُعد - يرجى إدخال بيانات API"
        
        # إحصائيات سريعة
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # عدد الإيداعات
        cursor.execute("SELECT COUNT(*) FROM coinex_deposits WHERE matched_request_id IS NULL")
        pending_deposits = cursor.fetchone()[0] or 0
        
        # عدد الطلبات المعلقة
        cursor.execute("SELECT COUNT(*) FROM coinex_payment_requests WHERE status = 'pending'")
        pending_requests = cursor.fetchone()[0] or 0
        
        # عدد الطلبات الفاشلة
        cursor.execute("SELECT COUNT(*) FROM coinex_payment_requests WHERE status IN ('expired', 'failed')")
        failed_requests = cursor.fetchone()[0] or 0
        
        # عدد المطابقات الناجحة
        cursor.execute("SELECT COUNT(*) FROM coinex_payment_matches")
        successful_matches = cursor.fetchone()[0] or 0
        
        conn.close()
        
        keyboard = [
            [InlineKeyboardButton("💵 عرض الرصيد", callback_data="coinex_view_balance")],
            [InlineKeyboardButton("📥 الإيداعات الواردة", callback_data="coinex_view_deposits")],
            [InlineKeyboardButton("📋 الطلبات المعلقة", callback_data="coinex_view_pending")],
            [InlineKeyboardButton("❌ الطلبات الفاشلة", callback_data="coinex_view_failed")],
            [InlineKeyboardButton("✅ المطابقات الناجحة", callback_data="coinex_view_matches")],
            [InlineKeyboardButton("⚙️ إعدادات API", callback_data="coinex_api_settings")],
            [InlineKeyboardButton("🔙 رجوع للخدمات الخارجية", callback_data="manage_external_proxies")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"""💰 <b>إدارة CoinEx</b>

📊 <b>حالة الاتصال:</b> {connection_status}

━━━━━━━━━━━━━━━━━━━━
📈 <b>الإحصائيات:</b>

📥 إيداعات غير مطابقة: <code>{pending_deposits}</code>
⏳ طلبات معلقة: <code>{pending_requests}</code>
❌ طلبات فاشلة: <code>{failed_requests}</code>
✅ مطابقات ناجحة: <code>{successful_matches}</code>

━━━━━━━━━━━━━━━━━━━━
اختر الإجراء المطلوب:"""
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"خطأ في إدارة CoinEx: {e}")
        keyboard = [
            [InlineKeyboardButton("⚙️ إعدادات API", callback_data="coinex_api_settings")],
            [InlineKeyboardButton("🔙 رجوع للخدمات الخارجية", callback_data="manage_external_proxies")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"💰 <b>إدارة CoinEx</b>\n\n"
            f"⚠️ تعذر تحميل البيانات: {str(e)[:50]}\n\n"
            f"يرجى التحقق من إعدادات API.",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )


async def handle_coinex_admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة جميع callbacks الخاصة بإدارة CoinEx"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # التحقق من صلاحيات الأدمن
    if not context.user_data.get('is_admin', False):
        await query.edit_message_text("❌ ليس لديك صلاحية للوصول لهذا القسم")
        return
    
    try:
        from CoinEx.coinex_payment import (
            get_coinex_settings, save_coinex_settings, init_coinex_tables,
            CoinExPaymentService, get_pending_deposits, get_pending_requests
        )
        from bot_utils import get_syria_time
        
        # تهيئة الجداول
        init_coinex_tables()
        
        back_button = [InlineKeyboardButton("🔙 رجوع لإدارة CoinEx", callback_data="manage_coinex_admin")]
        
        # ==================== عرض الرصيد ====================
        if query.data == "coinex_view_balance":
            settings = get_coinex_settings()
            access_id = settings.get('coinex_access_id', '')
            
            if not access_id:
                keyboard = [
                    [InlineKeyboardButton("⚙️ إعدادات API", callback_data="coinex_api_settings")],
                    back_button
                ]
                await query.edit_message_text(
                    "💵 <b>رصيد CoinEx</b>\n\n"
                    "⚠️ يرجى إعداد بيانات API أولاً للوصول للرصيد.",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
                return
            
            try:
                service = CoinExPaymentService()
                balance_result = service.api.get_balance()
                
                if balance_result.get('code') == 0 and balance_result.get('data'):
                    balances = balance_result['data']
                    
                    balance_text = "💵 <b>رصيد حسابك في CoinEx</b>\n\n━━━━━━━━━━━━━━━━━━━━\n"
                    
                    total_usdt = 0
                    for bal in balances:
                        ccy = bal.get('ccy', '')
                        available = float(bal.get('available', 0))
                        frozen = float(bal.get('frozen', 0))
                        total = available + frozen
                        
                        if total > 0:
                            balance_text += f"\n💰 <b>{ccy}</b>\n"
                            balance_text += f"   متاح: <code>{available:.8f}</code>\n"
                            if frozen > 0:
                                balance_text += f"   مجمد: <code>{frozen:.8f}</code>\n"
                            
                            if ccy == 'USDT':
                                total_usdt = total
                    
                    if total_usdt > 0:
                        balance_text += f"\n━━━━━━━━━━━━━━━━━━━━\n💎 إجمالي USDT: <code>${total_usdt:.2f}</code>"
                    
                    syria_time = get_syria_time()
                    balance_text += f"\n\n🕐 آخر تحديث: {syria_time.strftime('%Y-%m-%d %H:%M:%S')}"
                    
                else:
                    balance_text = f"❌ فشل جلب الرصيد: {balance_result.get('message', 'خطأ غير معروف')}"
                
            except Exception as e:
                balance_text = f"❌ خطأ في الاتصال: {str(e)[:50]}"
            
            keyboard = [
                [InlineKeyboardButton("🔄 تحديث", callback_data="coinex_view_balance")],
                back_button
            ]
            await query.edit_message_text(
                balance_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        
        # ==================== عرض الإيداعات ====================
        elif query.data == "coinex_view_deposits":
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            
            three_days_ago = (get_syria_time() - timedelta(days=3)).strftime('%Y-%m-%d 00:00:00')
            
            cursor.execute('''
                SELECT id, deposit_id, amount, currency, status, 
                       timestamp_received, matched_request_id 
                FROM coinex_deposits 
                WHERE timestamp_received >= ?
                ORDER BY timestamp_received DESC 
                LIMIT 20
            ''', (three_days_ago,))
            deposits = cursor.fetchall()
            conn.close()
            
            if deposits:
                message = "📥 <b>آخر الإيداعات الواردة</b> (آخر 3 أيام)\n\nاضغط على أي عملية لعرض التفاصيل:"
                
                keyboard = []
                for dep in deposits:
                    dep_id, deposit_id, amount, currency, status, timestamp, matched_id = dep
                    
                    status_emoji = "✅" if matched_id else ("⏳" if status == 'pending' else "🔄")
                    date_short = timestamp[:10] if timestamp else '-'
                    
                    btn_text = f"{status_emoji} {amount} {currency} | {date_short}"
                    keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"coinex_dep_{dep_id}")])
                
                keyboard.append([InlineKeyboardButton("🔄 تحديث", callback_data="coinex_view_deposits")])
                keyboard.append([InlineKeyboardButton("📥 جلب إيداعات جديدة", callback_data="coinex_fetch_deposits")])
                keyboard.append(back_button)
            else:
                message = "📥 <b>الإيداعات الواردة</b> (آخر 3 أيام)\n\n⚠️ لا توجد إيداعات مسجلة."
                keyboard = [
                    [InlineKeyboardButton("🔄 تحديث", callback_data="coinex_view_deposits")],
                    [InlineKeyboardButton("📥 جلب إيداعات جديدة", callback_data="coinex_fetch_deposits")],
                    back_button
                ]
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        
        # ==================== عرض تفاصيل إيداع معين ====================
        elif query.data.startswith("coinex_dep_"):
            dep_id = int(query.data.replace("coinex_dep_", ""))
            
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT d.id, d.deposit_id, d.tx_hash, d.sender_email, d.amount, d.currency, 
                       d.chain, d.status, d.timestamp_received, d.matched_request_id, d.confirmations,
                       r.user_sender_email, r.user_tx_hash, r.method
                FROM coinex_deposits d
                LEFT JOIN auto_payment_requests r ON d.matched_request_id = r.id
                WHERE d.id = ?
            ''', (dep_id,))
            dep = cursor.fetchone()
            conn.close()
            
            if dep:
                dep_id, deposit_id, tx_hash, sender_email, amount, currency, chain, status, timestamp, matched_id, confirmations, req_sender_email, req_tx_hash, req_method = dep
                
                final_sender_email = sender_email or req_sender_email
                final_tx_hash = tx_hash or req_tx_hash
                
                status_emoji = "✅" if matched_id else ("⏳" if status == 'pending' else "🔄")
                match_text = f"مطابق مع طلب #{matched_id}" if matched_id else "غير مطابق"
                
                message = f"""📥 <b>تفاصيل الإيداع</b>

━━━━━━━━━━━━━━━━━━━━

{status_emoji} <b>الحالة:</b> {status} | {match_text}

💰 <b>المبلغ:</b> <code>{amount} {currency}</code>
🔗 <b>الشبكة:</b> {chain or '-'}
📅 <b>التاريخ:</b> {timestamp or '-'}
🔢 <b>التأكيدات:</b> {confirmations or 0}

━━━━━━━━━━━━━━━━━━━━

🆔 <b>معرف الإيداع:</b>
<code>{deposit_id}</code>
"""
                if final_tx_hash:
                    message += f"""
🔑 <b>هاش العملية:</b>
<code>{final_tx_hash}</code>
"""
                if final_sender_email:
                    message += f"""
📧 <b>بريد المرسل:</b>
<code>{final_sender_email}</code>
"""
            else:
                message = "❌ لم يتم العثور على الإيداع"
            
            keyboard = [
                [InlineKeyboardButton("🔙 رجوع للإيداعات", callback_data="coinex_view_deposits")],
                back_button
            ]
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        
        # ==================== جلب إيداعات جديدة ====================
        elif query.data == "coinex_fetch_deposits":
            settings = get_coinex_settings()
            if not settings.get('coinex_access_id'):
                await query.edit_message_text(
                    "⚠️ يرجى إعداد API أولاً",
                    reply_markup=InlineKeyboardMarkup([back_button]),
                    parse_mode='HTML'
                )
                return
            
            try:
                service = CoinExPaymentService()
                stored = service.fetch_and_store_deposits()
                matched = service.run_auto_matching()
                
                message = f"📥 <b>جلب الإيداعات</b>\n\n"
                message += f"✅ تم جلب وتخزين: <code>{stored}</code> إيداع جديد\n"
                message += f"🎯 تم مطابقة: <code>{matched}</code> طلب"
                
            except Exception as e:
                message = f"❌ خطأ: {str(e)[:50]}"
            
            keyboard = [
                [InlineKeyboardButton("📥 عرض الإيداعات", callback_data="coinex_view_deposits")],
                back_button
            ]
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        
        # ==================== عرض الطلبات المعلقة ====================
        elif query.data == "coinex_view_pending":
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, user_id, expected_amount, currency, created_at, expires_at, order_id
                FROM coinex_payment_requests 
                WHERE status = 'pending'
                ORDER BY created_at DESC
                LIMIT 20
            ''')
            requests = cursor.fetchall()
            conn.close()
            
            if requests:
                message = "⏳ <b>الطلبات المعلقة</b>\n\n━━━━━━━━━━━━━━━━━━━━\n"
                
                for req in requests:
                    req_id, user_id, amount, currency, created_at, expires_at, order_id = req
                    message += f"\n🔹 طلب #{req_id}\n"
                    message += f"   👤 المستخدم: <code>{user_id}</code>\n"
                    message += f"   💰 المبلغ: <code>{amount} {currency}</code>\n"
                    message += f"   📅 الإنشاء: {created_at or '-'}\n"
                    message += f"   ⏰ ينتهي: {expires_at or '-'}\n"
            else:
                message = "⏳ <b>الطلبات المعلقة</b>\n\n✅ لا توجد طلبات معلقة."
            
            keyboard = [
                [InlineKeyboardButton("🔄 تحديث", callback_data="coinex_view_pending")],
                back_button
            ]
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        
        # ==================== عرض الطلبات الفاشلة ====================
        elif query.data == "coinex_view_failed":
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, user_id, expected_amount, currency, status, created_at, expires_at
                FROM coinex_payment_requests 
                WHERE status IN ('expired', 'failed', 'cancelled')
                ORDER BY created_at DESC
                LIMIT 20
            ''')
            requests = cursor.fetchall()
            conn.close()
            
            if requests:
                message = "❌ <b>الطلبات الفاشلة/المنتهية</b>\n\n━━━━━━━━━━━━━━━━━━━━\n"
                
                status_map = {'expired': '⏰ منتهي', 'failed': '❌ فاشل', 'cancelled': '🚫 ملغي'}
                
                for req in requests:
                    req_id, user_id, amount, currency, status, created_at, expires_at = req
                    status_text = status_map.get(status, status)
                    
                    message += f"\n🔸 طلب #{req_id} - {status_text}\n"
                    message += f"   👤 المستخدم: <code>{user_id}</code>\n"
                    message += f"   💰 المبلغ: <code>{amount} {currency}</code>\n"
                    message += f"   📅 التاريخ: {created_at or '-'}\n"
            else:
                message = "❌ <b>الطلبات الفاشلة</b>\n\n✅ لا توجد طلبات فاشلة."
            
            keyboard = [
                [InlineKeyboardButton("🔄 تحديث", callback_data="coinex_view_failed")],
                back_button
            ]
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        
        # ==================== عرض المطابقات الناجحة ====================
        elif query.data == "coinex_view_matches":
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT m.id, m.deposit_id, m.request_id, m.match_type, m.confidence, m.matched_at,
                       d.amount, d.currency
                FROM coinex_payment_matches m
                LEFT JOIN coinex_deposits d ON m.deposit_id = d.id
                ORDER BY m.matched_at DESC
                LIMIT 20
            ''')
            matches = cursor.fetchall()
            conn.close()
            
            if matches:
                message = "✅ <b>المطابقات الناجحة</b>\n\n━━━━━━━━━━━━━━━━━━━━\n"
                
                match_type_map = {
                    'tx_hash': '🔗 TX Hash',
                    'sender_email': '📧 البريد',
                    'amount_time': '💰 المبلغ+الوقت'
                }
                
                for match in matches:
                    m_id, dep_id, req_id, match_type, confidence, matched_at, amount, currency = match
                    type_text = match_type_map.get(match_type, match_type)
                    conf_percent = int(confidence * 100) if confidence else 0
                    
                    message += f"\n🎯 مطابقة #{m_id}\n"
                    message += f"   إيداع #{dep_id} ↔ طلب #{req_id}\n"
                    message += f"   💰 {amount or '-'} {currency or ''}\n"
                    message += f"   {type_text} ({conf_percent}%)\n"
                    message += f"   📅 {matched_at or '-'}\n"
            else:
                message = "✅ <b>المطابقات الناجحة</b>\n\n⚠️ لا توجد مطابقات بعد."
            
            keyboard = [
                [InlineKeyboardButton("🔄 تحديث", callback_data="coinex_view_matches")],
                back_button
            ]
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        
        # ==================== إعدادات API ====================
        elif query.data == "coinex_api_settings":
            settings = get_coinex_settings()
            access_id = settings.get('coinex_access_id', '')
            
            # إخفاء جزء من المفتاح للأمان
            if access_id:
                masked_id = access_id[:4] + "****" + access_id[-4:] if len(access_id) > 8 else "****"
            else:
                masked_id = "غير مُعد"
            
            auto_match = settings.get('auto_match_enabled', 'true') == 'true'
            polling_interval = settings.get('polling_interval', '30')
            
            message = f"""⚙️ <b>إعدادات CoinEx API</b>

━━━━━━━━━━━━━━━━━━━━
🔑 <b>معرف API:</b> <code>{masked_id}</code>
🔐 <b>المفتاح السري:</b> {'✅ مُعد' if access_id else '❌ غير مُعد'}

━━━━━━━━━━━━━━━━━━━━
⚙️ <b>الإعدادات:</b>

🔄 المطابقة التلقائية: {'✅ مفعّلة' if auto_match else '❌ معطّلة'}
⏱ فترة الاستعلام: {polling_interval} ثانية

━━━━━━━━━━━━━━━━━━━━
اختر الإجراء:"""
            
            keyboard = [
                [InlineKeyboardButton("🔑 تغيير معرف API", callback_data="coinex_set_access_id")],
                [InlineKeyboardButton("🔐 تغيير المفتاح السري", callback_data="coinex_set_secret_key")],
                [InlineKeyboardButton("🔗 اختبار الاتصال", callback_data="coinex_test_connection")],
                [InlineKeyboardButton(
                    f"{'🔴 تعطيل' if auto_match else '🟢 تفعيل'} المطابقة التلقائية",
                    callback_data="coinex_toggle_auto_match"
                )],
                back_button
            ]
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        
        # ==================== تغيير معرف API ====================
        elif query.data == "coinex_set_access_id":
            context.user_data['coinex_waiting_for'] = 'access_id'
            
            keyboard = [
                [InlineKeyboardButton("❌ إلغاء", callback_data="coinex_api_settings")]
            ]
            await query.edit_message_text(
                "🔑 <b>تغيير معرف API (Access ID)</b>\n\n"
                "📝 أرسل الآن معرف API الجديد:\n\n"
                "💡 يمكنك الحصول عليه من:\n"
                "CoinEx → API Management → Create API",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        
        # ==================== تغيير المفتاح السري ====================
        elif query.data == "coinex_set_secret_key":
            context.user_data['coinex_waiting_for'] = 'secret_key'
            
            keyboard = [
                [InlineKeyboardButton("❌ إلغاء", callback_data="coinex_api_settings")]
            ]
            await query.edit_message_text(
                "🔐 <b>تغيير المفتاح السري (Secret Key)</b>\n\n"
                "📝 أرسل الآن المفتاح السري الجديد:\n\n"
                "⚠️ تنبيه: هذا المفتاح حساس جداً، احتفظ به بأمان.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        
        # ==================== اختبار الاتصال ====================
        elif query.data == "coinex_test_connection":
            settings = get_coinex_settings()
            
            if not settings.get('coinex_access_id') or not settings.get('coinex_secret_key'):
                message = "❌ يرجى إعداد معرف API والمفتاح السري أولاً"
            else:
                try:
                    service = CoinExPaymentService()
                    is_connected, status_msg = service.test_connection()
                    
                    if is_connected:
                        message = f"✅ <b>الاتصال ناجح!</b>\n\n{status_msg}"
                    else:
                        message = f"❌ <b>فشل الاتصال</b>\n\n{status_msg}"
                except Exception as e:
                    message = f"❌ <b>خطأ في الاتصال</b>\n\n{str(e)[:100]}"
            
            keyboard = [
                [InlineKeyboardButton("🔄 إعادة الاختبار", callback_data="coinex_test_connection")],
                [InlineKeyboardButton("⚙️ الإعدادات", callback_data="coinex_api_settings")],
                back_button
            ]
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        
        # ==================== تبديل المطابقة التلقائية ====================
        elif query.data == "coinex_toggle_auto_match":
            settings = get_coinex_settings()
            current_state = settings.get('auto_match_enabled', 'true') == 'true'
            new_state = 'false' if current_state else 'true'
            
            save_coinex_settings({'auto_match_enabled': new_state})
            
            status_text = "✅ تم تفعيل" if new_state == 'true' else "❌ تم تعطيل"
            
            keyboard = [
                [InlineKeyboardButton("⚙️ العودة للإعدادات", callback_data="coinex_api_settings")],
                back_button
            ]
            await query.edit_message_text(
                f"{status_text} المطابقة التلقائية",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        
        else:
            # callback غير معروف
            await query.edit_message_text(
                "⚠️ إجراء غير معروف",
                reply_markup=InlineKeyboardMarkup([back_button]),
                parse_mode='HTML'
            )
    
    except Exception as e:
        logger.error(f"خطأ في معالجة callback CoinEx: {e}")
        import traceback
        traceback.print_exc()
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="manage_coinex_admin")]]
        await query.edit_message_text(
            f"❌ حدث خطأ: {str(e)[:50]}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )


async def handle_coinex_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة إدخال بيانات CoinEx من المستخدم (API Key / Secret)"""
    user_id = update.effective_user.id
    
    # التحقق من صلاحيات الأدمن
    if not context.user_data.get('is_admin', False):
        return
    
    waiting_for = context.user_data.get('coinex_waiting_for')
    if not waiting_for:
        return
    
    try:
        from CoinEx.coinex_payment import save_coinex_settings, get_coinex_settings
        
        text = update.message.text.strip()
        
        # حذف الرسالة التي تحتوي على المفتاح للأمان
        try:
            await update.message.delete()
        except:
            pass
        
        if waiting_for == 'access_id':
            save_coinex_settings({'coinex_access_id': text})
            context.user_data['coinex_waiting_for'] = None
            
            keyboard = [
                [InlineKeyboardButton("🔐 إضافة المفتاح السري", callback_data="coinex_set_secret_key")],
                [InlineKeyboardButton("🔗 اختبار الاتصال", callback_data="coinex_test_connection")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="coinex_api_settings")]
            ]
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="✅ تم حفظ معرف API بنجاح!\n\n"
                     "💡 لا تنسَ إضافة المفتاح السري أيضاً.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        
        elif waiting_for == 'secret_key':
            save_coinex_settings({'coinex_secret_key': text})
            context.user_data['coinex_waiting_for'] = None
            
            keyboard = [
                [InlineKeyboardButton("🔗 اختبار الاتصال", callback_data="coinex_test_connection")],
                [InlineKeyboardButton("🔙 رجوع للإعدادات", callback_data="coinex_api_settings")]
            ]
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="✅ تم حفظ المفتاح السري بنجاح!\n\n"
                     "🔗 يمكنك الآن اختبار الاتصال.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
    
    except Exception as e:
        logger.error(f"خطأ في حفظ بيانات CoinEx: {e}")
        context.user_data['coinex_waiting_for'] = None
        
        await update.message.reply_text(f"❌ حدث خطأ: {str(e)[:50]}")


async def handle_add_free_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء إضافة بروكسي مجاني"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع العملية", callback_data="cancel_add_proxy")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📝 أرسل الآن رسالة البروكسي المجاني التي تريد حفظها:\n\n"
        "مثال:\n"
        "```\n"
        "🎁 بروكسي تجريبي مجاني\n"
        "IP: 192.168.1.1\n"
        "Port: 8080\n"
        "```",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    return ADD_FREE_PROXY

async def handle_free_proxy_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة رسالة البروكسي المجاني"""
    message_content = update.message.text
    
    # حفظ الرسالة في قاعدة البيانات
    try:
        db.execute_query(
            "INSERT INTO free_proxies (message) VALUES (?)",
            (message_content,)
        )
        
        # الحصول على أعلى رقم ID لترقيم البروكسي
        result = db.execute_query("SELECT MAX(id) FROM free_proxies")
        proxy_id = result[0][0] if result and result[0][0] else 1
        
        await update.message.reply_text(
            f"✅ تم حفظ البروكسي بنجاح!\n\n"
            f"🆔 رقم البروكسي: #{proxy_id}\n"
            f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"💡 البروكسي أصبح متوفراً كعينة للزبائن"
        )
        
        # العودة للقائمة الرئيسية
        await restore_admin_keyboard(context, update.effective_user.id, "🔧 تم إضافة البروكسي بنجاح")
        
    except Exception as e:
        logger.error(f"Error saving free proxy: {e}")
        await update.message.reply_text("❌ حدث خطأ في حفظ البروكسي. يرجى المحاولة مرة أخرى.")
    
    return ConversationHandler.END

async def handle_delete_free_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """عرض قائمة البروكسيات المحفوظة للحذف"""
    query = update.callback_query
    await query.answer()
    
    # جلب جميع البروكسيات المحفوظة
    proxies = db.execute_query("SELECT id, message FROM free_proxies ORDER BY id")
    
    if not proxies:
        await query.edit_message_text(
            "📭 لا توجد بروكسيات محفوظة حالياً",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ رجوع", callback_data="back_to_manage_proxies")]])
        )
        return ConversationHandler.END
    
    # إنشاء أزرار البروكسيات
    keyboard = []
    for proxy_id, message in proxies:
        # عرض أول 30 حرف من الرسالة كعنوان
        title = message[:30] + "..." if len(message) > 30 else message
        keyboard.append([InlineKeyboardButton(f"بروكسي #{proxy_id}: {title}", callback_data=f"view_proxy_{proxy_id}")])
    
    keyboard.append([InlineKeyboardButton("❌ رجوع", callback_data="back_to_manage_proxies")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🗑 اختر البروكسي المراد حذفه:",
        reply_markup=reply_markup
    )
    
    return DELETE_FREE_PROXY

async def handle_view_proxy_for_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """عرض البروكسي مع خيارات الحذف أو التراجع"""
    query = update.callback_query
    await query.answer()
    
    proxy_id = int(query.data.split("_")[2])
    
    # جلب بيانات البروكسي
    result = db.execute_query("SELECT message, created_at FROM free_proxies WHERE id = ?", (proxy_id,))
    
    if not result:
        await query.edit_message_text("❌ البروكسي غير موجود")
        return ConversationHandler.END
    
    message, created_at = result[0]
    
    keyboard = [
        [InlineKeyboardButton("🗑 حذف", callback_data=f"confirm_delete_{proxy_id}")],
        [InlineKeyboardButton("❌ تراجع", callback_data="delete_free_proxy")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📋 بروكسي #{proxy_id}\n"
        f"📅 تاريخ الإنشاء: {created_at}\n\n"
        f"📝 المحتوى:\n{message}",
        reply_markup=reply_markup
    )
    
    return DELETE_FREE_PROXY

async def handle_confirm_delete_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """تأكيد حذف البروكسي"""
    query = update.callback_query
    await query.answer()
    
    proxy_id = int(query.data.split("_")[2])
    
    try:
        # حذف البروكسي من قاعدة البيانات
        db.execute_query("DELETE FROM free_proxies WHERE id = ?", (proxy_id,))
        
        await query.edit_message_text(f"✅ تم حذف بروكسي #{proxy_id} بنجاح")
        
        # العودة للقائمة الرئيسية
        await restore_admin_keyboard(context, update.effective_user.id, "🗑 تم حذف البروكسي بنجاح")
        
    except Exception as e:
        logger.error(f"Error deleting proxy {proxy_id}: {e}")
        await query.edit_message_text("❌ حدث خطأ في حذف البروكسي")
    
    return ConversationHandler.END

async def handle_cancel_add_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إلغاء إضافة البروكسي"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("❌ تم إلغاء عملية إضافة البروكسي")
    await restore_admin_keyboard(context, update.effective_user.id, "🔧 تم إلغاء العملية")
    
    return ConversationHandler.END

async def handle_back_to_manage_proxies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """العودة لقائمة إدارة الخدمات"""
    query = update.callback_query
    await query.answer()
    
    # رابط لوحة التحكم Mini App
    from config import MINIAPP_URL
    miniapp_url = MINIAPP_URL
    
    # بناء الأزرار - تجاوز زر Web App إذا كان الرابط HTTP (تيليجرام يتطلب HTTPS)
    keyboard = []
    
    # إضافة زر لوحة الإدارة فقط إذا كان الرابط HTTPS
    if miniapp_url and miniapp_url.startswith("https://"):
        keyboard.append([InlineKeyboardButton("🎛️ لوحة إدارة الأزرار", web_app=WebAppInfo(url=miniapp_url))])
    elif miniapp_url:
        # إذا كان الرابط HTTP، نعرض رابط عادي للفتح في المتصفح
        keyboard.append([InlineKeyboardButton("🎛️ لوحة إدارة الأزرار (افتح في المتصفح)", url=miniapp_url)])
    
    keyboard.extend([
        [InlineKeyboardButton("⚙️ تشغيل / إيقاف الخدمات", callback_data="manage_services")],
        [InlineKeyboardButton("🎁 إدارة البروكسيات المجانية", callback_data="manage_free_proxies_menu")],
        [InlineKeyboardButton("🌍 إدارة الخدمات الخارجية", callback_data="manage_external_proxies")],
        [InlineKeyboardButton("❌ رجوع", callback_data="back_to_admin_menu")]
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🛠️ إدارة الخدمات\n\nاختر الإجراء المطلوب:",
        reply_markup=reply_markup
    )

async def handle_back_to_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """العودة للقائمة الرئيسية للأدمن"""
    query = update.callback_query
    await query.answer()
    
    await query.delete_message()
    await restore_admin_keyboard(context, update.effective_user.id, "🔧 لوحة الأدمن جاهزة")

# وظائف المستخدمين للبروكسيات المجانية

async def handle_free_static_trial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة طلب تجربة ستاتيك مجانا"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    # جلب جميع البروكسيات المجانية المتاحة
    proxies = db.execute_query("SELECT id, message FROM free_proxies ORDER BY id")
    
    if not proxies:
        if language == 'ar':
            message = "😔 عذراً، لا توجد بروكسيات تجريبية متاحة حالياً\n\nيرجى المحاولة لاحقاً أو التواصل مع الأدمن"
        else:
            message = "😔 Sorry, no trial proxies are currently available\n\nPlease try again later or contact admin"
        
        await update.message.reply_text(message)
        return
    
    # إنشاء أزرار البروكسيات المتاحة
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
    
    await update.message.reply_text(message_text, reply_markup=reply_markup)

async def handle_get_free_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """إرسال البروكسي المجاني للمستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    proxy_id = int(query.data.split("_")[3])
    
    # جلب بيانات البروكسي
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
        thank_message = f"🎁 هذه عينة مجانية، استمتع بوقتك!\n\n{proxy_message}"
    else:
        thank_message = f"🎁 This is a free sample, enjoy your time!\n\n{proxy_message}"
    
    await query.edit_message_text(thank_message)
    
    # تسجيل العملية في اللوجس
    db.log_action(user_id, f"free_proxy_used_{proxy_id}")

# دوال التحقق من حالة الخدمات والإشعارات

async def check_service_availability(service_type: str, update: Update, context: ContextTypes.DEFAULT_TYPE, language: str, service_subtype: str = None) -> bool:
    """التحقق من توفر خدمة معينة وإرسال رسالة واضحة إذا كانت معطلة"""
    
    # تحديد اسم الخدمة بالعربية
    service_name_ar = "الخدمة"
    service_name_en = "Service"
    
    # للستاتيك
    if service_type == 'static':
        # إذا تم تحديد نوع فرعي (مثل monthly_residential, isp_att, datacenter)
        if service_subtype:
            if not db.get_service_status('static', service_subtype):
                subtype_names = {
                    'monthly_residential': ('البروكسي الريزيدنتال الشهري', 'Monthly Residential Proxy'),
                    'monthly_verizon': ('بروكسي Verizon الشهري', 'Monthly Verizon Proxy'),
                    'isp_att': ('بروكسي ISP', 'ISP Proxy'),
                    'datacenter': ('بروكسي داتا سينتر', 'Datacenter Proxy'),
                    'weekly_crocker': ('البروكسي الأسبوعي', 'Weekly Proxy'),
                    'daily_static': ('البروكسي اليومي', 'Daily Proxy')
                }
                service_name_ar, service_name_en = subtype_names.get(service_subtype, ('البروكسي', 'Proxy'))
                await send_service_disabled_message(update, language, 'static', service_name_ar if language == 'ar' else service_name_en)
                return False
        # فحص الخدمة الأساسية إذا لم يتم تحديد نوع فرعي
        elif not db.get_service_status('static', 'basic'):
            await send_service_disabled_message(update, language, 'static', 'خدمات البروكسي الستاتيك' if language == 'ar' else 'Static Proxy Services')
            return False
    
    # للسوكس
    elif service_type == 'socks':
        if service_subtype:
            if not db.get_service_status('socks', service_subtype):
                subtype_names = {
                    'single': ('بروكسي السوكس الواحد', 'Single SOCKS Proxy'),
                    'package_2': ('بروكسيان اثنان', 'Two SOCKS Proxies'),
                    'package_5': ('باكج 5 بروكسي', '5 Proxy Package'),
                    'package_10': ('باكج 10 بروكسي', '10 Proxy Package'),
                    'basic': ('خدمات السوكس الأساسية', 'Basic SOCKS Services')
                }
                service_name_ar, service_name_en = subtype_names.get(service_subtype, ('السوكس', 'SOCKS'))
                await send_service_disabled_message(update, language, 'socks', service_name_ar if language == 'ar' else service_name_en)
                return False
        elif not db.get_service_status('socks', 'basic'):
            await send_service_disabled_message(update, language, 'socks', 'خدمات بروكسي السوكس' if language == 'ar' else 'SOCKS Proxy Services')
            return False
    
    return True

async def send_service_disabled_message(update: Update, language: str, service_type: str, service_name: str):
    """إرسال رسالة تعطيل الخدمة للمستخدم"""
    if language == 'ar':
        message = f"""🚫 تم إيقاف خدمة {service_name}
        
⚠️ عذراً، تم إيقاف هذه الخدمة مؤقتاً من قبل الإدارة

🔸 الأسباب المحتملة:
• نفاد الكمية المتاحة
• تعطل مؤقت في سيرفرات الخدمة
• صيانة فنية

🔔 سيتم إعلامكم فور إعادة تشغيل الخدمة

💫 شكراً لتفهمكم وصبركم"""
    else:
        message = f"""🚫 {service_name} Service Disabled
        
⚠️ Sorry, this service is temporarily disabled by administration

🔸 Possible reasons:
• Available quantity exhausted
• Temporary server issues
• Technical maintenance

🔔 You will be notified once the service is restored

💫 Thank you for your understanding and patience"""
    
    try:
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(message)
        else:
            await update.message.reply_text(message)
    except Exception as e:
        print(f"خطأ في إرسال رسالة تعطيل الخدمة: {e}")

async def send_admin_notification(context: ContextTypes.DEFAULT_TYPE, service_name: str, is_enabled: bool, service_type: str = None):
    """إرسال إشعار للآدمن فقط عند تغيير حالة الخدمة"""
    global ACTIVE_ADMINS, ADMIN_CHAT_ID
    
    action_text = "تشغيل" if is_enabled else "إيقاف"
    status_icon = "✅" if is_enabled else "⏸"
    
    notification_message = f"""{status_icon} إشعار تحديث الخدمة

🔧 الخدمة: {service_name}
📊 الحالة الجديدة: {action_text}
⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✨ تم تطبيق التغييرات بنجاح!"""
    
    # جمع جميع معرفات الآدمن من جميع المصادر
    admin_ids = set(ACTIVE_ADMINS)
    if ADMIN_CHAT_ID:
        admin_ids.add(ADMIN_CHAT_ID)
    # إضافة معرفات الآدمن من ملف الإعدادات كاحتياط
    if ADMIN_IDS:
        admin_ids.update(ADMIN_IDS)
    
    logger.info(f"إرسال إشعار تعديل الخدمة لـ {len(admin_ids)} آدمن: {admin_ids}")
    
    if not admin_ids:
        logger.warning("لا يوجد آدمن لإرسال الإشعار إليهم!")
        return
    
    sent_count = 0
    for admin_id in admin_ids:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=notification_message
            )
            sent_count += 1
            logger.info(f"تم إرسال إشعار للآدمن {admin_id}: {service_name} - {action_text}")
        except Exception as e:
            logger.error(f"فشل إرسال الإشعار للآدمن {admin_id}: {e}")
    
    logger.info(f"تم إرسال {sent_count}/{len(admin_ids)} إشعار بنجاح")

async def handle_service_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة تشغيل/إيقاف الخدمات مثل toggle_socks_disable أو toggle_static_enable"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    # تنسيق: toggle_{service_type}_{action}
    # مثال: toggle_socks_disable أو toggle_monthly_residential_enable
    
    try:
        # إزالة "toggle_" من البداية
        remaining = callback_data.replace("toggle_", "")
        
        # استخراج الإجراء (enable أو disable) من النهاية
        if remaining.endswith("_disable"):
            action = "disable"
            service_type = remaining.replace("_disable", "")
            enable = False
        elif remaining.endswith("_enable"):
            action = "enable"
            service_type = remaining.replace("_enable", "")
            enable = True
        else:
            await query.edit_message_text("❌ خطأ: بيانات غير صحيحة")
            return
        
        # تحديد نوع الخدمة الرئيسي
        if service_type == 'socks':
            main_service = 'socks'
            service_subtype = 'basic'
            service_name = 'خدمات بروكسي السوكس'
        elif service_type in ['monthly_residential', 'monthly_verizon', 'isp_att', 'datacenter']:
            main_service = 'static'
            service_subtype = service_type
            service_names_map = {
                'monthly_residential': 'البروكسي السكني الشهري',
                'monthly_verizon': 'بروكسي فيريزون الشهري',
                'isp_att': 'بروكسي ISP/ATT',
                'datacenter': 'بروكسي داتا سنتر'
            }
            service_name = service_names_map.get(service_type, service_type)
        else:
            main_service = 'static'
            service_subtype = service_type
            service_name = service_type
        
        # عرض رسالة تحميل
        loading_message = await query.edit_message_text("⏳ جاري التحديث...")
        
        # حفظ حالة الخدمة في قاعدة البيانات
        db.set_service_status(main_service, enable, service_subtype)
        logger.info(f"تم {'تشغيل' if enable else 'إيقاف'} خدمة {main_service}: {service_subtype}")
        
        # إرسال إشعار للآدمن
        await send_admin_notification(context, service_name, enable, main_service)
        
        # رسالة النجاح
        status_icon = "✅" if enable else "🔴"
        action_text = "تفعيل" if enable else "تعطيل"
        
        keyboard = [
            [
                InlineKeyboardButton("🔴 تعطيل الخدمة", callback_data=f"toggle_{service_type}_disable"),
                InlineKeyboardButton("🟢 تفعيل الخدمة", callback_data=f"toggle_{service_type}_enable")
            ],
            [
                InlineKeyboardButton("🔙 رجوع للإدارة المتقدمة", callback_data="advanced_service_management")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await loading_message.edit_text(
            f"""⚙️ <b>إدارة تفصيلية - {service_name}</b>

{status_icon} تم {action_text} الخدمة بنجاح!

📊 <b>الحالة الحالية:</b> {'مفعلة' if enable else 'معطلة'}

🎯 يمكنك تفعيل أو تعطيل هذه الخدمة المحددة

⚠️ <b>ملاحظة:</b> عند التعطيل، سيتم إشعار جميع المستخدمين تلقائياً""",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"خطأ في handle_service_toggle: {e}")
        await query.edit_message_text(f"❌ حدث خطأ: {str(e)}")

# دوال إدارة خدمات البروكسي (تشغيل/إيقاف)

async def handle_manage_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة قائمة إدارة خدمات البروكسي"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # التحقق من أن المستخدم هو أدمن
    if not context.user_data.get('is_admin', False):
        await query.edit_message_text("❌ ليس لديك صلاحية للوصول لهذا القسم")
        return
    
    # فحص توفر NonVoip
    nonvoip_status = "✅" if NONVOIP_AVAILABLE else "⚠️"
    
    keyboard = [
        [InlineKeyboardButton(f"📱 {nonvoip_status} إدارة خدمات NonVoip", callback_data="manage_nonvoip_services")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_manage_proxies")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⚙️ إدارة الخدمات\n\n"
        "اختر الخدمة التي تريد إدارتها:",
        reply_markup=reply_markup
    )

async def handle_manage_nonvoip_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة قائمة إدارة خدمات NonVoip (تشغيل/إيقاف)"""
    query = update.callback_query
    await query.answer()
    
    # التحقق من أن المستخدم هو أدمن
    global ACTIVE_ADMINS
    user_id = query.from_user.id
    is_admin = context.user_data.get('is_admin', False) or user_id in ACTIVE_ADMINS
    
    if not is_admin:
        await query.edit_message_text("❌ ليس لديك صلاحية للوصول لهذا القسم")
        return
    
    # تأكيد حالة الأدمن في context
    context.user_data['is_admin'] = True
    
    if not NONVOIP_AVAILABLE:
        await query.edit_message_text("❌ وحدة NonVoip غير متاحة حالياً\n\nالرجاء التحقق من إعدادات NonVoipUsNumber")
        return
    
    # حالة خدمة NonVoip (تستخدم service_type = 'nonvoip')
    from non_voip_unified import NonVoipDB
    nvdb = NonVoipDB()
    
    # فحص إذا كانت الخدمة مفعلة (نستخدم نظام service_status)
    nonvoip_enabled = db.get_service_status('nonvoip', 'basic')
    
    keyboard = []
    
    # زر تشغيل/إيقاف خدمة NonVoip الكاملة
    status = "🟢" if nonvoip_enabled else "🔴"
    action = "disable" if nonvoip_enabled else "enable"
    toggle_text = "❌ إيقاف خدمة NonVoip" if nonvoip_enabled else "✅ تشغيل خدمة NonVoip"
    keyboard.append([InlineKeyboardButton(
        toggle_text,
        callback_data=f"toggle_nonvoip_basic_{action}"
    )])
    
    # معلومات عن الخدمة
    keyboard.append([InlineKeyboardButton("━━━━━ معلومات الخدمة ━━━━━", callback_data="separator")])
    
    availability_status = "✅ متاحة للمستخدمين" if nonvoip_enabled else "🔴 غير متاحة للمستخدمين"
    
    # زر العودة
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="manage_services")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"""📱 إدارة خدمات NonVoipUsNumber

{status} حالة الخدمة: {availability_status}

🔧 يمكنك تشغيل أو إيقاف خدمة الأرقام بالكامل من هنا.
عند الإيقاف، لن يتمكن المستخدمون من شراء أرقام جديدة.

🟢 = مفعل | 🔴 = معطل""",
        reply_markup=reply_markup
    )

async def handle_toggle_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة تشغيل/إيقاف خدمة معينة"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    # عرض رسالة تحميل
    loading_message = await query.edit_message_text("⏳ جاري التحديث...")
    
    try:
        service_names = {
            'basic': 'الأساسية',
            'nonvoip': 'خدمة Non-VOIP'
        }
        
        if callback_data.startswith("toggle_nonvoip_"):
            # تشغيل/إيقاف خدمة NonVoip
            try:
                parts = callback_data.split("_")
                if len(parts) < 4:
                    await loading_message.edit_text("❌ خطأ: بيانات غير صحيحة")
                    return
                
                service_subtype = "_".join(parts[2:-1])  # سيكون "basic"
                action = parts[-1]
                enable = action == "enable"
                
                # حفظ حالة NonVoip في قاعدة البيانات
                db.set_service_status('nonvoip', enable, service_subtype)
                logger.info(f"تم {'تشغيل' if enable else 'إيقاف'} خدمة NonVoip: {service_subtype}")
                
                # إرسال إشعار للآدمن - هذا هو الإصلاح الرئيسي!
                await send_admin_notification(context, "خدمة Non-VOIP", enable, 'nonvoip')
                
                # العودة لقائمة إدارة NonVoip
                await handle_manage_nonvoip_services(update, context)
            except Exception as inner_error:
                logger.error(f"خطأ في toggle_nonvoip: {inner_error}")
                await loading_message.edit_text("❌ حدث خطأ في تعديل خدمة NonVoip")
            
        # معالجات جديدة للدول والولايات حسب الخدمة
        elif callback_data.startswith("toggle_all_svc_countries_"):
            # تشغيل/إيقاف جميع دول خدمة محددة
            parts = callback_data.replace("toggle_all_svc_countries_", "").split("_")
            if len(parts) >= 2:
                service_type = "_".join(parts[:-1])
                enable = parts[-1] == "True"
                db.toggle_all_countries('static', service_type, enable)
                await send_admin_notification(context, f"جميع دول {service_type}", enable)
                await handle_manage_service_countries(update, context)
        
        elif callback_data.startswith("toggle_svc_country_") or callback_data.startswith("tsc_"):
            # تشغيل/إيقاف دولة محددة لخدمة محددة
            if callback_data.startswith("tsc_"):
                # تنسيق مختصر: tsc_svc_country_action
                parts = callback_data.replace("tsc_", "").split("_")
                if len(parts) >= 3:
                    svc_short = parts[0]
                    country_code = parts[1]
                    action = parts[2]
                    
                    # عكس الاختصارات
                    service_type = {
                        'mr': 'monthly_residential',
                        'mv': 'monthly_verizon',
                        'isp': 'isp_att',
                        'dc': 'datacenter',
                        'wc': 'weekly_crocker',
                        'ds': 'daily_static'
                    }.get(svc_short, svc_short)
                    
                    enable = action == "1"  # 1=enable, 0=disable
            else:
                # تنسيق قديم
                parts = callback_data.replace("toggle_svc_country_", "").split("_")
                if len(parts) >= 3:
                    action = parts[-1]
                    country_code = parts[-2]
                    service_type = "_".join(parts[:-2])
                    enable = action == "enable"
            
            db.set_service_status('static', enable, service_type, country_code)
            
            country_names = {
                'US': '🇺🇸 أمريكا', 'UK': '🇬🇧 بريطانيا',
                'FR': '🇫🇷 فرنسا', 'DE': '🇩🇪 ألمانيا', 'AT': '🇦🇹 النمسا'
            }
            service_name = country_names.get(country_code, country_code)
            await send_admin_notification(context, f"{service_name} في {service_type}", enable, 'static')
            
            # إعادة الطلب للعودة لنفس الصفحة
            await handle_manage_service_countries(update, context)
        
        elif callback_data.startswith("toggle_all_svc_states_"):
            # تشغيل/إيقاف جميع ولايات خدمة محددة
            parts = callback_data.replace("toggle_all_svc_states_", "").split("_")
            if len(parts) >= 2:
                service_type = "_".join(parts[:-1])
                enable = parts[-1] == "True"
                db.toggle_all_states('static', 'US', service_type, enable)
                await send_admin_notification(context, f"جميع ولايات {service_type}", enable)
                await handle_manage_service_states(update, context)
        
        elif callback_data.startswith("toggle_svc_state_") or callback_data.startswith("tss_"):
            # تشغيل/إيقاف ولاية محددة لخدمة محددة
            if callback_data.startswith("tss_"):
                # تنسيق مختصر: tss_svc_state_action
                parts = callback_data.replace("tss_", "").split("_")
                if len(parts) >= 3:
                    svc_short = parts[0]
                    state_code = parts[1]
                    action = parts[2]
                    
                    # عكس الاختصارات
                    service_type = {
                        'mr': 'monthly_residential',
                        'mv': 'monthly_verizon',
                        'isp': 'isp_att',
                        'dc': 'datacenter',
                        'wc': 'weekly_crocker',
                        'ds': 'daily_static'
                    }.get(svc_short, svc_short)
                    
                    enable = action == "1"  # 1=enable, 0=disable
            else:
                # تنسيق قديم
                parts = callback_data.replace("toggle_svc_state_", "").split("_")
                if len(parts) >= 3:
                    action = parts[-1]
                    state_code = parts[-2]
                    service_type = "_".join(parts[:-2])
                    enable = action == "enable"
            
            db.set_service_status('static', enable, service_type, 'US', state_code)
            
            state_names = {
                'NY': '🏙️ نيويورك', 'CA': '🌴 كاليفورنيا', 'TX': '🤠 تكساس',
                'FL': '🏖️ فلوريدا', 'VA': '🏛️ فيرجينيا', 'WA': '🌲 واشنطن',
                'AZ': '🌵 أريزونا', 'MA': '📚 ماساتشوستس', 'DE': '🏛️ ديلاوير'
            }
            service_name = state_names.get(state_code, state_code)
            await send_admin_notification(context, f"{service_name} في {service_type}", enable, 'static')
            
            # إعادة الطلب للعودة لنفس الصفحة
            await handle_manage_service_states(update, context)
            
        else:
            await loading_message.edit_text("❌ إجراء غير صحيح")
            
    except Exception as e:
        logger.error(f"خطأ في تشغيل/إيقاف الخدمة: {e}")
        try:
            await loading_message.edit_text("❌ حدث خطأ أثناء تحديث الخدمة")
        except:
            pass

# إنشاء معالجات المحادثة للبروكسيات المجانية

# معالج إدارة البروكسيات (المجانية والمدفوعة)
free_proxy_conv_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(handle_add_free_proxy, pattern="^add_free_proxy$"),
        CallbackQueryHandler(handle_delete_free_proxy, pattern="^delete_free_proxy$"),
    ],
    states={
        ADD_FREE_PROXY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_free_proxy_message),
        ],
        DELETE_FREE_PROXY: [
            CallbackQueryHandler(handle_view_proxy_for_delete, pattern="^view_proxy_"),
            CallbackQueryHandler(handle_confirm_delete_proxy, pattern="^confirm_delete_"),
            CallbackQueryHandler(handle_delete_free_proxy, pattern="^delete_free_proxy$"),
        ],
    },
    fallbacks=[
        CallbackQueryHandler(handle_cancel_add_proxy, pattern="^cancel_add_proxy$"),
        CallbackQueryHandler(handle_back_to_manage_proxies, pattern="^back_to_manage_proxies$"),
        CallbackQueryHandler(handle_back_to_admin_menu, pattern="^back_to_admin_menu$"),
    ],
    allow_reentry=True
)

# معالج قبول طلبات شحن الرصيد مع إدخال قيمة الآدمن
recharge_approval_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(handle_approve_recharge, pattern="^approve_recharge_")],
    states={
        ADMIN_RECHARGE_AMOUNT_INPUT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_recharge_amount_input)
        ]
    },
    fallbacks=[],
    allow_reentry=True
)

def setup_bot():
    """إعداد البوت وإضافة جميع المعالجات"""
    try:
        print("🔧 فحص إعدادات البوت...")
        
        if not TOKEN:
            print("❌ خطأ: لم يتم تعيين توكن البوت")
            return None
        
        print(f"✅ التوكن موجود: {TOKEN[:10]}...{TOKEN[-10:]}")
        
        print("🔧 بدء تهيئة البوت...")
        
        print("📊 تهيئة قاعدة البيانات...")
        # تهيئة نظام الأسئلة الشائعة FAQ
        try:
            init_faq_database()
            insert_faq_content()
            print("✅ تم تهيئة نظام FAQ بنجاح")
        except Exception as e:
            print(f"⚠️ تحذير: خطأ في تهيئة نظام FAQ: {e}")
        
        print("⚠️ لم يتم العثور على تسجيل دخول أدمن سابق")
        
        # إنشاء ملفات المساعدة
        print("📁 إنشاء ملفات المساعدة...")
        create_requirements_file()
        print("✅ تم إنشاء ملفات المساعدة")
        
        # إنشاء تطبيق التيليجرام
        print("⚡ إنشاء تطبيق التيليجرام...")
        application = Application.builder().token(TOKEN).build()
        print("✅ تم إنشاء التطبيق بنجاح")
        
        # اختبار الاتصال
        print("🌐 اختبار الاتصال مع خوادم تيليجرام...")
        print("🌐 سيتم اختبار الاتصال عند بدء التشغيل...")
        
        # إضافة المعالجات
        print("🔧 إضافة معالجات الأوامر...")
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("profile", profile_command))
        application.add_handler(CommandHandler("about", handle_about_command))
        application.add_handler(CommandHandler("terms", terms_command))
        application.add_handler(CommandHandler("reset", handle_reset_command))
        application.add_handler(CommandHandler("cleanup", handle_cleanup_command))
        application.add_handler(CommandHandler("status", handle_status_command))
        
        # ============================================
        # معالجات أوامر Luxury Support (اختيار الدولة/الولاية/المدينة)
        # ============================================
        if LUXURY_AVAILABLE:
            async def handle_select_country_cmd(update, context):
                from luxury_service import show_country_options_message
                if update.message and update.message.text:
                    parts = update.message.text.split()
                    country_code = parts[1] if len(parts) > 1 else ""
                    if country_code:
                        await show_country_options_message(update, context, country_code)
            
            async def handle_select_state_cmd(update, context):
                from luxury_service import show_city_options_message
                if update.message and update.message.text:
                    parts = update.message.text.split(maxsplit=2)
                    country_code = parts[1] if len(parts) > 1 else ""
                    state = parts[2] if len(parts) > 2 else ""
                    if country_code and state:
                        await show_city_options_message(update, context, country_code, state)
            
            async def handle_select_city_cmd(update, context):
                from luxury_service import show_proxy_options_message
                if update.message and update.message.text:
                    parts = update.message.text.split(maxsplit=3)
                    country_code = parts[1] if len(parts) > 1 else ""
                    state = parts[2] if len(parts) > 2 else ""
                    city = parts[3] if len(parts) > 3 else ""
                    if country_code:
                        await show_proxy_options_message(update, context, country_code, state, city)
            
            async def handle_select_isp_cmd(update, context):
                from luxury_service import process_random_purchase
                if update.message and update.message.text:
                    parts = update.message.text.split(maxsplit=4)
                    country_code = parts[1] if len(parts) > 1 else ""
                    state = parts[2].replace("-", " ") if len(parts) > 2 else ""
                    city = parts[3].replace("-", " ") if len(parts) > 3 else ""
                    isp = parts[4].replace("-", " ").replace("_", "/") if len(parts) > 4 else ""
                    if country_code:
                        await process_random_purchase(update, context, country_code, state or None, city or None, isp or None)
            
            async def handle_select_proxy_cmd(update, context):
                from luxury_service import show_proxy_confirm_by_id
                if update.message and update.message.text:
                    parts = update.message.text.split(maxsplit=1)
                    proxy_id = parts[1].strip() if len(parts) > 1 else ""
                    if proxy_id:
                        await show_proxy_confirm_by_id(update, context, proxy_id)
            
            application.add_handler(CommandHandler("select_country", handle_select_country_cmd))
            application.add_handler(CommandHandler("select_state", handle_select_state_cmd))
            application.add_handler(CommandHandler("select_city", handle_select_city_cmd))
            application.add_handler(CommandHandler("select_isp", handle_select_isp_cmd))
            application.add_handler(CommandHandler("select_proxy", handle_select_proxy_cmd))
        
        # ============================================
        # معالجات أوامر إدارة الرسائل للآدمن
        # ============================================
        application.add_handler(CommandHandler("msg_options", handle_msg_options))
        application.add_handler(CommandHandler("msg_delete", handle_msg_delete))
        application.add_handler(CommandHandler("msg_pin", handle_msg_pin))
        application.add_handler(CommandHandler("msg_unpin", handle_msg_unpin))
        # msg_edit_conv_handler موجود في bot_admin.py - تم دمجه بنجاح
        application.add_handler(msg_edit_conv_handler)
        application.add_handler(CommandHandler("msg_clean", handle_msg_clean))

        # معالج تأكيد حذف جميع الرسائل
        application.add_handler(CallbackQueryHandler(handle_msg_clean_confirmation, pattern="^(confirm_msg_clean|cancel_msg_clean)$"))
        
        # معالج تعديلات الرسائل (لتطبيق التعديلات على جميع المستخدمين)
        application.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited_message))

        print("🔧 إضافة معالجات المحادثات...")
        application.add_handler(admin_conv_handler)
        application.add_handler(password_change_conv_handler)
        application.add_handler(admin_functions_conv_handler)
        application.add_handler(process_order_conv_handler)
        application.add_handler(broadcast_conv_handler)
        application.add_handler(payment_conv_handler)
        application.add_handler(services_message_conv_handler)
        application.add_handler(exchange_rate_message_conv_handler)
        application.add_handler(terms_message_conv_handler)
        application.add_handler(free_proxy_conv_handler)
        application.add_handler(recharge_approval_conv_handler)
        
        print("🔧 إضافة معالجات الرسائل...")
        
        # إضافة معالج Inline Query الموحد لتجنب التضارب
        from non_voip_unified import handle_nonvoip_inline_query
        from luxury_service import handle_luxury_inline_query
        
        async def unified_inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            query_text = update.inline_query.query.strip().lower()
            # توجيه الطلب بناءً على الكلمة الافتتاحية
            # Luxury: أي بحث فارغ أو يبدأ بـ socks أو سوكس أو أي حرف (للبحث المباشر)
            if query_text.startswith("socks") or query_text.startswith("سوكس") or query_text == "":
                return await handle_luxury_inline_query(update, context)
            # NonVoip: يبدأ بـ nv: أو nonvoip أو أرقام
            if query_text.startswith("nv:") or query_text.startswith("nonvoip") or query_text.startswith("أرقام"):
                return await handle_nonvoip_inline_query(update, context)
            # البحث العام: يوجه إلى Luxury للبحث عن الدول
            return await handle_luxury_inline_query(update, context)

        application.add_handler(InlineQueryHandler(unified_inline_query_handler))
        
        # إضافة معالجات Callback لـ Non-Voip
        if NONVOIP_AVAILABLE:
            application.add_handler(CallbackQueryHandler(handle_buy_callback, pattern="^nv_buy_"))
            application.add_handler(CallbackQueryHandler(handle_confirm_buy_callback, pattern="^nv_confirm_buy_"))
            application.add_handler(CallbackQueryHandler(handle_confirm_buy_callback, pattern="^nv_cancel_buy$"))
            application.add_handler(CallbackQueryHandler(handle_cancel_order_callback, pattern="^nv_cancel_order_"))
            application.add_handler(CallbackQueryHandler(handle_activate_number_callback, pattern="^nv_activate_"))
            application.add_handler(CallbackQueryHandler(handle_manual_check_callback, pattern="^nv_manual_check_"))
            application.add_handler(CallbackQueryHandler(handle_sync_last3_callback, pattern="^nv_sync_last3_"))
            print("✅ تم إضافة معالجات Non-Voip")
        
        # إضافة معالج Inline Query لـ PremSocks
        # تم دمجه في unified_inline_query_handler أعلاه
        if PREMSOCKS_AVAILABLE:
            # application.add_handler(InlineQueryHandler(handle_premsocks_inline_query))
            pass
        
        # إضافة معالجات Callback لـ SMSPool
        if SMSPOOL_AVAILABLE:
            application.add_handler(CallbackQueryHandler(handle_smspool_user_callbacks, pattern="^sp_"))
            application.add_handler(CallbackQueryHandler(handle_manage_smspool_admin, pattern="^manage_smspool_admin$"))
            print("✅ تم إضافة معالجات SMSPool")
        
        # معالج الأسئلة الشائعة FAQ
        # معالج الأسئلة الشائعة - يشمل جميع callbacks المتعلقة بـ FAQ
        async def handle_all_faq_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """معالجة جميع callbacks المتعلقة بـ FAQ"""
            query = update.callback_query
            await query.answer()
            data = query.data
            
            # إذا كان faq_menu أو show_faq، نعرض قائمة الأسئلة
            if data in ["faq_menu", "show_faq"]:
                await show_faq_menu(update, context)
            # إذا كان faq_{id}، نعرض الإجابة
            elif data.startswith("faq_"):
                await handle_faq_callback(update, context)
        
        # نسجل معالج FAQ بنمط صحيح يطابق: faq_{digits} و show_faq و faq_menu
        application.add_handler(CallbackQueryHandler(handle_all_faq_callbacks, pattern="^(faq_\\d+|show_faq|faq_menu)$"))
        print("✅ تم إضافة معالج الأسئلة الشائعة FAQ")
        
        # معالج زر العودة للقائمة الرئيسية
        async def handle_back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """معالجة زر العودة للقائمة الرئيسية من أي مكان"""
            query = update.callback_query
            await query.answer()
            user_id = update.effective_user.id
            language = get_user_language(user_id)
            keyboard = create_main_user_keyboard(language)
            message = MESSAGES[language]['welcome']
            
            # حذف الرسالة القديمة (التي تحتوي على inline keyboard)
            try:
                await query.message.delete()
            except Exception:
                pass
            
            # إرسال رسالة جديدة مع الكيبورد العادي (ReplyKeyboardMarkup)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        
        application.add_handler(CallbackQueryHandler(handle_back_to_main, pattern="^back_to_main$"))
        
        # معالج قائمة طلباتي للمستخدم
        application.add_handler(CallbackQueryHandler(handle_my_orders_callback, pattern="^user_(order_reminder|pending_orders|previous_orders|back_main_menu|back_orders_menu)$"))
        
        # معالجات عرض وإلغاء الطلبات للمستخدم
        application.add_handler(CallbackQueryHandler(show_user_order_details, pattern="^user_view_order_"))
        application.add_handler(CallbackQueryHandler(handle_user_cancel_order, pattern="^user_cancel_order_"))
        application.add_handler(CallbackQueryHandler(confirm_user_cancel_order, pattern="^user_confirm_cancel_"))
        application.add_handler(CallbackQueryHandler(show_user_previous_order_details, pattern="^user_prev_order_"))
        
        application.add_handler(CallbackQueryHandler(handle_callback_query))
        # تم إزالة معالج callback المتداخل للسوكس لحل المشكلة
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo_messages))
        application.add_handler(MessageHandler(filters.Document.ALL, handle_document_messages))
        
        # إضافة معالج الأخطاء الشامل
        print("🔧 إضافة معالج الأخطاء الشامل...")
        application.add_error_handler(global_error_handler)
        
        # إضافة المهمة المجدولة لفحص الحظر المنتهي
        print("🔧 إضافة نظام فحص الحظر المنتهي...")
        try:
            # التحقق من وجود job_queue قبل الاستخدام
            if application.job_queue is not None:
                # إضافة مهمة دورية كل 5 دقائق للفحص عن الحظر المنتهي
                application.job_queue.run_repeating(
                    callback=lambda context: check_expired_bans_periodically(application), 
                    interval=300,  # 5 دقائق بالثواني
                    first=30,  # البدء بعد 30 ثانية من تشغيل البوت
                    name='ban_checker'
                )
                print("✅ تم إضافة نظام فحص الحظر المنتهي (كل 5 دقائق)")
                
                # إضافة نظام مراقبة رسائل SMS للأرقام
                if NONVOIP_AVAILABLE:
                    try:
                        # مراقبة الرسائل كل 15 ثانية
                        application.job_queue.run_repeating(
                            callback=job_poll_sms,
                            interval=15,
                            first=10,
                            name='sms_monitor'
                        )
                        
                        # التحقق من الأرقام المنتهية كل دقيقة
                        application.job_queue.run_repeating(
                            callback=job_check_expired,
                            interval=60,
                            first=30,
                            name='expired_checker')
                        
                        # التحقق من التفعيلات المنتهية كل دقيقة
                        application.job_queue.run_repeating(
                            callback=job_check_activation_expiry,
                            interval=60,
                            first=45,
                            name='activation_expiry_checker'
                        )
                        
                        # فحص رصيد NonVoip مرتين يومياً (12 ظهراً و6 مساءً بتوقيت سوريا)
                        import datetime
                        import pytz
                        syria_tz = pytz.timezone('Asia/Damascus')
                        
                        # الفحص الأول: 12 ظهراً
                        noon_time = datetime.time(hour=12, minute=0, second=0, tzinfo=syria_tz)
                        application.job_queue.run_daily(
                            callback=job_check_nonvoip_balance,
                            time=noon_time,
                            name='nonvoip_balance_checker_noon'
                        )
                        
                        # الفحص الثاني: 6 مساءً
                        evening_time = datetime.time(hour=18, minute=0, second=0, tzinfo=syria_tz)
                        application.job_queue.run_daily(
                            callback=job_check_nonvoip_balance,
                            time=evening_time,
                            name='nonvoip_balance_checker_evening'
                        )
                        
                        print("✅ تم إضافة نظام فحص رصيد NonVoip (مرتين يومياً: 12 ظهراً و6 مساءً)")
                        
                        print("✅ تم إضافة نظام مراقبة رسائل SMS (كل 15 ثانية)")
                    except Exception as sms_error:
                        print(f"⚠️ تحذير: فشل في إضافة نظام مراقبة SMS: {sms_error}")
            else:
                print("⚠️ تحذير: JobQueue غير متوفر - يجب تثبيت python-telegram-bot[job-queue]")
        except Exception as e:
            print(f"⚠️ تحذير: فشل في إضافة نظام فحص الحظر: {e}")
        
        # تهيئة نظام مراقبة الصحة
        # تم إزالة نظام مراقبة الصحة لحل مشكلة تسجيل الخروج التلقائي
        print("✅ تم تهيئة البوت بنجاح (مع نظام الحظر المتدرج)")
        
        print("✅ تم إضافة جميع المعالجات")
        print("📊 قاعدة البيانات جاهزة")
        print("⚡ البوت يعمل الآن!")
        print(f"🔑 التوكن: {TOKEN[:10]}...")
        print("💡 في انتظار الرسائل...")
        print("✅ البوت جاهز للتشغيل!")
        
        return application
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء التطبيق أو الاتصال: {e}")
        import traceback
        traceback.print_exc()
        return None

def check_bot_lock():
    """فحص وإنشاء قفل البوت - يعمل على Windows و Unix/Linux"""
    lock_file = None
    
    if FCNTL_AVAILABLE:
        # نظام Unix/Linux - استخدام fcntl
        try:
            lock_file = open('bot.lock', 'w')
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            lock_file.write(str(os.getpid()))
            lock_file.flush()
            print("🔒 تم الحصول على قفل البوت بنجاح (Unix/Linux)")
            return lock_file
        except IOError:
            print("❌ يوجد بوت آخر يعمل بالفعل!")
            print("⚠️ يرجى إيقاف البوت الآخر أولاً أو استخدام:")
            print("   pkill -f proxy_bot.py")
            if lock_file:
                lock_file.close()
            return None
    else:
        # نظام Windows - استخدام ملف PID
        try:
            if os.path.exists('bot.lock'):
                # قراءة PID من الملف
                with open('bot.lock', 'r') as f:
                    old_pid = f.read().strip()
                
                # التحقق من وجود العملية
                if old_pid.isdigit():
                    try:
                        if platform.system() == "Windows":
                            # على Windows، نستخدم tasklist للتحقق من وجود العملية
                            result = subprocess.run(['tasklist', '/FI', f'PID eq {old_pid}'], 
                                                  capture_output=True, text=True)
                            if old_pid in result.stdout:
                                print("❌ يوجد بوت آخر يعمل بالفعل!")
                                print("⚠️ يرجى إيقاف البوت الآخر أولاً أو حذف ملف bot.lock")
                                return None
                        else:
                            # على Unix/Linux، نستخدم os.kill مع الإشارة 0
                            os.kill(int(old_pid), 0)
                            print("❌ يوجد بوت آخر يعمل بالفعل!")
                            print("⚠️ يرجى إيقاف البوت الآخر أولاً أو حذف ملف bot.lock")
                            return None
                    except (OSError, subprocess.SubprocessError):
                        # العملية غير موجودة، يمكننا المتابعة
                        pass
            
            # إنشاء ملف القفل الجديد
            lock_file = open('bot.lock', 'w')
            lock_file.write(str(os.getpid()))
            lock_file.flush()
            print("🔒 تم الحصول على قفل البوت بنجاح (Windows)")
            return lock_file
            
        except Exception as e:
            print(f"⚠️ تحذير: لا يمكن إنشاء قفل البوت: {e}")
            print("سيتم تشغيل البوت بدون قفل")
            return None

def cleanup_bot_lock(lock_file):
    """تنظيف قفل البوت"""
    if lock_file:
        try:
            if FCNTL_AVAILABLE:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()
            os.unlink('bot.lock')
            print("🔓 تم تحرير قفل البوت")
        except:
            pass

# متغير عالمي لحفظ رسالة الخدمات
SERVICES_MESSAGE = {
    'ar': 'هذه رسالة الخدمات الافتراضية. يمكن للإدارة تعديلها.',
    'en': 'This is the default services message. Admin can modify it.'
}

# متغير عالمي لحفظ رسالة سعر الصرف
EXCHANGE_RATE_MESSAGE = {
    'ar': 'هذه رسالة سعر الصرف الافتراضية. يمكن للإدارة تعديلها.',
    'en': 'This is the default exchange rate message. Admin can modify it.'
}

# متغير عالمي لحفظ رسالة الشروط والأحكام
TERMS_MESSAGE = {
    'ar': '''📜 <b>الشروط والأحكام</b>

🔹 بإستخدامك لهذا البوت فأنت توافق على الشروط والأحكام التالية:

1️⃣ جميع خدمات البروكسي والأرقام مقدمة كما هي
2️⃣ يمنع استخدام الخدمات في أي نشاط غير قانوني
3️⃣ لا يمكن استرجاع المبالغ المدفوعة إلا في حالات خاصة
4️⃣ نحن غير مسؤولين عن أي استخدام خاطئ للخدمات
5️⃣ يحق للإدارة تعليق أو إيقاف أي حساب مخالف

📞 للاستفسارات، تواصل مع الدعم الفني''',
    'en': '''📜 <b>Terms and Conditions</b>

🔹 By using this bot, you agree to the following terms and conditions:

1️⃣ All proxy and number services are provided as-is
2️⃣ Using services for illegal activities is prohibited
3️⃣ Refunds are only available in special cases
4️⃣ We are not responsible for misuse of services
5️⃣ Management reserves the right to suspend violating accounts

📞 For inquiries, contact technical support'''
}

async def handle_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة زر المزيد من الخدمات"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    message = "اختر ما تريد من القائمة" if language == 'ar' else "Choose what you want from the menu"
    
    keyboard = [
        [InlineKeyboardButton(
            "📋 لمحة عن خدمات البوت" if language == 'ar' else "📋 About Bot Services", 
            callback_data="show_bot_services"
        )],
        [InlineKeyboardButton(
            "💱 سعر الصرف" if language == 'ar' else "💱 Exchange Rate", 
            callback_data="show_exchange_rate"
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup)


async def handle_show_bot_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة زر لمحة عن خدمات البوت - Fun1 الأصلية"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    language = get_user_language(user_id)
    
    # الحصول على رسالة الخدمات من قاعدة البيانات أو استخدام الافتراضية
    try:
        result = db.execute_query("SELECT value FROM settings WHERE key = ?", (f'services_message_{language}',))
        services_msg = result[0][0] if result else SERVICES_MESSAGE[language]
    except:
        services_msg = SERVICES_MESSAGE[language]
    
    await query.edit_message_text(services_msg, parse_mode='HTML')


async def handle_show_exchange_rate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة زر سعر الصرف - من inline button"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    language = get_user_language(user_id)
    
    # الحصول على رسالة سعر الصرف من قاعدة البيانات أو استخدام الافتراضية
    try:
        result = db.execute_query("SELECT value FROM settings WHERE key = ?", (f'exchange_rate_message_{language}',))
        exchange_msg = result[0][0] if result else EXCHANGE_RATE_MESSAGE[language]
    except:
        exchange_msg = EXCHANGE_RATE_MESSAGE[language]
    
    await query.edit_message_text(exchange_msg, parse_mode='HTML')

async def show_exchange_rate_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض رسالة سعر الصرف مباشرة - من الكيبورد الرئيسي"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    # الحصول على رسالة سعر الصرف من قاعدة البيانات أو استخدام الافتراضية
    try:
        result = db.execute_query("SELECT value FROM settings WHERE key = ?", (f'exchange_rate_message_{language}',))
        exchange_msg = result[0][0] if result else EXCHANGE_RATE_MESSAGE[language]
    except:
        exchange_msg = EXCHANGE_RATE_MESSAGE[language]
    
    await update.message.reply_text(exchange_msg, parse_mode='HTML')

async def show_services_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض رسالة لمحة عن الخدمات مباشرة - محدثة مع زر FAQ"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    # الحصول على رسالة الخدمات من قاعدة البيانات أو استخدام الافتراضية
    try:
        result = db.execute_query("SELECT value FROM settings WHERE key = ?", (f'services_message_{language}',))
        services_msg = result[0][0] if result else SERVICES_MESSAGE[language]
    except:
        services_msg = SERVICES_MESSAGE[language]
    
    # إضافة زر الأسئلة الشائعة
    if language == 'ar':
        keyboard = [[InlineKeyboardButton("❓ الأسئلة الشائعة", callback_data="faq_menu")]]
    else:
        keyboard = [[InlineKeyboardButton("❓ FAQ", callback_data="faq_menu")]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(services_msg, parse_mode='HTML', reply_markup=reply_markup)

async def handle_buy_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج زر شراء الأرقام للمستخدمين"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    if not NONVOIP_AVAILABLE:
        message = "❌ خدمة الأرقام غير متاحة حالياً.\nيرجى التواصل مع الآدمن." if language == 'ar' else "❌ Numbers service is not available.\nPlease contact admin."
        await update.message.reply_text(message)
        return
    
    # التحقق من حالة الخدمة في قاعدة البيانات
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

async def handle_daily_socks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج زر سوكس يومي للمستخدمين"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    if not LUXURY_AVAILABLE:
        message = "❌ خدمة سوكس يومي غير متاحة حالياً.\nيرجى التواصل مع الآدمن." if language == 'ar' else "❌ Daily SOCKS service is not available.\nPlease contact admin."
        await update.message.reply_text(message)
        return
    
    # التحقق من حالة الخدمة
    if not luxury_db.is_service_enabled():
        message = "⚠️ هذه الخدمة متوقفة مؤقتاً\n\nرمز الخطأ: x0x000A" if language == 'ar' else "⚠️ This service is temporarily disabled\n\nError code: x0x000A"
        await update.message.reply_text(message)
        return
    
    # عرض قائمة سوكس يومي (Luxury Support)
    keyboard = [
        [InlineKeyboardButton(get_luxury_message('buy_proxy', language), callback_data="lx_buy_menu")],
        [InlineKeyboardButton(get_luxury_message('my_proxies', language), callback_data="lx_my_proxies")],
        [InlineKeyboardButton(get_luxury_message('back', language), callback_data="lx_back_main")]
    ]
    
    await update.message.reply_text(
        f"🌐 <b>{get_luxury_message('menu_title', language)}</b>\n\n{get_luxury_message('menu_desc', language)}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def handle_manage_nonvoip_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة قائمة إدارة الأرقام للآدمن"""
    if not NONVOIP_AVAILABLE:
        await update.callback_query.edit_message_text("❌ خدمة الأرقام غير متاحة حالياً")
        return
    
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # التحقق من أن المستخدم هو أدمن
    if not context.user_data.get('is_admin', False):
        await query.edit_message_text("❌ ليس لديك صلاحية للوصول لهذا القسم")
        return
    
    try:
        api = NonVoipAPI()
        balance_result = api.get_balance()
        
        lang = get_user_language(user_id)
        
        balance_text = f"💰 الرصيد الحالي: ${balance_result.get('balance', '0.00')}" if balance_result.get('status') == 'success' else "❌ تعذر جلب الرصيد"
        
        
        # الحصول على حالة إشعارات انخفاض رصيد NonVoip
        try:
            conn_notif = sqlite3.connect(DATABASE_FILE)
            cursor_notif = conn_notif.cursor()
            cursor_notif.execute("SELECT value FROM settings WHERE key = 'nonvoip_balance_notifications_enabled'")
            notif_setting = cursor_notif.fetchone()
            notifications_enabled = notif_setting[0] == '1' if notif_setting else True
            conn_notif.close()
        except:
            notifications_enabled = True
        
        notif_status = "🔔 مفعّلة" if notifications_enabled else "🔕 معطّلة"
        
        keyboard = [
            [InlineKeyboardButton("💰 عرض الرصيد", callback_data="nva_balance")],
        [InlineKeyboardButton(f"{notif_status} إشعارات انخفاض رصيد NonVoip", callback_data="nva_toggle_balance_notif")],
            [InlineKeyboardButton("📦 عرض المنتجات المتاحة", callback_data="nva_products")],
            [InlineKeyboardButton("📋 عرض جميع الطلبات", callback_data="nva_orders")],
            [InlineKeyboardButton("⚙️ إعدادات الأرقام", callback_data="nva_settings")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="manage_external_proxies")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"""📱 *إدارة أرقام Non-Voip*
_(nonvoipusnumber.com)_

{balance_text}

اختر العملية المطلوبة:"""
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"خطأ في إدارة الأرقام: {e}")
        await query.edit_message_text(f"❌ حدث خطأ: {str(e)}")

async def handle_nonvoip_admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة callbacks إدارة الأرقام للآدمن"""
    query = update.callback_query
    
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        
        if query.data == "nva_balance":
            await nonvoip_admin_balance(update, context, conn)
        elif query.data == "nva_products":
            await nonvoip_admin_products(update, context, conn)
        elif query.data == "nva_orders":
            await nonvoip_admin_all_orders(update, context, conn)
        elif query.data == "nva_settings":
            await query.answer()
            await query.edit_message_text(
                "⚙️ *إعدادات الأرقام*\n\n🚧 قيد التطوير...\n\nستتمكن قريباً من:\n• تعديل السعر الافتراضي\n• إدارة الهوامش\n• تفعيل/تعطيل الخدمة",
                parse_mode=ParseMode.MARKDOWN
            )
        elif query.data == "nva_toggle_balance_notif":
            # تبديل حالة إشعارات انخفاض رصيد NonVoip
            await query.answer()
            
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = 'nonvoip_balance_notifications_enabled'")
            current_setting = cursor.fetchone()
            current_enabled = current_setting[0] == '1' if current_setting else True
            
            # تبديل الحالة
            new_state = '0' if current_enabled else '1'
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                ('nonvoip_balance_notifications_enabled', new_state)
            )
            conn.commit()
            
            # رسالة التأكيد
            status_text = "🔔 مفعّلة" if new_state == '1' else "🔕 معطّلة"
            message = f"*{status_text} إشعارات انخفاض رصيد NonVoip*\n\n"
            if new_state == '1':
                message += "✅ سيتم إرسال إشعارات عند انخفاض الرصيد تحت:\n• $20 (تنبيه)\n• $10 (تحذير)\n• $5 (خطر)\n\n"
                message += "⏰ يتم الفحص مرتين يومياً: 12 ظهراً و6 مساءً (توقيت سوريا)"
            else:
                message += "⚠️ لن يتم إرسال إشعارات انخفاض الرصيد حتى يتم التفعيل مجدداً"
            
            await query.edit_message_text(message, parse_mode=ParseMode.MARKDOWN)
            
            # العودة لقائمة إدارة NonVoip بعد ثانيتين
            import asyncio
            await asyncio.sleep(2)
            await handle_manage_nonvoip_admin(update, context)
        
        conn.close()
    except Exception as e:
        logger.error(f"خطأ في معالجة callback الآدمن: {e}")
        await query.answer("❌ حدث خطأ")

async def handle_nonvoip_user_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة callbacks شراء الأرقام للمستخدمين"""
    query = update.callback_query
    
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        
        # معالجات القائمة الرئيسية
        if query.data == "nv_request_new":
            await nonvoip_select_type(update, context, conn)
        elif query.data == "nv_country_usa":
            await nonvoip_select_type(update, context, conn)
        elif query.data == "nv_my_numbers":
            await nonvoip_my_numbers(update, context, conn)
        elif query.data == "nv_sync_numbers":
            await nonvoip_sync_numbers(update, context, conn)
        elif query.data == "nv_history":
            await nonvoip_history(update, context, conn)
        elif query.data.startswith("nv_view_messages_"):
            order_id = query.data.replace('nv_view_messages_', '')
            logger.info(f"📱 معالجة عرض رسائل الرقم - order_id: {order_id} من المستخدم {update.effective_user.id}")
            await nonvoip_view_number_messages(update, context, conn)
        
        # معالجات اختيار النوع والولاية
        elif query.data.startswith("nv_type_"):
            await nonvoip_select_type(update, context, conn)
        elif query.data.startswith("nv_state_"):
            await nonvoip_select_type(update, context, conn)
        elif query.data == "nv_all_states":
            await nonvoip_select_type(update, context, conn)
        
        # معالجات الشراء
        elif query.data.startswith("nv_prod_"):
            await nonvoip_confirm_order(update, context, conn)
        elif query.data.startswith("nv_confirm_") and not query.data.startswith("nv_confirm_renew"):
            await nonvoip_process_order(update, context, conn)
        
        # معالجات التجديد
        elif query.data.startswith("nv_renew_"):
            await nonvoip_renew_number(update, context, conn)
        elif query.data.startswith("nv_confirm_renew_"):
            await nonvoip_process_renew(update, context, conn)
        
        # معالجات الرجوع
        elif query.data == "nv_back_menu" or query.data == "nv_back":
            await nonvoip_main_menu(update, context, conn)
        elif query.data == "nv_country_usa":
            # الرجوع إلى قائمة أنواع الأرقام
            await nonvoip_select_type(update, context, conn)
        elif query.data == "nv_type_short_term":
            # الرجوع إلى قائمة الولايات
            number_type = context.user_data.get('selected_number_type', 'short_term')
            await nonvoip_select_type(update, context, conn)
        elif query.data == "nv_exit_to_main":
            await query.answer()
            await query.message.delete()
        
        conn.close()
    except Exception as e:
        logger.error(f"خطأ في معالجة callback المستخدم: {e}")
        await query.answer("❌ حدث خطأ")

# وظائف إدارة المستخدم المتقدمة الجديدة

async def handle_ban_user_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة حظر المستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    # تأكيد الحظر
    keyboard = [
        [
            InlineKeyboardButton("✅ نعم، حظر المستخدم", callback_data=f"confirm_ban_{user_id}"),
            InlineKeyboardButton("❌ إلغاء", callback_data=f"back_to_profile_{user_id}")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    
    message = f"""⚠️ <b>تأكيد حظر المستخدم</b>

📋 <b>المستخدم:</b> {first_name} {last_name}
🆔 <b>المعرف:</b> <code>{user_id}</code>

🚫 <b>هل أنت متأكد من حظر هذا المستخدم؟</b>

⚠️ <b>تحذير:</b> المستخدم المحظور لن يتمكن من استخدام البوت نهائياً"""
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

async def handle_unban_user_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة فك حظر المستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    # تأكيد فك الحظر
    keyboard = [
        [
            InlineKeyboardButton("✅ نعم، فك الحظر", callback_data=f"confirm_unban_{user_id}"),
            InlineKeyboardButton("❌ إلغاء", callback_data=f"back_to_profile_{user_id}")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    
    message = f"""✅ <b>تأكيد فك حظر المستخدم</b>

📋 <b>المستخدم:</b> {first_name} {last_name}
🆔 <b>المعرف:</b> <code>{user_id}</code>

🔓 <b>هل أنت متأكد من فك حظر هذا المستخدم؟</b>

ℹ️ <b>ملاحظة:</b> المستخدم سيتمكن من استخدام البوت مرة أخرى"""
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

async def handle_remove_temp_ban_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة رفع الحظر المؤقت بسبب العمليات التخريبية"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    # تأكيد رفع الحظر المؤقت
    keyboard = [
        [
            InlineKeyboardButton("✅ نعم، رفع الحظر المؤقت", callback_data=f"confirm_remove_temp_ban_{user_id}"),
            InlineKeyboardButton("❌ إلغاء", callback_data=f"back_to_profile_{user_id}")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    
    message = f"""🛠️ <b>رفع الحظر المؤقت</b>

📋 <b>المستخدم:</b> {first_name} {last_name}
🆔 <b>المعرف:</b> <code>{user_id}</code>

🔧 <b>رفع الحظر المؤقت بسبب العمليات التخريبية</b>

ℹ️ <b>هذا الخيار مخصص للمستخدمين المحظورين مؤقتاً بسبب:</b>
• النقر المتكرر أو السريع
• محاولة استغلال النظام
• أنشطة مشبوهة أخرى

✅ <b>سيتم إزالة الحظر المؤقت وإعادة تعيين عداد المخالفات</b>"""
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

async def handle_add_points_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة إضافة النقاط"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    # حفظ بيانات المستخدم المحدد
    context.user_data['target_user_id'] = user_id
    context.user_data['points_action'] = 'add'
    context.user_data['awaiting_points_input'] = True
    
    current_balance = float(user_data[6]) if user_data[6] else 0.0
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    
    keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data=f"manage_points_{user_id}")]]
    
    message = f"""➕ إضافة نقاط للمستخدم

📋 المستخدم: {first_name} {last_name}
🆔 المعرف: {user_id}
💳 الرصيد الحالي: ${current_balance:.2f}

💰 أدخل عدد النقاط المراد إضافتها:
(مثال: 1.5 لإضافة 1.5 كريديت)"""
    
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_subtract_points_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة خصم النقاط"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    # حفظ بيانات المستخدم المحدد
    context.user_data['target_user_id'] = user_id
    context.user_data['points_action'] = 'subtract'
    context.user_data['awaiting_points_input'] = True
    
    current_balance = float(user_data[6]) if user_data[6] else 0.0
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    
    keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data=f"manage_points_{user_id}")]]
    
    message = f"""➖ خصم نقاط من المستخدم

📋 المستخدم: {first_name} {last_name}
🆔 المعرف: {user_id}
💳 الرصيد الحالي: ${current_balance:.2f}

💸 أدخل عدد النقاط المراد خصمها:
(مثال: 0.5 لخصم 0.5 كريديت)"""
    
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_points_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """معالجة إدخال النقاط من الآدمن"""
    text = update.message.text.strip()
    
    try:
        amount = float(text)
        if amount <= 0:
            await update.message.reply_text("❌ الرجاء إدخال قيمة موجبة")
            return True
    except ValueError:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح")
        return True
    
    target_user_id = context.user_data.get('target_user_id')
    action = context.user_data.get('points_action')
    
    if not target_user_id or not action:
        await update.message.reply_text("❌ خطأ: بيانات العملية غير متوفرة")
        context.user_data.pop('awaiting_points_input', None)
        return True
    
    try:
        target_user_id = int(target_user_id)
    except:
        await update.message.reply_text("❌ خطأ في معرف المستخدم")
        context.user_data.pop('awaiting_points_input', None)
        return True
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # جلب الرصيد الحالي
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (target_user_id,))
    result = cursor.fetchone()
    
    if not result:
        await update.message.reply_text("❌ المستخدم غير موجود")
        conn.close()
        context.user_data.pop('awaiting_points_input', None)
        return True
    
    current_balance = float(result[0]) if result[0] else 0.0
    
    if action == 'add':
        new_balance = current_balance + amount
        cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, target_user_id))
        action_text = "إضافة"
        action_emoji = "➕"
    else:  # subtract
        if amount > current_balance:
            await update.message.reply_text(f"❌ لا يمكن خصم {amount} - الرصيد الحالي {current_balance:.2f} فقط")
            conn.close()
            return True
        new_balance = current_balance - amount
        cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, target_user_id))
        action_text = "خصم"
        action_emoji = "➖"
    
    conn.commit()
    conn.close()
    
    # تنظيف البيانات
    context.user_data.pop('awaiting_points_input', None)
    context.user_data.pop('points_action', None)
    context.user_data.pop('target_user_id', None)
    
    success_message = f"""✅ تمت العملية بنجاح!

{action_emoji} العملية: {action_text} نقاط
🆔 المستخدم: {target_user_id}
💰 القيمة: {amount:.2f} كريديت
💳 الرصيد السابق: {current_balance:.2f}
💵 الرصيد الجديد: {new_balance:.2f}"""
    
    await update.message.reply_text(success_message)
    return True

async def handle_add_referral_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة إدراج إحالة جديدة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    # حفظ بيانات المستخدم المحدد
    context.user_data['target_user_id'] = user_id
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    
    message = f"""➕ <b>إدراج إحالة جديدة</b>

📋 <b>المُحيل:</b> {first_name} {last_name}
🆔 <b>معرف المُحيل:</b> <code>{user_id}</code>

👤 <b>أدخل اسم المستخدم أو المعرف للمستخدم المُحال:</b>
(مثال: @username أو 123456789)

ℹ️ <b>ملاحظة:</b> سيتم ربط هذا المستخدم كإحالة من المُحيل المحدد"""
    
    await query.edit_message_text(message, parse_mode='HTML')
    return ADD_REFERRAL_USERNAME

async def handle_delete_referral_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة حذف إحالة محددة مع عرض أسماء المحالين"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    # جلب قائمة المستخدمين المحالين
    try:
        referrals = db.execute_query("""
            SELECT u.user_id, u.username, u.first_name, u.last_name, r.referred_at
            FROM referrals r
            JOIN users u ON r.referred_id = u.user_id
            WHERE r.referrer_id = ?
            ORDER BY r.referred_at DESC
        """, (user_id,))
        
        if not referrals:
            # تهريب الأحرف الخاصة في الأسماء
            first_name = escape_markdown(user_data[2] or "")
            last_name = escape_markdown(user_data[3] or "")
            
            await query.edit_message_text(f"""❌ <b>لا توجد إحالات</b>

📋 <b>المستخدم:</b> {first_name} {last_name}
🆔 <b>المعرف:</b> <code>{user_id}</code>

🔍 <b>هذا المستخدم لا يملك أي إحالات ليتم حذفها</b>""", parse_mode='HTML')
            return
        
        # إنشاء قائمة بالمحالين
        keyboard = []
        for i, referral in enumerate(referrals[:10]):  # أول 10 إحالات
            ref_id, username, first_name, last_name, referred_at = referral
            display_name = f"{first_name or ''} {last_name or ''}".strip() or f"مستخدم {ref_id}"
            username_text = f"@{username}" if username else "بدون اسم مستخدم"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"🗑️ {display_name} ({username_text})",
                    callback_data=f"confirm_delete_referral_{user_id}_{ref_id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔙 رجوع للملف", callback_data=f"back_to_profile_{user_id}")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # تهريب الأحرف الخاصة في الأسماء
        first_name = escape_markdown(user_data[2] or "")
        last_name = escape_markdown(user_data[3] or "")
        
        message = f"""❌ <b>حذف إحالة محددة</b>

📋 <b>المُحيل:</b> {first_name} {last_name}
🆔 <b>المعرف:</b> <code>{user_id}</code>

👥 <b>اختر المستخدم المُحال المراد حذفه:</b>
(عدد الإحالات: {len(referrals)})"""
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        await query.edit_message_text(f"❌ خطأ في جلب الإحالات: {str(e)}")

async def handle_reset_referral_balance_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة تصفير رصيد الإحالة فقط"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    referral_earnings = float(user_data[5]) if user_data[5] else 0.0
    
    # تأكيد تصفير رصيد الإحالة
    keyboard = [
        [
            InlineKeyboardButton("✅ نعم، تصفير رصيد الإحالة", callback_data=f"confirm_reset_referral_balance_{user_id}"),
            InlineKeyboardButton("❌ إلغاء", callback_data=f"back_to_profile_{user_id}")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    
    message = f"""🗑️ <b>تصفير رصيد الإحالة</b>

📋 <b>المستخدم:</b> {first_name} {last_name}
🆔 <b>المعرف:</b> <code>{user_id}</code>
💰 <b>رصيد الإحالة الحالي:</b> <code>${referral_earnings:.2f}</code>

⚠️ <b>هل أنت متأكد من تصفير رصيد الإحالة؟</b>

ℹ️ <b>ملاحظة:</b> سيتم تصفير رصيد الإحالة فقط وليس حذف الإحالات نفسها"""
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

async def handle_single_user_broadcast_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة إرسال رسالة نصية للمستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    # حفظ بيانات المستخدم المحدد
    context.user_data['target_user_id'] = user_id
    context.user_data['broadcast_type'] = 'text'
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    username = escape_markdown(user_data[1] or "غير محدد")
    
    message = f"""📝 <b>رسالة نصية للمستخدم</b>

📋 <b>المستخدم:</b> {first_name} {last_name}
🆔 <b>المعرف:</b> <code>{user_id}</code>
📱 <b>اسم المستخدم:</b> @{username}

💬 <b>أدخل الرسالة النصية:</b>"""
    
    await query.edit_message_text(message, parse_mode='HTML')
    return SINGLE_USER_BROADCAST_MESSAGE

async def handle_single_user_broadcast_photo_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة إرسال رسالة مع صورة للمستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    # حفظ بيانات المستخدم المحدد
    context.user_data['target_user_id'] = user_id
    context.user_data['broadcast_type'] = 'photo'
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    username = escape_markdown(user_data[1] or "غير محدد")
    
    message = f"""🖼️ <b>رسالة مع صورة للمستخدم</b>

📋 <b>المستخدم:</b> {first_name} {last_name}
🆔 <b>المعرف:</b> <code>{user_id}</code>
📱 <b>اسم المستخدم:</b> @{username}

📷 <b>أرسل الصورة مع النص (اختياري):</b>"""
    
    await query.edit_message_text(message, parse_mode='HTML')
    return SINGLE_USER_BROADCAST_MESSAGE

async def handle_single_user_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة رسالة البث للمستخدم الفردي (نص أو صورة)"""
    target_user_id = context.user_data.get('target_user_id')
    broadcast_type = context.user_data.get('broadcast_type')
    
    if not target_user_id:
        await update.message.reply_text("❌ خطأ: معرف المستخدم غير موجود")
        await restore_admin_keyboard(context, update.effective_chat.id)
        return
    
    try:
        # التحقق من نوع الرسالة (صورة أو نص)
        photo_file_id = None
        message_text = ""
        
        if update.message.photo:
            # رسالة تحتوي على صورة
            photo_file_id = update.message.photo[-1].file_id
            message_text = update.message.caption or ""
        elif update.message.text:
            # رسالة نصية فقط
            message_text = update.message.text
        else:
            await update.message.reply_text("❌ يرجى إرسال رسالة نصية أو صورة!")
            return
        
        # إرسال الرسالة للمستخدم المستهدف مع دعم MarkdownV2 للـ spoiler
        if photo_file_id:
            # إرسال صورة مع نص مع دعم MarkdownV2
            await context.bot.send_photo(
                chat_id=target_user_id,
                photo=photo_file_id,
                caption=message_text,
                parse_mode=ParseMode.MARKDOWN_V2
            )
        else:
            # إرسال نص فقط مع دعم MarkdownV2
            await context.bot.send_message(
                chat_id=target_user_id,
                text=message_text,
                parse_mode=ParseMode.MARKDOWN_V2
            )
        
        # تأكيد للأدمن
        user_data = context.user_data.get('selected_user_data')
        if user_data:
            first_name = user_data[2] or ""
            last_name = user_data[3] or ""
            
            success_message = f"""✅ تم إرسال الرسالة بنجاح!

📋 المستخدم: {first_name} {last_name}
🆔 المعرف: {target_user_id}
📨 نوع الرسالة: {"صورة مع نص" if photo_file_id else "نص"}"""
        else:
            success_message = f"✅ تم إرسال الرسالة للمستخدم {target_user_id} بنجاح!"
        
        await update.message.reply_text(success_message)
        
        # تنظيف البيانات المؤقتة
        context.user_data.pop('target_user_id', None)
        context.user_data.pop('broadcast_type', None)
        
        # إعادة تفعيل كيبورد الأدمن
        await restore_admin_keyboard(context, update.effective_chat.id, "✅ تم إرسال الرسالة - لوحة الأدمن جاهزة")
        
    except Exception as e:
        logger.error(f"خطأ في إرسال رسالة البث الفردية: {e}")
        await update.message.reply_text(f"❌ حدث خطأ أثناء إرسال الرسالة:\n{str(e)}")
        await restore_admin_keyboard(context, update.effective_chat.id)

async def handle_quick_message_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الرسائل السريعة (قوالب جاهزة)"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    # قوالب الرسائل السريعة
    keyboard = [
        [
            InlineKeyboardButton("🎉 تهنئة", callback_data=f"quick_template_congratulation_{user_id}"),
            InlineKeyboardButton("⚠️ تحذير", callback_data=f"quick_template_warning_{user_id}")
        ],
        [
            InlineKeyboardButton("ℹ️ إشعار", callback_data=f"quick_template_notification_{user_id}"),
            InlineKeyboardButton("🛠️ صيانة", callback_data=f"quick_template_maintenance_{user_id}")
        ],
        [
            InlineKeyboardButton("💰 عرض خاص", callback_data=f"quick_template_offer_{user_id}"),
            InlineKeyboardButton("📞 دعم فني", callback_data=f"quick_template_support_{user_id}")
        ],
        [
            InlineKeyboardButton("🔙 رجوع للملف", callback_data=f"back_to_profile_{user_id}")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    
    message = f"""⚡ <b>رسالة سريعة (قوالب جاهزة)</b>

📋 <b>المستخدم:</b> {first_name} {last_name}
🆔 <b>المعرف:</b> <code>{user_id}</code>

📝 <b>اختر نوع الرسالة السريعة:</b>"""
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

async def handle_important_notice_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الإشعارات الهامة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    # حفظ بيانات المستخدم المحدد
    context.user_data['target_user_id'] = user_id
    context.user_data['broadcast_type'] = 'important'
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    username = escape_markdown(user_data[1] or "غير محدد")
    
    message = f"""📢 <b>إشعار هام للمستخدم</b>

📋 <b>المستخدم:</b> {first_name} {last_name}
🆔 <b>المعرف:</b> <code>{user_id}</code>
📱 <b>اسم المستخدم:</b> @{username}

⚠️ <b>أدخل الإشعار الهام:</b>
(سيتم إرساله بتنسيق خاص ليبرز أهميته)"""
    
    await query.edit_message_text(message, parse_mode='HTML')
    return SINGLE_USER_BROADCAST_MESSAGE

async def handle_back_to_user_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """العودة لملف المستخدم الشخصي"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    # إعادة عرض ملف المستخدم
    await show_user_profile_detailed(update, context, user_id, user_data)

# دوال التأكيد الجديدة لإدارة المستخدم المتقدمة

async def handle_confirm_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تأكيد حظر المستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    try:
        # إضافة المستخدم لقائمة المحظورين
        db.execute_query("""
            INSERT OR REPLACE INTO banned_users (user_id, username, ban_reason, banned_at, banned_by)
            VALUES (?, ?, ?, datetime('now'), ?)
        """, (user_id, user_data[1], "حظر من الأدمن", update.effective_user.id))
        
        # إرسال إشعار للمستخدم المحظور
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="🚫 <b>تم حظرك من استخدام البوت</b>\n\nللاستفسار تواصل مع الإدارة",
                parse_mode='HTML'
            )
        except:
            pass  # المستخدم قد يكون حظر البوت
        
        # تهريب الأحرف الخاصة في الأسماء
        first_name = escape_markdown(user_data[2] or "")
        last_name = escape_markdown(user_data[3] or "")
        username = escape_markdown(user_data[1] or "غير محدد")
        
        success_message = f"""✅ <b>تم حظر المستخدم بنجاح</b>

📋 <b>المستخدم:</b> {first_name} {last_name}
🆔 <b>المعرف:</b> <code>{user_id}</code>
📱 <b>اسم المستخدم:</b> @{username}

🚫 <b>الحالة:</b> محظور نهائياً
📅 <b>تاريخ الحظر:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}

✅ <b>تم إرسال إشعار للمستخدم بالحظر</b>"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع لقائمة الأدمن", callback_data="back_to_admin_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(success_message, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        await query.edit_message_text(f"❌ خطأ في حظر المستخدم: {str(e)}")

async def handle_confirm_unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تأكيد فك حظر المستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    try:
        # إزالة المستخدم من قائمة المحظورين
        db.execute_query("DELETE FROM banned_users WHERE user_id = ?", (user_id,))
        
        # إزالة الحظر المؤقت أيضاً إن وجد
        if user_id in TEMP_BANNED_USERS:
            del TEMP_BANNED_USERS[user_id]
        
        # إرسال إشعار للمستخدم
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ <b>تم فك حظرك من البوت</b>\n\nيمكنك الآن استخدام البوت بشكل طبيعي\nمرحباً بك مرة أخرى! 🎉",
                parse_mode='HTML'
            )
        except:
            pass
        
        # تهريب الأحرف الخاصة في الأسماء
        first_name = escape_markdown(user_data[2] or "")
        last_name = escape_markdown(user_data[3] or "")
        username = escape_markdown(user_data[1] or "غير محدد")
        
        success_message = f"""✅ <b>تم فك حظر المستخدم بنجاح</b>

📋 <b>المستخدم:</b> {first_name} {last_name}
🆔 <b>المعرف:</b> <code>{user_id}</code>
📱 <b>اسم المستخدم:</b> @{username}

🔓 <b>الحالة:</b> تم فك الحظر
📅 <b>تاريخ فك الحظر:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}

✅ <b>تم إرسال إشعار للمستخدم بفك الحظر</b>"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع لقائمة الأدمن", callback_data="back_to_admin_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(success_message, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        await query.edit_message_text(f"❌ خطأ في فك حظر المستخدم: {str(e)}")

async def handle_confirm_remove_temp_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تأكيد رفع الحظر المؤقت"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    try:
        # رفع الحظر المؤقت
        if user_id in TEMP_BANNED_USERS:
            del TEMP_BANNED_USERS[user_id]
            temp_ban_removed = True
        else:
            temp_ban_removed = False
        
        # إزالة عداد النقرات السريعة
        if user_id in USER_CLICK_COUNT:
            del USER_CLICK_COUNT[user_id]
        
        if user_id in USER_LAST_CLICK:
            del USER_LAST_CLICK[user_id]
        
        # إرسال إشعار للمستخدم
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="🛠️ <b>تم رفع الحظر المؤقت</b>\n\nتم إزالة الحظر المؤقت وإعادة تعيين عداد المخالفات\nيمكنك الآن استخدام البوت بشكل طبيعي 🎉",
                parse_mode='HTML'
            )
        except:
            pass
        
        status = "تم رفع الحظر المؤقت" if temp_ban_removed else "لم يكن محظوراً مؤقتاً"
        
        # تهريب الأحرف الخاصة في الأسماء
        first_name = escape_markdown(user_data[2] or "")
        last_name = escape_markdown(user_data[3] or "")
        username = escape_markdown(user_data[1] or "غير محدد")
        
        success_message = f"""🛠️ <b>رفع الحظر المؤقت</b>

📋 <b>المستخدم:</b> {first_name} {last_name}
🆔 <b>المعرف:</b> <code>{user_id}</code>
📱 <b>اسم المستخدم:</b> @{username}

🔧 <b>الحالة:</b> {status}
📅 <b>تاريخ المعالجة:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}

✅ <b>تم إعادة تعيين عداد المخالفات</b>
✅ <b>تم إرسال إشعار للمستخدم</b>"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع لقائمة الأدمن", callback_data="back_to_admin_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(success_message, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        await query.edit_message_text(f"❌ خطأ في رفع الحظر المؤقت: {str(e)}")

async def handle_confirm_reset_referral_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تأكيد تصفير رصيد الإحالة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    try:
        old_balance = float(user_data[5]) if user_data[5] else 0.0
        
        # تصفير رصيد الإحالة فقط
        db.execute_query("UPDATE users SET referral_balance = 0 WHERE user_id = ?", (user_id,))
        
        # تهريب الأحرف الخاصة في الأسماء
        first_name = escape_markdown(user_data[2] or "")
        last_name = escape_markdown(user_data[3] or "")
        
        success_message = f"""🗑️ <b>تم تصفير رصيد الإحالة بنجاح</b>

📋 <b>المستخدم:</b> {first_name} {last_name}
🆔 <b>المعرف:</b> <code>{user_id}</code>

💰 <b>الرصيد السابق:</b> <code>${old_balance:.2f}</code>
💰 <b>الرصيد الحالي:</b> <code>$0.00</code>

✅ <b>تم تصفير رصيد الإحالة فقط</b>
ℹ️ <b>الإحالات نفسها لم يتم حذفها</b>"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع لقائمة الأدمن", callback_data="back_to_admin_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(success_message, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        await query.edit_message_text(f"❌ خطأ في تصفير رصيد الإحالة: {str(e)}")

async def handle_confirm_delete_referral(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تأكيد حذف إحالة محددة"""
    query = update.callback_query
    await query.answer()
    
    # استخراج معرف المُحيل ومعرف المُحال
    parts = query.data.split("_")
    referrer_id = parts[-2]
    referred_id = parts[-1]
    
    try:
        # جلب معلومات المستخدم المُحال
        referred_user = db.execute_query("""
            SELECT username, first_name, last_name 
            FROM users WHERE user_id = ?
        """, (referred_id,))
        
        if not referred_user:
            await query.edit_message_text("❌ خطأ: المستخدم المُحال غير موجود")
            return
        
        referred_username, referred_first, referred_last = referred_user[0]
        referred_name = f"{referred_first or ''} {referred_last or ''}".strip() or f"مستخدم {referred_id}"
        
        # حذف الإحالة
        db.execute_query("DELETE FROM referrals WHERE referrer_id = ? AND referred_id = ?", 
                        (referrer_id, referred_id))
        
        success_message = f"""❌ <b>تم حذف الإحالة بنجاح</b>

📋 <b>المُحيل:</b> معرف <code>{referrer_id}</code>
👤 <b>المُحال المحذوف:</b> {referred_name}
🆔 <b>معرف المُحال:</b> <code>{referred_id}</code>
📱 <b>اسم المستخدم:</b> @{referred_username or 'غير محدد'}

✅ <b>تم حذف الإحالة من قاعدة البيانات</b>
📅 <b>تاريخ الحذف:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع لقائمة الأدمن", callback_data="back_to_admin_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(success_message, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        await query.edit_message_text(f"❌ خطأ في حذف الإحالة: {str(e)}")

async def handle_quick_template_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة اختيار قالب الرسالة السريعة"""
    query = update.callback_query
    await query.answer()
    
    # استخراج نوع القالب ومعرف المستخدم
    parts = query.data.split("_")
    template_type = parts[2]  # congratulation, warning, etc.
    user_id = parts[-1]
    
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    # قوالب الرسائل السريعة
    templates = {
        'congratulation': "🎉 <b>تهنئة!</b>\n\nنهنئك على استخدامك المميز لخدماتنا!\nشكراً لك على ثقتك بنا 💫",
        'warning': "⚠️ <b>تحذير هام</b>\n\nيرجى الالتزام بشروط الاستخدام\nوتجنب أي أنشطة مخالفة للقوانين",
        'notification': "ℹ️ <b>إشعار</b>\n\nنود إعلامك بتحديث في خدماتنا\nيرجى مراجعة القائمة الرئيسية للتفاصيل",
        'maintenance': "🛠️ <b>إشعار صيانة</b>\n\nسيتم إجراء صيانة دورية على النظام\nشكراً لتفهمكم",
        'offer': "💰 <b>عرض خاص</b>\n\nلديك عرض خاص متاح الآن!\nاستفد من الخصومات المتاحة",
        'support': "📞 <b>دعم فني</b>\n\nفريق الدعم الفني جاهز لمساعدتك\nلا تتردد في التواصل معنا"
    }
    
    template_message = templates.get(template_type, "📝 رسالة عامة")
    
    try:
        # إرسال الرسالة للمستخدم
        await context.bot.send_message(
            chat_id=user_id,
            text=template_message,
            parse_mode='HTML'
        )
        
        # تهريب الأحرف الخاصة في الأسماء
        first_name = escape_markdown(user_data[2] or "")
        last_name = escape_markdown(user_data[3] or "")
        
        success_message = f"""✅ <b>تم إرسال الرسالة السريعة بنجاح</b>

📋 <b>المستخدم:</b> {first_name} {last_name}
🆔 <b>المعرف:</b> <code>{user_id}</code>
📝 <b>نوع الرسالة:</b> {template_type}

📤 <b>تم إرسال الرسالة بنجاح</b>
📅 <b>وقت الإرسال:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع لقائمة الأدمن", callback_data="back_to_admin_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(success_message, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        await query.edit_message_text(f"❌ خطأ في إرسال الرسالة: {str(e)}")


# دوال معالجة أزرار إدارة المستخدمين المتقدمة
async def handle_back_to_user_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """العودة لملف المستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        # إعادة البحث عن بيانات المستخدم
        user_result = db.execute_query("SELECT * FROM users WHERE user_id = ?", (user_id,))
        if not user_result:
            await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
            return
        user_data = user_result[0]
        context.user_data['selected_user_data'] = user_data
    
    # إعادة عرض ملف المستخدم
    await display_user_profile(query, user_data, context)

async def display_user_profile(query, user_data, context):
    """عرض ملف المستخدم"""
    user_id = user_data[0]
    current_balance = float(user_data[6]) if user_data[6] else 0.0
    referral_earned = float(user_data[5]) if user_data[5] else 0.0
    
    # الحصول على إحصائيات محدثة
    successful_orders = db.execute_query(
        "SELECT COUNT(*), SUM(payment_amount) FROM orders WHERE user_id = ? AND status = 'completed'",
        (user_id,)
    )[0]
    
    referral_count = db.execute_query(
        "SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,)
    )[0][0]
    
    status_text = "🟢 نشط" if current_balance > 0 or successful_orders[0] > 0 else "🟡 غير نشط"
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    username = escape_markdown(user_data[1] or "غير محدد")
    
    report = f"""📊 ملف المستخدم المحدث

👤 <b>البيانات الشخصية</b>
• الاسم: {first_name} {last_name}
• اسم المستخدم: @{username}  
• المعرف: <code>{user_id}</code>
• الحالة: {status_text}

💰 <b>النظام المالي</b>
• الرصيد الحالي: <code>${current_balance:.2f}</code>
• رصيد الإحالات: <code>${referral_earned:.2f}</code>

📈 <b>إحصائيات الطلبات</b>
• الطلبات الناجحة: <code>{successful_orders[0]}</code> (${successful_orders[1] or 0:.2f})
• عدد المُحالين: <code>{referral_count}</code> شخص"""
    
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
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(report, reply_markup=reply_markup, parse_mode='HTML')

async def handle_show_referred_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض قائمة المُحالين"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    
    # الحصول على قائمة المُحالين
    referrals = db.execute_query("""
        SELECT u.user_id, u.first_name, u.last_name, u.username, r.created_at
        FROM referrals r
        JOIN users u ON r.referred_id = u.user_id
        WHERE r.referrer_id = ?
        ORDER BY r.created_at DESC
    """, (user_id,))
    
    if not referrals:
        message = f"👥 <b>قائمة المُحالين</b>\n\n❌ لا يوجد مستخدمون محالون"
    else:
        referral_list = []
        for i, (ref_id, fname, lname, username, created_at) in enumerate(referrals[:10], 1):
            name = f"{fname} {lname}".strip()
            username_text = f"@{username}" if username else "لا يوجد"
            referral_list.append(f"{i}. <b>{name}</b> ({username_text})\n   • المعرف: <code>{ref_id}</code>\n   • تاريخ الإحالة: {created_at[:10]}")
        
        total_count = len(referrals)
        message = f"👥 <b>قائمة المُحالين</b> (إجمالي: {total_count})\n\n" + "\n\n".join(referral_list)
        
        if total_count > 10:
            message += f"\n\n📋 *عرض أول 10 من أصل {total_count} محال*"
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع لإدارة الإحالات", callback_data=f"manage_referrals_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

async def handle_referral_earnings_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض سجل أرباح الإحالات"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    # الحصول على سجل المعاملات المالية للإحالات
    transactions = db.execute_query("""
        SELECT transaction_type, amount, created_at, description
        FROM credits_transactions 
        WHERE user_id = ? AND transaction_type LIKE '%referral%'
        ORDER BY created_at DESC LIMIT 10
    """, (user_id,))
    
    referral_earnings = float(user_data[5]) if user_data[5] else 0.0
    
    if not transactions:
        message = f"💰 <b>سجل أرباح الإحالات</b>\n\n• إجمالي الأرباح: <code>${referral_earnings:.2f}</code>\n\n❌ لا توجد معاملات مسجلة"
    else:
        transaction_list = []
        for trans_type, amount, created_at, desc in transactions:
            date = created_at[:10] if created_at else "غير معروف"
            transaction_list.append(f"• <b>+${amount:.2f}</b> - {date}\n  {desc or 'مكافأة إحالة'}")
        
        message = f"💰 <b>سجل أرباح الإحالات</b>\n\n• إجمالي الأرباح: <code>${referral_earnings:.2f}</code>\n\n📊 <b>آخر المعاملات:</b>\n\n" + "\n\n".join(transaction_list)
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع لإدارة الإحالات", callback_data=f"manage_referrals_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

async def handle_full_report_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تقرير شامل للمستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    # الحصول على بيانات شاملة
    current_balance = float(user_data[6]) if user_data[6] else 0.0
    referral_earned = float(user_data[5]) if user_data[5] else 0.0
    
    # إحصائيات طلبات البروكسي
    orders_stats = db.execute_query("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN status = 'completed' THEN payment_amount ELSE 0 END) as total_spent
        FROM orders WHERE user_id = ?
    """, (user_id,))
    
    stats = orders_stats[0] if orders_stats else (0, 0, 0, 0, 0)
    proxy_spent = float(stats[4]) if stats[4] is not None else 0.0
    
    # إحصائيات طلبات NonVoIP
    nonvoip_stats = nonvoip_db.get_user_orders(int(user_id), limit=1000) if nonvoip_db else []
    nonvoip_count = len(nonvoip_stats)
    nonvoip_short = sum(1 for o in nonvoip_stats if o.get('type') == 'short_term')
    nonvoip_3days = sum(1 for o in nonvoip_stats if o.get('type') == '3days')
    nonvoip_long = sum(1 for o in nonvoip_stats if o.get('type') == 'long_term')
    nonvoip_spent = sum(float(o.get('sale_price') or 0) for o in nonvoip_stats if not o.get('refunded'))
    
    # إجمالي الإنفاق
    total_spent = proxy_spent + nonvoip_spent
    
    # إحصائيات الإحالات
    referral_count = db.execute_query("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))[0][0]
    
    # آخر نشاط (بروكسي و NonVoIP)
    last_order = db.execute_query("SELECT created_at FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT 1", (user_id,))
    last_proxy = last_order[0][0][:10] if last_order else None
    last_nonvoip = nonvoip_stats[0].get('created_at', '')[:10] if nonvoip_stats else None
    last_activity = last_proxy or last_nonvoip or "لا يوجد"
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    
    report = f"""📊 <b>التقرير الشامل</b>

👤 <b>المستخدم:</b> {first_name} {last_name}
🆔 <b>المعرف:</b> <code>{user_id}</code>
📅 <b>تاريخ الانضمام:</b> {user_data[7][:10] if user_data[7] else 'غير معروف'}

━━━━━━━━━━━━━━━━━━━━━━━
💰 <b>الملف المالي</b>
• الرصيد الحالي: <code>${current_balance:.2f}</code>
• رصيد الإحالات: <code>${referral_earned:.2f}</code>
• إجمالي الإنفاق: <code>${total_spent:.2f}</code>
  ├ بروكسي: <code>${proxy_spent:.2f}</code>
  └ أرقام: <code>${nonvoip_spent:.2f}</code>
• صافي الرصيد: <code>${(current_balance + referral_earned):.2f}</code>

━━━━━━━━━━━━━━━━━━━━━━━
🌐 <b>طلبات البروكسي</b>
• إجمالي الطلبات: <code>{stats[0]}</code>
• المكتملة: <code>{stats[1]}</code> | المعلقة: <code>{stats[2]}</code> | الفاشلة: <code>{stats[3]}</code>

━━━━━━━━━━━━━━━━━━━━━━━
📱 <b>طلبات الأرقام (NonVoIP)</b>
• إجمالي الطلبات: <code>{nonvoip_count}</code>
• 15 دقيقة: <code>{nonvoip_short}</code> | 3 أيام: <code>{nonvoip_3days}</code> | 30 يوم: <code>{nonvoip_long}</code>

━━━━━━━━━━━━━━━━━━━━━━━
👥 <b>نظام الإحالات</b>
• عدد المُحالين: <code>{referral_count}</code>
• أرباح الإحالات: <code>${referral_earned:.2f}</code>

━━━━━━━━━━━━━━━━━━━━━━━
📅 <b>النشاط</b>
• آخر نشاط: {last_activity}"""
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع للتقارير", callback_data=f"detailed_reports_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(report, reply_markup=reply_markup, parse_mode='HTML')

async def handle_financial_report_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """التقرير المالي المفصل"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    current_balance = float(user_data[6]) if user_data[6] else 0.0
    referral_earned = float(user_data[5]) if user_data[5] else 0.0
    
    # الحصول على تفاصيل المعاملات المالية
    transactions = db.execute_query("""
        SELECT transaction_type, amount, created_at, description
        FROM credits_transactions 
        WHERE user_id = ? 
        ORDER BY created_at DESC LIMIT 10
    """, (user_id,))
    
    # حساب الإنفاق حسب نوع الخدمة
    spending_by_service = db.execute_query("""
        SELECT proxy_type, COUNT(*), SUM(payment_amount)
        FROM orders 
        WHERE user_id = ? AND status = 'completed'
        GROUP BY proxy_type
    """, (user_id,))
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    
    report = f"""💰 <b>التقرير المالي المفصل</b>

👤 <b>المستخدم:</b> {first_name} {last_name}

━━━━━━━━━━━━━━━━━━━━━━━
💳 <b>الرصيد الحالي</b>
• الرصيد الأساسي: <code>${current_balance:.2f}</code>
• رصيد الإحالات: <code>${referral_earned:.2f}</code>
• المجموع: <code>${(current_balance + referral_earned):.2f}</code>

━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>الإنفاق حسب الخدمة</b>"""
    
    if spending_by_service:
        for service, count, total in spending_by_service:
            total_amount = float(total) if total is not None else 0.0
            report += f"\n• <b>{service}</b>: {count} طلب → <code>${total_amount:.2f}</code>"
    else:
        report += "\n• لا توجد مشتريات مكتملة"
    
    if transactions:
        report += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━\n📝 <b>آخر المعاملات</b>"
        for trans_type, amount, created_at, desc in transactions[:5]:
            date = created_at[:10] if created_at else "غير معروف"
            sign = "+" if amount > 0 else ""
            report += f"\n• <b>{sign}${amount:.2f}</b> - {date}\n  {desc or trans_type}"
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع للتقارير", callback_data=f"detailed_reports_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(report, reply_markup=reply_markup, parse_mode='HTML')

async def handle_orders_report_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تقرير الطلبات المفصل - شامل للبروكسي والأرقام"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    
    # الحصول على تفاصيل طلبات البروكسي
    proxy_orders = db.execute_query("""
        SELECT id, proxy_type, country, state, status, payment_amount, created_at
        FROM orders 
        WHERE user_id = ? 
        ORDER BY created_at DESC LIMIT 10
    """, (user_id,))
    
    # الحصول على تفاصيل طلبات NonVoIP
    nonvoip_orders = []
    if nonvoip_db:
        nonvoip_orders = nonvoip_db.get_user_orders(int(user_id), limit=10)
    
    report = f"📦 <b>تقرير الطلبات الشامل</b>\n\n🆔 <b>المعرف:</b> <code>{user_id}</code>"
    
    # ═══════════════════════════════════════════════════════════════
    # قسم طلبات البروكسي
    # ═══════════════════════════════════════════════════════════════
    report += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━\n🌐 <b>طلبات البروكسي</b>"
    
    if not proxy_orders:
        report += "\n• لا توجد طلبات بروكسي"
    else:
        completed = sum(1 for o in proxy_orders if o[4] == 'completed')
        pending = sum(1 for o in proxy_orders if o[4] == 'pending') 
        failed = sum(1 for o in proxy_orders if o[4] == 'failed')
        proxy_total_spent = sum(float(o[5] or 0) for o in proxy_orders if o[4] == 'completed')
        
        report += f"\n📊 المكتمل: {completed} | المعلق: {pending} | الفاشل: {failed}"
        report += f"\n💵 إجمالي الإنفاق: <code>${proxy_total_spent:.2f}</code>"
        
        report += f"\n\n📋 <b>آخر 5 طلبات:</b>"
        for i, (order_id, proxy_type, country, state, status, amount, created_at) in enumerate(proxy_orders[:5], 1):
            status_emoji = {"completed": "✅", "pending": "⏳", "failed": "❌"}.get(status, "❓")
            location = f"{country}-{state}" if state else country
            date = created_at[:10] if created_at else "غير معروف"
            order_amount = float(amount) if amount is not None else 0.0
            
            report += f"\n{i}. {status_emoji} {proxy_type} | {location} | ${order_amount:.2f} | {date}"
    
    # ═══════════════════════════════════════════════════════════════
    # قسم طلبات الأرقام (NonVoIP)
    # ═══════════════════════════════════════════════════════════════
    report += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━\n📱 <b>طلبات الأرقام (NonVoIP)</b>"
    
    if not nonvoip_orders:
        report += "\n• لا توجد طلبات أرقام"
    else:
        # إحصائيات حسب النوع
        type_names = {'short_term': '15 دقيقة', '3days': '3 أيام', 'long_term': '30 يوم'}
        short_count = sum(1 for o in nonvoip_orders if o.get('type') == 'short_term')
        three_days_count = sum(1 for o in nonvoip_orders if o.get('type') == '3days')
        long_count = sum(1 for o in nonvoip_orders if o.get('type') == 'long_term')
        nonvoip_total_spent = sum(float(o.get('sale_price') or 0) for o in nonvoip_orders if not o.get('refunded'))
        sms_received = sum(1 for o in nonvoip_orders if o.get('sms_received'))
        
        report += f"\n📊 15 دقيقة: {short_count} | 3 أيام: {three_days_count} | 30 يوم: {long_count}"
        report += f"\n💵 إجمالي الإنفاق: <code>${nonvoip_total_spent:.2f}</code>"
        report += f"\n📩 رسائل مستلمة: {sms_received}"
        
        report += f"\n\n📋 <b>آخر 5 طلبات:</b>"
        for i, order in enumerate(nonvoip_orders[:5], 1):
            order_type = type_names.get(order.get('type', ''), order.get('type', 'غير معروف'))
            number = order.get('number', 'N/A')
            service = order.get('service', 'N/A')
            price = float(order.get('sale_price') or 0)
            status = order.get('status', 'غير معروف')
            sms = "✅" if order.get('sms_received') else "⏳"
            refunded = " (مسترد)" if order.get('refunded') else ""
            created = str(order.get('created_at', ''))[:10]
            
            status_emoji = {"active": "🟢", "completed": "✅", "expired": "⏰", "refunded": "↩️", "cancelled": "❌"}.get(status, "❓")
            
            report += f"\n{i}. {status_emoji} {service} | {number}"
            report += f"\n   ⏱️ {order_type} | 💵 ${price:.2f} | 📩 {sms}{refunded}"
    
    # ═══════════════════════════════════════════════════════════════
    # ملخص إجمالي
    # ═══════════════════════════════════════════════════════════════
    total_proxy = len(proxy_orders) if proxy_orders else 0
    total_nonvoip = len(nonvoip_orders) if nonvoip_orders else 0
    report += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━\n📈 <b>الملخص الإجمالي</b>"
    report += f"\n• إجمالي الطلبات: {total_proxy + total_nonvoip}"
    report += f"\n• بروكسي: {total_proxy} | أرقام: {total_nonvoip}"
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع للتقارير", callback_data=f"detailed_reports_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(report, reply_markup=reply_markup, parse_mode='HTML')

async def handle_referrals_report_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تقرير الإحالات المفصل"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    # الحصول على تفاصيل الإحالات
    referrals = db.execute_query("""
        SELECT u.user_id, u.first_name, u.last_name, u.username, r.created_at,
               (SELECT COUNT(*) FROM orders WHERE user_id = u.user_id AND status = 'completed') as orders_count
        FROM referrals r
        JOIN users u ON r.referred_id = u.user_id
        WHERE r.referrer_id = ?
        ORDER BY r.created_at DESC
    """, (user_id,))
    
    referral_earnings = float(user_data[5]) if user_data[5] else 0.0
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    
    report = f"👥 <b>تقرير الإحالات المفصل</b>\n\n📋 <b>المستخدم:</b> {first_name} {last_name}\n🆔 <b>المعرف:</b> <code>{user_id}</code>"
    report += f"\n\n💰 <b>إجمالي الأرباح:</b> <code>${referral_earnings:.2f}</code>"
    report += f"\n👥 <b>عدد المُحالين:</b> {len(referrals)}"
    
    if not referrals:
        report += "\n\n❌ لا يوجد مستخدمون محالون"
    else:
        report += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━\n📊 <b>تفاصيل المُحالين:</b>"
        
        # إحصائيات الإحالات النشطة
        active_referrals = [r for r in referrals if r[5] > 0]  # لديهم طلبات
        report += f"\n• النشطون: {len(active_referrals)} من أصل {len(referrals)}"
        
        for i, (ref_id, fname, lname, username, created_at, orders_count) in enumerate(referrals[:8], 1):
            name = f"{fname} {lname}".strip()
            username_text = f"@{username}" if username else "لا يوجد"
            date = created_at[:10] if created_at else "غير معروف"
            activity = "🟢 نشط" if orders_count > 0 else "🟡 غير نشط"
            
            report += f"\n\n<b>{i}.</b> {name} ({username_text})"
            report += f"\n   • المعرف: <code>{ref_id}</code>"
            report += f"\n   • الطلبات: {orders_count}"
            report += f"\n   • تاريخ الإحالة: {date}"
            report += f"\n   • الحالة: {activity}"
        
        if len(referrals) > 8:
            report += f"\n\n📋 *عرض أول 8 من أصل {len(referrals)} محال*"
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع للتقارير", callback_data=f"detailed_reports_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(report, reply_markup=reply_markup, parse_mode='HTML')

async def handle_advanced_stats_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """الإحصائيات المتقدمة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    # إحصائيات متقدمة
    join_date = user_data[7][:10] if user_data[7] else "غير معروف"
    days_since_join = (datetime.now() - datetime.fromisoformat(user_data[7])).days if user_data[7] else 0
    
    # إحصائيات الطلبات بالتفصيل
    monthly_stats = db.execute_query("""
        SELECT 
            strftime('%Y-%m', created_at) as month,
            COUNT(*) as orders,
            SUM(payment_amount) as spent
        FROM orders 
        WHERE user_id = ? AND status = 'completed'
        GROUP BY strftime('%Y-%m', created_at)
        ORDER BY month DESC LIMIT 6
    """, (user_id,))
    
    # معدل الإنفاق
    total_orders = db.execute_query("SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = 'completed'", (user_id,))[0][0]
    total_spent = db.execute_query("SELECT COALESCE(SUM(payment_amount), 0) FROM orders WHERE user_id = ? AND status = 'completed'", (user_id,))[0][0]
    avg_order_value = float(total_spent) / total_orders if total_orders > 0 else 0
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    
    report = f"""📈 <b>الإحصائيات المتقدمة</b>

👤 <b>المستخدم:</b> {first_name} {last_name}
📅 <b>تاريخ الانضمام:</b> {join_date}
⏳ <b>مدة العضوية:</b> {days_since_join} يوم

━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>التحليل المالي</b>
• إجمالي الطلبات: {total_orders}
• إجمالي الإنفاق: <code>${float(total_spent):.2f}</code>
• متوسط قيمة الطلب: <code>${avg_order_value:.2f}</code>
• معدل الإنفاق اليومي: <code>${(float(total_spent) / max(days_since_join, 1)):.2f}</code>"""
    
    if monthly_stats:
        report += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━\n📅 <b>الإحصائيات الشهرية</b>"
        for month, orders, spent in monthly_stats:
            spent_amount = float(spent) if spent is not None else 0.0
            report += f"\n• <b>{month}</b>: {orders} طلب → <code>${spent_amount:.2f}</code>"
    
    # إحصائيات الإحالات
    referral_count = db.execute_query("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))[0][0]
    referral_conversion = (referral_count / max(days_since_join, 1)) * 30 if days_since_join > 0 else 0
    
    report += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━\n👥 <b>تحليل الإحالات</b>"
    report += f"\n• عدد المُحالين: {referral_count}"
    report += f"\n• معدل الإحالة الشهري: {referral_conversion:.1f}"
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع للتقارير", callback_data=f"detailed_reports_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(report, reply_markup=reply_markup, parse_mode='HTML')

async def handle_timeline_report_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """التقرير الزمني"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    # الحصول على التسلسل الزمني للأنشطة
    timeline_events = []
    
    # تاريخ الانضمام
    join_date = user_data[7]
    if join_date:
        timeline_events.append((join_date, "🎯 انضمام للبوت", "تسجيل حساب جديد"))
    
    # الطلبات الهامة
    important_orders = db.execute_query("""
        SELECT created_at, proxy_type, status, payment_amount
        FROM orders 
        WHERE user_id = ? 
        ORDER BY created_at DESC LIMIT 20
    """, (user_id,))
    
    for order_date, proxy_type, status, amount in important_orders:
        order_amount = float(amount) if amount is not None else 0.0
        if status == 'completed':
            timeline_events.append((order_date, f"✅ طلب مكتمل", f"{proxy_type} - ${order_amount:.2f}"))
        elif status == 'failed':
            timeline_events.append((order_date, f"❌ طلب فاشل", f"{proxy_type} - ${order_amount:.2f}"))
    
    # أول إحالة
    first_referral = db.execute_query("""
        SELECT r.created_at, u.first_name, u.last_name
        FROM referrals r
        JOIN users u ON r.referred_id = u.user_id
        WHERE r.referrer_id = ?
        ORDER BY r.created_at ASC LIMIT 1
    """, (user_id,))
    
    if first_referral:
        ref_date, fname, lname = first_referral[0]
        timeline_events.append((ref_date, "👥 أول إحالة", f"أحال {fname} {lname}"))
    
    # ترتيب الأحداث حسب التاريخ
    timeline_events.sort(key=lambda x: x[0] if x[0] else "", reverse=True)
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    
    report = f"""📅 <b>التقرير الزمني</b>

👤 <b>المستخدم:</b> {first_name} {last_name}
🆔 <b>المعرف:</b> <code>{user_id}</code>

━━━━━━━━━━━━━━━━━━━━━━━
⏳ <b>التسلسل الزمني للأنشطة</b>"""
    
    if not timeline_events:
        report += "\n\n❌ لا توجد أنشطة مسجلة"
    else:
        for i, (event_date, event_type, description) in enumerate(timeline_events[:15], 1):
            date = event_date[:10] if event_date else "غير معروف"
            report += f"\n\n<b>{i}.</b> {event_type}"
            report += f"\n   📅 {date}"
            report += f"\n   📝 {description}"
        
        if len(timeline_events) > 15:
            report += f"\n\n📋 *عرض أول 15 حدث من أصل {len(timeline_events)}*"
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع للتقارير", callback_data=f"detailed_reports_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(report, reply_markup=reply_markup, parse_mode='HTML')

async def handle_transaction_history_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """سجل المعاملات المالية"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    
    # الحصول على سجل المعاملات
    transactions = db.execute_query("""
        SELECT transaction_type, amount, created_at, description, order_id
        FROM credits_transactions 
        WHERE user_id = ? 
        ORDER BY created_at DESC LIMIT 15
    """, (user_id,))
    
    report = f"💳 سجل المعاملات المالية\n\n🆔 المعرف: {user_id}"
    
    if not transactions:
        report += "\n\n❌ لا توجد معاملات مسجلة"
    else:
        # حساب الرصيد
        total_credit = sum(float(t[1]) for t in transactions if t[1] is not None and float(t[1]) > 0)
        total_debit = sum(abs(float(t[1])) for t in transactions if t[1] is not None and float(t[1]) < 0)
        
        report += f"\n\n📊 ملخص المعاملات:"
        report += f"\n• إجمالي الإيداعات: +${total_credit:.2f}"
        report += f"\n• إجمالي المسحوبات: -${total_debit:.2f}"
        report += f"\n• صافي المعاملات: ${(total_credit - total_debit):.2f}"
        
        report += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━\n📝 تفاصيل المعاملات:"
        
        for i, (trans_type, amount, created_at, desc, order_id) in enumerate(transactions, 1):
            date = created_at[:10] if created_at else "غير معروف"
            amount_float = float(amount) if amount is not None else 0.0
            sign = "+" if amount_float > 0 else "-"
            color = "🟢" if amount_float > 0 else "🔴"
            
            report += f"\n\n{i}. {color} {sign}${abs(amount_float):.2f}"
            report += f"\n   📅 {date}"
            report += f"\n   📝 {desc or trans_type}"
            if order_id:
                report += f"\n   🔗 الطلب: {order_id[:8]}..."
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع لإدارة النقاط", callback_data=f"manage_points_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(report, reply_markup=reply_markup)

async def handle_custom_balance_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تعديل الرصيد لقيمة مخصصة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    current_balance = float(user_data[6]) if user_data[6] else 0.0
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    
    message = f"""💰 تعديل الرصيد المخصص

📋 المستخدم: {first_name} {last_name}
💳 الرصيد الحالي: ${current_balance:.2f}

⚠️ تحذير هام:
هذه العملية ستغير الرصيد إلى القيمة المحددة تماماً
(وليس إضافة أو خصم)

📝 أرسل الرصيد الجديد بالدولار:
مثال: 50.00 أو 25.5 أو 100"""
    
    # حفظ بيانات التعديل المخصص
    context.user_data['custom_balance_user_id'] = user_id
    context.user_data['awaiting_custom_balance'] = True
    
    keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data=f"manage_points_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

async def handle_custom_balance_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة إدخال الرصيد المخصص"""
    if not context.user_data.get('awaiting_custom_balance'):
        return
    
    user_id = context.user_data.get('custom_balance_user_id')
    if not user_id:
        await update.message.reply_text("❌ خطأ: معرف المستخدم غير موجود")
        context.user_data.pop('awaiting_custom_balance', None)
        return
    
    balance_text = update.message.text.strip()
    
    # التحقق من أن القيمة رقم عشري صحيح
    try:
        new_balance = float(balance_text)
        if new_balance < 0:
            await update.message.reply_text(
                "❌ الرصيد لا يمكن أن يكون سالباً!\n\n📝 أرسل رصيد صحيح (مثال: 50.00 أو 25.5)"
            )
            return
    except ValueError:
        await update.message.reply_text(
            "❌ قيمة غير صحيحة!\n\n📝 أرسل رقم عشري صحيح (مثال: 50.00 أو 25.5 أو 100)"
        )
        return
    
    # الحصول على بيانات المستخدم
    user_result = db.execute_query("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not user_result:
        await update.message.reply_text("❌ المستخدم غير موجود")
        context.user_data.pop('awaiting_custom_balance', None)
        return
    
    user_data = user_result[0]
    old_balance = float(user_data[6]) if user_data[6] else 0.0
    
    # تعديل الرصيد
    db.execute_query("UPDATE users SET credits_balance = ? WHERE user_id = ?", (new_balance, user_id))
    
    # تسجيل المعاملة
    difference = new_balance - old_balance
    transaction_type = "manual_credit" if difference >= 0 else "manual_debit"
    description = f"تعديل يدوي للرصيد بواسطة الأدمن (من ${old_balance:.2f} إلى ${new_balance:.2f})"
    
    db.execute_query("""
        INSERT INTO credits_transactions (user_id, transaction_type, amount, description, created_at)
        VALUES (?, ?, ?, ?, datetime('now'))
    """, (user_id, transaction_type, difference, description))
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    
    success_message = f"""✅ تم تعديل الرصيد بنجاح!

📋 المستخدم: {first_name} {last_name}
🆔 المعرف: {user_id}

💰 الرصيد السابق: ${old_balance:.2f}
💰 الرصيد الجديد: ${new_balance:.2f}
📊 الفرق: {"+" if difference >= 0 else ""}{difference:.2f}"""
    
    await update.message.reply_text(success_message)
    
    # إعادة تفعيل كيبورد الأدمن
    await restore_admin_keyboard(context, update.effective_chat.id, "✅ تم التعديل - لوحة الأدمن جاهزة")
    
    # تنظيف البيانات
    context.user_data.pop('awaiting_custom_balance', None)
    context.user_data.pop('custom_balance_user_id', None)

async def handle_reset_stats_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """إعادة تعيين الإحصائيات"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    
    message = f"""📊 <b>إعادة تعيين الإحصائيات</b>

📋 <b>المستخدم:</b> {first_name} {last_name}
🆔 <b>المعرف:</b> <code>{user_id}</code>

⚠️ <b>تحذير خطر:</b>
هذه العملية ستحذف نهائياً:
• جميع الطلبات والتاريخ
• سجل المعاملات المالية  
• إحصائيات الاستخدام
• لن يتم حذف الرصيد أو الإحالات

❌ <b>هذه العملية لا يمكن التراجع عنها!</b>

هل أنت متأكد من المتابعة؟"""
    
    keyboard = [
        [
            InlineKeyboardButton("✅ نعم، إعادة تعيين الإحصائيات", callback_data=f"confirm_reset_stats_{user_id}"),
            InlineKeyboardButton("❌ إلغاء", callback_data=f"manage_user_{user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

async def handle_delete_user_data_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """حذف بيانات المستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    
    message = f"""🗑️ <b>حذف بيانات المستخدم</b>

📋 <b>المستخدم:</b> {first_name} {last_name}
🆔 <b>المعرف:</b> <code>{user_id}</code>

💀 <b>تحذير خطر شديد:</b>
هذه العملية ستحذف نهائياً:
• ملف المستخدم بالكامل
• جميع الطلبات والتاريخ  
• الرصيد والنقاط
• الإحالات وأرباحها
• سجل المعاملات المالية
• جميع البيانات المرتبطة

❌ <b>هذه العملية لا يمكن التراجع عنها إطلاقاً!</b>
⚠️ <b>استخدم هذا فقط في الحالات القصوى!</b>

هل أنت متأكد 100% من الحذف النهائي؟"""
    
    keyboard = [
        [InlineKeyboardButton("💀 نعم، حذف نهائي للمستخدم", callback_data=f"confirm_delete_user_{user_id}")],
        [InlineKeyboardButton("❌ إلغاء (الخيار الآمن)", callback_data=f"manage_user_{user_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

async def handle_confirm_delete_user_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تأكيد حذف بيانات المستخدم نهائياً"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    try:
        # الحصول على معلومات المستخدم قبل الحذف
        first_name = user_data[2] or ""
        last_name = user_data[3] or ""
        username = user_data[1] or "غير محدد"
        
        # حذف جميع بيانات المستخدم من جميع الجداول
        db.execute_query("DELETE FROM orders WHERE user_id = ?", (user_id,))
        db.execute_query("DELETE FROM referrals WHERE referrer_id = ? OR referred_id = ?", (user_id, user_id))
        db.execute_query("DELETE FROM credits_transactions WHERE user_id = ?", (user_id,))
        db.execute_query("DELETE FROM user_bans WHERE user_id = ?", (user_id,))
        db.execute_query("DELETE FROM users WHERE user_id = ?", (user_id,))
        
        # رسالة تأكيد
        success_message = f"""✅ تم حذف المستخدم نهائياً!

📋 المستخدم المحذوف:
• الاسم: {first_name} {last_name}
• المعرف: {user_id}
• اسم المستخدم: @{username}

🗑️ تم حذف:
• ملف المستخدم بالكامل
• جميع الطلبات والتاريخ
• الرصيد والنقاط
• الإحالات وأرباحها
• سجل المعاملات
• جميع البيانات المرتبطة"""
        
        await query.edit_message_text(success_message)
        
        # تنظيف البيانات المؤقتة
        context.user_data.pop('selected_user_data', None)
        
        # إعادة تفعيل كيبورد الأدمن
        await restore_admin_keyboard(context, query.message.chat_id, "✅ تم حذف المستخدم - لوحة الأدمن جاهزة")
        
    except Exception as e:
        logger.error(f"خطأ في حذف بيانات المستخدم {user_id}: {e}")
        await query.edit_message_text(f"❌ حدث خطأ أثناء حذف البيانات:\n{str(e)}")

async def handle_clear_referrals_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """مسح جميع الإحالات"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[-1]
    user_data = context.user_data.get('selected_user_data')
    
    if not user_data:
        await query.edit_message_text("❌ خطأ: بيانات المستخدم غير متوفرة")
        return
    
    # الحصول على عدد الإحالات
    referral_count = db.execute_query("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))[0][0]
    referral_earned = float(user_data[5]) if user_data[5] else 0.0
    
    # تهريب الأحرف الخاصة في الأسماء
    first_name = escape_markdown(user_data[2] or "")
    last_name = escape_markdown(user_data[3] or "")
    
    message = f"""🔄 <b>مسح جميع الإحالات</b>

📋 <b>المستخدم:</b> {first_name} {last_name}
🆔 <b>المعرف:</b> <code>{user_id}</code>

📊 <b>البيانات الحالية:</b>
• عدد المُحالين: <code>{referral_count}</code> شخص
• رصيد الإحالات: <code>${referral_earned:.2f}</code>

⚠️ <b>تحذير:</b>
هذه العملية ستحذف:
• جميع سجلات الإحالات ({referral_count} إحالة)
• سيتم تصفير رصيد الإحالات
• لن يتأثر الرصيد الأساسي للمستخدم

❌ <b>لا يمكن التراجع عن هذه العملية!</b>

هل تريد المتابعة؟"""
    
    keyboard = [
        [
            InlineKeyboardButton("🗑️ نعم، مسح جميع الإحالات", callback_data=f"confirm_clear_referrals_{user_id}"),
            InlineKeyboardButton("❌ إلغاء", callback_data=f"manage_referrals_{user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

# ============================================
# ============================================
# نظام إدارة الرسائل للآدمن في بوت Telegram
# ============================================

import sqlite3
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# ============================================
# دوال مساعدة لإدارة قاعدة البيانات
# ============================================

def set_selected_message(db_file: str, admin_id: int, message_id: int, chat_id: int, target_user_id: int = None):
    """تحديد رسالة للآدمن (إلغاء التحديد السابق إذا وجد)"""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # حذف أي تحديد سابق لهذا الآدمن
    cursor.execute("DELETE FROM admin_selected_messages WHERE admin_id = ?", (admin_id,))
    
    # إضافة عمود target_user_id إذا لم يكن موجوداً
    try:
        cursor.execute("ALTER TABLE admin_selected_messages ADD COLUMN target_user_id INTEGER")
    except:
        pass
    
    # إضافة التحديد الجديد
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
    
    # التحقق من وجود عمود target_user_id
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
        # العمود غير موجود، استخدام الطريقة القديمة
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

# ============================================
# دوال مساعدة للتحقق من الصلاحيات
# ============================================

def is_admin(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """التحقق من أن المستخدم آدمن"""
    from bot import ACTIVE_ADMINS
    return context.user_data.get('is_admin', False) or user_id in ACTIVE_ADMINS

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
    # البحث عن @username أو user ID
    parts = text.strip().split()
    if len(parts) > 1:
        target = parts[1]
        if target.startswith('@'):
            username = target[1:]
            # تحويل username إلى user_id
            user_id = get_user_id_by_username(db_file, username)
            if user_id:
                return ('user_id', user_id)
            else:
                return ('username_not_found', username)
        elif target.isdigit():
            return ('user_id', int(target))
    return (None, None)

# ============================================
# معالجات الأوامر (Command Handlers)
# ============================================

async def handle_msg_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /msg_options - يحدد رسالة للإدارة"""
    user_id = update.effective_user.id
    
    # التحقق من صلاحيات الآدمن
    if not is_admin(user_id, context):
        await update.message.reply_text("⛔ هذا الأمر متاح فقط للآدمن.")
        return
    
    # التحقق من أن الأمر مستخدم كرد على رسالة
    if not update.message.reply_to_message:
        # عرض التعليمات الكاملة
        help_text = escape_markdown_v2("""نظام إدارة رسائل البوت للآدمن

/msg_options
|
|___/msg_delete
|
|___/msg_edit
|
|___/msg_pin
|
|___/msg_unpin

القواعد الأساسية:
• لا يمكن استخدام أي أمر قبل استخدام /msg_options
• استخدام /msg_options مرتين متتاليتين، الثانية تلغي الأولى
• في حال استخدام /msg_options ولم تستخدم بعدها أمر يبدأ بـ /msg، يُلغى مفعوله

طريقة الاستخدام:
1️⃣ قم بالرد على الرسالة المراد إدارتها بـ /msg_options
2️⃣ استخدم أحد الأوامر الفرعية (/msg_delete, /msg_pin, إلخ)

تحديد مستخدم محدد:
/msg_options @username
أو
/msg_options 123456789

مثال:
- رد على الرسالة بـ: /msg_options @ahmad
- ثم استخدم: /msg_delete
- النتيجة: سيتم الحذف فقط لدى المستخدم ahmad

⚠️ ملاحظة: يجب الرد على الرسالة عند استخدام /msg_options""")
        
        await update.message.reply_text(help_text, parse_mode='MarkdownV2')
        return
    
    # الحصول على معلومات الرسالة المحددة
    replied_msg = update.message.reply_to_message
    message_id = replied_msg.message_id
    chat_id = replied_msg.chat_id
    
    # التحقق من تحديد مستخدم معين
    from bot import DATABASE_FILE
    target_type, target_value = parse_target_user(update.message.text, DATABASE_FILE)
    
    # التحقق من أن المستخدم المستهدف موجود
    if target_type == 'username_not_found':
        await update.message.reply_text(
            f"❌ المستخدم @{target_value} غير موجود في قاعدة البيانات.\n"
            "تأكد من أن المستخدم قد تفاعل مع البوت من قبل."
        )
        return
    
    target_user_id = target_value if target_type == 'user_id' else None
    
    # حفظ الرسالة المحددة في قاعدة البيانات
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
    
    # التحقق من صلاحيات الآدمن
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
    from bot import DATABASE_FILE
    message_id, chat_id, target_user_id = get_selected_message(DATABASE_FILE, user_id)
    
    if not message_id:
        if not update.message.reply_to_message:
            await update.message.reply_text(
                "❌ يجب الرد على رسالة لحذفها مباشرة، أو استخدام /msg_options أولاً للحذف الجماعي."
            )
        return
    
    try:
        # الحصول على نسخ الرسالة
        copies = get_message_copies(DATABASE_FILE, message_id, chat_id)
        
        deleted_count = 0
        failed_count = 0
        
        for copy_user_id, copy_chat_id, copy_message_id in copies:
            # تخطي إذا كان المستخدم المستهدف محدد وليس هو
            if target_user_id and copy_user_id != target_user_id:
                continue
            
            # حذف الرسالة لدى المستخدم (عدا الآدمن)
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
        
        # إشعار الآدمن بالنتيجة
        target_info = ""
        if target_user_id:
            target_info = f" للمستخدم المحدد (ID: {target_user_id})"
        
        notification = f"✅ تم حذف الرسالة{target_info}!\n"
        notification += f"📊 تم الحذف لدى {deleted_count} مستخدم"
        
        if failed_count > 0:
            notification += f"\n⚠️ فشل الحذف لدى {failed_count} مستخدم"
        
        await update.message.reply_text(notification)
        
        # مسح الرسالة المحددة بعد التنفيذ
        clear_selected_message(DATABASE_FILE, user_id)
        
    except Exception as e:
        logger.error(f"Error in handle_msg_delete: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء حذف الرسالة.")

async def handle_msg_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /msg_pin - تثبيت الرسالة لدى المستخدمين المحددين"""
    user_id = update.effective_user.id
    
    # التحقق من صلاحيات الآدمن
    if not is_admin(user_id, context):
        await update.message.reply_text("⛔ هذا الأمر متاح فقط للآدمن.")
        return
    
    # الحصول على الرسالة المحددة مسبقاً بـ /msg_options
    from bot import DATABASE_FILE
    message_id, chat_id, target_user_id = get_selected_message(DATABASE_FILE, user_id)
    
    if not message_id:
        await update.message.reply_text(
            "❌ لا توجد رسالة محددة!\n"
            "يجب استخدام /msg_options أولاً بالرد على الرسالة المراد تثبيتها."
        )
        return
    
    try:
        # تثبيت الرسالة الأصلية
        await context.bot.pin_chat_message(
            chat_id=chat_id,
            message_id=message_id,
            disable_notification=True
        )
        
        # الحصول على نسخ الرسالة وتثبيتها
        copies = get_message_copies(DATABASE_FILE, message_id, chat_id)
        
        pinned_count = 0
        failed_count = 0
        
        for copy_user_id, copy_chat_id, copy_message_id in copies:
            # تخطي إذا كان المستخدم المستهدف محدد وليس هو
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
        
        # إشعار الآدمن بالنتيجة
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
        
        # مسح الرسالة المحددة بعد التنفيذ
        clear_selected_message(DATABASE_FILE, user_id)
        
    except Exception as e:
        logger.error(f"Error in handle_msg_pin: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء تثبيت الرسالة.")

async def handle_msg_unpin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /msg_unpin - فك تثبيت الرسالة"""
    user_id = update.effective_user.id
    
    # التحقق من صلاحيات الآدمن
    if not is_admin(user_id, context):
        await update.message.reply_text("⛔ هذا الأمر متاح فقط للآدمن.")
        return
    
    # الحصول على الرسالة المحددة مسبقاً بـ /msg_options
    from bot import DATABASE_FILE
    message_id, chat_id, target_user_id = get_selected_message(DATABASE_FILE, user_id)
    
    if not message_id:
        await update.message.reply_text(
            "❌ لا توجد رسالة محددة!\n"
            "يجب استخدام /msg_options أولاً بالرد على الرسالة المراد فك تثبيتها."
        )
        return
    
    try:
        # فك تثبيت الرسالة الأصلية
        await context.bot.unpin_chat_message(
            chat_id=chat_id,
            message_id=message_id
        )
        
        # الحصول على نسخ الرسالة وفك تثبيتها
        copies = get_message_copies(DATABASE_FILE, message_id, chat_id)
        
        unpinned_count = 0
        failed_count = 0
        
        for copy_user_id, copy_chat_id, copy_message_id in copies:
            # تخطي إذا كان المستخدم المستهدف محدد وليس هو
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
        
        # إشعار الآدمن بالنتيجة
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
        
        # مسح الرسالة المحددة بعد التنفيذ
        clear_selected_message(DATABASE_FILE, user_id)
        
    except Exception as e:
        logger.error(f"Error in handle_msg_unpin: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء فك تثبيت الرسالة.")

async def handle_msg_clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /msg_clean - حذف جميع رسائل البوت لدى جميع المستخدمين (أو مستخدم محدد) بعد تأكيد"""
    user_id = update.effective_user.id
    
    # التحقق من صلاحيات الآدمن
    if not is_admin(user_id, context):
        await update.message.reply_text("⛔ هذا الأمر متاح فقط للآدمن.")
        return
    
    # التحقق من تحديد مستخدم معين
    target_type, target_value = parse_target_user(update.message.text, DATABASE_FILE)
    
    # التحقق من أن المستخدم المستهدف موجود
    if target_type == 'username_not_found':
        await update.message.reply_text(
            f"❌ المستخدم @{target_value} غير موجود في قاعدة البيانات.\n"
            "تأكد من أن المستخدم قد تفاعل مع البوت من قبل."
        )
        return
    
    target_user_id = target_value if target_type == 'user_id' else None
    
    # حفظ معرف المستخدم المستهدف في context للاستخدام عند التأكيد
    context.user_data['msg_clean_target_user_id'] = target_user_id
    
    # طلب التأكيد
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    target_info = ""
    if target_user_id:
        target_info = f" للمستخدم المحدد (ID: {target_user_id})"
    else:
        # حساب عدد المستخدمين
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
    
    # التحقق من صلاحيات الآدمن
    if not is_admin(user_id, context):
        await query.edit_message_text("⛔ هذا الأمر متاح فقط للآدمن.")
        return
    
    if query.data == "confirm_msg_clean":
        await query.edit_message_text("🗑️ جاري حذف جميع الرسائل...")
        
        # الحصول على المستخدم المستهدف (إن وجد)
        target_user_id = context.user_data.get('msg_clean_target_user_id')
        
        try:
            import sqlite3
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            
            # الحصول على جميع نسخ الرسائل
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
                # تخطي الأدمن
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
            
            # تنظيف قاعدة البيانات
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
            
            # إشعار الآدمن بالنتيجة
            target_info = ""
            if target_user_id:
                target_info = f" للمستخدم المحدد (ID: {target_user_id})"
            
            notification = f"✅ تم حذف جميع الرسائل{target_info}!\n\n"
            notification += f"📊 الإحصائيات:\n"
            notification += f"✅ تم الحذف: {deleted_count} رسالة\n"
            
            if failed_count > 0:
                notification += f"⚠️ فشل الحذف: {failed_count} رسالة"
            
            await query.edit_message_text(notification)
            
            # تنظيف البيانات المؤقتة
            context.user_data.pop('msg_clean_target_user_id', None)
            
        except Exception as e:
            logger.error(f"Error in handle_msg_clean_confirmation: {e}")
            await query.edit_message_text("❌ حدث خطأ أثناء حذف الرسائل.")
            
    elif query.data == "cancel_msg_clean":
        await query.edit_message_text("❌ تم إلغاء عملية الحذف.")
        
        # تنظيف البيانات المؤقتة
        context.user_data.pop('msg_clean_target_user_id', None)

async def handle_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج تعديلات الرسائل - يطبق التعديل على المستخدمين المحددين"""
    # التحقق من أن المحرر هو آدمن
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
        from bot import DATABASE_FILE
        
        # الحصول على الرسالة المحددة للتحقق من المستخدم المستهدف
        _, _, target_user_id = get_selected_message(DATABASE_FILE, user_id)
        
        # الحصول على نسخ الرسالة
        copies = get_message_copies(DATABASE_FILE, message_id, chat_id)
        
        edited_count = 0
        failed_count = 0
        
        for copy_user_id, copy_chat_id, copy_message_id in copies:
            # تخطي إذا كان المستخدم المستهدف محدد وليس هو
            if target_user_id and copy_user_id != target_user_id:
                continue
            try:
                # تطبيق التعديل على نسخة المستخدم
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
    
    # التحقق من أن المستخدم آدمن
    if not is_admin(user_id, context):
        return
    
    # الحصول على النص
    text = update.message.text if update.message else ""
    
    # إذا كان الأمر يبدأ بـ /msg فلا تفعل شيء
    if text.startswith('/msg'):
        return
    
    # إلغاء أي تحديد سابق
    from bot import DATABASE_FILE
    message_id, _, _ = get_selected_message(DATABASE_FILE, user_id)
    
    if message_id:
        clear_selected_message(DATABASE_FILE, user_id)
        logger.info(f"تم إلغاء تحديد الرسالة للآدمن {user_id} تلقائياً")
def main():
    """الدالة الرئيسية لتشغيل البوت"""
    lock_file = None
    try:
        print("=" * 50)
        print("🤖 تشغيل بوت البروكسي")
        print("=" * 50)
        
        # فحص وإنشاء قفل البوت
        lock_file = check_bot_lock()
        if lock_file is None and FCNTL_AVAILABLE:
            # في أنظمة Unix، إذا فشل القفل فلا نكمل
            return
            
        # تسجيل دالة تنظيف عند إغلاق البرنامج
        def cleanup_lock():
            cleanup_bot_lock(lock_file)
        
        atexit.register(cleanup_lock)
        
        # إعداد البوت
        application = setup_bot()
        if application is None:
            print("❌ فشل في إعداد البوت")
            return
        
        # تشغيل البوت
        print("🚀 بدء تشغيل البوت...")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except KeyboardInterrupt:
        print("\n⚠️ تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        print(f"❌ خطأ فادح في البوت: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # تنظيف ملف القفل
        cleanup_bot_lock(lock_file)
        print("✅ تم إيقاف البوت بنجاح")

if __name__ == '__main__':
    main()


# ==================== نظام إشعارات رصيد Non-Voip التدريجي ====================

async def check_nonvoip_balance_and_notify(context: ContextTypes.DEFAULT_TYPE):
    """فحص رصيد Non-Voip وإرسال إشعار تدريجي للأدمن - ينبه فقط عند < 20, < 10, < 5"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # التحقق من تفعيل التنبيهات
        cursor.execute("SELECT value FROM settings WHERE key = 'nonvoip_balance_alerts_enabled'")
        result = cursor.fetchone()
        if result and result[0] == '0':
            logger.info("⏸ تنبيهات رصيد Non-Voip معطلة")
            conn.close()
            return
        
        # جلب الرصيد
        api = NonVoipAPI()
        balance_result = api.get_balance()
        
        if balance_result.get('status') != 'success':
            conn.close()
            return
        
        balance = float(balance_result.get('balance', 0))
        current_level = None
        
        if balance < 5:
            current_level = 5
        elif balance < 10:
            current_level = 10
        elif balance < 20:
            current_level = 20
        
        if current_level is None:
            cursor.execute("INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('last_balance_alert_level', '0', CURRENT_TIMESTAMP)")
            conn.commit()
            conn.close()
            return
        
        # جلب آخر مستوى تم التنبيه عنه
        cursor.execute("SELECT value FROM settings WHERE key = 'last_balance_alert_level'")
        last_alert = cursor.fetchone()
        last_level = int(last_alert[0]) if last_alert else 0
        
        if current_level <= last_level and last_level != 0:
            conn.close()
            return
        
        # إنشاء رسالة التنبيه
        emoji_map = {5: "🔴", 10: "🟠", 20: "🟡"}
        urgency_map = {5: "عاجل جداً", 10: "تحذير", 20: "تنبيه"}
        
        message = f"""
{emoji_map[current_level]} <b>تنبيه: رصيد Non-Voip منخفض</b>

💰 الرصيد: <code>${balance:.2f}</code>
⚠️ المستوى: <b>{urgency_map[current_level]}</b>

📊 لمراجعة الرصيد: /admin → إدارة أرقام Non-Voip
"""
        
        # إرسال للأدمن
        cursor.execute("SELECT DISTINCT user_id FROM admin_logins WHERE active = 1")
        admins = cursor.fetchall()
        
        for (admin_id,) in admins:
            try:
                await context.bot.send_message(chat_id=admin_id, text=message, parse_mode='HTML')
            except:
                pass
        
        # حفظ المستوى
        cursor.execute("INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('last_balance_alert_level', ?, CURRENT_TIMESTAMP)", (str(current_level),))
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ خطأ في فحص رصيد: {e}")


async def job_check_nonvoip_balance(context: ContextTypes.DEFAULT_TYPE):
    """Job: فحص رصيد Non-Voip"""
    await check_nonvoip_balance_and_notify(context)



# ═══════════════════════════════════════════════════════════════════════════════
# وظائف تسجيل عمليات NonVoip (Purchase Logs)
# ═══════════════════════════════════════════════════════════════════════════════

def log_nonvoip_purchase(user_id, username, order_id, number_type, service_type, 
                         price_usd, price_credits, credit_deducted, notes=""):
    """تسجيل عملية شراء أرقام NonVoip"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO nonvoip_purchase_logs 
            (user_id, username, order_id, number_type, service_type, 
             price_usd, price_credits, credit_deducted, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, username, str(order_id), number_type, service_type, 
              price_usd, price_credits, credit_deducted, notes))
        conn.commit()
        conn.close()
        logger.info(f"✅ LOG Purchase: order_id={order_id}, user={user_id}")
    except Exception as e:
        logger.error(f"❌ خطأ في تسجيل الشراء: {e}")

def update_purchase_sms_received(order_id):
    """تحديث وصول الرسالة في اللوغ"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE nonvoip_purchase_logs SET sms_received = 1 WHERE order_id = ?", (str(order_id),))
        conn.commit()
        conn.close()
        logger.info(f"✅ LOG SMS Received: order_id={order_id}")
    except Exception as e:
        logger.error(f"❌ خطأ في تحديث SMS: {e}")

def update_purchase_refund(order_id, refund_amount):
    """تسجيل استرجاع الرصيد في اللوغ"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE nonvoip_purchase_logs 
            SET refunded = 1, credit_refunded = ?, refund_amount = ?
            WHERE order_id = ?
        """, (refund_amount, refund_amount, str(order_id)))
        conn.commit()
        conn.close()
        logger.info(f"✅ LOG Refund: order_id={order_id}, amount={refund_amount}")
    except Exception as e:
        logger.error(f"❌ خطأ في تسجيل الاسترجاع: {e}")

def update_purchase_cancel(order_id):
    """تسجيل إلغاء الطلب في اللوغ"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE nonvoip_purchase_logs SET cancelled = 1 WHERE order_id = ?", (str(order_id),))
        conn.commit()
        conn.close()
        logger.info(f"✅ LOG Cancel: order_id={order_id}")
    except Exception as e:
        logger.error(f"❌ خطأ في تسجيل الإلغاء: {e}")

def log_renewal_operation(user_id, username, order_id, operation_type, 
                         original_number=None, new_number=None, price_usd=None, 
                         price_credits=None, credit_deducted=None, notes=""):
    """تسجيل عملية تجديد أو تفعيل أو استخدام"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO nonvoip_renewal_logs 
            (user_id, username, order_id, operation_type, original_number, 
             new_number, price_usd, price_credits, credit_deducted, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, username, str(order_id), operation_type, original_number, 
              new_number, price_usd, price_credits, credit_deducted, notes))
        conn.commit()
        conn.close()
        logger.info(f"✅ LOG Renewal: order_id={order_id}, type={operation_type}")
    except Exception as e:
        logger.error(f"❌ خطأ في تسجيل التجديد: {e}")

def increment_reuse_count(order_id):
    """زيادة عداد الاستخدام"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE nonvoip_renewal_logs 
            SET reuse_count = reuse_count + 1
            WHERE order_id = ?
        """, (str(order_id),))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"❌ خطأ في زيادة العداد: {e}")
