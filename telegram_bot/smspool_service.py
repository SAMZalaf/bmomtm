#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SMSPool Service Module - Complete API Integration for SMS Verifications
وحدة SMSPool المدمجة للتعامل مع API خدمات التحقق عبر الرسائل

هذا الملف يوفر تدفق شراء كامل ومتكامل:
- SMSPoolAPI: التعامل مع SMSPool API
- SMSPoolDB: إدارة قاعدة البيانات
- وظائف البوت: دوال الزبائن والآدمن
- معالجات Inline Query للبحث عن الدول والخدمات

تدفق الشراء (مطابق لـ NonVoip الناجح):
1. اختيار زر "شراء رقم" → handle_buy_sms()
2. فتح Inline Query للبحث → handle_smspool_inline_query()
3. عرض قائمة الدول → الدول الشائعة أولاً
4. اختيار دولة → عرض الخدمات المتاحة لتلك الدولة
5. اختيار خدمة → تأكيد الشراء مع عرض التفاصيل
6. إتمام الشراء → process_purchase() - خصم الرصيد وحفظ الطلب
7. المراقبة التلقائية → check_sms_job() - فحص وصول الرسائل

API Endpoints Used:
- Balance: POST https://api.smspool.net/request/balance
- Services: GET https://api.smspool.net/service/retrieve_all
- Countries: GET https://api.smspool.net/country/retrieve_all
- Price: POST https://api.smspool.net/request/price
- Purchase SMS: POST https://api.smspool.net/purchase/sms
- Check SMS: POST https://api.smspool.net/sms/check
- Cancel SMS: POST https://api.smspool.net/sms/cancel
- Active Orders: POST https://api.smspool.net/request/active
- Resend SMS: POST https://api.smspool.net/sms/resend

الوظائف الرئيسية:
- handle_buy_sms(): نقطة البداية لعملية الشراء
- handle_smspool_inline_query(): البحث عن دول وخدمات
- confirm_purchase(): تأكيد تفاصيل الشراء
- process_purchase(): معالجة الشراء وخصم الرصيد
- check_sms_job(): المراقبة التلقائية للرسائل
- cancel_order(): إلغاء الطلب واسترداد الرصيد
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
    from config import Config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

logger = logging.getLogger(__name__)

API_BASE = "https://api.smspool.net"
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
    import pytz
    syria_tz = pytz.timezone(Config.TIMEZONE if CONFIG_AVAILABLE else 'Asia/Damascus')
    return datetime.now(syria_tz).strftime('%Y-%m-%d %H:%M:%S')


CACHE = {
    'services': {'data': [], 'last_update': 0},
    'countries': {'data': [], 'last_update': 0},
    'prices': {'data': {}, 'last_update': 0},
    'cache_duration': 300
}

ERROR_CODES = {
    '0x0000': 'رصيد الحساب غير كافٍ',
    '0x0001': 'الخدمة غير متوفرة حالياً',
    '0x0002': 'خطأ في الاتصال بالموقع',
    '0x0003': 'تم رفض الطلب',
    '0x0004': 'انتهت مهلة الاتصال',
    '0x0005': 'مفتاح API غير صحيح',
    '0x0006': 'تم تجاوز حد الطلبات',
    '0x0007': 'الطلب غير موجود',
    '0x0008': 'فشل في جلب الرسالة',
    '0x0009': 'خطأ غير متوقع',
    '0x000A': 'الخدمة غير متاحة'
}


def get_error_code_from_message(error_message: str) -> str:
    """تحديد كود الخطأ المناسب بناءً على رسالة الخطأ"""
    error_lower = str(error_message).lower()
    
    if 'balance' in error_lower or 'insufficient' in error_lower:
        return '0x0000'
    elif 'not available' in error_lower or 'out of stock' in error_lower:
        return '0x0001'
    elif 'connection' in error_lower or 'network' in error_lower:
        return '0x0002'
    elif 'rejected' in error_lower or 'denied' in error_lower:
        return '0x0003'
    elif 'timeout' in error_lower:
        return '0x0004'
    elif 'api key' in error_lower or 'invalid key' in error_lower:
        return '0x0005'
    elif 'rate limit' in error_lower or 'too many' in error_lower:
        return '0x0006'
    elif 'not found' in error_lower or 'order' in error_lower:
        return '0x0007'
    elif 'sms' in error_lower and 'fail' in error_lower:
        return '0x0008'
    else:
        return '0x0009'


