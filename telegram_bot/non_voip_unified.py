#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
وحدة NonVoipUsNumber المدمجة للتعامل مع API بيع أرقام الهواتف الافتراضية
NonVoipUsNumber Unified Module - Complete API Integration for Virtual Phone Numbers

هذا الملف يجمع جميع وظائف خدمة الأرقام في مكان واحد:
- NonVoipAPI: التعامل مع API
- NonVoipDB: إدارة قاعدة البيانات
- وظائف البوت: دوال الزبائن والآدمن
- معالجات Inline Query
"""

import os
import time
import logging
import sqlite3
import asyncio
import requests
import aiosqlite
import math
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineQueryResultsButton
)
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

try:
    from config import Config, US_STATE_AREA_CODES, POPULAR_US_STATES, US_STATE_NAMES_AR
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    US_STATE_AREA_CODES = {}
    POPULAR_US_STATES = []
    US_STATE_NAMES_AR = {}

logger = logging.getLogger(__name__)

API_BASE = "https://nonvoipusnumber.com/manager/api"
# استخدام مسار مطلق لقاعدة البيانات
DATABASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "proxy_bot.db")


def get_db_connection():
    """إنشاء اتصال بقاعدة البيانات مع إعدادات لتجنب التضارب"""
    conn = sqlite3.connect(DATABASE_FILE, timeout=10.0)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def get_syria_time():
    """الحصول على الوقت الحالي بتوقيت سوريا"""
    from datetime import datetime
    import pytz
    
    syria_tz = pytz.timezone(Config.TIMEZONE)
    return datetime.now(syria_tz).strftime('%Y-%m-%d %H:%M:%S')


def log_nonvoip_operation(
    user_id: int,
    operation_type: str,
    operation_category: str,
    status: str = 'success',
    order_id: int = None,
    amount: float = 0,
    service: str = None,
    number: str = None,
    order_type: str = None,
    details: str = None,
    error_message: str = None
):
    """
    تسجيل شامل لجميع عمليات NonVoip في قاعدة البيانات
    
    Args:
        user_id: معرف المستخدم
        operation_type: نوع العملية (purchase, cancel, refund, sms_received, renewal, etc.)
        operation_category: فئة العملية (order, payment, sms, system)
        status: حالة العملية (success, failed, pending, skipped)
        order_id: معرف الطلب (اختياري)
        amount: المبلغ المالي (للدفع/الاسترداد)
        service: اسم الخدمة
        number: رقم الهاتف
        order_type: نوع الطلب (short_term, long_term, 3days)
        details: تفاصيل إضافية
        error_message: رسالة الخطأ إن وجدت
    """
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        syria_time = get_syria_time()
        
        cursor.execute("""
            INSERT INTO nonvoip_operations_log 
            (order_id, user_id, operation_type, operation_category, amount, 
             service, number, order_type, status, details, error_message, syria_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (order_id, user_id, operation_type, operation_category, amount,
              service, number, order_type, status, details, error_message, syria_time))
        
        conn.commit()
        conn.close()
        
        logger.info(f"📝 LOG [{syria_time}] User:{user_id} | Type:{operation_type} | Category:{operation_category} | Status:{status} | Order:{order_id}")
        
    except Exception as e:
        logger.error(f"خطأ في تسجيل عملية NonVoip: {e}")


def log_refund_operation(order_id: int, user_id: int, operation_type: str, 
                         refund_amount: float, reason: str, status: str = 'success', details: str = None):
    """
    تسجيل عمليات الاسترداد والإلغاء - متوافق مع النظام القديم
    يستخدم log_nonvoip_operation الجديد
    """
    log_nonvoip_operation(
        user_id=user_id,
        operation_type=operation_type,
        operation_category='refund',
        status=status,
        order_id=order_id,
        amount=refund_amount,
        details=f"{reason} | {details if details else ''}"
    )


def calculate_renewal_price(sale_price, order_type: str = 'long_term') -> float:
    """
    حساب سعر التجديد حسب نوع الرقم:
    - short_term (15 دقيقة): نصف السعر (50%)
    - long_term & 3days: نفس السعر الأصلي (100%)
    
    Args:
        sale_price: سعر البيع الأصلي (float, str, أو None)
        order_type: نوع الرقم ('short_term', 'long_term', '3days')
    
    Returns:
        float: سعر التجديد بالكريديت
        
    Examples:
        short_term: 1.00 -> 0.50
        long_term: 1.00 -> 1.00
        3days: 2.00 -> 2.00
    """
    if not sale_price:
        return 0.0
    
    try:
        price = float(sale_price)
        
        # short_term: نصف السعر
        if order_type == 'short_term':
            half_price = price / 2.0
            return math.ceil(half_price * 100) / 100
        
        # long_term & 3days: نفس السعر الأصلي
        return round(price, 2)
    except (ValueError, TypeError):
        logger.error(f"خطأ في تحويل السعر: {sale_price}")
        return 0.0

# تخزين مؤقت للمنتجات لتسريع Inline Query
PRODUCTS_CACHE = {
    'data': [],
    'last_update': 0,
    'cache_duration': 120  # تحديث كل دقيقتين
}

# نظام أكواد الأخطاء المشفرة لإخفاء تفاصيل API عن المستخدمين
ERROR_CODES = {
    '0x0000': 'رصيد الحساب في الموقع غير كافٍ',
    '0x0001': 'الخدمة المطلوبة غير متوفرة حالياً في الموقع',
    '0x0002': 'خطأ في الاتصال بالموقع البعيد',
    '0x0003': 'تم رفض الطلب من قبل الموقع',
    '0x0004': 'انتهت مهلة الاتصال بالموقع',
    '0x0005': 'معلومات تسجيل الدخول غير صحيحة',
    '0x0006': 'تم تجاوز حد الطلبات المسموح',
    '0x0007': 'الرقم المطلوب غير موجود في النظام',
    '0x0008': 'فشل في جلب الرسالة من الموقع',
    '0x0009': 'خطأ غير متوقع من الموقع البعيد',
    '0x000A': 'المنتج غير متاح أو تم حذفه'
}


def log_api_error(error_code: str, actual_error: str, context: str = ""):
    """
    تسجيل الأخطاء الحقيقية في اللوجات مع ربطها بالأكواد المشفرة

    Args:
        error_code: الكود المشفر (مثل 0x0000)
        actual_error: الخطأ الحقيقي من API
        context: سياق إضافي (مثل اسم الدالة أو معرف المستخدم)
    """
    logger.error(f"[{error_code}] {ERROR_CODES.get(error_code, 'خطأ غير معروف')} | الخطأ الفعلي: {actual_error} | السياق: {context}")


def get_error_code_from_message(error_message: str) -> str:
    """
    تحديد كود الخطأ المناسب بناءً على رسالة الخطأ من API

    Args:
        error_message: رسالة الخطأ من API

    Returns:
        كود الخطأ المشفر
    """
    error_lower = str(error_message).lower()

    # التحقق من الأخطاء المختلفة
    if 'balance' in error_lower or 'insufficient' in error_lower or 'رصيد' in error_lower or 'غير كافي' in error_lower or 'funds' in error_lower:
        return '0x0000'
    elif 'not available' in error_lower or 'out of stock' in error_lower or 'غير متوفر' in error_lower:
        return '0x0001'
    elif 'connection' in error_lower or 'network' in error_lower or 'اتصال' in error_lower:
        return '0x0002'
    elif 'rejected' in error_lower or 'denied' in error_lower or 'رفض' in error_lower:
        return '0x0003'
    elif 'timeout' in error_lower or 'timed out' in error_lower or 'انتهت المهلة' in error_lower:
        return '0x0004'
    elif 'auth' in error_lower or 'login' in error_lower or 'password' in error_lower or 'تسجيل الدخول' in error_lower:
        return '0x0005'
    elif 'rate limit' in error_lower or 'too many' in error_lower or 'حد الطلبات' in error_lower:
        return '0x0006'
    elif 'not found' in error_lower or 'غير موجود' in error_lower:
        return '0x0007'
    elif 'sms' in error_lower and ('fail' in error_lower or 'error' in error_lower):
        return '0x0008'
    elif 'product' in error_lower and ('not' in error_lower or 'deleted' in error_lower):
        return '0x000A'
    else:
        return '0x0009'


def generate_message_hash(message_content: str) -> str:
    """
    إنشاء hash للرسالة لمنع إرسال نفس المحتوى مرتين
    
    Args:
        message_content: محتوى الرسالة
    
    Returns:
        hash MD5 للمحتوى
    """
    return hashlib.md5(message_content.encode('utf-8')).hexdigest()


def check_notification_sent(order_id: int, notification_type: str, message_content: str, db_file: str = DATABASE_FILE) -> bool:
    """
    التحقق من إرسال رسالة مماثلة مسبقاً
    
    Args:
        order_id: معرف الطلب
        notification_type: نوع الإشعار (sms, expiry, renewal, etc.)
        message_content: محتوى الرسالة
        db_file: ملف قاعدة البيانات
    
    Returns:
        True إذا تم إرسال الرسالة مسبقاً
    """
    try:
        message_hash = generate_message_hash(message_content)
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id FROM nonvoip_sent_notifications
            WHERE order_id = ? AND notification_type = ? AND message_hash = ?
        """, (order_id, notification_type, message_hash))
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    except Exception as e:
        logger.error(f"خطأ في التحقق من الرسالة المرسلة: {e}")
        return False


def mark_notification_sent(order_id: int, user_id: int, notification_type: str, message_content: str, db_file: str = DATABASE_FILE) -> bool:
    """
    تسجيل إرسال رسالة لمنع التكرار
    
    Args:
        order_id: معرف الطلب
        user_id: معرف المستخدم
        notification_type: نوع الإشعار (sms, expiry, renewal, etc.)
        message_content: محتوى الرسالة
        db_file: ملف قاعدة البيانات
    
    Returns:
        True عند النجاح
    """
    try:
        message_hash = generate_message_hash(message_content)
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR IGNORE INTO nonvoip_sent_notifications 
            (order_id, user_id, notification_type, message_hash)
            VALUES (?, ?, ?, ?)
        """, (order_id, user_id, notification_type, message_hash))
        
        conn.commit()
        conn.close()
        
        logger.info(f"تم تسجيل إرسال {notification_type} للطلب {order_id}")
        return True
    except Exception as e:
        logger.error(f"خطأ في تسجيل الرسالة المرسلة: {e}")
        return False

# ═══════════════════════════════════════════════════════════════════════════════
# PART 1: API CLIENT CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class NonVoipAPI:
    """
    فئة للتعامل مع API الخاص بـ NonVoipUsNumber

    جميع الطلبات تتم من حساب الآدمن الواحد
    """

    def __init__(self, email: Optional[str] = None, password: Optional[str] = None):
        """
        تهيئة الاتصال بـ API

        Args:
            email: البريد الإلكتروني (يُؤخذ من NVUEMAIL إن لم يُحدد)
            password: كلمة المرور (تُؤخذ من NVUPASS إن لم تُحدد)
        """
        if email and password:
            self.email = email
            self.password = password
        elif CONFIG_AVAILABLE:
            self.email = Config.NVUEMAIL
            self.password = Config.NVUPASS
        else:
            self.email = os.getenv("NVUEMAIL")
            self.password = os.getenv("NVUPASS")

        if not self.email or not self.password:
            raise ValueError("يجب تحديد NVUEMAIL و NVUPASS في ملف config.py أو متغيرات البيئة")

        self.auth = {
            "email": self.email,
            "password": self.password
        }

        self.rate_limit_info = {
            "limit": None,
            "remaining": None,
            "reset": None
        }

    def _api_post(self, endpoint: str, data: Optional[Dict] = None, timeout: int = 15) -> Dict:
        """
        إرسال طلب POST إلى API

        Args:
            endpoint: نقطة النهاية (مثل: balance, products, order)
            data: البيانات الإضافية
            timeout: مهلة الانتظار بالثواني

        Returns:
            استجابة JSON من API

        Raises:
            requests.RequestException: عند فشل الاتصال
        """
        url = f"{API_BASE}/{endpoint}"
        payload = {**self.auth, **(data or {})}

        logger.info(f"إرسال طلب API إلى {endpoint} - البيانات: {data}")

        try:
            resp = requests.post(url, json=payload, timeout=timeout)

            logger.info(f"استجابة API من {endpoint}: الحالة {resp.status_code}")

            if 'X-RateLimit-Limit' in resp.headers:
                self.rate_limit_info['limit'] = int(resp.headers.get('X-RateLimit-Limit', 0))
                self.rate_limit_info['remaining'] = int(resp.headers.get('X-RateLimit-Remaining', 0))
                self.rate_limit_info['reset'] = resp.headers.get('X-RateLimit-Reset')

            if resp.status_code == 429:
                retry_after = int(resp.headers.get('Retry-After', 60))
                logger.warning(f"تم تجاوز حد الطلبات. إعادة المحاولة بعد {retry_after} ثانية")
                return {
                    "status": "error",
                    "message": f"تم تجاوز حد الطلبات. يرجى المحاولة بعد {retry_after} ثانية",
                    "retry_after": retry_after
                }

            if resp.status_code == 400:
                try:
                    error_data = resp.json()
                    error_msg = error_data.get('message', 'طلب غير صالح')
                    logger.error(f"خطأ 400 من API: {error_msg} - البيانات المرسلة: {payload}")
                    return {"status": "error", "message": f"خطأ في الطلب: {error_msg}"}
                except:
                    logger.error(f"خطأ 400 من API - لم يتم فك تشفير الاستجابة")
                    return {"status": "error", "message": "خطأ في الطلب: البيانات المرسلة غير صحيحة"}

            resp.raise_for_status()
            return resp.json()

        except requests.Timeout:
            logger.error(f"انتهت مهلة الطلب إلى {endpoint}")
            return {"status": "error", "message": "انتهت مهلة الطلب"}
        except requests.HTTPError as e:
            logger.error(f"خطأ HTTP في الطلب إلى {endpoint}: {e} - الحالة: {resp.status_code}")
            try:
                error_response = resp.json()
                return {"status": "error", "message": error_response.get('message', str(e))}
            except:
                return {"status": "error", "message": f"خطأ HTTP: {str(e)}"}
        except requests.RequestException as e:
            logger.error(f"خطأ في الطلب إلى {endpoint}: {str(e)}")
            return {"status": "error", "message": f"خطأ في الاتصال: {str(e)}"}

    def get_balance(self) -> Dict[str, Any]:
        """
        جلب رصيد حساب الآدمن

        للآدمن فقط

        Returns:
            {"status": "success", "balance": "50.00"} عند النجاح
            {"status": "error", "message": "..."} عند الفشل
        """
        result = self._api_post("balance")
        logger.info(f"جلب الرصيد: {result}")
        return result

    def get_products(self, product_type: Optional[str] = None,
                    network: Optional[int] = None,
                    product_id: Optional[int] = None) -> Dict[str, Any]:
        """
        جلب قائمة المنتجات المتاحة وأسعارها

        للآدمن فقط (لعرض الخدمات المتاحة)

        Args:
            product_type: نوع المنتج ('short_term', 'long_term', '3days')
            network: الشبكة (1 أو 2)
            product_id: معرف المنتج (للحصول على منتج واحد)

        Returns:
            قائمة المنتجات مع الأسعار والمخزون المتاح
        """
        data = {}
        if product_type:
            data['type'] = product_type
        if network:
            data['network'] = network
        if product_id:
            data['id'] = product_id

        result = self._api_post("products", data)
        logger.info(f"جلب المنتجات: {len(result.get('message', []))} منتج")
        return result

    def order(self, product_id: int, auction: Optional[int] = None) -> Dict[str, Any]:
        """
        طلب رقم جديد

        للزبائن (يتم الطلب من حساب الآدمن)

        Args:
            product_id: معرف المنتج المطلوب
            auction: نسبة العرض للمزاد (10-2000%) للأرقام الأمريكية عند عدم التوفر

        Returns:
            تفاصيل الطلب مع الرقم
        """
        data = {"product_id": product_id}
        if auction:
            data['auction'] = auction

        result = self._api_post("order", data)

        if result.get('status') == 'success':
            order_info = result['message'][0]
            logger.info(f"تم طلب رقم جديد: {order_info.get('number', 'في انتظار التخصيص')}")
        else:
            logger.error(f"فشل طلب الرقم: {result.get('message')}")

        return result

    def get_sms(self, service: str, number: str, order_id: Optional[int] = None) -> Dict[str, Any]:
        """
        جلب آخر رسالة SMS للرقم

        للزبائن

        Args:
            service: اسم الخدمة (مثل: paypal, google)
            number: رقم الهاتف بصيغة E.164
            order_id: معرف الطلب (اختياري)

        Returns:
            آخر رسالة SMS ورمز PIN إن وُجد
        """
        data = {"service": service, "number": number}
        if order_id:
            data['order_id'] = order_id

        result = self._api_post("getsms", data)

        if result.get('status') == 'success':
            logger.info(f"تم جلب SMS للرقم {number}")

        return result

    def reuse(self, service: str, number: str) -> Dict[str, Any]:
        """
        إعادة استخدام رقم قصير الأمد مجاناً

        للزبائن

        Args:
            service: اسم الخدمة
            number: رقم الهاتف

        Returns:
            تفاصيل إعادة الاستخدام
        """
        data = {"service": service, "number": number}
        result = self._api_post("reuse", data)

        if result.get('status') == 'success':
            logger.info(f"تم إعادة استخدام الرقم {number}")

        return result

    def reject(self, service: Optional[str] = None,
               number: Optional[str] = None,
               order_id: Optional[int] = None) -> Dict[str, Any]:
        """
        رفض رقم لاسترداد المبلغ (قبل استقبال SMS)

        للزبائن

        Args:
            service: اسم الخدمة (مطلوب إذا لم يُحدد order_id)
            number: رقم الهاتف (مطلوب إذا لم يُحدد order_id)
            order_id: معرف الطلب (للأرقام غير المخصصة بعد)

        Returns:
            تأكيد الرفض والاسترداد
        """
        data = {}
        if service:
            data['service'] = service
        if number:
            data['number'] = number
        if order_id:
            data['order_id'] = order_id

        result = self._api_post("reject", data)

        if result.get('status') == 'success':
            logger.info(f"تم رفض الرقم {number or order_id} واسترداد المبلغ")

        return result

    def renew(self, service: str, number: str) -> Dict[str, Any]:
        """
        تجديد رقم طويل الأمد (long_term أو 3days)

        للزبائن

        Args:
            service: اسم الخدمة
            number: رقم الهاتف

        Returns:
            تاريخ انتهاء الصلاحية الجديد
        """
        data = {"service": service, "number": number}
        result = self._api_post("renew", data)

        if result.get('status') == 'success':
            logger.info(f"تم تجديد الرقم {number}")

        return result

    def activate(self, service: str, number: str) -> Dict[str, Any]:
        """
        تفعيل رقم طويل الأمد قبل استقبال SMS

        للزبائن

        Args:
            service: اسم الخدمة
            number: رقم الهاتف

        Returns:
            حالة التفعيل والوقت المتاح
        """
        data = {"service": service, "number": number}
        result = self._api_post("activate", data)

        if result.get('status') == 'success':
            logger.info(f"تم تفعيل الرقم {number}")

        return result


