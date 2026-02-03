#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================
خدمة Luxury Support - Daily Static Proxy Service
============================================
هذا الملف يجمع جميع وظائف خدمة Luxury Support في مكان واحد:
- LuxuryAPI: التعامل مع API
- LuxuryDB: إدارة قاعدة البيانات
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

API_BASE = "http://165.22.199.159:3536/api/v1"
DATABASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "proxy_bot.db")

PRODUCTS_CACHE = {
    'proxies': [],
    'countries': {},
    'last_update': 0,
    'cache_duration': 120
}

ERROR_CODES_LUXURY = {
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
    'VN': {'ar': 'فيتنام', 'en': 'Vietnam'},
    'PL': {'ar': 'بولندا', 'en': 'Poland'},
    'TR': {'ar': 'تركيا', 'en': 'Turkey'},
    'MX': {'ar': 'المكسيك', 'en': 'Mexico'},
    'AR': {'ar': 'الأرجنتين', 'en': 'Argentina'},
    'AT': {'ar': 'النمسا', 'en': 'Austria'},
    'CH': {'ar': 'سويسرا', 'en': 'Switzerland'},
    'BE': {'ar': 'بلجيكا', 'en': 'Belgium'},
    'PT': {'ar': 'البرتغال', 'en': 'Portugal'},
    'GR': {'ar': 'اليونان', 'en': 'Greece'},
    'RO': {'ar': 'رومانيا', 'en': 'Romania'},
    'HU': {'ar': 'المجر', 'en': 'Hungary'},
    'CZ': {'ar': 'التشيك', 'en': 'Czech Republic'},
    'UA': {'ar': 'أوكرانيا', 'en': 'Ukraine'},
    'FI': {'ar': 'فنلندا', 'en': 'Finland'},
    'DK': {'ar': 'الدنمارك', 'en': 'Denmark'},
    'IE': {'ar': 'أيرلندا', 'en': 'Ireland'},
    'NZ': {'ar': 'نيوزيلندا', 'en': 'New Zealand'},
    'SG': {'ar': 'سنغافورة', 'en': 'Singapore'},
    'TH': {'ar': 'تايلاند', 'en': 'Thailand'},
    'MY': {'ar': 'ماليزيا', 'en': 'Malaysia'},
    'PH': {'ar': 'الفلبين', 'en': 'Philippines'},
    'ID': {'ar': 'إندونيسيا', 'en': 'Indonesia'},
    'EG': {'ar': 'مصر', 'en': 'Egypt'},
    'SA': {'ar': 'السعودية', 'en': 'Saudi Arabia'},
    'AE': {'ar': 'الإمارات', 'en': 'UAE'},
    'IL': {'ar': 'إسرائيل', 'en': 'Israel'},
    'PK': {'ar': 'باكستان', 'en': 'Pakistan'},
    'BD': {'ar': 'بنغلاديش', 'en': 'Bangladesh'},
    'CO': {'ar': 'كولومبيا', 'en': 'Colombia'},
    'CL': {'ar': 'تشيلي', 'en': 'Chile'},
    'PE': {'ar': 'بيرو', 'en': 'Peru'},
    'VE': {'ar': 'فنزويلا', 'en': 'Venezuela'}
}


def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE, timeout=10.0)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def get_country_flag_luxury(country_code: str) -> str:
    return COUNTRY_FLAGS.get(country_code.upper(), '🌍')


def get_country_name(country_code: str, language: str = 'ar') -> str:
    country_data = COUNTRY_NAMES.get(country_code.upper(), {})
    return country_data.get(language, country_code)


def log_api_error_luxury(error_code: str, actual_error: str, context: str = ""):
    logger.error(f"[Luxury {error_code}] {ERROR_CODES_LUXURY.get(error_code, 'خطأ غير معروف')} | الخطأ الفعلي: {actual_error} | السياق: {context}")


def get_error_code_from_luxury(error_code: int, error_message: str = "") -> str:
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