class SMSPoolAPI:
    """
    فئة للتعامل مع SMSPool API
    
    API Key-based authentication
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        تهيئة الاتصال بـ API
        
        Args:
            api_key: مفتاح API (يُؤخذ من SMSPOOL_API_KEY إن لم يُحدد)
        """
        if api_key:
            self.api_key = api_key
        elif CONFIG_AVAILABLE and hasattr(Config, 'SMSPOOL_API_KEY'):
            self.api_key = Config.SMSPOOL_API_KEY
        else:
            self.api_key = os.getenv("SMSPOOL_API_KEY")
        
        if not self.api_key:
            logger.warning("SMSPOOL_API_KEY not configured")

    def test_connection(self) -> Tuple[bool, str, Optional[str]]:
        """اختبار الاتصال عبر request/balance وإرجاع نتيجة واضحة."""
        if not self.api_key:
            return False, "API key not configured", None

        result = self._api_request("request/balance")
        if isinstance(result, dict) and 'balance' in result:
            balance = str(result.get('balance'))
            logger.info(f"✅ SMSPool API connection OK. Balance={balance}")
            return True, "OK", balance

        message = str(result.get('message', 'Unknown error')) if isinstance(result, dict) else 'Unknown error'
        logger.error(f"❌ SMSPool API connection failed: {message}")
        return False, message, None
    
    def _api_request(self, endpoint: str, method: str = "POST", 
                     data: Optional[Dict] = None, timeout: int = 15) -> Dict:
        """
        إرسال طلب إلى API
        
        Args:
            endpoint: نقطة النهاية
            method: GET أو POST
            data: البيانات الإضافية
            timeout: مهلة الانتظار
        
        Returns:
            استجابة JSON من API
        """
        url = f"{API_BASE}/{endpoint}"
        
        if data is None:
            data = {}
        data['key'] = self.api_key
        
        logger.info(f"SMSPool API request to {endpoint}")
        
        try:
            if method.upper() == "GET":
                resp = requests.get(url, params=data, timeout=timeout)
            else:
                resp = requests.post(url, data=data, timeout=timeout)
            
            logger.info(f"SMSPool API response: status {resp.status_code}")
            
            if resp.status_code == 429:
                return {"success": 0, "message": "Rate limit exceeded"}
            
            resp.raise_for_status()
            return resp.json()
            
        except requests.Timeout:
            logger.error(f"Timeout on {endpoint}")
            return {"success": 0, "message": "Connection timeout"}
        except requests.RequestException as e:
            logger.error(f"Request error on {endpoint}: {e}")
            return {"success": 0, "message": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error on {endpoint}: {e}")
            return {"success": 0, "message": str(e)}
    
    def get_balance(self) -> Dict[str, Any]:
        """
        جلب رصيد الحساب
        
        Returns:
            {"balance": "5.00"} عند النجاح
        """
        result = self._api_request("request/balance")
        if 'balance' in result:
            return {"status": "success", "balance": result['balance']}
        return {"status": "error", "message": result.get('message', 'Unknown error')}
    
    def get_services(self) -> List[Dict]:
        """جلب قائمة الخدمات المتاحة (مع Cache)."""
        global CACHE

        now = time.time()
        cache_duration = CACHE['cache_duration']
        services_cache = CACHE['services']

        if (now - services_cache['last_update'] < cache_duration) and services_cache['data']:
            return services_cache['data']

        result = self._api_request("service/retrieve_all", method="GET")

        if isinstance(result, list):
            services_cache['data'] = result
            services_cache['last_update'] = now
            return result

        return []

    def get_countries(self) -> List[Dict]:
        """جلب قائمة الدول المتاحة (مع Cache)."""
        global CACHE

        now = time.time()
        cache_duration = CACHE['cache_duration']
        countries_cache = CACHE['countries']

        if (now - countries_cache['last_update'] < cache_duration) and countries_cache['data']:
            return countries_cache['data']

        result = self._api_request("country/retrieve_all", method="GET")

        if isinstance(result, list):
            countries_cache['data'] = result
            countries_cache['last_update'] = now
            return result

        return []

    def get_service_price(self, service: str, country: str) -> Optional[Dict]:
        """جلب سعر خدمة معينة في دولة معينة (Live + Cache)."""
        global CACHE

        now = time.time()
        cache_duration = CACHE['cache_duration']
        cache_key = f"{country}:{service}"

        cached = CACHE['prices']['data'].get(cache_key)
        if cached and (now - cached['ts'] < cache_duration):
            return cached['result']

        result = self._api_request(
            "request/price",
            data={
                'service': service,
                'country': country,
            },
        )

        price_result: Optional[Dict] = None
        if isinstance(result, dict):
            if result.get('success') == 1 and result.get('price') is not None:
                price_result = result
            elif 'price' in result and result.get('price') is not None:
                price_result = result

        CACHE['prices']['data'][cache_key] = {'ts': now, 'result': price_result}
        return price_result
    
    def purchase_sms(self, country: str, service: str, 
                     pool: Optional[str] = None, order_type: str = 'temp', days: Optional[str] = None) -> Dict[str, Any]:
        """
        شراء رقم للتحقق SMS (يدعم الشراء العادي والإيجار)
        """
        if order_type == 'rent':
            # https://api.smspool.net/purchase/rent
            endpoint = "purchase/rent"
            data = {
                'country': country,
                'service': service,
                'duration': days or '1'
            }
        else:
            endpoint = "purchase/sms"
            data = {
                'country': country,
                'service': service
            }

        if pool:
            data['pool'] = pool
        
        result = self._api_request(endpoint, data=data)
        
        if result.get('success') == 1:
            return {
                "status": "success",
                "order_id": result.get('order_id'),
                "number": result.get('number'),
                "country": result.get('country'),
                "service": result.get('service'),
                "pool": result.get('pool'),
                "expires_in": result.get('expires_in', 600)
            }
        
        return {
            "status": "error",
            "message": result.get('message', 'Purchase failed')
        }
    
    def check_sms(self, order_id: str) -> Dict[str, Any]:
        """
        فحص حالة الطلب وجلب الرسالة
        
        Args:
            order_id: معرف الطلب
        
        Returns:
            {
                "status": 1-4,
                "sms": "Your code is 123456",
                "full_sms": "Full message content"
            }
            
            Status codes:
            1 = Waiting for SMS
            2 = SMS Received
            3 = Order Cancelled/Refunded
            4 = Order Expired
        """
        result = self._api_request("sms/check", data={'orderid': order_id})
        
        status = result.get('status', 0)
        
        if status == 2:
            return {
                "status": "received",
                "sms": result.get('sms', ''),
                "full_sms": result.get('full_sms', '')
            }
        elif status == 1:
            return {"status": "waiting"}
        elif status == 3:
            return {"status": "cancelled"}
        elif status == 4:
            return {"status": "expired"}
        else:
            return {"status": "error", "message": result.get('message', 'Unknown status')}
    
    def cancel_sms(self, order_id: str) -> Dict[str, Any]:
        """
        إلغاء الطلب واسترداد المبلغ
        
        Args:
            order_id: معرف الطلب
        
        Returns:
            {"success": 1} عند النجاح
        """
        result = self._api_request("sms/cancel", data={'orderid': order_id})
        
        if result.get('success') == 1:
            return {"status": "success", "message": "Order cancelled and refunded"}
        
        return {"status": "error", "message": result.get('message', 'Cancel failed')}
    
    def resend_sms(self, order_id: str) -> Dict[str, Any]:
        """
        إعادة إرسال الرسالة
        
        Args:
            order_id: معرف الطلب
        
        Returns:
            {"success": 1} عند النجاح
        """
        result = self._api_request("sms/resend", data={'orderid': order_id})
        
        if result.get('success') == 1:
            return {"status": "success", "message": "SMS resend requested"}
        
        return {"status": "error", "message": result.get('message', 'Resend failed')}
    
    def get_active_orders(self) -> List[Dict]:
        """
        جلب الطلبات النشطة
        
        Returns:
            قائمة الطلبات النشطة
        """
        result = self._api_request("request/active")
        
        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and 'orders' in result:
            return result['orders']
        
        return []
    
    def get_order_history(self) -> List[Dict]:
        """
        جلب سجل الطلبات
        
        Returns:
            قائمة الطلبات السابقة
        """
        result = self._api_request("request/history")
        
        if isinstance(result, list):
            return result
        
        return []


class SMSPoolDB:
    """
    فئة لإدارة قاعدة البيانات لخدمة SMSPool
    """
    
    def __init__(self, db_file: str = DATABASE_FILE):
        self.db_file = db_file
        self.init_tables()
    
    def init_tables(self):
        """إنشاء الجداول اللازمة"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS smspool_settings (
                id INTEGER PRIMARY KEY DEFAULT 1,
                api_key TEXT,
                enabled INTEGER DEFAULT 1,
                margin_percent REAL DEFAULT 30,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS smspool_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                order_id TEXT NOT NULL UNIQUE,
                number TEXT,
                country TEXT,
                country_id TEXT,
                service TEXT,
                service_id TEXT,
                pool TEXT,
                cost_price REAL DEFAULT 0,
                sale_price REAL DEFAULT 0,
                status TEXT DEFAULT 'pending',
                sms_code TEXT,
                full_sms TEXT,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS smspool_services_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_id TEXT NOT NULL,
                service_name TEXT NOT NULL,
                short_name TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            INSERT OR IGNORE INTO smspool_settings (id, enabled) VALUES (1, 1)
        """)

        # جدول سجل التجديد (اختياري - مطابق لنمط Non-VoIP)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS smspool_renewal_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_order_id TEXT,
                renewed_order_id TEXT,
                user_id INTEGER,
                renewal_price REAL,
                renewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ترقيات قاعدة البيانات (إضافة أعمدة جديدة بدون كسر التوافق)
        cursor.execute("PRAGMA table_info(smspool_orders)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        if 'already_renewed' not in existing_columns:
            cursor.execute("ALTER TABLE smspool_orders ADD COLUMN already_renewed INTEGER DEFAULT 0")

        # إذا كان مفتاح API موجوداً في ENV/Config ولم يتم تعيينه بعد في القاعدة
        try:
            cursor.execute("SELECT api_key FROM smspool_settings WHERE id = 1")
            current_key = cursor.fetchone()
            current_key = current_key[0] if current_key else None

            if not current_key:
                candidate_key = os.getenv('SMSPOOL_API_KEY')
                if not candidate_key and CONFIG_AVAILABLE and getattr(Config, 'SMSPOOL_API_KEY', ''):
                    candidate_key = Config.SMSPOOL_API_KEY

                if candidate_key:
                    cursor.execute(
                        "UPDATE smspool_settings SET api_key = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1",
                        (candidate_key,),
                    )
        except Exception as e:
            logger.warning(f"SMSPool settings bootstrap skipped: {e}")

        conn.commit()
        conn.close()
        logger.info("SMSPool database tables initialized")
    
    def get_api_key(self) -> Optional[str]:
        """جلب مفتاح API"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT api_key FROM smspool_settings WHERE id = 1")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def set_api_key(self, api_key: str) -> bool:
        """تعيين مفتاح API"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE smspool_settings 
                SET api_key = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = 1
            """, (api_key,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error setting API key: {e}")
            return False
    
    def is_enabled(self) -> bool:
        """التحقق من تفعيل الخدمة"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT enabled FROM smspool_settings WHERE id = 1")
        result = cursor.fetchone()
        conn.close()
        return bool(result[0]) if result else False
    
    def set_enabled(self, enabled: bool) -> bool:
        """تفعيل/تعطيل الخدمة"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE smspool_settings 
                SET enabled = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = 1
            """, (1 if enabled else 0,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error setting enabled status: {e}")
            return False
    
    def get_margin_percent(self) -> float:
        """جلب نسبة الربح"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT margin_percent FROM smspool_settings WHERE id = 1")
        result = cursor.fetchone()
        conn.close()
        return float(result[0]) if result else 30.0
    
    def set_margin_percent(self, margin: float) -> bool:
        """تعيين نسبة الربح"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE smspool_settings 
                SET margin_percent = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = 1
            """, (margin,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error setting margin: {e}")
            return False
    
    def create_order(self, user_id: int, order_id: str, number: str,
                     country: str, country_id: str, service: str, 
                     service_id: str, pool: str, cost_price: float,
                     sale_price: float, expires_in: int) -> Optional[int]:
        """إنشاء طلب جديد"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            cursor.execute("""
                INSERT INTO smspool_orders 
                (user_id, order_id, number, country, country_id, service, 
                 service_id, pool, cost_price, sale_price, status, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
            """, (user_id, order_id, number, country, country_id, service,
                  service_id, pool, cost_price, sale_price, expires_at))
            
            order_db_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Created SMSPool order {order_id} for user {user_id}")
            return order_db_id
            
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return None
    
    def get_order_by_order_id(self, order_id: str) -> Optional[Dict]:
        """جلب طلب بواسطة order_id"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM smspool_orders WHERE order_id = ?
        """, (order_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, result))
        return None
    
    def get_user_orders(self, user_id: int, status: Optional[str] = None,
                        limit: int = 10) -> List[Dict]:
        """جلب طلبات المستخدم"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if status:
            cursor.execute("""
                SELECT * FROM smspool_orders 
                WHERE user_id = ? AND status = ?
                ORDER BY created_at DESC LIMIT ?
            """, (user_id, status, limit))
        else:
            cursor.execute("""
                SELECT * FROM smspool_orders 
                WHERE user_id = ?
                ORDER BY created_at DESC LIMIT ?
            """, (user_id, limit))
        
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        
        return [dict(zip(columns, row)) for row in results]

    def mark_expired_orders(self, user_id: Optional[int] = None) -> int:
        """تحديث الطلبات المنتهية محلياً بناءً على expires_at."""
        conn = get_db_connection()
        cursor = conn.cursor()

        if user_id is not None:
            cursor.execute(
                """
                UPDATE smspool_orders
                SET status = 'expired', updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                  AND status IN ('pending', 'received')
                  AND expires_at IS NOT NULL
                  AND datetime(expires_at) < datetime('now')
                """,
                (user_id,),
            )
        else:
            cursor.execute(
                """
                UPDATE smspool_orders
                SET status = 'expired', updated_at = CURRENT_TIMESTAMP
                WHERE status IN ('pending', 'received')
                  AND expires_at IS NOT NULL
                  AND datetime(expires_at) < datetime('now')
                """
            )

        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected or 0

    def get_user_active_orders(self, user_id: int, limit: int = 10, offset: int = 0) -> List[Dict]:
        """جلب الأرقام النشطة للمستخدم (pending/received) مع Pagination."""
        self.mark_expired_orders(user_id=user_id)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM smspool_orders
            WHERE user_id = ?
              AND status IN ('pending', 'received')
              AND (expires_at IS NULL OR datetime(expires_at) >= datetime('now'))
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, limit, offset),
        )
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        return [dict(zip(columns, row)) for row in results]

    def count_user_active_orders(self, user_id: int) -> int:
        self.mark_expired_orders(user_id=user_id)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) FROM smspool_orders
            WHERE user_id = ?
              AND status IN ('pending', 'received')
              AND (expires_at IS NULL OR datetime(expires_at) >= datetime('now'))
            """,
            (user_id,),
        )
        count = cursor.fetchone()
        conn.close()
        return int(count[0]) if count else 0

    def get_user_renewable_orders(self, user_id: int, limit: int = 10, offset: int = 0) -> List[Dict]:
        """طلبات History: منتهية وقابلة لإعادة الشراء (expired + not already_renewed)."""
        self.mark_expired_orders(user_id=user_id)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM smspool_orders
            WHERE user_id = ?
              AND status = 'expired'
              AND COALESCE(already_renewed, 0) = 0
            ORDER BY expires_at DESC, created_at DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, limit, offset),
        )
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        return [dict(zip(columns, row)) for row in results]

    def count_user_expired_orders(self, user_id: int) -> int:
        self.mark_expired_orders(user_id=user_id)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) FROM smspool_orders
            WHERE user_id = ?
              AND status = 'expired'
            """,
            (user_id,),
        )
        count = cursor.fetchone()
        conn.close()
        return int(count[0]) if count else 0

    def count_user_renewable_orders(self, user_id: int) -> int:
        self.mark_expired_orders(user_id=user_id)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) FROM smspool_orders
            WHERE user_id = ?
              AND status = 'expired'
              AND COALESCE(already_renewed, 0) = 0
            """,
            (user_id,),
        )
        count = cursor.fetchone()
        conn.close()
        return int(count[0]) if count else 0

    def sum_user_renewable_cost(self, user_id: int) -> float:
        self.mark_expired_orders(user_id=user_id)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COALESCE(SUM(sale_price), 0) FROM smspool_orders
            WHERE user_id = ?
              AND status = 'expired'
              AND COALESCE(already_renewed, 0) = 0
            """,
            (user_id,),
        )
        total = cursor.fetchone()
        conn.close()
        return float(total[0]) if total and total[0] is not None else 0.0

    def mark_order_as_renewed(self, order_id: str) -> bool:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE smspool_orders
                SET already_renewed = 1, updated_at = CURRENT_TIMESTAMP
                WHERE order_id = ?
                """,
                (order_id,),
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error marking order as renewed: {e}")
            return False

    def log_renewal(self, original_order_id: str, renewed_order_id: str, user_id: int, renewal_price: float) -> None:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO smspool_renewal_log (original_order_id, renewed_order_id, user_id, renewal_price)
                VALUES (?, ?, ?, ?)
                """,
                (original_order_id, renewed_order_id, user_id, renewal_price),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error logging renewal: {e}")

    def update_order_status(self, order_id: str, status: str,
                            sms_code: str = None, full_sms: str = None) -> bool:
        """تحديث حالة الطلب"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if sms_code:
                cursor.execute("""
                    UPDATE smspool_orders 
                    SET status = ?, sms_code = ?, full_sms = ?, 
                        updated_at = CURRENT_TIMESTAMP 
                    WHERE order_id = ?
                """, (status, sms_code, full_sms, order_id))
            else:
                cursor.execute("""
                    UPDATE smspool_orders 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE order_id = ?
                """, (status, order_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            return False
    
    def get_active_orders_count(self) -> int:
        """عدد الطلبات النشطة"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM smspool_orders 
            WHERE status = 'pending' AND expires_at > datetime('now')
        """)
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0


smspool_db = SMSPoolDB()


def get_user_language(user_id: int) -> str:
    """جلب لغة المستخدم"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 'ar'
    except:
        return 'ar'