# ═══════════════════════════════════════════════════════════════════════════════
# PART 2: DATABASE MANAGER CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class NonVoipDB:
    """
    إدارة قاعدة البيانات لطلبات NonVoip
    """

    def __init__(self, db_file: str = DATABASE_FILE):
        """تهيئة الاتصال بقاعدة البيانات"""
        self.db_file = db_file
        self._init_tables()

    def _init_tables(self):
        """إنشاء جداول قاعدة البيانات"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nonvoip_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                order_id INTEGER NOT NULL,
                product_id INTEGER,
                product_name TEXT,
                number TEXT,
                service TEXT,
                status TEXT DEFAULT 'pending',
                type TEXT,
                expiration TEXT,
                expires_at TEXT,
                sms_received TEXT,
                pin_code TEXT,
                cost_price REAL,
                sale_price REAL,
                refunded BOOLEAN DEFAULT 0,
                sms_sent BOOLEAN DEFAULT 0,
                monitoring_started TIMESTAMP,
                message_id INTEGER,
                renewable BOOLEAN DEFAULT 0,
                renewal_deadline TEXT,
                renewed BOOLEAN DEFAULT 0,
                renewal_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # إضافة الحقول الجديدة للجداول الموجودة (Migration)
        try:
            cursor.execute("ALTER TABLE nonvoip_orders ADD COLUMN renewable BOOLEAN DEFAULT 0")
        except:
            pass  # الحقل موجود بالفعل

        try:
            cursor.execute("ALTER TABLE nonvoip_orders ADD COLUMN renewal_deadline TEXT")
        except:
            pass

        try:
            cursor.execute("ALTER TABLE nonvoip_orders ADD COLUMN renewed BOOLEAN DEFAULT 0")
        except:
            pass

        try:
            cursor.execute("ALTER TABLE nonvoip_orders ADD COLUMN renewal_type TEXT")
        except:
            pass

        # إضافة حقل لتحديد ما إذا كان الرقم مرئياً في "My Numbers" (فصل منطق الحذف)
        try:
            cursor.execute("ALTER TABLE nonvoip_orders ADD COLUMN visible_in_my_numbers BOOLEAN DEFAULT 1")
            logger.info("✅ تمت إضافة حقل visible_in_my_numbers بنجاح")
        except:
            pass  # الحقل موجود بالفعل

        # إضافة حقول التفعيل للأرقام طويلة المدى
        try:
            cursor.execute("ALTER TABLE nonvoip_orders ADD COLUMN activation_status TEXT DEFAULT 'inactive'")
            logger.info("✅ تمت إضافة حقل activation_status بنجاح")
        except:
            pass
        
        try:
            cursor.execute("ALTER TABLE nonvoip_orders ADD COLUMN activated_until TEXT")
            logger.info("✅ تمت إضافة حقل activated_until بنجاح")
        except:
            pass
        
        try:
            cursor.execute("ALTER TABLE nonvoip_orders ADD COLUMN auto_activated BOOLEAN DEFAULT 0")
            logger.info("✅ تمت إضافة حقل auto_activated بنجاح")
        except:
            pass

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nonvoip_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stat_date DATE NOT NULL,
                stat_type TEXT NOT NULL,
                orders_count INTEGER DEFAULT 0,
                total_revenue REAL DEFAULT 0.0,
                total_cost REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(stat_date, stat_type)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_nonvoip_user_id
            ON nonvoip_orders(user_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_nonvoip_order_id
            ON nonvoip_orders(order_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_nonvoip_status
            ON nonvoip_orders(status)
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nonvoip_price_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT NOT NULL UNIQUE,
                price_percentage REAL DEFAULT 0.0,
                credit_value REAL DEFAULT 1.0,
                is_enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_nonvoip_service_name
            ON nonvoip_price_settings(service_name)
        """)

        try:
            cursor.execute("ALTER TABLE nonvoip_orders ADD COLUMN sms_sent BOOLEAN DEFAULT 0")
        except:
            pass

        try:
            cursor.execute("ALTER TABLE nonvoip_orders ADD COLUMN monitoring_started TIMESTAMP")
        except:
            pass

        try:
            cursor.execute("ALTER TABLE nonvoip_orders ADD COLUMN message_id INTEGER")
        except:
            pass

        try:
            cursor.execute("ALTER TABLE nonvoip_orders ADD COLUMN expired_notified BOOLEAN DEFAULT 0")
        except:
            pass

        try:
            cursor.execute("ALTER TABLE nonvoip_orders ADD COLUMN activation_notified BOOLEAN DEFAULT 0")
            logger.info("✅ تمت إضافة حقل activation_notified بنجاح")
        except:
            pass  # الحقل موجود بالفعل

        try:
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_nonvoip_order_id_unique ON nonvoip_orders(order_id)")
            logger.info("✅ تم إنشاء UNIQUE INDEX على order_id")
        except Exception as e:
            logger.warning(f"⚠️ UNIQUE INDEX موجود مسبقاً أو حدث خطأ: {e}")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nonvoip_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                message_text TEXT NOT NULL,
                pin_code TEXT,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES nonvoip_orders(order_id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_order
            ON nonvoip_messages(order_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_user
            ON nonvoip_messages(user_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_time
            ON nonvoip_messages(received_at)
        """)

        # جدول جديد لتتبع الرسائل المرسلة لمنع التكرار
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nonvoip_sent_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                notification_type TEXT NOT NULL,
                message_hash TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(order_id, notification_type, message_hash)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_order
            ON nonvoip_sent_notifications(order_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_type
            ON nonvoip_sent_notifications(notification_type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_hash
            ON nonvoip_sent_notifications(message_hash)
        """)

        # جدول لتتبع إشعارات رصيد NonVoip (نظام تدريجي)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nonvoip_balance_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                notification_level INTEGER NOT NULL,
                balance_amount REAL NOT NULL,
                notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(notification_level)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_balance_notifications_level
            ON nonvoip_balance_notifications(notification_level)
        """)

        conn.commit()
        conn.close()
        logger.info("تم تهيئة جداول قاعدة بيانات NonVoip")

        self._migrate_success_to_active()
        self._migrate_old_messages()

    def _migrate_success_to_active(self):
        """
        تحديث الأرقام القديمة من status='success' إلى status='active'
        هذا migration لإصلاح الأرقام التي تم حفظها قبل إصلاح save_order
        """
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE nonvoip_orders
                SET status = 'active', updated_at = CURRENT_TIMESTAMP
                WHERE status = 'success'
                AND refunded = 0
            """)

            updated_count = cursor.rowcount

            if updated_count > 0:
                logger.info(f"✅ تم تحديث {updated_count} طلب من status='success' إلى status='active'")

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"خطأ في migration: {e}")

    def _migrate_old_messages(self):
        """
        ترحيل الرسائل القديمة من الحقول sms_received/pin_code إلى جدول nonvoip_messages
        """
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT order_id, user_id, sms_received, pin_code, updated_at
                FROM nonvoip_orders
                WHERE sms_received IS NOT NULL 
                AND sms_received != ''
                AND order_id NOT IN (SELECT DISTINCT order_id FROM nonvoip_messages)
            """)

            old_messages = cursor.fetchall()

            migrated_count = 0
            for row in old_messages:
                order_id, user_id, sms_text, pin_code, updated_at = row
                try:
                    cursor.execute("""
                        INSERT INTO nonvoip_messages (order_id, user_id, message_text, pin_code, received_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (order_id, user_id, sms_text, pin_code, updated_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    migrated_count += 1
                except Exception as e:
                    logger.warning(f"خطأ في ترحيل الرسالة للطلب {order_id}: {e}")
                    continue

            if migrated_count > 0:
                logger.info(f"✅ تم ترحيل {migrated_count} رسالة قديمة إلى جدول nonvoip_messages")

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"خطأ في ترحيل الرسائل القديمة: {e}")

    def _get_connection(self):
        """إنشاء اتصال مؤقت بقاعدة البيانات"""
        return sqlite3.connect(self.db_file)

    def fetch_one(self, query: str, params: tuple = ()):
        """
        جلب سطر واحد من قاعدة البيانات

        Args:
            query: استعلام SQL
            params: معاملات الاستعلام

        Returns:
            سطر واحد أو None
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        conn.close()
        return result

    def fetch_all(self, query: str, params: tuple = ()):
        """
        جلب جميع السطور من قاعدة البيانات

        Args:
            query: استعلام SQL
            params: معاملات الاستعلام

        Returns:
            قائمة بالسطور
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        return results

    def execute_query(self, query: str, params: tuple = ()):
        """
        تنفيذ استعلام تعديل (INSERT/UPDATE/DELETE)

        Args:
            query: استعلام SQL
            params: معاملات الاستعلام

        Returns:
            عدد السطور المتأثرة
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        rowcount = cursor.rowcount
        conn.close()
        return rowcount

    def set_order_message_id(self, order_id: int, message_id: int):
        """
        حفظ message_id للطلب لتمكين المراقبة التلقائية

        Args:
            order_id: معرف الطلب من API
            message_id: معرف رسالة تيليجرام
        """
        self.execute_query("""
            UPDATE nonvoip_orders
            SET message_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE order_id = ?
        """, (message_id, order_id))
        logger.info(f"تم حفظ message_id={message_id} للطلب {order_id}")

    def auto_activate_number_on_purchase(self, order_id: int, service: str, number: str) -> Dict[str, Any]:
        """
        تفعيل الرقم تلقائياً فور الشراء للأرقام طويلة المدى (مرة واحدة فقط)
        
        Args:
            order_id: معرف الطلب
            service: اسم الخدمة
            number: رقم الهاتف
        
        Returns:
            نتيجة التفعيل من API
        """
        try:
            api = NonVoipAPI()
            result = api.activate(service=service, number=number)
            
            if result.get('status') == 'success':
                import pytz
                from datetime import datetime
                from dateutil import parser
                
                activation_data = result.get('message', [{}])[0]
                end_time_str = activation_data.get('end_on')
                
                # تحويل الوقت لتوقيت سوريا
                syria_tz = pytz.timezone(Config.TIMEZONE)
                try:
                    end_time = parser.parse(end_time_str)
                    if end_time.tzinfo is None:
                        end_time = pytz.UTC.localize(end_time)
                    end_time_syria = end_time.astimezone(syria_tz)
                    end_time_str_syria = end_time_syria.isoformat()
                except Exception as parse_error:
                    logger.warning(f"فشل تحويل الوقت لتوقيت سوريا: {parse_error}, استخدام الوقت الأصلي")
                    end_time_str_syria = end_time_str
                
                # تحديث قاعدة البيانات
                self.execute_query("""
                    UPDATE nonvoip_orders
                    SET activation_status = 'active',
                        activated_until = ?,
                        auto_activated = 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE order_id = ?
                """, (end_time_str_syria, order_id))
                
                logger.info(f"✅ تم التفعيل التلقائي للرقم {number} - الطلب {order_id} - ينتهي في {end_time_str_syria}")
                return {'status': 'success', 'activated_until': end_time_str_syria}
            else:
                logger.warning(f"⚠️ فشل التفعيل التلقائي للطلب {order_id}: {result.get('message')}")
                return result
        except Exception as e:
            logger.error(f"❌ خطأ في التفعيل التلقائي للطلب {order_id}: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def update_activation_status(self, order_id: int, activation_status: str, activated_until: str = None):
        """
        تحديث حالة التفعيل للرقم (مع تحويل التوقيت لتوقيت سوريا)
        
        Args:
            order_id: معرف الطلب
            activation_status: حالة التفعيل ('active' أو 'inactive')
            activated_until: وقت انتهاء التفعيل (سيتم تحويله لتوقيت سوريا)
        """
        # تحويل الوقت لتوقيت سوريا إذا كان موجوداً
        if activated_until:
            import pytz
            from dateutil import parser
            syria_tz = pytz.timezone(Config.TIMEZONE)
            try:
                end_time = parser.parse(activated_until)
                if end_time.tzinfo is None:
                    end_time = pytz.UTC.localize(end_time)
                end_time_syria = end_time.astimezone(syria_tz)
                activated_until = end_time_syria.isoformat()
            except Exception as e:
                logger.warning(f"فشل تحويل الوقت لتوقيت سوريا: {e}, استخدام الوقت الأصلي")
        
        self.execute_query("""
            UPDATE nonvoip_orders
            SET activation_status = ?,
                activated_until = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE order_id = ?
        """, (activation_status, activated_until, order_id))
        logger.info(f"تم تحديث حالة التفعيل للطلب {order_id}: {activation_status}")
    
    def get_activation_status(self, order_id: int) -> Dict[str, Any]:
        """
        الحصول على حالة التفعيل الحالية للرقم
        
        Args:
            order_id: معرف الطلب
        
        Returns:
            قاموس يحتوي على activation_status و activated_until
        """
        result = self.fetch_one("""
            SELECT activation_status, activated_until, type
            FROM nonvoip_orders
            WHERE order_id = ?
        """, (order_id,))
        
        if result:
            return {
                'activation_status': result[0] or 'inactive',
                'activated_until': result[1],
                'type': result[2]
            }
        return {'activation_status': 'inactive', 'activated_until': None, 'type': None}

    def save_order(self, user_id: int, order_data: Dict,
                   cost_price: Optional[float] = None,
                   sale_price: Optional[float] = None) -> int:
        """
        حفظ طلب جديد في قاعدة البيانات وتحديث الإحصائيات

        Args:
            user_id: معرف المستخدم في تيليجرام
            order_data: بيانات الطلب من API
            cost_price: سعر التكلفة
            sale_price: سعر البيع للزبون

        Returns:
            معرف السجل في قاعدة البيانات
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # تحويل status من API إلى status صالح للنظام
        api_status = order_data.get('status', 'pending')
        # تحويل جميع الحالات إلى حروف صغيرة للتوحيد
        api_status_lower = api_status.lower() if isinstance(api_status, str) else 'pending'
        # تحويل 'success' إلى 'active' لأن هذا يعني أن الطلب نشط ومحجوز
        normalized_status = 'active' if api_status_lower == 'success' else api_status_lower

        # حساب expires_at بشكل موحد لجميع أنواع الأرقام
        order_type = order_data.get('type', 'short_term')
        expires_at = None

        if order_type == 'short_term':
            # للأرقام قصيرة الأمد: حساب الوقت بإضافة expiration (بالثواني) للوقت الحالي
            expiration_seconds = order_data.get('expiration', 900)  # 15 دقيقة افتراضياً
            if expiration_seconds:
                from datetime import datetime, timedelta
                expires_at = (datetime.utcnow() + timedelta(seconds=expiration_seconds)).strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"[save_order] short_term - expiration={expiration_seconds}s → expires_at={expires_at}")
        else:
            # للأرقام طويلة الأمد (long_term/3days): استخدام expires من API مباشرة
            expires_at = order_data.get('expires')
            if expires_at:
                logger.info(f"[save_order] {order_type} - expires_at={expires_at}")

        cursor.execute("""
            INSERT INTO nonvoip_orders
            (user_id, order_id, product_id, product_name, number, service,
             status, type, expiration, expires_at, cost_price, sale_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            order_data.get('order_id'),
            order_data.get('product_id'),
            order_data.get('product_name', order_data.get('service')),
            order_data.get('number', ''),
            order_data.get('service'),
            normalized_status,
            order_type,
            order_data.get('expiration'),
            expires_at,
            cost_price,
            sale_price
        ))

        order_db_id = cursor.lastrowid

        # تحديث الإحصائيات فقط للأرقام طويلة الأمد (long_term & 3days)
        # أما short_term فتُحسب عند وصول SMS فقط
        if order_type in ['long_term', '3days']:
            from datetime import datetime
            today = datetime.now().strftime('%Y-%m-%d')
            
            for stat_type in ['daily', 'weekly', 'monthly', 'total']:
                cursor.execute("""
                    INSERT OR REPLACE INTO nonvoip_statistics
                    (stat_date, stat_type, orders_count, total_revenue, total_cost, updated_at)
                    VALUES (
                        ?, ?,
                        COALESCE((SELECT orders_count FROM nonvoip_statistics WHERE stat_date = ? AND stat_type = ?), 0) + 1,
                        COALESCE((SELECT total_revenue FROM nonvoip_statistics WHERE stat_date = ? AND stat_type = ?), 0) + ?,
                        COALESCE((SELECT total_cost FROM nonvoip_statistics WHERE stat_date = ? AND stat_type = ?), 0) + ?,
                        CURRENT_TIMESTAMP
                    )
                """, (today, stat_type, today, stat_type, today, stat_type, sale_price or 0, today, stat_type, cost_price or 0))
            
            logger.info(f"✅ تم تحديث الإحصائيات للطلب {order_data.get('order_id')} ({order_type}) - {sale_price} كريديت")

        conn.commit()
        conn.close()

        logger.info(f"تم حفظ الطلب {order_data.get('order_id')} للمستخدم {user_id} - النوع: {order_type}, expires_at: {expires_at}")
        return order_db_id

    def update_order_sms(self, order_id: int, sms: str, pin: Optional[str] = None):
        """
        تحديث الطلب عند وصول رسالة SMS وتحديث الإحصائيات
        
        ملاحظة: تحديث الإحصائيات يحدث فقط للأرقام قصيرة الأمد (short_term)
        أما long_term & 3days فتُحسب إحصائياتها عند الشراء مباشرة
        
        يتم استدعاء save_message بشكل منفصل لحفظ الرسالة في الجدول الجديد

        Args:
            order_id: معرف الطلب من API
            sms: نص الرسالة
            pin: رمز PIN المستخرج
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id, sale_price, cost_price, type FROM nonvoip_orders
            WHERE order_id = ?
        """, (order_id,))

        order_row = cursor.fetchone()
        if not order_row:
            logger.warning(f"الطلب {order_id} غير موجود في قاعدة البيانات")
            conn.close()
            return
        
        user_id = order_row[0]
        sale_price = order_row[1]
        cost_price = order_row[2]
        order_type = order_row[3] if len(order_row) > 3 else 'short_term'

        # حفظ الرسالة في الجدول الجديد (مع حذف تلقائي للرسائل القديمة)
        self.save_message(order_id, user_id, sms, pin)

        # تحديث الرسالة والحالة (لا نغير renewed - يُستخدم فقط للتجديد الفعلي)
        cursor.execute("""
            UPDATE nonvoip_orders
            SET sms_received = ?, pin_code = ?, status = 'delivered',
                updated_at = CURRENT_TIMESTAMP
            WHERE order_id = ?
        """, (sms, pin, order_id))
        logger.info(f"تم تحديث SMS للطلب {order_id} - Status: delivered")
        
        # تسجيل وصول SMS في nonvoip_purchase_logs
        import sys
        sys.path.insert(0, '/home/runner/workspace')
        from bot import update_purchase_sms_received
        update_purchase_sms_received(order_id)

        # تحديث الإحصائيات فقط للأرقام قصيرة الأمد (short_term)
        # long_term & 3days تُحسب عند الشراء مباشرة
        if order_type == 'short_term':
            from datetime import datetime
            today = datetime.now().strftime('%Y-%m-%d')

            for stat_type in ['daily', 'weekly', 'monthly', 'total']:
                cursor.execute("""
                    INSERT OR REPLACE INTO nonvoip_statistics
                    (stat_date, stat_type, orders_count, total_revenue, total_cost, updated_at)
                    VALUES (
                        ?, ?,
                        COALESCE((SELECT orders_count FROM nonvoip_statistics WHERE stat_date = ? AND stat_type = ?), 0) + 1,
                        COALESCE((SELECT total_revenue FROM nonvoip_statistics WHERE stat_date = ? AND stat_type = ?), 0) + ?,
                        COALESCE((SELECT total_cost FROM nonvoip_statistics WHERE stat_date = ? AND stat_type = ?), 0) + ?,
                        CURRENT_TIMESTAMP
                    )
                """, (today, stat_type, today, stat_type, today, stat_type, sale_price or 0, today, stat_type, cost_price or 0))
            
            logger.info(f"✅ تم تحديث الإحصائيات للطلب {order_id} (short_term) عند وصول SMS - {sale_price} كريديت")

        conn.commit()
        conn.close()
        logger.info(f"تم تحديث SMS للطلب {order_id}")

    def save_message(self, order_id: int, user_id: int, message_text: str, pin_code: Optional[str] = None):
        """
        حفظ رسالة جديدة في جدول الرسائل مع الاحتفاظ بآخر 3 رسائل فقط
        
        Args:
            order_id: معرف الطلب
            user_id: معرف المستخدم
            message_text: نص الرسالة
            pin_code: رمز التحقق إن وجد
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO nonvoip_messages (order_id, user_id, message_text, pin_code, received_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (order_id, user_id, message_text, pin_code))
            
            cursor.execute("""
                SELECT COUNT(*) FROM nonvoip_messages WHERE order_id = ?
            """, (order_id,))
            
            message_count = cursor.fetchone()[0]
            
            if message_count > 3:
                delete_count = message_count - 3
                cursor.execute("""
                    DELETE FROM nonvoip_messages
                    WHERE id IN (
                        SELECT id FROM nonvoip_messages
                        WHERE order_id = ?
                        ORDER BY received_at ASC
                        LIMIT ?
                    )
                """, (order_id, delete_count))
                logger.info(f"🗑️ تم حذف {delete_count} رسالة قديمة للطلب {order_id} (الاحتفاظ بآخر 3 فقط)")
            
            conn.commit()
            logger.info(f"✅ تم حفظ رسالة جديدة للطلب {order_id} - إجمالي الرسائل: {min(message_count, 3)}")
            
        except Exception as e:
            logger.error(f"خطأ في حفظ الرسالة للطلب {order_id}: {e}")
            conn.rollback()
        finally:
            conn.close()

    def get_messages_for_order(self, order_id: int, user_id: Optional[int] = None, limit: int = 3) -> List[Dict]:
        """
        جلب آخر N رسائل لرقم معين من قاعدة البيانات المحلية
        
        Args:
            order_id: معرف الطلب
            user_id: معرف المستخدم (للتحقق من الصلاحية)
            limit: عدد الرسائل المطلوبة (افتراضي 3)
        
        Returns:
            قائمة بالرسائل مرتبة من الأحدث إلى الأقدم
        """
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute("""
                SELECT message_text, pin_code, received_at
                FROM nonvoip_messages
                WHERE order_id = ? AND user_id = ?
                ORDER BY received_at DESC
                LIMIT ?
            """, (order_id, user_id, limit))
        else:
            cursor.execute("""
                SELECT message_text, pin_code, received_at
                FROM nonvoip_messages
                WHERE order_id = ?
                ORDER BY received_at DESC
                LIMIT ?
            """, (order_id, limit))
        
        messages = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        logger.info(f"📨 جلب {len(messages)} رسالة للطلب {order_id} من قاعدة البيانات المحلية")
        return messages

    def delete_messages_for_order(self, order_id: int):
        """
        حذف جميع الرسائل المرتبطة برقم معين
        
        Args:
            order_id: معرف الطلب
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM nonvoip_messages WHERE order_id = ?
            """, (order_id,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            if deleted_count > 0:
                logger.info(f"🗑️ تم حذف {deleted_count} رسالة للطلب {order_id} بعد انتهاء الصلاحية")
            
        except Exception as e:
            logger.error(f"خطأ في حذف الرسائل للطلب {order_id}: {e}")
            conn.rollback()
        finally:
            conn.close()

    def delete_messages_for_expired_numbers(self):
        """
        حذف جميع الرسائل للأرقام المنتهية صلاحيتها
        
        Returns:
            عدد الرسائل المحذوفة
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM nonvoip_messages
                WHERE order_id IN (
                    SELECT order_id FROM nonvoip_orders
                    WHERE status = 'expired'
                    OR (expires_at IS NOT NULL AND datetime(expires_at) < datetime('now'))
                )
            """)
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            if deleted_count > 0:
                logger.info(f"🗑️ تم حذف {deleted_count} رسالة للأرقام المنتهية الصلاحية")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"خطأ في حذف رسائل الأرقام المنتهية: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()

    def update_order_status(self, order_id: int, status: str):
        """
        تحديث حالة الطلب

        Args:
            order_id: معرف الطلب من API
            status: الحالة الجديدة
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE nonvoip_orders
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE order_id = ?
        """, (status, order_id))

        conn.commit()
        conn.close()
        logger.info(f"تم تحديث حالة الطلب {order_id} إلى {status}")

    def get_user_orders(self, user_id: int, limit: int = 50) -> List[Dict]:
        """
        جلب جميع طلبات مستخدم معين

        Args:
            user_id: معرف المستخدم في تيليجرام
            limit: الحد الأقصى للطلبات

        Returns:
            قائمة بطلبات المستخدم
        """
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM nonvoip_orders
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))

        orders = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return orders

    def get_active_orders(self, user_id: Optional[int] = None) -> List[Dict]:
        """
        جلب الطلبات النشطة (غير المنتهية الصلاحية)

        Args:
            user_id: معرف المستخدم (اختياري - للحصول على طلبات مستخدم معين)

        Returns:
            قائمة بالطلبات النشطة (لا تشمل الأرقام الملغاة أو المستردة)
        """
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if user_id:
            cursor.execute("""
                SELECT * FROM nonvoip_orders
                WHERE user_id = ?
                AND status IN ('pending', 'reserved', 'active', 'delivered', 'success')
                AND refunded = 0
                ORDER BY created_at DESC
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT * FROM nonvoip_orders
                WHERE status IN ('pending', 'reserved', 'active', 'delivered', 'success')
                AND refunded = 0
                ORDER BY created_at DESC
            """)

        orders = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return orders

    def get_current_orders(self, user_id: Optional[int] = None) -> List[Dict]:
        """
        جلب الطلبات النشطة حالياً (My Numbers - تصفية الأرقام المنتهية والمخفية)

        هذه الدالة تعرض فقط الأرقام التي:
        - لم تنته صلاحيتها بعد
        - مرئية في My Numbers (visible_in_my_numbers = 1)
        - لم تستقبل رسالة SMS (للأرقام short_term) أو لا تزال نشطة (للأرقام الأخرى)

        Args:
            user_id: معرف المستخدم (اختياري - للحصول على طلبات مستخدم معين)

        Returns:
            قائمة بالطلبات النشطة المرئية في My Numbers
        """
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if user_id:
            cursor.execute("""
                SELECT * FROM nonvoip_orders
                WHERE user_id = ?
                AND status IN ('pending', 'reserved', 'active', 'delivered', 'success')
                AND (expires_at IS NULL OR datetime(expires_at) > datetime('now'))
                AND refunded = 0
                AND COALESCE(visible_in_my_numbers, 1) = 1
                AND NOT (type = 'short_term' AND sms_received IS NOT NULL)
                ORDER BY created_at DESC
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT * FROM nonvoip_orders
                WHERE status IN ('pending', 'reserved', 'active', 'delivered', 'success')
                AND (expires_at IS NULL OR datetime(expires_at) > datetime('now'))
                AND refunded = 0
                AND COALESCE(visible_in_my_numbers, 1) = 1
                AND NOT (type = 'short_term' AND sms_received IS NOT NULL)
                ORDER BY created_at DESC
            """)

        orders = [dict(row) for row in cursor.fetchall()]
        conn.close()

        logger.info(f"تم جلب {len(orders)} طلب نشط" + (f" للمستخدم {user_id}" if user_id else ""))
        return orders

    def get_order_by_id(self, order_id: int) -> Optional[Dict]:
        """
        جلب طلب معين بواسطة معرف API

        Args:
            order_id: معرف الطلب من API

        Returns:
            بيانات الطلب أو None
        """
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM nonvoip_orders
            WHERE order_id = ?
        """, (order_id,))

        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def get_all_orders(self, limit: int = 1000) -> List[Dict]:
        """
        جلب جميع الطلبات (للآدمن - لعرض الإحصائيات)

        Args:
            limit: الحد الأقصى للطلبات (افتراضي: 1000)

        Returns:
            قائمة بجميع الطلبات
        """
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM nonvoip_orders
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        orders = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return orders

    def set_service_price_settings(self, service_name: str,
                                   price_percentage: float,
                                   credit_value: Optional[float] = None) -> bool:
        """
        تعيين إعدادات السعر لخدمة معينة

        Args:
            service_name: اسم الخدمة (مثل: NonVoipUsNumber)
            price_percentage: النسبة المئوية المضافة على السعر بالدولار
            credit_value: قيمة الكريديت الواحد بالدولار (اختياري)

        Returns:
            True عند النجاح
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        if credit_value is None:
            cursor.execute("""
                INSERT OR REPLACE INTO nonvoip_price_settings
                (service_name, price_percentage, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (service_name, price_percentage))
        else:
            cursor.execute("""
                INSERT OR REPLACE INTO nonvoip_price_settings
                (service_name, price_percentage, credit_value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (service_name, price_percentage, credit_value))

        conn.commit()
        conn.close()
        logger.info(f"تم تحديث إعدادات السعر لخدمة {service_name}")
        return True

    def get_service_price_settings(self, service_name: str) -> Optional[Dict]:
        """
        الحصول على إعدادات السعر لخدمة معينة

        Args:
            service_name: اسم الخدمة

        Returns:
            قاموس بإعدادات السعر أو None
        """
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM nonvoip_price_settings
            WHERE service_name = ?
        """, (service_name,))

        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def calculate_service_price_in_credits(self, dollar_price: float,
                                          service_name: str = "website") -> float:
        """
        حساب سعر الخدمة بالكريديت بناءً على السعر بالدولار
        يتم تطبيق النسبة المئوية من إدارة الأسعار

        Args:
            dollar_price: السعر الأصلي بالدولار
            service_name: اسم الخدمة (افتراضي: website)

        Returns:
            السعر المحسوب بالكريديت (بعد تطبيق النسبة المئوية من إدارة الأسعار)
        """
        # محاولة جلب إعدادات الخدمة المحددة
        settings = self.get_service_price_settings(service_name)

        # إذا لم توجد إعدادات للخدمة المحددة، جرب النسبة العامة لـ NonVoip
        if not settings:
            settings = self.get_service_price_settings("NonVoipUsNumber")

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        if settings:
            price_percentage = settings.get('price_percentage', 0.0)
            credit_value = settings.get('credit_value', 1.0)
            logger.info(f"تطبيق النسبة المئوية {price_percentage}% على خدمة {service_name}")
        else:
            # استخدام النسبة الافتراضية من config.py
            if CONFIG_AVAILABLE:
                from config import Config
                price_percentage = Config.DEFAULT_NONVOIP_MARGIN_PERCENT
            else:
                price_percentage = 20.0  # النسبة الافتراضية 20%

            cursor.execute("SELECT value FROM settings WHERE key = 'credit_price'")
            credit_result = cursor.fetchone()
            credit_value = float(credit_result[0]) if credit_result else 1.0
            logger.info(f"لا توجد إعدادات مخصصة للخدمة {service_name}، استخدام النسبة الافتراضية {price_percentage}%")

        conn.close()

        # تطبيق النسبة المئوية من إدارة الأسعار
        price_with_margin = dollar_price * (1 + price_percentage / 100.0)
        credits_needed = price_with_margin / credit_value

        logger.info(f"حساب السعر: ${dollar_price} + {price_percentage}% = ${price_with_margin:.2f} = {credits_needed:.2f} كريديت")

        return round(credits_needed, 2)

    def get_statistics(self) -> Dict[str, Any]:
        """
        الحصول على الإحصائيات التفصيلية لمبيعات NonVoip

        Returns:
            قاموس يحتوي على الإحصائيات اليومية والأسبوعية والشهرية والكلية
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        from datetime import datetime, timedelta
        today = datetime.now().strftime('%Y-%m-%d')

        stats = {
            'daily': {'orders': 0, 'revenue': 0.0, 'cost': 0.0, 'profit': 0.0},
            'weekly': {'orders': 0, 'revenue': 0.0, 'cost': 0.0, 'profit': 0.0},
            'monthly': {'orders': 0, 'revenue': 0.0, 'cost': 0.0, 'profit': 0.0},
            'total': {'orders': 0, 'revenue': 0.0, 'cost': 0.0, 'profit': 0.0}
        }

        for stat_type in ['daily', 'weekly', 'monthly', 'total']:
            cursor.execute("""
                SELECT orders_count, total_revenue, total_cost
                FROM nonvoip_statistics
                WHERE stat_date = ? AND stat_type = ?
            """, (today, stat_type))

            row = cursor.fetchone()
            if row:
                stats[stat_type] = {
                    'orders': row[0] or 0,
                    'revenue': row[1] or 0.0,
                    'cost': row[2] or 0.0,
                    'profit': (row[1] or 0.0) - (row[2] or 0.0)
                }

        conn.close()
        return stats

    def refund_order_credits(self, order_id: int, user_id: int, refund_amount: float) -> bool:
        """
        استرجاع الرصيد للمستخدم عند عدم وصول SMS

        Args:
            order_id: معرف الطلب من API
            user_id: معرف المستخدم
            refund_amount: المبلغ المراد استرجاعه بالكريديت

        Returns:
            True عند النجاح
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE nonvoip_orders
                SET refunded = 1, status = 'refunded', updated_at = CURRENT_TIMESTAMP
                WHERE order_id = ?
            """, (order_id,))

            cursor.execute("""
                UPDATE users
                SET credits_balance = credits_balance + ?
                WHERE user_id = ?
            """, (refund_amount, user_id))

            conn.commit()
            logger.info(f"تم استرجاع {refund_amount} كريديت للمستخدم {user_id} للطلب {order_id}")
            
            # تسجيل الاسترجاع في nonvoip_purchase_logs
            import sys
            sys.path.insert(0, '/home/runner/workspace')
            from bot import update_purchase_refund
            update_purchase_refund(order_id, refund_amount)
            
            return True

        except Exception as e:
            logger.error(f"خطأ في استرجاع الرصيد: {e}")
            conn.rollback()
            return False

        finally:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# PART 3: HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_sale_price(cost_price: float, margin_percent: float = 20.0) -> float:
    """
    حساب سعر البيع بناءً على سعر التكلفة وهامش الربح

    Args:
        cost_price: سعر التكلفة بالدولار
        margin_percent: نسبة هامش الربح (افتراضي: 20%)

    Returns:
        سعر البيع بالدولار
    """
    sale_price = cost_price * (1 + margin_percent / 100.0)
    return round(sale_price, 2)


def format_expiration_time(seconds: int, lang: str = 'ar') -> str:
    """
    تحويل مدة الصلاحية من ثوانٍ إلى نص مفهوم

    Args:
        seconds: عدد الثواني
        lang: اللغة ('ar' أو 'en')

    Returns:
        نص منسق بالمدة
    """
    if seconds <= 0:
        return 'منتهي' if lang == 'ar' else 'Expired'

    # التحويل إلى وحدات مفهومة
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60

    if days > 0:
        if lang == 'ar':
            return f"{days} يوم" if days == 1 else f"{days} أيام"
        else:
            return f"{days} day" if days == 1 else f"{days} days"
    elif hours > 0:
        if lang == 'ar':
            return f"{hours} ساعة" if hours == 1 else f"{hours} ساعات"
        else:
            return f"{hours} hour" if hours == 1 else f"{hours} hours"
    else:
        return f"{minutes} min"


def should_show_cancel_button(order_type: str) -> bool:
    """
    تحديد ما إذا كان يجب عرض زر Cancel & Refund

    Args:
        order_type: نوع الرقم (short_term, long_term, 3days)

    Returns:
        True إذا كان يجب عرض الزر
    """
    # فقط الأرقام قصيرة الأمد (15 دقيقة) يمكن إلغاؤها
    # الزر يبقى موجوداً دائماً، لكن معالج الزر نفسه يتحقق من الوقت
    return order_type == 'short_term'


def build_cancel_refund_markup(order_id: int, lang: str = 'ar') -> InlineKeyboardMarkup:
    """
    إنشاء keyboard markup مع زر Cancel & Refund

    Args:
        order_id: معرف الطلب
        lang: اللغة

    Returns:
        InlineKeyboardMarkup مع الزر
    """
    cancel_keyboard = [[InlineKeyboardButton(
        "❌ إلغاء وإعادة الرصيد" if lang == "ar" else "❌ Cancel & Refund",
        callback_data=f"nv_cancel_order_{order_id}"
    )]]
    return InlineKeyboardMarkup(cancel_keyboard)


