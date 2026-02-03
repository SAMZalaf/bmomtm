#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================
خدمة PremSocks - Daily SOCKS Proxy Service
============================================
هذا الملف يجمع جميع وظائف خدمة PremSocks في مكان واحد:
- PremSocksAPI: التعامل مع API
- PremSocksDB: إدارة قاعدة البيانات
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
import socket
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple, Union

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

logger = logging.getLogger(__name__)

API_BASE = "https://premsocks.com/api/v1"
DATABASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "proxy_bot.db")

PRODUCTS_CACHE = {
    'proxies': [],
    'countries': {},
    'last_update': 0,
    'cache_duration': 120
}

ERROR_CODES_PREMSOCKS = {
    'x0x0000': 'رصيد حساب الآدمن في الموقع غير كافٍ',
    'x0x0001': 'البروكسي المطلوب غير متوفر حالياً',
    'x0x0002': 'خطأ في الاتصال بالخدمة',
    'x0x0003': 'تم رفض الطلب - مفتاح API غير صحيح',
    'x0x0004': 'انتهت مهلة الاتصال',
    'x0x0005': 'معلومات الحساب غير صحيحة',
    'x0x0006': 'تم تجاوز حد الطلبات اليومي',
    'x0x0007': 'البروكسي غير موجود',
    'x0x0008': 'فشل في فحص البروكسي',
    'x0x0009': 'خطأ غير متوقع',
    'x0x000A': 'الخدمة متوقفة مؤقتاً'
}

COUNTRY_FLAGS = {
    'US': '🇺🇸', 'GB': '🇬🇧', 'UK': '🇬🇧', 'DE': '🇩🇪', 'FR': '🇫🇷', 'CA': '🇨🇦',
    'AU': '🇦🇺', 'JP': '🇯🇵', 'KR': '🇰🇷', 'CN': '🇨🇳', 'IN': '🇮🇳', 'BR': '🇧🇷',
    'RU': '🇷🇺', 'IT': '🇮🇹', 'ES': '🇪🇸', 'NL': '🇳🇱', 'SE': '🇸🇪', 'NO': '🇳🇴',
    'DK': '🇩🇰', 'FI': '🇫🇮', 'PL': '🇵🇱', 'TR': '🇹🇷', 'MX': '🇲🇽', 'AR': '🇦🇷',
    'ZA': '🇿🇦', 'EG': '🇪🇬', 'SA': '🇸🇦', 'AE': '🇦🇪', 'TW': '🇹🇼', 'HK': '🇭🇰',
    'SG': '🇸🇬', 'TH': '🇹🇭', 'VN': '🇻🇳', 'ID': '🇮🇩', 'MY': '🇲🇾', 'PH': '🇵🇭',
    'UA': '🇺🇦', 'CZ': '🇨🇿', 'AT': '🇦🇹', 'CH': '🇨🇭', 'BE': '🇧🇪', 'PT': '🇵🇹',
    'GR': '🇬🇷', 'RO': '🇷🇴', 'HU': '🇭🇺', 'IL': '🇮🇱', 'NZ': '🇳🇿', 'IE': '🇮🇪',
    'CO': '🇨🇴', 'CL': '🇨🇱', 'PE': '🇵🇪', 'VE': '🇻🇪', 'PK': '🇵🇰', 'BD': '🇧🇩'
}

COUNTRY_NAMES = {
    'US': {'ar': 'الولايات المتحدة', 'en': 'United States'},
    'GB': {'ar': 'المملكة المتحدة', 'en': 'United Kingdom'},
    'UK': {'ar': 'المملكة المتحدة', 'en': 'United Kingdom'},
    'DE': {'ar': 'ألمانيا', 'en': 'Germany'},
    'FR': {'ar': 'فرنسا', 'en': 'France'},
    'CA': {'ar': 'كندا', 'en': 'Canada'},
    'AU': {'ar': 'أستراليا', 'en': 'Australia'},
    'JP': {'ar': 'اليابان', 'en': 'Japan'},
    'KR': {'ar': 'كوريا الجنوبية', 'en': 'South Korea'},
    'CN': {'ar': 'الصين', 'en': 'China'},
    'IN': {'ar': 'الهند', 'en': 'India'},
    'BR': {'ar': 'البرازيل', 'en': 'Brazil'},
    'RU': {'ar': 'روسيا', 'en': 'Russia'},
    'IT': {'ar': 'إيطاليا', 'en': 'Italy'},
    'ES': {'ar': 'إسبانيا', 'en': 'Spain'},
    'NL': {'ar': 'هولندا', 'en': 'Netherlands'},
    'SE': {'ar': 'السويد', 'en': 'Sweden'},
    'NO': {'ar': 'النرويج', 'en': 'Norway'},
    'TW': {'ar': 'تايوان', 'en': 'Taiwan'},
    'HK': {'ar': 'هونغ كونغ', 'en': 'Hong Kong'},
    'ZA': {'ar': 'جنوب أفريقيا', 'en': 'South Africa'},
    'VN': {'ar': 'فيتنام', 'en': 'Vietnam'}
}


def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE, timeout=10.0)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def get_country_flag_premsocks(country_code: str) -> str:
    return COUNTRY_FLAGS.get(country_code.upper(), '🌍')


def get_country_name(country_code: str, language: str = 'ar') -> str:
    country_data = COUNTRY_NAMES.get(country_code.upper(), {})
    return country_data.get(language, country_code)


def log_api_error_premsocks(error_code: str, actual_error: str, context: str = ""):
    logger.error(f"[PremSocks {error_code}] {ERROR_CODES_PREMSOCKS.get(error_code, 'خطأ غير معروف')} | الخطأ الفعلي: {actual_error} | السياق: {context}")


def get_error_code_from_premsocks(error_code: int, error_message: str = "") -> str:
    error_mapping = {
        0: 'x0x0009',
        401: 'x0x0003',
        1000: 'x0x0007',
        1001: 'x0x0000',
        1002: 'x0x0000',
        1003: 'x0x0006',
        1004: 'x0x0006'
    }
    return error_mapping.get(error_code, 'x0x0009')


class PremSocksAPI:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session = requests.Session()
        self.timeout = 30
    
    def set_api_key(self, api_key: str):
        self.api_key = api_key
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def _make_request(self, method: str, endpoint: str, params: Dict = None) -> Dict:
        if not self.api_key:
            return {'status': False, 'error_code': 401, 'error_message': 'API key not set'}
        
        url = f"{API_BASE}{endpoint}"
        try:
            if method == 'GET':
                response = self.session.get(url, headers=self._get_headers(), params=params, timeout=self.timeout)
            else:
                response = self.session.post(url, headers=self._get_headers(), json=params, timeout=self.timeout)
            
            if response.status_code == 429:
                return {'status': False, 'error_code': 429, 'error_message': 'Rate limit exceeded'}
            elif response.status_code == 401:
                return {'status': False, 'error_code': 401, 'error_message': 'Unauthorized'}
            elif response.status_code == 503:
                return {'status': False, 'error_code': 503, 'error_message': 'Service unavailable'}
            
            return response.json()
        except requests.exceptions.Timeout:
            log_api_error_premsocks('x0x0004', 'Request timeout', endpoint)
            return {'status': False, 'error_code': 0, 'error_message': 'Timeout'}
        except requests.exceptions.RequestException as e:
            log_api_error_premsocks('x0x0002', str(e), endpoint)
            return {'status': False, 'error_code': 0, 'error_message': str(e)}
        except Exception as e:
            log_api_error_premsocks('x0x0009', str(e), endpoint)
            return {'status': False, 'error_code': 0, 'error_message': str(e)}
    
    def get_account_info(self) -> Dict:
        return self._make_request('GET', '/account')
    
    def get_proxy_list(self, country: str = None, city: str = None, state: str = None, 
                       isp: str = None, speed: int = None) -> Dict:
        params = {}
        if country:
            params['country'] = country
        if city:
            params['city'] = city
        if state:
            params['state'] = state
        if isp:
            params['isp'] = isp
        if speed:
            params['speed'] = speed
        
        return self._make_request('GET', '/socks/list', params)
    
    def get_proxy_list_smart(self, country: str = None, city: str = None, state: str = None, 
                              isp: str = None) -> Dict:
        """
        جلب البروكسيات مع فلتر السرعة التلقائي:
        1. يجلب البروكسيات السريعة (speed=1) أولاً
        2. إذا لم توجد، يجلب المتوسطة (speed=2)
        3. لا يجلب البطيئة أبداً (speed=3)
        """
        result = self.get_proxy_list(country=country, city=city, state=state, isp=isp, speed=1)
        
        if result.get('status') and result.get('data') and len(result.get('data', [])) > 0:
            logger.info(f"✅ تم جلب {len(result['data'])} بروكسي سريع (speed=1)")
            return result
        
        result = self.get_proxy_list(country=country, city=city, state=state, isp=isp, speed=2)
        
        if result.get('status') and result.get('data') and len(result.get('data', [])) > 0:
            logger.info(f"✅ تم جلب {len(result['data'])} بروكسي متوسط (speed=2)")
            return result
        
        logger.info("⚠️ لا توجد بروكسيات سريعة أو متوسطة متاحة")
        return {'status': True, 'data': [], 'count': 0}
    
    def get_proxy_by_id(self, proxy_id: Union[int, str]) -> Dict:
        return self._make_request('GET', f'/socks/{proxy_id}')
    
    def get_random_proxy(self, count: int = 1, country: str = None, speed: int = None) -> Dict:
        params = {'count': count}
        if country:
            params['country'] = country
        if speed:
            params['speed'] = speed
        
        return self._make_request('GET', '/socks/random', params)
    
    def get_random_proxy_smart(self, count: int = 1, country: str = None) -> Dict:
        """
        جلب بروكسي عشوائي مع فلتر السرعة التلقائي:
        1. يجلب بروكسي سريع (speed=1) أولاً
        2. إذا لم يوجد، يجلب متوسط (speed=2)
        3. لا يجلب البطيء أبداً (speed=3)
        """
        result = self.get_random_proxy(count=count, country=country, speed=1)
        
        if result.get('status') and result.get('data'):
            logger.info(f"✅ تم جلب بروكسي عشوائي سريع (speed=1)")
            return result
        
        result = self.get_random_proxy(count=count, country=country, speed=2)
        
        if result.get('status') and result.get('data'):
            logger.info(f"✅ تم جلب بروكسي عشوائي متوسط (speed=2)")
            return result
        
        logger.info("⚠️ لا توجد بروكسيات عشوائية سريعة أو متوسطة متاحة")
        return {'status': False, 'data': None, 'error_message': 'لا توجد بروكسيات سريعة أو متوسطة'}
    
    def get_proxy_history(self) -> Dict:
        return self._make_request('GET', '/socks/history')
    
    def check_proxy(self, ip: str, port: int, timeout: int = 10) -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except:
            return False