def get_user_balance(user_id: int) -> float:
    """جلب رصيد المستخدم"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return float(result[0]) if result else 0.0
    except:
        return 0.0


def update_user_balance(user_id: int, amount: float, operation: str = 'subtract') -> bool:
    """تحديث رصيد المستخدم"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if operation == 'add':
            cursor.execute("""
                UPDATE users SET balance = balance + ? WHERE user_id = ?
            """, (amount, user_id))
        else:
            cursor.execute("""
                UPDATE users SET balance = balance - ? WHERE user_id = ?
            """, (amount, user_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error updating balance: {e}")
        return False


SMSPOOL_MESSAGES = {
    'ar': {
        'menu_title': '📱 سيرڤر US only (1) | Server 2 🆕',
        'menu_desc': 'احصل على رقم للتحقق عبر الرسائل',
        'buy_number': '🛒 شراء رقم',
        'my_numbers': '📋 أرقامي',
        'history': '📜 السجل',
        'back': '🔙 رجوع',
        'no_active_numbers': '📭 لا توجد أرقام نشطة حالياً',
        'no_history': '📭 لا توجد أرقام متاحة للتجديد',
        'renew': '🔄 تجديد',
        'select_country': '🌍 اختر الدولة',
        'select_service': '📱 اختر الخدمة',
        'confirm_purchase': '✅ تأكيد الشراء',
        'cancel': '❌ إلغاء',
        'purchase_success': '''
✅ <b>تم شراء الرقم بنجاح!</b>

📱 الرقم: <code>{number}</code>
🌍 الدولة: {country}
📱 الخدمة: {service}
⏱️ صالح لمدة: {expires} دقيقة

💡 انتظر الرسالة وستظهر تلقائياً
''',
        'sms_received': '''
📩 <b>تم استلام الرسالة!</b>

📱 الرقم: <code>{number}</code>
🔐 الكود: <code>{code}</code>

📄 الرسالة الكاملة:
{full_sms}
''',
        'waiting_sms': '⏳ في انتظار الرسالة...',
        'order_cancelled': '❌ تم إلغاء الطلب واسترداد المبلغ',
        'order_expired': '⏰ انتهت صلاحية الرقم',
        'insufficient_balance': '❌ رصيدك غير كافٍ!\n\n💳 رصيدك: {balance} كريديت\n💵 المطلوب: {required} كريديت',
        'service_disabled': '⚠️ خدمة الأرقام متوقفة مؤقتاً',
        'no_orders': '📭 لا توجد طلبات',
        'error': '❌ حدث خطأ: {message}'
    },
    'en': {
        'menu_title': '📱 SMS Numbers',
        'menu_desc': 'Get a number for SMS verification',
        'buy_number': '🛒 Buy Number',
        'my_numbers': '📋 My Numbers',
        'history': '📜 History',
        'back': '🔙 Back',
        'no_active_numbers': '📭 No active numbers right now',
        'no_history': '📭 No numbers available for renewal',
        'renew': '🔄 Renew',
        'select_country': '🌍 Select Country',
        'select_service': '📱 Select Service',
        'confirm_purchase': '✅ Confirm Purchase',
        'cancel': '❌ Cancel',
        'purchase_success': '''
✅ <b>Number purchased successfully!</b>

📱 Number: <code>{number}</code>
🌍 Country: {country}
📱 Service: {service}
⏱️ Valid for: {expires} minutes

💡 Wait for the SMS and it will appear automatically
''',
        'sms_received': '''
📩 <b>SMS Received!</b>

📱 Number: <code>{number}</code>
🔐 Code: <code>{code}</code>

📄 Full message:
{full_sms}
''',
        'waiting_sms': '⏳ Waiting for SMS...',
        'order_cancelled': '❌ Order cancelled and refunded',
        'order_expired': '⏰ Number expired',
        'insufficient_balance': '❌ Insufficient balance!\n\n💳 Your balance: {balance} credits\n💵 Required: {required} credits',
        'service_disabled': '⚠️ SMS service is temporarily disabled',
        'no_orders': '📭 No orders found',
        'error': '❌ Error: {message}'
    }
}


def get_smspool_message(key: str, language: str = 'ar') -> str:
    """جلب رسالة مترجمة"""
    return SMSPOOL_MESSAGES.get(language, SMSPOOL_MESSAGES['ar']).get(key, key)


async def smspool_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """القائمة الرئيسية لخدمة SMSPool"""
    query = update.callback_query
    if query:
        await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    if not smspool_db.is_enabled():
        text = get_smspool_message('service_disabled', language)
        if query:
            await query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return
    
    title = get_smspool_message('menu_title', language)
    desc = get_smspool_message('menu_desc', language)
    
    text = f"<b>{title}</b>\n\n{desc}"
    
    keyboard = [
        [InlineKeyboardButton(
            get_smspool_message('buy_number', language),
            callback_data="sp_buy"
        )],
        [InlineKeyboardButton(
            get_smspool_message('my_numbers', language),
            callback_data="sp_my_numbers"
        )],
        [InlineKeyboardButton(
            get_smspool_message('history', language),
            callback_data="sp_history"
        )],
        [InlineKeyboardButton(
            get_smspool_message('back', language),
            callback_data="main_menu"
        )]
    ]
    
    if query:
        await query.edit_message_text(
            text, 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )


async def handle_smspool_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج callbacks لـ SMSPool"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    if data == "sp_main" or data == "sp_menu":
        await smspool_main_menu(update, context)
    
    elif data == "sp_buy":
        await handle_buy_sms(update, context)

    elif data.startswith("sp_type_"):
        await handle_smspool_type_selection(update, context)

    elif data.startswith("sp_rent_dur_"):
        duration = data.replace("sp_rent_dur_", "")
        context.user_data['sp_rent_days'] = duration
        
        user_id = update.effective_user.id
        language = get_user_language(user_id)
        
        if language == 'ar':
            message_text = "🌍 *اختر الدولة*\nاضغط على الزر واكتب اسم الدولة للبحث عنها."
            search_button = "🔍 ابحث عن دولة"
        else:
            message_text = "🌍 *Select Country*\nClick the button and type country name to search."
            search_button = "🔍 Search for country"
            
        keyboard = [[InlineKeyboardButton(search_button, switch_inline_query_current_chat="sp:")],
                    [InlineKeyboardButton(get_smspool_message('back', language), callback_data="sp_type_rent")]]
        await query.edit_message_text(message_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return
    
    elif data.startswith("sp_country_"):
        country_id = data.replace("sp_country_", "")
        context.user_data['sp_country'] = country_id
        
        # جلب اسم الدولة للعرض
        api_key = smspool_db.get_api_key()
        api = SMSPoolAPI(api_key)
        countries = api.get_countries()
        selected_country = next((c for c in countries if str(c.get('ID', c.get('id', ''))) == str(country_id)), None)
        country_name = selected_country.get('name', 'Unknown') if selected_country else 'Unknown'
        country_code = selected_country.get('short_name', selected_country.get('code', '')) if selected_country else ''
        flag = get_country_flag(country_code)

        if language == 'ar':
            msg = f"🌍 **الدولة المختارة:** {flag} {country_name}\n\n🔍 ابحث عن الخدمة المطلوبة في هذه الدولة:"
        else:
            msg = f"🌍 **Selected Country:** {flag} {country_name}\n\n🔍 Search for the desired service in this country:"
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "🔍 " + ("ابحث عن خدمة" if language == 'ar' else "Search for service"),
                    switch_inline_query_current_chat=f"sp_svc:{country_id}:"
                )
            ], [
                InlineKeyboardButton(get_smspool_message('back', language), callback_data="sp_buy")
            ]]),
            parse_mode='Markdown'
        )

    elif data.startswith("sp_services_page_"):
        # sp_services_page_{country_id}_{page}
        parts = data.replace("sp_services_page_", "").split("_")
        if len(parts) >= 2:
            country_id = parts[0]
            try:
                page = int(parts[1])
            except ValueError:
                page = 0
            await handle_services_menu(update, context, country_id=country_id, page=page)

    elif data == "sp_unavail":
        await query.answer(
            "❌ " + ("غير متاح" if language == 'ar' else "Unavailable"),
            show_alert=True,
        )

    elif data.startswith("sp_service_select_"):
        service_id = data.replace("sp_service_select_", "")

        api_key = smspool_db.get_api_key()
        api = SMSPoolAPI(api_key)
        countries = api.get_countries()

        if not countries:
            await query.edit_message_text(
                get_smspool_message('error', language).format(
                    message=(
                        'تعذر جلب الدول حالياً' if language == 'ar' else 'Failed to load countries'
                    )
                ),
                parse_mode='HTML',
            )
            return

        popular_codes = ['US', 'GB', 'CA', 'DE', 'FR', 'NL', 'RU', 'IN', 'PH', 'ID']
        popular = [c for c in countries if str(c.get('short_name', '')).upper() in popular_codes]
        others = [c for c in countries if str(c.get('short_name', '')).upper() not in popular_codes]

        selected = (popular + others)[:20]

        keyboard: List[List[InlineKeyboardButton]] = []
        row: List[InlineKeyboardButton] = []

        for c in selected:
            country_id = str(c.get('ID', c.get('id', '')))
            name = c.get('name', 'Unknown')
            code = str(c.get('short_name', c.get('code', '')))
            flag = get_country_flag(code)

            row.append(
                InlineKeyboardButton(
                    f"{flag} {name}",
                    callback_data=f"sp_buy_{country_id}_{service_id}",
                )
            )
            if len(row) == 2:
                keyboard.append(row)
                row = []

        if row:
            keyboard.append(row)

        keyboard.append([InlineKeyboardButton(get_smspool_message('back', language), callback_data='sp_buy')])

        title = '🌍 اختر الدولة' if language == 'ar' else '🌍 Select country'
        await query.edit_message_text(
            f"<b>{title}</b>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML',
        )

    elif data.startswith("sp_buy_"):
        # sp_buy_country_service
        parts = data.replace("sp_buy_", "").split("_")
        if len(parts) >= 2:
            country_id = parts[0]
            service_id = parts[1]
            await confirm_purchase(update, context, country_id, service_id)
        else:
            await query.answer("❌ خطأ في البيانات", show_alert=True)
    
    elif data.startswith("sp_confirm_"):
        parts = data.replace("sp_confirm_", "").split("_")
        country_id = parts[0]
        service_id = parts[1] if len(parts) > 1 else ""
        
        # إضافة دعم الإيجار في المعالجة
        if context.user_data.get('sp_order_type') == 'rent':
            days = context.user_data.get('sp_rent_days', '1')
            await process_rent_purchase(update, context, country_id, service_id, days)
        else:
            await process_purchase(update, context, country_id, service_id)
    
    elif data.startswith("sp_type_") or data.startswith("sp_rent_dur_"):
        if data.startswith("sp_type_"):
            await handle_smspool_type_selection(update, context)
        else:
            await handle_smspool_rent_duration(update, context)
        return

    elif data.startswith("sp_check_"):
        order_id = data.replace("sp_check_", "")
        await check_order_status(update, context, order_id)
    
    elif data.startswith("sp_cancel_"):
        order_id = data.replace("sp_cancel_", "")
        await cancel_order(update, context, order_id)
    
    elif data.startswith("sp_resend_"):
        order_id = data.replace("sp_resend_", "")
        await resend_sms(update, context, order_id)
    
    elif data in {"sp_my_numbers", "sp_my_orders"}:
        await handle_my_numbers(update, context, page=0)

    elif data.startswith("sp_my_numbers_page_"):
        try:
            page = int(data.replace("sp_my_numbers_page_", ""))
        except ValueError:
            page = 0
        await handle_my_numbers(update, context, page=page)

    elif data.startswith("sp_country_"):
        # sp_country_{country_id}
        country_id = data.replace("sp_country_", "")
        
        user_id = update.effective_user.id
        language = get_user_language(user_id)
        
        # تخزين الدولة المختارة في context
        context.user_data['sp_selected_country'] = country_id
        
        if language == 'ar':
            message_text = (
                "📱 *اختر الخدمة*\n\n"
                "اضغط على زر \"🔍 ابحث عن خدمة\" أدناه، ثم اكتب اسم الخدمة (مثلاً WhatsApp أو Telegram)."
            )
            search_button = "🔍 ابحث عن خدمة"
        else:
            message_text = (
                "📱 *Select Service*\n\n"
                "Click \"🔍 Search for service\" button below, then type service name (e.g., WhatsApp or Telegram)."
            )
            search_button = "🔍 Search for service"
            
        keyboard = [
            [InlineKeyboardButton(
                search_button,
                switch_inline_query_current_chat=f"sp_svc:{country_id}:"
            )],
            [InlineKeyboardButton(
                get_smspool_message('back', language),
                callback_data="sp_buy"
            )]
        ]
        
        await query.edit_message_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif data == "sp_history":
        await handle_history(update, context, page=0)

    elif data.startswith("sp_history_page_"):
        try:
            page = int(data.replace("sp_history_page_", ""))
        except ValueError:
            page = 0
        await handle_history(update, context, page=page)

    elif data.startswith("sp_renew_"):
        original_order_id = data.replace("sp_renew_", "")
        await renew_smspool_number(update, context, original_order_id=original_order_id)


