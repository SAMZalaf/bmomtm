#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================
خدمة 9Proxy - Daily SOCKS Proxy Service
============================================
هذا الملف يجمع جميع وظائف خدمة 9Proxy في مكان واحد:
- NineProxyAPI: التعامل مع API
- NineProxyDB: إدارة قاعدة البيانات
- وظائف البوت: دوال الزبائن والآدمن
- معالجات Inline Query للبحث
============================================
"""

import os
import time
import logging
import sqlite3
import asyncio
import requests
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple, Union

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent
)
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)

API_BASE = "https://api.9proxy.com"
DATABASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "proxy_bot.db")

PRODUCTS_CACHE = {
    'countries': [],
    'states': {},
    'cities': {},
    'today_list': [],
    'last_update': 0,
    'cache_duration': 300
}

ERROR_CODES_9PROXY = {
    'x0x0000': 'رصيد الحساب غير كافٍ لإتمام العملية',
    'x0x0001': 'البروكسي المطلوب غير متوفر حالياً',
    'x0x0002': 'خطأ في الاتصال بالخدمة',
    'x0x0003': 'تم رفض الطلب',
    'x0x0004': 'انتهت مهلة الاتصال',
    'x0x0005': 'معلومات الحساب غير صحيحة',
    'x0x0006': 'تم تجاوز حد الطلبات المسموح',
    'x0x0007': 'البروكسي غير موجود',
    'x0x0008': 'فشل في فحص البروكسي',
    'x0x0009': 'خطأ غير متوقع',
    'x0x000A': 'الخدمة متوقفة مؤقتاً'
}


def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE, timeout=10.0)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def log_api_error_9proxy(error_code: str, actual_error: str, context: str = ""):
    logger.error(f"[9Proxy {error_code}] {ERROR_CODES_9PROXY.get(error_code, 'خطأ غير معروف')} | الخطأ الفعلي: {actual_error} | السياق: {context}")


def get_error_code_from_message_9proxy(error_message: str) -> str:
    error_lower = str(error_message).lower()
    
    if 'balance' in error_lower or 'insufficient' in error_lower or '402' in error_lower:
        return 'x0x0000'
    elif 'not available' in error_lower or 'out of stock' in error_lower:
        return 'x0x0001'
    elif 'connection' in error_lower or 'network' in error_lower:
        return 'x0x0002'
    elif 'rejected' in error_lower or 'denied' in error_lower:
        return 'x0x0003'
    elif 'timeout' in error_lower or 'timed out' in error_lower:
        return 'x0x0004'
    elif 'auth' in error_lower or 'login' in error_lower or '401' in error_lower:
        return 'x0x0005'
    elif 'rate limit' in error_lower or 'too many' in error_lower or '429' in error_lower:
        return 'x0x0006'
    elif 'not found' in error_lower or '404' in error_lower:
        return 'x0x0007'
    else:
        return 'x0x0009'


class NineProxyAPI:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._get_api_key_from_db()
        self.base_url = API_BASE
        self.session = requests.Session()
        
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })
    
    def _get_api_key_from_db(self) -> Optional[str]:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT setting_value FROM nineproxy_settings WHERE setting_key = 'nineproxy_api_key'")
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else None
        except:
            return None
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 402:
                log_api_error_9proxy('x0x0000', 'Insufficient balance', endpoint)
                return {"error": True, "message": "رصيد غير كافٍ", "error_code": "x0x0000"}
            
            if response.status_code == 429:
                log_api_error_9proxy('x0x0006', 'Rate limit exceeded', endpoint)
                return {"error": True, "message": "تجاوز حد الطلبات", "error_code": "x0x0006"}
            
            response.raise_for_status()
            return response.json()
            
        except requests.Timeout:
            log_api_error_9proxy('x0x0004', 'Request timeout', endpoint)
            return {"error": True, "message": "انتهت مهلة الطلب", "error_code": "x0x0004"}
        except requests.RequestException as e:
            error_code = get_error_code_from_message_9proxy(str(e))
            log_api_error_9proxy(error_code, str(e), endpoint)
            return {"error": True, "message": str(e), "error_code": error_code}
    
    def get_random_proxies(
        self,
        num: int = 1,
        country: Optional[str] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        today: bool = False
    ) -> Dict:
        params = {'t': 2, 'num': num}
        
        if country:
            params['country'] = country
        if state:
            params['state'] = state
        if city:
            params['city'] = city
        if today:
            params['today'] = 'true'
        
        return self._make_request('/api/proxy', params)
    
    def get_today_list(
        self,
        country: Optional[str] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        limit: int = 100
    ) -> Dict:
        params = {'t': 2, 'limit': limit}
        
        if country:
            params['country'] = country
        if state:
            params['state'] = state
        if city:
            params['city'] = city
        
        return self._make_request('/api/today_list', params)
    
    def forward_request(self, proxy_id: str, port: str, plan: str = "1") -> Dict:
        params = {
            'id': proxy_id,
            'port': port,
            'plan': plan,
            't': 2
        }
        return self._make_request('/api/forward', params)
    
    def check_port_status(self, ports: Union[str, List[int]] = "all") -> Dict:
        params = {'t': 2}
        
        if isinstance(ports, list):
            params['ports'] = ','.join(map(str, ports))
        else:
            params['ports'] = str(ports)
        
        return self._make_request('/api/port_check', params)
    
    def get_port_status(self) -> Dict:
        return self._make_request('/api/port_status', {'t': 2})


class NineProxyDB:
    def __init__(self, db_file: str = DATABASE_FILE):
        self.db_file = db_file
        self._init_tables()
    
    def _get_connection(self):
        return get_db_connection()
    
    def _init_tables(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nineproxy_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                proxy_id TEXT,
                proxy_ip TEXT,
                proxy_port TEXT,
                proxy_username TEXT,
                proxy_password TEXT,
                country_code TEXT,
                country_name TEXT,
                state TEXT,
                city TEXT,
                is_online BOOLEAN DEFAULT 1,
                cost_price REAL DEFAULT 0.0,
                sale_price REAL DEFAULT 0.0,
                status TEXT DEFAULT 'active',
                expires_at TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_nineproxy_user_id
            ON nineproxy_orders(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_nineproxy_status
            ON nineproxy_orders(status)
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nineproxy_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT NOT NULL UNIQUE,
                setting_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            INSERT OR IGNORE INTO nineproxy_settings (setting_key, setting_value)
            VALUES ('margin_percent', '20.0')
        """)
        
        cursor.execute("""
            INSERT OR IGNORE INTO nineproxy_settings (setting_key, setting_value)
            VALUES ('service_enabled', 'true')
        """)
        
        cursor.execute("""
            INSERT OR IGNORE INTO nineproxy_settings (setting_key, setting_value)
            VALUES ('base_price', '0.05')
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nineproxy_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stat_date DATE NOT NULL,
                stat_type TEXT NOT NULL,
                orders_count INTEGER DEFAULT 0,
                total_revenue REAL DEFAULT 0.0,
                total_cost REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(stat_date, stat_type)
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("✅ تم تهيئة جداول 9Proxy")
    
    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT setting_value FROM nineproxy_settings WHERE setting_key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else default
    
    def set_setting(self, key: str, value: str):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO nineproxy_settings (setting_key, setting_value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (key, value))
        conn.commit()
        conn.close()
    
    def is_service_enabled(self) -> bool:
        return self.get_setting('service_enabled', 'true').lower() == 'true'
    
    def get_margin_percent(self) -> float:
        try:
            return float(self.get_setting('margin_percent', '20.0'))
        except:
            return 20.0
    
    def get_base_price(self) -> float:
        try:
            return float(self.get_setting('base_price', '0.05'))
        except:
            return 0.05
    
    def calculate_sale_price(self, cost_price: float = None) -> float:
        if cost_price is None:
            cost_price = self.get_base_price()
        margin = self.get_margin_percent()
        return round(cost_price * (1 + margin / 100), 2)
    
    def save_order(self, user_id: int, proxy_data: Dict, cost_price: float, sale_price: float) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        expires_at = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute("""
            INSERT INTO nineproxy_orders
            (user_id, proxy_id, proxy_ip, proxy_port, proxy_username, proxy_password,
             country_code, country_name, state, city, is_online, cost_price, sale_price, status, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
        """, (
            user_id,
            proxy_data.get('id', ''),
            proxy_data.get('ip', ''),
            proxy_data.get('port', ''),
            proxy_data.get('username', ''),
            proxy_data.get('password', ''),
            proxy_data.get('country_code', ''),
            proxy_data.get('country_name', ''),
            proxy_data.get('state', ''),
            proxy_data.get('city', ''),
            proxy_data.get('is_online', True),
            cost_price,
            sale_price,
            expires_at
        ))
        
        order_id = cursor.lastrowid
        
        today = datetime.now().strftime('%Y-%m-%d')
        for stat_type in ['daily', 'total']:
            cursor.execute("""
                INSERT OR REPLACE INTO nineproxy_statistics
                (stat_date, stat_type, orders_count, total_revenue, total_cost)
                VALUES (
                    ?, ?,
                    COALESCE((SELECT orders_count FROM nineproxy_statistics WHERE stat_date = ? AND stat_type = ?), 0) + 1,
                    COALESCE((SELECT total_revenue FROM nineproxy_statistics WHERE stat_date = ? AND stat_type = ?), 0) + ?,
                    COALESCE((SELECT total_cost FROM nineproxy_statistics WHERE stat_date = ? AND stat_type = ?), 0) + ?
                )
            """, (today, stat_type, today, stat_type, today, stat_type, sale_price, today, stat_type, cost_price))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ تم حفظ طلب 9Proxy #{order_id} للمستخدم {user_id}")
        return order_id
    
    def get_user_active_proxies(self, user_id: int) -> List[Dict]:
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM nineproxy_orders
            WHERE user_id = ? AND status = 'active'
            AND datetime(expires_at) > datetime('now')
            ORDER BY created_at DESC
        """, (user_id,))
        
        proxies = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return proxies
    
    def get_proxy_by_id(self, order_id: int, user_id: int = None) -> Optional[Dict]:
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute("SELECT * FROM nineproxy_orders WHERE id = ? AND user_id = ?", (order_id, user_id))
        else:
            cursor.execute("SELECT * FROM nineproxy_orders WHERE id = ?", (order_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return dict(result) if result else None
    
    def update_proxy_status(self, order_id: int, is_online: bool):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE nineproxy_orders
            SET is_online = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (is_online, order_id))
        conn.commit()
        conn.close()
    
    def expire_old_proxies(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE nineproxy_orders
            SET status = 'expired', updated_at = CURRENT_TIMESTAMP
            WHERE status = 'active' AND datetime(expires_at) < datetime('now')
        """)
        expired_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        if expired_count > 0:
            logger.info(f"🕐 تم تحديث {expired_count} بروكسي منتهي الصلاحية")
        
        return expired_count
    
    def get_statistics(self) -> Dict:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute("""
            SELECT orders_count, total_revenue, total_cost
            FROM nineproxy_statistics
            WHERE stat_date = ? AND stat_type = 'daily'
        """, (today,))
        daily = cursor.fetchone()
        
        cursor.execute("""
            SELECT SUM(orders_count), SUM(total_revenue), SUM(total_cost)
            FROM nineproxy_statistics
            WHERE stat_type = 'total'
        """)
        total = cursor.fetchone()
        
        conn.close()
        
        return {
            'daily': {
                'orders': daily[0] if daily else 0,
                'revenue': daily[1] if daily else 0.0,
                'cost': daily[2] if daily else 0.0
            },
            'total': {
                'orders': total[0] if total else 0,
                'revenue': total[1] if total else 0.0,
                'cost': total[2] if total else 0.0
            }
        }


def get_user_language(user_id: int) -> str:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result and result[0] else 'ar'
    except:
        return 'ar'


def get_user_balance(user_id: int) -> float:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return float(result[0]) if result and result[0] else 0.0
    except:
        return 0.0


def deduct_user_balance(user_id: int, amount: float) -> bool:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET balance = balance - ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND balance >= ?
        """, (amount, user_id, amount))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    except:
        return False


NINEPROXY_MESSAGES = {
    'ar': {
        'menu_title': '🌐 سوكس يومي',
        'menu_desc': 'احصل على بروكسي SOCKS5 يومي عالي الجودة',
        'buy_proxy': '🛒 شراء بروكسي',
        'my_proxies': '📋 بروكسياتي الحالية',
        'back': '🔙 رجوع',
        'select_country': '🌍 تحديد الدولة',
        'today_proxies': '🆕 بروكسي مضاف اليوم',
        'random_proxy': '🎲 بروكسي عشوائي',
        'select_state': '📍 اختر الولاية:',
        'select_city': '🏙️ اختر المدينة:',
        'search_placeholder': '🔍 ابحث...',
        'confirm_purchase': '✅ تأكيد الشراء',
        'cancel': '❌ إلغاء',
        'purchase_confirm_msg': '''
💰 <b>تأكيد الشراء</b>

🌍 الدولة: {country}
📍 الولاية: {state}
🏙️ المدينة: {city}

💵 السعر: <code>{price}</code> كريديت
💳 رصيدك: <code>{balance}</code> كريديت

هل تريد المتابعة؟
''',
        'purchase_success': '''
✅ <b>تم الشراء بنجاح!</b>

🌐 <b>بيانات البروكسي:</b>
━━━━━━━━━━━━━━━
🔹 IP: <code>{ip}</code>
🔹 Port: <code>{port}</code>
🔹 Username: <code>{username}</code>
🔹 Password: <code>{password}</code>
━━━━━━━━━━━━━━━

🌍 الدولة: {country}
📍 الموقع: {location}
⏰ ينتهي خلال: 24 ساعة

💡 استخدم زر "فحص" للتحقق من حالة البروكسي
''',
        'insufficient_balance': '❌ رصيدك غير كافٍ!\n\n💳 رصيدك الحالي: {balance} كريديت\n💵 المبلغ المطلوب: {required} كريديت\n\n⚠️ رمز الخطأ: x0x0000',
        'no_proxies': '📭 لا توجد لديك بروكسيات نشطة حالياً',
        'proxy_expired': '⏰ انتهت صلاحية هذا البروكسي',
        'check_status': '🔍 فحص',
        'proxy_online': '✅ البروكسي يعمل\n🌍 الدولة: {country}',
        'proxy_offline': '❌ البروكسي لا يعمل حالياً',
        'service_disabled': '⚠️ هذه الخدمة متوقفة مؤقتاً\n\nرمز الخطأ: x0x000A',
        'error_occurred': '❌ حدث خطأ\n\nرمز الخطأ: {code}',
        'no_results': '😔 لا توجد نتائج متاحة',
        'loading': '⏳ جاري التحميل...'
    },
    'en': {
        'menu_title': '🌐 Daily SOCKS',
        'menu_desc': 'Get high-quality daily SOCKS5 proxy',
        'buy_proxy': '🛒 Buy Proxy',
        'my_proxies': '📋 My Proxies',
        'back': '🔙 Back',
        'select_country': '🌍 Select Country',
        'today_proxies': '🆕 Added Today',
        'random_proxy': '🎲 Random Proxy',
        'select_state': '📍 Select State:',
        'select_city': '🏙️ Select City:',
        'search_placeholder': '🔍 Search...',
        'confirm_purchase': '✅ Confirm Purchase',
        'cancel': '❌ Cancel',
        'purchase_confirm_msg': '''
💰 <b>Confirm Purchase</b>

🌍 Country: {country}
📍 State: {state}
🏙️ City: {city}

💵 Price: <code>{price}</code> credits
💳 Your balance: <code>{balance}</code> credits

Do you want to proceed?
''',
        'purchase_success': '''
✅ <b>Purchase Successful!</b>

🌐 <b>Proxy Details:</b>
━━━━━━━━━━━━━━━
🔹 IP: <code>{ip}</code>
🔹 Port: <code>{port}</code>
🔹 Username: <code>{username}</code>
🔹 Password: <code>{password}</code>
━━━━━━━━━━━━━━━

🌍 Country: {country}
📍 Location: {location}
⏰ Expires in: 24 hours

💡 Use "Check" button to verify proxy status
''',
        'insufficient_balance': '❌ Insufficient balance!\n\n💳 Your balance: {balance} credits\n💵 Required: {required} credits\n\n⚠️ Error code: x0x0000',
        'no_proxies': '📭 You have no active proxies',
        'proxy_expired': '⏰ This proxy has expired',
        'check_status': '🔍 Check',
        'proxy_online': '✅ Proxy is working\n🌍 Country: {country}',
        'proxy_offline': '❌ Proxy is currently offline',
        'service_disabled': '⚠️ This service is temporarily disabled\n\nError code: x0x000A',
        'error_occurred': '❌ An error occurred\n\nError code: {code}',
        'no_results': '😔 No results available',
        'loading': '⏳ Loading...'
    }
}


def get_message(key: str, language: str = 'ar') -> str:
    return NINEPROXY_MESSAGES.get(language, NINEPROXY_MESSAGES['ar']).get(key, key)


nineproxy_db = NineProxyDB()


async def nineproxy_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    if not nineproxy_db.is_service_enabled():
        await update.message.reply_text(get_message('service_disabled', language))
        return
    
    keyboard = [
        [InlineKeyboardButton(get_message('buy_proxy', language), callback_data="9proxy_buy_menu")],
        [InlineKeyboardButton(get_message('my_proxies', language), callback_data="9proxy_my_proxies")],
        [InlineKeyboardButton(get_message('back', language), callback_data="9proxy_back_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"<b>{get_message('menu_title', language)}</b>\n\n{get_message('menu_desc', language)}",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )


async def handle_9proxy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    data = query.data
    
    if not nineproxy_db.is_service_enabled() and not data.startswith("9proxy_admin"):
        await query.edit_message_text(get_message('service_disabled', language))
        return
    
    if data == "9proxy_buy_menu":
        await show_buy_menu(query, language)
    
    elif data == "9proxy_my_proxies":
        await show_my_proxies(query, user_id, language)
    
    elif data == "9proxy_select_country":
        await show_country_selection(query, language, context)
    
    elif data == "9proxy_today":
        await show_today_proxies(query, language, context)
    
    elif data == "9proxy_random":
        await confirm_random_purchase(query, user_id, language, context)
    
    elif data.startswith("9proxy_country_"):
        country_code = data.replace("9proxy_country_", "")
        await show_state_selection(query, country_code, language, context)
    
    elif data.startswith("9proxy_state_"):
        parts = data.replace("9proxy_state_", "").split("_")
        country_code = parts[0]
        state = "_".join(parts[1:])
        await show_city_selection(query, country_code, state, language, context)
    
    elif data.startswith("9proxy_city_"):
        parts = data.replace("9proxy_city_", "").split("_")
        country_code = parts[0]
        state = parts[1]
        city = "_".join(parts[2:])
        await confirm_purchase(query, user_id, language, country_code, state, city, context)
    
    elif data.startswith("9proxy_confirm_"):
        await execute_purchase(query, user_id, language, context)
    
    elif data.startswith("9proxy_check_"):
        order_id = int(data.replace("9proxy_check_", ""))
        await check_proxy_status(query, user_id, order_id, language)
    
    elif data.startswith("9proxy_view_"):
        order_id = int(data.replace("9proxy_view_", ""))
        await view_proxy_details(query, user_id, order_id, language)
    
    elif data == "9proxy_back_main":
        from bot_keyboards import create_main_user_keyboard
        await query.delete_message()
        await context.bot.send_message(
            chat_id=user_id,
            text="🏠",
            reply_markup=create_main_user_keyboard(language)
        )
    
    elif data == "9proxy_back_menu":
        await show_main_menu_inline(query, language)
    
    elif data == "9proxy_cancel":
        await show_main_menu_inline(query, language)


async def show_main_menu_inline(query, language: str):
    keyboard = [
        [InlineKeyboardButton(get_message('buy_proxy', language), callback_data="9proxy_buy_menu")],
        [InlineKeyboardButton(get_message('my_proxies', language), callback_data="9proxy_my_proxies")],
        [InlineKeyboardButton(get_message('back', language), callback_data="9proxy_back_main")]
    ]
    
    await query.edit_message_text(
        f"<b>{get_message('menu_title', language)}</b>\n\n{get_message('menu_desc', language)}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


async def show_buy_menu(query, language: str):
    keyboard = [
        [InlineKeyboardButton(get_message('select_country', language), callback_data="9proxy_select_country")],
        [InlineKeyboardButton(get_message('today_proxies', language), callback_data="9proxy_today")],
        [InlineKeyboardButton(get_message('random_proxy', language), callback_data="9proxy_random")],
        [InlineKeyboardButton(get_message('back', language), callback_data="9proxy_back_menu")]
    ]
    
    await query.edit_message_text(
        f"<b>{get_message('buy_proxy', language)}</b>\n\n{get_message('menu_desc', language)}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


async def show_country_selection(query, language: str, context: ContextTypes.DEFAULT_TYPE):
    api = NineProxyAPI()
    result = api.get_today_list(limit=500)
    
    if result.get('error'):
        await query.edit_message_text(
            get_message('error_occurred', language).format(code=result.get('error_code', 'x0x0009'))
        )
        return
    
    countries = {}
    for proxy in result.get('data', []):
        code = proxy.get('country_code', 'XX')
        if code not in countries:
            countries[code] = 0
        countries[code] += 1
    
    keyboard = []
    sorted_countries = sorted(countries.items(), key=lambda x: x[1], reverse=True)
    
    row = []
    for code, count in sorted_countries[:20]:
        flag = get_country_flag(code)
        row.append(InlineKeyboardButton(f"{flag} {code} ({count})", callback_data=f"9proxy_country_{code}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton(get_message('back', language), callback_data="9proxy_buy_menu")])
    
    await query.edit_message_text(
        get_message('select_country', language) if language == 'en' else '🌍 اختر الدولة:',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_state_selection(query, country_code: str, language: str, context: ContextTypes.DEFAULT_TYPE):
    api = NineProxyAPI()
    result = api.get_today_list(country=country_code, limit=500)
    
    if result.get('error'):
        await query.edit_message_text(
            get_message('error_occurred', language).format(code=result.get('error_code', 'x0x0009'))
        )
        return
    
    states = {}
    for proxy in result.get('data', []):
        state = proxy.get('state', 'Unknown')
        if state and state not in states:
            states[state] = 0
        if state:
            states[state] += 1
    
    if not states:
        await query.edit_message_text(get_message('no_results', language))
        return
    
    keyboard = []
    sorted_states = sorted(states.items(), key=lambda x: x[1], reverse=True)
    
    for state, count in sorted_states[:15]:
        keyboard.append([InlineKeyboardButton(f"📍 {state} ({count})", callback_data=f"9proxy_state_{country_code}_{state}")])
    
    keyboard.append([InlineKeyboardButton(get_message('back', language), callback_data="9proxy_select_country")])
    
    await query.edit_message_text(
        get_message('select_state', language),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_city_selection(query, country_code: str, state: str, language: str, context: ContextTypes.DEFAULT_TYPE):
    api = NineProxyAPI()
    result = api.get_today_list(country=country_code, state=state, limit=200)
    
    if result.get('error'):
        await query.edit_message_text(
            get_message('error_occurred', language).format(code=result.get('error_code', 'x0x0009'))
        )
        return
    
    cities = {}
    for proxy in result.get('data', []):
        city = proxy.get('city', 'Unknown')
        if city and city not in cities:
            cities[city] = 0
        if city:
            cities[city] += 1
    
    if not cities:
        await query.edit_message_text(get_message('no_results', language))
        return
    
    keyboard = []
    sorted_cities = sorted(cities.items(), key=lambda x: x[1], reverse=True)
    
    for city, count in sorted_cities[:15]:
        keyboard.append([InlineKeyboardButton(f"🏙️ {city} ({count})", callback_data=f"9proxy_city_{country_code}_{state}_{city}")])
    
    keyboard.append([InlineKeyboardButton(get_message('back', language), callback_data=f"9proxy_country_{country_code}")])
    
    await query.edit_message_text(
        get_message('select_city', language),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_today_proxies(query, language: str, context: ContextTypes.DEFAULT_TYPE):
    await show_country_selection(query, language, context)


async def confirm_random_purchase(query, user_id: int, language: str, context: ContextTypes.DEFAULT_TYPE):
    balance = get_user_balance(user_id)
    sale_price = nineproxy_db.calculate_sale_price()
    
    if balance < sale_price:
        await query.edit_message_text(
            get_message('insufficient_balance', language).format(balance=balance, required=sale_price),
            parse_mode=ParseMode.HTML
        )
        return
    
    context.user_data['9proxy_purchase'] = {
        'type': 'random',
        'country': 'Random',
        'state': 'Random',
        'city': 'Random'
    }
    
    keyboard = [
        [InlineKeyboardButton(get_message('confirm_purchase', language), callback_data="9proxy_confirm_random")],
        [InlineKeyboardButton(get_message('cancel', language), callback_data="9proxy_buy_menu")]
    ]
    
    msg = get_message('purchase_confirm_msg', language).format(
        country='🎲 عشوائي' if language == 'ar' else '🎲 Random',
        state='-',
        city='-',
        price=sale_price,
        balance=balance
    )
    
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)


async def confirm_purchase(query, user_id: int, language: str, country: str, state: str, city: str, context: ContextTypes.DEFAULT_TYPE):
    balance = get_user_balance(user_id)
    sale_price = nineproxy_db.calculate_sale_price()
    
    if balance < sale_price:
        await query.edit_message_text(
            get_message('insufficient_balance', language).format(balance=balance, required=sale_price),
            parse_mode=ParseMode.HTML
        )
        return
    
    context.user_data['9proxy_purchase'] = {
        'type': 'specific',
        'country': country,
        'state': state,
        'city': city
    }
    
    keyboard = [
        [InlineKeyboardButton(get_message('confirm_purchase', language), callback_data="9proxy_confirm_specific")],
        [InlineKeyboardButton(get_message('cancel', language), callback_data="9proxy_buy_menu")]
    ]
    
    flag = get_country_flag(country)
    msg = get_message('purchase_confirm_msg', language).format(
        country=f"{flag} {country}",
        state=state,
        city=city,
        price=sale_price,
        balance=balance
    )
    
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)


async def execute_purchase(query, user_id: int, language: str, context: ContextTypes.DEFAULT_TYPE):
    purchase_data = context.user_data.get('9proxy_purchase', {})
    
    if not purchase_data:
        await query.edit_message_text(get_message('error_occurred', language).format(code='x0x0009'))
        return
    
    sale_price = nineproxy_db.calculate_sale_price()
    cost_price = nineproxy_db.get_base_price()
    
    if not deduct_user_balance(user_id, sale_price):
        balance = get_user_balance(user_id)
        await query.edit_message_text(
            get_message('insufficient_balance', language).format(balance=balance, required=sale_price),
            parse_mode=ParseMode.HTML
        )
        return
    
    await query.edit_message_text(get_message('loading', language))
    
    api = NineProxyAPI()
    
    if purchase_data.get('type') == 'random':
        result = api.get_random_proxies(num=1, today=True)
    else:
        result = api.get_random_proxies(
            num=1,
            country=purchase_data.get('country'),
            state=purchase_data.get('state'),
            city=purchase_data.get('city')
        )
    
    if result.get('error'):
        refund_user_balance(user_id, sale_price)
        await query.edit_message_text(
            get_message('error_occurred', language).format(code=result.get('error_code', 'x0x0009'))
        )
        return
    
    proxy_list = result.get('data', [])
    if not proxy_list:
        refund_user_balance(user_id, sale_price)
        await query.edit_message_text(get_message('no_results', language))
        return
    
    proxy_str = proxy_list[0] if isinstance(proxy_list[0], str) else str(proxy_list[0])
    parts = proxy_str.split(':')
    
    proxy_data = {
        'ip': parts[0] if len(parts) > 0 else '',
        'port': parts[1] if len(parts) > 1 else '',
        'username': parts[2] if len(parts) > 2 else '',
        'password': parts[3] if len(parts) > 3 else '',
        'country_code': purchase_data.get('country', 'XX'),
        'country_name': purchase_data.get('country', 'Unknown'),
        'state': purchase_data.get('state', ''),
        'city': purchase_data.get('city', ''),
        'is_online': True
    }
    
    order_id = nineproxy_db.save_order(user_id, proxy_data, cost_price, sale_price)
    
    context.user_data.pop('9proxy_purchase', None)
    
    location = f"{proxy_data['state']}, {proxy_data['city']}" if proxy_data['state'] else proxy_data['city']
    flag = get_country_flag(proxy_data['country_code'])
    
    keyboard = [
        [InlineKeyboardButton(get_message('check_status', language), callback_data=f"9proxy_check_{order_id}")],
        [InlineKeyboardButton(get_message('my_proxies', language), callback_data="9proxy_my_proxies")],
        [InlineKeyboardButton(get_message('back', language), callback_data="9proxy_back_menu")]
    ]
    
    msg = get_message('purchase_success', language).format(
        ip=proxy_data['ip'],
        port=proxy_data['port'],
        username=proxy_data['username'],
        password=proxy_data['password'],
        country=f"{flag} {proxy_data['country_name']}",
        location=location or '-'
    )
    
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)


def refund_user_balance(user_id: int, amount: float):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET balance = balance + ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (amount, user_id))
        conn.commit()
        conn.close()
        logger.info(f"💰 تم استرداد {amount} كريديت للمستخدم {user_id}")
    except Exception as e:
        logger.error(f"❌ خطأ في استرداد الرصيد: {e}")


async def show_my_proxies(query, user_id: int, language: str):
    nineproxy_db.expire_old_proxies()
    
    proxies = nineproxy_db.get_user_active_proxies(user_id)
    
    if not proxies:
        keyboard = [[InlineKeyboardButton(get_message('back', language), callback_data="9proxy_back_menu")]]
        await query.edit_message_text(
            get_message('no_proxies', language),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    keyboard = []
    for proxy in proxies[:10]:
        flag = get_country_flag(proxy.get('country_code', 'XX'))
        status = "🟢" if proxy.get('is_online') else "🔴"
        btn_text = f"{status} {flag} {proxy['proxy_ip']}:{proxy['proxy_port']}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"9proxy_view_{proxy['id']}")])
    
    keyboard.append([InlineKeyboardButton(get_message('back', language), callback_data="9proxy_back_menu")])
    
    await query.edit_message_text(
        f"<b>{get_message('my_proxies', language)}</b>\n\n{'اختر بروكسي لعرض التفاصيل' if language == 'ar' else 'Select a proxy to view details'}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


async def view_proxy_details(query, user_id: int, order_id: int, language: str):
    proxy = nineproxy_db.get_proxy_by_id(order_id, user_id)
    
    if not proxy:
        await query.edit_message_text(get_message('error_occurred', language).format(code='x0x0007'))
        return
    
    if proxy.get('status') == 'expired':
        await query.edit_message_text(get_message('proxy_expired', language))
        return
    
    flag = get_country_flag(proxy.get('country_code', 'XX'))
    location = f"{proxy.get('state', '')}, {proxy.get('city', '')}" if proxy.get('state') else proxy.get('city', '-')
    
    msg = f'''
🌐 <b>بيانات البروكسي</b>
━━━━━━━━━━━━━━━
🔹 IP: <code>{proxy['proxy_ip']}</code>
🔹 Port: <code>{proxy['proxy_port']}</code>
🔹 Username: <code>{proxy['proxy_username']}</code>
🔹 Password: <code>{proxy['proxy_password']}</code>
━━━━━━━━━━━━━━━

🌍 الدولة: {flag} {proxy.get('country_name', proxy.get('country_code', 'Unknown'))}
📍 الموقع: {location}
⏰ ينتهي في: {proxy.get('expires_at', '-')}
'''
    
    keyboard = [
        [InlineKeyboardButton(get_message('check_status', language), callback_data=f"9proxy_check_{order_id}")],
        [InlineKeyboardButton(get_message('back', language), callback_data="9proxy_my_proxies")]
    ]
    
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)


async def check_proxy_status(query, user_id: int, order_id: int, language: str):
    proxy = nineproxy_db.get_proxy_by_id(order_id, user_id)
    
    if not proxy:
        await query.answer(get_message('error_occurred', language).format(code='x0x0007'), show_alert=True)
        return
    
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((proxy['proxy_ip'], int(proxy['proxy_port'])))
        sock.close()
        
        is_online = result == 0
        nineproxy_db.update_proxy_status(order_id, is_online)
        
        flag = get_country_flag(proxy.get('country_code', 'XX'))
        country_name = proxy.get('country_name', proxy.get('country_code', 'Unknown'))
        
        if is_online:
            await query.answer(
                get_message('proxy_online', language).format(country=f"{flag} {country_name}"),
                show_alert=True
            )
        else:
            await query.answer(get_message('proxy_offline', language), show_alert=True)
    
    except Exception as e:
        logger.error(f"خطأ في فحص البروكسي: {e}")
        await query.answer(get_message('error_occurred', language).format(code='x0x0008'), show_alert=True)


def get_country_flag(country_code: str) -> str:
    flags = {
        'US': '🇺🇸', 'GB': '🇬🇧', 'UK': '🇬🇧', 'DE': '🇩🇪', 'FR': '🇫🇷',
        'CA': '🇨🇦', 'AU': '🇦🇺', 'JP': '🇯🇵', 'CN': '🇨🇳', 'IN': '🇮🇳',
        'BR': '🇧🇷', 'RU': '🇷🇺', 'KR': '🇰🇷', 'IT': '🇮🇹', 'ES': '🇪🇸',
        'NL': '🇳🇱', 'SE': '🇸🇪', 'PL': '🇵🇱', 'UA': '🇺🇦', 'RO': '🇷🇴',
        'TR': '🇹🇷', 'MX': '🇲🇽', 'ID': '🇮🇩', 'TH': '🇹🇭', 'VN': '🇻🇳',
        'PH': '🇵🇭', 'MY': '🇲🇾', 'SG': '🇸🇬', 'AE': '🇦🇪', 'SA': '🇸🇦',
        'EG': '🇪🇬', 'ZA': '🇿🇦', 'NG': '🇳🇬', 'AR': '🇦🇷', 'CL': '🇨🇱',
        'CO': '🇨🇴', 'PE': '🇵🇪', 'VE': '🇻🇪', 'AT': '🇦🇹', 'BE': '🇧🇪',
        'CH': '🇨🇭', 'CZ': '🇨🇿', 'DK': '🇩🇰', 'FI': '🇫🇮', 'GR': '🇬🇷',
        'HU': '🇭🇺', 'IE': '🇮🇪', 'NO': '🇳🇴', 'PT': '🇵🇹', 'SK': '🇸🇰',
        'BG': '🇧🇬', 'HR': '🇭🇷', 'RS': '🇷🇸', 'SI': '🇸🇮', 'LT': '🇱🇹',
        'LV': '🇱🇻', 'EE': '🇪🇪', 'BY': '🇧🇾', 'MD': '🇲🇩', 'AL': '🇦🇱',
        'BA': '🇧🇦', 'MK': '🇲🇰', 'ME': '🇲🇪', 'XK': '🇽🇰', 'IL': '🇮🇱',
        'IQ': '🇮🇶', 'IR': '🇮🇷', 'JO': '🇯🇴', 'KW': '🇰🇼', 'LB': '🇱🇧',
        'OM': '🇴🇲', 'QA': '🇶🇦', 'SY': '🇸🇾', 'YE': '🇾🇪', 'PK': '🇵🇰',
        'BD': '🇧🇩', 'LK': '🇱🇰', 'NP': '🇳🇵', 'MM': '🇲🇲', 'KH': '🇰🇭',
        'LA': '🇱🇦', 'TW': '🇹🇼', 'HK': '🇭🇰', 'MO': '🇲🇴', 'NZ': '🇳🇿'
    }
    return flags.get(country_code.upper(), '🌍')


async def nineproxy_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    stats = nineproxy_db.get_statistics()
    is_enabled = nineproxy_db.is_service_enabled()
    margin = nineproxy_db.get_margin_percent()
    
    status_text = "🟢 مفعلة" if is_enabled else "🔴 متوقفة"
    
    msg = f'''
<b>🌐 إدارة 9Proxy</b>
━━━━━━━━━━━━━━━

📊 <b>الإحصائيات اليومية:</b>
📦 الطلبات: {stats['daily']['orders']}
💵 الإيرادات: {stats['daily']['revenue']:.2f}$
💰 التكلفة: {stats['daily']['cost']:.2f}$
📈 الربح: {stats['daily']['revenue'] - stats['daily']['cost']:.2f}$

📊 <b>الإحصائيات الكلية:</b>
📦 الطلبات: {stats['total']['orders']}
💵 الإيرادات: {stats['total']['revenue']:.2f}$

⚙️ <b>الإعدادات:</b>
📌 الحالة: {status_text}
📌 هامش الربح: {margin}%
'''
    
    toggle_text = "🔴 إيقاف الخدمة" if is_enabled else "🟢 تشغيل الخدمة"
    
    keyboard = [
        [InlineKeyboardButton(toggle_text, callback_data="9proxy_admin_toggle")],
        [InlineKeyboardButton("📊 هامش الربح", callback_data="9proxy_admin_margin")],
        [InlineKeyboardButton("💳 رصيد الحساب", callback_data="9proxy_admin_balance")],
        [InlineKeyboardButton("🔑 مفتاح API", callback_data="9proxy_admin_apikey")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_external_services")]
    ]
    
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)


async def handle_9proxy_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    data = query.data
    
    if data == "9proxy_admin_toggle":
        current = nineproxy_db.is_service_enabled()
        nineproxy_db.set_setting('service_enabled', 'false' if current else 'true')
        await nineproxy_admin_menu(update, context)
    
    elif data == "9proxy_admin_margin":
        context.user_data['waiting_9proxy_margin'] = True
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="9proxy_admin_menu")]]
        await query.edit_message_text(
            f"📊 هامش الربح الحالي: {nineproxy_db.get_margin_percent()}%\n\nأرسل النسبة الجديدة (مثال: 25):",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data == "9proxy_admin_balance":
        api = NineProxyAPI()
        result = api.get_port_status()
        
        if result.get('error'):
            await query.answer(f"خطأ: {result.get('error_code', 'x0x0009')}", show_alert=True)
        else:
            data_info = result.get('data', [])
            count = len(data_info) if isinstance(data_info, list) else 0
            await query.answer(f"📊 عدد المنافذ النشطة: {count}", show_alert=True)
    
    elif data == "9proxy_admin_apikey":
        context.user_data['waiting_9proxy_apikey'] = True
        current_key = nineproxy_db.get_setting('nineproxy_api_key', 'غير محدد')
        masked = current_key[:8] + "****" if current_key and len(current_key) > 8 else current_key
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="9proxy_admin_menu")]]
        await query.edit_message_text(
            f"🔑 مفتاح API الحالي: {masked}\n\nأرسل مفتاح API الجديد:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data == "9proxy_admin_menu":
        await nineproxy_admin_menu(update, context)


async def handle_9proxy_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if context.user_data.get('waiting_9proxy_margin'):
        try:
            margin = float(text)
            if margin < 0 or margin > 500:
                await update.message.reply_text("❌ النسبة يجب أن تكون بين 0 و 500")
                return True
            
            nineproxy_db.set_setting('margin_percent', str(margin))
            context.user_data.pop('waiting_9proxy_margin', None)
            await update.message.reply_text(f"✅ تم تحديث هامش الربح إلى {margin}%")
            return True
        except ValueError:
            await update.message.reply_text("❌ أدخل رقماً صحيحاً")
            return True
    
    elif context.user_data.get('waiting_9proxy_apikey'):
        nineproxy_db.set_setting('nineproxy_api_key', text)
        context.user_data.pop('waiting_9proxy_apikey', None)
        
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        except:
            pass
        
        await update.message.reply_text("✅ تم تحديث مفتاح API بنجاح")
        return True
    
    return False