class LuxuryAPI:
    """كلاس التعامل مع Luxury Support API"""
    
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
    
    def _make_request(self, method: str, endpoint: str, params: Dict = None, json_data: Dict = None) -> Dict:
        if not self.api_key:
            return {'status': False, 'error_code': 401, 'error_message': 'API key not set'}
        
        url = f"{API_BASE}{endpoint}"
        try:
            if method == 'GET':
                response = self.session.get(url, headers=self._get_headers(), params=params, timeout=self.timeout)
            else:
                response = self.session.post(url, headers=self._get_headers(), json=json_data, timeout=self.timeout)
            
            if response.status_code == 429:
                return {'status': False, 'error_code': 429, 'error_message': 'Rate limit exceeded'}
            elif response.status_code == 401:
                return {'status': False, 'error_code': 401, 'error_message': 'Unauthorized'}
            elif response.status_code == 503:
                return {'status': False, 'error_code': 503, 'error_message': 'Service unavailable'}
            
            return response.json()
        except requests.exceptions.Timeout:
            log_api_error_luxury('x0x0004', 'Request timeout', endpoint)
            return {'status': False, 'error_code': 0, 'error_message': 'Timeout'}
        except requests.exceptions.RequestException as e:
            log_api_error_luxury('x0x0002', str(e), endpoint)
            return {'status': False, 'error_code': 0, 'error_message': str(e)}
        except Exception as e:
            log_api_error_luxury('x0x0009', str(e), endpoint)
            return {'status': False, 'error_code': 0, 'error_message': str(e)}
    
    def get_balance(self) -> Dict:
        """جلب رصيد الحساب"""
        return self._make_request('GET', '/socks/balance')
    
    def get_proxy_counts(self) -> Dict:
        """جلب عدد البروكسيات حسب القارة"""
        return self._make_request('GET', '/socks/proxy')
    
    def get_country_list(self) -> Dict:
        """جلب قائمة الدول المتاحة"""
        return self._make_request('GET', '/socks/list_country')
    
    def get_state_list(self) -> Dict:
        """جلب قائمة الولايات المتاحة"""
        return self._make_request('GET', '/socks/list_state')
    
    def get_city_list(self) -> Dict:
        """جلب قائمة المدن المتاحة"""
        return self._make_request('GET', '/socks/list_city')
    
    def get_isp_list(self) -> Dict:
        """جلب قائمة مزودي الخدمة"""
        return self._make_request('GET', '/socks/list_isp')
    
    def search_proxies(self, country_code: str = None, state: str = None, 
                       city: str = None, isp: str = None, zip_code: str = None,
                       limit: int = 10, page: int = 0) -> Dict:
        """البحث عن بروكسيات"""
        params = {'limit': limit, 'page': page}
        if country_code:
            params['country_code'] = country_code
        if state:
            params['state'] = state
        if city:
            params['city'] = city
        if isp:
            params['isp'] = isp
        if zip_code:
            params['zip_code'] = zip_code
        
        return self._make_request('GET', '/socks/search', params)
    
    def search_proxies_v2(self, country_code: str = None, state: str = None, 
                          city: str = None, isp: str = None, zip_code: str = None,
                          limit: int = 10, page: int = 1, proxy_id: str = None) -> Dict:
        """البحث عن بروكسيات - النسخة الثانية"""
        params = {'limit': limit, 'page': page}
        if country_code:
            params['country_code'] = country_code
        if state:
            params['state'] = state
        if city:
            params['city'] = city
        if isp:
            params['isp'] = isp
        if zip_code:
            params['zip_code'] = zip_code
        if proxy_id:
            params['proxy_id'] = proxy_id
        
        return self._make_request('GET', '/socks/v2/search', params)
    
    def search_proxies_v3(self, country_code: str = None, state: str = None,
                          city: str = None, isp: str = None, zip_code: str = None) -> Dict:
        """البحث عن بروكسيات - النسخة الثالثة"""
        params = {}
        if country_code:
            params['country_code'] = country_code
        if state:
            params['state'] = state
        if city:
            params['city'] = city
        if isp:
            params['isp'] = isp
        if zip_code:
            params['zip_code'] = zip_code
        
        return self._make_request('GET', '/socks/v3/search', params)
    
    def get_states_by_country(self, country_code: str) -> Dict:
        """جلب الولايات حسب الدولة"""
        params = {'country_code': country_code} if country_code else {}
        return self._make_request('GET', '/socks/v2/mapp_country', params)
    
    def get_cities_by_state(self, state: str) -> Dict:
        """جلب المدن حسب الولاية"""
        params = {'state': state} if state else {}
        return self._make_request('GET', '/socks/v2/mapp_state', params)
    
    def get_isps_by_city(self, city: str) -> Dict:
        """جلب مزودي الخدمة حسب المدينة"""
        params = {'city': city} if city else {}
        return self._make_request('GET', '/socks/v2/mapp_city', params)
    
    def check_ip(self, proxy_id: str) -> Dict:
        """فحص حالة البروكسي"""
        params = {'proxy_id': proxy_id}
        return self._make_request('GET', '/socks/check_ip', params)
    
    def buy_proxy(self, proxy_id: str, daily_buy: bool = True) -> Dict:
        """
        شراء بروكسي
        daily_buy=True: بروكسي 24 ساعة مع إمكانية تغيير IP
        daily_buy=False: بروكسي 4 ساعات بدون تغيير IP
        """
        json_data = {
            'proxy_id': proxy_id,
            'daily_buy': daily_buy
        }
        return self._make_request('POST', '/socks/buy', json_data=json_data)
    
    def refund_proxy(self, record_id: int) -> Dict:
        """استرداد بروكسي"""
        json_data = {'record_id': record_id}
        return self._make_request('POST', '/socks/refund', json_data=json_data)
    
    def get_user_records(self, limit: int = 10, page: int = 0, **filters) -> Dict:
        """جلب سجلات المستخدم"""
        params = {'limit': limit, 'page': page}
        params.update(filters)
        return self._make_request('GET', '/socks/records_by_user', params)
    
    def check_proxy_socket(self, ip: str, port: int, timeout: int = 10) -> bool:
        """فحص اتصال البروكسي عبر socket"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except:
            return False


class LuxuryDB:
    """إدارة قاعدة البيانات لخدمة Luxury"""
    
    def __init__(self):
        self.init_tables()
    
    def init_tables(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS luxury_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS luxury_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                proxy_id TEXT NOT NULL,
                record_id INTEGER,
                ip TEXT NOT NULL,
                port INTEGER NOT NULL,
                country TEXT,
                city TEXT,
                state TEXT,
                isp TEXT,
                price REAL NOT NULL,
                daily_buy BOOLEAN DEFAULT TRUE,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_luxury_user_id 
            ON luxury_purchases(user_id)
        ''')
        
        conn.commit()
        conn.close()
        logger.info("تم تهيئة جداول Luxury Support")
    
    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM luxury_settings WHERE key = ?', (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else default
    
    def set_setting(self, key: str, value: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO luxury_settings (key, value) VALUES (?, ?)
        ''', (key, value))
        conn.commit()
        conn.close()
    
    def is_service_enabled(self) -> bool:
        """تحقق من حالة الخدمة في الإعدادات"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM luxury_settings WHERE key = 'service_enabled'")
        row = cursor.fetchone()
        conn.close()
        if row is None:
            return True
        return row[0] == '1'
    
    def get_proxy_price(self, daily: bool = True) -> float:
        """الحصول على سعر البروكسي بالدولار - يومي أو ساعي"""
        if daily:
            return float(self.get_setting('proxy_price_daily', self.get_setting('proxy_price', '0.15')))
        else:
            return float(self.get_setting('proxy_price_hourly', '0.08'))
    
    def set_proxy_price(self, price: float, daily: bool = True) -> None:
        """تعيين سعر البروكسي بالدولار - يومي أو ساعي"""
        if daily:
            self.set_setting('proxy_price_daily', str(price))
        else:
            self.set_setting('proxy_price_hourly', str(price))
    
    def get_api_cost(self, daily: bool = True) -> float:
        """الحصول على تكلفة البروكسي في الموقع (API) - يومي أو ساعي"""
        if daily:
            return float(self.get_setting('api_cost_daily', '0.10'))
        else:
            return float(self.get_setting('api_cost_hourly', '0.05'))
    
    def set_api_cost(self, cost: float, daily: bool = True) -> None:
        """تعيين تكلفة البروكسي في الموقع (API) - يومي أو ساعي"""
        if daily:
            self.set_setting('api_cost_daily', str(cost))
        else:
            self.set_setting('api_cost_hourly', str(cost))
    
    def get_api_key(self) -> Optional[str]:
        return self.get_setting('luxury_api_key')
    
    def save_purchase(self, user_id: int, proxy_data: Dict, price: float, daily_buy: bool = True) -> int:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        expires_hours = 24 if daily_buy else 4
        expires_at = datetime.now() + timedelta(hours=expires_hours)
        
        cursor.execute('''
            INSERT INTO luxury_purchases 
            (user_id, proxy_id, record_id, ip, port, country, city, state, isp, price, daily_buy, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            proxy_data.get('proxy_id', proxy_data.get('id', '')),
            proxy_data.get('record_id', 0),
            proxy_data.get('real_ip', proxy_data.get('ip', '')),
            proxy_data.get('port', 0),
            proxy_data.get('country_code', proxy_data.get('country', '')),
            proxy_data.get('city', ''),
            proxy_data.get('state', ''),
            proxy_data.get('isp', ''),
            price,
            daily_buy,
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
            SELECT id, proxy_id, record_id, ip, port, country, city, state, isp, price, 
                   daily_buy, purchased_at, expires_at
            FROM luxury_purchases
            WHERE user_id = ?
            ORDER BY purchased_at DESC
            LIMIT ?
        ''', (user_id, limit))
        
        columns = ['id', 'proxy_id', 'record_id', 'ip', 'port', 'country', 'city', 'state', 
                   'isp', 'price', 'daily_buy', 'purchased_at', 'expires_at']
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_active_proxies(self, user_id: int) -> List[Dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, proxy_id, record_id, ip, port, country, city, state, isp, price, 
                   daily_buy, purchased_at, expires_at
            FROM luxury_purchases
            WHERE user_id = ? AND expires_at > datetime('now')
            ORDER BY purchased_at DESC
        ''', (user_id,))
        
        columns = ['id', 'proxy_id', 'record_id', 'ip', 'port', 'country', 'city', 'state', 
                   'isp', 'price', 'daily_buy', 'purchased_at', 'expires_at']
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def delete_purchase(self, purchase_id: int) -> bool:
        """حذف عملية شراء بعد الاسترداد"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM luxury_purchases WHERE id = ?', (purchase_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error deleting purchase: {e}")
            return False


LUXURY_MESSAGES = {
    'ar': {
        'menu_title': '🌐 ستاتيك يومي',
        'menu_desc': 'احصل على بروكسي ستاتيك عالي الجودة',
        'buy_proxy': '🛒 شراء بروكسي',
        'my_proxies': '📦 بروكسياتي',
        'back': '🔙 رجوع',
        'select_country': '🌍 اختر الدولة',
        'random_proxy': '🎲 شراء بروكسي عشوائي',
        'search_proxy': '🔍 بحث متقدم',
        'select_city': '🏙️ اختر المدينة:',
        'select_state': '📍 اختر الولاية:',
        'search_placeholder': 'اكتب للبحث...',
        'confirm_purchase': '✅ تأكيد الشراء',
        'cancel': '❌ إلغاء',
        'purchase_confirm_msg': '''
<b>تأكيد الشراء</b>

الدولة: {country}
المدينة: {city}
الولاية: {state}

السعر: <code>{price}</code> كريديت
رصيدك: <code>{balance}</code> كريديت

هل تريد المتابعة؟
''',
        'purchase_success': '''
<b>{purchase_success_title}</b>

<b>{proxy_details_title}</b>
━━━━━━━━━━━━━━━
IP: <code>{ip}</code>
Port: <code>{port}</code>
━━━━━━━━━━━━━━━

{country_label}: {country}
{city_label}: {city}
{state_label}: {state}
{valid_for_label}: {valid_duration}

{check_hint}
''',
        'purchase_success_title': 'تمت عملية الشراء بنجاح!',
        'proxy_details_title': 'تفاصيل البروكسي:',
        'valid_for_label': 'صالح لمدة',
        'valid_duration_24h': '24 ساعة',
        'valid_duration_4h': '4 ساعات',
        'check_hint': 'استخدم زر "فحص" للتحقق من حالة البروكسي',
        'insufficient_balance': 'رصيدك غير كافٍ!\n\nرصيدك الحالي: {balance} كريديت\nالمبلغ المطلوب: {required} كريديت',
        'admin_balance_low': 'عذراً، الخدمة غير متاحة حالياً.\n\nرمز الخطأ: x0x0000',
        'no_proxies': 'لا توجد لديك بروكسيات نشطة حالياً',
        'proxy_expired': 'انتهت صلاحية هذا البروكسي',
        'check_status': '🔄 فحص',
        'proxy_online': '✅ البروكسي يعمل\nالدولة: {country}',
        'proxy_offline': '❌ البروكسي لا يعمل حالياً',
        'refund': '💰 استرداد',
        'refund_success': '✅ تم استرداد {amount} كريديت بنجاح!',
        'refund_failed': '❌ فشل الاسترداد. قد يكون البروكسي غير قابل للاسترداد.',
        'refund_confirm': '⚠️ هل أنت متأكد من استرداد هذا البروكسي؟\n\nسيتم إعادة {amount} كريديت لرصيدك.',
        'refund_confirm_btn': '✅ تأكيد الاسترداد',
        'service_disabled': '🚫 هذه الخدمة متوقفة مؤقتاً\n\nرمز الخطأ: x0x000A',
        'error_occurred': '⚠️ حدث خطأ\n\nرمز الخطأ: {code}',
        'no_results': '📭 لا توجد نتائج متاحة',
        'loading': '⏳ جاري التحميل...',
        'inline_title': '🔍 بحث بروكسي ستاتيك',
        'inline_desc': 'اكتب اسم الدولة أو المدينة للبحث',
        'proxy_info': '{country} | {city}',
        'buy_menu_text': '''
<b>🛒 شراء بروكسي ستاتيك</b>

اضغط على زر البحث أدناه لتصفح البروكسيات المتاحة حسب الدولة والولاية والمدينة.

💵 السعر: {price} كريديت لكل بروكسي
''',
        'daily_proxy': '📅 بروكسي يومي (24 ساعة)',
        'hourly_proxy': '⏰ بروكسي ساعي (4 ساعات)'
    },
    'en': {
        'menu_title': '🌐 Daily Static',
        'menu_desc': 'Get high-quality Static proxy',
        'buy_proxy': '🛒 Buy Proxy',
        'my_proxies': '📦 My Proxies',
        'back': '🔙 Back',
        'select_country': '🌍 Select Country',
        'random_proxy': '🎲 Random Proxy Purchase',
        'search_proxy': '🔍 Advanced Search',
        'select_city': '🏙️ Select City:',
        'select_state': '📍 Select State:',
        'search_placeholder': 'Type to search...',
        'confirm_purchase': '✅ Confirm Purchase',
        'cancel': '❌ Cancel',
        'purchase_confirm_msg': '''
<b>Confirm Purchase</b>

Country: {country}
City: {city}
State: {state}

Price: <code>{price}</code> credits
Your balance: <code>{balance}</code> credits

Do you want to proceed?
''',
        'purchase_success': '''
<b>{purchase_success_title}</b>

<b>{proxy_details_title}</b>
━━━━━━━━━━━━━━━
IP: <code>{ip}</code>
Port: <code>{port}</code>
━━━━━━━━━━━━━━━

{country_label}: {country}
{city_label}: {city}
{state_label}: {state}
{valid_for_label}: {valid_duration}

{check_hint}
''',
        'purchase_success_title': 'Purchase Successful!',
        'proxy_details_title': 'Proxy Details:',
        'valid_for_label': 'Valid for',
        'valid_duration_24h': '24 hours',
        'valid_duration_4h': '4 hours',
        'check_hint': 'Use "Check" button to verify proxy status',
        'insufficient_balance': '⚠️ Insufficient balance!\n\nYour balance: {balance} credits\nRequired: {required} credits',
        'admin_balance_low': '🚫 Sorry, service is currently unavailable.\n\nError code: x0x0000',
        'no_proxies': '📭 You have no active proxies',
        'proxy_expired': '⏰ This proxy has expired',
        'check_status': '🔄 Check',
        'proxy_online': '✅ Proxy is working\nCountry: {country}',
        'proxy_offline': '❌ Proxy is currently offline',
        'refund': '💰 Refund',
        'refund_success': '✅ Successfully refunded {amount} credits!',
        'refund_failed': '❌ Refund failed. The proxy may not be refundable.',
        'refund_confirm': '⚠️ Are you sure you want to refund this proxy?\n\n{amount} credits will be returned to your balance.',
        'refund_confirm_btn': '✅ Confirm Refund',
        'service_disabled': '🚫 This service is temporarily disabled\n\nError code: x0x000A',
        'error_occurred': '⚠️ An error occurred\n\nError code: {code}',
        'no_results': '📭 No results available',
        'loading': '⏳ Loading...',
        'inline_title': '🔍 Static Proxy Search',
        'inline_desc': 'Type country or city name to search',
        'proxy_info': '{country} | {city}',
        'buy_menu_text': '''
<b>🛒 Buy Static Proxy</b>

Click the search button below to browse available proxies by country, state, and city.

💵 Price: {price} credits per proxy
''',
        'daily_proxy': '📅 Daily Proxy (24 hours)',
        'hourly_proxy': '⏰ Hourly Proxy (4 hours)'
    }
}


def get_luxury_message(key: str, language: str = 'ar') -> str:
    return LUXURY_MESSAGES.get(language, LUXURY_MESSAGES['ar']).get(key, key)


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
        cursor.execute('SELECT credits_balance FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return float(result[0]) if result else 0.0
    except:
        return 0.0


def deduct_user_balance(user_id: int, amount: float) -> bool:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT credits_balance FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        if not result or float(result[0]) < amount:
            conn.close()
            return False
        
        new_balance = float(result[0]) - amount
        cursor.execute('UPDATE users SET credits_balance = ? WHERE user_id = ?', (new_balance, user_id))
        conn.commit()
        conn.close()
        return True
    except:
        return False


luxury_db = LuxuryDB()

# تعيين مفتاح API الافتراضي إذا لم يكن موجوداً
DEFAULT_LUXURY_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4NDkxMTA2NTMwIiwiZXhwIjoxODEyNTU3MDA3fQ.j1nNqJinrSqOdQ_DepE8iPH8gdI-iK6HBhaPMvi3owE"

def init_default_settings():
    """تهيئة الإعدادات الافتراضية"""
    if not luxury_db.get_api_key():
        luxury_db.set_setting('luxury_api_key', DEFAULT_LUXURY_API_KEY)
        logger.info("تم تعيين مفتاح API الافتراضي لـ Luxury Support")
    
    if not luxury_db.get_setting('service_enabled'):
        luxury_db.set_setting('service_enabled', '1')
        logger.info("تم تفعيل خدمة Luxury Support افتراضياً")

init_default_settings()


async def luxury_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """القائمة الرئيسية لخدمة Luxury"""
    query = update.callback_query
    if query:
        await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    if not luxury_db.is_service_enabled():
        if query:
            await query.edit_message_text(get_luxury_message('service_disabled', language))
        else:
            await update.message.reply_text(get_luxury_message('service_disabled', language))
        return
    
    keyboard = [
        [InlineKeyboardButton(
            get_luxury_message('buy_proxy', language),
            callback_data="lx_buy_menu"
        )],
        [InlineKeyboardButton(
            get_luxury_message('my_proxies', language),
            callback_data="lx_my_proxies"
        )],
        [InlineKeyboardButton(
            get_luxury_message('back', language),
            callback_data="back_to_main"
        )]
    ]
    
    text = f"<b>{get_luxury_message('menu_title', language)}</b>\n\n{get_luxury_message('menu_desc', language)}"
    
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


async def show_buy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """قائمة شراء البروكسي - اختيار نوع المدة أولاً"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    daily_price = luxury_db.get_proxy_price(daily=True)
    hourly_price = luxury_db.get_proxy_price(daily=False)
    balance = get_user_balance(user_id)
    
    keyboard = [
        [InlineKeyboardButton(
            f"📅 24h (${daily_price})" if language == 'ar' else f"📅 24h (${daily_price})",
            callback_data="lx_duration_daily"
        )],
        [InlineKeyboardButton(
            f"⏰ 4h (${hourly_price})" if language == 'ar' else f"⏰ 4h (${hourly_price})",
            callback_data="lx_duration_hourly"
        )],
        [InlineKeyboardButton(
            get_luxury_message('back', language),
            callback_data="lx_main_menu"
        )]
    ]
    
    text = f"""
<b>{"🛒 شراء بروكسي ستاتيك" if language == 'ar' else "🛒 Buy Static Proxy"}</b>

{"اختر نوع البروكسي:" if language == 'ar' else "Select proxy type:"}

📅 <b>{"بروكسي يومي" if language == 'ar' else "Daily Proxy"}</b> (24 {"ساعة" if language == 'ar' else "hours"}) - <b>${daily_price:.2f}</b>
   
⏰ <b>{"بروكسي ساعي" if language == 'ar' else "Hourly Proxy"}</b> (4 {"ساعات" if language == 'ar' else "hours"}) - <b>${hourly_price:.2f}</b>

💰 {"رصيدك" if language == 'ar' else "Balance"}: {balance:.2f} {"كريديت" if language == 'ar' else "credits"}
"""
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def show_proxy_selection_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, duration_type: str) -> None:
    """قائمة اختيار البروكسي بعد تحديد المدة"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    is_daily = duration_type == 'daily'
    price = luxury_db.get_proxy_price(daily=is_daily)
    
    context.user_data['lx_duration'] = duration_type
    
    duration_text = get_luxury_message('daily_proxy', language) if is_daily else get_luxury_message('hourly_proxy', language)
    
    keyboard = [
        [InlineKeyboardButton(
            get_luxury_message('select_country', language),
            switch_inline_query_current_chat="lu_static:country: "
        )],
        [InlineKeyboardButton(
            get_luxury_message('random_proxy', language),
            callback_data=f"lx_random_{duration_type}"
        )],
        [InlineKeyboardButton(
            get_luxury_message('back', language),
            callback_data="lx_buy_menu"
        )]
    ]
    
    text = f"""
<b>{"🔍 اختيار البروكسي" if language == 'ar' else "🔍 Select Proxy"}</b>

{"النوع المختار" if language == 'ar' else "Selected Type"}: {duration_text}
💵 {"السعر" if language == 'ar' else "Price"}: {price} {"كريديت" if language == 'ar' else "credits"}

{"اختر طريقة البحث:" if language == 'ar' else "Choose search method:"}
"""
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def select_random_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """اختيار دولة عشوائي والانتقال لاختيار الولاية"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    api_key = luxury_db.get_api_key()
    if not api_key:
        await query.edit_message_text(get_luxury_message('admin_balance_low', language))
        return
    
    api = LuxuryAPI(api_key)
    
    import random
    countries = api.get_countries()
    if isinstance(countries, dict):
        countries = countries.get('result', countries.get('data', countries.get('countries', [])))
    
    if not countries:
        await query.edit_message_text(
            get_luxury_message('no_results', language),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(get_luxury_message('back', language), callback_data="lx_buy_menu")]
            ])
        )
        return
    
    random_country = random.choice(countries)
    if isinstance(random_country, dict):
        country_code = random_country.get('code', random_country.get('country_code', ''))
    else:
        country_code = str(random_country)
    
    await show_state_selection(update, context, country_code)


async def show_random_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, duration_type: str) -> None:
    """عرض تأكيد شراء بروكسي عشوائي"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    price = luxury_db.get_proxy_price()
    balance = get_user_balance(user_id)
    
    duration_text = get_luxury_message('daily_proxy', language) if duration_type == 'daily' else get_luxury_message('hourly_proxy', language)
    
    keyboard = [
        [InlineKeyboardButton(
            get_luxury_message('confirm_purchase', language),
            callback_data=f"lx_do_random_{duration_type}"
        )],
        [InlineKeyboardButton(
            get_luxury_message('cancel', language),
            callback_data="lx_buy_menu"
        )]
    ]
    
    text = f"""
<b>{"🎲 تأكيد شراء بروكسي عشوائي" if language == 'ar' else "🎲 Confirm Random Proxy Purchase"}</b>

{"النوع" if language == 'ar' else "Type"}: {duration_text}
💵 {"السعر" if language == 'ar' else "Price"}: <code>{price:.2f}</code> {"كريديت" if language == 'ar' else "credits"}
💰 {"رصيدك" if language == 'ar' else "Balance"}: <code>{balance:.2f}</code> {"كريديت" if language == 'ar' else "credits"}

{"سيتم اختيار بروكسي عشوائي من المتاح. هل تريد المتابعة؟" if language == 'ar' else "A random proxy will be selected from available options. Continue?"}
"""
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def buy_random_proxy_final(update: Update, context: ContextTypes.DEFAULT_TYPE, daily_buy: bool) -> None:
    """تنفيذ شراء بروكسي عشوائي"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    price = luxury_db.get_proxy_price()
    balance = get_user_balance(user_id)
    
    if balance < price:
        await query.edit_message_text(
            get_luxury_message('insufficient_balance', language).format(
                balance=balance, required=price
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(get_luxury_message('back', language), callback_data="lx_buy_menu")]
            ])
        )
        return
    
    api_key = luxury_db.get_api_key()
    if not api_key:
        await query.edit_message_text(get_luxury_message('admin_balance_low', language))
        return
    
    api = LuxuryAPI(api_key)
    
    await query.edit_message_text(
        get_luxury_message('loading', language),
        parse_mode='HTML'
    )
    
    result = api.search_proxies(limit=20)
    
    if not result or 'error' in str(result).lower():
        await query.edit_message_text(
            get_luxury_message('error_occurred', language).format(code='x0x0002'),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(get_luxury_message('back', language), callback_data="lx_buy_menu")]
            ])
        )
        return
    
    proxies = result if isinstance(result, list) else result.get('data', result.get('proxies', result.get('result', [])))
    
    if not proxies:
        await query.edit_message_text(
            get_luxury_message('no_results', language),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(get_luxury_message('back', language), callback_data="lx_buy_menu")]
            ])
        )
        return
    
    import random
    proxy_data = random.choice(proxies) if len(proxies) > 1 else proxies[0]
    proxy_id = proxy_data.get('proxy_id', proxy_data.get('id', ''))
    
    await process_purchase(update, context, proxy_id, daily_buy=daily_buy)


async def process_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, proxy_id: str, daily_buy: bool) -> None:
    """معالجة عملية الشراء"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    price = luxury_db.get_proxy_price()
    balance = get_user_balance(user_id)
    
    if balance < price:
        await query.edit_message_text(
            get_luxury_message('insufficient_balance', language).format(
                balance=balance, required=price
            )
        )
        return
    
    api_key = luxury_db.get_api_key()
    if not api_key:
        await query.edit_message_text(get_luxury_message('admin_balance_low', language))
        return
    
    api = LuxuryAPI(api_key)
    
    await query.edit_message_text(
        get_luxury_message('loading', language),
        parse_mode='HTML'
    )
    
    buy_result = api.buy_proxy(proxy_id, daily_buy=daily_buy)
    
    if not buy_result or 'error' in str(buy_result).lower():
        error_msg = buy_result.get('detail', buy_result.get('message', 'Unknown error')) if isinstance(buy_result, dict) else str(buy_result)
        await query.edit_message_text(
            get_luxury_message('error_occurred', language).format(code='x0x0001') + f"\n\n{error_msg}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(get_luxury_message('back', language), callback_data="lx_buy_menu")]
            ])
        )
        return
    
    if not deduct_user_balance(user_id, price):
        await query.edit_message_text(
            get_luxury_message('insufficient_balance', language).format(
                balance=balance, required=price
            )
        )
        return
    
    bought_proxy = buy_result if isinstance(buy_result, dict) else {}
    if 'data' in bought_proxy:
        bought_proxy = bought_proxy['data']
    
    purchase_id = luxury_db.save_purchase(user_id, bought_proxy, price, daily_buy)
    
    flag = get_country_flag_luxury(bought_proxy.get('country_code', bought_proxy.get('country', 'XX')))
    country_name = get_country_name(bought_proxy.get('country_code', bought_proxy.get('country', 'XX')), language)
    
    country_label = "الدولة" if language == 'ar' else "Country"
    city_label = "المدينة" if language == 'ar' else "City"
    state_label = "الولاية" if language == 'ar' else "State"
    valid_duration = get_luxury_message('valid_duration_24h' if daily_buy else 'valid_duration_4h', language)
    
    text = get_luxury_message('purchase_success', language).format(
        ip=bought_proxy.get('real_ip', bought_proxy.get('ip', 'N/A')),
        port=bought_proxy.get('port', 'N/A'),
        country=f"{flag} {country_name}",
        city=bought_proxy.get('city', 'N/A'),
        state=bought_proxy.get('state', 'N/A'),
        country_label=country_label,
        city_label=city_label,
        state_label=state_label,
        purchase_success_title=get_luxury_message('purchase_success_title', language),
        proxy_details_title=get_luxury_message('proxy_details_title', language),
        valid_for_label=get_luxury_message('valid_for_label', language),
        valid_duration=valid_duration,
        check_hint=get_luxury_message('check_hint', language)
    )
    
    keyboard = [[InlineKeyboardButton(
        get_luxury_message('check_status', language),
        callback_data=f"lx_check_{purchase_id}"
    )]]
    keyboard.append([InlineKeyboardButton(
        get_luxury_message('back', language),
        callback_data="lx_main_menu"
    )])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def show_my_proxies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض بروكسيات المستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    proxies = luxury_db.get_active_proxies(user_id)
    
    if not proxies:
        keyboard = [[InlineKeyboardButton(
            get_luxury_message('back', language),
            callback_data="lx_main_menu"
        )]]
        await query.edit_message_text(
            get_luxury_message('no_proxies', language),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    keyboard = []
    for proxy in proxies:
        flag = get_country_flag_luxury(proxy.get('country', 'XX'))
        city = proxy.get('city', 'N/A')
        ip = proxy.get('ip', 'N/A')
        is_daily = proxy.get('daily_buy', True)
        duration_label = "(24h)" if is_daily else "(4h)"
        
        keyboard.append([InlineKeyboardButton(
            f"{flag} {city} | {ip} {duration_label}",
            callback_data=f"lx_view_{proxy['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton(
        get_luxury_message('back', language),
        callback_data="lx_main_menu"
    )])
    
    await query.edit_message_text(
        f"<b>{get_luxury_message('my_proxies', language)}</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def view_proxy_details(update: Update, context: ContextTypes.DEFAULT_TYPE, purchase_id: int) -> None:
    """عرض تفاصيل بروكسي معين"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    proxies = luxury_db.get_user_proxies(user_id, limit=50)
    proxy = None
    for p in proxies:
        if p['id'] == purchase_id:
            proxy = p
            break
    
    if not proxy:
        await query.edit_message_text(get_luxury_message('proxy_expired', language))
        return
    
    flag = get_country_flag_luxury(proxy.get('country', 'XX'))
    country_name = get_country_name(proxy.get('country', 'XX'), language)
    valid_duration = get_luxury_message('valid_duration_24h' if proxy.get('daily_buy', True) else 'valid_duration_4h', language)
    
    text = f"""
<b>{get_luxury_message('proxy_details_title', language)}</b>
━━━━━━━━━━━━━━━
IP: <code>{proxy.get('ip', 'N/A')}</code>
Port: <code>{proxy.get('port', 'N/A')}</code>
━━━━━━━━━━━━━━━

{"الدولة" if language == 'ar' else "Country"}: {flag} {country_name}
{"المدينة" if language == 'ar' else "City"}: {proxy.get('city', 'N/A')}
{"الولاية" if language == 'ar' else "State"}: {proxy.get('state', 'N/A')}
{"ISP"}: {proxy.get('isp', 'N/A')}
{"صالح لمدة" if language == 'ar' else "Valid for"}: {valid_duration}
"""
    
    keyboard = [
        [InlineKeyboardButton(
            get_luxury_message('check_status', language),
            callback_data=f"lx_check_{purchase_id}"
        )],
        [InlineKeyboardButton(
            get_luxury_message('refund', language),
            callback_data=f"lx_refund_ask_{purchase_id}"
        )],
        [InlineKeyboardButton(
            get_luxury_message('back', language),
            callback_data="lx_my_proxies"
        )]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def refund_proxy_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, purchase_id: int) -> None:
    """عرض تأكيد الاسترداد"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    proxies = luxury_db.get_user_proxies(user_id, limit=50)
    proxy = None
    for p in proxies:
        if p['id'] == purchase_id:
            proxy = p
            break
    
    if not proxy:
        await query.edit_message_text(get_luxury_message('proxy_expired', language))
        return
    
    price = proxy.get('price', 0)
    text = get_luxury_message('refund_confirm', language).format(amount=price)
    
    keyboard = [
        [InlineKeyboardButton(
            get_luxury_message('refund_confirm_btn', language),
            callback_data=f"lx_refund_do_{purchase_id}"
        )],
        [InlineKeyboardButton(
            get_luxury_message('back', language),
            callback_data=f"lx_view_{purchase_id}"
        )]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def process_refund(update: Update, context: ContextTypes.DEFAULT_TYPE, purchase_id: int) -> None:
    """معالجة الاسترداد الفعلي"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    proxies = luxury_db.get_user_proxies(user_id, limit=50)
    proxy = None
    for p in proxies:
        if p['id'] == purchase_id:
            proxy = p
            break
    
    if not proxy:
        await query.edit_message_text(get_luxury_message('proxy_expired', language))
        return
    
    record_id = proxy.get('record_id', 0)
    price = proxy.get('price', 0)
    
    if not record_id:
        await query.edit_message_text(get_luxury_message('refund_failed', language))
        return
    
    api_key = luxury_db.get_api_key()
    if not api_key:
        await query.edit_message_text(get_luxury_message('admin_balance_low', language))
        return
    
    api = LuxuryAPI(api_key)
    result = api.refund_proxy(record_id)
    
    if result.get('status') == True or result.get('success') == True or 'refund' in str(result).lower():
        from bot_utils import update_user_balance
        update_user_balance(user_id, price)
        
        luxury_db.delete_purchase(purchase_id)
        
        text = get_luxury_message('refund_success', language).format(amount=price)
        keyboard = [[InlineKeyboardButton(
            get_luxury_message('back', language),
            callback_data="lx_my_proxies"
        )]]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    else:
        text = get_luxury_message('refund_failed', language)
        keyboard = [[InlineKeyboardButton(
            get_luxury_message('back', language),
            callback_data=f"lx_view_{purchase_id}"
        )]]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )


async def check_proxy_status(update: Update, context: ContextTypes.DEFAULT_TYPE, purchase_id: int) -> None:
    """فحص حالة البروكسي"""
    query = update.callback_query
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    proxies = luxury_db.get_user_proxies(user_id, limit=50)
    proxy = None
    for p in proxies:
        if p['id'] == purchase_id:
            proxy = p
            break
    
    if not proxy:
        await query.answer(get_luxury_message('proxy_expired', language), show_alert=True)
        return
    
    api_key = luxury_db.get_api_key()
    if api_key:
        api = LuxuryAPI(api_key)
        is_online = api.check_proxy_socket(proxy.get('ip', ''), proxy.get('port', 0))
    else:
        is_online = False
    
    if is_online:
        flag = get_country_flag_luxury(proxy.get('country', 'XX'))
        country_name = get_country_name(proxy.get('country', 'XX'), language)
        await query.answer(
            get_luxury_message('proxy_online', language).format(country=f"{flag} {country_name}"),
            show_alert=True
        )
    else:
        await query.answer(get_luxury_message('proxy_offline', language), show_alert=True)


async def handle_luxury_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج callbacks الرئيسي لخدمة Luxury"""
    query = update.callback_query
    data = query.data
    
    if data == "lx_main_menu":
        await luxury_main_menu(update, context)
    elif data == "lx_verify_sub":
        # Verify subscription and go to main menu
        user_id = update.effective_user.id
        language = get_user_language(user_id)
        is_subscribed, channel = await check_user_subscription(context.bot, user_id)
        if is_subscribed:
            await query.answer("✅ " + ("تم التحقق بنجاح!" if language == 'ar' else "Verified successfully!"))
            await luxury_main_menu(update, context)
        else:
            await query.answer(
                "❌ " + ("لم تشترك بعد!" if language == 'ar' else "Not subscribed yet!"),
                show_alert=True
            )
    elif data == "lx_buy_menu":
        await show_buy_menu(update, context)
    elif data == "lx_my_proxies":
        await show_my_proxies(update, context)
    elif data == "lx_duration_daily":
        await show_proxy_selection_menu(update, context, "daily")
    elif data == "lx_duration_hourly":
        await show_proxy_selection_menu(update, context, "hourly")
    elif data == "lx_random":
        await process_random_purchase(update, context, None, None, None, None)
    elif data == "lx_random_daily":
        await process_random_purchase(update, context, None, None, None, None)
    elif data == "lx_random_hourly":
        await process_random_purchase(update, context, None, None, None, None)
    elif data.startswith("lx_do_random_"):
        duration = data.replace("lx_do_random_", "")
        await buy_random_proxy_final(update, context, duration == "daily")
    elif data.startswith("lx_confirm_daily_"):
        proxy_id = data.replace("lx_confirm_daily_", "")
        await process_purchase(update, context, proxy_id, daily_buy=True)
    elif data.startswith("lx_confirm_hourly_"):
        proxy_id = data.replace("lx_confirm_hourly_", "")
        await process_purchase(update, context, proxy_id, daily_buy=False)
    elif data.startswith("lx_view_"):
        purchase_id = int(data.replace("lx_view_", ""))
        await view_proxy_details(update, context, purchase_id)
    elif data.startswith("lx_check_"):
        purchase_id = int(data.replace("lx_check_", ""))
        await check_proxy_status(update, context, purchase_id)
    elif data.startswith("lx_refund_ask_"):
        purchase_id = int(data.replace("lx_refund_ask_", ""))
        await refund_proxy_confirm(update, context, purchase_id)
    elif data.startswith("lx_refund_do_"):
        purchase_id = int(data.replace("lx_refund_do_", ""))
        await process_refund(update, context, purchase_id)
    elif data.startswith("lx_country_"):
        country_code = data.replace("lx_country_", "")
        await show_country_proxies(update, context, country_code)
    elif data.startswith("lx_buy_random_"):
        parts = data.replace("lx_buy_random_", "").split("_")
        country = parts[0] if len(parts) > 0 and parts[0] else None
        state = parts[1].replace("-", " ") if len(parts) > 1 and parts[1] else None
        city = parts[2].replace("-", " ") if len(parts) > 2 and parts[2] else None
        await process_random_purchase(update, context, country, state, city)
    elif data.startswith("lx_quick_buy_"):
        parts = data.replace("lx_quick_buy_", "").split("_")
        country = parts[0] if len(parts) > 0 and parts[0] else None
        state = parts[1].replace("-", " ") if len(parts) > 1 and parts[1] else None
        city = parts[2].replace("-", " ") if len(parts) > 2 and parts[2] else None
        await process_random_purchase(update, context, country, state, city, None)
    elif data.startswith("lx_skip_state_"):
        country_code = data.replace("lx_skip_state_", "")
        await show_city_selection(update, context, country_code, None)
    elif data.startswith("lx_state_"):
        parts = data.replace("lx_state_", "").split("_", 1)
        country_code = parts[0]
        state = parts[1].replace("-", " ") if len(parts) > 1 and parts[1] else None
        if state:
            await show_city_selection(update, context, country_code, state)
        else:
            await show_state_selection(update, context, country_code)
    elif data.startswith("lx_skip_city_"):
        parts = data.replace("lx_skip_city_", "").split("_", 1)
        country_code = parts[0]
        state = parts[1].replace("-", " ") if len(parts) > 1 else None
        await show_isp_selection(update, context, country_code, state, None)
    elif data.startswith("lx_city_"):
        parts = data.replace("lx_city_", "").split("_", 2)
        country_code = parts[0]
        state = parts[1].replace("-", " ") if len(parts) > 1 and parts[1] else None
        city = parts[2].replace("-", " ") if len(parts) > 2 and parts[2] else None
        if city:
            await show_isp_selection(update, context, country_code, state, city)
        else:
            await show_city_selection(update, context, country_code, state)
    elif data.startswith("lx_skip_isp_"):
        parts = data.replace("lx_skip_isp_", "").split("_", 2)
        country_code = parts[0]
        state = parts[1].replace("-", " ") if len(parts) > 1 and parts[1] else None
        city = parts[2].replace("-", " ") if len(parts) > 2 and parts[2] else None
        await process_random_purchase(update, context, country_code, state, city, None)
    elif data.startswith("lx_isp_"):
        parts = data.replace("lx_isp_", "").split("_", 3)
        country_code = parts[0]
        state = parts[1].replace("-", " ") if len(parts) > 1 and parts[1] else None
        city = parts[2].replace("-", " ") if len(parts) > 2 and parts[2] else None
        isp = parts[3].replace("-", " ") if len(parts) > 3 and parts[3] else None
        await process_random_purchase(update, context, country_code, state, city, isp)
    elif data.startswith("lx_buy_isp_"):
        parts = data.replace("lx_buy_isp_", "").split("_", 3)
        country = parts[0] if len(parts) > 0 else None
        state = parts[1].replace("-", " ") if len(parts) > 1 and parts[1] else None
        city = parts[2].replace("-", " ") if len(parts) > 2 and parts[2] else None
        isp = parts[3].replace("-", " ") if len(parts) > 3 and parts[3] else None
        await process_random_purchase(update, context, country, state, city, isp)
    elif data.startswith("lx_zip_buy_"):
        zip_code = data.replace("lx_zip_buy_", "")
        await process_zip_purchase(update, context, zip_code)
    elif data.startswith("lx_select_"):
        proxy_id = data.replace("lx_select_", "")
        await show_proxy_confirm(update, context, proxy_id)


async def show_country_proxies(update: Update, context: ContextTypes.DEFAULT_TYPE, country_code: str) -> None:
    """عرض بروكسيات دولة معينة"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    flag = get_country_flag_luxury(country_code)
    country_name = get_country_name(country_code, language)
    
    keyboard = [
        [InlineKeyboardButton(
            "📍 اختيار ولاية" if language == 'ar' else "📍 Select State",
            switch_inline_query_current_chat=f"lu_static:state:{country_code}: "
        )],
        [InlineKeyboardButton(
            "📮 بحث برمز ZIP" if language == 'ar' else "📮 Search by ZIP Code",
            switch_inline_query_current_chat=f"lu_static:zip:{country_code}: "
        )],
        [InlineKeyboardButton(
            "⏭️ تخطي الولاية" if language == 'ar' else "⏭️ Skip State",
            callback_data=f"lx_skip_state_{country_code}"
        )],
        [InlineKeyboardButton(
            "⚡ شراء سريع" if language == 'ar' else "⚡ Quick Buy",
            callback_data=f"lx_quick_buy_{country_code}__"
        )],
        [InlineKeyboardButton(
            get_luxury_message('back', language),
            callback_data="lx_buy_menu"
        )]
    ]
    
    text = f"""
<b>{"📍 اختيار الولاية" if language == 'ar' else "📍 Select State"}</b>

{"الدولة" if language == 'ar' else "Country"}: {flag} {country_name}

{"اختر ولاية أو تخطَ للاختيار عشوائياً" if language == 'ar' else "Select a state or skip for random selection"}
"""
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def show_city_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               country_code: str, state: str = None) -> None:
    """عرض اختيار المدينة"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    flag = get_country_flag_luxury(country_code)
    country_name = get_country_name(country_code, language)
    state_safe = state.replace(" ", "-") if state else ""
    
    keyboard = [
        [InlineKeyboardButton(
            "🏙️ اختيار مدينة" if language == 'ar' else "🏙️ Select City",
            switch_inline_query_current_chat=f"lu_static:city:{country_code}:{state_safe}: "
        )],
        [InlineKeyboardButton(
            "⏭️ تخطي المدينة" if language == 'ar' else "⏭️ Skip City",
            callback_data=f"lx_skip_city_{country_code}_{state_safe}"
        )],
        [InlineKeyboardButton(
            "⚡ شراء سريع" if language == 'ar' else "⚡ Quick Buy",
            callback_data=f"lx_quick_buy_{country_code}_{state_safe}_"
        )],
        [InlineKeyboardButton(
            get_luxury_message('back', language),
            callback_data=f"lx_country_{country_code}"
        )]
    ]
    
    text = f"""
<b>{"🏙️ اختيار المدينة" if language == 'ar' else "🏙️ Select City"}</b>

{"الدولة" if language == 'ar' else "Country"}: {flag} {country_name}
{"الولاية" if language == 'ar' else "State"}: {state or '-'}

{"اختر مدينة أو تخطَ للاختيار عشوائياً" if language == 'ar' else "Select a city or skip for random selection"}
"""
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def show_isp_selection(update: Update, context: ContextTypes.DEFAULT_TYPE,
                              country_code: str, state: str = None, city: str = None) -> None:
    """عرض اختيار مزود الخدمة"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    flag = get_country_flag_luxury(country_code)
    country_name = get_country_name(country_code, language)
    state_safe = state.replace(" ", "-") if state else ""
    city_safe = city.replace(" ", "-") if city else ""
    
    api_key = luxury_db.get_api_key()
    isps = []
    if api_key:
        api = LuxuryAPI(api_key)
        if city:
            isp_result = api.get_isps_by_city(city)
            isps = isp_result if isinstance(isp_result, list) else isp_result.get('result', isp_result.get('data', isp_result.get('isps', [])))
    
    keyboard = [
        [InlineKeyboardButton(
            "🏢 اختيار ISP" if language == 'ar' else "🏢 Select ISP",
            switch_inline_query_current_chat=f"lu_static:isp:{country_code}:{state_safe}:{city_safe}: "
        )]
    ]
    
    for isp_item in isps[:6]:
        isp_name = isp_item.get('isp', isp_item) if isinstance(isp_item, dict) else isp_item
        isp_safe = isp_name.replace(" ", "-")
        keyboard.append([InlineKeyboardButton(
            f"🏢 {isp_name}",
            callback_data=f"lx_isp_{country_code}_{state_safe}_{city_safe}_{isp_safe}"
        )])
    
    keyboard.append([InlineKeyboardButton(
        "⏭️ تخطي ISP (شراء حالاً)" if language == 'ar' else "⏭️ Skip ISP (Buy Now)",
        callback_data=f"lx_skip_isp_{country_code}_{state_safe}_{city_safe}"
    )])
    keyboard.append([InlineKeyboardButton(
        get_luxury_message('back', language),
        callback_data=f"lx_state_{country_code}_{state_safe}" if state else f"lx_country_{country_code}"
    )])
    
    duration_type = context.user_data.get('lx_duration', 'daily')
    is_daily = duration_type == 'daily'
    price = luxury_db.get_proxy_price(daily=is_daily)
    
    text = f"""
<b>{"🏢 اختيار مزود الخدمة (الخطوة الأخيرة)" if language == 'ar' else "🏢 Select ISP (Final Step)"}</b>

{"الدولة" if language == 'ar' else "Country"}: {flag} {country_name}
{"الولاية" if language == 'ar' else "State"}: {state or '-'}
{"المدينة" if language == 'ar' else "City"}: {city or '-'}
{"💵 السعر" if language == 'ar' else "💵 Price"}: ${price}

{"اختر ISP أو تخطَ للشراء مباشرة" if language == 'ar' else "Select ISP or skip to purchase directly"}
"""
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def show_proxy_list(update: Update, context: ContextTypes.DEFAULT_TYPE,
                          country_code: str, state: str = None, city: str = None, isp: str = None) -> None:
    """عرض قائمة البروكسيات للشراء"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    price = luxury_db.get_proxy_price()
    
    api_key = luxury_db.get_api_key()
    if not api_key:
        await query.edit_message_text(get_luxury_message('admin_balance_low', language))
        return
    
    api = LuxuryAPI(api_key)
    
    await query.edit_message_text(get_luxury_message('loading', language))
    
    result = api.search_proxies(
        country_code=country_code,
        state=state,
        city=city,
        isp=isp,
        limit=10
    )
    
    proxies = result if isinstance(result, list) else result.get('proxies', result.get('result', result.get('data', [])))
    
    if not proxies:
        await query.edit_message_text(
            get_luxury_message('no_results', language),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(get_luxury_message('back', language), callback_data="lx_buy_menu")]
            ])
        )
        return
    
    keyboard = []
    for proxy in proxies[:8]:
        proxy_id = proxy.get('proxy_id', proxy.get('id', ''))
        ip = proxy.get('real_ip', proxy.get('ip', 'N/A'))
        proxy_city = proxy.get('city', 'N/A')
        
        keyboard.append([InlineKeyboardButton(
            f"{ip} | {proxy_city}",
            callback_data=f"lx_select_{proxy_id}"
        )])
    
    keyboard.append([InlineKeyboardButton(
        get_luxury_message('back', language),
        callback_data="lx_buy_menu"
    )])
    
    flag = get_country_flag_luxury(country_code)
    country_name = get_country_name(country_code, language)
    
    text = f"""
<b>{"البروكسيات المتاحة" if language == 'ar' else "Available Proxies"}</b>

{"الدولة" if language == 'ar' else "Country"}: {flag} {country_name}
{"السعر" if language == 'ar' else "Price"}: {price} {"كريديت" if language == 'ar' else "credits"}

{"اختر بروكسي للشراء" if language == 'ar' else "Select a proxy to purchase"}
"""
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def show_proxy_confirm_by_id(update: Update, context: ContextTypes.DEFAULT_TYPE, proxy_id: str) -> None:
    """عرض تأكيد شراء بروكسي محدد (من الرسائل)"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    duration_type = context.user_data.get('lx_duration', 'daily')
    is_daily = duration_type == 'daily'
    price = luxury_db.get_proxy_price(daily=is_daily)
    balance = get_user_balance(user_id)
    
    api_key = luxury_db.get_api_key()
    if not api_key:
        await update.message.reply_text(get_luxury_message('admin_balance_low', language))
        return
    
    context.user_data['pending_proxy_id'] = proxy_id
    
    duration_text = get_luxury_message('daily_proxy', language) if is_daily else get_luxury_message('hourly_proxy', language)
    confirm_callback = f"lx_confirm_{duration_type}_{proxy_id}"
    
    keyboard = [
        [InlineKeyboardButton(
            "✅ " + ("تأكيد الشراء" if language == 'ar' else "Confirm Purchase"),
            callback_data=confirm_callback
        )],
        [InlineKeyboardButton(
            get_luxury_message('back', language),
            callback_data="lx_buy_menu"
        )]
    ]
    
    confirm_text = f"""
<b>{"🛒 تأكيد الشراء" if language == 'ar' else "🛒 Confirm Purchase"}</b>

🆔 {"معرف البروكسي" if language == 'ar' else "Proxy ID"}: <code>{proxy_id[:12]}...</code>
{"النوع" if language == 'ar' else "Type"}: {duration_text}

💵 {"السعر" if language == 'ar' else "Price"}: {price:.2f} {"كريديت" if language == 'ar' else "credits"}
💰 {"رصيدك" if language == 'ar' else "Your balance"}: {balance:.2f} {"كريديت" if language == 'ar' else "credits"}

{"اضغط تأكيد الشراء للمتابعة" if language == 'ar' else "Click Confirm Purchase to proceed"}
"""
    
    await update.message.reply_text(
        confirm_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def show_proxy_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, proxy_id: str) -> None:
    """عرض تأكيد شراء بروكسي محدد"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    price = luxury_db.get_proxy_price()
    balance = get_user_balance(user_id)
    
    api_key = luxury_db.get_api_key()
    if not api_key:
        await query.edit_message_text(get_luxury_message('admin_balance_low', language))
        return
    
    context.user_data['pending_proxy_id'] = proxy_id
    
    duration_type = context.user_data.get('lx_duration', 'daily')
    duration_text = get_luxury_message('daily_proxy', language) if duration_type == 'daily' else get_luxury_message('hourly_proxy', language)
    confirm_callback = f"lx_confirm_{duration_type}_{proxy_id}"
    
    keyboard = [
        [InlineKeyboardButton(
            "✅ " + ("تأكيد الشراء" if language == 'ar' else "Confirm Purchase"),
            callback_data=confirm_callback
        )],
        [InlineKeyboardButton(
            get_luxury_message('back', language),
            callback_data="lx_buy_menu"
        )]
    ]
    
    confirm_text = f"""
<b>{"🛒 تأكيد الشراء" if language == 'ar' else "🛒 Confirm Purchase"}</b>

🆔 {"معرف البروكسي" if language == 'ar' else "Proxy ID"}: <code>{proxy_id[:12]}...</code>
{"النوع" if language == 'ar' else "Type"}: {duration_text}

💵 {"السعر" if language == 'ar' else "Price"}: {price:.2f} {"كريديت" if language == 'ar' else "credits"}
💰 {"رصيدك" if language == 'ar' else "Your balance"}: {balance:.2f} {"كريديت" if language == 'ar' else "credits"}

{"اضغط تأكيد الشراء للمتابعة" if language == 'ar' else "Click Confirm Purchase to proceed"}
"""
    
    await query.edit_message_text(
        confirm_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def process_zip_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, zip_code: str) -> None:
    """معالجة شراء بروكسي برمز ZIP"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    price = luxury_db.get_proxy_price()
    balance = get_user_balance(user_id)
    
    api_key = luxury_db.get_api_key()
    if not api_key:
        await query.edit_message_text(get_luxury_message('admin_balance_low', language))
        return
    
    api = LuxuryAPI(api_key)
    
    await query.edit_message_text(get_luxury_message('loading', language))
    
    result = api.search_proxies(zip_code=zip_code, limit=10)
    proxies = result if isinstance(result, list) else result.get('proxies', result.get('result', result.get('data', [])))
    
    if not proxies:
        await query.edit_message_text(
            get_luxury_message('no_results', language),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(get_luxury_message('back', language), callback_data="lx_buy_menu")]
            ])
        )
        return
    
    import random
    proxy_data = random.choice(proxies) if len(proxies) > 1 else proxies[0]
    proxy_id = proxy_data.get('proxy_id', proxy_data.get('id', ''))
    
    context.user_data['pending_proxy'] = proxy_data
    context.user_data['pending_proxy_id'] = proxy_id
    
    flag = get_country_flag_luxury(proxy_data.get('country_code', proxy_data.get('country', 'XX')))
    country_name = get_country_name(proxy_data.get('country_code', proxy_data.get('country', 'XX')), language)
    
    # استخدام المدة المختارة مسبقاً
    duration_type = context.user_data.get('lx_duration', 'daily')
    duration_text = get_luxury_message('daily_proxy', language) if duration_type == 'daily' else get_luxury_message('hourly_proxy', language)
    confirm_callback = f"lx_confirm_{duration_type}_{proxy_id}"
    
    keyboard = [
        [InlineKeyboardButton(
            "✅ " + ("تأكيد الشراء" if language == 'ar' else "Confirm Purchase"),
            callback_data=confirm_callback
        )],
        [InlineKeyboardButton(
            get_luxury_message('back', language),
            callback_data="lx_buy_menu"
        )]
    ]
    
    confirm_text = f"""
<b>{"🛒 تأكيد الشراء" if language == 'ar' else "🛒 Confirm Purchase"}</b>

{"الدولة" if language == 'ar' else "Country"}: {flag} {country_name}
{"الولاية" if language == 'ar' else "State"}: {proxy_data.get('state', 'N/A')}
{"المدينة" if language == 'ar' else "City"}: {proxy_data.get('city', 'N/A')}
{"رمز ZIP" if language == 'ar' else "ZIP Code"}: {zip_code}
{"النوع" if language == 'ar' else "Type"}: {duration_text}

💵 {"السعر" if language == 'ar' else "Price"}: {price:.2f} {"كريديت" if language == 'ar' else "credits"}
💰 {"رصيدك" if language == 'ar' else "Your balance"}: {balance:.2f} {"كريديت" if language == 'ar' else "credits"}

{"اضغط تأكيد الشراء للمتابعة" if language == 'ar' else "Click Confirm Purchase to proceed"}
"""
    
    await query.edit_message_text(
        confirm_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def process_random_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                   country: str = None, state: str = None, city: str = None, isp: str = None) -> None:
    """معالجة شراء عشوائي بناءً على المعايير"""
    query = update.callback_query
    is_callback = query is not None
    
    if is_callback:
        await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    duration_type = context.user_data.get('lx_duration', 'daily')
    is_daily = duration_type == 'daily'
    price = luxury_db.get_proxy_price(daily=is_daily)
    balance = get_user_balance(user_id)
    
    async def send_message(text, reply_markup=None, parse_mode=None):
        if is_callback:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    
    api_key = luxury_db.get_api_key()
    if not api_key:
        await send_message(get_luxury_message('admin_balance_low', language))
        return
    
    api = LuxuryAPI(api_key)
    
    loading_msg = None
    if is_callback:
        await query.edit_message_text(get_luxury_message('loading', language), parse_mode='HTML')
    else:
        loading_msg = await update.message.reply_text(get_luxury_message('loading', language), parse_mode='HTML')
    
    result = api.search_proxies(
        country_code=country,
        state=state,
        city=city,
        limit=50
    )
    
    proxies = result if isinstance(result, list) else result.get('proxies', result.get('result', result.get('data', [])))
    
    if proxies and isp:
        isp_lower = isp.lower()
        filtered = [p for p in proxies if isp_lower in p.get('isp', '').lower()]
        if filtered:
            proxies = filtered
    
    if not proxies:
        if is_callback:
            await query.edit_message_text(
                get_luxury_message('no_results', language),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(get_luxury_message('back', language), callback_data="lx_buy_menu")]
                ])
            )
        else:
            if loading_msg:
                await loading_msg.edit_text(
                    get_luxury_message('no_results', language),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(get_luxury_message('back', language), callback_data="lx_buy_menu")]
                    ])
                )
        return
    
    import random
    proxy_data = random.choice(proxies) if len(proxies) > 1 else proxies[0]
    proxy_id = proxy_data.get('proxy_id', proxy_data.get('id', ''))
    
    context.user_data['pending_proxy'] = proxy_data
    context.user_data['pending_proxy_id'] = proxy_id
    
    flag = get_country_flag_luxury(proxy_data.get('country_code', proxy_data.get('countryCode', 'XX')))
    country_name = get_country_name(proxy_data.get('country_code', proxy_data.get('countryCode', 'XX')), language)
    
    duration_text = get_luxury_message('daily_proxy', language) if is_daily else get_luxury_message('hourly_proxy', language)
    confirm_callback = f"lx_confirm_{duration_type}_{proxy_id}"
    
    keyboard = [
        [InlineKeyboardButton(
            "✅ " + ("تأكيد الشراء" if language == 'ar' else "Confirm Purchase"),
            callback_data=confirm_callback
        )],
        [InlineKeyboardButton(
            get_luxury_message('cancel', language),
            callback_data="lx_buy_menu"
        )]
    ]
    
    confirm_text = f"""
<b>{"🛒 تأكيد الشراء" if language == 'ar' else "🛒 Confirm Purchase"}</b>

{"الدولة" if language == 'ar' else "Country"}: {flag} {country_name}
{"الولاية" if language == 'ar' else "State"}: {proxy_data.get('state', 'N/A')}
{"المدينة" if language == 'ar' else "City"}: {proxy_data.get('city', 'N/A')}
{"مزود الخدمة" if language == 'ar' else "ISP"}: {proxy_data.get('isp', 'N/A')}
{"النوع" if language == 'ar' else "Type"}: {duration_text}

💵 {"السعر" if language == 'ar' else "Price"}: {price:.2f} {"كريديت" if language == 'ar' else "credits"}
💰 {"رصيدك" if language == 'ar' else "Your balance"}: {balance:.2f} {"كريديت" if language == 'ar' else "credits"}

{"اضغط تأكيد الشراء للمتابعة" if language == 'ar' else "Click Confirm Purchase to proceed"}
"""
    
    if is_callback:
        await query.edit_message_text(
            confirm_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    else:
        if loading_msg:
            await loading_msg.edit_text(
                confirm_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )


async def luxury_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """قائمة الآدمن لخدمة Luxury"""
    query = update.callback_query
    if query:
        await query.answer()
    
    api_key = luxury_db.get_api_key()
    service_enabled = luxury_db.is_service_enabled()
    proxy_price = luxury_db.get_proxy_price()
    
    account_info = "غير متصل"
    if api_key:
        api = LuxuryAPI(api_key)
        result = api.get_balance()
        if result and not isinstance(result, dict):
            account_info = f"الرصيد: {result}"
        elif isinstance(result, dict) and 'balance' in result:
            account_info = f"الرصيد: ${result.get('balance', 0)}"
        elif isinstance(result, dict) and 'data' in result:
            account_info = f"الرصيد: ${result['data'].get('balance', 0)}"
    
    status_text = "مفعّل" if service_enabled else "معطّل"
    
    daily_price = luxury_db.get_proxy_price(daily=True)
    hourly_price = luxury_db.get_proxy_price(daily=False)
    
    text = f"""
<b>🌐 إدارة ستاتيك يومي (Luxury Support)</b>

<b>📊 حالة الخدمة:</b> {status_text}

<b>💵 أسعار البيع:</b>
• 📅 بروكسي 24 ساعة: <b>${daily_price}</b>
• ⏰ بروكسي 4 ساعات: <b>${hourly_price}</b>

<b>💰 معلومات الحساب:</b>
{account_info}
"""
    
    keyboard = [
        [InlineKeyboardButton(
            "🔴 إيقاف الخدمة" if service_enabled else "🟢 تشغيل الخدمة",
            callback_data="lx_admin_toggle"
        )],
        [InlineKeyboardButton("📅 سعر 24h", callback_data="lx_admin_price_daily"),
         InlineKeyboardButton("⏰ سعر 4h", callback_data="lx_admin_price_hourly")],
        [InlineKeyboardButton("🔑 مفتاح API", callback_data="lx_admin_apikey")],
        [InlineKeyboardButton("💰 رصيد الحساب", callback_data="lx_admin_balance")],
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


async def handle_luxury_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج callbacks الآدمن"""
    query = update.callback_query
    data = query.data
    
    if data == "lx_admin_toggle":
        current = luxury_db.is_service_enabled()
        new_status = '1' if not current else '0'
        luxury_db.set_setting('service_enabled', new_status)
        logger.info(f"Luxury service toggled to: {new_status}")
        await query.answer(f"تم {'تفعيل' if new_status == '1' else 'تعطيل'} الخدمة")
        await luxury_admin_menu(update, context)
    
    elif data == "lx_admin_price_daily":
        await query.answer()
        context.user_data['waiting_lx_price_daily'] = True
        current_price = luxury_db.get_proxy_price(daily=True)
        api_cost = luxury_db.get_api_cost(daily=True)
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="lx_admin_menu")]]
        await query.edit_message_text(
            f"📅 <b>تعديل سعر بروكسي 24 ساعة</b>\n\n"
            f"🏷️ تكلفة الموقع (API): <b>${api_cost}</b>\n"
            f"💵 سعر البيع الحالي: <b>${current_price}</b>\n\n"
            f"أرسل السعر الجديد بالدولار:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    
    elif data == "lx_admin_price_hourly":
        await query.answer()
        context.user_data['waiting_lx_price_hourly'] = True
        current_price = luxury_db.get_proxy_price(daily=False)
        api_cost = luxury_db.get_api_cost(daily=False)
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="lx_admin_menu")]]
        await query.edit_message_text(
            f"⏰ <b>تعديل سعر بروكسي 4 ساعات</b>\n\n"
            f"🏷️ تكلفة الموقع (API): <b>${api_cost}</b>\n"
            f"💵 سعر البيع الحالي: <b>${current_price}</b>\n\n"
            f"أرسل السعر الجديد بالدولار:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    
    elif data == "lx_admin_apikey":
        await query.answer()
        context.user_data['waiting_lx_apikey'] = True
        current_key = luxury_db.get_api_key()
        masked = current_key[:20] + "****" if current_key and len(current_key) > 20 else "غير محدد"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="lx_admin_menu")]]
        await query.edit_message_text(
            f"🔑 <b>تعديل مفتاح API</b>\n\n"
            f"المفتاح الحالي: <code>{masked}</code>\n\n"
            f"أرسل مفتاح API الجديد (Bearer token):",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    
    elif data == "lx_admin_balance":
        await query.answer()
        api_key = luxury_db.get_api_key()
        
        if not api_key:
            await query.edit_message_text(
                "مفتاح API غير محدد في الإعدادات",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="lx_admin_menu")]])
            )
            return
        
        api = LuxuryAPI(api_key)
        result = api.get_balance()
        
        if result:
            balance = result.get('balance', result) if isinstance(result, dict) else result
            if isinstance(result, dict) and 'data' in result:
                balance = result['data'].get('balance', 0)
            
            text = f"""
<b>معلومات حساب Luxury Support</b>

<b>الرصيد:</b> ${balance}
"""
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="lx_admin_menu")]]
            await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text(
                "❌ فشل في جلب المعلومات",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="lx_admin_menu")]])
            )
    
    elif data == "lx_admin_menu":
        await luxury_admin_menu(update, context)


async def handle_luxury_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """معالجة مدخلات الآدمن"""
    text = update.message.text.strip()
    
    if context.user_data.get('waiting_lx_price_daily'):
        try:
            price = float(text)
            if price < 0 or price > 1000:
                await update.message.reply_text("❌ السعر يجب أن يكون بين 0 و 1000")
                return True
            
            luxury_db.set_proxy_price(price, daily=True)
            context.user_data.pop('waiting_lx_price_daily', None)
            await update.message.reply_text(f"✅ تم تحديث سعر بروكسي 24 ساعة إلى ${price}")
            return True
        except ValueError:
            await update.message.reply_text("❌ أدخل رقماً صحيحاً")
            return True
    
    elif context.user_data.get('waiting_lx_price_hourly'):
        try:
            price = float(text)
            if price < 0 or price > 1000:
                await update.message.reply_text("❌ السعر يجب أن يكون بين 0 و 1000")
                return True
            
            luxury_db.set_proxy_price(price, daily=False)
            context.user_data.pop('waiting_lx_price_hourly', None)
            await update.message.reply_text(f"✅ تم تحديث سعر بروكسي 4 ساعات إلى ${price}")
            return True
        except ValueError:
            await update.message.reply_text("❌ أدخل رقماً صحيحاً")
            return True
    
    elif context.user_data.get('waiting_lx_apikey'):
        luxury_db.set_setting('luxury_api_key', text)
        context.user_data.pop('waiting_lx_apikey', None)
        
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        except:
            pass
        
        await update.message.reply_text("تم تحديث مفتاح API بنجاح")
        return True
    
    return False


async def handle_luxury_inline_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """معالجة اختيارات الـ inline query (الرسائل النصية /select_country, /select_state, /select_city)"""
    if not update.message or not update.message.text:
        return False
    
    text = update.message.text.strip()
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    if text.startswith("/select_country "):
        country_code = text.replace("/select_country ", "").strip()
        if country_code:
            await show_country_options_message(update, context, country_code)
            return True
    
    elif text.startswith("/select_state "):
        parts = text.replace("/select_state ", "").strip().split(" ", 1)
        country_code = parts[0] if len(parts) > 0 else ""
        state = parts[1] if len(parts) > 1 else ""
        if country_code and state:
            await show_city_options_message(update, context, country_code, state)
            return True
    
    elif text.startswith("/select_city "):
        parts = text.replace("/select_city ", "").strip().split(" ", 2)
        country_code = parts[0] if len(parts) > 0 else ""
        state = parts[1] if len(parts) > 1 else ""
        city = parts[2] if len(parts) > 2 else ""
        if country_code:
            await show_proxy_options_message(update, context, country_code, state, city)
            return True
    
    elif text.startswith("/select_isp "):
        parts = text.replace("/select_isp ", "").strip().split(" ", 3)
        country_code = parts[0] if len(parts) > 0 else ""
        state = parts[1] if len(parts) > 1 else ""
        city = parts[2] if len(parts) > 2 else ""
        isp = parts[3] if len(parts) > 3 else ""
        if country_code and isp:
            await show_isp_confirm_message(update, context, country_code, state, city, isp)
            return True
    
    elif text.startswith("/select_proxy "):
        proxy_id = text.replace("/select_proxy ", "").strip()
        if proxy_id:
            await show_proxy_buy_confirm(update, context, proxy_id)
            return True
    
    return False


async def show_country_options_message(update: Update, context: ContextTypes.DEFAULT_TYPE, country_code: str) -> None:
    """عرض خيارات بعد اختيار دولة من inline query"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    price = luxury_db.get_proxy_price()
    
    flag = get_country_flag_luxury(country_code)
    country_name = get_country_name(country_code, language)
    duration_type = context.user_data.get('lx_duration', 'daily')
    duration_text = get_luxury_message('daily_proxy', language) if duration_type == 'daily' else get_luxury_message('hourly_proxy', language)
    
    keyboard = [
        [InlineKeyboardButton(
            "📍 " + ("اختيار ولاية" if language == 'ar' else "Select State"),
            switch_inline_query_current_chat=f"lu_static:state:{country_code}: "
        )],
        [InlineKeyboardButton(
            "📮 " + ("بحث برمز ZIP" if language == 'ar' else "Search by ZIP Code"),
            switch_inline_query_current_chat=f"lu_static:zip:{country_code}: "
        )],
        [InlineKeyboardButton(
            "⏭️ " + ("تخطي الولاية" if language == 'ar' else "Skip State"),
            callback_data=f"lx_skip_state_{country_code}"
        )],
        [InlineKeyboardButton(
            "⚡ " + ("شراء سريع" if language == 'ar' else "Quick Buy"),
            callback_data=f"lx_buy_random_{country_code}__"
        )],
        [InlineKeyboardButton(
            get_luxury_message('back', language),
            callback_data="lx_buy_menu"
        )]
    ]
    
    text = f"""
<b>{"🌍 اختيار البروكسي" if language == 'ar' else "🌍 Select Proxy"}</b>

{"الدولة" if language == 'ar' else "Country"}: {flag} {country_name}
{"النوع" if language == 'ar' else "Type"}: {duration_text}
💵 {"السعر" if language == 'ar' else "Price"}: {price} {"كريديت" if language == 'ar' else "credits"}

{"اختر ولاية أو ابحث برمز ZIP أو اشترِ بروكسي عشوائي" if language == 'ar' else "Select a state, search by ZIP, or buy a random proxy"}
"""
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def show_city_options_message(update: Update, context: ContextTypes.DEFAULT_TYPE, country_code: str, state: str) -> None:
    """عرض خيارات بعد اختيار ولاية من inline query"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    flag = get_country_flag_luxury(country_code)
    country_name = get_country_name(country_code, language)
    state_safe = state.replace(" ", "-")
    
    keyboard = [
        [InlineKeyboardButton(
            "🏙️ " + ("اختيار مدينة" if language == 'ar' else "Select City"),
            switch_inline_query_current_chat=f"lu_static:city:{country_code}:{state}: "
        )],
        [InlineKeyboardButton(
            "⏭️ " + ("تخطي المدينة" if language == 'ar' else "Skip City"),
            callback_data=f"lx_skip_city_{country_code}_{state_safe}"
        )],
        [InlineKeyboardButton(
            "⚡ " + ("شراء سريع" if language == 'ar' else "Quick Buy"),
            callback_data=f"lx_buy_random_{country_code}_{state_safe}_"
        )],
        [InlineKeyboardButton(
            get_luxury_message('back', language),
            callback_data=f"lx_country_{country_code}"
        )]
    ]
    
    text = f"""
<b>{"📍 اختيار المدينة" if language == 'ar' else "📍 Select City"}</b>

{"الدولة" if language == 'ar' else "Country"}: {flag} {country_name}
{"الولاية" if language == 'ar' else "State"}: {state}

{"اختر مدينة أو اشترِ بروكسي عشوائي من هذه الولاية" if language == 'ar' else "Select a city or buy a random proxy from this state"}
"""
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def show_proxy_options_message(update: Update, context: ContextTypes.DEFAULT_TYPE, country_code: str, state: str, city: str) -> None:
    """عرض خيارات بعد اختيار مدينة من inline query - اختيار ISP"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    price = luxury_db.get_proxy_price()
    
    flag = get_country_flag_luxury(country_code)
    country_name = get_country_name(country_code, language)
    state_safe = state.replace(" ", "-") if state else ""
    city_safe = city.replace(" ", "-") if city else ""
    
    keyboard = [
        [InlineKeyboardButton(
            "🏢 " + ("اختيار مزود الخدمة" if language == 'ar' else "Select ISP"),
            switch_inline_query_current_chat=f"lu_static:isp:{country_code}:{state_safe}:{city_safe}: "
        )],
        [InlineKeyboardButton(
            "⏭️ " + ("تخطي ISP" if language == 'ar' else "Skip ISP"),
            callback_data=f"lx_buy_random_{country_code}_{state_safe}_{city_safe}"
        )],
        [InlineKeyboardButton(
            get_luxury_message('back', language),
            callback_data=f"lx_state_{country_code}_{state_safe}" if state else f"lx_country_{country_code}"
        )]
    ]
    
    text = f"""
<b>{"🏙️ اختيار مزود الخدمة" if language == 'ar' else "🏙️ Select ISP"}</b>

{"الدولة" if language == 'ar' else "Country"}: {flag} {country_name}
{"الولاية" if language == 'ar' else "State"}: {state or 'N/A'}
{"المدينة" if language == 'ar' else "City"}: {city or 'N/A'}

💵 {"السعر" if language == 'ar' else "Price"}: {price} {"كريديت" if language == 'ar' else "credits"}

{"اختر مزود خدمة الإنترنت أو تخطى للشراء مباشرة" if language == 'ar' else "Select an ISP or skip to buy directly"}
"""
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
)


async def show_isp_confirm_message(update: Update, context: ContextTypes.DEFAULT_TYPE, country_code: str, state: str, city: str, isp: str) -> None:
    """عرض تأكيد الشراء بعد اختيار ISP"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    price = luxury_db.get_proxy_price()
    
    flag = get_country_flag_luxury(country_code)
    country_name = get_country_name(country_code, language)
    state_safe = state.replace("-", " ") if state else ""
    city_safe = city.replace("-", " ") if city else ""
    isp_safe = isp.replace("-", " ") if isp else ""
    
    # حفظ ISP في user_data للاستخدام عند الشراء
    context.user_data['lx_isp'] = isp_safe
    
    keyboard = [
        [InlineKeyboardButton(
            "✅ " + ("شراء الآن" if language == 'ar' else "Buy Now"),
            callback_data=f"lx_buy_isp_{country_code}_{state.replace(' ', '-')}_{city.replace(' ', '-')}_{isp.replace(' ', '-')}"
        )],
        [InlineKeyboardButton(
            get_luxury_message('back', language),
            callback_data=f"lx_city_{country_code}_{state.replace(' ', '-')}_{city.replace(' ', '-')}"
        )]
    ]
    
    text = f"""
<b>{"✅ تأكيد الشراء" if language == 'ar' else "✅ Confirm Purchase"}</b>

{"الدولة" if language == 'ar' else "Country"}: {flag} {country_name}
{"الولاية" if language == 'ar' else "State"}: {state_safe or 'N/A'}
{"المدينة" if language == 'ar' else "City"}: {city_safe or 'N/A'}
{"مزود الخدمة" if language == 'ar' else "ISP"}: 🏢 {isp_safe or 'N/A'}

💵 {"السعر" if language == 'ar' else "Price"}: {price} {"كريديت" if language == 'ar' else "credits"}

{"اضغط شراء الآن للحصول على بروكسي" if language == 'ar' else "Click Buy Now to get a proxy"}
"""
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def handle_luxury_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج Inline Query للبحث عن البروكسيات"""
    query = update.inline_query
    query_text = query.query.strip()
    user_id = query.from_user.id
    language = get_user_language(user_id)
    
    if not query_text.startswith("lu_static:"):
        return
    
    parts = query_text.split(":")
    search_type = parts[1] if len(parts) > 1 else ""
    
    api_key = luxury_db.get_api_key()
    if not api_key:
        return
    
    api = LuxuryAPI(api_key)
    results = []
    
    try:
        if search_type == "country":
            country_list = api.get_country_list()
            if isinstance(country_list, dict):
                countries = country_list.get('result', country_list.get('data', []))
            else:
                countries = country_list if isinstance(country_list, list) else []
            
            search_term = parts[2].strip().lower() if len(parts) > 2 else ""
            
            # الدول الأكثر شيوعاً - تظهر أولاً عند عدم وجود بحث
            popular_countries = ['US', 'GB', 'DE', 'FR', 'CA', 'AU', 'NL', 'JP', 'KR', 'SG', 'AE', 'SA']
            
            # تصفية الدول حسب البحث أولاً
            filtered_countries = []
            for country in countries:
                if isinstance(country, dict):
                    code = country.get('countryCode', country.get('country_code', ''))
                    name = country.get('countryName', get_country_name(code, language))
                else:
                    code = country
                    name = get_country_name(code, language)
                
                # إذا كان هناك بحث، تحقق من المطابقة
                if search_term:
                    if search_term not in name.lower() and search_term not in code.lower():
                        continue
                
                filtered_countries.append({'code': code, 'name': name})
            
            # ترتيب الدول - الشائعة أولاً إذا لم يكن هناك بحث
            if not search_term:
                def sort_key(c):
                    if c['code'] in popular_countries:
                        return (0, popular_countries.index(c['code']))
                    return (1, c['name'])
                filtered_countries.sort(key=sort_key)
            
            # تحديد النتائج إلى 50
            for country in filtered_countries[:50]:
                code = country['code']
                name = country['name']
                flag_url = f"https://flagcdn.com/w80/{code.lower()}.png"
                
                results.append(InlineQueryResultArticle(
                    id=f"country_{code}",
                    title=name,
                    description=f"اختر {name}" if language == 'ar' else f"Select {name}",
                    thumbnail_url=flag_url,
                    input_message_content=InputTextMessageContent(
                        message_text=f"/select_country {code}"
                    )
                ))
        
        elif search_type == "state":
            country_code = parts[2] if len(parts) > 2 else ""
            search_term = parts[3].strip().lower() if len(parts) > 3 else ""
            
            state_list = api.get_states_by_country(country_code)
            if isinstance(state_list, dict):
                states = state_list.get('result', state_list.get('data', []))
            else:
                states = state_list if isinstance(state_list, list) else []
            
            flag_url = f"https://flagcdn.com/w80/{country_code.lower()}.png"
            for state in states[:50]:
                if isinstance(state, dict):
                    state_name = state.get('stateName', state.get('state', ''))
                else:
                    state_name = str(state)
                
                if search_term and search_term not in state_name.lower():
                    continue
                
                results.append(InlineQueryResultArticle(
                    id=f"state_{country_code}_{state_name}",
                    title=f"📍 {state_name}",
                    description=f"اختر {state_name}" if language == 'ar' else f"Select {state_name}",
                    thumbnail_url=flag_url,
                    input_message_content=InputTextMessageContent(
                        message_text=f"/select_state {country_code} {state_name}"
                    )
                ))
        
        elif search_type == "city":
            country_code = parts[2] if len(parts) > 2 else ""
            state = parts[3].replace("-", " ") if len(parts) > 3 else ""
            search_term = parts[4].strip().lower() if len(parts) > 4 else ""
            
            logger.info(f"City inline query: country={country_code}, state={state}, search={search_term}")
            
            if state:
                city_list = api.get_cities_by_state(state)
            else:
                city_list = api.get_city_list()
            
            logger.info(f"City list response: {str(city_list)[:300]}")
            
            if isinstance(city_list, dict):
                cities = city_list.get('result', city_list.get('data', city_list.get('cities', [])))
                if not cities:
                    for key, val in city_list.items():
                        if isinstance(val, list) and len(val) > 0:
                            cities = val
                            break
            else:
                cities = city_list if isinstance(city_list, list) else []
            
            logger.info(f"Found {len(cities) if cities else 0} cities")
            
            flag_url = f"https://flagcdn.com/w80/{country_code.lower()}.png"
            import hashlib
            for city in (cities or [])[:50]:
                if isinstance(city, dict):
                    city_name = city.get('cityName', city.get('city', city.get('name', '')))
                elif isinstance(city, str):
                    city_name = city
                else:
                    continue
                
                if not city_name:
                    continue
                
                if search_term and search_term not in city_name.lower():
                    continue
                
                state_safe = state.replace(" ", "-") if state else ""
                
                result_id = hashlib.md5(f"city_{country_code}_{state_safe}_{city_name}".encode()).hexdigest()[:32]
                
                results.append(InlineQueryResultArticle(
                    id=result_id,
                    title=f"🏙️ {city_name}",
                    description=f"📍 {state}" if state else (f"اختر {city_name}" if language == 'ar' else f"Select {city_name}"),
                    thumbnail_url=flag_url,
                    input_message_content=InputTextMessageContent(
                        message_text=f"/select_city {country_code} {state_safe} {city_name}"
                    )
                ))
        
        elif search_type == "isp":
            country_code = parts[2] if len(parts) > 2 else ""
            state = parts[3].replace("-", " ") if len(parts) > 3 else ""
            city = parts[4].replace("-", " ") if len(parts) > 4 else ""
            search_term = parts[5].strip().lower() if len(parts) > 5 else ""
            
            logger.info(f"ISP inline query: country={country_code}, state={state}, city={city}, search={search_term}")
            
            isp_list = api.get_isp_list()
            
            if isinstance(isp_list, dict):
                isps = isp_list.get('result', isp_list.get('data', []))
            elif isinstance(isp_list, list):
                isps = isp_list
            else:
                isps = []
            
            logger.info(f"Found {len(isps) if isps else 0} ISPs")
            
            import hashlib
            flag_url = f"https://flagcdn.com/w80/{country_code.lower()}.png"
            added_count = 0
            for isp in (isps or []):
                if isinstance(isp, dict):
                    isp_name = isp.get('isp', isp.get('name', ''))
                elif isinstance(isp, str):
                    isp_name = isp
                else:
                    continue
                
                if not isp_name:
                    continue
                
                if search_term and search_term not in isp_name.lower():
                    continue
                
                state_safe = state.replace(" ", "-") if state else ""
                city_safe = city.replace(" ", "-") if city else ""
                isp_safe = isp_name.replace(" ", "-").replace("/", "_").replace("\\", "_").replace(":", "_")
                
                result_id = hashlib.md5(f"isp_{isp_name}".encode()).hexdigest()[:32]
                
                results.append(InlineQueryResultArticle(
                    id=result_id,
                    title=f"🏢 {isp_name[:55]}",
                    description=f"📍 {city}, {state}" if city else (f"اختر مزود الخدمة" if language == 'ar' else f"Select ISP"),
                    thumbnail_url=flag_url,
                    input_message_content=InputTextMessageContent(
                        message_text=f"/select_isp {country_code} {state_safe} {city_safe} {isp_safe}"
                    )
                ))
                added_count += 1
                if added_count >= 50:
                    break
            
            logger.info(f"Added {added_count} ISP results")
        
        elif search_type == "zip":
            country_code = parts[2] if len(parts) > 2 else ""
            zip_code = parts[3].strip() if len(parts) > 3 else ""
            
            logger.info(f"ZIP inline query: country={country_code}, zip={zip_code}")
            
            if zip_code and len(zip_code) >= 3:
                proxy_list = api.search_proxies(zip_code=zip_code, limit=50)
                logger.info(f"ZIP search response: {str(proxy_list)[:500]}")
                
                if isinstance(proxy_list, dict):
                    proxies = proxy_list.get('proxies', proxy_list.get('result', proxy_list.get('data', [])))
                else:
                    proxies = proxy_list if isinstance(proxy_list, list) else []
                
                if country_code and proxies:
                    proxies = [p for p in proxies if isinstance(p, dict) and 
                              p.get('countryCode', p.get('country_code', '')).upper() == country_code.upper()]
                
                logger.info(f"Found {len(proxies) if proxies else 0} proxies for ZIP (after country filter)")
                
                import hashlib
                if proxies:
                    for proxy in proxies[:30]:
                        if isinstance(proxy, dict):
                            proxy_id = proxy.get('proxy_id', proxy.get('id', ''))
                            city = proxy.get('city', 'N/A')
                            state = proxy.get('state', 'N/A')
                            isp = proxy.get('isp', 'N/A')
                            zip_val = proxy.get('zipCode', proxy.get('zip_code', proxy.get('zip', '')))
                            proxy_country = proxy.get('countryCode', proxy.get('country_code', country_code))
                            flag_url = f"https://flagcdn.com/w80/{proxy_country.lower()}.png"
                            
                            result_id = hashlib.md5(f"zip_{proxy_id}".encode()).hexdigest()[:32]
                            
                            results.append(InlineQueryResultArticle(
                                id=result_id,
                                title=f"📮 {zip_val} - {city}",
                                description=f"🏢 {isp[:35]} | 📍 {state}",
                                thumbnail_url=flag_url,
                                input_message_content=InputTextMessageContent(
                                    message_text=f"/select_proxy {proxy_id}"
                                )
                            ))
                else:
                    results.append(InlineQueryResultArticle(
                        id="no_zip_results",
                        title="❌ " + ("لا توجد نتائج لهذا الرمز" if language == 'ar' else "No results for this ZIP"),
                        description="جرب: 10001, 90210, 33101" if language == 'ar' else "Try: 10001, 90210, 33101",
                        input_message_content=InputTextMessageContent(
                            message_text="💡 " + ("أمثلة ZIP صالحة: 10001 (نيويورك), 90210 (كاليفورنيا), 33101 (فلوريدا)" if language == 'ar' else "Valid ZIP examples: 10001 (NY), 90210 (CA), 33101 (FL)")
                        )
                    ))
            else:
                results.append(InlineQueryResultArticle(
                    id="zip_hint",
                    title="📮 " + ("أدخل 3 أرقام على الأقل" if language == 'ar' else "Enter at least 3 digits"),
                    description="مثال: 10001, 90210" if language == 'ar' else "Example: 10001, 90210",
                    input_message_content=InputTextMessageContent(
                        message_text="💡 " + ("ابحث برمز ZIP مثل 10001 أو 90210" if language == 'ar' else "Search by ZIP code like 10001 or 90210")
                    )
                ))
    
    except Exception as e:
        logger.error(f"Error in inline query: {e}")
    
    await query.answer(results[:50], cache_time=60)