async def handle_buy_sms(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج الشراء الأساسي - يطلب اختيار نوع الخدمة (مرة واحدة أو إيجار)"""
    query = update.callback_query
    if query:
        await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    if language == 'ar':
        text = "⏱️ **اختر نوع الخدمة:**"
        btn_one_time = "🔢 رقم لمرة واحدة (Temp)"
        btn_rent = "📅 إيجار رقم (Rent)"
    else:
        text = "⏱️ **Select service type:**"
        btn_one_time = "🔢 One-time number (Temp)"
        btn_rent = "📅 Rent a number (Rent)"
        
    keyboard = [
        [InlineKeyboardButton(btn_one_time, callback_data="sp_type_temp")],
        [InlineKeyboardButton(btn_rent, callback_data="sp_type_rent")],
        [InlineKeyboardButton(get_smspool_message('back', language), callback_data="sp_main")]
    ]
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_smspool_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة اختيار نوع الخدمة"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    if data == "sp_type_temp":
        context.user_data['sp_order_type'] = 'temp'
        # فتح البحث عن الدول مباشرة للأرقام المؤقتة
        if language == 'ar':
            message_text = "🔍 *ابحث عن دولة أو خدمة*\nاضغط على الزر واكتب اسم الدولة."
            search_button = "🔍 ابحث عن دولة"
        else:
            message_text = "🔍 *Search for country or service*\nClick and type country name."
            search_button = "🔍 Search for country"
            
        keyboard = [[InlineKeyboardButton(search_button, switch_inline_query_current_chat="sp:")],
                    [InlineKeyboardButton(get_smspool_message('back', language), callback_data="sp_buy")]]
        await query.edit_message_text(message_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    elif data == "sp_type_rent":
        context.user_data['sp_order_type'] = 'rent'
        if language == 'ar':
            text = "⏳ **اختر مدة الإيجار:**"
            options = [("يوم واحد", "1"), ("3 أيام", "3"), ("7 أيام", "7"), ("30 يوم", "30")]
        else:
            text = "⏳ **Select rent duration:**"
            options = [("1 Day", "1"), ("3 Days", "3"), ("7 Days", "7"), ("30 Days", "30")]
            
        keyboard = []
        for label, val in options:
            keyboard.append([InlineKeyboardButton(label, callback_data=f"sp_rent_dur_{val}")])
        keyboard.append([InlineKeyboardButton(get_smspool_message('back', language), callback_data="sp_buy")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_smspool_rent_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    duration = query.data.replace("sp_rent_dur_", "")
    context.user_data['sp_rent_days'] = duration
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    search_btn = "🔍 ابحث عن دولة" if language == 'ar' else "🔍 Search for country"
    
    keyboard = [[InlineKeyboardButton(search_btn, switch_inline_query_current_chat="sp:")],
                [InlineKeyboardButton(get_smspool_message('back', language), callback_data="sp_type_rent")]]
    await query.edit_message_text("🌍 اختر الدولة الآن:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_services_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    country_id: str,
    page: int = 0,
    page_size: int = 15,
) -> None:
    """عرض الخدمات المتاحة لدولة معينة مع السعر (Live) + الهامش."""
    query = update.callback_query
    user_id = update.effective_user.id
    language = get_user_language(user_id)

    api_key = smspool_db.get_api_key()
    api = SMSPoolAPI(api_key)

    services = api.get_services()
    countries = api.get_countries()

    if not services or not countries:
        await query.edit_message_text(
            get_smspool_message('error', language).format(
                message=(
                    'تعذر جلب البيانات من SMSPool حالياً'
                    if language == 'ar'
                    else 'Failed to load data from SMSPool'
                )
            ),
            parse_mode='HTML',
        )
        return

    selected_country = next(
        (
            c
            for c in countries
            if str(c.get('ID', c.get('id', ''))) == str(country_id)
        ),
        None,
    )
    country_name = selected_country.get('name', 'Unknown') if selected_country else 'Unknown'
    country_code = selected_country.get('short_name', selected_country.get('code', '')) if selected_country else ''
    flag = get_country_flag(country_code)

    margin = smspool_db.get_margin_percent()

    # ترتيب خدمات شائعة أولاً
    popular_keywords = [
        'whatsapp',
        'telegram',
        'google',
        'facebook',
        'instagram',
        'tiktok',
        'twitter',
        'discord',
        'amazon',
        'uber',
    ]

    def popularity_key(svc: Dict[str, Any]) -> Tuple[int, str]:
        name = str(svc.get('name', '')).lower()
        for idx, kw in enumerate(popular_keywords):
            if kw in name:
                return (0, f"{idx:02d}_{name}")
        return (1, name)

    sorted_services = sorted(services, key=popularity_key)

    # Pagination على قائمة الخدمات (قبل فحص الأسعار)
    start = max(page, 0) * page_size
    end = start + page_size
    page_services = sorted_services[start:end]

    keyboard: List[List[InlineKeyboardButton]] = []

    for service in page_services:
        service_id = str(service.get('ID', service.get('id', '')))
        service_name = service.get('name', 'Unknown')

        price_info = api.get_service_price(service_id, country_id)

        icon = '📧'
        service_lower = str(service_name).lower()
        if 'whatsapp' in service_lower:
            icon = '💚'
        elif 'telegram' in service_lower:
            icon = '✈️'
        elif 'google' in service_lower:
            icon = '🔍'
        elif 'facebook' in service_lower:
            icon = '📘'
        elif 'instagram' in service_lower:
            icon = '📷'

        if price_info and price_info.get('price') is not None:
            cost_price = float(price_info.get('price'))
            sale_price = round(cost_price * (1 + margin / 100), 2)
            btn_text = f"✅ {icon} {service_name} - {sale_price:.2f} " + (
                'كريديت' if language == 'ar' else 'credits'
            )
            keyboard.append(
                [
                    InlineKeyboardButton(
                        btn_text,
                        callback_data=f"sp_buy_{country_id}_{service_id}",
                    )
                ]
            )
        else:
            btn_text = f"❌ {icon} {service_name} - " + (
                'غير متاح' if language == 'ar' else 'Unavailable'
            )
            keyboard.append([InlineKeyboardButton(btn_text, callback_data="sp_unavail")])

    nav_row: List[InlineKeyboardButton] = []
    if start > 0:
        nav_row.append(
            InlineKeyboardButton(
                "⬅️ " + ("السابق" if language == 'ar' else "Previous"),
                callback_data=f"sp_services_page_{country_id}_{page - 1}",
            )
        )
    if end < len(sorted_services):
        nav_row.append(
            InlineKeyboardButton(
                ("التالي" if language == 'ar' else "Next") + " ➡️",
                callback_data=f"sp_services_page_{country_id}_{page + 1}",
            )
        )
    if nav_row:
        keyboard.append(nav_row)

    keyboard.append(
        [
            InlineKeyboardButton(
                get_smspool_message('back', language),
                callback_data="sp_buy",
            )
        ]
    )

    title = get_smspool_message('select_service', language)
    text = f"<b>{flag} {country_name}</b>\n\n<b>{title}</b>"

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML',
    )


async def show_services_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    country_id: str,
) -> None:
    """Backward-compat wrapper."""
    await handle_services_menu(update, context, country_id=country_id, page=0)


async def confirm_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE,
                          country_id: str, service_id: str) -> None:
    """تأكيد الشراء"""
    query = update.callback_query
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    balance = get_user_balance(user_id)
    
    api_key = smspool_db.get_api_key()
    api = SMSPoolAPI(api_key)
    
    # الحصول على معلومات السعر (Live فقط)
    price_info = api.get_service_price(service_id, country_id)
    if not price_info or price_info.get('price') is None:
        msg = (
            'الخدمة غير متاحة في هذه الدولة حالياً' if language == 'ar' else 'Service is not available in this country right now'
        )
        await query.edit_message_text(
            get_smspool_message('error', language).format(message=msg),
            parse_mode='HTML',
        )
        return

    cost_price = float(price_info.get('price'))

    margin = smspool_db.get_margin_percent()
    sale_price = round(cost_price * (1 + margin / 100), 2)
    
    # الحصول على معلومات الخدمة والدولة
    services = api.get_services()
    service_name = 'Unknown'
    for s in services:
        if str(s.get('ID', s.get('id', ''))) == service_id:
            service_name = s.get('name', 'Unknown')
            break
    
    countries = api.get_countries()
    country_name = 'Unknown'
    country_code = ''
    for c in countries:
        if str(c.get('ID', c.get('id', ''))) == country_id:
            country_name = c.get('name', 'Unknown')
            country_code = c.get('short_name', '')
            break
    
    flag = get_country_flag(country_code)
    
    # أيقونة الخدمة
    icon = '📱'
    service_lower = service_name.lower()
    if 'whatsapp' in service_lower:
        icon = '💚'
    elif 'telegram' in service_lower:
        icon = '✈️'
    elif 'google' in service_lower:
        icon = '🔍'
    elif 'facebook' in service_lower:
        icon = '📘'
    elif 'instagram' in service_lower:
        icon = '📷'
    
    if balance < sale_price:
        await query.edit_message_text(
            get_smspool_message('insufficient_balance', language).format(
                balance=balance,
                required=sale_price
            ),
            parse_mode='HTML'
        )
        return
    
    context.user_data['sp_cost_price'] = cost_price
    context.user_data['sp_sale_price'] = sale_price
    context.user_data['sp_service_name'] = service_name
    context.user_data['sp_country_name'] = country_name
    
    if language == 'ar':
        text = f"""
💰 <b>تأكيد الشراء</b>

{icon} <b>الخدمة:</b> {service_name}
{flag} <b>الدولة:</b> {country_name}

💵 <b>السعر:</b> <code>{sale_price}</code> كريديت
💳 <b>رصيدك:</b> <code>{balance}</code> كريديت
💵 <b>الرصيد بعد الشراء:</b> <code>{balance - sale_price}</code> كريديت

هل تريد المتابعة؟
"""
    else:
        text = f"""
💰 <b>Confirm Purchase</b>

{icon} <b>Service:</b> {service_name}
{flag} <b>Country:</b> {country_name}

💵 <b>Price:</b> <code>{sale_price}</code> credits
💳 <b>Your balance:</b> <code>{balance}</code> credits
💵 <b>Balance after:</b> <code>{balance - sale_price}</code> credits

Do you want to proceed?
"""
    
    keyboard = [
        [InlineKeyboardButton(
            get_smspool_message('confirm_purchase', language),
            callback_data=f"sp_confirm_{country_id}_{service_id}"
        )],
        [InlineKeyboardButton(
            get_smspool_message('cancel', language),
            callback_data="sp_buy"
        )]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )




async def process_rent_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE,
                               country_id: str, service_id: str, days: str) -> None:
    """معالجة شراء إيجار رقم"""
    query = update.callback_query
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    # جلب السعر من API مباشرة للإيجار
    api_key = smspool_db.get_api_key()
    api = SMSPoolAPI(api_key)
    
    # استخدام endpoint خاص بالإيجار
    price_info = api._api_request("request/rent_price", data={
        'service': service_id,
        'country': country_id,
        'duration': days
    })
    
    if not price_info or price_info.get('price') is None:
        msg = (
            'خدمة الإيجار غير متاحة حالياً' if language == 'ar' else 'Rent service not available right now'
        )
        await query.edit_message_text(
            get_smspool_message('error', language).format(message=msg),
            parse_mode='HTML',
        )
        return
    
    cost_price = float(price_info.get('price'))
    margin = smspool_db.get_margin_percent()
    sale_price = round(cost_price * (1 + margin / 100), 2)
    
    balance = get_user_balance(user_id)
    if balance < sale_price:
        await query.edit_message_text(
            get_smspool_message('insufficient_balance', language).format(
                balance=balance,
                required=sale_price
            ),
            parse_mode='HTML'
        )
        return
    
    # الحصول على معلومات الخدمة والدولة
    services = api.get_services()
    service_name = 'Unknown'
    for s in services:
        if str(s.get('ID', s.get('id', ''))) == service_id:
            service_name = s.get('name', 'Unknown')
            break
    
    countries = api.get_countries()
    country_name = 'Unknown'
    for c in countries:
        if str(c.get('ID', c.get('id', ''))) == country_id:
            country_name = c.get('name', 'Unknown')
            break
    
    # عرض رسالة معالجة
    processing_msg = "⏳ " + ("جاري معالجة الطلب..." if language == 'ar' else "Processing order...")
    await query.edit_message_text(processing_msg)
    
    try:
        result = api.purchase_sms(country_id, service_id, order_type='rent', days=days)
        
        if result.get('status') == 'success':
            # خصم الرصيد
            update_user_balance(user_id, sale_price, 'subtract')
            
            order_id = result.get('order_id')
            number = result.get('number')
            country = result.get('country', country_name)
            service = result.get('service', service_name)
            pool = result.get('pool', '')
            expires_in = result.get('expires_in', int(days) * 24 * 3600)  # بالثواني
            
            # حفظ الطلب في قاعدة البيانات
            smspool_db.create_order(
                user_id=user_id,
                order_id=order_id,
                number=number,
                country=country,
                country_id=country_id,
                service=service,
                service_id=service_id,
                pool=str(pool),
                cost_price=cost_price,
                sale_price=sale_price,
                expires_in=expires_in
            )
            
            expires_days = int(days)
            
            text = get_smspool_message('purchase_success', language).format(
                number=number,
                country=country,
                service=service,
                expires=f"{expires_days} " + ("يوم" if language == 'ar' else "day(s)")
            )
            
            keyboard = [
                [InlineKeyboardButton(
                    "🔄 " + ("فحص الرسالة" if language == 'ar' else "Check SMS"),
                    callback_data=f"sp_check_{order_id}"
                )],
                [InlineKeyboardButton(
                    "📤 " + ("إعادة إرسال" if language == 'ar' else "Resend"),
                    callback_data=f"sp_resend_{order_id}"
                )],
                [InlineKeyboardButton(
                    "❌ " + ("إلغاء واسترداد" if language == 'ar' else "Cancel & Refund"),
                    callback_data=f"sp_cancel_{order_id}"
                )],
                [InlineKeyboardButton(
                    get_smspool_message('back', language),
                    callback_data="sp_main"
                )]
            ]
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
            
            # بدء المراقبة التلقائية للرسائل
            if hasattr(context, 'job_queue') and context.job_queue:
                context.job_queue.run_repeating(
                    check_sms_job,
                    interval=10,
                    first=5,
                    data={'order_id': order_id, 'user_id': user_id, 'chat_id': query.message.chat_id},
                    name=f"sms_check_{order_id}"
                )
        else:
            error_msg = result.get('message', 'Purchase failed')
            error_code = get_error_code_from_message(error_msg)
            
            await query.edit_message_text(
                get_smspool_message('error', language).format(message=ERROR_CODES.get(error_code, error_msg)),
                parse_mode='HTML'
            )
    
    except Exception as e:
        logger.error(f"خطأ في معالجة شراء إيجار SMSPool: {e}")
        error_text = "❌ " + ("حدث خطأ غير متوقع" if language == 'ar' else "An unexpected error occurred")
        await query.edit_message_text(error_text)

async def process_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE,
                          country_id: str, service_id: str) -> None:
    """معالجة الشراء"""
    query = update.callback_query
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    cost_price = context.user_data.get('sp_cost_price')
    sale_price = context.user_data.get('sp_sale_price')
    service_name = context.user_data.get('sp_service_name', 'Unknown')
    country_name = context.user_data.get('sp_country_name', 'Unknown')

    if cost_price is None or sale_price is None:
        await query.edit_message_text(
            get_smspool_message('error', language).format(
                message=(
                    'تعذر تحديد السعر. يرجى إعادة المحاولة.'
                    if language == 'ar'
                    else 'Could not determine price. Please try again.'
                )
            ),
            parse_mode='HTML',
        )
        return

    cost_price = float(cost_price)
    sale_price = float(sale_price)
    
    balance = get_user_balance(user_id)
    if balance < sale_price:
        await query.edit_message_text(
            get_smspool_message('insufficient_balance', language).format(
                balance=balance,
                required=sale_price
            ),
            parse_mode='HTML'
        )
        return
    
    # عرض رسالة معالجة
    processing_msg = "⏳ " + ("جاري معالجة الطلب..." if language == 'ar' else "Processing order...")
    await query.edit_message_text(processing_msg)
    
    api_key = smspool_db.get_api_key()
    api = SMSPoolAPI(api_key)
    
    try:
        order_type = context.user_data.get('sp_order_type', 'temp')
        rent_days = context.user_data.get('sp_rent_days')
        
        result = api.purchase_sms(country_id, service_id, order_type=order_type, days=rent_days)
        
        if result.get('status') == 'success':
            # خصم الرصيد
            update_user_balance(user_id, sale_price, 'subtract')
            
            order_id = result.get('order_id')
            number = result.get('number')
            country = result.get('country', country_name)
            service = result.get('service', service_name)
            pool = result.get('pool', '')
            expires_in = result.get('expires_in', 600)
            
            # حفظ الطلب في قاعدة البيانات
            smspool_db.create_order(
                user_id=user_id,
                order_id=order_id,
                number=number,
                country=country,
                country_id=country_id,
                service=service,
                service_id=service_id,
                pool=str(pool),
                cost_price=cost_price,
                sale_price=sale_price,
                expires_in=expires_in
            )
            
            expires_min = expires_in // 60
            
            # أيقونة الخدمة
            icon = '📱'
            service_lower = service.lower()
            if 'whatsapp' in service_lower:
                icon = '💚'
            elif 'telegram' in service_lower:
                icon = '✈️'
            elif 'google' in service_lower:
                icon = '🔍'
            elif 'facebook' in service_lower:
                icon = '📘'
            elif 'instagram' in service_lower:
                icon = '📷'
            
            text = get_smspool_message('purchase_success', language).format(
                number=number,
                country=country,
                service=service,
                expires=expires_min
            )
            
            keyboard = [
                [InlineKeyboardButton(
                    "🔄 " + ("فحص الرسالة" if language == 'ar' else "Check SMS"),
                    callback_data=f"sp_check_{order_id}"
                )],
                [InlineKeyboardButton(
                    "📤 " + ("إعادة إرسال" if language == 'ar' else "Resend"),
                    callback_data=f"sp_resend_{order_id}"
                )],
                [InlineKeyboardButton(
                    "❌ " + ("إلغاء واسترداد" if language == 'ar' else "Cancel & Refund"),
                    callback_data=f"sp_cancel_{order_id}"
                )],
                [InlineKeyboardButton(
                    get_smspool_message('back', language),
                    callback_data="sp_main"
                )]
            ]
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
            
            # بدء المراقبة التلقائية للرسائل
            if hasattr(context, 'job_queue') and context.job_queue:
                context.job_queue.run_repeating(
                    check_sms_job,
                    interval=10,
                    first=5,
                    data={'order_id': order_id, 'user_id': user_id, 'chat_id': query.message.chat_id},
                    name=f"sms_check_{order_id}"
                )
                logger.info(f"🔄 بدء المراقبة التلقائية للطلب {order_id}")
            else:
                logger.warning("⚠️ job_queue غير متاح - المراقبة التلقائية معطلة")
        else:
            error_msg = result.get('message', 'Purchase failed')
            error_code = get_error_code_from_message(error_msg)
            
            await query.edit_message_text(
                get_smspool_message('error', language).format(message=ERROR_CODES.get(error_code, error_msg)),
                parse_mode='HTML'
            )
            
            logger.error(f"فشل شراء SMSPool للمستخدم {user_id}: {error_msg}")
    
    except Exception as e:
        logger.error(f"خطأ في معالجة شراء SMSPool: {e}")
        
        error_text = "❌ " + ("حدث خطأ غير متوقع" if language == 'ar' else "An unexpected error occurred")
        error_text += "\n\n"
        error_text += ("يرجى المحاولة لاحقاً أو التواصل مع الآدمن" if language == 'ar' else "Please try again later or contact admin")
        
        await query.edit_message_text(error_text)


async def check_sms_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """وظيفة فحص الرسائل التلقائية"""
    job = context.job
    data = job.data
    
    order_id = data['order_id']
    user_id = data['user_id']
    chat_id = data['chat_id']
    
    language = get_user_language(user_id)
    
    api_key = smspool_db.get_api_key()
    api = SMSPoolAPI(api_key)
    
    result = api.check_sms(order_id)
    status = result.get('status')
    
    if status == 'received':
        job.schedule_removal()
        
        sms_code = result.get('sms', '')
        full_sms = result.get('full_sms', '')
        
        smspool_db.update_order_status(order_id, 'received', sms_code, full_sms)
        
        order = smspool_db.get_order_by_order_id(order_id)
        number = order.get('number', '') if order else ''
        
        text = get_smspool_message('sms_received', language).format(
            number=number,
            code=sms_code,
            full_sms=full_sms
        )
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='HTML'
        )
    
    elif status in ['cancelled', 'expired']:
        job.schedule_removal()
        smspool_db.update_order_status(order_id, status)


async def check_order_status(update: Update, context: ContextTypes.DEFAULT_TYPE,
                            order_id: str) -> None:
    """فحص حالة الطلب يدوياً"""
    query = update.callback_query
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    api_key = smspool_db.get_api_key()
    api = SMSPoolAPI(api_key)
    
    result = api.check_sms(order_id)
    status = result.get('status')
    
    order = smspool_db.get_order_by_order_id(order_id)
    number = order.get('number', '') if order else ''
    
    if status == 'received':
        sms_code = result.get('sms', '')
        full_sms = result.get('full_sms', '')
        
        smspool_db.update_order_status(order_id, 'received', sms_code, full_sms)
        
        text = get_smspool_message('sms_received', language).format(
            number=number,
            code=sms_code,
            full_sms=full_sms
        )
    elif status == 'waiting':
        text = get_smspool_message('waiting_sms', language)
    elif status == 'cancelled':
        text = get_smspool_message('order_cancelled', language)
    elif status == 'expired':
        text = get_smspool_message('order_expired', language)
    else:
        text = get_smspool_message('error', language).format(message=result.get('message', 'Unknown'))
    
    keyboard = [
        [InlineKeyboardButton(
            "🔄 " + ("فحص مرة أخرى" if language == 'ar' else "Check Again"),
            callback_data=f"sp_check_{order_id}"
        )],
        [InlineKeyboardButton(
            get_smspool_message('back', language),
            callback_data="sp_my_orders"
        )]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE,
                      order_id: str) -> None:
    """إلغاء الطلب"""
    query = update.callback_query
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    order = smspool_db.get_order_by_order_id(order_id)
    if not order or order.get('user_id') != user_id:
        await query.answer("Order not found", show_alert=True)
        return
    
    api_key = smspool_db.get_api_key()
    api = SMSPoolAPI(api_key)
    
    result = api.cancel_sms(order_id)
    
    if result.get('status') == 'success':
        sale_price = order.get('sale_price', 0)
        update_user_balance(user_id, sale_price, 'add')
        
        smspool_db.update_order_status(order_id, 'cancelled')
        
        for job in context.job_queue.get_jobs_by_name(f"sms_check_{order_id}"):
            job.schedule_removal()
        
        text = get_smspool_message('order_cancelled', language)
    else:
        text = get_smspool_message('error', language).format(message=result.get('message', 'Cancel failed'))
    
    keyboard = [[InlineKeyboardButton(
        get_smspool_message('back', language),
        callback_data="sp_main"
    )]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def resend_sms(update: Update, context: ContextTypes.DEFAULT_TYPE,
                    order_id: str) -> None:
    """إعادة إرسال الرسالة"""
    query = update.callback_query
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    api_key = smspool_db.get_api_key()
    api = SMSPoolAPI(api_key)
    
    result = api.resend_sms(order_id)
    
    if result.get('status') == 'success':
        if language == 'ar':
            text = "✅ تم طلب إعادة إرسال الرسالة"
        else:
            text = "✅ SMS resend requested"
    else:
        text = get_smspool_message('error', language).format(message=result.get('message', 'Resend failed'))
    
    await query.answer(text, show_alert=True)


def _parse_db_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None

    if isinstance(value, datetime):
        return value

    s = str(value)
    try:
        return datetime.fromisoformat(s)
    except Exception:
        try:
            return datetime.strptime(s.split('.')[0], '%Y-%m-%d %H:%M:%S')
        except Exception:
            return None


def _format_time_left(expires_at: Any, language: str) -> str:
    dt = _parse_db_datetime(expires_at)
    if not dt:
        return 'غير معروف' if language == 'ar' else 'Unknown'

    delta = dt - datetime.now()
    total = int(delta.total_seconds())
    if total <= 0:
        return 'منتهي' if language == 'ar' else 'Expired'

    hours = total // 3600
    minutes = (total % 3600) // 60
    seconds = total % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def _status_label(status: str, language: str) -> Tuple[str, str]:
    status = (status or '').lower()

    mapping = {
        'pending': ('⏳', 'في الانتظار' if language == 'ar' else 'Waiting'),
        'received': ('✅', 'مستلم' if language == 'ar' else 'Received'),
        'cancelled': ('❌', 'ملغى' if language == 'ar' else 'Cancelled'),
        'expired': ('⏰', 'منتهي' if language == 'ar' else 'Expired'),
    }
    return mapping.get(status, ('❓', status or 'Unknown'))


async def handle_my_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0) -> None:
    """زر (أرقامي): يعرض الأرقام النشطة فقط مع خيارات الإدارة + Pagination."""
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id
    language = get_user_language(user_id)

    page_size = 10
    page = max(page, 0)
    offset = page * page_size

    total = smspool_db.count_user_active_orders(user_id)
    orders = smspool_db.get_user_active_orders(user_id, limit=page_size, offset=offset)

    if not orders:
        keyboard = [[InlineKeyboardButton(get_smspool_message('back', language), callback_data='sp_main')]]
        await query.edit_message_text(
            get_smspool_message('no_active_numbers', language),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML',
        )
        return

    title = '📋 <b>أرقامي</b>' if language == 'ar' else '📋 <b>My Numbers</b>'
    text = title + "\n\n"

    keyboard: List[List[InlineKeyboardButton]] = []

    for idx, order in enumerate(orders, start=offset + 1):
        order_id = str(order.get('order_id', ''))
        number = order.get('number', 'N/A')
        service = order.get('service', 'N/A')
        country = order.get('country', 'N/A')
        status = order.get('status', 'pending')

        emoji, status_text = _status_label(status, language)
        time_left = _format_time_left(order.get('expires_at'), language)

        text += (
            f"<b>{idx}.</b> {emoji} <b>{service}</b>\n"
            f"📱 <code>{number}</code>\n"
            f"🌍 {country}\n"
            f"🔔 {(status_text)}\n"
            f"⏱️ {(('الوقت المتبقي' if language == 'ar' else 'Time left'))}: <code>{time_left}</code>\n\n"
        )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "🔄 " + ("Check SMS" if language == 'en' else "فحص"),
                    callback_data=f"sp_check_{order_id}",
                ),
                InlineKeyboardButton(
                    "📤 " + ("Resend" if language == 'en' else "إعادة إرسال"),
                    callback_data=f"sp_resend_{order_id}",
                ),
                InlineKeyboardButton(
                    "❌ " + ("Cancel" if language == 'en' else "إلغاء"),
                    callback_data=f"sp_cancel_{order_id}",
                ),
            ]
        )

    nav_row: List[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(
                "⬅️ " + ("السابق" if language == 'ar' else "Previous"),
                callback_data=f"sp_my_numbers_page_{page - 1}",
            )
        )
    if offset + page_size < total:
        nav_row.append(
            InlineKeyboardButton(
                ("التالي" if language == 'ar' else "Next") + " ➡️",
                callback_data=f"sp_my_numbers_page_{page + 1}",
            )
        )
    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton(get_smspool_message('back', language), callback_data='sp_main')])

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML',
    )


async def handle_history(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0) -> None:
    """زر (History): يعرض فقط الأرقام المنتهية القابلة لإعادة الشراء."""
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id
    language = get_user_language(user_id)

    page_size = 10
    page = max(page, 0)
    offset = page * page_size

    total_expired = smspool_db.count_user_expired_orders(user_id)
    total_renewable = smspool_db.count_user_renewable_orders(user_id)
    total_cost = smspool_db.sum_user_renewable_cost(user_id)

    orders = smspool_db.get_user_renewable_orders(user_id, limit=page_size, offset=offset)

    if language == 'ar':
        header = "📋 <b>الأرقام المتاحة للتجديد:</b>\n\n"
        stats_title = "📊 <b>إحصائيات:</b>"
    else:
        header = "📋 <b>Numbers available for renewal:</b>\n\n"
        stats_title = "📊 <b>Stats:</b>"

    if not orders:
        text = header + get_smspool_message('no_history', language) + "\n\n" + stats_title
        text += f"\n- {( 'إجمالي الأرقام المنتهية' if language=='ar' else 'Total expired')}: {total_expired}"
        text += f"\n- {( 'الأرقام المتاحة للتجديد' if language=='ar' else 'Renewable')}: {total_renewable}"
        text += f"\n- {( 'إجمالي تكلفة التجديد' if language=='ar' else 'Total renewal cost')}: {total_cost:.2f}"

        keyboard = [[InlineKeyboardButton(get_smspool_message('back', language), callback_data='sp_main')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return

    text = header
    keyboard: List[List[InlineKeyboardButton]] = []

    for idx, order in enumerate(orders, start=offset + 1):
        order_id = str(order.get('order_id', ''))
        number = order.get('number', 'N/A')
        service = order.get('service', 'N/A')
        country = order.get('country', 'N/A')
        price = float(order.get('sale_price') or 0)
        expires_at = order.get('expires_at')

        ended = str(expires_at) if expires_at else ('غير معروف' if language == 'ar' else 'Unknown')

        if language == 'ar':
            text += (
                f"🔹 <b>رقم {idx}:</b>\n"
                f"   📱 <code>{number}</code>\n"
                f"   📧 {service}\n"
                f"   🌍 {country}\n"
                f"   💰 السعر: {price:.2f} كريديت\n"
                f"   📅 انتهت في: {ended}\n"
                f"   ✅ جاهز للتجديد\n\n"
            )
            btn_label = f"🔄 تجديد رقم {idx}"
        else:
            text += (
                f"🔹 <b>#{idx}:</b>\n"
                f"   📱 <code>{number}</code>\n"
                f"   📧 {service}\n"
                f"   🌍 {country}\n"
                f"   💰 Price: {price:.2f} credits\n"
                f"   📅 Expired at: {ended}\n"
                f"   ✅ Ready to renew\n\n"
            )
            btn_label = f"🔄 Renew #{idx}"

        keyboard.append([InlineKeyboardButton(btn_label, callback_data=f"sp_renew_{order_id}")])

    text += stats_title
    text += f"\n- {( 'إجمالي الأرقام المنتهية' if language=='ar' else 'Total expired')}: {total_expired}"
    text += f"\n- {( 'الأرقام المتاحة للتجديد' if language=='ar' else 'Renewable')}: {total_renewable}"
    text += f"\n- {( 'إجمالي تكلفة التجديد' if language=='ar' else 'Total renewal cost')}: {total_cost:.2f}"

    nav_row: List[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(
                "⬅️ " + ("السابق" if language == 'ar' else "Previous"),
                callback_data=f"sp_history_page_{page - 1}",
            )
        )
    if offset + page_size < total_renewable:
        nav_row.append(
            InlineKeyboardButton(
                ("التالي" if language == 'ar' else "Next") + " ➡️",
                callback_data=f"sp_history_page_{page + 1}",
            )
        )
    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton(get_smspool_message('back', language), callback_data='sp_main')])

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML',
    )


async def renew_smspool_number(update: Update, context: ContextTypes.DEFAULT_TYPE, original_order_id: str) -> None:
    """تجديد رقم من History (شراء جديد بنفس الدولة/الخدمة) + تسجيل smspool_renewal_log."""
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id
    language = get_user_language(user_id)

    order = smspool_db.get_order_by_order_id(original_order_id)
    if not order or int(order.get('user_id') or 0) != int(user_id):
        await query.answer("❌ " + ("الطلب غير موجود" if language == 'ar' else "Order not found"), show_alert=True)
        return

    if order.get('status') != 'expired' or int(order.get('already_renewed') or 0) == 1:
        await query.answer(
            "⚠️ " + ("هذا الرقم غير قابل للتجديد" if language == 'ar' else "This number is not renewable"),
            show_alert=True,
        )
        return

    country_id = str(order.get('country_id', ''))
    service_id = str(order.get('service_id', ''))

    margin = smspool_db.get_margin_percent()

    api_key = smspool_db.get_api_key()
    api = SMSPoolAPI(api_key)

    # سعر التجديد: نحاول جلبه Live، وإن فشل نستخدم السعر المحفوظ
    price_info = api.get_service_price(service_id, country_id)
    if price_info and price_info.get('price') is not None:
        cost_price = float(price_info.get('price'))
        renewal_price = round(cost_price * (1 + margin / 100), 2)
    else:
        cost_price = float(order.get('cost_price') or 0)
        renewal_price = float(order.get('sale_price') or 0)

    balance = get_user_balance(user_id)
    if balance < renewal_price:
        await query.edit_message_text(
            get_smspool_message('insufficient_balance', language).format(
                balance=balance,
                required=renewal_price,
            ),
            parse_mode='HTML',
        )
        return

    await query.edit_message_text(
        "⏳ " + ("جاري التجديد..." if language == 'ar' else "Renewing..."),
        parse_mode='HTML',
    )

    result = api.purchase_sms(country_id, service_id, pool=order.get('pool') or None)
    if result.get('status') != 'success':
        error_msg = result.get('message', 'Renewal failed')
        error_code = get_error_code_from_message(error_msg)
        await query.edit_message_text(
            get_smspool_message('error', language).format(message=ERROR_CODES.get(error_code, error_msg)),
            parse_mode='HTML',
        )
        return

    # خصم الرصيد + حفظ الطلب الجديد + تسجيل التجديد
    update_user_balance(user_id, renewal_price, 'subtract')

    new_order_id = result.get('order_id')
    number = result.get('number')
    country = result.get('country', order.get('country', 'Unknown'))
    service = result.get('service', order.get('service', 'Unknown'))
    pool = result.get('pool', order.get('pool', ''))
    expires_in = result.get('expires_in', 600)

    smspool_db.create_order(
        user_id=user_id,
        order_id=new_order_id,
        number=number,
        country=country,
        country_id=country_id,
        service=service,
        service_id=service_id,
        pool=str(pool or ''),
        cost_price=cost_price,
        sale_price=renewal_price,
        expires_in=expires_in,
    )

    smspool_db.mark_order_as_renewed(original_order_id)
    smspool_db.log_renewal(original_order_id, new_order_id, user_id, renewal_price)

    expires_min = int(expires_in) // 60

    if language == 'ar':
        text = (
            f"✅ <b>تم تجديد الرقم بنجاح!</b>\n\n"
            f"📱 الرقم: <code>{number}</code>\n"
            f"🌍 الدولة: {country}\n"
            f"📧 الخدمة: {service}\n"
            f"⏱️ صالح لمدة: {expires_min} دقيقة\n"
        )
    else:
        text = (
            f"✅ <b>Number renewed successfully!</b>\n\n"
            f"📱 Number: <code>{number}</code>\n"
            f"🌍 Country: {country}\n"
            f"📧 Service: {service}\n"
            f"⏱️ Valid for: {expires_min} minutes\n"
        )

    keyboard = [
        [InlineKeyboardButton("🔄 " + ("فحص الرسالة" if language == 'ar' else "Check SMS"), callback_data=f"sp_check_{new_order_id}")],
        [InlineKeyboardButton("📤 " + ("إعادة إرسال" if language == 'ar' else "Resend"), callback_data=f"sp_resend_{new_order_id}")],
        [InlineKeyboardButton("❌ " + ("إلغاء واسترداد" if language == 'ar' else "Cancel & Refund"), callback_data=f"sp_cancel_{new_order_id}")],
        [InlineKeyboardButton(get_smspool_message('back', language), callback_data='sp_main')],
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    if hasattr(context, 'job_queue') and context.job_queue:
        context.job_queue.run_repeating(
            check_sms_job,
            interval=10,
            first=5,
            data={'order_id': new_order_id, 'user_id': user_id, 'chat_id': query.message.chat_id},
            name=f"sms_check_{new_order_id}",
        )


async def show_user_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض طلبات المستخدم"""
    query = update.callback_query
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    orders = smspool_db.get_user_orders(user_id, limit=10)
    
    if not orders:
        text = get_smspool_message('no_orders', language)
        keyboard = [[InlineKeyboardButton(
            get_smspool_message('back', language),
            callback_data="sp_main"
        )]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    if language == 'ar':
        text = "📋 <b>طلباتك الأخيرة:</b>\n\n"
    else:
        text = "📋 <b>Your Recent Orders:</b>\n\n"
    
    keyboard = []
    for order in orders:
        number = order.get('number', 'N/A')
        service = order.get('service', 'N/A')
        status = order.get('status', 'pending')
        order_id = order.get('order_id', '')
        
        status_emoji = {
            'pending': '⏳',
            'received': '✅',
            'cancelled': '❌',
            'expired': '⏰'
        }.get(status, '❓')
        
        text += f"{status_emoji} {service}: <code>{number}</code>\n"
        
        if status == 'pending':
            keyboard.append([InlineKeyboardButton(
                f"🔄 {number}",
                callback_data=f"sp_check_{order_id}"
            )])
    
    keyboard.append([InlineKeyboardButton(
        get_smspool_message('back', language),
        callback_data="sp_main"
    )])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


def get_country_flag(country_code: str) -> str:
    """جلب علم الدولة"""
    if not country_code or len(country_code) != 2:
        return "🌍"
    
    try:
        flag = ''.join(chr(127397 + ord(c)) for c in country_code.upper())
        return flag
    except:
        return "🌍"


async def smspool_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """قائمة إدارة SMSPool للآدمن"""
    query = update.callback_query
    if query:
        await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)

    api_key = smspool_db.get_api_key()
    enabled = smspool_db.is_enabled()
    margin = smspool_db.get_margin_percent()

    balance_info = "❓ " + ("غير متصل" if language == 'ar' else "Not connected")
    if api_key:
        api = SMSPoolAPI(api_key)
        is_ok, status_msg, balance = api.test_connection()
        if is_ok and balance is not None:
            balance_info = ("✅ متصل" if language == 'ar' else "✅ Connected") + f" | 💰 ${balance}"
        else:
            short_msg = (status_msg or "Unknown")[:40]
            balance_info = ("❌ فشل الاتصال" if language == 'ar' else "❌ Connection failed") + f" | {short_msg}"
    
    text = f"""
⚙️ <b>إعدادات SMSPool</b>

🔑 مفتاح API: {'✅ مُعيّن' if api_key else '❌ غير مُعيّن'}
{balance_info}
📊 الخدمة: {'✅ مفعّلة' if enabled else '❌ معطّلة'}
💹 نسبة الربح: {margin}%
📦 الطلبات النشطة: {smspool_db.get_active_orders_count()}
"""
    
    keyboard = [
        [InlineKeyboardButton("🔑 تعيين مفتاح API", callback_data="sp_admin_set_key")],
        [InlineKeyboardButton(
            "🔌 اختبار الاتصال" if language == 'ar' else "🔌 Test Connection",
            callback_data="sp_admin_test",
        )],
        [InlineKeyboardButton(
            "❌ تعطيل الخدمة" if enabled else "✅ تفعيل الخدمة",
            callback_data="sp_admin_toggle"
        )],
        [InlineKeyboardButton("💹 تعديل نسبة الربح", callback_data="sp_admin_margin")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_menu")]
    ]
    
    if query:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )


async def handle_smspool_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    """معالج callbacks الآدمن لـ SMSPool"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "sp_admin_menu":
        await smspool_admin_menu(update, context)
        return None
    
    elif data == "sp_admin_toggle":
        current = smspool_db.is_enabled()
        smspool_db.set_enabled(not current)
        await smspool_admin_menu(update, context)
        return None

    elif data == "sp_admin_test":
        api_key = smspool_db.get_api_key()
        if not api_key:
            await query.answer("❌ " + ("مفتاح API غير مُعيّن" if get_user_language(update.effective_user.id) == 'ar' else "API key not set"), show_alert=True)
            return None

        api = SMSPoolAPI(api_key)
        is_ok, status_msg, balance = api.test_connection()
        if is_ok:
            msg = (
                f"✅ الاتصال ناجح\n💰 الرصيد: ${balance}" if get_user_language(update.effective_user.id) == 'ar' else f"✅ Connection OK\n💰 Balance: ${balance}"
            )
            await query.answer(msg, show_alert=True)
        else:
            msg = (
                f"❌ فشل الاتصال: {status_msg}" if get_user_language(update.effective_user.id) == 'ar' else f"❌ Connection failed: {status_msg}"
            )
            await query.answer(msg[:200], show_alert=True)

        await smspool_admin_menu(update, context)
        return None
    
    elif data == "sp_admin_set_key":
        await query.edit_message_text(
            "🔑 أرسل مفتاح API الخاص بـ SMSPool:\n\n"
            "يمكنك الحصول عليه من: https://www.smspool.net/my/settings",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ إلغاء", callback_data="sp_admin_menu")]
            ])
        )
        return 100
    
    elif data == "sp_admin_margin":
        await query.edit_message_text(
            f"💹 أرسل نسبة الربح الجديدة (رقم فقط):\n\n"
            f"النسبة الحالية: {smspool_db.get_margin_percent()}%",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ إلغاء", callback_data="sp_admin_menu")]
            ])
        )
        return 101
    
    return None


async def handle_admin_api_key_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إدخال مفتاح API"""
    api_key = update.message.text.strip()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)

    if len(api_key) >= 32:
        api = SMSPoolAPI(api_key)
        is_ok, status_msg, balance = api.test_connection()

        if is_ok:
            smspool_db.set_api_key(api_key)
            if language == 'ar':
                await update.message.reply_text(
                    f"✅ تم حفظ مفتاح API بنجاح!\n💰 الرصيد: ${balance}"
                )
            else:
                await update.message.reply_text(
                    f"✅ API key saved successfully!\n💰 Balance: ${balance}"
                )
        else:
            if language == 'ar':
                await update.message.reply_text(f"❌ فشل اختبار مفتاح API: {status_msg}")
            else:
                await update.message.reply_text(f"❌ API key test failed: {status_msg}")
    else:
        await update.message.reply_text(
            "❌ مفتاح API يجب أن يكون 32 حرفاً على الأقل!" if language == 'ar' else "❌ API key must be at least 32 characters!"
        )
    
    return ConversationHandler.END