class PremSocksDB:
    def __init__(self):
        self.init_tables()
    
    def init_tables(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS premsocks_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS premsocks_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                proxy_id INTEGER NOT NULL,
                ip TEXT NOT NULL,
                port INTEGER NOT NULL,
                country TEXT,
                city TEXT,
                state TEXT,
                isp TEXT,
                speed INTEGER,
                price REAL NOT NULL,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_premsocks_user_id 
            ON premsocks_purchases(user_id)
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ تم تهيئة جداول PremSocks")
    
    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM premsocks_settings WHERE key = ?', (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else default
    
    def set_setting(self, key: str, value: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO premsocks_settings (key, value) VALUES (?, ?)
        ''', (key, value))
        conn.commit()
        conn.close()
    
    def is_service_enabled(self) -> bool:
        """تحقق من حالة الخدمة في الإعدادات"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM premsocks_settings WHERE key = 'service_enabled'")
        row = cursor.fetchone()
        conn.close()
        # مفعّل افتراضياً إذا لم تكن القيمة موجودة
        if row is None:
            return True
        return row[0] == '1'
    
    def get_proxy_price(self) -> float:
        return float(self.get_setting('proxy_price', '0.2'))
    
    def get_margin_percent(self) -> float:
        return float(self.get_setting('margin_percent', '20'))
    
    def get_api_key(self) -> Optional[str]:
        return self.get_setting('premsocks_api_key')
    
    def save_purchase(self, user_id: int, proxy_data: Dict, price: float) -> int:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        expires_at = datetime.now() + timedelta(hours=2)
        
        cursor.execute('''
            INSERT INTO premsocks_purchases 
            (user_id, proxy_id, ip, port, country, city, state, isp, speed, price, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            proxy_data.get('id', 0),
            proxy_data.get('ip', ''),
            proxy_data.get('port', 0),
            proxy_data.get('country', ''),
            proxy_data.get('city', ''),
            proxy_data.get('state', ''),
            proxy_data.get('isp', ''),
            proxy_data.get('speed', 0),
            price,
            expires_at.isoformat()
        ))
        
        purchase_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return purchase_id
    
    def get_user_proxies(self, user_id: int, limit: int = 10) -> List[Dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, proxy_id, ip, port, country, city, state, isp, speed, price, 
                   purchased_at, expires_at
            FROM premsocks_purchases
            WHERE user_id = ?
            ORDER BY purchased_at DESC
            LIMIT ?
        ''', (user_id, limit))
        
        columns = ['id', 'proxy_id', 'ip', 'port', 'country', 'city', 'state', 
                   'isp', 'speed', 'price', 'purchased_at', 'expires_at']
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_active_proxies(self, user_id: int) -> List[Dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, proxy_id, ip, port, country, city, state, isp, speed, price, 
                   purchased_at, expires_at
            FROM premsocks_purchases
            WHERE user_id = ? AND expires_at > datetime('now')
            ORDER BY purchased_at DESC
        ''', (user_id,))
        
        columns = ['id', 'proxy_id', 'ip', 'port', 'country', 'city', 'state', 
                   'isp', 'speed', 'price', 'purchased_at', 'expires_at']
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results


PREMSOCKS_MESSAGES = {
    'ar': {
        'menu_title': '🌐 سوكس يومي',
        'menu_desc': 'احصل على بروكسي SOCKS5 عالي الجودة',
        'buy_proxy': '🛒 شراء بروكسي',
        'my_proxies': '📋 بروكسياتي',
        'back': '🔙 رجوع',
        'select_country': '🌍 اختر الدولة',
        'random_proxy': '🎲 بروكسي عشوائي',
        'search_proxy': '🔍 بحث متقدم',
        'select_city': '🏙️ اختر المدينة:',
        'select_state': '📍 اختر الولاية:',
        'search_placeholder': '🔍 اكتب للبحث...',
        'confirm_purchase': '✅ تأكيد الشراء',
        'cancel': '❌ إلغاء',
        'purchase_confirm_msg': '''
💰 <b>تأكيد الشراء</b>

🌍 الدولة: {country}
🏙️ المدينة: {city}
📍 الولاية: {state}
🚀 السرعة: {speed}

💵 السعر: <code>{price}</code> كريديت
💳 رصيدك: <code>{balance}</code> كريديت

هل تريد المتابعة؟
''',
        'purchase_success': '''
✅ <b>{purchase_success_title}</b>

🌐 <b>{proxy_details_title}</b>
━━━━━━━━━━━━━━━
🔹 IP: <code>{ip}</code>
🔹 Port: <code>{port}</code>
━━━━━━━━━━━━━━━

{country_label}: {country}
{city_label}: {city}
{state_label}: {state}
{speed_label}: {speed}
{valid_for_label}: {valid_duration}

💡 {check_hint}
''',
        'purchase_success_title': 'تمت عملية الشراء بنجاح!',
        'proxy_details_title': 'تفاصيل البروكسي:',
        'valid_for_label': '',
        'valid_duration': '',
        'check_hint': 'استخدم زر "فحص" للتحقق من حالة البروكسي',
        'insufficient_balance': '❌ رصيدك غير كافٍ!\n\n💳 رصيدك الحالي: {balance} كريديت\n💵 المبلغ المطلوب: {required} كريديت',
        'admin_balance_low': '⚠️ عذراً، الخدمة غير متاحة حالياً.\n\nرمز الخطأ: x0x0000',
        'no_proxies': '📭 لا توجد لديك بروكسيات نشطة حالياً',
        'proxy_expired': '⏰ انتهت صلاحية هذا البروكسي',
        'check_status': '🔍 فحص',
        'proxy_online': '✅ البروكسي يعمل\n🌍 الدولة: {country}',
        'proxy_offline': '❌ البروكسي لا يعمل حالياً',
        'service_disabled': '⚠️ هذه الخدمة متوقفة مؤقتاً\n\nرمز الخطأ: x0x000A',
        'error_occurred': '❌ حدث خطأ\n\nرمز الخطأ: {code}',
        'no_results': '😔 لا توجد نتائج متاحة',
        'loading': '⏳ جاري التحميل...',
        'speed_fast': '⚡ سريع',
        'speed_medium': '🔄 متوسط',
        'speed_slow': '🐢 بطيء',
        'inline_title': '🌐 بحث بروكسي SOCKS5',
        'inline_desc': 'اكتب اسم الدولة أو المدينة للبحث',
        'proxy_info': '🌍 {country} | 🏙️ {city} | 🚀 {speed}',
        'buy_menu_text': '''
🛒 <b>شراء بروكسي SOCKS5</b>

اضغط على زر البحث أدناه لتصفح البروكسيات المتاحة حسب الدولة والولاية والمدينة.

💵 السعر: 0.2 كريديت لكل بروكسي
'''
    },
    'en': {
        'menu_title': '🌐 Daily SOCKS',
        'menu_desc': 'Get high-quality SOCKS5 proxy',
        'buy_proxy': '🛒 Buy Proxy',
        'my_proxies': '📋 My Proxies',
        'back': '🔙 Back',
        'select_country': '🌍 Select Country',
        'random_proxy': '🎲 Random Proxy',
        'search_proxy': '🔍 Advanced Search',
        'select_city': '🏙️ Select City:',
        'select_state': '📍 Select State:',
        'search_placeholder': '🔍 Type to search...',
        'confirm_purchase': '✅ Confirm Purchase',
        'cancel': '❌ Cancel',
        'purchase_confirm_msg': '''
💰 <b>Confirm Purchase</b>

🌍 Country: {country}
🏙️ City: {city}
📍 State: {state}
🚀 Speed: {speed}

💵 Price: <code>{price}</code> credits
💳 Your balance: <code>{balance}</code> credits

Do you want to proceed?
''',
        'purchase_success': '''
✅ <b>{purchase_success_title}</b>

🌐 <b>{proxy_details_title}</b>
━━━━━━━━━━━━━━━
🔹 IP: <code>{ip}</code>
🔹 Port: <code>{port}</code>
━━━━━━━━━━━━━━━

{country_label}: {country}
{city_label}: {city}
{state_label}: {state}
{speed_label}: {speed}
{valid_for_label}: {valid_duration}

💡 {check_hint}
''',
        'purchase_success_title': 'Purchase Successful!',
        'proxy_details_title': 'Proxy Details:',
        'valid_for_label': '',
        'valid_duration': '',
        'check_hint': 'Use "Check" button to verify proxy status',
        'insufficient_balance': '❌ Insufficient balance!\n\n💳 Your balance: {balance} credits\n💵 Required: {required} credits',
        'admin_balance_low': '⚠️ Sorry, service is currently unavailable.\n\nError code: x0x0000',
        'no_proxies': '📭 You have no active proxies',
        'proxy_expired': '⏰ This proxy has expired',
        'check_status': '🔍 Check',
        'proxy_online': '✅ Proxy is working\n🌍 Country: {country}',
        'proxy_offline': '❌ Proxy is currently offline',
        'service_disabled': '⚠️ This service is temporarily disabled\n\nError code: x0x000A',
        'error_occurred': '❌ An error occurred\n\nError code: {code}',
        'no_results': '😔 No results available',
        'loading': '⏳ Loading...',
        'speed_fast': '⚡ Fast',
        'speed_medium': '🔄 Medium',
        'speed_slow': '🐢 Slow',
        'inline_title': '🌐 SOCKS5 Proxy Search',
        'inline_desc': 'Type country or city name to search',
        'proxy_info': '🌍 {country} | 🏙️ {city} | 🚀 {speed}',
        'buy_menu_text': '''
🛒 <b>Buy SOCKS5 Proxy</b>

Click the search button below to browse available proxies by country, state, and city.

💵 Price: 0.2 credits per proxy
'''
    }
}


def get_premsocks_message(key: str, language: str = 'ar') -> str:
    return PREMSOCKS_MESSAGES.get(language, PREMSOCKS_MESSAGES['ar']).get(key, key)


def get_speed_text(speed: int, language: str = 'ar') -> str:
    speed_map = {
        1: get_premsocks_message('speed_fast', language),
        2: get_premsocks_message('speed_medium', language),
        3: get_premsocks_message('speed_slow', language)
    }
    return speed_map.get(speed, '❓')


def get_user_language(user_id: int) -> str:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT language FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 'ar'
    except:
        return 'ar'


def get_user_balance(user_id: int) -> float:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return float(result[0]) if result else 0.0
    except:
        return 0.0


def deduct_user_balance(user_id: int, amount: float) -> bool:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET balance = balance - ? 
            WHERE user_id = ? AND balance >= ?
        ''', (amount, user_id, amount))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    except:
        return False


premsocks_db = PremSocksDB()


async def premsocks_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    if not premsocks_db.is_service_enabled():
        if update.callback_query:
            await update.callback_query.edit_message_text(get_premsocks_message('service_disabled', language))
        else:
            await update.message.reply_text(get_premsocks_message('service_disabled', language))
        return
    
    keyboard = [
        [InlineKeyboardButton(get_premsocks_message('buy_proxy', language), callback_data="ps_buy_menu")],
        [InlineKeyboardButton(get_premsocks_message('my_proxies', language), callback_data="ps_my_proxies")],
        [InlineKeyboardButton(get_premsocks_message('back', language), callback_data="ps_back_main")]
    ]
    
    text = f"🌐 <b>{get_premsocks_message('menu_title', language)}</b>\n\n{get_premsocks_message('menu_desc', language)}"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
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


async def show_buy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    text = get_premsocks_message('buy_menu_text', language)
    
    keyboard = [
        [InlineKeyboardButton(
            "🔍 البحث عن بروكسي 🔍" if language == 'ar' else "🔍 Search for Proxy 🔍", 
            switch_inline_query_current_chat="socks:country "
        )],
        [InlineKeyboardButton(
            "🔙 رجوع" if language == 'ar' else "🔙 Back", 
            callback_data="ps_main_menu"
        )]
    ]
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def show_countries_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await show_buy_menu(update, context)

async def show_country_proxies(update: Update, context: ContextTypes.DEFAULT_TYPE, country_code: str) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    api_key = premsocks_db.get_api_key() or premsocks_db.get_setting('premsocks_api_key')
    api = PremSocksAPI(api_key)
    result = api.get_proxy_list(country=country_code)
    
    if not result.get('status'):
        error_code = get_error_code_from_premsocks(result.get('error_code', 0))
        await query.edit_message_text(get_premsocks_message('error_occurred', language).format(code=error_code))
        return
    
    proxies = result.get('data', [])[:10]
    
    if not proxies:
        await query.edit_message_text(get_premsocks_message('no_results', language))
        return
    
    keyboard = []
    price = premsocks_db.get_proxy_price()
    
    for proxy in proxies:
        proxy_id = proxy.get('id')
        city = proxy.get('city', 'N/A')
        speed = proxy.get('speed', 2)
        speed_text = get_speed_text(speed, language)
        
        keyboard.append([InlineKeyboardButton(
            f"🏙️ {city} | {speed_text} | 💵 {price}",
            callback_data=f"ps_buy_{proxy_id}"
        )])
    
    keyboard.append([InlineKeyboardButton(
        get_premsocks_message('back', language),
        callback_data="ps_buy_menu"
    )])
    
    flag = get_country_flag_premsocks(country_code)
    name = get_country_name(country_code, language)
    
    await query.edit_message_text(
        f"{flag} <b>{name}</b>\n\n{get_premsocks_message('select_city', language)}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def confirm_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, proxy_id: int) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    api_key = premsocks_db.get_api_key() or premsocks_db.get_setting('premsocks_api_key')
    if not api_key:
        await query.edit_message_text(get_premsocks_message('error_occurred', language).format(code='x0x0003'))
        return
    
    api = PremSocksAPI(api_key)
    
    # الحصول على تفاصيل البروكسي قبل الشراء لتأكيد السعر والمعلومات
    result = api.get_proxy_list()
    if not result.get('status'):
        await query.edit_message_text(get_premsocks_message('error_occurred', language).format(code='x0x0002'))
        return
    
    proxy_data = None
    for p in result.get('data', []):
        if p.get('id') == proxy_id:
            proxy_data = p
            break
    
    if not proxy_data:
        await query.edit_message_text(get_premsocks_message('error_occurred', language).format(code='x0x0007'))
        return
    
    context.user_data['pending_proxy'] = proxy_data
    
    price = premsocks_db.get_proxy_price()
    balance = get_user_balance(user_id)
    
    flag = get_country_flag_premsocks(proxy_data.get('country', 'XX'))
    country_name = get_country_name(proxy_data.get('country', 'XX'), language)
    speed_text = get_speed_text(proxy_data.get('speed', 2), language)
    
    text = get_premsocks_message('purchase_confirm_msg', language).format(
        country=f"{flag} {country_name}",
        city=proxy_data.get('city', 'N/A'),
        state=proxy_data.get('state', 'N/A'),
        speed=speed_text,
        price=price,
        balance=balance
    )
    
    keyboard = [
        [
            InlineKeyboardButton(get_premsocks_message('confirm_purchase', language), callback_data=f"ps_confirm_{proxy_id}"),
            InlineKeyboardButton(get_premsocks_message('cancel', language), callback_data="ps_buy_menu")
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def process_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, proxy_id: int) -> None:
    query = update.callback_query
    await query.answer(get_premsocks_message('loading', get_user_language(update.effective_user.id)))
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    price = premsocks_db.get_proxy_price()
    balance = get_user_balance(user_id)
    
    if balance < price:
        await query.edit_message_text(
            get_premsocks_message('insufficient_balance', language).format(
                balance=balance,
                required=price
            )
        )
        return
    
    api_key = premsocks_db.get_api_key() or premsocks_db.get_setting('premsocks_api_key')
    if not api_key:
        if query:
            await query.edit_message_text(get_premsocks_message('error_occurred', language).format(code='x0x0003'))
        return
    api = PremSocksAPI(api_key)
    
    result = api.get_proxy_by_id(proxy_id)
    
    if not result.get('status'):
        error_code = result.get('error_code', 0)
        if error_code in [1001, 1002]:
            await query.edit_message_text(get_premsocks_message('admin_balance_low', language))
        elif error_code == 1003:
            await query.edit_message_text(get_premsocks_message('error_occurred', language).format(code='x0x0006'))
        else:
            await query.edit_message_text(get_premsocks_message('error_occurred', language).format(code=get_error_code_from_premsocks(error_code)))
        return
    
    proxy_data = result.get('data', [{}])[0]
    
    if not deduct_user_balance(user_id, price):
        await query.edit_message_text(get_premsocks_message('insufficient_balance', language).format(
            balance=balance, required=price
        ))
        return
    
    purchase_id = premsocks_db.save_purchase(user_id, proxy_data, price)
    
    flag = get_country_flag_premsocks(proxy_data.get('country', 'XX'))
    country_name = get_country_name(proxy_data.get('country', 'XX'), language)
    speed_text = get_speed_text(proxy_data.get('speed', 2), language)
    
    text = get_premsocks_message('purchase_success', language).format(
        ip=proxy_data.get('ip', 'N/A'),
        port=proxy_data.get('port', 'N/A'),
        country=f"{flag} {country_name}",
        city=proxy_data.get('city', 'N/A'),
        state=proxy_data.get('state', 'N/A'),
        speed=speed_text
    )
    
    keyboard = [[InlineKeyboardButton(
        get_premsocks_message('check_status', language),
        callback_data=f"ps_check_{purchase_id}"
    )]]
    keyboard.append([InlineKeyboardButton(
        get_premsocks_message('back', language),
        callback_data="ps_main_menu"
    )])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def buy_random_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer(get_premsocks_message('loading', get_user_language(update.effective_user.id)))
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    price = premsocks_db.get_proxy_price()
    balance = get_user_balance(user_id)
    
    if balance < price:
        await query.edit_message_text(
            get_premsocks_message('insufficient_balance', language).format(
                balance=balance,
                required=price
            )
        )
        return
    
    api_key = premsocks_db.get_api_key() or premsocks_db.get_setting('premsocks_api_key')
    if not api_key:
        if query:
            await query.edit_message_text(get_premsocks_message('error_occurred', language).format(code='x0x0003'))
        return
    api = PremSocksAPI(api_key)
    
    result = api.get_random_proxy_smart()
    
    if not result.get('status'):
        error_code = result.get('error_code', 0)
        if error_code in [1001, 1002]:
            await query.edit_message_text(get_premsocks_message('admin_balance_low', language))
        else:
            await query.edit_message_text(get_premsocks_message('error_occurred', language).format(
                code=get_error_code_from_premsocks(error_code)
            ))
        return
    
    proxy_data = result.get('data', [{}])[0]
    
    if not deduct_user_balance(user_id, price):
        await query.edit_message_text(get_premsocks_message('insufficient_balance', language).format(
            balance=balance, required=price
        ))
        return
    
    purchase_id = premsocks_db.save_purchase(user_id, proxy_data, price)
    
    flag = get_country_flag_premsocks(proxy_data.get('country', 'XX'))
    country_name = get_country_name(proxy_data.get('country', 'XX'), language)
    speed_text = get_speed_text(proxy_data.get('speed', 2), language)
    
    text = get_premsocks_message('purchase_success', language).format(
        ip=proxy_data.get('ip', 'N/A'),
        port=proxy_data.get('port', 'N/A'),
        country=f"{flag} {country_name}",
        city=proxy_data.get('city', 'N/A'),
        state=proxy_data.get('state', 'N/A'),
        speed=speed_text
    )
    
    keyboard = [[InlineKeyboardButton(
        get_premsocks_message('check_status', language),
        callback_data=f"ps_check_{purchase_id}"
    )]]
    keyboard.append([InlineKeyboardButton(
        get_premsocks_message('back', language),
        callback_data="ps_main_menu"
    )])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def process_random_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                   country: str = None, state: str = None, 
                                   city: str = None, isp: str = None) -> None:
    """
    شراء بروكسي عشوائي بناءً على المعايير المحددة
    يبحث عن بروكسي متاح يطابق المعايير ثم يشتريه
    """
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    price = premsocks_db.get_proxy_price()
    balance = get_user_balance(user_id)
    
    if balance < price:
        await query.edit_message_text(
            get_premsocks_message('insufficient_balance', language).format(
                balance=balance,
                required=price
            )
        )
        return
    
    api_key = premsocks_db.get_api_key() or premsocks_db.get_setting('premsocks_api_key')
    if not api_key:
        await query.edit_message_text(get_premsocks_message('error_occurred', language).format(code='x0x0003'))
        return
    
    api = PremSocksAPI(api_key)
    
    # بناء معايير البحث
    params = {}
    if country:
        params['country'] = country
    if state:
        params['state'] = state
    if city:
        params['city'] = city
    if isp:
        params['isp'] = isp
    
    # عرض رسالة انتظار
    criteria_text = []
    if country:
        flag = get_country_flag_premsocks(country)
        country_name = get_country_name(country, language)
        criteria_text.append(f"🌍 الدولة: {flag} {country_name}")
    if state:
        criteria_text.append(f"📍 الولاية: {state}")
    if city:
        criteria_text.append(f"🏙️ المدينة: {city}")
    if isp:
        criteria_text.append(f"🌐 المزود: {isp}")
    
    if not criteria_text:
        criteria_text.append("🎲 عشوائي بالكامل")
    
    await query.edit_message_text(
        f"⏳ جاري البحث عن بروكسي...\n\n" + "\n".join(criteria_text),
        parse_mode='HTML'
    )
    
    # البحث عن بروكسي متاح مع فلتر السرعة التلقائي
    if params:
        result = api.get_proxy_list_smart(**params)
    else:
        result = api.get_random_proxy_smart()
    
    if not result.get('status'):
        error_code = result.get('error_code', 0)
        if error_code in [1001, 1002]:
            await query.edit_message_text(get_premsocks_message('admin_balance_low', language))
        else:
            await query.edit_message_text(get_premsocks_message('error_occurred', language).format(
                code=get_error_code_from_premsocks(error_code)
            ))
        return
    
    proxies = result.get('data', [])
    if not proxies:
        await query.edit_message_text(
            "❌ لا توجد بروكسيات متاحة بهذه المواصفات\n\nجرب تغيير المعايير أو اختر شراء عشوائي"
            if language == 'ar' else
            "❌ No proxies available with these specifications\n\nTry changing criteria or choose random buy",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(get_premsocks_message('back', language), callback_data="ps_buy_menu")]
            ])
        )
        return
    
    # اختيار أول بروكسي متاح
    import random
    proxy_data = random.choice(proxies) if len(proxies) > 1 else proxies[0]
    proxy_id = proxy_data.get('id')
    
    # جلب البروكسي فعلياً (يستهلك من حساب الأدمن)
    buy_result = api.get_proxy_by_id(proxy_id)
    
    if not buy_result.get('status'):
        error_code = buy_result.get('error_code', 0)
        if error_code in [1001, 1002]:
            await query.edit_message_text(get_premsocks_message('admin_balance_low', language))
        else:
            await query.edit_message_text(get_premsocks_message('error_occurred', language).format(
                code=get_error_code_from_premsocks(error_code)
            ))
        return
    
    bought_proxy = buy_result.get('data', [{}])[0] if isinstance(buy_result.get('data'), list) else buy_result.get('data', {})
    
    # خصم الرصيد من المستخدم
    if not deduct_user_balance(user_id, price):
        await query.edit_message_text(get_premsocks_message('insufficient_balance', language).format(
            balance=balance, required=price
        ))
        return
    
    # حفظ عملية الشراء
    purchase_id = premsocks_db.save_purchase(user_id, bought_proxy, price)
    
    flag = get_country_flag_premsocks(bought_proxy.get('country', 'XX'))
    country_name = get_country_name(bought_proxy.get('country', 'XX'), language)
    speed_text = get_speed_text(bought_proxy.get('speed', 2), language)
    
    # ترجمة أسماء الحقول حسب اللغة
    country_label = "الدولة" if language == 'ar' else "Country"
    city_label = "المدينة" if language == 'ar' else "City"
    state_label = "الولاية" if language == 'ar' else "State"
    speed_label = "السرعة" if language == 'ar' else "Speed"
    
    text = get_premsocks_message('purchase_success', language).format(
        ip=bought_proxy.get('ip', 'N/A'),
        port=bought_proxy.get('port', 'N/A'),
        country=f"{flag} {country_name}",
        city=bought_proxy.get('city', 'N/A'),
        state=bought_proxy.get('state', 'N/A'),
        speed=speed_text,
        country_label=country_label,
        city_label=city_label,
        state_label=state_label,
        speed_label=speed_label,
        purchase_success_title=get_premsocks_message('purchase_success_title', language),
        proxy_details_title=get_premsocks_message('proxy_details_title', language),
        valid_for_label=get_premsocks_message('valid_for_label', language),
        valid_duration=get_premsocks_message('valid_duration', language),
        check_hint=get_premsocks_message('check_hint', language)
    )
    
    keyboard = [[InlineKeyboardButton(
        get_premsocks_message('check_status', language),
        callback_data=f"ps_check_{purchase_id}"
    )]]
    keyboard.append([InlineKeyboardButton(
        get_premsocks_message('back', language),
        callback_data="ps_main_menu"
    )])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def show_my_proxies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    proxies = premsocks_db.get_active_proxies(user_id)
    
    if not proxies:
        keyboard = [[InlineKeyboardButton(
            get_premsocks_message('back', language),
            callback_data="ps_main_menu"
        )]]
        await query.edit_message_text(
            get_premsocks_message('no_proxies', language),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    keyboard = []
    for proxy in proxies:
        flag = get_country_flag_premsocks(proxy.get('country', 'XX'))
        city = proxy.get('city', 'N/A')
        ip = proxy.get('ip', 'N/A')
        
        keyboard.append([InlineKeyboardButton(
            f"{flag} {city} | {ip}",
            callback_data=f"ps_view_{proxy['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton(
        get_premsocks_message('back', language),
        callback_data="ps_main_menu"
    )])
    
    await query.edit_message_text(
        f"📋 <b>{get_premsocks_message('my_proxies', language)}</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def view_proxy_details(update: Update, context: ContextTypes.DEFAULT_TYPE, purchase_id: int) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    proxies = premsocks_db.get_user_proxies(user_id, limit=50)
    proxy = None
    for p in proxies:
        if p['id'] == purchase_id:
            proxy = p
            break
    
    if not proxy:
        await query.edit_message_text(get_premsocks_message('proxy_expired', language))
        return
    
    flag = get_country_flag_premsocks(proxy.get('country', 'XX'))
    country_name = get_country_name(proxy.get('country', 'XX'), language)
    speed_text = get_speed_text(proxy.get('speed', 2), language)
    
    text = f"""
🌐 <b>{get_premsocks_message('proxy_details_title', language)}</b>
━━━━━━━━━━━━━━━
🔹 IP: <code>{proxy.get('ip', 'N/A')}</code>
🔹 Port: <code>{proxy.get('port', 'N/A')}</code>
━━━━━━━━━━━━━━━

{"🌍 الدولة" if language == 'ar' else "🌍 Country"}: {flag} {country_name}
{"🏙️ المدينة" if language == 'ar' else "🏙️ City"}: {proxy.get('city', 'N/A')}
{"📍 الولاية" if language == 'ar' else "📍 State"}: {proxy.get('state', 'N/A')}
{"🚀 السرعة" if language == 'ar' else "🚀 Speed"}: {speed_text}
"""
    
    keyboard = [
        [InlineKeyboardButton(
            get_premsocks_message('check_status', language),
            callback_data=f"ps_check_{purchase_id}"
        )],
        [InlineKeyboardButton(
            get_premsocks_message('back', language),
            callback_data="ps_my_proxies"
        )]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def check_proxy_status(update: Update, context: ContextTypes.DEFAULT_TYPE, purchase_id: int) -> None:
    query = update.callback_query
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    proxies = premsocks_db.get_user_proxies(user_id, limit=50)
    proxy = None
    for p in proxies:
        if p['id'] == purchase_id:
            proxy = p
            break
    
    if not proxy:
        await query.answer(get_premsocks_message('proxy_expired', language), show_alert=True)
        return
    
    api = PremSocksAPI()
    is_online = api.check_proxy(proxy.get('ip', ''), proxy.get('port', 0))
    
    if is_online:
        flag = get_country_flag_premsocks(proxy.get('country', 'XX'))
        country_name = get_country_name(proxy.get('country', 'XX'), language)
        await query.answer(
            get_premsocks_message('proxy_online', language).format(country=f"{flag} {country_name}"),
            show_alert=True
        )
    else:
        await query.answer(get_premsocks_message('proxy_offline', language), show_alert=True)


async def handle_premsocks_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data
    
    if data == "ps_main_menu":
        await premsocks_main_menu(update, context)
    elif data == "ps_buy_menu":
        await show_buy_menu(update, context)
    elif data == "ps_my_proxies":
        await show_my_proxies(update, context)
    elif data == "ps_random":
        await buy_random_proxy(update, context)
    elif data == "ps_back_main":
        await query.answer()
        await query.message.delete()
    elif data.startswith("ps_country_"):
        country_code = data.replace("ps_country_", "")
        await show_country_proxies(update, context, country_code)
    elif data.startswith("ps_buy_random_"):
        # شراء عشوائي بناءً على المعايير المحددة
        # الصيغة: ps_buy_random_COUNTRY_STATE_CITY_ISP
        parts = data.replace("ps_buy_random_", "").split("_")
        country = parts[0] if len(parts) > 0 and parts[0] else None
        state = parts[1].replace("_", " ") if len(parts) > 1 and parts[1] else None
        city = parts[2].replace("_", " ") if len(parts) > 2 and parts[2] else None
        isp = parts[3].replace("_", " ") if len(parts) > 3 and parts[3] else None
        await process_random_purchase(update, context, country, state, city, isp)
    elif data.startswith("ps_skip_state_"):
        # تخطي الولاية → الانتقال لاختيار المدينة مباشرة
        user_id = update.effective_user.id
        language = get_user_language(user_id)
        country_code = data.replace("ps_skip_state_", "")
        country_name = get_country_name(country_code, language)
        flag = get_country_flag_premsocks(country_code)
        
        if language == 'ar':
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 شراء سريع", callback_data=f"ps_buy_random_{country_code}___")],
                [InlineKeyboardButton("🏙️ اختيار مدينة ←", switch_inline_query_current_chat=f"socks:city:{country_code}: ")],
                [InlineKeyboardButton("⏭️ تخطي المدينة", callback_data=f"ps_skip_city_{country_code}_")]
            ])
            await query.edit_message_text(
                f"📍 تم تخطي اختيار الولاية\n\n"
                f"🌍 الدولة: {flag} {country_name}\n"
                f"📍 الولاية: عشوائية\n\n"
                f"الخطوة التالية: اختر مدينة أو اشترِ مباشرة",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        else:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Quick Buy", callback_data=f"ps_buy_random_{country_code}___")],
                [InlineKeyboardButton("🏙️ Select City ←", switch_inline_query_current_chat=f"socks:city:{country_code}: ")],
                [InlineKeyboardButton("⏭️ Skip City", callback_data=f"ps_skip_city_{country_code}_")]
            ])
            await query.edit_message_text(
                f"📍 State selection skipped\n\n"
                f"🌍 Country: {flag} {country_name}\n"
                f"📍 State: Random\n\n"
                f"Next step: Select a city or buy directly",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
    elif data.startswith("ps_skip_city_"):
        # تخطي المدينة → الانتقال لاختيار المزود مباشرة
        user_id = update.effective_user.id
        language = get_user_language(user_id)
        parts = data.replace("ps_skip_city_", "").split("_")
        country_code = parts[0] if len(parts) > 0 else ""
        state_encoded = parts[1] if len(parts) > 1 else ""
        country_name = get_country_name(country_code, language)
        flag = get_country_flag_premsocks(country_code)
        state_display = state_encoded.replace("_", " ") if state_encoded else ""
        
        if language == 'ar':
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 شراء سريع", callback_data=f"ps_buy_random_{country_code}_{state_encoded}__")],
                [InlineKeyboardButton("🌐 اختيار مزود ←", switch_inline_query_current_chat=f"socks:isp:{country_code}:{state_encoded}: ")],
                [InlineKeyboardButton("⏭️ تخطي المزود (شراء)", callback_data=f"ps_buy_random_{country_code}_{state_encoded}__")]
            ])
            await query.edit_message_text(
                f"🏙️ تم تخطي اختيار المدينة\n\n"
                f"🌍 الدولة: {flag} {country_name}\n"
                f"📍 الولاية: {state_display or 'عشوائية'}\n"
                f"🏙️ المدينة: عشوائية\n\n"
                f"الخطوة التالية: اختر مزود أو اشترِ مباشرة",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        else:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Quick Buy", callback_data=f"ps_buy_random_{country_code}_{state_encoded}__")],
                [InlineKeyboardButton("🌐 Select ISP ←", switch_inline_query_current_chat=f"socks:isp:{country_code}:{state_encoded}: ")],
                [InlineKeyboardButton("⏭️ Skip ISP (Buy)", callback_data=f"ps_buy_random_{country_code}_{state_encoded}__")]
            ])
            await query.edit_message_text(
                f"🏙️ City selection skipped\n\n"
                f"🌍 Country: {flag} {country_name}\n"
                f"📍 State: {state_display or 'Random'}\n"
                f"🏙️ City: Random\n\n"
                f"Next step: Select an ISP or buy directly",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
    elif data.startswith("ps_buy_"):
        proxy_id = int(data.replace("ps_buy_", ""))
        await confirm_purchase(update, context, proxy_id)
    elif data.startswith("ps_confirm_"):
        proxy_id = int(data.replace("ps_confirm_", ""))
        await process_purchase(update, context, proxy_id)
    elif data.startswith("ps_view_"):
        purchase_id = int(data.replace("ps_view_", ""))
        await view_proxy_details(update, context, purchase_id)
    elif data.startswith("ps_check_"):
        purchase_id = int(data.replace("ps_check_", ""))
        await check_proxy_status(update, context, purchase_id)


async def premsocks_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()
    
    api_key = premsocks_db.get_api_key()
    service_enabled = premsocks_db.is_service_enabled()
    proxy_price = premsocks_db.get_proxy_price()
    margin_percent = premsocks_db.get_margin_percent()
    
    account_info = "❓ غير متصل"
    if api_key:
        api = PremSocksAPI(api_key)
        result = api.get_account_info()
        if result.get('status'):
            data = result.get('data', {})
            balance = data.get('balance', 0)
            package = data.get('package', {})
            package_name = package.get('name', 'N/A')
            daily_limit = package.get('daily_limit', 0)
            limit_remaining = package.get('limit_remaining', 0)
            days_left = package.get('days_left', 0)
            
            account_info = f"""
💰 الرصيد: ${balance}
📦 الباقة: {package_name}
📊 الحد اليومي: {limit_remaining}/{daily_limit}
⏰ أيام متبقية: {days_left}
"""
    
    status_text = "✅ مفعّل" if service_enabled else "❌ معطّل"
    
    text = f"""
🌐 <b>إدارة سوكس يومي (PremSocks)</b>

📊 <b>حالة الخدمة:</b> {status_text}
💵 <b>سعر البروكسي:</b> {proxy_price} كريديت

🏦 <b>معلومات الحساب:</b>
{account_info}
"""
    
    keyboard = [
        [InlineKeyboardButton(
            "🔴 إيقاف الخدمة" if service_enabled else "🟢 تشغيل الخدمة",
            callback_data="ps_admin_toggle"
        )],
        [InlineKeyboardButton("💵 تعديل السعر", callback_data="ps_admin_price")],
        [InlineKeyboardButton("🔑 تعديل مفتاح API", callback_data="ps_admin_apikey")],
        [InlineKeyboardButton("👤 عرض معلومات الحساب", callback_data="ps_admin_balance")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_manage_proxies")]
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


async def handle_premsocks_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data
    
    if data == "ps_admin_toggle":
        current = premsocks_db.is_service_enabled()
        new_status = '1' if not current else '0'
        premsocks_db.set_setting('service_enabled', new_status)
        logger.info(f"PremSocks service toggled to: {new_status}")
        await query.answer(f"تم {'تفعيل' if new_status == '1' else 'تعطيل'} الخدمة")
        await premsocks_admin_menu(update, context)
    
    elif data == "ps_admin_price":
        await query.answer()
        context.user_data['waiting_ps_price'] = True
        current_price = premsocks_db.get_proxy_price()
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="ps_admin_menu")]]
        await query.edit_message_text(
            f"💵 السعر الحالي: {current_price} كريديت\n\nأرسل السعر الجديد:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data == "ps_admin_apikey":
        await query.answer()
        context.user_data['waiting_ps_apikey'] = True
        current_key = premsocks_db.get_api_key()
        masked = current_key[:8] + "****" if current_key and len(current_key) > 8 else "غير محدد"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="ps_admin_menu")]]
        await query.edit_message_text(
            f"🔑 مفتاح API الحالي: {masked}\n\nأرسل مفتاح API الجديد:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data == "ps_admin_balance":
        await query.answer()
        api_key = premsocks_db.get_api_key() or premsocks_db.get_setting('premsocks_api_key')
        
        if not api_key:
            await query.edit_message_text("❌ مفتاح API غير محدد في الإعدادات")
            return
            
        api = PremSocksAPI(api_key)
        result = api.get_account_info()
        
        if result.get('status'):
            data_info = result.get('data', {})
            username = data_info.get('username', 'N/A')
            email = data_info.get('email', 'N/A')
            balance = data_info.get('balance', 0)
            package = data_info.get('package', {})
            
            package_name = package.get('name', 'N/A')
            daily_limit = package.get('daily_limit', 0)
            used = package.get('used', 0)
            limit_remaining = package.get('limit_remaining', 0)
            limit_reached = "✅ لا" if not package.get('limit_reached', False) else "❌ نعم"
            days_left = package.get('days_left', 0)
            activated_at = package.get('activated_at', 'N/A')
            expires_at = package.get('expires_at', 'N/A')
            
            text = f"""
💰 <b>معلومات حساب PremSocks</b>

👤 <b>اسم المستخدم:</b> {username}
📧 <b>البريد:</b> {email}
💵 <b>الرصيد:</b> ${balance}

📦 <b>تفاصيل الباقة:</b>
├ 📛 الاسم: {package_name}
├ 📊 الحد اليومي: {daily_limit}
├ ✅ المستخدم اليوم: {used}
├ 📈 المتبقي: {limit_remaining}
├ 🚫 وصل للحد: {limit_reached}
├ ⏳ الأيام المتبقية: {days_left}
├ 📅 تاريخ التفعيل: {activated_at}
└ 📅 تاريخ الانتهاء: {expires_at}
"""
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="ps_admin_menu")]]
            await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            error_msg = result.get('message', result.get('error', 'خطأ غير معروف'))
            await query.edit_message_text(f"❌ فشل في جلب المعلومات: {error_msg}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="ps_admin_menu")]]))
    
    elif data == "ps_admin_menu":
        await premsocks_admin_menu(update, context)


async def handle_premsocks_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    text = update.message.text.strip()
    
    if context.user_data.get('waiting_ps_price'):
        try:
            price = float(text)
            if price < 0 or price > 1000:
                await update.message.reply_text("❌ السعر يجب أن يكون بين 0 و 1000")
                return True
            
            premsocks_db.set_setting('proxy_price', str(price))
            context.user_data.pop('waiting_ps_price', None)
            await update.message.reply_text(f"✅ تم تحديث السعر إلى {price} كريديت")
            return True
        except ValueError:
            await update.message.reply_text("❌ أدخل رقماً صحيحاً")
            return True
    
    elif context.user_data.get('waiting_ps_apikey'):
        premsocks_db.set_setting('premsocks_api_key', text)
        context.user_data.pop('waiting_ps_apikey', None)
        
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        except:
            pass
        
        await update.message.reply_text("✅ تم تحديث مفتاح API بنجاح")
        return True
    
    return False


async def handle_premsocks_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    نظام البحث التدريجي عبر Inline Query
    البادئات:
    - socks:country → عرض الدول المتاحة
    - socks:state:XX → عرض الولايات في الدولة XX
    - socks:city:XX:STATE → عرض المدن في الولاية
    - socks:isp:XX:STATE:CITY → عرض المزودين في المدينة
    """
    query = update.inline_query
    search_text = query.query.strip()
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    # تحويل البحث إلى lowercase للمقارنة
    search_text_lower = search_text.lower()
    
    # التحقق مما إذا كان البحث يبدأ بالكلمات المفتاحية المطلوبة
    # إذا كان فارغاً تماماً أو يبدأ بـ "socks" أو "سوكس"
    if search_text_lower == "":
        search_text = "socks:country"
    elif search_text_lower in ["socks", "socks:", "سوكس", "سوكس:"]:
        search_text = "socks:country"
    elif search_text_lower.startswith("socks ") or search_text_lower.startswith("سوكس "):
        parts = search_text.split(None, 1)
        if len(parts) > 1:
            search_text = f"socks:country:{parts[1]}"
        else:
            search_text = "socks:country"
    elif search_text_lower.startswith("socks:") or search_text_lower.startswith("سوكس:"):
        # إذا كان يبدأ بـ "سوكس:" نحولها لـ "socks:" لتفهمها بقية الدالة
        if search_text_lower.startswith("سوكس:"):
            search_text = "socks:" + search_text[5:]
    else:
        # البحث المباشر: أي نص يعتبر بحث عن الدول/الولايات
        # مثال: كتابة "F" أو "Florida" يبحث مباشرة
        search_text = f"socks:country:{search_text}"
    
    # تسجيل الوصول إلى هنا للتشخيص
    logger.info(f"Processing PremSocks inline query: '{search_text}' (Original: '{query.query}')")
    
    if not premsocks_db.is_service_enabled():
        return
    
    api_key = premsocks_db.get_api_key() or premsocks_db.get_setting('premsocks_api_key')
    if not api_key:
        logger.warning(f"PremSocks API key missing for user {user_id}")
        results = []
        results.append(InlineQueryResultArticle(
            id="no_api_key",
            title="⚠️ خدمة البروكسي غير متوفرة" if language == 'ar' else "⚠️ Proxy Service Unavailable",
            description="يرجى مراجعة المسؤول لضبط الإعدادات" if language == 'ar' else "Please contact admin to set settings",
            input_message_content=InputTextMessageContent(
                message_text="⚠️ عذراً، خدمة البروكسي غير متوفرة حالياً بسبب عدم ضبط الإعدادات. يرجى مراجعة المسؤول."
                if language == 'ar' else
                "⚠️ Sorry, the proxy service is currently unavailable due to missing settings. Please contact the administrator."
            )
        ))
        try:
            await query.answer(
                results, 
                cache_time=30,
                is_personal=True,
                button=InlineQueryResultsButton(
                    text='⚙️ ضبط الإعدادات' if language == 'ar' else '⚙️ Settings',
                    start_parameter='premsocks_admin'
                )
            )
        except Exception as e:
            logger.error(f"Error answering inline query for missing API key: {e}")
        return
    
    api = PremSocksAPI(api_key)
    results = []
    price = premsocks_db.get_proxy_price()
    
    logger.info(f"Handling inline query: {search_text} (original: {query.query}) for user {user_id}")
    
    parts = search_text.split(":")
    # التحقق من أن search_text يحتوي على أجزاء كافية
    if len(parts) < 2:
        mode = "country"
    else:
        mode = parts[1].lower().strip()
    
    # تحويل النص المصفى إلى حروف صغيرة ودعم البحث الجزئي بشكل أفضل
    filter_text = parts[2].strip() if len(parts) > 2 else ""
    search_filter = filter_text.lower()

    # ============ المستوى 1: عرض الدول ============
    if mode == "country" or mode == "" or mode.startswith("country") or mode == "socks":
        search_filter = filter_text.lower() if filter_text else ""
        
        # جلب قائمة الدول من API مع فلتر السرعة التلقائي (سريع أولاً، ثم متوسط)
        try:
            proxy_result = api.get_proxy_list_smart()
            status = proxy_result.get('status')
            data = proxy_result.get('data', [])
            logger.info(f"PremSocks API Raw Result: status={status}, data_type={type(data)}, count={len(data) if isinstance(data, list) else 'N/A'}")
            
            if not status and not data:
                # محاولة ثانية في حال فشل الاتصال المؤقت
                logger.info("Retrying PremSocks API request...")
                proxy_result = api.get_proxy_list_smart()
                status = proxy_result.get('status')
                data = proxy_result.get('data', [])
                logger.info(f"PremSocks API Retry Result: status={status}, count={len(data) if isinstance(data, list) else 'N/A'}")
        except Exception as e:
            logger.error(f"Error fetching proxy list: {e}")
            proxy_result = {'status': False}

        if not proxy_result.get('status') and not proxy_result.get('data'):
            results.append(InlineQueryResultArticle(
                id="api_error",
                title="❌ خطأ في الاتصال" if language == 'ar' else "❌ Connection Error",
                description="فشل جلب البيانات من المزود" if language == 'ar' else "Failed to fetch data from provider",
                input_message_content=InputTextMessageContent(
                    message_text="❌ عذراً، فشل الاتصال بمزود الخدمة حالياً. قد يكون هناك قيود على API أو مفتاح غير صالح."
                    if language == 'ar' else
                    "❌ Sorry, connection to the service provider failed. There might be API limits or an invalid key."
                )
            ))
            try:
                await query.answer(results, cache_time=5, is_personal=True)
            except Exception as e:
                logger.error(f"Error answering inline query for API error: {e}")
            return

        proxies = proxy_result.get('data', [])

        # إضافة مؤشر حالة البحث
        results.append(InlineQueryResultArticle(
            id="ps_search_status_country",
            title="🔍 جاري البحث عن دولة: " + (search_filter if search_filter else "الكل") if language == 'ar' else "🔍 Searching for country: " + (search_filter if search_filter else "All"),
            description="اكتب اسم الدولة لتصفية النتائج" if language == 'ar' else "Type country name to filter",
            input_message_content=InputTextMessageContent(
                message_text="استخدم لوحة البحث لتصفية الدول" if language == 'ar' else "Use search to filter countries"
            )
        ))

        # استخراج الدول الفريدة
        countries = {}
        for proxy in proxies:
            cc = proxy.get('country')
            if not cc or cc == 'XX' or len(str(cc)) != 2:
                continue
            cc = str(cc).upper()
            
            # فلترة الدول بناءً على البحث (اللغة العربية والإنجليزية ورمز الدولة)
            if search_filter:
                country_name_ar = get_country_name(cc, 'ar').lower()
                country_name_en = get_country_name(cc, 'en').lower()
                if not (search_filter in country_name_ar or search_filter in country_name_en or search_filter in cc.lower()):
                    continue
                    
            if cc not in countries:
                countries[cc] = 0
            countries[cc] += 1
        
        logger.info(f"Filtered countries for query '{search_filter}': {len(countries)} found")
        
        # إذا لم تكن هناك دول متاحة
        if not countries:
            logger.info(f"No countries found for filter: '{search_filter}'")
            if language == 'ar':
                desc_text = f"لا توجد دول تطابق '{search_filter}'" if search_filter else "لا توجد بروكسيات متاحة حالياً"
                msg_text = "⚠️ عذراً، لا توجد دول متاحة حالياً تطابق بحثك."
            else:
                desc_text = f"No countries matching '{search_filter}'" if search_filter else "No proxies available currently"
                msg_text = "⚠️ Sorry, no countries currently available matching your search."
            results.append(InlineQueryResultArticle(
                id="no_countries_available",
                title="⚠️ لا توجد نتائج" if language == 'ar' else "⚠️ No Results",
                description=desc_text,
                input_message_content=InputTextMessageContent(
                    message_text=msg_text
                )
            ))
            try:
                await query.answer(results, cache_time=5, is_personal=True)
            except Exception as e:
                logger.error(f"Error answering empty countries list: {e}")
            return
        if not countries:
            results.append(InlineQueryResultArticle(
                id="no_proxies_available",
                title="⚠️ لا توجد بروكسيات متاحة" if language == 'ar' else "⚠️ No Proxies Available",
                description="نعتذر، لا توجد بروكسيات متوفرة في الوقت الحالي" if language == 'ar' else "Sorry, no proxies are currently available",
                input_message_content=InputTextMessageContent(
                    message_text="⚠️ نعتذر، لا توجد بروكسيات متوفرة حالياً." if language == 'ar' else "⚠️ Sorry, no proxies are currently available."
                )
            ))
            try:
                await query.answer(results, cache_time=30, is_personal=True)
            except Exception as e:
                logger.error(f"Error answering empty country list: {e}")
            return

        # فلترة بالبحث
        for cc, count in sorted(countries.items(), key=lambda x: x[1], reverse=True):
            country_name_ar = get_country_name(cc, 'ar')
            country_name_en = get_country_name(cc, 'en')
            flag = get_country_flag_premsocks(cc)

            country_name = country_name_ar if language == 'ar' else country_name_en
            title = f"{flag} {country_name}"
            description = (
                f"📊 {count} بروكسي متاح | 💵 {price} كريديت"
                if language == 'ar' else
                f"📊 {count} proxies available | 💵 {price} credits"
            )

            # رسالة بعد الاختيار مع أزرار المتابعة
            if language == 'ar':
                message_text = f"""
🌍 <b>تم اختيار الدولة</b>

{flag} <b>{country_name}</b> ({cc})
📊 عدد البروكسيات المتاحة: {count}
💵 السعر: {price} كريديت

<b>الخطوة التالية:</b> اختر ولاية أو اشترِ مباشرة
"""
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛒 شراء سريع (عشوائي)", callback_data=f"ps_buy_random_{cc}___")],
                    [InlineKeyboardButton("📍 اختيار ولاية ←", switch_inline_query_current_chat=f"socks:state:{cc} ")],
                    [InlineKeyboardButton("⏭️ تخطي الولاية", callback_data=f"ps_skip_state_{cc}")]
                ])
            else:
                message_text = f"""
🌍 <b>Country Selected</b>

{flag} <b>{country_name}</b> ({cc})
📊 Available proxies: {count}
💵 Price: {price} Credits

<b>Next Step:</b> Select a state or buy directly
"""
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛒 Quick Buy (Random)", callback_data=f"ps_buy_random_{cc}___")],
                    [InlineKeyboardButton("📍 Select State ←", switch_inline_query_current_chat=f"socks:state:{cc} ")],
                    [InlineKeyboardButton("⏭️ Skip State", callback_data=f"ps_skip_state_{cc}")]
                ])

            results.append(InlineQueryResultArticle(
                id=f"country_{cc}",
                title=title,
                description=description,
                input_message_content=InputTextMessageContent(
                    message_text=message_text,
                    parse_mode='HTML'
                ),
                reply_markup=keyboard
            ))

            if len(results) >= 50:
                break

    # ============ المستوى 2: عرض الولايات ============
    elif mode == "state" or mode.startswith("state"):
        country_code = parts[2].strip().split()[0].upper() if len(parts) > 2 else ""
        # استخراج البحث من بقية الجزء الثاني أو من الجزء الثالث
        search_filter = ""
        if len(parts) > 2:
            sub_parts = parts[2].strip().split(None, 1)
            if len(sub_parts) > 1:
                search_filter = sub_parts[1].lower()
        
        if not search_filter and len(parts) > 3:
            search_filter = parts[3].strip().lower()

        if not country_code:
            logger.error("Missing country_code in state mode")
            return

        results.append(InlineQueryResultArticle(
            id="ps_search_status_state",
            title="🔍 جاري البحث في الولايات عن: " + (search_filter if search_filter else "الكل") if language == 'ar' else "🔍 Searching states for: " + (search_filter if search_filter else "All"),
            description="اكتب لتصفية الولايات" if language == 'ar' else "Type to filter states",
            input_message_content=InputTextMessageContent(
                message_text="استخدم لوحة البحث لتصفية الولايات" if language == 'ar' else "Use search to filter states"
            )
        ))

        proxy_result = api.get_proxy_list_smart(country=country_code)
        if not proxy_result.get('status') and not proxy_result.get('data'):
            results.append(InlineQueryResultArticle(
                id="api_error_state",
                title="❌ خطأ في الاتصال" if language == 'ar' else "❌ Connection Error",
                description="فشل جلب البيانات من المزود" if language == 'ar' else "Failed to fetch data from provider",
                input_message_content=InputTextMessageContent(
                    message_text="❌ عذراً، فشل الاتصال بمزود الخدمة حالياً." if language == 'ar' else "❌ Sorry, connection to the service provider failed."
                )
            ))
            try:
                await query.answer(results, cache_time=5, is_personal=True)
            except Exception as e:
                logger.error(f"Error answering state API error: {e}")
            return

        proxies = proxy_result.get('data', [])

        # استخراج الولايات الفريدة
        states = {}
        for proxy in proxies:
            state = proxy.get('state', 'Unknown')
            if state and state != 'Unknown':
                # تصفية حسب البحث (إذا وجد) في مستوى الولايات
                if search_filter:
                    if search_filter not in str(state).lower():
                        continue
                if state not in states:
                    states[state] = 0
                states[state] += 1

        if not states:
            logger.info(f"No states found for country {country_code} with filter: '{search_filter}'")
            results.append(InlineQueryResultArticle(
                id="no_states_available",
                title="⚠️ لا توجد ولايات" if language == 'ar' else "⚠️ No States",
                description=f"لا توجد نتائج تطابق '{search_filter}'" if search_filter else "لا توجد ولايات متاحة",
                input_message_content=InputTextMessageContent(
                    message_text=f"⚠️ عذراً، لا توجد ولايات متاحة حالياً تطابق بحثك في هذه الدولة."
                )
            ))
            try:
                await query.answer(results, cache_time=5, is_personal=True)
            except Exception as e:
                logger.error(f"Error answering empty states list: {e}")
            return

        country_name = get_country_name(country_code, language)
        flag = get_country_flag_premsocks(country_code)

        for state, count in sorted(states.items(), key=lambda x: x[1], reverse=True):
            title = f"📍 {state}"
            description = (
                f"{flag} {country_name} | {count} بروكسي"
                if language == 'ar' else
                f"{flag} {country_name} | {count} proxies"
            )

            # ترميز الولاية للـ callback
            state_encoded = state.replace(" ", "_").replace(",", "")[:20]

            # رسالة بعد الاختيار مع أزرار المتابعة
            if language == 'ar':
                message_text = f"""
📍 <b>تم اختيار الولاية</b>

{flag} <b>{country_name}</b>
📍 الولاية: <b>{state}</b>
📊 عدد البروكسيات: {count}
💵 السعر: {price} كريديت

<b>الخطوة التالية:</b> اختر مدينة أو اشترِ مباشرة
"""
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛒 شراء سريع", callback_data=f"ps_buy_random_{country_code}_{state_encoded}__")],
                    [InlineKeyboardButton("🏙️ اختيار مدينة ←", switch_inline_query_current_chat=f"socks:city:{country_code}:{state_encoded} ")],
                    [InlineKeyboardButton("⏭️ تخطي المدينة", callback_data=f"ps_skip_city_{country_code}_{state_encoded}")]
                ])
            else:
                message_text = f"""
📍 <b>State Selected</b>

{flag} <b>{country_name}</b>
📍 State: <b>{state}</b>
📊 Proxies: {count}
💵 Price: {price} Credits

<b>Next Step:</b> Select a city or buy directly
"""
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛒 Quick Buy", callback_data=f"ps_buy_random_{country_code}_{state_encoded}__")],
                    [InlineKeyboardButton("🏙️ Select City ←", switch_inline_query_current_chat=f"socks:city:{country_code}:{state_encoded} ")],
                    [InlineKeyboardButton("⏭️ Skip City", callback_data=f"ps_skip_city_{country_code}_{state_encoded}")]
                ])

            results.append(InlineQueryResultArticle(
                id=f"state_{country_code}_{state_encoded}",
                title=title,
                description=description,
                input_message_content=InputTextMessageContent(
                    message_text=message_text,
                    parse_mode='HTML'
                ),
                reply_markup=keyboard
            ))

            if len(results) >= 50:
                break

    # ============ المستوى 3: عرض المدن ============
    elif mode == "city" or mode.startswith("city"):
        country_code = parts[2].strip().upper() if len(parts) > 2 else ""
        state_raw = parts[3].strip() if len(parts) > 3 else ""
        state_name = state_raw.split()[0].replace("_", " ") if state_raw else ""
        
        # استخراج البحث من بقية الجزء الثالث أو من الجزء الرابع
        search_filter = ""
        if state_raw:
            sub_parts = state_raw.split(None, 1)
            if len(sub_parts) > 1:
                search_filter = sub_parts[1].lower()
            
        if not search_filter and len(parts) > 4:
            search_filter = parts[4].strip().lower()

        if not country_code:
            logger.error("Missing country_code in city mode")
            return

        results.append(InlineQueryResultArticle(
            id="ps_search_status_city",
            title="🔍 جاري البحث في المدن عن: " + (search_filter if search_filter else "الكل") if language == 'ar' else "🔍 Searching cities for: " + (search_filter if search_filter else "All"),
            description="اكتب لتصفية المدن" if language == 'ar' else "Type to filter cities",
            input_message_content=InputTextMessageContent(
                message_text="استخدم لوحة البحث لتصفية المدن" if language == 'ar' else "Use search to filter cities"
            )
        ))

        proxy_result = api.get_proxy_list_smart(country=country_code, state=state_name if state_name else None)
        if not proxy_result.get('status') and not proxy_result.get('data'):
            results.append(InlineQueryResultArticle(
                id="api_error_city",
                title="❌ خطأ في الاتصال" if language == 'ar' else "❌ Connection Error",
                description="فشل جلب البيانات من المزود" if language == 'ar' else "Failed to fetch data from provider",
                input_message_content=InputTextMessageContent(
                    message_text="❌ عذراً، فشل الاتصال بمزود الخدمة حالياً." if language == 'ar' else "❌ Sorry, connection to the service provider failed."
                )
            ))
            try:
                await query.answer(results, cache_time=5, is_personal=True)
            except Exception as e:
                logger.error(f"Error answering city API error: {e}")
            return

        proxies = proxy_result.get('data', [])

        # استخراج المدن الفريدة
        cities = {}
        for proxy in proxies:
            city = proxy.get('city', 'Unknown')
            if city and city != 'Unknown':
                # تصفية حسب البحث (إذا وجد) في مستوى المدن
                if search_filter:
                    if search_filter not in str(city).lower():
                        continue
                if city not in cities:
                    cities[city] = 0
                cities[city] += 1

        if not cities:
            logger.info(f"No cities found for {country_code}/{state_name} with filter: '{search_filter}'")
            results.append(InlineQueryResultArticle(
                id="no_cities_available",
                title="⚠️ لا توجد مدن" if language == 'ar' else "⚠️ No Cities",
                description=f"لا توجد نتائج تطابق '{search_filter}'" if search_filter else "لا توجد مدن متاحة",
                input_message_content=InputTextMessageContent(
                    message_text=f"⚠️ عذراً، لا توجد مدن متاحة حالياً تطابق بحثك في هذا الموقع."
                )
            ))
            try:
                await query.answer(results, cache_time=5, is_personal=True)
            except Exception as e:
                logger.error(f"Error answering empty cities list: {e}")
            return

        country_name = get_country_name(country_code, language)
        flag = get_country_flag_premsocks(country_code)
        state_encoded = state_name.replace(" ", "_").replace(",", "")[:20]

        for city, count in sorted(cities.items(), key=lambda x: x[1], reverse=True):
            title = f"🏙️ {city}"
            description = (
                f"{flag} {state_name or country_name} | {count} بروكسي"
                if language == 'ar' else
                f"{flag} {state_name or country_name} | {count} proxies"
            )

            city_encoded = city.replace(" ", "_").replace(",", "")[:20]

            # رسالة بعد الاختيار مع أزرار المتابعة
            if language == 'ar':
                message_text = f"""
🏙️ <b>تم اختيار المدينة</b>

{flag} <b>{country_name}</b>
📍 الولاية: {state_name or 'غير محدد'}
🏙️ المدينة: <b>{city}</b>
📊 عدد البروكسيات: {count}
💵 السعر: {price} كريديت

<b>الخطوة التالية:</b> اختر مزود الخدمة أو اشترِ مباشرة
"""
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛒 شراء سريع", callback_data=f"ps_buy_random_{country_code}_{state_encoded}_{city_encoded}_")],
                    [InlineKeyboardButton("🌐 اختيار مزود ←", switch_inline_query_current_chat=f"socks:isp:{country_code}:{state_encoded}:{city_encoded} ")],
                    [InlineKeyboardButton("⏭️ تخطي المزود (شراء)", callback_data=f"ps_buy_random_{country_code}_{state_encoded}_{city_encoded}_")]
                ])
            else:
                message_text = f"""
🏙️ <b>City Selected</b>

{flag} <b>{country_name}</b>
📍 State: {state_name or 'Not specified'}
🏙️ City: <b>{city}</b>
📊 Proxies: {count}
💵 Price: {price} Credits

<b>Next Step:</b> Select an ISP or buy directly
"""
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛒 Quick Buy", callback_data=f"ps_buy_random_{country_code}_{state_encoded}_{city_encoded}_")],
                    [InlineKeyboardButton("🌐 Select ISP ←", switch_inline_query_current_chat=f"socks:isp:{country_code}:{state_encoded}:{city_encoded} ")],
                    [InlineKeyboardButton("⏭️ Skip ISP (Buy)", callback_data=f"ps_buy_random_{country_code}_{state_encoded}_{city_encoded}_")]
                ])

            results.append(InlineQueryResultArticle(
                id=f"city_{country_code}_{city_encoded}",
                title=title,
                description=description,
                input_message_content=InputTextMessageContent(
                    message_text=message_text,
                    parse_mode='HTML'
                ),
                reply_markup=keyboard
            ))

            if len(results) >= 50:
                break

    # ============ المستوى 4: عرض المزودين ============
    elif mode == "isp" or mode.startswith("isp"):
        country_code = parts[2].strip().upper() if len(parts) > 2 else ""
        state_name = parts[3].strip().replace("_", " ") if len(parts) > 3 else ""
        city_raw = parts[4].strip() if len(parts) > 4 else ""
        city_name = city_raw.split()[0].replace("_", " ") if city_raw else ""
        
        # استخراج البحث من بقية الجزء الرابع أو من الجزء الخامس
        search_filter = ""
        if city_raw:
            sub_parts = city_raw.split(None, 1)
            if len(sub_parts) > 1:
                search_filter = sub_parts[1].lower()
            
        if not search_filter and len(parts) > 5:
            search_filter = parts[5].strip().lower()

        if not country_code:
            logger.error("Missing country_code in isp mode")
            return

        results.append(InlineQueryResultArticle(
            id="ps_search_status_isp",
            title="🔍 جاري البحث في المزودين عن: " + (search_filter if search_filter else "الكل") if language == 'ar' else "🔍 Searching ISPs for: " + (search_filter if search_filter else "All"),
            description="اكتب لتصفية المزودين" if language == 'ar' else "Type to filter ISPs",
            input_message_content=InputTextMessageContent(
                message_text="استخدم لوحة البحث لتصفية المزودين" if language == 'ar' else "Use search to filter ISPs"
            )
        ))

        try:
            proxy_result = api.get_proxy_list_smart(
                country=country_code,
                state=state_name if state_name and state_name.lower() != 'any' else None,
                city=city_name if city_name and city_name.lower() != 'any' else None
            )
        except Exception as e:
            logger.error(f"Error fetching proxy list for ISP: {e}")
            proxy_result = {'status': False}

        if not proxy_result.get('status'):
            results.append(InlineQueryResultArticle(
                id="api_error_isp",
                title="❌ خطأ في الاتصال" if language == 'ar' else "❌ Connection Error",
                description="فشل جلب البيانات من المزود" if language == 'ar' else "Failed to fetch data from provider",
                input_message_content=InputTextMessageContent(
                    message_text="❌ عذراً، فشل الاتصال بمزود الخدمة حالياً." if language == 'ar' else "❌ Sorry, connection to the service provider failed."
                )
            ))
            try:
                await query.answer(results, cache_time=5, is_personal=True)
            except Exception as e:
                logger.error(f"Error answering isp API error: {e}")
            return

        proxies = proxy_result.get('data', [])

        # استخراج المزودين الفريدين
        isps = {}
        for proxy in proxies:
            isp = proxy.get('isp', 'Unknown')
            if isp and isp != 'Unknown':
                if isp not in isps:
                    isps[isp] = {'count': 0, 'sample_id': proxy.get('id')}
                isps[isp]['count'] += 1

        country_name = get_country_name(country_code, language)
        flag = get_country_flag_premsocks(country_code)
        state_encoded = state_name.replace(" ", "_").replace(",", "")[:20]
        city_encoded = city_name.replace(" ", "_").replace(",", "")[:20]

        for isp, data in sorted(isps.items(), key=lambda x: x[1]['count'], reverse=True):
            if search_filter and search_filter not in isp.lower():
                continue

            title = f"🌐 {isp}"
            description = (
                f"{flag} {city_name or state_name or country_name} | {data['count']} بروكسي"
                if language == 'ar' else
                f"{flag} {city_name or state_name or country_name} | {data['count']} proxies"
            )

            # رسالة بعد الاختيار مع أزرار المتابعة
            if language == 'ar':
                message_text = f"""
🌐 <b>تم اختيار المزود</b>

{flag} <b>{country_name}</b>
📍 الولاية: {state_name or 'أي ولاية'}
🏙️ المدينة: {city_name or 'أي مدينة'}
🌐 المزود: <b>{isp}</b>
📊 عدد البروكسيات: {data['count']}
💵 السعر: {price} كريديت

اضغط للشراء الآن 👇
"""
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛒 شراء الآن", callback_data=f"ps_buy_random_{country_code}_{state_encoded}_{city_encoded}_{isp_encoded}")]
                ])
            else:
                message_text = f"""
🌐 <b>ISP Selected</b>

{flag} <b>{country_name}</b>
📍 State: {state_name or 'Any State'}
🏙️ City: {city_name or 'Any City'}
🌐 ISP: <b>{isp}</b>
📊 Proxies: {data['count']}
💵 Price: {price} Credits

Click to buy now 👇
"""
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛒 Buy Now", callback_data=f"ps_buy_random_{country_code}_{state_encoded}_{city_encoded}_{isp_encoded}")]
                ])

            results.append(InlineQueryResultArticle(
                id=f"isp_{country_code}_{isp_encoded}",
                title=title,
                description=description,
                input_message_content=InputTextMessageContent(
                    message_text=message_text,
                    parse_mode='HTML'
                ),
                reply_markup=keyboard
            ))

            if len(results) >= 50:
                break
    
    # رسالة في حال عدم وجود نتائج
    if not results:
        results.append(InlineQueryResultArticle(
            id="no_results",
            title="❌ لا توجد نتائج" if language == 'ar' else "❌ No Results",
            description="جرب البحث بكلمات مختلفة" if language == 'ar' else "Try searching with different keywords",
            input_message_content=InputTextMessageContent(
                message_text="❌ لا توجد نتائج متاحة حالياً" if language == 'ar' else "❌ No results currently available"
            )
        ))
    
    await query.answer(results, cache_time=30)
