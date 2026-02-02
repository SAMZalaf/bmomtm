#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SMSPool Service Module - Complete API Integration for SMS Verifications
وحدة SMSPool المدمجة للتعامل مع API خدمات التحقق عبر الرسائل

هذا الملف يحل محل خدمة NonVoip ويوفر:
- SMSPoolAPI: التعامل مع SMSPool API
- SMSPoolDB: إدارة قاعدة البيانات
- وظائف البوت: دوال الزبائن والآدمن
- معالجات Inline Query

API Endpoints Used:
- Balance: POST https://api.smspool.net/request/balance
- Services: GET https://api.smspool.net/service/retrieve_all
- Countries: GET https://api.smspool.net/country/retrieve_all
- Purchase SMS: POST https://api.smspool.net/purchase/sms
- Check SMS: POST https://api.smspool.net/sms/check
- Cancel SMS: POST https://api.smspool.net/sms/cancel
- Active Orders: POST https://api.smspool.net/request/active
- Resend SMS: POST https://api.smspool.net/sms/resend
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


PRODUCTS_CACHE = {
    'services': [],
    'countries': [],
    'last_update': 0,
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
        """
        جلب قائمة الخدمات المتاحة
        
        Returns:
            قائمة الخدمات مع IDs والأسماء
        """
        global PRODUCTS_CACHE
        
        if (time.time() - PRODUCTS_CACHE['last_update'] < PRODUCTS_CACHE['cache_duration'] 
            and PRODUCTS_CACHE['services']):
            return PRODUCTS_CACHE['services']
        
        result = self._api_request("service/retrieve_all", method="GET")
        
        if isinstance(result, list):
            PRODUCTS_CACHE['services'] = result
            PRODUCTS_CACHE['last_update'] = time.time()
            return result
        
        return []
    
    def get_countries(self) -> List[Dict]:
        """
        جلب قائمة الدول المتاحة
        
        Returns:
            قائمة الدول مع IDs والأسماء
        """
        global PRODUCTS_CACHE
        
        if (time.time() - PRODUCTS_CACHE['last_update'] < PRODUCTS_CACHE['cache_duration'] 
            and PRODUCTS_CACHE['countries']):
            return PRODUCTS_CACHE['countries']
        
        result = self._api_request("country/retrieve_all", method="GET")
        
        if isinstance(result, list):
            PRODUCTS_CACHE['countries'] = result
            PRODUCTS_CACHE['last_update'] = time.time()
            return result
        
        return []
    
    def get_service_price(self, service: str, country: str) -> Optional[Dict]:
        """
        جلب سعر خدمة معينة في دولة معينة
        
        Args:
            service: ID أو اسم الخدمة
            country: ID أو رمز الدولة
        
        Returns:
            معلومات السعر
        """
        result = self._api_request("request/price", data={
            'service': service,
            'country': country
        })
        return result if result.get('success', 0) != 0 else None
    
    def purchase_sms(self, country: str, service: str, 
                     pool: Optional[str] = None) -> Dict[str, Any]:
        """
        شراء رقم للتحقق SMS
        
        Args:
            country: ID الدولة
            service: ID الخدمة
            pool: اسم المجموعة (اختياري)
        
        Returns:
            {
                "success": 1,
                "number": "123456789",
                "order_id": "ABCDEFG",
                "country": "United States",
                "service": "Google",
                "pool": 5,
                "expires_in": 599
            }
        """
        data = {
            'country': country,
            'service': service
        }
        if pool:
            data['pool'] = pool
        
        result = self._api_request("purchase/sms", data=data)
        
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
        'menu_title': '📱 أرقام SMS',
        'menu_desc': 'احصل على رقم للتحقق عبر الرسائل',
        'buy_number': '🛒 شراء رقم',
        'my_numbers': '📋 أرقامي',
        'back': '🔙 رجوع',
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
        'back': '🔙 Back',
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
            callback_data="sp_my_orders"
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
        await show_countries_menu(update, context)
    
    elif data.startswith("sp_country_"):
        country_id = data.replace("sp_country_", "")
        context.user_data['sp_country'] = country_id
        await show_services_menu(update, context, country_id)
    
    elif data.startswith("sp_service_"):
        service_id = data.replace("sp_service_", "")
        country_id = context.user_data.get('sp_country', '1')
        await confirm_purchase(update, context, country_id, service_id)
    
    elif data.startswith("sp_confirm_"):
        parts = data.replace("sp_confirm_", "").split("_")
        country_id = parts[0]
        service_id = parts[1] if len(parts) > 1 else ""
        await process_purchase(update, context, country_id, service_id)
    
    elif data.startswith("sp_check_"):
        order_id = data.replace("sp_check_", "")
        await check_order_status(update, context, order_id)
    
    elif data.startswith("sp_cancel_"):
        order_id = data.replace("sp_cancel_", "")
        await cancel_order(update, context, order_id)
    
    elif data.startswith("sp_resend_"):
        order_id = data.replace("sp_resend_", "")
        await resend_sms(update, context, order_id)
    
    elif data == "sp_my_orders":
        await show_user_orders(update, context)


async def show_countries_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض قائمة الدول"""
    query = update.callback_query
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    api_key = smspool_db.get_api_key()
    if not api_key:
        await query.edit_message_text(get_smspool_message('service_disabled', language))
        return
    
    api = SMSPoolAPI(api_key)
    countries = api.get_countries()
    
    if not countries:
        await query.edit_message_text(get_smspool_message('error', language).format(message="No countries available"))
        return
    
    popular_countries = ['US', 'GB', 'CA', 'DE', 'FR', 'NL', 'RU', 'IN', 'PH', 'ID']
    
    keyboard = []
    for country in countries[:20]:
        country_id = country.get('ID', country.get('id', ''))
        country_name = country.get('name', '')
        short_name = country.get('short_name', '')
        
        flag = get_country_flag(short_name)
        btn_text = f"{flag} {country_name}"
        
        keyboard.append([InlineKeyboardButton(
            btn_text,
            callback_data=f"sp_country_{country_id}"
        )])
    
    keyboard.append([InlineKeyboardButton(
        get_smspool_message('back', language),
        callback_data="sp_main"
    )])
    
    title = get_smspool_message('select_country', language)
    await query.edit_message_text(
        f"<b>{title}</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def show_services_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                             country_id: str) -> None:
    """عرض قائمة الخدمات"""
    query = update.callback_query
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    api_key = smspool_db.get_api_key()
    api = SMSPoolAPI(api_key)
    services = api.get_services()
    
    if not services:
        await query.edit_message_text(get_smspool_message('error', language).format(message="No services available"))
        return
    
    popular_services = ['google', 'facebook', 'whatsapp', 'telegram', 'twitter', 
                       'instagram', 'tiktok', 'discord', 'amazon', 'uber']
    
    keyboard = []
    for service in services[:20]:
        service_id = service.get('ID', service.get('id', ''))
        service_name = service.get('name', '')
        
        keyboard.append([InlineKeyboardButton(
            f"📱 {service_name}",
            callback_data=f"sp_service_{service_id}"
        )])
    
    keyboard.append([InlineKeyboardButton(
        get_smspool_message('back', language),
        callback_data="sp_buy"
    )])
    
    title = get_smspool_message('select_service', language)
    await query.edit_message_text(
        f"<b>{title}</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def confirm_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE,
                          country_id: str, service_id: str) -> None:
    """تأكيد الشراء"""
    query = update.callback_query
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    balance = get_user_balance(user_id)
    
    api_key = smspool_db.get_api_key()
    api = SMSPoolAPI(api_key)
    
    price_info = api.get_service_price(service_id, country_id)
    cost_price = float(price_info.get('price', 0.5)) if price_info else 0.5
    
    margin = smspool_db.get_margin_percent()
    sale_price = round(cost_price * (1 + margin/100), 2)
    
    if balance < sale_price:
        await query.edit_message_text(
            get_smspool_message('insufficient_balance', language).format(
                balance=balance,
                required=sale_price
            )
        )
        return
    
    context.user_data['sp_cost_price'] = cost_price
    context.user_data['sp_sale_price'] = sale_price
    
    if language == 'ar':
        text = f"""
💰 <b>تأكيد الشراء</b>

💵 السعر: <code>{sale_price}</code> كريديت
💳 رصيدك: <code>{balance}</code> كريديت

هل تريد المتابعة؟
"""
    else:
        text = f"""
💰 <b>Confirm Purchase</b>

💵 Price: <code>{sale_price}</code> credits
💳 Your balance: <code>{balance}</code> credits

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


async def process_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE,
                          country_id: str, service_id: str) -> None:
    """معالجة الشراء"""
    query = update.callback_query
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    cost_price = context.user_data.get('sp_cost_price', 0.5)
    sale_price = context.user_data.get('sp_sale_price', 0.5)
    
    balance = get_user_balance(user_id)
    if balance < sale_price:
        await query.edit_message_text(
            get_smspool_message('insufficient_balance', language).format(
                balance=balance,
                required=sale_price
            )
        )
        return
    
    api_key = smspool_db.get_api_key()
    api = SMSPoolAPI(api_key)
    
    result = api.purchase_sms(country_id, service_id)
    
    if result.get('status') == 'success':
        update_user_balance(user_id, sale_price, 'subtract')
        
        order_id = result.get('order_id')
        number = result.get('number')
        country = result.get('country', '')
        service = result.get('service', '')
        pool = result.get('pool', '')
        expires_in = result.get('expires_in', 600)
        
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
        
        context.job_queue.run_repeating(
            check_sms_job,
            interval=10,
            first=5,
            data={'order_id': order_id, 'user_id': user_id, 'chat_id': query.message.chat_id},
            name=f"sms_check_{order_id}"
        )
    else:
        error_msg = result.get('message', 'Purchase failed')
        await query.edit_message_text(
            get_smspool_message('error', language).format(message=error_msg)
        )


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
    
    api_key = smspool_db.get_api_key()
    enabled = smspool_db.is_enabled()
    margin = smspool_db.get_margin_percent()
    
    balance_info = "❓ غير متصل"
    if api_key:
        api = SMSPoolAPI(api_key)
        result = api.get_balance()
        if result.get('status') == 'success':
            balance_info = f"💰 ${result.get('balance', '0.00')}"
    
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
    
    if len(api_key) == 32:
        api = SMSPoolAPI(api_key)
        result = api.get_balance()
        
        if result.get('status') == 'success':
            smspool_db.set_api_key(api_key)
            await update.message.reply_text(
                f"✅ تم حفظ مفتاح API بنجاح!\n💰 الرصيد: ${result.get('balance', '0.00')}"
            )
        else:
            await update.message.reply_text("❌ مفتاح API غير صحيح!")
    else:
        await update.message.reply_text("❌ مفتاح API يجب أن يكون 32 حرفاً!")
    
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