async def handle_admin_margin_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إدخال نسبة الربح"""
    try:
        margin = float(update.message.text.strip().replace('%', ''))
        if 0 <= margin <= 500:
            smspool_db.set_margin_percent(margin)
            await update.message.reply_text(f"✅ تم تحديث نسبة الربح إلى {margin}%")
        else:
            await update.message.reply_text("❌ النسبة يجب أن تكون بين 0 و 500!")
    except ValueError:
        await update.message.reply_text("❌ أدخل رقماً صحيحاً!")
    
    return ConversationHandler.END


async def handle_countries_inline_query(
    api: SMSPoolAPI,
    language: str,
    query_text: str = "",
    limit: int = 20,
) -> List[InlineQueryResultArticle]:
    """جلب وعرض الدول الفعلية من SMSPool API (للاستخدام داخل Inline Query)."""
    q = (query_text or "").strip().lower()

    countries = api.get_countries()
    if not countries:
        return []

    if q:
        filtered = [
            c
            for c in countries
            if q in str(c.get('name', '')).lower()
            or q in str(c.get('short_name', c.get('code', ''))).lower()
        ]
    else:
        popular_codes = ['US', 'GB', 'CA', 'DE', 'FR', 'NL', 'RU', 'IN', 'PH', 'ID']
        popular = [c for c in countries if str(c.get('short_name', '')).upper() in popular_codes]
        others = [c for c in countries if str(c.get('short_name', '')).upper() not in popular_codes]
        filtered = popular + others

    results: List[InlineQueryResultArticle] = []

    for country in filtered[:limit]:
        country_id = str(country.get('ID', country.get('id', '')))
        country_name = country.get('name', 'Unknown')
        short_name = country.get('short_name', country.get('code', ''))

        flag = get_country_flag(short_name)

        title = f"{flag} {country_name}"
        description = 'انقر لعرض الخدمات المتاحة' if language == 'ar' else 'Click to view available services'

        results.append(
            InlineQueryResultArticle(
                id=f'country_{country_id}',
                title=title,
                description=description,
                input_message_content=InputTextMessageContent(
                    f"{flag} **{country_name}**\n\n"
                    + (
                        'جاري تحميل الخدمات المتاحة...'
                        if language == 'ar'
                        else 'Loading available services...'
                    ),
                    parse_mode='Markdown',
                ),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                '📱 ' + ('عرض الخدمات' if language == 'ar' else 'View Services'),
                                switch_inline_query_current_chat=f"sp_svc:{country_id}:"
                            )
                        ]
                    ]
                ),
                thumbnail_url='https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Mobile_phone_icon.svg/120px-Mobile_phone_icon.svg.png',
            )
        )

    return results


async def handle_smspool_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    معالج Inline Query للبحث عن خدمات ودول SMSPool
    يعمل بنفس طريقة NonVoip الناجح
    """
    raw_query = (update.inline_query.query or "").strip()
    raw_lower = raw_query.lower()

    user_id = update.effective_user.id
    language = get_user_language(user_id)

    # ✅ البحث عن خدمات لدولة محددة: sp_svc:{country_id}:{query}
    if raw_lower.startswith("sp_svc:"):
        parts = raw_lower.split(":")
        if len(parts) >= 3:
            country_id = parts[1]
            query_text = ":".join(parts[2:]).strip()
            
            api_key = smspool_db.get_api_key()
            if not api_key: return
            api = SMSPoolAPI(api_key)
            
            services = api.get_services()
            margin = smspool_db.get_margin_percent()
            
            results = []
            matching = [s for s in services if query_text in str(s.get('name', '')).lower()]
            
            for svc in matching[:25]:
                service_id = str(svc.get('ID', svc.get('id', '')))
                service_name = svc.get('name', 'Unknown')
                
                # جلب السعر حسب النوع (Temp أو Rent)
                order_type = context.user_data.get('sp_order_type', 'temp')
                if order_type == 'rent':
                    # https://api.smspool.net/request/rent_price
                    rent_days = context.user_data.get('sp_rent_days', '1')
                    price_info = api._api_request("request/rent_price", data={'service': service_id, 'country': country_id, 'duration': rent_days})
                else:
                    price_info = api.get_service_price(service_id, country_id)

                if price_info and price_info.get('price') is not None:
                    cost_price = float(price_info.get('price'))
                    sale_price = round(cost_price * (1 + margin / 100), 2)
                    
                    icon = '📱'
                    if 'whatsapp' in service_name.lower(): icon = '💚'
                    elif 'telegram' in service_name.lower(): icon = '✈️'
                    
                    title = f"{icon} {service_name}"
                    description = f"💰 {sale_price:.2f} " + ('كريديت' if language == 'ar' else 'credits')
                    
                    results.append(
                        InlineQueryResultArticle(
                            id=f"sp_svc_{country_id}_{service_id}",
                            title=title,
                            description=description,
                            input_message_content=InputTextMessageContent(
                                f"{icon} **{service_name}**\n💰 {description}",
                                parse_mode='Markdown'
                            ),
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton(
                                    "✅ " + ('تأكيد الشراء' if language == 'ar' else 'Confirm Purchase'),
                                    callback_data=f"sp_buy_{country_id}_{service_id}"
                                )
                            ]])
                        )
                    )
            
            await update.inline_query.answer(results, cache_time=30, is_personal=True)
            return

    # ✅ SMSPool inline queries يجب أن تبدأ بـ prefix لتجنب تضارب InlineQueryHandler الموحد
    if raw_lower.startswith("sp:"):
        query_text = raw_lower[3:].strip()
    elif raw_lower.startswith("smspool:"):
        query_text = raw_lower[len("smspool:"):].strip()
    elif not raw_lower.startswith(("socks:", "type:", "sp_svc:")):
        # إذا لم يبدأ بـ prefix معروف، سنعتبره بحثاً مباشراً عن دول/خدمات SMSPool
        query_text = raw_lower
    else:
        return

    user_id = update.effective_user.id

    # تجاهل إذا كان البحث خاصاً بخدمات أخرى
    if query_text.startswith("socks:") or query_text.startswith("type:"):
        return
    
    language = get_user_language(user_id)
    
    logger.info(f"🔍 SMSPool Inline query من المستخدم {user_id}: '{query_text}'")
    
    try:
        api_key = smspool_db.get_api_key()
        if not api_key:
            error_result = [
                InlineQueryResultArticle(
                    id='no_api_key',
                    title='❌ ' + ('الخدمة غير متاحة' if language == 'ar' else 'Service unavailable'),
                    description='يرجى التواصل مع الآدمن' if language == 'ar' else 'Please contact admin',
                    input_message_content=InputTextMessageContent(
                        get_smspool_message('service_disabled', language)
                    )
                )
            ]
            await update.inline_query.answer(error_result, cache_time=10)
            return
        
        api = SMSPoolAPI(api_key)
        
        # إذا كان البحث فارغاً: عرض رسالة مساعدة + بعض الدول الشائعة من API
        if not query_text:
            countries = api.get_countries()
            if not countries:
                await update.inline_query.answer([], cache_time=10, is_personal=True)
                return

            if language == 'ar':
                help_title = "ابدأ البحث عن الدول والخدمات في SMSPool"
                help_desc = "مثال: اكتب google أو us"
                help_text = "ابدأ البحث عن الدول والخدمات في SMSPool\n\nمثال: اكتب: google أو us"
            else:
                help_title = "Start searching SMSPool countries & services"
                help_desc = "Example: type google or us"
                help_text = "Start searching SMSPool countries & services\n\nExample: type: google or us"

            # ترتيب الدول الشائعة أولاً
            popular_codes = ['US', 'GB', 'CA', 'DE', 'FR', 'NL', 'RU', 'IN', 'PH', 'ID']
            popular_countries = []
            other_countries = []

            for country in countries[:80]:
                short_name = country.get('short_name', country.get('code', ''))
                if short_name in popular_codes:
                    popular_countries.append(country)
                else:
                    other_countries.append(country)

            # دمج القوائم: الشائعة أولاً
            sorted_countries = popular_countries + other_countries[:20]

            results = [
                InlineQueryResultArticle(
                    id='sp_help',
                    title='ℹ️ ' + help_title,
                    description=help_desc,
                    input_message_content=InputTextMessageContent(help_text),
                )
            ]
            for country in sorted_countries[:20]:
                country_id = str(country.get('ID', country.get('id', '')))
                country_name = country.get('name', 'Unknown')
                short_name = country.get('short_name', country.get('code', ''))
                
                flag = get_country_flag(short_name)
                
                title = f"{flag} {country_name}"
                description = 'انقر لعرض الخدمات المتاحة' if language == 'ar' else 'Click to view available services'
                
                results.append(
                    InlineQueryResultArticle(
                        id=f'country_{country_id}',
                        title=title,
                        description=description,
                        input_message_content=InputTextMessageContent(
                            f"{flag} **{country_name}**\n\n"
                            + ('جاري تحميل الخدمات المتاحة...' if language == 'ar' else 'Loading available services...'),
                            parse_mode='Markdown'
                        ),
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton(
                                '📱 ' + ('عرض الخدمات' if language == 'ar' else 'View Services'),
                                switch_inline_query_current_chat=f"sp_svc:{country_id}:"
                            )
                        ]]),
                        thumbnail_url='https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Mobile_phone_icon.svg/120px-Mobile_phone_icon.svg.png'
                    )
                )
            
            await update.inline_query.answer(
                results,
                cache_time=300,
                is_personal=True,
                button=InlineQueryResultsButton(
                    text='💡 ' + ('اختر دولة' if language == 'ar' else 'Select a country'),
                    start_parameter='inline_help'
                )
            )
            return
        
        # البحث عن دول أو خدمات
        results = []
        
        # البحث في الدول
        countries = api.get_countries()
        matching_countries = []
        
        for country in countries:
            country_name = country.get('name', '').lower()
            short_name = country.get('short_name', '').lower()
            
            # البحث من أول حرف (startswith) أو في أي مكان (in)
            if country_name.startswith(query_text) or short_name.startswith(query_text) or query_text in country_name or query_text in short_name:
                matching_countries.append(country)
        
        # إضافة نتائج الدول
        for country in matching_countries[:10]:
            country_id = str(country.get('ID', country.get('id', '')))
            country_name = country.get('name', 'Unknown')
            short_name = country.get('short_name', country.get('code', ''))
            
            flag = get_country_flag(short_name)
            
            title = f"{flag} {country_name}"
            description = 'انقر لعرض الخدمات المتاحة' if language == 'ar' else 'Click to view available services'
            
            results.append(
                InlineQueryResultArticle(
                    id=f'country_{country_id}',
                    title=title,
                    description=description,
                    input_message_content=InputTextMessageContent(
                        f"{flag} **{country_name}**\n\n"
                        + ('جاري تحميل الخدمات المتاحة...' if language == 'ar' else 'Loading available services...'),
                        parse_mode='Markdown'
                    ),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            '📱 ' + ('عرض الخدمات' if language == 'ar' else 'View Services'),
                            callback_data=f'sp_country_{country_id}'
                        )
                    ]]),
                    thumbnail_url='https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Mobile_phone_icon.svg/120px-Mobile_phone_icon.svg.png'
                )
            )
        
        # البحث في الخدمات
        services = api.get_services()
        matching_services = []
        
        for service in services:
            service_name = service.get('name', '').lower()
            service_id = service.get('ID', service.get('id', ''))
            
            if query_text in service_name:
                matching_services.append(service)
        
        # إضافة نتائج الخدمات (السعر Live لدولة افتراضية US إن وجدت)
        margin = smspool_db.get_margin_percent()

        default_country_id = None
        default_country_code = None
        for c in countries:
            if str(c.get('short_name', '')).upper() == 'US':
                default_country_id = str(c.get('ID', c.get('id', '')))
                default_country_code = 'US'
                break

        if not default_country_id and countries:
            c = countries[0]
            default_country_id = str(c.get('ID', c.get('id', '')))
            default_country_code = str(c.get('short_name', c.get('code', ''))).upper()[:2]

        for service in matching_services[:10]:
            service_id = str(service.get('ID', service.get('id', '')))
            service_name = service.get('name', 'Unknown')

            icon = '📧'
            if 'whatsapp' in service_name.lower():
                icon = '💚'
            elif 'telegram' in service_name.lower():
                icon = '✈️'
            elif 'google' in service_name.lower():
                icon = '🔍'
            elif 'facebook' in service_name.lower():
                icon = '📘'

            title = f"{icon} {service_name}"

            price_info = None
            if default_country_id:
                price_info = api.get_service_price(service_id, default_country_id)

            if price_info and price_info.get('price') is not None:
                cost_price = float(price_info.get('price'))
                sale_price = round(cost_price * (1 + margin / 100), 2)
                description = f"{sale_price:.2f} " + ('كريديت' if language == 'ar' else 'credits')
                if default_country_code:
                    description += f" ({default_country_code})"

                if language == 'ar':
                    msg_text = (
                        f"{icon} **{service_name}**\n\n"
                        f"💰 السعر: {sale_price:.2f} كريديت ({default_country_code or ''})\n\n"
                        "💡 اختر دولة لعرض الخدمات المتاحة لها"
                    )
                else:
                    msg_text = (
                        f"{icon} **{service_name}**\n\n"
                        f"💰 Price: {sale_price:.2f} credits ({default_country_code or ''})\n\n"
                        "💡 Select a country to view available services"
                    )
            else:
                description = 'غير متاح' if language == 'ar' else 'Unavailable'
                if language == 'ar':
                    msg_text = (
                        f"{icon} **{service_name}**\n\n"
                        "❌ لا توجد بيانات سعر لهذا البحث حالياً\n\n"
                        "💡 اختر دولة لمتابعة الشراء"
                    )
                else:
                    msg_text = (
                        f"{icon} **{service_name}**\n\n"
                        "❌ No price data available right now\n\n"
                        "💡 Select a country to continue"
                    )

            results.append(
                InlineQueryResultArticle(
                    id=f'service_{service_id}',
                    title=title,
                    description=description,
                    input_message_content=InputTextMessageContent(
                        msg_text,
                        parse_mode='Markdown',
                    ),
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    '🌍 ' + ('اختيار الدولة' if language == 'ar' else 'Select Country'),
                                    callback_data=f'sp_service_select_{service_id}',
                                )
                            ]
                        ]
                    ),
                    thumbnail_url='https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Mobile_phone_icon.svg/120px-Mobile_phone_icon.svg.png',
                )
            )
        
        if not results:
            # لا توجد نتائج
            no_results_title = '❌ ' + ('لا توجد نتائج' if language == 'ar' else 'No results')
            no_results_desc = ('لم يتم العثور على تطابق' if language == 'ar' else 'No matches found')
            
            results = [
                InlineQueryResultArticle(
                    id='no_results',
                    title=no_results_title,
                    description=no_results_desc,
                    input_message_content=InputTextMessageContent(
                        f'❌ ' + ('لا توجد نتائج لـ' if language == 'ar' else 'No results for') + f' "{query_text}"\n\n'
                        + ('💡 جرب البحث عن: WhatsApp, Google, Telegram' if language == 'ar' else '💡 Try: WhatsApp, Google, Telegram')
                    )
                )
            ]
        
        await update.inline_query.answer(
            results,
            cache_time=60,
            is_personal=True
        )
        
        logger.info(f"تم إرسال {len(results)} نتيجة للمستخدم {user_id}")
    
    except Exception as e:
        logger.error(f"خطأ في معالجة SMSPool inline query: {e}")
        
        error_result = [
            InlineQueryResultArticle(
                id='error',
                title='❌ ' + ('حدث خطأ' if language == 'ar' else 'Error occurred'),
                description='يرجى المحاولة مرة أخرى' if language == 'ar' else 'Please try again',
                input_message_content=InputTextMessageContent(
                    f'❌ ' + ('حدث خطأ:' if language == 'ar' else 'Error:') + f' {str(e)}'
                )
            )
        ]
        await update.inline_query.answer(error_result, cache_time=10)