def format_activation_time(activated_until: str, lang: str = 'ar') -> str:
    """
    حساب الوقت المتبقي للتفعيل وعرضه بتوقيت سوريا
    
    Args:
        activated_until: وقت انتهاء التفعيل (UTC أو مع timezone)
        lang: اللغة
    
    Returns:
        نص منسق بالوقت المتبقي
    """
    import pytz
    from datetime import datetime
    from dateutil import parser
    
    try:
        # تحويل وقت انتهاء التفعيل إلى توقيت سوريا
        if not activated_until:
            return "غير نشط" if lang == 'ar' else "Inactive"
        
        # استخدام dateutil.parser لدعم صيغ متعددة
        end_time = parser.parse(activated_until)
        
        # إذا لم يكن له timezone، نعتبره UTC
        if end_time.tzinfo is None:
            end_time = pytz.utc.localize(end_time)
        
        # تحويل إلى توقيت سوريا
        syria_tz = pytz.timezone(Config.TIMEZONE)
        syria_time = end_time.astimezone(syria_tz)
        
        # حساب الوقت المتبقي
        now_syria = datetime.now(syria_tz)
        time_left = syria_time - now_syria
        
        if time_left.total_seconds() <= 0:
            return "منتهي" if lang == 'ar' else "Expired"
        
        minutes = int(time_left.total_seconds() // 60)
        seconds = int(time_left.total_seconds() % 60)
        
        if minutes > 0:
            return f"{minutes}د {seconds}ث" if lang == 'ar' else f"{minutes}m {seconds}s"
        else:
            return f"{seconds}ث" if lang == 'ar' else f"{seconds}s"
    except Exception as e:
        logger.error(f"خطأ في حساب وقت التفعيل: {e} - القيمة: {activated_until}")
        return "غير معروف" if lang == 'ar' else "Unknown"


def build_activate_button_markup(order_id: int, order_type: str, activation_status: str = 'inactive', 
                                  activated_until: str = None, lang: str = 'ar') -> InlineKeyboardMarkup:
    """
    إنشاء زر Active للأرقام طويلة المدى (3days و long_term)
    
    Args:
        order_id: معرف الطلب
        order_type: نوع الرقم
        activation_status: حالة التفعيل ('active' أو 'inactive')
        activated_until: وقت انتهاء التفعيل
        lang: اللغة
    
    Returns:
        InlineKeyboardMarkup مع زر Active
    """
    # فقط للأرقام طويلة المدى
    if order_type not in ['3days', 'long_term']:
        return build_cancel_refund_markup(order_id, lang)
    
    # تحديد نص الزر والإيموجي حسب حالة التفعيل
    if activation_status == 'active' and activated_until:
        # فحص ما إذا كان التفعيل منتهياً
        import pytz
        from datetime import datetime
        from dateutil import parser
        
        try:
            end_time = parser.parse(activated_until)
            if end_time.tzinfo is None:
                end_time = pytz.utc.localize(end_time)
            
            syria_tz = pytz.timezone(Config.TIMEZONE)
            now_syria = datetime.now(syria_tz)
            
            if end_time.astimezone(syria_tz) <= now_syria:
                # التفعيل منتهي
                button_text = "✔️ Activated (Expired)" if lang == 'en' else "✔️ مفعل (منتهي)"
            else:
                # التفعيل نشط
                time_left = format_activation_time(activated_until, lang)
                button_text = f"✅ Activated ({time_left})" if lang == 'en' else f"✅ مفعل ({time_left})"
        except:
            # في حالة خطأ في التحويل، افترض أنه منتهي
            button_text = "✔️ Activated (Expired)" if lang == 'en' else "✔️ مفعل (منتهي)"
    else:
        # غير مفعل
        button_text = "✔️ Active" if lang == 'en' else "✔️ تفعيل"
    
    keyboard = [[InlineKeyboardButton(
        button_text,
        callback_data=f"nv_activate_{order_id}"
    )]]
    
    return InlineKeyboardMarkup(keyboard)


def format_order_for_user(order_data: Dict, lang: str = 'ar') -> str:
    """
    تنسيق معلومات الطلب للعرض للمستخدم

    Args:
        order_data: بيانات الطلب من API
        lang: اللغة ('ar' أو 'en')

    Returns:
        نص منسق بمعلومات الطلب
    """
    # تنسيق مدة الصلاحية
    expiration_text = 'N/A'
    if order_data.get('expiration'):
        try:
            expiration_seconds = int(order_data['expiration'])
            expiration_text = format_expiration_time(expiration_seconds, lang)
        except (ValueError, TypeError):
            expiration_text = str(order_data.get('expiration', 'N/A'))

    if lang == 'ar':
        message = f"""
📱 *رقمك: * `{order_data.get('number', 'في انتظار التخصيص')}`
🏷️ *الخدمة: * {order_data.get('service', 'N/A')}
📊 *الحالة: * {order_data.get('status', 'N/A')}
⏱️ *النوع: * {order_data.get('type', 'N/A')}
⏰ *الصلاحية: * {expiration_text}
🆔 *معرف الطلب: * {order_data.get('order_id', 'N/A')}
"""
    else:
        message = f"""
📱 *Your Number: * `{order_data.get('number', 'Pending allocation')}`
🏷️ *Service: * {order_data.get('service', 'N/A')}
📊 *Status: * {order_data.get('status', 'N/A')}
⏱️ *Type: * {order_data.get('type', 'N/A')}
⏰ *Validity: * {expiration_text}
🆔 *Order ID: * {order_data.get('order_id', 'N/A')}
"""

    return message


def get_nonvoip_price() -> float:
    """الحصول على سعر Non-Voip من قاعدة البيانات"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'nonvoip_price'")
        result = cursor.fetchone()
        conn.close()
        if result and result[0]:
            return float(result[0])
    except Exception:
        pass
    return 1.0


def get_user_language(user_id: int, conn=None) -> str:
    """
    الحصول على لغة المستخدم من قاعدة البيانات
    
    Args:
        user_id: معرف المستخدم
        conn: اتصال قاعدة البيانات (اختياري - سيتم إنشاؤه تلقائياً إذا لم يُمرر)
    
    Returns:
        str: كود اللغة ('ar' أو 'en')
    """
    close_conn = False
    try:
        if conn is None:
            conn = sqlite3.connect(DATABASE_FILE)
            close_conn = True
        
        cursor = conn.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else 'en'
    except Exception as e:
        logger.debug(f"خطأ في الحصول على لغة المستخدم {user_id}: {e}")
        return 'ar'
    finally:
        if close_conn and conn:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# PART 4: BOT FUNCTIONS - CUSTOMER HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

NONVOIP_MESSAGES = {
    'ar': {
        'main_button': '📱 شراء أرقام',
        'menu_title': '📱 *قائمة شراء الأرقام*\n\nاختر ما تريد القيام به:',
        'request_new_number': '➕ طلب رقم جديد',
        'my_numbers': '📱 أرقامي',
        'history': '📜 السجل',
        'short_term': '⏱️ رقم قصير الأمد (15 دقيقة)',
        'long_term': '📅 رقم طويل الأمد (30 يوماً)',
        'three_days': '🗓️ رقم لثلاثة أيام',
        'usa_country': '🇺🇸 الولايات المتحدة',
        'select_state': '📍 اختر الولاية',
        'all_states': '🌎 جميع الولايات',
        'back': '🔙 رجوع',
        'select_service': '🏷️ *اختر الخدمة:*\n\nاختر الخدمة التي تريد استقبال SMS منها:',
        'loading_products': '⏳ جاري تحميل الخدمات المتاحة...',
        'no_products': '❌ لا توجد خدمات متاحة حالياً',
        'confirm_order': '✅ *تأكيد الطلب*\n\n🏷️ الخدمة: {service}\n💵 السعر: ${price}\n📊 متوفر: {available}\n\nهل تريد المتابعة؟',
        'yes': '✅ نعم، اشتري',
        'no': '❌ لا، إلغاء',
        'processing_order': '⏳ جاري معالجة طلبك...',
        'order_success': '✅ *تم شراء الرقم بنجاح!*\n\n',
        'order_failed': '❌ فشل شراء الرقم:\n{error}',
        'insufficient_balance': '❌ رصيدك غير كافٍ!\n\n💰 رصيدك الحالي: ${balance}\n💵 السعر المطلوب: ${price}\n\nيرجى شحن رصيدك أولاً.',
        'my_numbers_title': '📋 *أرقامك الحالية:*\n\n',
        'no_numbers': 'ليس لديك أرقام حالياً',
        'number_item': '📱 {number} - {service}\n📊 الحالة: {status}\n⏰ انتهى في: {expiry}\n\n',
        'check_sms': '📬 فحص الرسائل',
        'renew_number': '🔄 تجديد',
        'reject_number': '❌ رفض واسترداد',
        'admin_menu_title': '🛠️ *إدارة خدمة الأرقام*\n\nاختر العملية:',
        'view_balance': '💰 عرض الرصيد',
        'view_products': '📦 عرض المنتجات المتاحة',
        'view_all_orders': '📋 عرض جميع الطلبات',
        'number_settings': '⚙️ إعدادات الأرقام',
        'balance_info': '💰 *معلومات الرصيد*\n\n💵 الرصيد الحالي: ${balance}\n\n⚠️ تأكد من وجود رصيد كافٍ لتلبية طلبات الزبائن',
        'products_loading': '⏳ جاري تحميل المنتجات...',
        'products_list': '📦 *المنتجات المتاحة - {type}*\n\n',
        'product_item': '🏷️ {name}\n💵 السعر: ${price}\n📊 المتوفر: {available}\n\n',
        'all_orders_title': '📋 *جميع طلبات الأرقام*\n\nإجمالي: {count} طلب\n\n',
        'order_summary': '🆔 #{id} - {user_id}\n📱 {number}\n🏷️ {service}\n📊 {status}\n\n'
    },
    'en': {
        'main_button': '📱 Buy Numbers',
        'menu_title': '📱 *Buy Numbers Menu*\n\nChoose what you want to do:',
        'request_new_number': '➕ Request New Number',
        'my_numbers': '📱 My Numbers',
        'history': '📜 History',
        'short_term': '⏱️ Short-term Number (15 min)',
        'long_term': '📅 Long-term Number (30 days)',
        'three_days': '🗓️ Three Days Number',
        'usa_country': '🇺🇸 USA',
        'select_state': '📍 Select State',
        'all_states': '🌎 All States',
        'back': '🔙 Back',
        'select_service': '🏷️ *Select Service:*\n\nChoose the service to receive SMS from:',
        'loading_products': '⏳ Loading available services...',
        'no_products': '❌ No services available right now',
        'confirm_order': '✅ *Confirm Order*\n\n🏷️ Service: {service}\n💵 Price: ${price}\n📊 Available: {available}\n\nProceed?',
        'yes': '✅ Yes, Buy',
        'no': '❌ No, Cancel',
        'processing_order': '⏳ Processing your order...',
        'order_success': '✅ *Number Purchased Successfully!*\n\n',
        'order_failed': '❌ Purchase failed:\n{error}',
        'insufficient_balance': '❌ Insufficient balance!\n\n💰 Your balance: ${balance}\n💵 Required: ${price}\n\nPlease recharge first.',
        'my_numbers_title': '📋 *Your Current Numbers:*\n\n',
        'no_numbers': 'You have no numbers yet',
        'number_item': '📱 {number} - {service}\n📊 Status: {status}\n⏰ Expires: {expiry}\n\n',
        'check_sms': '📬 Check Messages',
        'renew_number': '🔄 Renew',
        'reject_number': '❌ Reject & Refund',
        'admin_menu_title': '🛠️ *Numbers Service Management*\n\nSelect operation:',
        'view_balance': '💰 View Balance',
        'view_products': '📦 View Available Products',
        'view_all_orders': '📋 View All Orders',
        'number_settings': '⚙️ Number Settings',
        'balance_info': '💰 *Balance Information*\n\n💵 Current Balance: ${balance}\n\n⚠️ Ensure sufficient balance for customer orders',
        'products_loading': '⏳ Loading products...',
        'products_list': '📦 *Available Products - {type}*\n\n',
        'product_item': '🏷️ {name}\n💵 Price: ${price}\n📊 Available: {available}\n\n',
        'all_orders_title': '📋 *All Number Orders*\n\nTotal: {count} orders\n\n',
        'order_summary': '🆔 #{id} - {user_id}\n📱 {number}\n🏷️ {service}\n📊 {status}\n\n'
    }
}


async def nonvoip_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, conn) -> int:
    """عرض القائمة الرئيسية لشراء الأرقام"""
    user_id = update.effective_user.id
    lang = get_user_language(user_id, conn)

    # فحص حالة خدمة NonVoip - الفحص مباشرة من قاعدة البيانات
    try:
        cursor = conn.execute("""
            SELECT is_enabled FROM service_status
            WHERE service_type = 'nonvoip' AND service_subtype = 'basic'
        """)
        result = cursor.fetchone()
        nonvoip_enabled = result[0] if result else True  # افتراضياً مفعّل
    except Exception as e:
        logger.warning(f"فشل فحص حالة NonVoip: {e}")
        nonvoip_enabled = True  # افتراضياً مفعّل

    if not nonvoip_enabled:
        error_msg = (
            "❌ *عذراً، خدمة الأرقام غير متاحة حالياً*\n\n"
            "🔧 الخدمة قيد الصيانة\n"
            "⏰ سنعود قريباً"
        ) if lang == 'ar' else (
            "❌ *Sorry, numbers service is currently unavailable*\n\n"
            "🔧 Service under maintenance\n"
            "⏰ We'll be back soon"
        )

        if update.callback_query:
            await update.callback_query.edit_message_text(
                error_msg,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                error_msg,
                parse_mode=ParseMode.MARKDOWN
            )
        return ConversationHandler.END

    # القائمة الرئيسية: طلب رقم جديد + أرقامي + السجل
    keyboard = [
        [InlineKeyboardButton(NONVOIP_MESSAGES[lang]['request_new_number'], callback_data='nv_request_new')],
        [InlineKeyboardButton(NONVOIP_MESSAGES[lang]['my_numbers'], callback_data='nv_my_numbers')],
        [InlineKeyboardButton(NONVOIP_MESSAGES[lang]['history'], callback_data='nv_history')],
        [InlineKeyboardButton(NONVOIP_MESSAGES[lang]['back'], callback_data='nv_exit_to_main')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    menu_message = NONVOIP_MESSAGES[lang]['menu_title']

    if update.callback_query:
        await update.callback_query.edit_message_text(
            menu_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            menu_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    return 'NONVOIP_SELECT_TYPE'


async def nonvoip_select_type(update: Update, context: ContextTypes.DEFAULT_TYPE, conn) -> int:
    """اختيار نوع الرقم وعرض الخدمات المتاحة عبر Inline Query"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    lang = get_user_language(user_id, conn)

    # التعامل مع "طلب رقم جديد" - عرض زر أميركا
    if query.data == 'nv_request_new':
        keyboard = [
            [InlineKeyboardButton(NONVOIP_MESSAGES[lang]['usa_country'], callback_data='nv_country_usa')],
            [InlineKeyboardButton(NONVOIP_MESSAGES[lang]['back'], callback_data='nv_back_menu')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        country_message = (
            "🌍 *اختر الدولة*\n\n"
            "📱 اختر الدولة التي تريد شراء رقم منها"
        ) if lang == 'ar' else (
            "🌍 *Select Country*\n\n"
            "📱 Choose the country you want to buy a number from"
        )

        await query.edit_message_text(
            country_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

        return 'NONVOIP_SELECT_TYPE'

    # التعامل مع اختيار الدولة (أميركا)
    if query.data == 'nv_country_usa':
        # عرض أنواع الأرقام للولايات المتحدة
        keyboard = [
            [InlineKeyboardButton(NONVOIP_MESSAGES[lang]['short_term'], callback_data='nv_type_short_term')],
            [InlineKeyboardButton(NONVOIP_MESSAGES[lang]['three_days'], callback_data='nv_type_3days')],
            [InlineKeyboardButton(NONVOIP_MESSAGES[lang]['long_term'], callback_data='nv_type_long_term')],
            [InlineKeyboardButton(NONVOIP_MESSAGES[lang]['back'], callback_data='nv_back_menu')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        types_message = (
            "🇺🇸 *الولايات المتحدة الأمريكية*\n\n"
            "📱 اختر نوع الرقم الذي تريده:"
        ) if lang == 'ar' else (
            "🇺🇸 *United States of America*\n\n"
            "📱 Choose the type of number you want:"
        )

        await query.edit_message_text(
            types_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

        return 'NONVOIP_SELECT_TYPE'

    # التعامل مع اختيار نوع الرقم - فتح Inline Query للبحث
    if query.data.startswith('nv_type_'):
        number_type = query.data.replace('nv_type_', '')
        context.user_data['selected_number_type'] = number_type

        # حفظ نوع الرقم لاستخدامه في Inline Query
        context.bot_data[f'user_{user_id}_number_type'] = number_type

        type_names = {
            'short_term': '⏱️ رقم قصير الأمد (15 دقيقة)' if lang == 'ar' else '⏱️ Short-term (15 min)',
            'long_term': '📅 رقم طويل الأمد (30 يوم)' if lang == 'ar' else '📅 Long-term (30 days)',
            '3days': '🗓️ رقم 3 أيام' if lang == 'ar' else '🗓️ Three Days'
        }

        if lang == 'ar':
            message_text = (
                f"🔍 *ابحث عن الخدمات*\n\n"
                f"🎯 النوع: {type_names.get(number_type, 'رقم')}\n\n"
                f"اضغط على زر \"🔍 ابحث\" أدناه، ثم اكتب اسم الخدمة:\n\n"
                f"📱 أمثلة للخدمات:\n"
                f"• WhatsApp\n"
                f"• Google\n"
                f"• Telegram\n"
                f"• Facebook\n"
                f"• Instagram\n\n"
                f"💡 مثال: whatsapp\n"
                f"💡 مثال: google\n\n"
                f"✨ ستظهر جميع الأرقام المتاحة مع صورها وأسعارها!"
            )
        else:
            message_text = (
                f"🔍 *Search Services*\n\n"
                f"🎯 Type: {type_names.get(number_type, 'Number')}\n\n"
                f"Click \"🔍 Search\" button below, then type the service name:\n\n"
                f"📱 Example services:\n"
                f"• WhatsApp\n"
                f"• Google\n"
                f"• Telegram\n"
                f"• Facebook\n"
                f"• Instagram\n\n"
                f"💡 Example: whatsapp\n"
                f"💡 Example: google\n\n"
                f"✨ All available numbers will show with images and prices!"
            )

        # زر لفتح Inline Query مع تصفية النوع
        keyboard = [
            [InlineKeyboardButton(
                f"🔍 {'ابحث عن خدمة' if lang == 'ar' else 'Search Service'}",
                switch_inline_query_current_chat=f"{number_type} "
            )],
            [InlineKeyboardButton(NONVOIP_MESSAGES[lang]['back'], callback_data='nv_country_usa')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

        return 'NONVOIP_SELECT_PRODUCT'

    return 'NONVOIP_SELECT_PRODUCT'


async def nonvoip_confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE, conn) -> int:
    """تأكيد طلب الرقم"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    lang = get_user_language(user_id, conn)

    product_id = query.data.replace('nv_prod_', '')
    product = context.user_data.get('available_products', {}).get(product_id)

    if not product:
        await query.edit_message_text("❌ خطأ: المنتج غير موجود")
        return ConversationHandler.END

    context.user_data['selected_product'] = product

    cursor = conn.execute("SELECT (COALESCE(credits_balance, 0) + COALESCE(referral_balance, 0)) as total_balance FROM users WHERE user_id = ?", (user_id,))
    user_balance_row = cursor.fetchone()
    user_balance = user_balance_row[0] if user_balance_row else 0.0

    db = NonVoipDB()
    dollar_price = float(product.get('price', 0))
    # استخدام NonVoipUsNumber العام لجميع الأرقام (يطبق النسبة من إدارة الأسعار)
    sale_price = db.calculate_service_price_in_credits(dollar_price, service_name='NonVoipUsNumber')

    if user_balance < sale_price:
        await query.edit_message_text(
            NONVOIP_MESSAGES[lang]['insufficient_balance'].format(
                balance=user_balance,
                price=sale_price
            ),
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(NONVOIP_MESSAGES[lang]['yes'], callback_data='nv_confirm_yes')],
        [InlineKeyboardButton(NONVOIP_MESSAGES[lang]['no'], callback_data='nv_confirm_no')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        NONVOIP_MESSAGES[lang]['confirm_order'].format(
            service=product['name'],
            price=sale_price,
            available=product['available']
        ),
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

    return 'NONVOIP_CONFIRM_ORDER'


async def nonvoip_process_order(update: Update, context: ContextTypes.DEFAULT_TYPE, conn) -> int:
    """معالجة طلب شراء الرقم"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    lang = get_user_language(user_id, conn)

    if query.data == 'nv_confirm_no':
        await query.edit_message_text("❌ تم إلغاء الطلب")
        return ConversationHandler.END

    product = context.user_data.get('selected_product')
    if not product:
        await query.edit_message_text("❌ خطأ: لم يتم العثور على المنتج")
        return ConversationHandler.END

    await query.edit_message_text(NONVOIP_MESSAGES[lang]['processing_order'])

    try:
        db = NonVoipDB()
        dollar_price = float(product.get('price', 0))
        # استخدام NonVoipUsNumber العام لجميع الأرقام (يطبق النسبة من إدارة الأسعار)
        sale_price = db.calculate_service_price_in_credits(dollar_price, service_name='NonVoipUsNumber')

        cursor = conn.execute("SELECT (COALESCE(credits_balance, 0) + COALESCE(referral_balance, 0)) as total_balance FROM users WHERE user_id = ?", (user_id,))
        current_balance_row = cursor.fetchone()
        current_balance = current_balance_row[0] if current_balance_row else 0.0

        if current_balance < sale_price:
            await query.edit_message_text(
                NONVOIP_MESSAGES[lang]['insufficient_balance'].format(
                    balance=current_balance,
                    price=sale_price
                ),
                parse_mode=ParseMode.MARKDOWN
            )
            return ConversationHandler.END

        api = NonVoipAPI()
        order_result = api.order(product_id=int(product['product_id']))

        if order_result.get('status') != 'success':
            error_msg = order_result.get('message', 'خطأ غير معروف')

            error_keywords = ['balance', 'insufficient', 'رصيد', 'غير كافي', 'funds', 'credit']
            is_balance_error = any(keyword in str(error_msg).lower() for keyword in error_keywords)

            if is_balance_error:
                admin_error_msg = (
                    "❌ *عذراً، حدث خطأ من طرفنا*\n\n"
                    "⚠️ لا يتوفر رصيد كافٍ في حساب الإدارة لإتمام هذا الطلب.\n"
                    "💬 يرجى التواصل مع الآدمن لمعالجة المشكلة.\n\n"
                    "🔄 سيتم حل المشكلة في أقرب وقت ممكن."
                ) if lang == 'ar' else (
                    "❌ *Sorry, an error occurred on our side*\n\n"
                    "⚠️ Insufficient balance in admin account to complete this order.\n"
                    "💬 Please contact admin to resolve this issue.\n\n"
                    "🔄 The issue will be resolved as soon as possible."
                )
                await query.edit_message_text(admin_error_msg, parse_mode=ParseMode.MARKDOWN)
                logger.error(f"رصيد الآدمن غير كافٍ في NonVoip: {error_msg}")
            else:
                await query.edit_message_text(
                    NONVOIP_MESSAGES[lang]['order_failed'].format(error=error_msg)
                )
            return ConversationHandler.END

        order_info = order_result['message'][0]
        cost_price = float(product['price'])

        # خصم من credits_balance أولاً، ثم من referral_balance إذا لزم الأمر
        cursor = conn.execute("SELECT COALESCE(credits_balance, 0), COALESCE(referral_balance, 0) FROM users WHERE user_id = ?", (user_id,))
        balances = cursor.fetchone()
        credits_bal = balances[0] if balances else 0.0
        referral_bal = balances[1] if balances else 0.0

        if credits_bal >= sale_price:
            # خصم من credits_balance فقط
            conn.execute("UPDATE users SET credits_balance = credits_balance - ? WHERE user_id = ?", (sale_price, user_id))
            deduction_desc = f"خصم {sale_price:.2f} من الرصيد المشحون"
        else:
            # خصم من credits_balance بالكامل ثم من referral_balance
            remaining = sale_price - credits_bal
            conn.execute("UPDATE users SET credits_balance = 0, referral_balance = referral_balance - ? WHERE user_id = ?", (remaining, user_id))
            deduction_desc = f"خصم {credits_bal:.2f} من الرصيد المشحون + {remaining:.2f} من رصيد الإحالات"
        conn.commit()
        
        # تسجيل المعاملة في credits_transactions
        service_name = product.get('name', 'NonVoIP')
        order_id_for_log = order_info.get('order_id', '')
        conn.execute("""
            INSERT INTO credits_transactions (user_id, transaction_type, amount, order_id, description)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, 'nonvoip_purchase', -sale_price, str(order_id_for_log), 
              f"شراء رقم {service_name} - {deduction_desc}"))
        conn.commit()
        logger.info(f"✅ تم تسجيل معاملة شراء NonVoIP للمستخدم {user_id}: -{sale_price} كريديت")

        db.save_order(
            user_id=user_id,
            order_data=order_info,
            cost_price=cost_price,
            sale_price=sale_price
        )
        
        # تسجيل عملية الشراء في nonvoip_purchase_logs
        import sys
        sys.path.insert(0, '/home/runner/workspace')
        from bot import log_nonvoip_purchase
        order_id = order_info.get('order_id')
        username = user.get('username', f'user_{user_id}')
        number_type = product.get('number_type', order_info.get('type', 'unknown'))
        service_type = product.get('name', order_info.get('service', 'unknown'))
        log_nonvoip_purchase(
            user_id=user_id,
            username=username,
            order_id=order_id,
            number_type=number_type,
            service_type=service_type,
            price_usd=sale_price,
            price_credits=credits_amount,
            credit_deducted=credits_amount,
            notes=f"Order: {order_id}"
        )

        success_message = NONVOIP_MESSAGES[lang]['order_success']
        success_message += format_order_for_user(order_info, lang)

        # الحصول على معرف الطلب والرقم
        number = order_info.get('number')
        service = order_info.get('service', product.get('name', ''))
        expiration_seconds = int(order_info.get('expiration', 900))

        # إضافة أزرار التحكم
        keyboard = []

        # زر التفاصيل
        keyboard.append([InlineKeyboardButton(
            "📊 تفاصيل الرقم" if lang == 'ar' else "📊 Details",
            callback_data=f"nv_manual_check_{order_id}"
        )])

        # زر Cancel & Refund للأرقام قصيرة الأمد أو زر Active للأرقام طويلة المدى
        order_type = order_info.get('type', 'short_term')
        if should_show_cancel_button(order_type):
            keyboard.append([InlineKeyboardButton(
                "❌ إلغاء وإعادة الرصيد" if lang == 'ar' else "❌ Cancel & Refund",
                callback_data=f"nv_cancel_order_{order_id}"
            )])
        elif order_type in ['3days', 'long_term']:
            # زر Active للأرقام طويلة المدى - يتغير حسب حالة التفعيل
            activation_status = order_info.get('activation_status', 'inactive')
            activated_until = order_info.get('activated_until')
            
            if activation_status == 'active' and activated_until:
                time_left = format_activation_time(activated_until, lang)
                button_text = f"✅ مفعل ({time_left})" if lang == 'ar' else f"✅ Activated ({time_left})"
            else:
                button_text = "✔️ تفعيل" if lang == 'ar' else "✔️ Active"
            
            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f"nv_activate_{order_id}"
            )])

        keyboard.append([InlineKeyboardButton(
            "🔙 العودة لأرقامي" if lang == 'ar' else "🔙 Back to My Numbers",
            callback_data='nv_my_numbers'
        )])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # الحصول على message_id قبل تحديث الرسالة
        message_id = query.message.message_id if query.message else None

        await query.edit_message_text(success_message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

        # حفظ message_id في قاعدة البيانات لتفعيل المراقبة التلقائية
        if message_id and order_id:
            db.set_order_message_id(order_id, message_id)
            logger.info(f"✅ تم حفظ message_id={message_id} للطلب {order_id}")
        else:
            logger.warning(f"⚠️ لم يتم الحصول على message_id للطلب {order_id}")

        logger.info(f"تم شراء رقم للمستخدم {user_id}: {order_info.get('number', 'N/A')} - خصم {sale_price} كريديت")

        # تفعيل تلقائي للأرقام طويلة المدى (3days & long_term) لمرة واحدة
        if order_type in ['3days', 'long_term']:
            try:
                activation_result = db.auto_activate_number_on_purchase(
                    order_id=order_id,
                    service=service,
                    number=number
                )
                if activation_result.get('status') == 'success':
                    activated_msg = (
                        f"\n\n🔥 *تم التفعيل التلقائي!*\n"
                        f"✅ الرقم جاهز الآن لاستقبال الرسائل\n"
                        f"⏱️ مدة التفعيل: 10 دقائق\n\n"
                        f"⚠️ *ملاحظة:* الأرقام طويلة المدى لا تستقبل رسائل قبل التفعيل."
                    ) if lang == 'ar' else (
                        f"\n\n🔥 *Auto-Activated!*\n"
                        f"✅ Number is now ready to receive messages\n"
                        f"⏱️ Activation duration: 10 minutes\n\n"
                        f"⚠️ *Note:* Long-term numbers don't receive messages before activation."
                    )
                    
                    # تحديث الرسالة بإضافة معلومات التفعيل
                    updated_message = success_message + activated_msg
                    await query.edit_message_text(updated_message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
                    
                    logger.info(f"✅ تم التفعيل التلقائي للطلب {order_id}")
            except Exception as e:
                logger.error(f"خطأ في التفعيل التلقائي للطلب {order_id}: {e}")

        # بدء مراقبة الرقم تلقائياً فقط إذا كان لدينا message_id
        if message_id:
            asyncio.create_task(monitor_order_for_sms(
                application=context.application,
                user_id=user_id,
                order_id=order_id,
                service=service,
                number=number,
                message_id=message_id,
                expiration_seconds=expiration_seconds,
                lang=lang
            ))
            logger.info(f"🔄 بدء المراقبة التلقائية للطلب {order_id}")
        else:
            logger.warning(f"لم يتم الحصول على message_id للطلب {order_id} - المراقبة التلقائية غير نشطة")

        return ConversationHandler.END

    except Exception as e:
        logger.error(f"خطأ في معالجة طلب الرقم: {e}")
        error_message = (
            "❌ *عذراً، حدث خطأ غير متوقع*\n\n"
            "💬 يرجى المحاولة لاحقاً أو التواصل مع الآدمن.\n"
            f"🔍 التفاصيل: {str(e)}"
        ) if lang == 'ar' else (
            "❌ *Sorry, an unexpected error occurred*\n\n"
            "💬 Please try again later or contact admin.\n"
            f"🔍 Details: {str(e)}"
        )
        await query.edit_message_text(error_message, parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END


async def nonvoip_my_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE, conn) -> int:
    """عرض أرقام المستخدم النشطة كأزرار تفاعلية (تصفية الأرقام المنتهية)"""
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id
    lang = get_user_language(user_id, conn)

    db = NonVoipDB()
    # استخدام get_current_orders بدلاً من get_active_orders لتصفية الأرقام المنتهية
    orders = db.get_current_orders(user_id=user_id)

    if not orders:
        message = (
            "📱 *أرقامي النشطة*\n\n"
            "❌ لا توجد أرقام نشطة حالياً\n\n"
            "💡 الأرقام المنتهية الصلاحية لا تظهر هنا"
        ) if lang == 'ar' else (
            "📱 *My Active Numbers*\n\n"
            "❌ No active numbers currently\n\n"
            "💡 Expired numbers are not shown here"
        )

        # إضافة زر Sync
        keyboard = []
        keyboard.append([InlineKeyboardButton(
            "🔄 مزامنة" if lang == 'ar' else "🔄 Sync",
            callback_data='nv_sync_numbers'
        )])
        keyboard.append([InlineKeyboardButton(
            NONVOIP_MESSAGES[lang]['back'],
            callback_data='nv_back_menu'
        )])
        reply_markup = InlineKeyboardMarkup(keyboard)

        if query:
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

    # إنشاء أزرار للأرقام النشطة
    keyboard = []

    message = (
        f"📱 *أرقامي النشطة*\n\n"
        f"📊 عدد الأرقام: {len(orders)}\n\n"
        f"✅ يعرض فقط الأرقام التي لم تنته صلاحيتها\n\n"
        f"اختر رقماً لعرض الرسائل:"
    ) if lang == 'ar' else (
        f"📱 *My Active Numbers*\n\n"
        f"📊 Count: {len(orders)}\n\n"
        f"✅ Showing only non-expired numbers\n\n"
        f"Select a number to view messages:"
    )

    for order in orders[:10]:  # عرض أول 10 أرقام
        number = order.get('number', 'N/A')
        service = order.get('service', 'N/A')
        order_id = order.get('order_id', 0)
        expires_at = order.get('expires_at')

        # الحصول على الاسم المعروض
        display_service = get_display_service_name(service)
        icon = get_service_icon(service)

        # إضافة معلومات الانتهاء إذا كانت متاحة
        button_text = f"{icon} {number} - {display_service}"

        # إضافة وقت الانتهاء للأرقام قصيرة الأمد
        if order.get('type') == 'short_term' and expires_at:
            from datetime import datetime
            try:
                expires_dt = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
                time_left = expires_dt - datetime.now()
                if time_left.total_seconds() > 0:
                    minutes_left = int(time_left.total_seconds() // 60)
                    button_text += f" ({minutes_left}m)"
            except:
                pass

        keyboard.append([InlineKeyboardButton(
            button_text,
            callback_data=f"nv_view_messages_{order_id}"
        )])

    # زر المزامنة
    keyboard.append([InlineKeyboardButton(
        "🔄 مزامنة" if lang == 'ar' else "🔄 Sync",
        callback_data='nv_sync_numbers'
    )])

    # زر الرجوع
    keyboard.append([InlineKeyboardButton(
        NONVOIP_MESSAGES[lang]['back'],
        callback_data='nv_back_menu'
    )])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    return ConversationHandler.END


async def nonvoip_sync_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE, conn) -> int:
    """
    مزامنة الأرقام - تحديث البيانات من API وفحص الرسائل الواردة
    """
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    lang = get_user_language(user_id, conn)

    await query.edit_message_text(
        "🔄 *جاري المزامنة...*\n\n⏳ يتم تحديث البيانات من الخادم" if lang == 'ar'
        else "🔄 *Syncing...*\n\n⏳ Updating data from server",
        parse_mode=ParseMode.MARKDOWN
    )

    try:
        db = NonVoipDB()
        api = NonVoipAPI()

        # جلب جميع الطلبات للمستخدم (بما فيها المنتهية)
        orders = db.get_active_orders(user_id=user_id)

        synced_count = 0
        messages_found = 0
        errors = 0
        new_messages = []  # قائمة لتخزين الرسائل الجديدة

        for order in orders:
            try:
                order_id = order.get('order_id')
                service = order.get('service')
                number = order.get('number')
                sms_received = order.get('sms_received')

                if not service or not number:
                    continue

                # فحص الرسائل الواردة فقط إذا لم تصل رسالة بعد
                if not sms_received:
                    result = api.get_sms(service=service, number=number, order_id=order_id)

                    if result.get('status') == 'success' and result.get('sms'):
                        sms_text = result.get('sms')
                        pin_code = result.get('pin')

                        # تحديث قاعدة البيانات
                        db.update_order_sms(order_id=order_id, sms=sms_text, pin=pin_code)
                        
                        # حفظ الرسالة في جدول الرسائل (لعرض آخر 3 رسائل)
                        db.save_message(order_id=order_id, user_id=user_id, message_text=sms_text, pin_code=pin_code)
                        
                        # تحديث sms_sent في قاعدة البيانات
                        try:
                            conn_db = db._get_connection()
                            cursor = conn_db.cursor()
                            cursor.execute("""
                                UPDATE nonvoip_orders 
                                SET sms_sent = 1, updated_at = CURRENT_TIMESTAMP
                                WHERE order_id = ?
                            """, (order_id,))
                            conn_db.commit()
                            conn_db.close()
                        except Exception as e:
                            logger.error(f"خطأ في تحديث sms_sent للطلب {order_id}: {e}")

                        # تخزين الرسالة الجديدة لإرسالها لاحقاً
                        icon = get_service_icon(service)
                        display_service = get_display_service_name(service)
                        
                        # الحصول على تاريخ الرسالة إن وجد
                        msg_time = result.get('time', result.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                        
                        new_messages.append({
                            'number': number,
                            'service': display_service,
                            'icon': icon,
                            'message': sms_text,
                            'pin': pin_code,
                            'time': msg_time
                        })

                        messages_found += 1

                synced_count += 1

            except Exception as e:
                logger.error(f"خطأ في مزامنة الطلب {order.get('order_id')}: {e}")
                errors += 1
                continue

        # رسالة النتيجة
        result_message = (
            f"✅ *تمت المزامنة بنجاح!*\n\n"
            f"📊 *الإحصائيات:*\n"
            f"🔄 تم فحص: {synced_count} رقم\n"
            f"📬 رسائل جديدة: {messages_found}\n"
            + (f"⚠️ أخطاء: {errors}\n" if errors > 0 else "")
            + f"\n⏰ آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ) if lang == 'ar' else (
            f"✅ *Sync Completed!*\n\n"
            f"📊 *Statistics:*\n"
            f"🔄 Checked: {synced_count} number(s)\n"
            f"📬 New messages: {messages_found}\n"
            + (f"⚠️ Errors: {errors}\n" if errors > 0 else "")
            + f"\n⏰ Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # أزرار العودة
        keyboard = [
            [InlineKeyboardButton(
                "📱 أرقامي" if lang == 'ar' else "📱 My Numbers",
                callback_data='nv_my_numbers'
            )],
            [InlineKeyboardButton(
                NONVOIP_MESSAGES[lang]['back'],
                callback_data='nv_back_menu'
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            result_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

        # إرسال كل رسالة جديدة في رسالة منفصلة بعد الإحصائيات
        for msg_data in new_messages:
            notify_message = (
                f"📨 *رسالة جديدة*\n\n"
                f"{msg_data['icon']} *الخدمة:* {msg_data['service']}\n"
                f"📱 *الرقم:* `{msg_data['number']}`\n"
                f"⏰ *التاريخ:* {msg_data['time']}\n"
                f"💬 *الرسالة:* `{msg_data['message']}`\n"
                + (f"🔐 *رمز التحقق:* `{msg_data['pin']}`" if msg_data['pin'] else "")
            ) if lang == 'ar' else (
                f"📨 *New Message*\n\n"
                f"{msg_data['icon']} *Service:* {msg_data['service']}\n"
                f"📱 *Number:* `{msg_data['number']}`\n"
                f"⏰ *Date:* {msg_data['time']}\n"
                f"💬 *Message:* `{msg_data['message']}`\n"
                + (f"🔐 *Code:* `{msg_data['pin']}`" if msg_data['pin'] else "")
            )
            
            await context.bot.send_message(
                chat_id=user_id,
                text=notify_message,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # تأخير بسيط لتجنب تجاوز حدود Telegram
            await asyncio.sleep(0.1)

        logger.info(f"✅ تمت مزامنة {synced_count} طلب للمستخدم {user_id} - رسائل جديدة: {messages_found}")
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"خطأ في المزامنة: {e}")

        error_message = (
            f"❌ *حدث خطأ في المزامنة*\n\n"
            f"🔍 التفاصيل: {str(e)}\n\n"
            f"💡 يرجى المحاولة مرة أخرى"
        ) if lang == 'ar' else (
            f"❌ *Sync Error*\n\n"
            f"🔍 Details: {str(e)}\n\n"
            f"💡 Please try again"
        )

        await query.edit_message_text(error_message, parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END


async def nonvoip_view_number_messages(update: Update, context: ContextTypes.DEFAULT_TYPE, conn) -> int:
    """عرض الرسائل التي وصلت لرقم معين"""
    query = update.callback_query
    
    user_id = update.effective_user.id
    
    # استخراج order_id
    order_id = int(query.data.replace('nv_view_messages_', ''))
    logger.info(f"🔍 دخول دالة nonvoip_view_number_messages - order_id: {order_id}, user_id: {user_id}")
    
    await query.answer()
    
    lang = get_user_language(user_id, conn)

    db = NonVoipDB()

    # جلب معلومات الطلب
    try:
        order_info = db.fetch_one("""
            SELECT number, service, created_at, type, activation_status, activated_until
            FROM nonvoip_orders
            WHERE order_id = ? AND user_id = ?
        """, (order_id, user_id))

        if not order_info:
            await query.edit_message_text("❌ خطأ: الرقم غير موجود")
            return ConversationHandler.END

        number = order_info[0]
        service = order_info[1]
        order_type = order_info[3] if len(order_info) > 3 else 'short_term'
        activation_status = order_info[4] if len(order_info) > 4 else 'inactive'
        activated_until = order_info[5] if len(order_info) > 5 else None

        # الحصول على الاسم المعروض
        display_service = get_display_service_name(service)
        icon = get_service_icon(service)

        await query.edit_message_text(
            "⏳ جاري جلب الرسائل..." if lang == 'ar' else "⏳ Fetching messages..."
        )

        # جلب الرسائل من API
        api = NonVoipAPI()
        messages_result = api.get_sms(service=service, number=number)

        if messages_result.get('status') != 'success':
            message = (
                f"{icon} *{display_service}*\n"
                f"📱 الرقم: `{number}`\n\n"
                f"📭 لم تصل أي رسائل بعد\n\n"
                f"⏳ الرسائل ستظهر هنا تلقائياً عند وصولها"
            ) if lang == 'ar' else (
                f"{icon} *{display_service}*\n"
                f"📱 Number: `{number}`\n\n"
                f"📭 No messages received yet\n\n"
                f"⏳ Messages will appear here automatically when received"
            )
        else:
            # عرض الرسائل
            messages_data = messages_result.get('message', [])
            
            # حفظ الرسالة في قاعدة البيانات إذا كانت جديدة
            if messages_result.get('sms'):
                sms_text = messages_result.get('sms')
                pin_code = messages_result.get('pin')
                db.save_message(order_id=order_id, user_id=user_id, message_text=sms_text, pin_code=pin_code)
                logger.info(f"✅ تم حفظ رسالة جديدة للطلب {order_id}")

            if not messages_data or len(messages_data) == 0:
                message = (
                    f"{icon} *{display_service}*\n"
                    f"📱 الرقم: `{number}`\n\n"
                    f"📭 لم تصل أي رسائل بعد"
                ) if lang == 'ar' else (
                    f"{icon} *{display_service}*\n"
                    f"📱 Number: `{number}`\n\n"
                    f"📭 No messages received yet"
                )
            else:
                message = (
                    f"{icon} *{display_service}*\n"
                    f"📱 الرقم: `{number}`\n\n"
                    f"📬 *الرسائل الواردة:*\n\n"
                ) if lang == 'ar' else (
                    f"{icon} *{display_service}*\n"
                    f"📱 Number: `{number}`\n\n"
                    f"📬 *Received Messages:*\n\n"
                )

                for idx, msg in enumerate(messages_data, 1):
                    msg_text = msg.get('message', msg.get('text', 'N/A'))
                    msg_time = msg.get('time', msg.get('created_at', ''))

                    message += f"{idx}. 💬 `{msg_text}`\n"
                    if msg_time:
                        message += f"   ⏰ {msg_time}\n"
                    message += "\n"

        # الأزرار
        keyboard = []

        # صف واحد: مزامنة الرسالة الأخيرة + تفاصيل
        keyboard.append([
            InlineKeyboardButton(
                "🔄 مزامنة آخر 3 رسائل" if lang == 'ar' else "🔄 Sync Last 3 Messages",
                callback_data=f"nv_sync_last3_{order_id}"
            ),
            InlineKeyboardButton(
                "📊 تفاصيل" if lang == 'ar' else "📊 Details",
                callback_data=f"nv_manual_check_{order_id}"
            )
        ])

        # إضافة زر Cancel & Refund للأرقام قصيرة الأمد أو زر Active للأرقام طويلة المدى
        if should_show_cancel_button(order_type):
            keyboard.append([InlineKeyboardButton(
                "❌ إلغاء وإعادة الرصيد" if lang == 'ar' else "❌ Cancel & Refund",
                callback_data=f"nv_cancel_order_{order_id}"
            )])
        elif order_type in ['3days', 'long_term']:
            # زر Active للأرقام طويلة المدى - يتغير حسب حالة التفعيل
            if activation_status == 'active' and activated_until:
                time_left = format_activation_time(activated_until, lang)
                button_text = f"✅ مفعل ({time_left})" if lang == 'ar' else f"✅ Activated ({time_left})"
            else:
                button_text = "✔️ تفعيل" if lang == 'ar' else "✔️ Active"
            
            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f"nv_activate_{order_id}"
            )])

        keyboard.append([InlineKeyboardButton(
            "🔙 العودة لأرقامي" if lang == 'ar' else "🔙 Back to My Numbers",
            callback_data='nv_my_numbers'
        )])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

        return ConversationHandler.END

    except Exception as e:
        logger.error(f"خطأ في عرض رسائل الرقم: {e}")
        await query.edit_message_text(f"❌ حدث خطأ: {str(e)}")
        return ConversationHandler.END


def get_renewable_numbers(user_id: int, db: 'NonVoipDB', limit: int = 5) -> list:
    """
    تحديد الأرقام القابلة للتجديد بالتحقق من API والقاعدة المحلية

    قواعد التجديد:
    - short_term: يمكن إعادة استخدامه (reuse) خلال 24 ساعة من الانتهاء
    - long_term/3days: يمكن تجديده (renew) خلال 7 أيام فقط من الانتهاء أو قبل الانتهاء
    - لم يتم تجديده مسبقاً (renewed=0)
    - لم يتم استرداده (refunded=0)
    - لديه رقم فعلي (number IS NOT NULL)
    """
    now = datetime.now()
    renewable_numbers = []
    api = NonVoipAPI()

    try:
        # جلب الأرقام المحتملة للتجديد من القاعدة المحلية
        # شروط الظهور في History:
        # 1. للأرقام short_term (15 دقيقة): فقط إذا استقبلت رسالة
        # 2. للأرقام الأخرى (long_term/3days): إذا انتهت الصلاحية
        # 3. لم يتم استردادها (refunded = 0)
        # 4. لديها رقم فعلي
        # ملاحظة: تم إزالة شرط renewed = 0 للسماح بالتجديد المتكرر
        all_orders = db.fetch_all("""
            SELECT order_id, number, service, status, expires_at, created_at, type, sale_price, renewed, sms_sent, sms_received
            FROM nonvoip_orders
            WHERE user_id = ?
            AND refunded = 0
            AND number IS NOT NULL
            AND number != ''
            AND (
                (type = 'short_term' AND (sms_sent = 1 OR sms_received IS NOT NULL))
                OR (type != 'short_term' AND expires_at IS NOT NULL AND datetime(expires_at) < datetime('now'))
            )
            ORDER BY created_at DESC
            LIMIT 50
        """, (user_id,))

        for order in all_orders:
            if len(renewable_numbers) >= limit:
                break

            order_id, number, service, status, expires_at, created_at, order_type, sale_price, renewed, sms_sent, sms_received = order

            if not expires_at or not order_type:
                continue

            # التحقق من الرسائل من API
            try:
                sms_result = api.get_sms(service=service, number=number, order_id=order_id)
                if sms_result.get('status') == 'success' and sms_result.get('sms'):
                    # تحديث الرسالة في القاعدة المحلية
                    sms_text = sms_result.get('sms')
                    pin_code = sms_result.get('pin')
                    db.update_order_sms(order_id=order_id, sms=sms_text, pin=pin_code)
                    sms_sent = True
            except Exception as e:
                logger.error(f"خطأ في التحقق من الرسائل للطلب {order_id}: {e}")

            try:
                expires_dt = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
            except:
                continue

            time_since_expiry = (now - expires_dt).total_seconds()

            # قواعد التجديد حسب النوع
            is_renewable = False
            renewal_type = None
            renewal_price = 0

            if order_type == 'short_term':
                # ✅ أرقام 15 دقيقة:
                # - عند وصول رسالة → ينتقل فوراً إلى History (بغض النظر عن الوقت)
                # - فقط الأرقام التي استقبلت رسالة تظهر في History وتكون قابلة للتجديد
                if sms_sent or sms_received:
                    # استقبل رسالة → يظهر في History ويكون قابل للتجديد
                    is_renewable = True
                    renewal_type = 'reuse'
                    renewal_price = calculate_renewal_price(sale_price, order_type)
                    logger.debug(f"✅ الرقم {order_id} قابل للتجديد - short_term استقبل رسالة (sms_sent={sms_sent}, sms_received={bool(sms_received)})")
            else:
                # الأرقام طويلة الأمد و3 أيام: قابلة للتجديد خلال 7 أيام فقط
                if -86400 <= time_since_expiry <= 604800:
                    is_renewable = True
                    renewal_type = 'renew'
                    renewal_price = calculate_renewal_price(sale_price, order_type)

            # إضافة الرقم إلى History إذا كان قابلاً للتجديد أو للعرض فقط
            if is_renewable or renewal_type == 'view_only':
                renewable_numbers.append({
                    'order_id': order_id,
                    'number': number,
                    'service': service,
                    'renewal_type': renewal_type,
                    'order_type': order_type,
                    'renewal_price': renewal_price,
                    'expires_at': expires_at,
                    'sms_sent': sms_sent
                })

    except Exception as e:
        logger.error(f"خطأ في تحديد الأرقام القابلة للتجديد: {e}")

    return renewable_numbers


def cleanup_old_history_numbers(user_id: int, db: 'NonVoipDB', keep_last: int = 5):
    """
    حذف الأرقام الأقدم من History والاحتفاظ بآخر N أرقام فقط
    
    Args:
        user_id: معرف المستخدم
        db: كائن قاعدة البيانات
        keep_last: عدد الأرقام المراد الاحتفاظ بها (افتراضي: 5)
    """
    try:
        # جلب جميع الأرقام المخفية من My Numbers (الموجودة في History فقط)
        # مرتبة حسب التاريخ (الأحدث أولاً)
        all_history_orders = db.fetch_all("""
            SELECT order_id, created_at
            FROM nonvoip_orders
            WHERE user_id = ?
            AND visible_in_my_numbers = 0
            AND number IS NOT NULL
            AND number != ''
            ORDER BY created_at DESC
        """, (user_id,))
        
        # إذا كان عدد الأرقام أكثر من الحد المسموح، احذف الأقدم
        if len(all_history_orders) > keep_last:
            # الاحتفاظ بالـ N الأحدث وحذف الباقي
            orders_to_delete = all_history_orders[keep_last:]
            
            for order in orders_to_delete:
                order_id = order[0]
                # حذف الرقم نهائياً من قاعدة البيانات
                db.execute("""
                    DELETE FROM nonvoip_orders
                    WHERE order_id = ?
                """, (order_id,))
                logger.info(f"🗑️ تم حذف الرقم القديم {order_id} من History (الاحتفاظ بآخر {keep_last} فقط)")
            
            logger.info(f"✅ تم حذف {len(orders_to_delete)} رقم قديم للمستخدم {user_id} من History")
    
    except Exception as e:
        logger.error(f"خطأ في تنظيف History القديم: {e}")


async def nonvoip_history(update: Update, context: ContextTypes.DEFAULT_TYPE, conn) -> int:
    """عرض سجل آخر 5 أرقام قابلة للتجديد (بدون استدعاء API)"""
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id
    lang = get_user_language(user_id, conn)

    db = NonVoipDB()
    
    # ✅ تنظيف History: حذف الأرقام الأقدم والاحتفاظ بآخر 5 فقط
    cleanup_old_history_numbers(user_id, db, keep_last=5)

    # جلب الأرقام القابلة للتجديد من قاعدة البيانات المحلية
    renewable_numbers = get_renewable_numbers(user_id, db, limit=5)

    if not renewable_numbers:
        message = (
            "📜 *السجل*\n\n"
            "ℹ️ لا توجد أرقام قابلة للتجديد حالياً\n\n"
            "💡 الأرقام القابلة للتجديد:\n"
            "• Short-term: خلال 24 ساعة من الانتهاء\n"
            "• Long-term/3days: خلال 30 يوم من الانتهاء"
        ) if lang == 'ar' else (
            "📜 *History*\n\n"
            "ℹ️ No renewable numbers available now\n\n"
            "💡 Renewable numbers:\n"
            "• Short-term: within 24 hours of expiry\n"
            "• Long-term/3days: within 30 days of expiry"
        )

        keyboard = [[InlineKeyboardButton(
            NONVOIP_MESSAGES[lang]['back'],
            callback_data='nv_back_menu'
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if query:
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

    # عرض الأرقام القابلة للتجديد في أزرار
    keyboard = []

    for idx, num_info in enumerate(renewable_numbers[:5], 1):
        number = num_info['number']
        service = num_info['service']
        renewal_type = num_info['renewal_type']
        renewal_price = num_info['renewal_price']

        # تحديد الأيقونة حسب نوع التجديد
        price_icon = "🆓" if renewal_type == 'reuse' else f"💰 {renewal_price:.2f}"

        button_text = f"📱 {number} - {service} ({price_icon})"

        keyboard.append([InlineKeyboardButton(
            button_text,
            callback_data=f"nv_renew_{num_info['order_id']}"
        )])

    # زر رجوع
    keyboard.append([InlineKeyboardButton(
        NONVOIP_MESSAGES[lang]['back'],
        callback_data='nv_back_menu'
    )])

    reply_markup = InlineKeyboardMarkup(keyboard)

    history_message = (
        "📜 *السجل - أرقام قابلة للتجديد*\n\n"
        f"📊 عدد الأرقام: {len(renewable_numbers)}\n\n"
        "💰 التكلفة:\n"
        "• Short-term: نصف السعر 💰\n"
        "• Long-term/3days: نفس السعر الأصلي 💰\n\n"
        "اختر رقماً لتجديده:"
    ) if lang == 'ar' else (
        "📜 *History - Renewable Numbers*\n\n"
        f"📊 Count: {len(renewable_numbers)}\n\n"
        "💰 Cost:\n"
        "• Short-term: Half price 💰\n"
        "• Long-term/3days: Same as original price 💰\n\n"
        "Select a number to renew:"
    )

    if query:
        await query.edit_message_text(
            history_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            history_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    return 'NONVOIP_HISTORY'


async def nonvoip_renew_number(update: Update, context: ContextTypes.DEFAULT_TYPE, conn) -> int:
    """تجديد رقم من السجل مع التحققات الكاملة"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    lang = get_user_language(user_id, conn)

    # استخراج order_id
    order_id = int(query.data.replace('nv_renew_', ''))

    db = NonVoipDB()

    # جلب معلومات الطلب مع جميع الحقول المطلوبة
    try:
        order_info = db.fetch_one("""
            SELECT number, service, sale_price, type, refunded, renewed, expires_at, status, user_id
            FROM nonvoip_orders
            WHERE order_id = ?
        """, (order_id,))

        if not order_info:
            await query.edit_message_text(
                "❌ خطأ: الرقم غير موجود" if lang == 'ar' else "❌ Error: Number not found"
            )
            return ConversationHandler.END

        number, service, sale_price, order_type, refunded, renewed, expires_at, status, order_user_id = order_info

        # التحقق من الملكية
        if order_user_id != user_id:
            await query.edit_message_text(
                "❌ هذا الرقم لا ينتمي لك" if lang == 'ar' else "❌ This number doesn't belong to you"
            )
            return ConversationHandler.END

        # التحقق من عدم الاسترداد
        if refunded:
            await query.edit_message_text(
                "❌ لا يمكن تجديد رقم تم استرداد ثمنه" if lang == 'ar' else "❌ Cannot renew a refunded number"
            )
            return ConversationHandler.END

        # السماح بالتجديد المتكرر - تم إزالة التحقق من التجديد المسبق

        # التحقق من وجود الرقم
        if not number or number == '':
            await query.edit_message_text(
                "❌ رقم غير صالح" if lang == 'ar' else "❌ Invalid number"
            )
            return ConversationHandler.END

        # التحقق من قابلية التجديد حسب النوع والوقت
        if not expires_at:
            await query.edit_message_text(
                "❌ لا يمكن تحديد صلاحية الرقم" if lang == 'ar' else "❌ Cannot determine number expiry"
            )
            return ConversationHandler.END

        try:
            expires_dt = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
            now = datetime.now()
            time_since_expiry = (now - expires_dt).total_seconds()
        except:
            await query.edit_message_text(
                "❌ خطأ في تاريخ الانتهاء" if lang == 'ar' else "❌ Invalid expiry date"
            )
            return ConversationHandler.END

        # التحقق من النافذة الزمنية للتجديد
        is_renewable = False
        renewal_type = None
        renewal_price = 0

        if order_type == 'short_term':
            # short_term: قابل لإعادة الاستخدام في أي وقت بعد استقبال رسالة (بنصف السعر)
            is_renewable = True
            renewal_type = 'reuse'
            renewal_price = calculate_renewal_price(sale_price, order_type)
        else:
            # long_term/3days: قابل للتجديد خلال 7 أيام فقط من الانتهاء (بنفس السعر الأصلي)
            if -86400 <= time_since_expiry <= 604800:
                is_renewable = True
                renewal_type = 'renew'
                renewal_price = calculate_renewal_price(sale_price, order_type)

        if not is_renewable:
            if order_type == 'short_term':
                msg = (
                    "❌ لا يمكن تجديد هذا الرقم\n\n"
                    "⏰ يمكن تجديد الأرقام قصيرة الأمد خلال 24 ساعة فقط من الانتهاء"
                ) if lang == 'ar' else (
                    "❌ Cannot renew this number\n\n"
                    "⏰ Short-term numbers can only be renewed within 24 hours of expiry"
                )
            else:
                msg = (
                    "❌ لا يمكن تجديد هذا الرقم\n\n"
                    "⏰ يمكن تجديد الأرقام طويلة الأمد خلال أسبوع فقط من الانتهاء"
                ) if lang == 'ar' else (
                    "❌ Cannot renew this number\n\n"
                    "⏰ Long-term numbers can only be renewed within 7 days of expiry"
                )
            await query.edit_message_text(msg)
            return ConversationHandler.END

        # التحقق من رصيد المستخدم
        cursor = conn.execute(
            "SELECT (COALESCE(credits_balance, 0) + COALESCE(referral_balance, 0)) as total_balance FROM users WHERE user_id = ?",
            (user_id,)
        )
        user_balance_row = cursor.fetchone()
        user_balance = user_balance_row[0] if user_balance_row else 0.0

        if user_balance < renewal_price:
            await query.edit_message_text(
                NONVOIP_MESSAGES[lang]['insufficient_balance'].format(
                    balance=user_balance,
                    price=renewal_price
                ),
                parse_mode=ParseMode.MARKDOWN
            )
            return ConversationHandler.END

        # عرض تأكيد التجديد
        if order_type == 'short_term':
            price_label = f"{renewal_price:.2f} كريديت (نصف السعر)"
            price_label_en = f"{renewal_price:.2f} credits (half price)"
        else:
            price_label = f"{renewal_price:.2f} كريديت (نفس السعر الأصلي)"
            price_label_en = f"{renewal_price:.2f} credits (same as original price)"
        
        confirm_message = (
            f"🔄 *تأكيد تجديد الرقم*\n\n"
            f"📱 الرقم: {number}\n"
            f"🏷️ الخدمة: {service}\n"
            f"💰 السعر: {price_label}\n"
            f"💵 رصيدك: {user_balance:.2f} كريديت\n\n"
            f"هل تريد المتابعة؟"
        ) if lang == 'ar' else (
            f"🔄 *Confirm Number Renewal*\n\n"
            f"📱 Number: {number}\n"
            f"🏷️ Service: {service}\n"
            f"💰 Price: {price_label_en}\n"
            f"💵 Your balance: {user_balance:.2f} credits\n\n"
            f"Proceed?"
        )

        # حفظ المعلومات في context
        context.user_data['renew_order_id'] = order_id
        context.user_data['renew_number'] = number
        context.user_data['renew_service'] = service
        context.user_data['renew_price'] = renewal_price
        context.user_data['renew_order_type'] = order_type
        context.user_data['renew_renewal_type'] = renewal_type

        keyboard = [
            [InlineKeyboardButton(
                NONVOIP_MESSAGES[lang]['yes'],
                callback_data='nv_confirm_renew_yes'
            )],
            [InlineKeyboardButton(
                NONVOIP_MESSAGES[lang]['no'],
                callback_data='nv_confirm_renew_no'
            )]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            confirm_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

        return 'NONVOIP_CONFIRM_RENEW'

    except Exception as e:
        logger.error(f"خطأ في تجديد الرقم: {e}")
        await query.edit_message_text(f"❌ حدث خطأ: {str(e)}")
        return ConversationHandler.END


async def nonvoip_process_renew(update: Update, context: ContextTypes.DEFAULT_TYPE, conn) -> int:
    """معالجة تجديد الرقم مع التحققات الكاملة والتحديث في قاعدة البيانات"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    lang = get_user_language(user_id, conn)

    if query.data == 'nv_confirm_renew_no':
        await query.edit_message_text("❌ تم إلغاء التجديد")
        return ConversationHandler.END

    # استرجاع المعلومات
    order_id = context.user_data.get('renew_order_id')
    number = context.user_data.get('renew_number')
    service = context.user_data.get('renew_service')
    renewal_price = context.user_data.get('renew_price', 0)
    order_type = context.user_data.get('renew_order_type', 'short_term')
    renewal_type = context.user_data.get('renew_renewal_type', 'reuse')

    if not all([number, service, order_id]):
        await query.edit_message_text("❌ خطأ: معلومات التجديد غير موجودة")
        return ConversationHandler.END

    try:
        db = NonVoipDB()

        # التحقق من صحة الطلب (بدون فحص التجديد المسبق للسماح بالتجديد المتكرر)
        order_check = db.fetch_one("""
            SELECT refunded, user_id
            FROM nonvoip_orders
            WHERE order_id = ?
        """, (order_id,))

        if not order_check:
            await query.edit_message_text("❌ خطأ: الطلب غير موجود")
            return ConversationHandler.END

        refunded_status, order_user_id = order_check

        if order_user_id != user_id:
            await query.edit_message_text("❌ خطأ: هذا الطلب لا ينتمي لك")
            return ConversationHandler.END

        if refunded_status:
            await query.edit_message_text("❌ لا يمكن تجديد رقم تم استرداد ثمنه")
            return ConversationHandler.END

        # التحقق من وجود الرقم
        if not number or number == '':
            await query.edit_message_text("❌ رقم غير صالح")
            return ConversationHandler.END

        # جلب تاريخ انتهاء الصلاحية من قاعدة البيانات
        cursor = conn.execute("SELECT expires_at, sale_price FROM nonvoip_orders WHERE order_id = ?", (order_id,))
        order_details = cursor.fetchone()
        
        if not order_details:
            await query.edit_message_text("❌ معلومات الطلب غير موجودة")
            return ConversationHandler.END
            
        expires_at = order_details[0]
        sale_price = order_details[1]

        # التحقق من قابلية التجديد حسب النوع والوقت
        if not expires_at:
            await query.edit_message_text("❌ لا يمكن تحديد صلاحية الرقم")
            return ConversationHandler.END

        try:
            expires_dt = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
            now = datetime.now()
            time_since_expiry = (now - expires_dt).total_seconds()
        except:
            await query.edit_message_text("❌ خطأ في تاريخ الانتهاء")
            return ConversationHandler.END

        # التحقق من النافذة الزمنية للتجديد
        is_renewable = False
        renewal_type = None
        renewal_price = 0

        if order_type == 'short_term':
            # short_term: قابل لإعادة الاستخدام في أي وقت بعد استقبال رسالة (بنصف السعر)
            is_renewable = True
            renewal_type = 'reuse'
            renewal_price = calculate_renewal_price(sale_price, order_type)
        else:
            # long_term/3days: قابل للتجديد خلال 7 أيام فقط من الانتهاء (بنفس السعر الأصلي)
            if -86400 <= time_since_expiry <= 604800:
                is_renewable = True
                renewal_type = 'renew'
                renewal_price = calculate_renewal_price(sale_price, order_type)

        if not is_renewable:
            if order_type == 'short_term':
                msg = (
                    "❌ لا يمكن تجديد هذا الرقم\n\n"
                    "⏰ يمكن تجديد الأرقام قصيرة الأمد خلال 24 ساعة فقط من الانتهاء"
                ) if lang == 'ar' else (
                    "❌ Cannot renew this number\n\n"
                    "⏰ Short-term numbers can only be renewed within 24 hours of expiry"
                )
            else:
                msg = (
                    "❌ لا يمكن تجديد هذا الرقم\n\n"
                    "⏰ يمكن تجديد الأرقام طويلة الأمد خلال أسبوع فقط من الانتهاء"
                ) if lang == 'ar' else (
                    "❌ Cannot renew this number\n\n"
                    "⏰ Long-term numbers can only be renewed within 7 days of expiry"
                )
            await query.edit_message_text(msg)
            return ConversationHandler.END

        # التحقق من رصيد المستخدم
        cursor = conn.execute(
            "SELECT COALESCE(credits_balance, 0), COALESCE(referral_balance, 0) FROM users WHERE user_id = ?",
            (user_id,)
        )
        user_balance_row = cursor.fetchone()
        user_balance = user_balance_row[0] if user_balance_row else 0.0

        if user_balance < renewal_price:
            # تسجيل محاولة تجديد فاشلة (رصيد ناقص)
            import sys
            sys.path.insert(0, '/home/runner/workspace')
            from bot import log_renewal_operation
            log_renewal_operation(
                user_id=user_id,
                username=f'user_{user_id}',
                order_id=order_id,
                operation_type='FAILED_INSUFFICIENT_BALANCE',
                original_number=number,
                new_number=number,
                price_usd=None,
                price_credits=renewal_price,
                credit_deducted=0,
                notes=f"Failed: Insufficient balance (have={user_balance}, need={renewal_price})"
            )
            
            await query.edit_message_text(
                NONVOIP_MESSAGES[lang]['insufficient_balance'].format(
                    balance=user_balance,
                    price=renewal_price
                ),
                parse_mode=ParseMode.MARKDOWN
            )
            return ConversationHandler.END

        # عرض رسالة المعالجة قبل استدعاء API
        await query.edit_message_text(NONVOIP_MESSAGES[lang]['processing_order'])

        # تجديد الرقم عبر API - استخدام الدالة الصحيحة حسب نوع الرقم
        api = NonVoipAPI()

        if renewal_type == 'reuse':
            # الأرقام قصيرة الأمد: استخدام reuse
            renew_result = api.reuse(service=service, number=number)
        else:
            # الأرقام طويلة الأمد: استخدام renew
            renew_result = api.renew(service=service, number=number)

        if renew_result.get('status') != 'success':
            error_msg = renew_result.get('message', 'خطأ غير معروف')
            
            # تسجيل فشل التجديد (API failure)
            import sys
            sys.path.insert(0, '/home/runner/workspace')
            from bot import log_renewal_operation
            log_renewal_operation(
                user_id=user_id,
                username=f'user_{user_id}',
                order_id=order_id,
                operation_type='FAILED_API_ERROR',
                original_number=number,
                new_number=number,
                price_usd=None,
                price_credits=renewal_price,
                credit_deducted=0,
                notes=f"Failed: API error - {error_msg[:100]}"
            )
            
            failure_message = (
                f"❌ *فشل التجديد*\n\n"
                f"📋 السبب: `{error_msg}`\n\n"
                f"💡 الأسباب المحتملة:\n"
                f"• الرقم لم يستقبل رسالة في المرة الأولى\n"
                f"• الرقم غير متاح للتجديد في الموقع\n"
                f"• انتهى وقت التجديد المسموح\n\n"
                f"ℹ️ لم يتم خصم أي رصيد من حسابك"
            ) if lang == 'ar' else (
                f"❌ *Renewal Failed*\n\n"
                f"📋 Reason: `{error_msg}`\n\n"
                f"💡 Possible causes:\n"
                f"• Number didn't receive a message the first time\n"
                f"• Number not available for renewal on the website\n"
                f"• Renewal time window expired\n\n"
                f"ℹ️ No credits were deducted from your account"
            )
            await query.edit_message_text(
                failure_message,
                parse_mode=ParseMode.MARKDOWN
            )
            return ConversationHandler.END

        # خصم من رصيد المستخدم (فقط إذا كان هناك تكلفة)
        if renewal_price > 0:
            cursor = conn.execute(
                "SELECT COALESCE(credits_balance, 0), COALESCE(referral_balance, 0) FROM users WHERE user_id = ?",
                (user_id,)
            )
            balances = cursor.fetchone()
            credits_bal = balances[0] if balances else 0.0
            referral_bal = balances[1] if balances else 0.0

            if credits_bal >= renewal_price:
                conn.execute(
                    "UPDATE users SET credits_balance = credits_balance - ? WHERE user_id = ?",
                    (renewal_price, user_id)
                )
            else:
                remaining = renewal_price - credits_bal
                conn.execute(
                    "UPDATE users SET credits_balance = 0, referral_balance = referral_balance - ? WHERE user_id = ?",
                    (remaining, user_id)
                )
            conn.commit()

        # تحديث الطلب القديم بعلامة التجديد وتاريخ الانتهاء الجديد
        order_info = renew_result.get('message', [{}])[0] if renew_result.get('message') else {}

        # استخراج تاريخ الانتهاء الجديد من الاستجابة
        new_expires_at = None
        if renewal_type == 'reuse':
            # short_term: الرد يحتوي على till_expiration بالثواني
            expiration_seconds = order_info.get('till_expiration', 900)
            new_expires_dt = datetime.now() + timedelta(seconds=expiration_seconds)
            new_expires_at = new_expires_dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            # long_term/3days: الرد يحتوي على expiration كتاريخ UTC
            new_expires_at = order_info.get('expiration') or order_info.get('expires')

        # تحديث الطلب في قاعدة البيانات - إعادة تعيين كل شيء كأنه رقم جديد
        # renewed = 0 لإظهار الرقم في My Numbers بعد التجديد
        # visible_in_my_numbers = 1 لإعادة الرقم إلى My Numbers بعد التجديد
        update_query = """
            UPDATE nonvoip_orders
            SET renewed = 0,
                renewal_type = ?,
                status = 'active',
                expires_at = COALESCE(?, expires_at),
                sms_sent = 0,
                sms_received = NULL,
                pin_code = NULL,
                visible_in_my_numbers = 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE order_id = ?
        """
        conn.execute(update_query, (renewal_type, new_expires_at, order_id))
        conn.commit()
        
        # تسجيل عملية التجديد في nonvoip_renewal_logs
        import sys
        sys.path.insert(0, '/home/runner/workspace')
        from bot import log_renewal_operation
        username = context.user_data.get('username', f'user_{user_id}')
        log_renewal_operation(
            user_id=user_id,
            username=username,
            order_id=order_id,
            operation_type=renewal_type,
            original_number=number,
            new_number=number,
            price_usd=None,
            price_credits=renewal_price,
            credit_deducted=renewal_price,
            notes=f"Renewal Type: {renewal_type}, Order Type: {order_type}, Service: {service}"
        )

        # إنشاء رسالة نجاح مع أزرار التحكم
        if order_type == 'short_term':
            price_text = f"{renewal_price} كريديت (نصف السعر)"
            price_text_en = f"{renewal_price} credits (half price)"
        else:
            price_text = f"{renewal_price} كريديت (نفس السعر الأصلي)"
            price_text_en = f"{renewal_price} credits (same as original price)"

        icon = get_service_icon(service)
        display_service = get_display_service_name(service)
        
        success_message = (
            f"✅ *تم تجديد الرقم بنجاح!*\n\n"
            f"📱 الرقم: `{number}`\n"
            f"{icon} *الخدمة:* {display_service}\n"
            f"⏱️ النوع: {order_type}\n"
            f"💰 المبلغ المدفوع: {price_text}\n"
            f"⏰ صالح حتى: {new_expires_at if new_expires_at else 'غير محدد'}\n\n"
            f"📬 انتظار الرسالة...\n"
            f"سيتم إرسال الرسالة فوراً عند وصولها\n"
            f"⏳ مراقبة تلقائية نشطة\n\n"
            f"⚠️ في حال عدم وصول رسالة، سيتم استرداد الرصيد تلقائياً"
        ) if lang == 'ar' else (
            f"✅ *Number Renewed Successfully!*\n\n"
            f"📱 Number: `{number}`\n"
            f"{icon} *Service:* {display_service}\n"
            f"⏱️ Type: {order_type}\n"
            f"💰 Amount paid: {price_text_en}\n"
            f"⏰ Valid until: {new_expires_at if new_expires_at else 'N/A'}\n\n"
            f"📬 Waiting for message...\n"
            f"Message will be sent immediately when received\n"
            f"⏳ Auto-monitoring active\n\n"
            f"⚠️ If no message arrives, credits will be refunded automatically"
        )

        # إضافة أزرار التحكم
        keyboard = []

        # زر التفاصيل
        keyboard.append([InlineKeyboardButton(
            "📊 تفاصيل الرقم" if lang == 'ar' else "📊 Details",
            callback_data=f"nv_manual_check_{order_id}"
        )])

        # زر Cancel & Refund للأرقام قصيرة الأمد أو زر Active للأرقام طويلة المدى
        if order_type == 'short_term':
            keyboard.append([InlineKeyboardButton(
                "❌ إلغاء وإعادة الرصيد" if lang == 'ar' else "❌ Cancel & Refund",
                callback_data=f"nv_cancel_order_{order_id}"
            )])
        elif order_type in ['3days', 'long_term']:
            # زر Active للأرقام طويلة المدى - يتغير حسب حالة التفعيل
            activation_status = order_info.get('activation_status', 'inactive')
            activated_until = order_info.get('activated_until')
            
            if activation_status == 'active' and activated_until:
                time_left = format_activation_time(activated_until, lang)
                button_text = f"✅ مفعل ({time_left})" if lang == 'ar' else f"✅ Activated ({time_left})"
            else:
                button_text = "✔️ تفعيل" if lang == 'ar' else "✔️ Active"
            
            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f"nv_activate_{order_id}"
            )])

        keyboard.append([InlineKeyboardButton(
            "🔙 العودة لأرقامي" if lang == 'ar' else "🔙 Back to My Numbers",
            callback_data='nv_my_numbers'
        )])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # الحصول على message_id قبل تحديث الرسالة
        message_id = query.message.message_id if query.message else None

        await query.edit_message_text(
            success_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

        # حفظ message_id في قاعدة البيانات لتفعيل المراقبة التلقائية
        if message_id and order_id:
            db.set_order_message_id(order_id, message_id)
            logger.info(f"✅ تم حفظ message_id={message_id} للطلب المُجدد {order_id}")
        else:
            logger.warning(f"⚠️ لم يتم الحصول على message_id للطلب المُجدد {order_id}")

        logger.info(f"✅ تم تجديد رقم للمستخدم {user_id}: {number} - نوع: {renewal_type} - مبلغ: {renewal_price} كريديت")

        # بدء مراقبة الرقم تلقائياً فقط إذا كان لدينا message_id
        if message_id and renewal_type == 'reuse':
            # فقط للأرقام قصيرة الأمد نحتاج المراقبة التلقائية
            expiration_seconds = order_info.get('till_expiration', 900)
            asyncio.create_task(monitor_order_for_sms(
                application=context.application,
                user_id=user_id,
                order_id=order_id,
                service=service,
                number=number,
                message_id=message_id,
                expiration_seconds=expiration_seconds,
                lang=lang
            ))
            logger.info(f"🔄 بدء المراقبة التلقائية للطلب المُجدد {order_id}")
        else:
            logger.info(f"ℹ️ الطلب المُجدد {order_id} من نوع {renewal_type} - لا يحتاج مراقبة تلقائية")

        return ConversationHandler.END

    except Exception as e:
        logger.error(f"خطأ في معالجة التجديد: {e}")
        # تنظيف رسالة الخطأ من الأحرف الخاصة التي قد تسبب مشاكل في Markdown
        error_text = str(e).replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
        error_message = (
            "❌ *عذراً، حدث خطأ غير متوقع*\n\n"
            "💬 يرجى المحاولة لاحقاً أو التواصل مع الآدمن.\n"
            f"🔍 التفاصيل: {error_text}"
        ) if lang == 'ar' else (
            "❌ *Sorry, an unexpected error occurred*\n\n"
            "💬 Please try again later or contact admin.\n"
            f"🔍 Details: {error_text}"
        )
        await query.edit_message_text(error_message, parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════════════════════
# PART 5: BOT FUNCTIONS - ADMIN HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

async def nonvoip_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, conn) -> int:
    """قائمة إدارة الأرقام للآدمن"""
    user_id = update.effective_user.id
    lang = get_user_language(user_id, conn)

    keyboard = [
        [InlineKeyboardButton(NONVOIP_MESSAGES[lang]['view_balance'], callback_data='nva_balance')],
        [InlineKeyboardButton(NONVOIP_MESSAGES[lang]['view_products'], callback_data='nva_products')],
        [InlineKeyboardButton(NONVOIP_MESSAGES[lang]['view_all_orders'], callback_data='nva_orders')],
        [InlineKeyboardButton(NONVOIP_MESSAGES[lang]['back'], callback_data='nva_back')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            NONVOIP_MESSAGES[lang]['admin_menu_title'],
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            NONVOIP_MESSAGES[lang]['admin_menu_title'],
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    return 'NONVOIP_ADMIN_MENU'


async def nonvoip_admin_balance(update: Update, context: ContextTypes.DEFAULT_TYPE, conn) -> int:
    """عرض رصيد حساب NonVoip"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    lang = get_user_language(user_id, conn)

    try:
        api = NonVoipAPI()
        balance_result = api.get_balance()

        if balance_result.get('status') == 'success':
            balance = balance_result.get('balance', '0.00')
            message = NONVOIP_MESSAGES[lang]['balance_info'].format(balance=balance)
        else:
            message = f"❌ خطأ: {balance_result.get('message', 'Unknown error')}"

        await query.edit_message_text(message, parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"خطأ في جلب الرصيد: {e}")
        await query.edit_message_text(f"❌ خطأ: {str(e)}")
        return ConversationHandler.END


async def nonvoip_admin_products(update: Update, context: ContextTypes.DEFAULT_TYPE, conn) -> int:
    """عرض المنتجات المتاحة"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    lang = get_user_language(user_id, conn)

    await query.edit_message_text(NONVOIP_MESSAGES[lang]['products_loading'])

    try:
        api = NonVoipAPI()

        all_products = []
        product_types = [
            ('short_term', 'قصيرة الأمد'),
            ('long_term', 'طويلة الأمد'),
            ('3days', '3 أيام')
        ]

        for ptype, ptype_ar in product_types:
            products_result = api.get_products(product_type=ptype)
            if products_result.get('status') == 'success':
                products = products_result.get('message', [])
                all_products.extend([(p, ptype_ar) for p in products])

        if not all_products:
            await query.edit_message_text("❌ لا توجد منتجات متاحة حالياً")
            return ConversationHandler.END

        MAX_MESSAGE_LENGTH = 4000

        await query.edit_message_text(
            f"📦 *المنتجات المتاحة* (إجمالي: {len(all_products)})\n\n"
            f"⏳ جاري إرسال جميع المنتجات...",
            parse_mode=ParseMode.MARKDOWN
        )

        current_message = "📦 *قائمة المنتجات المتاحة*\n\n"
        message_count = 1

        for product, ptype_ar in all_products:
            product_line = f"🔹 *{product['name']}*\n"
            product_line += f"   💵 ${product['price']} | 📊 متوفر: {product['available']} | ⏱️ {ptype_ar}\n\n"

            if len(current_message) + len(product_line) > MAX_MESSAGE_LENGTH:
                await update.effective_chat.send_message(
                    current_message,
                    parse_mode=ParseMode.MARKDOWN
                )
                message_count += 1
                current_message = f"📦 *قائمة المنتجات المتاحة (تابع {message_count})*\n\n"

            current_message += product_line

        if current_message.strip():
            await update.effective_chat.send_message(
                current_message,
                parse_mode=ParseMode.MARKDOWN
            )

        return ConversationHandler.END

    except Exception as e:
        logger.error(f"خطأ في عرض المنتجات: {e}")
        await query.edit_message_text(f"❌ حدث خطأ: {str(e)}")
        return ConversationHandler.END


async def nonvoip_admin_all_orders(update: Update, context: ContextTypes.DEFAULT_TYPE, conn) -> int:
    """عرض جميع طلبات الأرقام مع تفاصيل شاملة"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    lang = get_user_language(user_id, conn)

    try:
        db = NonVoipDB()
        orders = db.get_active_orders()

        if not orders:
            await query.edit_message_text("📋 لا توجد طلبات حالياً")
            return ConversationHandler.END

        # حساب الإحصائيات الإجمالية
        total_cost = sum(float(o.get('cost_price') or 0) for o in orders)
        total_sale = sum(float(o.get('sale_price') or 0) for o in orders)
        total_profit = total_sale - total_cost
        sms_received_count = sum(1 for o in orders if o.get('sms_received'))
        
        # إحصائيات حسب النوع
        type_counts = {'short_term': 0, '3days': 0, 'long_term': 0}
        for o in orders:
            order_type = o.get('type', 'short_term')
            if order_type in type_counts:
                type_counts[order_type] += 1
        
        type_names = {'short_term': '15 دقيقة', '3days': '3 أيام', 'long_term': '30 يوم'}
        
        message = f"""📋 *جميع الطلبات النشطة* (إجمالي: {len(orders)})

━━━━━━━━━━━━━━━━━━━━━━━
📊 *الإحصائيات الإجمالية:*
• 15 دقيقة: {type_counts['short_term']} | 3 أيام: {type_counts['3days']} | 30 يوم: {type_counts['long_term']}
• إجمالي التكلفة: `${total_cost:.2f}`
• إجمالي المبيعات: `${total_sale:.2f}`
• صافي الربح: `${total_profit:.2f}`
• رسائل مستلمة: {sms_received_count}

━━━━━━━━━━━━━━━━━━━━━━━
📦 *تفاصيل الطلبات:*
"""

        for i, order in enumerate(orders[:15], 1):
            order_id = order.get('order_id', 'N/A')
            order_user_id = order.get('user_id', 'N/A')
            number = order.get('number', 'N/A')
            service = order.get('service', 'N/A')
            status = order.get('status', 'N/A')
            order_type = order.get('type', 'short_term')
            cost_price = float(order.get('cost_price') or 0)
            sale_price = float(order.get('sale_price') or 0)
            profit = sale_price - cost_price
            sms = "✅" if order.get('sms_received') else "⏳"
            created = str(order.get('created_at', ''))[:16] if order.get('created_at') else 'N/A'
            expires = str(order.get('expires_at', ''))[:16] if order.get('expires_at') else 'N/A'
            type_ar = type_names.get(order_type, order_type)
            
            # رمز الحالة
            status_emoji = {"active": "🟢", "completed": "✅", "expired": "⏰", 
                           "refunded": "↩️", "cancelled": "❌", "pending": "⏳",
                           "reserved": "📝", "delivered": "📨", "success": "✅"}.get(status, "❓")
            
            message += f"""
{i}. {status_emoji} *{service}*
   📱 `{number}`
   👤 المستخدم: `{order_user_id}`
   ⏱️ النوع: {type_ar} | 📩 SMS: {sms}
   💵 تكلفة: `${cost_price:.2f}` → بيع: `${sale_price:.2f}` (ربح: `${profit:.2f}`)
   📅 الإنشاء: {created}
   ⏰ الانتهاء: {expires}
"""

        if len(orders) > 15:
            message += f"\n... و {len(orders) - 15} طلب آخر"

        await query.edit_message_text(message, parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"خطأ في عرض الطلبات: {e}")
        await query.edit_message_text(f"❌ حدث خطأ: {str(e)}")
        return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════════════════════
# PART 6: INLINE QUERY HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

SERVICE_ICONS = {
    'whatsapp': '💚',
    'telegram': '✈️',
    'facebook': '📘',
    'instagram': '📷',
    'google': '🔍',
    'gmail': '📧',
    'twitter': '🐦',
    'x.com': '❌',
    'tiktok': '🎵',
    'amazon': '📦',
    'paypal': '💰',
    'uber': '🚗',
    'netflix': '🎬',
    'spotify': '🎵',
    'snapchat': '👻',
    'discord': '🎮',
    'microsoft': '💼',
    'apple': '🍎',
    'yahoo': '📧',
    'linkedin': '💼',
    'reddit': '🤖',
    'twitch': '🟣',
    'coinbase': '💎',
    'binance': '🟡',
    'steam': '🎮',
    'ebay': '🛒',
    'airbnb': '🏠',
    'booking': '🏨',
    'viber': '💜',
    'wechat': '💬',
    'line': '💬',
    'signal': '🔒',
    'skype': '💙',
    'zoom': '🎥',
    'pinterest': '📌',
    'tinder': '❤️',
    'bumble': '💛',
    'badoo': '💜',
    'alibaba': '🟠',
    'otp': '🔐',
    'sms': '💬',
    'verification': '✅',
    'default': '📱'
}

COUNTRY_FLAGS = {
    'US': '🇺🇸',
    'CA': '🇨🇦',
    'GB': '🇬🇧',
    'UK': '🇬🇧',
    'FR': '🇫🇷',
    'DE': '🇩🇪',
    'IT': '🇮🇹',
    'ES': '🇪🇸',
    'NL': '🇳🇱',
    'BE': '🇧🇪',
    'AU': '🇦🇺',
    'NZ': '🇳🇿',
    'BR': '🇧🇷',
    'MX': '🇲🇽',
    'AR': '🇦🇷',
    'CL': '🇨🇱',
    'CO': '🇨🇴',
    'IN': '🇮🇳',
    'PK': '🇵🇰',
    'BD': '🇧🇩',
    'ID': '🇮🇩',
    'MY': '🇲🇾',
    'SG': '🇸🇬',
    'TH': '🇹🇭',
    'VN': '🇻🇳',
    'PH': '🇵🇭',
    'JP': '🇯🇵',
    'KR': '🇰🇷',
    'CN': '🇨🇳',
    'RU': '🇷🇺',
    'UA': '🇺🇦',
    'PL': '🇵🇱',
    'RO': '🇷🇴',
    'CZ': '🇨🇿',
    'SE': '🇸🇪',
    'NO': '🇳🇴',
    'DK': '🇩🇰',
    'FI': '🇫🇮',
    'PT': '🇵🇹',
    'GR': '🇬🇷',
    'TR': '🇹🇷',
    'EG': '🇪🇬',
    'SA': '🇸🇦',
    'AE': '🇦🇪',
    'IL': '🇮🇱',
    'ZA': '🇿🇦',
    'NG': '🇳🇬',
    'KE': '🇰🇪',
    'default': '🌐'
}

# قاموس صور الخدمات للاستخدام في Inline Query
# تم تصغير الصور من 240px إلى 120px لتسريع التحميل
SERVICE_THUMBNAIL_URLS = {
    'whatsapp': 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/WhatsApp.svg/120px-WhatsApp.svg.png',
    'telegram': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/82/Telegram_logo.svg/120px-Telegram_logo.svg.png',
    'facebook': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/Facebook_Logo_%282019%29.png/120px-Facebook_Logo_%282019%29.png',
    'instagram': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e7/Instagram_logo_2016.svg/120px-Instagram_logo_2016.svg.png',
    'google': 'https://upload.wikimedia.org/wikipedia/commons/thumb/2/2f/Google_2015_logo.svg/120px-Google_2015_logo.svg.png',
    'gmail': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Gmail_icon_%282020%29.svg/120px-Gmail_icon_%282020%29.svg.png',
    'twitter': 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Logo_of_Twitter.svg/120px-Logo_of_Twitter.svg.png',
    'x.com': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/X_icon_2.svg/120px-X_icon_2.svg.png',
    'tiktok': 'https://upload.wikimedia.org/wikipedia/en/thumb/a/a9/TikTok_logo.svg/120px-TikTok_logo.svg.png',
    'amazon': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/Amazon_logo.svg/120px-Amazon_logo.svg.png',
    'paypal': 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/PayPal.svg/120px-PayPal.svg.png',
    'uber': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/cc/Uber_logo_2018.png/120px-Uber_logo_2018.png',
    'netflix': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/Netflix_2015_logo.svg/120px-Netflix_2015_logo.svg.png',
    'spotify': 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/Spotify_logo_without_text.svg/120px-Spotify_logo_without_text.svg.png',
    'snapchat': 'https://upload.wikimedia.org/wikipedia/en/thumb/c/c4/Snapchat_logo.svg/120px-Snapchat_logo.svg.png',
    'discord': 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/f6/Discord_icon_clyde_%28white%29.svg/120px-Discord_icon_clyde_%28white%29.svg.png',
    'microsoft': 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/Microsoft_logo.svg/120px-Microsoft_logo.svg.png',
    'apple': 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/Apple_logo_black.svg/120px-Apple_logo_black.svg.png',
    'yahoo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Yahoo%21_%282019%29.svg/120px-Yahoo%21_%282019%29.svg.png',
    'linkedin': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/LinkedIn_logo_initials.png/120px-LinkedIn_logo_initials.png',
    'reddit': 'https://upload.wikimedia.org/wikipedia/en/thumb/5/58/Reddit_logo_new.svg/120px-Reddit_logo_new.svg.png',
    'twitch': 'https://upload.wikimedia.org/wikipedia/commons/thumb/2/26/Twitch_logo.svg/120px-Twitch_logo.svg.png',
    'coinbase': 'https://cryptologos.cc/logos/coinbase-coin-logo.png',
    'binance': 'https://cryptologos.cc/logos/binance-coin-bnb-logo.png',
    'steam': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/83/Steam_icon_logo.svg/120px-Steam_icon_logo.svg.png',
    'ebay': 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/EBay_logo.svg/120px-EBay_logo.svg.png',
    'airbnb': 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/69/Airbnb_Logo_B%C3%A9lo.svg/120px-Airbnb_Logo_B%C3%A9lo.svg.png',
    'viber': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/74/Viber_logo.svg/120px-Viber_logo.svg.png',
    'wechat': 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/dc/WeChat_logo.svg/120px-WeChat_logo.svg.png',
    'line': 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/LINE_logo.svg/120px-LINE_logo.svg.png',
    'signal': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/56/Signal_Logo.png/120px-Signal_Logo.png',
    'skype': 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/60/Skype_logo_%282019%E2%80%93present%29.svg/120px-Skype_logo_%282019%E2%80%93present%29.svg.png',
    'zoom': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Zoom_Communications_Logo.svg/120px-Zoom_Communications_Logo.svg.png',
    'pinterest': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/Pinterest-logo.png/120px-Pinterest-logo.png',
    'tinder': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/77/Tinder_Logo_Style_2_2023.svg/120px-Tinder_Logo_Style_2_2023.svg.png',
    'bolt': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/92/Bolt_logo.svg/120px-Bolt_logo.svg.png',
    'cashapp': 'https://logo.clearbit.com/cash.app',
    'default': 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Mobile_phone_icon.svg/120px-Mobile_phone_icon.svg.png'
}


def get_service_icon(service_name: str) -> str:
    """الحصول على الأيقونة المناسبة للخدمة"""
    service_lower = service_name.lower()

    for key, icon in SERVICE_ICONS.items():
        if key in service_lower:
            return icon

    return SERVICE_ICONS['default']


def get_service_thumbnail(service_name: str) -> str:
    """
    الحصول على رابط صورة الخدمة للاستخدام في Inline Query
    يستخدم Clearbit Logo API للخدمات غير المحددة مسبقاً
    """
    service_lower = service_name.lower()

    # أولاً: البحث في القاموس المحدد مسبقاً
    for key, thumbnail_url in SERVICE_THUMBNAIL_URLS.items():
        if key in service_lower:
            return thumbnail_url

    # ثانياً: استخدام Clearbit Logo API كبديل ديناميكي
    # تنظيف اسم الخدمة وتحويله لنطاق محتمل
    cleaned_name = service_lower.replace(' ', '').replace('_', '').replace('-', '')

    # قاموس النطاقات الشائعة للخدمات غير المحددة (موسع)
    domain_mapping = {
        # خدمات الاستطلاعات والمكافآت
        'ipsos': 'i-say.com',
        'isay': 'i-say.com',
        'swagbucks': 'swagbucks.com',
        'surveyjunkie': 'surveyjunkie.com',
        'inboxdollars': 'inboxdollars.com',
        'prizerebel': 'prizerebel.com',
        'toluna': 'toluna.com',
        'vindale': 'vindale.com',
        'mypoints': 'mypoints.com',
        'opinionoutpost': 'opinionoutpost.com',
        'brandedsurveys': 'branded-surveys.com',
        'branded': 'branded-surveys.com',
        'beautyrewards': 'beautyrewards.com',
        'albertgenius': 'albertgenius.com',
        
        # خدمات جديدة
        '3fun': '3fun.com',
        'adverifi': 'adverifi.com',
        'ando': 'andomoney.com',
        'aspiration': 'aspiration.com',
        'alexgenie': 'alexgenie.com',
        'adltup': 'adltup.com',
        'askpolonia': 'askpolonia.com',
        'braid': 'braid.co',
        'cashing': 'cashing.app',
        'chispa': 'chispaapp.com',
        'chowbus': 'chowbus.com',
        'foodhwy': 'foodhwy.com',

        # خدمات التواصل والبريد
        'yahoo': 'yahoo.com',
        'outlook': 'outlook.com',
        'hotmail': 'outlook.com',
        'protonmail': 'proton.me',
        'proton': 'proton.me',
        'zoho': 'zoho.com',
        'aol': 'aol.com',
        'yandex': 'yandex.com',
        'mailcom': 'mail.com',
        'gmx': 'gmx.com',
        'icloud': 'icloud.com',

        # شركات التكنولوجيا
        'microsoft': 'microsoft.com',
        'apple': 'apple.com',
        'samsung': 'samsung.com',
        'huawei': 'huawei.com',
        'xiaomi': 'mi.com',
        'oppo': 'oppo.com',
        'vivo': 'vivo.com',
        'oneplus': 'oneplus.com',
        'sony': 'sony.com',
        'lg': 'lg.com',
        'nokia': 'nokia.com',

        # التجارة الإلكترونية
        'amazon': 'amazon.com',
        'ebay': 'ebay.com',
        'aliexpress': 'aliexpress.com',
        'alibaba': 'alibaba.com',
        'wish': 'wish.com',
        'joom': 'joom.com',
        'etsy': 'etsy.com',
        'shopify': 'shopify.com',
        'target': 'target.com',
        'walmart': 'walmart.com',
        'bestbuy': 'bestbuy.com',
        'homedepot': 'homedepot.com',
        'lowes': 'lowes.com',
        'wayfair': 'wayfair.com',
        'ikea': 'ikea.com',
        'costco': 'costco.com',
        'samsclub': 'samsclub.com',
        'overstock': 'overstock.com',
        'newegg': 'newegg.com',

        # المدفوعات والبنوك
        'paypal': 'paypal.com',
        'venmo': 'venmo.com',
        'cashapp': 'cash.app',
        'zelle': 'zellepay.com',
        'wise': 'wise.com',
        'transferwise': 'wise.com',
        'revolut': 'revolut.com',
        'monzo': 'monzo.com',
        'n26': 'n26.com',
        'chime': 'chime.com',
        'square': 'squareup.com',
        'stripe': 'stripe.com',
        'adyen': 'adyen.com',
        'payoneer': 'payoneer.com',
        'skrill': 'skrill.com',
        'neteller': 'neteller.com',
        'paysafecard': 'paysafecard.com',

        # التمويل والاستثمار
        'klarna': 'klarna.com',
        'afterpay': 'afterpay.com',
        'affirm': 'affirm.com',
        'plaid': 'plaid.com',
        'truebill': 'truebill.com',
        'mint': 'mint.com',
        'creditkarma': 'creditkarma.com',
        'nerdwallet': 'nerdwallet.com',
        'robinhood': 'robinhood.com',
        'webull': 'webull.com',
        'etrade': 'etrade.com',
        'fidelity': 'fidelity.com',
        'schwab': 'schwab.com',
        'tdameritrade': 'tdameritrade.com',
        'vanguard': 'vanguard.com',
        'acorns': 'acorns.com',
        'stash': 'stash.com',

        # البنوك التقليدية
        'ally': 'ally.com',
        'sofi': 'sofi.com',
        'marcus': 'marcus.com',
        'discover': 'discover.com',
        'capitalone': 'capitalone.com',
        'chase': 'chase.com',
        'wellsfargo': 'wellsfargo.com',
        'bankofamerica': 'bankofamerica.com',
        'usbank': 'usbank.com',
        'pnc': 'pnc.com',
        'truist': 'truist.com',
        'citizensbank': 'citizensbank.com',
        'huntington': 'huntington.com',
        'regions': 'regions.com',
        'keybank': 'key.com',
        'suntrust': 'suntrust.com',
        'bbt': 'bbt.com',
        'fifth3rd': '53.com',
        'citibank': 'citigroup.com',
        'hsbc': 'hsbc.com',
        'barclays': 'barclays.com',
        'santander': 'santander.com',

        # خدمات التوصيل
        'doordash': 'doordash.com',
        'grubhub': 'grubhub.com',
        'ubereats': 'ubereats.com',
        'postmates': 'postmates.com',
        'instacart': 'instacart.com',
        'shipt': 'shipt.com',
        'gopuff': 'gopuff.com',
        'seamless': 'seamless.com',
        'deliveroo': 'deliveroo.com',
        'justeat': 'just-eat.com',
        'foodpanda': 'foodpanda.com',

        # خدمات النقل
        'uber': 'uber.com',
        'lyft': 'lyft.com',
        'bolt': 'bolt.eu',
        'grab': 'grab.com',
        'gojek': 'gojek.com',
        'didi': 'didiglobal.com',
        'ola': 'olacabs.com',
        'careem': 'careem.com',

        # الحجوزات والسفر
        'booking': 'booking.com',
        'airbnb': 'airbnb.com',
        'expedia': 'expedia.com',
        'hotels': 'hotels.com',
        'trivago': 'trivago.com',
        'kayak': 'kayak.com',
        'priceline': 'priceline.com',
        'hotwire': 'hotwire.com',
        'agoda': 'agoda.com',
        'tripadvisor': 'tripadvisor.com',
        'vrbo': 'vrbo.com',

        # الألعاب
        'steam': 'steampowered.com',
        'epicgames': 'epicgames.com',
        'origin': 'origin.com',
        'battlenet': 'blizzard.com',
        'blizzard': 'blizzard.com',
        'playstation': 'playstation.com',
        'xbox': 'xbox.com',
        'nintendo': 'nintendo.com',
        'roblox': 'roblox.com',
        'minecraft': 'minecraft.net',
        'fortnite': 'epicgames.com',
        'pubg': 'pubg.com',
        'leagueoflegends': 'leagueoflegends.com',
        'riot': 'riotgames.com',
        'ea': 'ea.com',
        'ubisoft': 'ubisoft.com',
        'rockstar': 'rockstargames.com',

        # البث
        'netflix': 'netflix.com',
        'hulu': 'hulu.com',
        'disneyplus': 'disneyplus.com',
        'disney': 'disneyplus.com',
        'hbo': 'hbomax.com',
        'hbomax': 'hbomax.com',
        'primevideo': 'primevideo.com',
        'paramount': 'paramountplus.com',
        'peacock': 'peacocktv.com',
        'appletv': 'tv.apple.com',
        'crunchyroll': 'crunchyroll.com',
        'funimation': 'funimation.com',

        # الموسيقى
        'spotify': 'spotify.com',
        'applemusic': 'music.apple.com',
        'youtube': 'youtube.com',
        'youtubemusic': 'music.youtube.com',
        'soundcloud': 'soundcloud.com',
        'pandora': 'pandora.com',
        'deezer': 'deezer.com',
        'tidal': 'tidal.com',
        'amazonmusic': 'music.amazon.com',

        # مواعدة
        'tinder': 'tinder.com',
        'bumble': 'bumble.com',
        'hinge': 'hinge.co',
        'okcupid': 'okcupid.com',
        'match': 'match.com',
        'pof': 'pof.com',
        'badoo': 'badoo.com',
        'coffeemeetsbagel': 'coffeemeetsbagel.com',
        'grindr': 'grindr.com',

        # التعليم
        'coursera': 'coursera.org',
        'udemy': 'udemy.com',
        'skillshare': 'skillshare.com',
        'linkedin': 'linkedin.com',
        'duolingo': 'duolingo.com',
        'khanacademy': 'khanacademy.org',
        'edx': 'edx.org',
        'masterclass': 'masterclass.com',

        # العملات الرقمية
        'coinbase': 'coinbase.com',
        'binance': 'binance.com',
        'kraken': 'kraken.com',
        'gemini': 'gemini.com',
        'bitstamp': 'bitstamp.net',
        'crypto': 'crypto.com',
        'ftx': 'ftx.com',
        'kucoin': 'kucoin.com',
        'bitfinex': 'bitfinex.com',
        'huobi': 'huobi.com',
        'okx': 'okx.com',
        'gate': 'gate.io',

        # أدوات العمل
        'slack': 'slack.com',
        'zoom': 'zoom.us',
        'teams': 'microsoft.com',
        'dropbox': 'dropbox.com',
        'box': 'box.com',
        'notion': 'notion.so',
        'trello': 'trello.com',
        'asana': 'asana.com',
        'monday': 'monday.com',
        'airtable': 'airtable.com',
        'figma': 'figma.com',
        'canva': 'canva.com',
        'adobe': 'adobe.com',
    }

    # البحث عن نطاق مطابق
    domain = domain_mapping.get(cleaned_name)

    # إذا لم يتم العثور على نطاق محدد، نحاول بناء نطاق تلقائي
    if not domain:
        # محاولة بناء نطاق من اسم الخدمة مباشرة
        domain = f"{cleaned_name}.com"

    # استخدام Clearbit Logo API
    # الصيغة: https://logo.clearbit.com/domain.com
    clearbit_url = f"https://logo.clearbit.com/{domain}"

    return clearbit_url


def get_country_flag(country_code: str) -> str:
    """الحصول على علم الدولة"""
    return COUNTRY_FLAGS.get(country_code.upper(), COUNTRY_FLAGS['default'])


SERVICE_ALIASES = {
    'isay': 'ipsos',
    'ipsos': 'ipsos'
}

# أسماء مخصصة للعرض (اسم كامل للخدمات)
SERVICE_DISPLAY_NAMES = {
    'ipsos': 'Ipsos ISay',
    'isay': 'Ipsos ISay'
}


def normalize_service_name(service_name: str) -> str:
    """توحيد أسماء الخدمات المتشابهة"""
    service_lower = service_name.lower()
    return SERVICE_ALIASES.get(service_lower, service_lower)


def get_display_service_name(service_name: str) -> str:
    """الحصول على الاسم الكامل للعرض"""
    service_lower = service_name.lower()
    # البحث عن الاسم في قاموس الأسماء المخصصة
    for key in SERVICE_DISPLAY_NAMES.keys():
        if key in service_lower:
            return SERVICE_DISPLAY_NAMES[key]
    return service_name


def update_products_cache() -> bool:
    """تحديث الـ cache بالمنتجات من API"""
    try:
        current_time = time.time()

        # التحقق من صلاحية الـ cache
        if (current_time - PRODUCTS_CACHE['last_update']) < PRODUCTS_CACHE['cache_duration']:
            return True  # الـ cache لا يزال صالحاً

        logger.info("تحديث cache المنتجات...")

        api = NonVoipAPI()
        all_products = []

        # جلب جميع الأنواع
        for ptype in ['short_term', 'long_term', '3days']:
            result = api.get_products(product_type=ptype)
            if result.get('status') == 'success':
                products = result.get('message', [])
                for product in products:
                    product['type'] = ptype
                    all_products.append(product)

        # تحديث الـ cache
        PRODUCTS_CACHE['data'] = all_products
        PRODUCTS_CACHE['last_update'] = current_time

        logger.info(f"تم تحديث cache بـ {len(all_products)} منتج")
        return True

    except Exception as e:
        logger.error(f"خطأ في تحديث cache المنتجات: {e}")
        return False


async def handle_nonvoip_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج Inline Query للبحث عن خدمات الأرقام Non-Voip - مع اختيار النوع أولاً"""
    query = update.inline_query.query.strip().lower()
    user_id = update.effective_user.id
    
    # تجاهل طلبات PremSocks (تبدأ بـ socks:)
    if query.startswith("socks:"):
        return

    # الحصول على لغة المستخدم
    import sqlite3
    conn = sqlite3.connect(DATABASE_FILE)
    lang = get_user_language(user_id, conn)
    conn.close()

    logger.info(f"🔍 Inline query من المستخدم {user_id}: '{query}'")

    try:
        # إذا كان البحث فارغاً، عرض أنواع الأرقام الثلاثة فقط
        if not query:
            results = []
            
            # النوع الأول: 15 دقيقة
            results.append(
                InlineQueryResultArticle(
                    id='type_short_term',
                    title='⏱️ رقم قصير الأمد (15 دقيقة)' if lang == 'ar' else '⏱️ Short-term (15 min)',
                    description='اكتب: type:short_term ثم اسم الخدمة' if lang == 'ar' else 'Type: type:short_term then service name',
                    input_message_content=InputTextMessageContent(
                        '⏱️ للبحث عن خدمة قصيرة الأمد:\n\nاكتب في خانة البحث:\n`type:short_term اسم_الخدمة`\n\nمثال: type:short_term whatsapp'
                        if lang == 'ar' else
                        '⏱️ To search for short-term service:\n\nType in search:\n`type:short_term service_name`\n\nExample: type:short_term whatsapp',
                        parse_mode='Markdown'
                    ),
                    thumbnail_url='https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Circle-icons-clock.svg/120px-Circle-icons-clock.svg.png'
                )
            )
            
            # النوع الثاني: 3 أيام
            results.append(
                InlineQueryResultArticle(
                    id='type_3days',
                    title='🗓️ رقم لثلاثة أيام' if lang == 'ar' else '🗓️ Three Days Number',
                    description='اكتب: type:3days ثم اسم الخدمة' if lang == 'ar' else 'Type: type:3days then service name',
                    input_message_content=InputTextMessageContent(
                        '🗓️ للبحث عن خدمة 3 أيام:\n\nاكتب في خانة البحث:\n`type:3days اسم_الخدمة`\n\nمثال: type:3days telegram'
                        if lang == 'ar' else
                        '🗓️ To search for 3-day service:\n\nType in search:\n`type:3days service_name`\n\nExample: type:3days telegram',
                        parse_mode='Markdown'
                    ),
                    thumbnail_url='https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Event_note_add_24.svg/120px-Event_note_add_24.svg.png'
                )
            )
            
            # النوع الثالث: 30 يوم
            results.append(
                InlineQueryResultArticle(
                    id='type_long_term',
                    title='📅 رقم طويل الأمد (30 يوماً)' if lang == 'ar' else '📅 Long-term (30 days)',
                    description='اكتب: type:long_term ثم اسم الخدمة' if lang == 'ar' else 'Type: type:long_term then service name',
                    input_message_content=InputTextMessageContent(
                        '📅 للبحث عن خدمة طويلة الأمد:\n\nاكتب في خانة البحث:\n`type:long_term اسم_الخدمة`\n\nمثال: type:long_term google'
                        if lang == 'ar' else
                        '📅 To search for long-term service:\n\nType in search:\n`type:long_term service_name`\n\nExample: type:long_term google',
                        parse_mode='Markdown'
                    ),
                    thumbnail_url='https://upload.wikimedia.org/wikipedia/commons/thumb/7/73/Flat_tick_icon.svg/120px-Flat_tick_icon.svg.png'
                )
            )
            
            await update.inline_query.answer(
                results,
                cache_time=60,
                is_personal=True,
                button=InlineQueryResultsButton(
                    text='💡 اختر نوع الرقم أولاً' if lang == 'ar' else '💡 Select number type first',
                    start_parameter='inline_help'
                )
            )
            return

        # تحديث الـ cache إذا لزم الأمر
        update_products_cache()

        # استخدام المنتجات من الـ cache مباشرة
        all_products = PRODUCTS_CACHE['data'].copy()

        if not all_products:
            update_products_cache()
            all_products = PRODUCTS_CACHE['data'].copy()

        db = NonVoipDB()

        # تحليل الاستعلام لاستخراج نوع الرقم والبحث
        product_type_filter = None
        search_query = query

        # استخراج نوع الرقم بصيغة "type:short_term" أو مباشرة "short_term"
        if query.startswith('type:'):
            # إزالة "type:" من البداية
            query_without_prefix = query[5:].strip()
            
            # البحث عن النوع
            for ptype in ['short_term', 'long_term', '3days']:
                if query_without_prefix.startswith(ptype):
                    product_type_filter = ptype
                    # إزالة النوع من النص المتبقي للبحث
                    search_query = query_without_prefix[len(ptype):].strip()
                    break
        else:
            # الطريقة القديمة: البحث المباشر بدون "type:"
            for ptype in ['short_term', 'long_term', '3days']:
                if query.startswith(ptype):
                    product_type_filter = ptype
                    search_query = query.replace(ptype, '').strip()
                    break

        # تصفية حسب النوع
        if product_type_filter:
            all_products = [p for p in all_products if p.get('type') == product_type_filter]

        # تصفية حسب البحث عن الخدمة (بحث متقدم)
        if search_query:
            search_terms = [normalize_service_name(term) for term in search_query.split()]
            filtered_products = []

            for product in all_products:
                product_name = normalize_service_name(product.get('name', ''))
                # البحث يطابق إذا كانت جميع الكلمات موجودة في اسم الخدمة
                if all(term in product_name for term in search_terms):
                    filtered_products.append(product)
        else:
            # إذا لم يكن هناك بحث عن خدمة، عرض جميع المنتجات المصفاة (محدود بـ 50)
            filtered_products = all_products[:50]

        if not filtered_products:
            # رسالة "لا توجد نتائج" حسب اللغة
            if lang == 'ar':
                no_results_title = '❌ لا توجد نتائج'
                no_results_desc = f'لم يتم العثور على خدمات تطابق "{query}"'
                no_results_text = (
                    f'❌ عذراً، لم يتم العثور على خدمات تطابق "{query}"\n\n'
                    f"💡 جرب البحث عن: WhatsApp, Google, Telegram, Facebook"
                )
            else:
                no_results_title = '❌ No Results'
                no_results_desc = f'No services match "{query}"'
                no_results_text = (
                    f'❌ Sorry, no services match "{query}"\n\n'
                    f'💡 Try searching for: WhatsApp, Google, Telegram, Facebook'
                )

            results = [
                InlineQueryResultArticle(
                    id='no_results',
                    title=no_results_title,
                    description=no_results_desc,
                    input_message_content=InputTextMessageContent(no_results_text)
                )
            ]
            await update.inline_query.answer(results, cache_time=10)
            return

        results = []

        for product in filtered_products[:50]:
            service_name = product.get('name', 'Unknown')
            dollar_price = float(product.get('price', 0))
            available = product.get('available', 0)
            product_id = product.get('product_id')
            product_type = product.get('type', 'short_term')

            # استخدام NonVoipUsNumber العام لجميع الأرقام (يطبق النسبة من إدارة الأسعار)
            credit_price = db.calculate_service_price_in_credits(
                dollar_price,
                service_name='NonVoipUsNumber'
            )

            # الحصول على الاسم الكامل للعرض (مثل: "Ipsos ISay" بدلاً من "ipsos")
            display_name = get_display_service_name(service_name)

            icon = get_service_icon(service_name)
            thumbnail_url = get_service_thumbnail(service_name)

            # نصوص متعددة اللغات
            type_names = {
                'ar': {
                    'short_term': '⏱️ قصير الأمد',
                    'long_term': '📅 طويل الأمد',
                    '3days': '🗓️ 3 أيام'
                },
                'en': {
                    'short_term': '⏱️ Short-term',
                    'long_term': '📅 Long-term',
                    '3days': '🗓️ 3 Days'
                }
            }

            type_label = type_names.get(lang, type_names['ar']).get(product_type, '📱')

            # العنوان: الأيقونة + اسم الخدمة المخصص للعرض
            title = f"{icon} {display_name}"

            # الوصف: السعر + النوع + المتوفر (حسب اللغة)
            if lang == 'ar':
                description = f"💰 {credit_price} كريديت | {type_label} | 📊 {available} متوفر"
            else:
                description = f"💰 {credit_price} credits | {type_label} | 📊 {available} available"

            # محتوى الرسالة عند الاختيار (حسب اللغة)
            if lang == 'ar':
                message_text = f"""
{icon} **{display_name}**

💰 السعر: **{credit_price} كريديت**
📊 المتوفر: {available}
⏱️ النوع: {type_label}

🔒 الرقم سيظهر بعد إتمام عملية الشراء
"""
                buy_button_text = f"🛒 شراء الآن - {credit_price} كريديت"
            else:
                message_text = f"""
{icon} **{display_name}**

💰 Price: **{credit_price} credits**
📊 Available: {available}
⏱️ Type: {type_label}

🔒 Number will appear after purchase
"""
                buy_button_text = f"🛒 Buy Now - {credit_price} credits"

            keyboard = [
                [InlineKeyboardButton(
                    buy_button_text,
                    callback_data=f"nv_buy_{product_id}"
                )]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            results.append(
                InlineQueryResultArticle(
                    id=str(product_id),
                    title=title,
                    description=description,
                    input_message_content=InputTextMessageContent(
                        message_text,
                        parse_mode='Markdown'
                    ),
                    reply_markup=reply_markup,
                    thumbnail_url=thumbnail_url,
                    thumbnail_width=48,
                    thumbnail_height=48
                )
            )

        await update.inline_query.answer(
            results,
            cache_time=60,
            is_personal=True
        )

        logger.info(f"تم إرسال {len(results)} نتيجة للمستخدم {user_id}")

    except Exception as e:
        logger.error(f"خطأ في معالجة inline query: {e}")

        error_result = [
            InlineQueryResultArticle(
                id='error',
                title='❌ حدث خطأ',
                description='يرجى المحاولة مرة أخرى',
                input_message_content=InputTextMessageContent(
                    f'❌ حدث خطأ: {str(e)}'
                )
            )
        ]
        await update.inline_query.answer(error_result, cache_time=10)


async def handle_country_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج اختيار الدولة بعد اختيار الخدمة"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data

    if data.startswith('nv_countries_'):
        product_id = data.replace('nv_countries_', '')

        countries = [
            ('US', 'الولايات المتحدة'),
            ('CA', 'كندا'),
            ('GB', 'بريطانيا'),
            ('FR', 'فرنسا'),
            ('DE', 'ألمانيا'),
            ('IT', 'إيطاليا'),
            ('ES', 'إسبانيا'),
            ('NL', 'هولندا'),
            ('AU', 'أستراليا'),
            ('BR', 'البرازيل'),
            ('MX', 'المكسيك'),
            ('AR', 'الأرجنتين'),
            ('IN', 'الهند'),
            ('PK', 'باكستان'),
            ('BD', 'بنغلاديش'),
            ('ID', 'إندونيسيا'),
            ('MY', 'ماليزيا'),
            ('SG', 'سنغافورة'),
            ('TH', 'تايلاند'),
            ('VN', 'فيتنام'),
            ('PH', 'الفلبين'),
            ('JP', 'اليابان'),
            ('KR', 'كوريا الجنوبية'),
            ('CN', 'الصين'),
            ('RU', 'روسيا'),
            ('UA', 'أوكرانيا'),
            ('PL', 'بولندا'),
            ('RO', 'رومانيا'),
            ('CZ', 'التشيك'),
            ('SE', 'السويد'),
            ('NO', 'النرويج'),
            ('DK', 'الدنمارك'),
            ('FI', 'فنلندا'),
            ('PT', 'البرتغال'),
            ('GR', 'اليونان'),
            ('TR', 'تركيا'),
            ('EG', 'مصر'),
            ('SA', 'السعودية'),
            ('AE', 'الإمارات'),
            ('IL', 'إسرائيل')
        ]

        keyboard = []
        for country_code, country_name in countries:
            flag = get_country_flag(country_code)
            keyboard.append([
                InlineKeyboardButton(
                    f"{flag} {country_name}",
                    callback_data=f"nv_country_{country_code}_{product_id}"
                )
            ])

        lang = get_user_language(user_id)
        
        keyboard.append([
            InlineKeyboardButton(
                "🔙 رجوع" if lang == 'ar' else "🔙 Back", 
                callback_data=f"nv_back_{product_id}"
            )
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        message = "🌍 *اختر الدولة:*\n\nاختر الدولة التي تريد الرقم منها:" if lang == 'ar' else "🌍 *Select Country:*\n\nChoose the country you want the number from:"
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    elif data.startswith('nv_country_'):
        parts = data.split('_')
        country_code = parts[2]
        product_id = parts[3]

        flag = get_country_flag(country_code)
        lang = get_user_language(user_id)

        message = (
            f"✅ تم اختيار {flag}\n\n"
            f"🆔 المنتج: {product_id}\n"
            f"🌍 الدولة: {country_code}\n\n"
            f"للمتابعة مع الشراء، استخدم: /buy_{product_id}_{country_code}"
        ) if lang == 'ar' else (
            f"✅ Selected {flag}\n\n"
            f"🆔 Product: {product_id}\n"
            f"🌍 Country: {country_code}\n\n"
            f"To proceed with purchase, use: /buy_{product_id}_{country_code}"
        )
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown'
        )


async def handle_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج زر الشراء المباشر من Inline Query"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data

    if not data.startswith('nv_buy_'):
        return

    product_id = int(data.replace('nv_buy_', ''))

    try:
        # فتح اتصال قاعدة البيانات
        import sqlite3
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # الحصول على لغة المستخدم
        lang = get_user_language(user_id, conn)

        # جلب معلومات المنتج من API
        api = NonVoipAPI()
        db = NonVoipDB()

        # محاولة جلب المنتج من جميع الأنواع
        product = None
        for ptype in ['short_term', 'long_term', '3days']:
            result = api.get_products(product_type=ptype, product_id=product_id)
            if result.get('status') == 'success' and result.get('message'):
                product = result['message'][0]
                product['type'] = ptype
                break

        if not product:
            await query.edit_message_text(
                "❌ عذراً، هذا المنتج غير متاح حالياً" if lang == 'ar'
                else "❌ Sorry, this product is not available"
            )
            conn.close()
            return

        # حساب السعر - استخدام NonVoipUsNumber العام لجميع الأرقام
        dollar_price = float(product.get('price', 0))
        credit_price = db.calculate_service_price_in_credits(
            dollar_price,
            service_name='NonVoipUsNumber'
        )

        # التحقق من رصيد المستخدم
        cursor.execute("SELECT (COALESCE(credits_balance, 0) + COALESCE(referral_balance, 0)) as total_balance FROM users WHERE user_id = ?", (user_id,))
        user_balance_row = cursor.fetchone()
        user_balance = user_balance_row[0] if user_balance_row else 0.0

        if user_balance < credit_price:
            await query.edit_message_text(
                f"❌ رصيدك غير كافٍ!\n\n💰 رصيدك الحالي: {user_balance} كريديت\n💵 المطلوب: {credit_price} كريديت\n\nيرجى شحن الرصيد أولاً"
                if lang == 'ar' else
                f"❌ Insufficient balance!\n\n💰 Your balance: {user_balance} credits\n💵 Required: {credit_price} credits\n\nPlease recharge first"
            )
            conn.close()
            return

        # تأكيد الشراء
        icon = get_service_icon(product.get('name', ''))
        type_ar = {
            'short_term': '⏱️ قصير الأمد',
            'long_term': '📅 طويل الأمد',
            '3days': '🗓️ 3 أيام'
        }.get(product.get('type', ''), '📱')

        confirm_message = (
            f"📱 **تأكيد الشراء**\n\n"
            f"🏷️ الخدمة: **{product.get('name', 'Unknown')}**\n"
            f"⏱️ النوع: {type_ar}\n"
            f"💰 السعر: **{credit_price} كريديت**\n"
            f"📊 المتوفر: {product.get('available', 0)}\n\n"
            f"💳 رصيدك الحالي: {user_balance} كريديت\n"
            f"💳 رصيدك بعد الشراء: {user_balance - credit_price} كريديت\n\n"
            f"هل تريد المتابعة؟"
            if lang == 'ar' else
            f"📱 **Confirm Purchase**\n\n"
            f"🏷️ Service: **{product.get('name', 'Unknown')}**\n"
            f"⏱️ Type: {type_ar}\n"
            f"💰 Price: **{credit_price} credits**\n"
            f"📊 Available: {product.get('available', 0)}\n\n"
            f"💳 Current balance: {user_balance} credits\n"
            f"💳 Balance after purchase: {user_balance - credit_price} credits\n\n"
            f"Do you want to proceed?"
        )

        keyboard = [
            [InlineKeyboardButton(
                "✅ نعم، اشترِ الآن" if lang == 'ar' else "✅ Yes, Buy Now",
                callback_data=f"nv_confirm_buy_{product_id}"
            )],
            [InlineKeyboardButton(
                "❌ إلغاء" if lang == 'ar' else "❌ Cancel",
                callback_data="nv_cancel_buy"
            )]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        # حفظ معلومات المنتج في context للاستخدام عند التأكيد
        context.user_data['pending_product'] = product
        context.user_data['pending_credit_price'] = credit_price

        await query.edit_message_text(
            confirm_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        conn.close()

    except Exception as e:
        logger.error(f"خطأ في معالجة الشراء: {e}")
        await query.edit_message_text(
            f"❌ حدث خطأ: {str(e)}"
        )



async def handle_confirm_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج تأكيد الشراء النهائي"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data

    # معالجة إلغاء الشراء
    if data == "nv_cancel_buy":
        await query.edit_message_text(
            "❌ تم إلغاء عملية الشراء"
        )
        return

    # معالجة تأكيد الشراء
    if not data.startswith("nv_confirm_buy_"):
        return

    product_id = int(data.replace("nv_confirm_buy_", ""))

    try:
        # فتح اتصال قاعدة البيانات
        import sqlite3
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # الحصول على لغة المستخدم
        lang = get_user_language(user_id, conn)

        # جلب المنتج المحفوظ من context
        product = context.user_data.get("pending_product")
        credit_price = context.user_data.get("pending_credit_price")

        if not product or not credit_price:
            await query.edit_message_text(
                "❌ انتهت صلاحية الطلب. يرجى المحاولة مرة أخرى"
            )
            conn.close()
            return

        await query.edit_message_text(
            "⏳ جاري معالجة طلبك..." if lang == "ar"
            else "⏳ Processing your order..."
        )

        # التحقق من الرصيد مرة أخرى
        cursor.execute("SELECT (COALESCE(credits_balance, 0) + COALESCE(referral_balance, 0)) as total_balance FROM users WHERE user_id = ?", (user_id,))
        user_balance_row = cursor.fetchone()
        user_balance = user_balance_row[0] if user_balance_row else 0.0

        if user_balance < credit_price:
            await query.edit_message_text(
                f"❌ رصيدك غير كافٍ!\n\n💰 رصيدك: {user_balance} كريديت\n💵 المطلوب: {credit_price} كريديت"
                if lang == "ar" else
                f"❌ Insufficient balance!\n\n💰 Your balance: {user_balance} credits\n💵 Required: {credit_price} credits"
            )
            conn.close()
            return

        # التحقق من حد الأرقام النشطة (short_term فقط - 15 دقيقة)
        product_type = product.get('type', 'short_term')
        if product_type == 'short_term':
            # التحقق من عدد الأرقام النشطة من نوع short_term
            cursor.execute("""
                SELECT COUNT(*) FROM nonvoip_orders
                WHERE user_id = ?
                AND type = 'short_term'
                AND status IN ('pending', 'reserved', 'active')
                AND (expires_at IS NULL OR expires_at > datetime('now'))
            """, (user_id,))
            active_short_term_count = cursor.fetchone()[0]

            if active_short_term_count >= 2:
                await query.edit_message_text(
                    f"⛔ تجاوزت الحد المسموح!\n\nلديك بالفعل {active_short_term_count} رقم نشط من نوع 15 دقيقة\nالحد الأقصى: رقمين نشطين في نفس الوقت\n\nيرجى الانتظار حتى ينتهي أحد الأرقام أو استخدام الأرقام طويلة الأمد"
                    if lang == "ar" else
                    f"⛔ Limit Exceeded!\n\nYou already have {active_short_term_count} active 15-minute number(s)\nMaximum allowed: 2 active numbers at once\n\nPlease wait for one to expire or use long-term numbers"
                )
                conn.close()
                return

        # طلب الرقم من API
        api = NonVoipAPI()
        db = NonVoipDB()

        order_result = api.order(product_id=product_id)

        if order_result.get("status") != "success":
            actual_error = order_result.get("message", "خطأ غير معروف")
            error_code = get_error_code_from_message(actual_error)
            log_api_error(error_code, actual_error, f"user_id:{user_id}, product_id:{product_id}")

            error_display = (
                f"❌ *فشل الطلب*\n\n"
                f"⚠️ حدث خطأ أثناء معالجة طلبك\n"
                f"🔍 رمز الخطأ: `{error_code}`\n\n"
                f"💬 يرجى التواصل مع الدعم وإرفاق رمز الخطأ\n"
                f"ليتم المعالجة في أقرب وقت"
            ) if lang == "ar" else (
                f"❌ *Order Failed*\n\n"
                f"⚠️ An error occurred while processing your order\n"
                f"🔍 Error Code: `{error_code}`\n\n"
                f"💬 Please contact support with the error code\n"
                f"to be resolved as soon as possible"
            )

            await query.edit_message_text(
                error_display,
                parse_mode="Markdown"
            )
            conn.close()
            return

        # تم الطلب بنجاح
        order_info = order_result["message"][0]

        # خصم النقاط من رصيد المستخدم
        # خصم من credits_balance أولاً، ثم من referral_balance إذا لزم الأمر
        cursor.execute("SELECT COALESCE(credits_balance, 0), COALESCE(referral_balance, 0) FROM users WHERE user_id = ?", (user_id,))
        balances = cursor.fetchone()
        credits_bal = balances[0] if balances else 0.0
        referral_bal = balances[1] if balances else 0.0

        if credits_bal >= credit_price:
            # خصم من credits_balance فقط
            cursor.execute("UPDATE users SET credits_balance = credits_balance - ? WHERE user_id = ?", (credit_price, user_id))
        else:
            # خصم من credits_balance بالكامل ثم من referral_balance
            remaining = credit_price - credits_bal
            cursor.execute("UPDATE users SET credits_balance = 0, referral_balance = referral_balance - ? WHERE user_id = ?", (remaining, user_id))
        conn.commit()

        # حفظ الطلب في قاعدة البيانات
        dollar_price = float(product.get("price", 0))
        db.save_order(
            user_id=user_id,
            order_data=order_info,
            cost_price=dollar_price,
            sale_price=credit_price
        )

        # إرسال معلومات الرقم للمستخدم
        number = order_info.get("number", "في انتظار التخصيص")
        service_name = order_info.get("service", product.get("name", "Unknown"))
        order_id = order_info.get("order_id")
        expires = order_info.get("expires", "غير محدد")
        expiration_seconds = int(order_info.get("expiration", 900))
        number_type = order_info.get("type", product.get("type", "short_term"))

        # تنسيق نوع الرقم والمدة
        type_names = {
            'ar': {
                'short_term': '⏱️ قصير الأمد',
                'long_term': '📅 طويل الأمد',
                '3days': '🗓️ 3 أيام'
            },
            'en': {
                'short_term': '⏱️ Short-term',
                'long_term': '📅 Long-term',
                '3days': '🗓️ 3 Days'
            }
        }
        type_label = type_names.get(lang, type_names['ar']).get(number_type, '📱')
        duration_text = format_expiration_time(expiration_seconds, lang)

        cursor.execute("SELECT COALESCE(credits_balance, 0) + COALESCE(referral_balance, 0) FROM users WHERE user_id = ?", (user_id,))
        new_balance_row = cursor.fetchone()
        new_balance = new_balance_row[0] if new_balance_row else 0.0

        icon = get_service_icon(service_name)

        success_message = (
            f"✅ **تم شراء الرقم بنجاح!**\n\n"
            f"{icon} **الخدمة:** {service_name}\n"
            f"📱 **الرقم:** `{number}`\n"
            f"🆔 **رقم الطلب:** `{order_id}`\n"
            f"⏱️ **النوع:** {type_label} - المدة: {duration_text}\n"
            f"⏰ **ينتهي في:** {expires}\n\n"
            f"💳 **رصيدك الجديد:** {new_balance} كريديت\n\n"
            f"📬 **انتظار الرسالة...**\n"
            f"سيتم إرسال الرسالة فوراً عند وصولها\n"
            f"⏳ مراقبة تلقائية نشطة\n\n"
            f"⚠️ في حال عدم وصول رسالة، سيتم استرداد الرصيد تلقائياً"
            if lang == "ar" else
            f"✅ **Number Purchased Successfully!**\n\n"
            f"{icon} **Service:** {service_name}\n"
            f"📱 **Number:** `{number}`\n"
            f"🆔 **Order ID:** `{order_id}`\n"
            f"⏱️ **Type:** {type_label} - Duration: {duration_text}\n"
            f"⏰ **Expires:** {expires}\n\n"
            f"💳 **New Balance:** {new_balance} credits\n\n"
            f"📬 **Waiting for message...**\n"
            f"Message will be sent immediately when received\n"
            f"⏳ Auto-monitoring active\n\n"
            f"⚠️ If no message arrives, credits will be refunded automatically"
        )

        cancel_keyboard = [[InlineKeyboardButton(
            "❌ إلغاء وإعادة الرصيد" if lang == "ar" else "❌ Cancel & Refund",
            callback_data=f"nv_cancel_order_{order_id}"
        )]]
        cancel_markup = InlineKeyboardMarkup(cancel_keyboard)

        # الحصول على message_id من الرسالة الموجودة قبل تحديثها
        message_id = query.message.message_id if query.message else None

        # تحديث الرسالة بالمحتوى الجديد
        await query.edit_message_text(
            success_message,
            reply_markup=cancel_markup,
            parse_mode="Markdown"
        )
        
        # إرسال رسائل تحذير للأرقام 3d و long_term
        if number_type in ['3days', 'long_term']:
            # رسالة تحذير أولى ⚠️
            warning_msg_1 = "⚠️" if lang == "ar" else "⚠️"
            await context.bot.send_message(
                chat_id=user_id,
                text=warning_msg_1
            )
            
            # رسالة تحذير ثانية مفصلة
            warning_msg_2 = (
                f"⚠️ **تنبيه هام:**\n\n"
                f"🔴 يجب تفعيل الرقم قبل طلب أي كود من التطبيق!\n\n"
                f"📱 الرقم: `{number}`\n"
                f"✅ استخدم زر التفعيل أولاً، ثم اطلب الكود\n\n"
                f"💡 بدون تفعيل، لن تصل الرسائل للرقم"
            ) if lang == "ar" else (
                f"⚠️ **Important Notice:**\n\n"
                f"🔴 You must activate the number before requesting any code from the app!\n\n"
                f"📱 Number: `{number}`\n"
                f"✅ Use the Activate button first, then request the code\n\n"
                f"💡 Without activation, messages won't arrive to the number"
            )
            
            await context.bot.send_message(
                chat_id=user_id,
                text=warning_msg_2,
                parse_mode="Markdown"
            )

        # حفظ message_id في قاعدة البيانات لتفعيل المراقبة التلقائية
        if message_id and order_id:
            db.set_order_message_id(order_id, message_id)
            logger.info(f"✅ تم حفظ message_id={message_id} للطلب {order_id}")
        else:
            logger.warning(f"⚠️ لم يتم الحصول على message_id للطلب {order_id}")

        # تنظيف البيانات المؤقتة
        context.user_data.pop("pending_product", None)
        context.user_data.pop("pending_credit_price", None)

        conn.close()

        logger.info(f"تم شراء رقم بنجاح للمستخدم {user_id}: {number}")

        # بدء مراقبة الرقم تلقائياً فقط إذا كان لدينا message_id
        if message_id:
            asyncio.create_task(monitor_order_for_sms(
                application=context.application,
                user_id=user_id,
                order_id=order_id,
                service=service_name,
                number=number,
                message_id=message_id,
                expiration_seconds=expiration_seconds,
                lang=lang
            ))
        else:
            logger.warning(f"لم يتم الحصول على message_id للطلب {order_id} - المراقبة التلقائية غير نشطة")

    except Exception as e:
        logger.error(f"خطأ في تأكيد الشراء: {e}")
        try:
            if query.message:
                await query.edit_message_text(
                    f"❌ حدث خطأ: {str(e)}"
                )
            else:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"❌ حدث خطأ: {str(e)}"
                )
        except Exception as send_error:
            logger.error(f"فشل إرسال رسالة الخطأ: {send_error}")


# ═══════════════════════════════════════════════════════════════════════════════
# PART 7: NUMBER ACTIVATION SYSTEM (3DAYS & LONG-TERM NUMBERS)
# ═══════════════════════════════════════════════════════════════════════════════

async def handle_activate_number_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج زر تفعيل الرقم للأرقام طويلة المدى"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if not data.startswith("nv_activate_"):
        return
    
    order_id = int(data.replace("nv_activate_", ""))
    
    try:
        import sqlite3
        conn = sqlite3.connect(DATABASE_FILE)
        lang = get_user_language(user_id, conn)
        db = NonVoipDB()
        
        # الحصول على معلومات الطلب
        cursor = conn.cursor()
        cursor.execute("""
            SELECT order_id, number, service, type, activation_status, activated_until
            FROM nonvoip_orders
            WHERE order_id = ? AND user_id = ?
        """, (order_id, user_id))
        
        order_row = cursor.fetchone()
        conn.close()
        
        if not order_row:
            await query.edit_message_text(
                "❌ الطلب غير موجود" if lang == "ar" else "❌ Order not found"
            )
            return
        
        _, number, service, order_type, activation_status, activated_until = order_row
        
        # التحقق من نوع الرقم
        if order_type not in ['3days', 'long_term']:
            await query.answer(
                "⚠️ هذه الميزة للأرقام طويلة المدى فقط" if lang == "ar" else "⚠️ This feature is for long-term numbers only",
                show_alert=True
            )
            return
        
        # التحقق من حالة التفعيل الحالية
        import pytz
        from datetime import datetime
        syria_tz = pytz.timezone(Config.TIMEZONE)
        now = datetime.now(syria_tz)
        
        is_currently_active = False
        if activation_status == 'active' and activated_until:
            try:
                from dateutil import parser
                end_time = parser.parse(activated_until)
                if end_time.tzinfo is None:
                    end_time = pytz.UTC.localize(end_time)
                end_time_syria = end_time.astimezone(syria_tz)
                is_currently_active = now < end_time_syria
            except:
                pass
        
        if is_currently_active:
            remaining = format_activation_time(activated_until, lang)
            # رسالة تفصيلية عند الضغط على زر التفعيل لرقم مفعل بالفعل
            active_msg = (
                f"✅ *الرقم مفعّل بالفعل!*\n\n"
                f"📱 الرقم: `{number}`\n"
                f"🔥 جاهز لاستقبال الرسائل\n"
                f"⏳ الوقت المتبقي: {remaining}\n\n"
                f"💡 يمكنك طلب الكود الآن من التطبيق"
            ) if lang == "ar" else (
                f"✅ *Number is already activated!*\n\n"
                f"📱 Number: `{number}`\n"
                f"🔥 Ready to receive messages\n"
                f"⏳ Time remaining: {remaining}\n\n"
                f"💡 You can request the code now from the app"
            )
            
            # إرسال إشعار بسيط
            await query.answer("✅ مفعل" if lang == "ar" else "✅ Activated", show_alert=False)
            
            # بناء الأزرار المحدثة
            try:
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                
                keyboard = [[InlineKeyboardButton(
                    "📊 تفاصيل الرقم" if lang == 'ar' else "📊 Details",
                    callback_data=f"nv_manual_check_{order_id}"
                )]]
                
                # زر التفعيل المحدث - يعرض الإيموجي ✅ والوقت المتبقي
                button_text = f"✅ مفعل ({remaining})" if lang == 'ar' else f"✅ Activated ({remaining})"
                keyboard.append([InlineKeyboardButton(
                    button_text,
                    callback_data=f"nv_activate_{order_id}"
                )])
                
                keyboard.append([InlineKeyboardButton(
                    "🔙 العودة لأرقامي" if lang == 'ar' else "🔙 Back to My Numbers",
                    callback_data='nv_my_numbers'
                )])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # تحديث الرسالة مع النص الجديد والأزرار المحدثة
                await query.edit_message_text(active_msg, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            except Exception as edit_error:
                logger.warning(f"فشل تحديث الرسالة: {edit_error}")
                # إرسال رسالة جديدة إذا فشل التحديث
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=active_msg,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
            
            return
        
        # إجراء التفعيل
        api = NonVoipAPI()
        result = api.activate(service=service, number=number)
        
        if result.get('status') == 'success':
            activation_data = result.get('message', [{}])[0]
            end_time_str = activation_data.get('end_on')
            
            # تحديث قاعدة البيانات
            db.update_activation_status(order_id, 'active', end_time_str)
            
            # حساب الوقت المتبقي والمدة من API
            remaining = format_activation_time(end_time_str, lang)
            
            # حساب مدة التفعيل من البيانات المرجعة من API
            duration_text = None
            try:
                from dateutil import parser
                from datetime import datetime
                import pytz
                
                # تحويل وقت الانتهاء
                end_dt = parser.parse(end_time_str)
                if end_dt.tzinfo is None:
                    end_dt = pytz.UTC.localize(end_dt)
                
                # الوقت الحالي بـ UTC
                now_dt = datetime.now(pytz.UTC)
                
                # حساب المدة بالدقائق
                duration_seconds = (end_dt - now_dt).total_seconds()
                duration_minutes = int(duration_seconds / 60)
                
                # تأكد من أن المدة إيجابية
                if duration_minutes > 0:
                    duration_text = f"{duration_minutes} دقيقة" if lang == "ar" else f"{duration_minutes} minutes"
                else:
                    logger.warning(f"المدة المحسوبة سالبة أو صفر: {duration_minutes} دقيقة")
                    
            except Exception as calc_error:
                logger.error(f"خطأ في حساب مدة التفعيل: {calc_error} - end_time_str: {end_time_str}")
            
            # استخدام القيمة من API مباشرة إذا فشل الحساب
            if not duration_text:
                # محاولة جلب المدة من بيانات API مباشرة
                try:
                    duration_from_api = activation_data.get('duration')
                    if duration_from_api:
                        duration_text = f"{duration_from_api} دقيقة" if lang == "ar" else f"{duration_from_api} minutes"
                        logger.info(f"استخدام المدة من API: {duration_from_api}")
                    else:
                        duration_text = "غير محدد" if lang == "ar" else "Not specified"
                        logger.warning("لم يتم العثور على مدة التفعيل في استجابة API")
                except:
                    duration_text = "غير محدد" if lang == "ar" else "Not specified"
            
            success_msg = (
                f"✅ *تم تفعيل الرقم بنجاح!*\n\n"
                f"📱 الرقم: `{number}`\n"
                f"⏱️ مدة التفعيل: {duration_text}\n"
                f"⏳ الوقت المتبقي: {remaining}\n\n"
                f"🔥 الرقم جاهز الآن لاستقبال الرسائل"
            ) if lang == "ar" else (
                f"✅ *Number activated successfully!*\n\n"
                f"📱 Number: `{number}`\n"
                f"⏱️ Activation duration: {duration_text}\n"
                f"⏳ Time remaining: {remaining}\n\n"
                f"🔥 Number is now ready to receive messages"
            )
            
            await query.answer("✅ تم التفعيل!" if lang == "ar" else "✅ Activated!", show_alert=True)
            
            # تحديث الرسالة وتحديث الزر ليعكس الحالة الجديدة
            try:
                # بناء الأزرار الجديدة مع حالة التفعيل المحدثة
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                
                keyboard = [[InlineKeyboardButton(
                    "📊 تفاصيل الرقم" if lang == 'ar' else "📊 Details",
                    callback_data=f"nv_manual_check_{order_id}"
                )]]
                
                # زر التفعيل المحدث - يعرض الإيموجي ✅ والوقت المتبقي
                button_text = f"✅ مفعل ({remaining})" if lang == 'ar' else f"✅ Activated ({remaining})"
                keyboard.append([InlineKeyboardButton(
                    button_text,
                    callback_data=f"nv_activate_{order_id}"
                )])
                
                keyboard.append([InlineKeyboardButton(
                    "🔙 العودة لأرقامي" if lang == 'ar' else "🔙 Back to My Numbers",
                    callback_data='nv_my_numbers'
                )])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # تحديث الرسالة بالنص الجديد فقط (بدون إضافته للنص القديم)
                await query.edit_message_text(success_msg, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            except Exception as edit_error:
                logger.warning(f"فشل تحديث الرسالة: {edit_error}")
                await context.bot.send_message(
                    chat_id=user_id,
                    text=success_msg,
                    parse_mode=ParseMode.MARKDOWN
                )
            
            logger.info(f"✅ تم تفعيل الرقم {number} - الطلب {order_id} - بواسطة المستخدم {user_id}")
        else:
            error_msg = result.get('message', 'Unknown error')
            await query.answer(
                f"❌ فشل التفعيل: {error_msg}" if lang == "ar" else f"❌ Activation failed: {error_msg}",
                show_alert=True
            )
            logger.warning(f"⚠️ فشل التفعيل اليدوي للطلب {order_id}: {error_msg}")
    
    except Exception as e:
        logger.error(f"❌ خطأ في معالج التفعيل: {e}")
        await query.answer(
            f"❌ حدث خطأ: {str(e)}" if lang == "ar" else f"❌ Error: {str(e)}",
            show_alert=True
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PART 8: ORDER CANCELLATION AND AUTO-REFUND SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

async def handle_cancel_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج زر إلغاء الطلب مع استرداد الرصيد"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data

    if not data.startswith("nv_cancel_order_"):
        return

    order_id = int(data.replace("nv_cancel_order_", ""))

    try:
        import sqlite3
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        lang = get_user_language(user_id, conn)

        cursor.execute("""
            SELECT order_id, number, service, sale_price, status, refunded, sms_sent, type, created_at, expires_at
            FROM nonvoip_orders
            WHERE order_id = ? AND user_id = ?
        """, (order_id, user_id))

        order_row = cursor.fetchone()

        if not order_row:
            await query.edit_message_text(
                "❌ الطلب غير موجود" if lang == "ar" else "❌ Order not found"
            )
            conn.close()
            return

        db_order_id, number, service, sale_price, status, refunded, sms_sent, order_type, created_at, expires_at = order_row

        if refunded:
            await query.edit_message_text(
                "⚠️ تم استرداد الرصيد لهذا الطلب مسبقاً" if lang == "ar"
                else "⚠️ Credit already refunded for this order"
            )
            conn.close()
            return

        if sms_sent:
            await query.edit_message_text(
                "⚠️ لا يمكن الإلغاء - تم استلام الرسالة بالفعل" if lang == "ar"
                else "⚠️ Cannot cancel - message already received"
            )
            conn.close()
            return

        # قواعد منع الإلغاء
        # 1. منع إلغاء الأرقام الشهرية و3 أيام نهائياً
        if order_type in ['long_term', '3days']:
            await query.edit_message_text(
                "❌ لا يمكن إلغاء الأرقام الشهرية أو أرقام 3 أيام\n\n"
                "هذه الأرقام غير قابلة للإلغاء حسب سياسة الخدمة"
                if lang == "ar" else
                "❌ Cannot cancel monthly or 3-day numbers\n\n"
                "These numbers are non-refundable according to service policy"
            )
            conn.close()
            return

        # 2. منع إلغاء الأرقام بعد انتهاء صلاحيتها بسبب الوقت
        if expires_at:
            from datetime import datetime
            try:
                expiry_time = datetime.fromisoformat(expires_at)
                if datetime.now() >= expiry_time:
                    await query.edit_message_text(
                        "❌ لا يمكن الإلغاء - انتهت صلاحية الرقم\n\n"
                        "تم استرداد الكريديت تلقائياً عند انتهاء الصلاحية"
                        if lang == "ar" else
                        "❌ Cannot cancel - number has expired\n\n"
                        "Credits were automatically refunded upon expiration"
                    )
                    conn.close()
                    return
            except:
                pass

        # 3. منع إلغاء أرقام 15 دقيقة قبل مرور 5 دقائق من الشراء
        if order_type == 'short_term':
            from datetime import datetime, timedelta
            created_time = datetime.fromisoformat(created_at)
            elapsed_time = datetime.now() - created_time

            if elapsed_time < timedelta(minutes=5):
                remaining_seconds = int((timedelta(minutes=5) - elapsed_time).total_seconds())
                remaining_minutes = remaining_seconds // 60
                remaining_secs = remaining_seconds % 60
                
                # تسجيل محاولة إلغاء فاشلة (قبل الوقت المسموح)
                import sys
                sys.path.insert(0, '/home/runner/workspace')
                from bot import log_nonvoip_purchase
                log_nonvoip_purchase(
                    user_id=user_id,
                    username=f'user_{user_id}',
                    order_id=order_id,
                    number_type=order_type,
                    service_type=service,
                    price_usd=0,
                    price_credits=0,
                    credit_deducted=0,
                    notes=f"FAILED_CANCEL_EARLY - Too early (waited {elapsed_time.total_seconds():.0f}s, need 300s)"
                )

                await query.edit_message_text(
                    f"⏰ لا يمكن الإلغاء قبل مرور 5 دقائق من الشراء\n\n"
                    f"⏳ الوقت المتبقي: {remaining_minutes} دقيقة و {remaining_secs} ثانية\n\n"
                    f"يرجى الانتظار ثم المحاولة مرة أخرى"
                    if lang == "ar" else
                    f"⏰ Cannot cancel before 5 minutes from purchase\n\n"
                    f"⏳ Remaining time: {remaining_minutes} min {remaining_secs} sec\n\n"
                    f"Please wait and try again"
                )
                conn.close()
                return

        await query.edit_message_text(
            "⏳ جاري إلغاء الطلب..." if lang == "ar" else "⏳ Cancelling order..."
        )

        api = NonVoipAPI()
        reject_result = api.reject(service=service, number=number, order_id=order_id)

        refund_successful = False
        error_message = ""

        if reject_result.get("status") == "success":
            refund_successful = True
        else:
            error_message = reject_result.get("message", "Unknown error")
            if "already" in error_message.lower() or "delivered" in error_message.lower():
                await query.edit_message_text(
                    f"⚠️ الرقم قد استلم رسالة بالفعل - لا يمكن الإلغاء\n\n{error_message}"
                    if lang == "ar" else
                    f"⚠️ Number already received message - cannot cancel\n\n{error_message}"
                )
                conn.close()
                return
            elif "not" in error_message.lower() and "allow" in error_message.lower():
                refund_successful = True
                logger.warning(f"الموقع لا يسمح بالإلغاء لكن سنسترد الرصيد للمستخدم: {error_message}")

        cursor.execute("SELECT COALESCE(credits_balance, 0), COALESCE(referral_balance, 0) FROM users WHERE user_id = ?", (user_id,))
        balances = cursor.fetchone()
        old_credits = balances[0] if balances else 0.0

        cursor.execute("UPDATE users SET credits_balance = credits_balance + ? WHERE user_id = ?", (sale_price, user_id))

        cursor.execute("""
            UPDATE nonvoip_orders
            SET status = 'cancelled', refunded = 1, updated_at = CURRENT_TIMESTAMP
            WHERE order_id = ?
        """, (order_id,))
        
        # تسجيل معاملة الاسترداد في credits_transactions
        cursor.execute("""
            INSERT INTO credits_transactions (user_id, transaction_type, amount, order_id, description)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, 'nonvoip_refund', sale_price, str(order_id), 
              f"استرداد رقم {service} - إلغاء الطلب"))
        logger.info(f"✅ تم تسجيل معاملة استرداد NonVoIP للمستخدم {user_id}: +{sale_price} كريديت")

        conn.commit()
        
        # تسجيل العملية في اللوغز
        log_refund_operation(
            order_id=order_id,
            user_id=user_id,
            operation_type='manual_cancel',
            refund_amount=sale_price,
            reason=f'User cancelled order via cancel & refund button - Type: {order_type}',
            status='success',
            details=f'API Response: {reject_result.get("status")}, Service: {service}, Number: {number}'
        )
        
        # تسجيل الإلغاء في nonvoip_purchase_logs
        import sys
        sys.path.insert(0, '/home/runner/workspace')
        from bot import update_purchase_cancel
        update_purchase_cancel(order_id)

        # إخفاء الرقم من My Numbers بعد الإلغاء - مع الحفاظ على السجل في History
        cursor.execute("""
            UPDATE nonvoip_orders 
            SET visible_in_my_numbers = 0, updated_at = CURRENT_TIMESTAMP
            WHERE order_id = ?
        """, (order_id,))
        conn.commit()
        logger.info(f"✅ تم إخفاء الرقم {order_id} من My Numbers (cancelled - محفوظ في History)")

        new_balance = old_credits + sale_price

        success_msg = (
            f"✅ *تم إلغاء الطلب بنجاح!*\n\n"
            f"🆔 رقم الطلب: `{order_id}`\n"
            f"💰 تم استرداد: {sale_price} كريديت\n"
            f"💳 رصيدك الجديد: {new_balance} كريديت\n\n"
            f"{'⚠️ لم يتمكن الموقع من استرداد الرقم، لكن تم استرداد رصيدك' if not reject_result.get('status') == 'success' else '✅ تم استرداد الرقم للموقع'}"
            if lang == "ar" else
            f"✅ *Order Cancelled Successfully!*\n\n"
            f"🆔 Order ID: `{order_id}`\n"
            f"💰 Refunded: {sale_price} credits\n"
            f"💳 New Balance: {new_balance} credits\n\n"
            f"{'⚠️ Website could not refund number, but your credits were refunded' if not reject_result.get('status') == 'success' else '✅ Number returned to website'}"
        )

        await query.edit_message_text(success_msg, parse_mode="Markdown")

        logger.info(f"تم إلغاء الطلب {order_id} للمستخدم {user_id} واسترداد {sale_price} كريديت")

        conn.close()

    except Exception as e:
        logger.error(f"خطأ في إلغاء الطلب: {e}")
        await query.edit_message_text(
            f"❌ حدث خطأ أثناء الإلغاء: {str(e)}"
        )


async def handle_manual_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج زر التفاصيل - عرض تفاصيل شاملة للرقم"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data

    if not data.startswith("nv_manual_check_"):
        return

    order_id = int(data.replace("nv_manual_check_", ""))

    conn = None
    try:
        conn = await aiosqlite.connect(DATABASE_FILE)

        # الحصول على لغة المستخدم
        async with conn.execute("SELECT language FROM users WHERE user_id = ?", (user_id,)) as cursor:
            lang_row = await cursor.fetchone()
        lang = lang_row[0] if lang_row and lang_row[0] else 'ar'

        # جلب معلومات الطلب الكاملة
        async with conn.execute("""
            SELECT number, service, type, status, created_at, expires_at, renewed, sms_received, pin_code, activation_status, activated_until
            FROM nonvoip_orders
            WHERE order_id = ? AND user_id = ?
        """, (order_id, user_id)) as cursor:
            order_row = await cursor.fetchone()

        if not order_row:
            await query.edit_message_text(
                "❌ الطلب غير موجود" if lang == "ar" else "❌ Order not found"
            )
            return

        number, service, order_type, status, created_at, expires_at, renewed, sms_received, pin_code, activation_status, activated_until = order_row

        display_service = get_display_service_name(service)
        icon = get_service_icon(service)
        
        # تحديد رمز الحالة
        status_emoji = {
            'active': '✅',
            'delivered': '📨',
            'expired': '⏰',
            'cancelled': '❌',
            'pending': '⏳',
            'reserved': '🔒'
        }.get(status, '❓')
        
        # تحديد النص للحالة
        status_text = {
            'active': 'نشط' if lang == 'ar' else 'Active',
            'delivered': 'تم التسليم' if lang == 'ar' else 'Delivered',
            'expired': 'منتهي' if lang == 'ar' else 'Expired',
            'cancelled': 'ملغي' if lang == 'ar' else 'Cancelled',
            'pending': 'معلق' if lang == 'ar' else 'Pending',
            'reserved': 'محجوز' if lang == 'ar' else 'Reserved'
        }.get(status, status)
        
        # حساب الوقت المتبقي
        from datetime import datetime
        time_remaining = "N/A"
        
        if expires_at:
            try:
                expire_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                now = datetime.now()
                delta = expire_time - now
                
                if delta.total_seconds() > 0:
                    days = delta.days
                    hours = delta.seconds // 3600
                    minutes = (delta.seconds % 3600) // 60
                    
                    if days > 0:
                        time_remaining = f"{days} يوم {hours} ساعة" if lang == 'ar' else f"{days}d {hours}h"
                    elif hours > 0:
                        time_remaining = f"{hours} ساعة {minutes} دقيقة" if lang == 'ar' else f"{hours}h {minutes}m"
                    else:
                        time_remaining = f"{minutes} دقيقة" if lang == 'ar' else f"{minutes}m"
                else:
                    time_remaining = "منتهي" if lang == 'ar' else "Expired"
            except:
                time_remaining = "N/A"
        
        # بناء رسالة التفاصيل
        message = (
            f"📊 **تفاصيل الرقم**\n\n" if lang == 'ar' else f"📊 **Number Details**\n\n"
        )
        
        message += (
            f"{icon} **الخدمة:** {display_service}\n"
            f"📱 **الرقم:** `{number}`\n"
            f"🆔 **رقم الطلب:** `{order_id}`\n"
            f"{status_emoji} **الحالة:** {status_text}\n"
            f"📅 **تاريخ الشراء:** {created_at or 'N/A'}\n"
            f"⏰ **تاريخ الانتهاء:** {expires_at or 'N/A'}\n"
            f"⏳ **الوقت المتبقي:** {time_remaining}\n"
            if lang == 'ar' else
            f"{icon} **Service:** {display_service}\n"
            f"📱 **Number:** `{number}`\n"
            f"🆔 **Order ID:** `{order_id}`\n"
            f"{status_emoji} **Status:** {status_text}\n"
            f"📅 **Purchase Date:** {created_at or 'N/A'}\n"
            f"⏰ **Expiry Date:** {expires_at or 'N/A'}\n"
            f"⏳ **Time Remaining:** {time_remaining}\n"
        )
        
        # إضافة معلومات الرسالة إن وجدت
        if sms_received:
            message += (
                f"\n💬 **آخر رسالة:**\n`{sms_received}`\n" if lang == 'ar' 
                else f"\n💬 **Last Message:**\n`{sms_received}`\n"
            )
            if pin_code:
                message += f"🔐 **الرمز:** `{pin_code}`\n" if lang == 'ar' else f"🔐 **Code:** `{pin_code}`\n"
        else:
            message += (
                "\n📭 لم تصل أي رسالة بعد\n" if lang == 'ar' 
                else "\n📭 No messages received yet\n"
            )
        
        # إضافة الأزرار
        keyboard = []
        
        # زر مزامنة آخر 3 رسائل
        keyboard.append([InlineKeyboardButton(
            "🔄 مزامنة آخر 3 رسائل" if lang == 'ar' else "🔄 Sync Last 3 Messages",
            callback_data=f"nv_sync_last3_{order_id}"
        )])
        
        # زر Cancel & Refund للأرقام قصيرة الأمد أو زر Active للأرقام طويلة المدى
        if should_show_cancel_button(order_type):
            keyboard.append([InlineKeyboardButton(
                "❌ إلغاء وإعادة الرصيد" if lang == 'ar' else "❌ Cancel & Refund",
                callback_data=f"nv_cancel_order_{order_id}"
            )])
        elif order_type in ['3days', 'long_term']:
            # زر Active للأرقام طويلة المدى (3 أيام و 30 يوم) - يتغير حسب حالة التفعيل (مدة 5 دقائق)
            if activation_status == 'active' and activated_until:
                time_left = format_activation_time(activated_until, lang)
                button_text = f"مفعل ✅ ({time_left})" if lang == 'ar' else f"Activated ✅ ({time_left})"
            else:
                button_text = "تفعيل ✔️" if lang == 'ar' else "Activate ✔️"
            
            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f"nv_activate_{order_id}"
            )])
        
        keyboard.append([InlineKeyboardButton(
            "🔙 العودة لأرقامي" if lang == 'ar' else "🔙 Back to My Numbers",
            callback_data='nv_my_numbers'
        )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        logger.info(f"تم عرض تفاصيل الرقم {order_id} للمستخدم {user_id}")

    except Exception as e:
        logger.error(f"خطأ في التحقق اليدوي: {e}")
        await query.answer(
            f"❌ حدث خطأ: {str(e)}",
            show_alert=True
        )
    finally:
        if conn:
            await conn.close()


async def handle_sync_last3_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج زر مزامنة آخر 3 رسائل - يقرأ من قاعدة البيانات المحلية"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data

    if not data.startswith("nv_sync_last3_"):
        return

    order_id = int(data.replace("nv_sync_last3_", ""))

    conn = None
    try:
        conn = await aiosqlite.connect(DATABASE_FILE)

        # الحصول على لغة المستخدم
        async with conn.execute("SELECT language FROM users WHERE user_id = ?", (user_id,)) as cursor:
            lang_row = await cursor.fetchone()
        lang = lang_row[0] if lang_row and lang_row[0] else 'ar'

        # جلب معلومات الطلب
        async with conn.execute("""
            SELECT number, service, type
            FROM nonvoip_orders
            WHERE order_id = ? AND user_id = ?
        """, (order_id, user_id)) as cursor:
            order_row = await cursor.fetchone()

        if not order_row:
            await query.edit_message_text(
                "❌ الطلب غير موجود" if lang == "ar" else "❌ Order not found"
            )
            return

        number, service, order_type = order_row

        # عرض رسالة التحميل
        await query.answer(
            "🔄 جاري جلب آخر 3 رسائل من قاعدة البيانات..." if lang == "ar" else "🔄 Fetching last 3 messages from database...",
            show_alert=False
        )

        # جلب آخر 3 رسائل من قاعدة البيانات المحلية
        db = NonVoipDB()
        messages = db.get_messages_for_order(order_id, user_id, limit=3)

        display_service = get_display_service_name(service)
        icon = get_service_icon(service)

        if messages and len(messages) > 0:
            # عرض آخر 3 رسائل من قاعدة البيانات
            message = (
                f"✅ **آخر {len(messages)} رسالة محفوظة:**\n\n"
                f"{icon} **الخدمة:** {display_service}\n"
                f"📱 **الرقم:** `{number}`\n"
                f"🆔 **رقم الطلب:** `{order_id}`\n\n"
                f"📬 **الرسائل:**\n\n"
                if lang == "ar" else
                f"✅ **Last {len(messages)} saved message(s):**\n\n"
                f"{icon} **Service:** {display_service}\n"
                f"📱 **Number:** `{number}`\n"
                f"🆔 **Order ID:** `{order_id}`\n\n"
                f"📬 **Messages:**\n\n"
            )

            for idx, msg in enumerate(messages, 1):
                msg_text = msg.get('message_text', 'N/A')
                msg_time = msg.get('received_at', '')
                pin_code = msg.get('pin_code', '')

                message += f"{idx}. 💬 `{msg_text}`\n"
                if pin_code:
                    message += f"   🔐 **الرمز:** `{pin_code}`\n" if lang == 'ar' else f"   🔐 **Code:** `{pin_code}`\n"
                if msg_time:
                    message += f"   ⏰ {msg_time}\n"
                message += "\n"
        else:
            message = (
                f"📭 **لا توجد رسائل محفوظة**\n\n"
                f"{icon} **الخدمة:** {display_service}\n"
                f"📱 **الرقم:** `{number}`\n"
                f"🆔 **رقم الطلب:** `{order_id}`\n\n"
                f"💡 **ملاحظة:** استخدم زر 'عرض الرسائل' أو 'التفاصيل' لجلب الرسائل من السيرفر وحفظها محلياً."
                if lang == "ar" else
                f"📭 **No Saved Messages**\n\n"
                f"{icon} **Service:** {display_service}\n"
                f"📱 **Number:** `{number}`\n"
                f"🆔 **Order ID:** `{order_id}`\n\n"
                f"💡 **Note:** Use 'View Messages' or 'Details' button to fetch and save messages from server."
            )

        # الأزرار
        keyboard = []

        # صف واحد: مزامنة الرسالة الأخيرة + تفاصيل
        keyboard.append([
            InlineKeyboardButton(
                "🔄 مزامنة آخر 3 رسائل" if lang == 'ar' else "🔄 Sync Last 3 Messages",
                callback_data=f"nv_sync_last3_{order_id}"
            ),
            InlineKeyboardButton(
                "📊 تفاصيل" if lang == 'ar' else "📊 Details",
                callback_data=f"nv_manual_check_{order_id}"
            )
        ])

        # زر Cancel & Refund للأرقام قصيرة الأمد فقط
        if should_show_cancel_button(order_type):
            keyboard.append([InlineKeyboardButton(
                "❌ إلغاء وإعادة الرصيد" if lang == 'ar' else "❌ Cancel & Refund",
                callback_data=f"nv_cancel_order_{order_id}"
            )])

        keyboard.append([InlineKeyboardButton(
            "🔙 العودة لأرقامي" if lang == 'ar' else "🔙 Back to My Numbers",
            callback_data='nv_my_numbers'
        )])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"خطأ في مزامنة الرسالة الأخيرة: {e}")
        await query.answer(
            f"❌ حدث خطأ: {str(e)}",
            show_alert=True
        )
    finally:
        if conn:
            await conn.close()


async def monitor_order_for_sms(application, user_id: int, order_id: int, service: str, number: str,
                                 message_id: int, expiration_seconds: int, lang: str = "ar"):
    """
    مراقبة الطلب تلقائياً للتحقق من وصول SMS

    Args:
        application: تطبيق البوت
        user_id: معرف المستخدم
        order_id: معرف الطلب من API
        service: اسم الخدمة
        number: رقم الهاتف
        message_id: معرف الرسالة لتحديثها
        expiration_seconds: مدة الصلاحية بالثواني
        lang: لغة المستخدم
    """
    conn = None
    try:
        api = NonVoipAPI()
        db = NonVoipDB()

        conn = await aiosqlite.connect(DATABASE_FILE)

        check_interval = 30
        max_checks = max(1, int(expiration_seconds / check_interval))

        logger.info(f"بدء مراقبة الطلب {order_id} للمستخدم {user_id} - المدة: {expiration_seconds} ثانية")

        await conn.execute("""
            UPDATE nonvoip_orders
            SET monitoring_started = CURRENT_TIMESTAMP, message_id = ?
            WHERE order_id = ?
        """, (message_id, order_id))
        await conn.commit()

        for check_num in range(max_checks):
            await asyncio.sleep(check_interval)

            async with conn.execute("SELECT sms_sent, refunded, status FROM nonvoip_orders WHERE order_id = ?", (order_id,)) as cursor:
                order_status = await cursor.fetchone()

            if not order_status:
                logger.warning(f"الطلب {order_id} غير موجود في قاعدة البيانات")
                break

            sms_sent, refunded, status = order_status

            if refunded or status == 'cancelled':
                logger.info(f"توقف المراقبة - الطلب {order_id} تم إلغاؤه")
                break

            if sms_sent:
                logger.info(f"توقف المراقبة - الرسالة تم إرسالها بالفعل للطلب {order_id}")
                break

            sms_result = api.get_sms(service=service, number=number, order_id=order_id)

            if sms_result.get("status") == "success":
                sms_text = sms_result.get("sms", "")
                pin_code = sms_result.get("pin")

                if sms_text:
                    await conn.execute("""
                        UPDATE nonvoip_orders
                        SET sms_received = ?, pin_code = ?, status = 'delivered',
                            sms_sent = 1, updated_at = CURRENT_TIMESTAMP
                        WHERE order_id = ?
                    """, (sms_text, pin_code, order_id))
                    await conn.commit()

                    icon = get_service_icon(service)

                    sms_message = (
                        f"📬 **وصلت رسالة جديدة!**\n\n"
                        f"{icon} **الخدمة:** {service}\n"
                        f"📱 **الرقم:** `{number}`\n"
                        f"🆔 **رقم الطلب:** `{order_id}`\n\n"
                        f"💬 **الرسالة:**\n`{sms_text}`\n\n"
                        f"{f'🔐 **الرمز:** `{pin_code}`' if pin_code else ''}"
                        if lang == "ar" else
                        f"📬 **New Message Received!**\n\n"
                        f"{icon} **Service:** {service}\n"
                        f"📱 **Number:** `{number}`\n"
                        f"🆔 **Order ID:** `{order_id}`\n\n"
                        f"💬 **Message:**\n`{sms_text}`\n\n"
                        f"{f'🔐 **Code:** `{pin_code}`' if pin_code else ''}"
                    )

                    # استرجاع نوع الطلب لتحديد الأزرار
                    async with conn.execute("SELECT type FROM nonvoip_orders WHERE order_id = ?", (order_id,)) as cursor:
                        order_details = await cursor.fetchone()
                    reply_markup = None

                    if order_details:
                        order_type = order_details[0] or 'short_term'
                        if should_show_cancel_button(order_type):
                            reply_markup = build_cancel_refund_markup(order_id, lang)

                    try:
                        await application.bot.edit_message_text(
                            chat_id=user_id,
                            message_id=message_id,
                            text=sms_message,
                            reply_markup=reply_markup,
                            parse_mode="Markdown"
                        )
                        logger.info(f"تم إرسال الرسالة للمستخدم {user_id} - الطلب {order_id}")
                    except Exception as e:
                        logger.error(f"فشل تحديث الرسالة: {e}")
                        await application.bot.send_message(
                            chat_id=user_id,
                            text=sms_message,
                            parse_mode="Markdown"
                        )

                    break

        else:
            # إذا لم تصل رسالة بعد انتهاء المهلة، قم بالاسترداد التلقائي
            async with conn.execute("SELECT sms_sent, refunded, status, sale_price FROM nonvoip_orders WHERE order_id = ?", (order_id,)) as cursor:
                final_status = await cursor.fetchone()

            if final_status:
                sms_sent, refunded, status, sale_price = final_status

                if not sms_sent and not refunded and status not in ['cancelled', 'delivered', 'expired_refunded']:
                    logger.info(f"انتهت مهلة الطلب {order_id} - محاولة الاسترداد التلقائي")

                    reject_result = api.reject(service=service, number=number, order_id=order_id)

                    await conn.execute("UPDATE users SET credits_balance = credits_balance + ? WHERE user_id = ?",
                                   (sale_price, user_id))

                    await conn.execute("""
                        UPDATE nonvoip_orders
                        SET status = 'expired_refunded', refunded = 1, updated_at = CURRENT_TIMESTAMP
                        WHERE order_id = ?
                    """, (order_id,))

                    await conn.commit()

                    refund_msg = (
                        f"⏰ **انتهت مهلة الطلب**\n\n"
                        f"🆔 رقم الطلب: `{order_id}`\n"
                        f"📱 الرقم: `{number}`\n\n"
                        f"⚠️ لم تصل رسالة خلال المهلة المحددة\n\n"
                        f"✅ تم استرداد {sale_price} كريديت تلقائياً إلى حسابك\n"
                        f"{'✅ تم إعادة الرقم للموقع' if reject_result.get('status') == 'success' else '⚠️ لم يتمكن الموقع من استرداد الرقم'}"
                        if lang == "ar" else
                        f"⏰ **Order Expired**\n\n"
                        f"🆔 Order ID: `{order_id}`\n"
                        f"📱 Number: `{number}`\n\n"
                        f"⚠️ No message received within the time limit\n\n"
                        f"✅ {sale_price} credits automatically refunded to your account\n"
                        f"{'✅ Number returned to website' if reject_result.get('status') == 'success' else '⚠️ Website could not refund number'}"
                    )

                    try:
                        # حاول تحديث الرسالة الأصلية، إذا فشل أرسل رسالة جديدة
                        await application.bot.edit_message_text(
                            chat_id=user_id,
                            message_id=message_id,
                            text=refund_msg,
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        logger.error(f"فشل تحديث الرسالة عند انتهاء المهلة: {e}")
                        await application.bot.send_message(
                            chat_id=user_id,
                            text=refund_msg,
                            parse_mode="Markdown"
                        )

                    logger.info(f"تم استرداد {sale_price} كريديت تلقائياً للمستخدم {user_id} - الطلب {order_id}")

    except Exception as e:
        logger.error(f"خطأ في مراقبة الطلب {order_id}: {e}")
    finally:
        if conn:
            await conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# PART 11: ACTIVATION EXPIRY NOTIFICATION SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

async def check_expired_activations(context: ContextTypes.DEFAULT_TYPE) -> None:
    """التحقق من التفعيلات المنتهية وإرسال إشعارات للمستخدمين"""
    try:
        import sqlite3
        import pytz
        from datetime import datetime
        from dateutil import parser
        
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # البحث عن الأرقام المفعلة التي انتهى تفعيلها
        cursor.execute("""
            SELECT order_id, user_id, number, service, activated_until, activation_notified
            FROM nonvoip_orders
            WHERE type IN ('3days', 'long_term')
            AND activation_status = 'active'
            AND activated_until IS NOT NULL
            AND (activation_notified = 0 OR activation_notified IS NULL)
            AND status NOT IN ('cancelled', 'expired_refunded')
        """)
        
        active_numbers = cursor.fetchall()
        syria_tz = pytz.timezone(Config.TIMEZONE)
        now = datetime.now(syria_tz)
        
        for row in active_numbers:
            order_id, user_id, number, service, activated_until, activation_notified = row
            
            try:
                # تحويل وقت انتهاء التفعيل
                end_time = parser.parse(activated_until)
                if end_time.tzinfo is None:
                    end_time = pytz.UTC.localize(end_time)
                end_time_syria = end_time.astimezone(syria_tz)
                
                # التحقق إذا انتهى التفعيل
                if now >= end_time_syria:
                    # تحديث حالة التفعيل في قاعدة البيانات
                    cursor.execute("""
                        UPDATE nonvoip_orders
                        SET activation_status = 'inactive',
                            activation_notified = 1,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE order_id = ?
                    """, (order_id,))
                    conn.commit()
                    
                    # الحصول على لغة المستخدم
                    lang = get_user_language(user_id, conn)
                    icon = get_service_icon(service)
                    
                    # رسالة الإشعار
                    expiry_msg = (
                        f"⏰ **انتهى تفعيل الرقم**\n\n"
                        f"{icon} **الخدمة:** {service}\n"
                        f"📱 **الرقم:** `{number}`\n"
                        f"🆔 **رقم الطلب:** `{order_id}`\n\n"
                        f"❌ الرقم لن يستقبل رسائل جديدة الآن\n"
                        f"✅ لاستقبال رسائل جديدة، قم بتفعيل الرقم مجدداً\n\n"
                        f"💡 يمكنك تفعيل الرقم من \"أرقامي\" أو \"السجل\""
                    ) if lang == "ar" else (
                        f"⏰ **Number Activation Expired**\n\n"
                        f"{icon} **Service:** {service}\n"
                        f"📱 **Number:** `{number}`\n"
                        f"🆔 **Order ID:** `{order_id}`\n\n"
                        f"❌ Number will not receive new messages now\n"
                        f"✅ To receive new messages, activate the number again\n\n"
                        f"💡 You can activate from \"My Numbers\" or \"History\""
                    )
                    
                    # إرسال الإشعار
                    try:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=expiry_msg,
                            parse_mode="Markdown"
                        )
                        logger.info(f"✅ تم إرسال إشعار انتهاء التفعيل للمستخدم {user_id} - الطلب {order_id}")
                    except Exception as send_error:
                        logger.error(f"فشل إرسال إشعار انتهاء التفعيل: {send_error}")
                        
            except Exception as row_error:
                logger.error(f"خطأ في معالجة الطلب {order_id}: {row_error}")
                continue
        
        conn.close()
        
    except Exception as e:
        logger.error(f"خطأ في التحقق من التفعيلات المنتهية: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# NONVOIP BALANCE NOTIFICATION SYSTEM (نظام إشعارات رصيد NonVoip)
# ═══════════════════════════════════════════════════════════════════════════════

async def check_nonvoip_balance_and_notify(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    فحص رصيد NonVoip وإرسال إشعارات تدريجية للآدمن
    
    النظام التدريجي:
    - المستوى 1: رصيد أقل من 20$ (إشعار أصفر)
    - المستوى 2: رصيد أقل من 10$ (إشعار برتقالي)
    - المستوى 3: رصيد أقل من 5$ (إشعار أحمر خطر)
    
    يتم تشغيل هذه الدالة مرتين يومياً: 12 ظهراً و6 مساءً (بتوقيت سوريا)
    """
    try:
        import sqlite3
        from datetime import datetime
        import pytz
        
        # تهيئة قاعدة البيانات أولاً (لضمان وجود الجداول)
        db_instance = NonVoipDB()
        logger.info("✅ تم التأكد من تهيئة جداول NonVoip")
        
        # التحقق من حالة الإشعارات - هل هي مفعلة أم لا؟
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT value FROM settings WHERE key = 'nonvoip_balance_notifications_enabled'")
        notifications_setting = cursor.fetchone()
        notifications_enabled = notifications_setting[0] == '1' if notifications_setting else True
        
        if not notifications_enabled:
            logger.info("🔕 إشعارات انخفاض رصيد NonVoip معطلة - تم تخطي الفحص")
            conn.close()
            return
        
        logger.info("🔔 إشعارات انخفاض رصيد NonVoip مفعلة - جاري الفحص...")
        
        # الحصول على الرصيد من API
        api = NonVoipAPI()
        balance_result = api.get_balance()
        
        if balance_result.get('status') != 'success':
            logger.error(f"فشل الحصول على رصيد NonVoip: {balance_result.get('message')}")
            return
        
        try:
            balance = float(balance_result.get('balance', '0'))
        except (ValueError, TypeError):
            logger.error(f"قيمة رصيد غير صحيحة: {balance_result.get('balance')}")
            return
        
        logger.info(f"💰 رصيد NonVoip الحالي: ${balance:.2f}")
        
        # تحديد المستوى المناسب
        notification_levels = [
            (3, 5, "🔴 **تحذير خطر!**"),    # أقل من 5$ - خطر
            (2, 10, "🟠 **تنبيه مهم**"),     # أقل من 10$ - تحذير
            (1, 20, "🟡 **تنبيه**")          # أقل من 20$ - ملاحظة
        ]
        
        notification_to_send = None
        
        for level, threshold, title in notification_levels:
            if balance < threshold:
                # التحقق من عدم إرسال هذا المستوى سابقاً
                cursor.execute("""
                    SELECT balance_amount, notified_at 
                    FROM nonvoip_balance_notifications 
                    WHERE notification_level = ?
                """, (level,))
                
                existing = cursor.fetchone()
                
                # إرسال إشعار إذا:
                # 1. لم يتم الإرسال من قبل
                # 2. أو الرصيد انخفض عن المستوى السابق
                if not existing or (existing and balance < existing[0]):
                    notification_to_send = (level, threshold, title)
                    break
        
        if notification_to_send:
            level, threshold, title = notification_to_send
            
            # إنشاء رسالة الإشعار
            syria_tz = pytz.timezone(Config.TIMEZONE)
            now = datetime.now(syria_tz)
            time_str = now.strftime("%Y-%m-%d %H:%M")
            
            # تحديد رسالة حسب المستوى
            if level == 3:  # أقل من 5$
                emoji = "🚨"
                urgency = "**عاجل جداً!**"
                message_body = (
                    f"💵 **الرصيد الحالي:** `${balance:.2f}`\n"
                    f"⚠️ **الحد الأدنى:** `${threshold}`\n\n"
                    f"❗ الرصيد منخفض جداً ويحتاج تعبئة فورية!\n"
                    f"⚡ قد تتوقف خدمات NonVoip في أي لحظة\n\n"
                    f"📌 يُرجى إعادة شحن الحساب فوراً"
                )
            elif level == 2:  # أقل من 10$
                emoji = "⚠️"
                urgency = "**مهم**"
                message_body = (
                    f"💵 **الرصيد الحالي:** `${balance:.2f}`\n"
                    f"⚠️ **الحد الأدنى:** `${threshold}`\n\n"
                    f"📉 الرصيد منخفض ويُنصح بإعادة الشحن قريباً\n"
                    f"✅ الخدمة تعمل بشكل طبيعي حالياً"
                )
            else:  # أقل من 20$
                emoji = "ℹ️"
                urgency = "**للعلم**"
                message_body = (
                    f"💵 **الرصيد الحالي:** `${balance:.2f}`\n"
                    f"⚠️ **الحد الأدنى:** `${threshold}`\n\n"
                    f"📊 الرصيد أصبح أقل من ${threshold}\n"
                    f"💡 يُفضل مراقبة الرصيد وإعادة الشحن قريباً"
                )
            
            notification_message = (
                f"{title}\n"
                f"{emoji} **تنبيه رصيد NonVoip** {emoji}\n\n"
                f"{urgency}\n\n"
                f"{message_body}\n\n"
                f"🕐 **الوقت:** {time_str}\n"
                f"📍 **المنطقة الزمنية:** {Config.TIMEZONE}"
            )
            
            # إرسال الإشعار للآدمن
            try:
                admin_ids = Config.get_admin_ids()
                
                for admin_id in admin_ids:
                    try:
                        await context.bot.send_message(
                            chat_id=admin_id,
                            text=notification_message,
                            parse_mode="Markdown"
                        )
                        logger.info(f"✅ تم إرسال إشعار رصيد NonVoip (المستوى {level}) للآدمن {admin_id}")
                    except Exception as send_error:
                        logger.error(f"فشل إرسال إشعار للآدمن {admin_id}: {send_error}")
                
                # حفظ حالة الإشعار في قاعدة البيانات
                cursor.execute("""
                    INSERT OR REPLACE INTO nonvoip_balance_notifications 
                    (notification_level, balance_amount, notified_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (level, balance))
                
                conn.commit()
                logger.info(f"💾 تم حفظ حالة الإشعار: المستوى {level} - الرصيد ${balance:.2f}")
                
            except Exception as notify_error:
                logger.error(f"خطأ في إرسال الإشعار: {notify_error}")
        
        else:
            logger.info(f"✓ الرصيد جيد (${balance:.2f}) - لا حاجة لإشعارات")
        
        # إذا ارتفع الرصيد فوق 20$، نقوم بإعادة تعيين جميع المستويات السابقة
        # لكن بطريقة تسمح بإرسال إشعارات جديدة عند انخفاض الرصيد مستقبلاً
        if balance >= 20:
            # التحقق من وجود سجلات سابقة
            cursor.execute("SELECT COUNT(*) FROM nonvoip_balance_notifications")
            count = cursor.fetchone()[0]
            
            if count > 0:
                # حذف جميع السجلات القديمة لإعادة تعيين النظام
                cursor.execute("DELETE FROM nonvoip_balance_notifications")
                conn.commit()
                logger.info(f"✅ تم إعادة تعيين مستويات الإشعارات (الرصيد: ${balance:.2f} >= $20)")
        
        # إذا انخفض الرصيد مجدداً بعد التعافي، سيتم حذف المستويات الأعلى تلقائياً
        # مثلاً: إذا كان في المستوى 3 (< $5) ثم ارتفع إلى $15، نحذف المستوى 3 و 2
        # لكن نحتفظ بالمستوى 1 (< $20) فقط
        elif 10 <= balance < 20:
            # حذف المستويات 2 و 3 فقط (الأشد خطورة)
            cursor.execute("DELETE FROM nonvoip_balance_notifications WHERE notification_level IN (2, 3)")
            if cursor.rowcount > 0:
                conn.commit()
                logger.info(f"✅ تم إعادة تعيين المستويات العليا (الرصيد: ${balance:.2f})")
        
        elif 5 <= balance < 10:
            # حذف المستوى 3 فقط (الأكثر خطورة)
            cursor.execute("DELETE FROM nonvoip_balance_notifications WHERE notification_level = 3")
            if cursor.rowcount > 0:
                conn.commit()
                logger.info(f"✅ تم إعادة تعيين المستوى الأعلى (الرصيد: ${balance:.2f})")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ خطأ في فحص رصيد NonVoip: {e}")
        import traceback
        logger.error(traceback.format_exc())