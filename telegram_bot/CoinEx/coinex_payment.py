#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================
📍 نظام الدفع التلقائي عبر CoinEx - coinex_payment.py
============================================
يحتوي على:
1. CoinExAPIv2 - عميل API مع توثيق HMAC SHA256
2. CoinExDepositFetcher - جلب الإيداعات من CoinEx
3. PaymentMatcher - مطابقة الإيداعات مع طلبات الدفع
4. دوال قاعدة البيانات - SQLite
5. دوال الإشعارات - Telegram
============================================
"""

import hmac
import hashlib
import time
import json
import sqlite3
import logging
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Any, Tuple, Union
from urllib.parse import urlencode
import requests

try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False

from bot_utils import get_syria_time, get_syria_time_str, escape_html
from config import Config, DATABASE_FILE, ADMIN_IDS

logger = logging.getLogger(__name__)

SYRIA_TZ = pytz.timezone('Asia/Damascus') if PYTZ_AVAILABLE else None


# ============================================
# 📍 قسم 1: CoinExAPIv2 - عميل API
# ============================================

class CoinExAPIv2:
    """
    CoinEx API v2 Client with proper HMAC SHA256 authentication
    
    عميل API v2 لـ CoinEx مع توثيق HMAC SHA256 الصحيح
    
    Base URL: https://api.coinex.com/v2
    Signature: METHOD + REQUEST_PATH + BODY + TIMESTAMP
    Headers: X-COINEX-KEY, X-COINEX-SIGN, X-COINEX-TIMESTAMP
    """
    
    BASE_URL = "https://api.coinex.com/v2"
    
    def __init__(self, access_id: str = None, secret_key: str = None):
        """
        تهيئة عميل API
        
        Args:
            access_id: معرف الوصول (API Key)
            secret_key: المفتاح السري
        """
        self.access_id = (access_id or "").strip()
        self.secret_key = (secret_key or "").strip()
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json"
        })
    
    def set_credentials(self, access_id: str, secret_key: str):
        """تحديث بيانات الاعتماد"""
        self.access_id = access_id.strip() if access_id else ""
        self.secret_key = secret_key.strip() if secret_key else ""
    
    def _get_timestamp(self) -> str:
        """الحصول على الطابع الزمني بالمللي ثانية"""
        return str(int(time.time() * 1000))
    
    def _generate_signature(self, method: str, request_path: str, 
                           body: str, timestamp: str) -> str:
        """
        توليد التوقيع الصحيح لـ CoinEx API v2
        
        الصيغة: METHOD + REQUEST_PATH + BODY + TIMESTAMP
        مثال: GET/v2/assets/deposit-history?ccy=USDT1700000000000
        
        Args:
            method: طريقة الطلب (GET, POST, etc.)
            request_path: المسار الكامل مع المعاملات
            body: جسم الطلب (للـ POST)
            timestamp: الطابع الزمني
            
        Returns:
            التوقيع المُولَّد (hexdigest lowercase)
        """
        prepared_str = f"{method}{request_path}{body}{timestamp}"
        
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            prepared_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest().lower()
        
        return signature
    
    def _get_headers(self, method: str, request_path: str, body: str = "") -> dict:
        """
        إنشاء الرؤوس المطلوبة للطلب
        
        Args:
            method: طريقة الطلب
            request_path: المسار الكامل
            body: جسم الطلب
            
        Returns:
            قاموس الرؤوس
        """
        timestamp = self._get_timestamp()
        signature = self._generate_signature(method, request_path, body, timestamp)
        
        return {
            "X-COINEX-KEY": self.access_id,
            "X-COINEX-SIGN": signature,
            "X-COINEX-TIMESTAMP": timestamp,
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json"
        }
    
    def request(self, method: str, endpoint: str, 
                params: dict = None, data: dict = None,
                timeout: int = 30) -> dict:
        """
        إرسال طلب إلى CoinEx API
        
        Args:
            method: طريقة الطلب (GET, POST)
            endpoint: نقطة النهاية (مثل /assets/deposit-history)
            params: معاملات الاستعلام (للـ GET)
            data: البيانات (للـ POST)
            timeout: مهلة الطلب بالثواني
            
        Returns:
            استجابة API كقاموس
        """
        method = method.upper()
        
        request_path = f"/v2{endpoint}"
        if method == "GET" and params:
            sorted_params = sorted(params.items())
            query_string = urlencode(sorted_params)
            request_path = f"/v2{endpoint}?{query_string}"
        
        body = ""
        if method == "POST" and data:
            body = json.dumps(data, separators=(',', ':'), sort_keys=True)
        
        headers = self._get_headers(method, request_path, body)
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            if method == "GET":
                if params:
                    sorted_params = sorted(params.items())
                    response = self.session.get(url, params=sorted_params, headers=headers, timeout=timeout)
                else:
                    response = self.session.get(url, headers=headers, timeout=timeout)
            elif method == "POST":
                response = self.session.post(url, data=body, headers=headers, timeout=timeout)
            else:
                return {"code": -1, "message": f"Unsupported method: {method}", "data": None}
            
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 0:
                logger.warning(f"⚠️ CoinEx API Warning: {result.get('message')} (code: {result.get('code')})")
            
            return result
            
        except requests.exceptions.Timeout:
            logger.error(f"❌ CoinEx API Timeout: {endpoint}")
            return {"code": -2, "message": "Request timeout", "data": None}
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ CoinEx API Connection Error: {e}")
            return {"code": -3, "message": f"Connection error: {str(e)}", "data": None}
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ CoinEx API HTTP Error: {e}")
            return {"code": -4, "message": f"HTTP error: {str(e)}", "data": None}
        except json.JSONDecodeError as e:
            logger.error(f"❌ CoinEx API JSON Decode Error: {e}")
            return {"code": -5, "message": f"JSON decode error: {str(e)}", "data": None}
        except Exception as e:
            logger.error(f"❌ CoinEx API Error: {e}")
            return {"code": -1, "message": str(e), "data": None}
    
    def get_account_info(self) -> dict:
        """الحصول على معلومات الحساب"""
        return self.request("GET", "/account/info")
    
    def get_balance(self, currency: str = None) -> dict:
        """
        الحصول على الرصيد
        
        Args:
            currency: العملة (اختياري)
        """
        params = {}
        if currency:
            params["ccy"] = currency
        return self.request("GET", "/assets/spot/balance", params=params)
    
    def get_deposit_history(self, currency: str = None, status: str = None,
                           tx_id: str = None, page: int = 1, limit: int = 100) -> dict:
        """
        الحصول على سجل الإيداعات
        
        Args:
            currency: العملة (اختياري)
            status: حالة الإيداع (processing, confirming, finish, failed)
            tx_id: معرف المعاملة (اختياري)
            page: رقم الصفحة
            limit: عدد النتائج (1-100)
            
        Returns:
            قائمة الإيداعات
        """
        params = {"page": page, "limit": min(limit, 100)}
        
        if currency:
            params["ccy"] = currency
        if status:
            params["status"] = status
        if tx_id:
            params["tx_id"] = tx_id
        
        return self.request("GET", "/assets/deposit-history", params=params)
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        اختبار الاتصال بـ API
        
        Returns:
            (نجاح, رسالة)
        """
        try:
            result = self.get_account_info()
            if result.get("code") == 0:
                return True, "✅ الاتصال ناجح"
            else:
                return False, f"❌ خطأ: {result.get('message')}"
        except Exception as e:
            return False, f"❌ خطأ في الاتصال: {str(e)}"


# ============================================
# 📍 قسم 2: CoinExDepositFetcher - جلب الإيداعات
# ============================================

class CoinExDepositFetcher:
    """
    خدمة جلب الإيداعات من CoinEx API v2
    
    تجلب الإيداعات وتخزنها في قاعدة البيانات المحلية
    """
    
    SUPPORTED_CURRENCIES = ['USDT', 'LTC', 'BTC', 'ETH', 'BNB', 'TRX', 'USDC']
    
    STATUS_MAP = {
        'processing': 'pending',
        'confirming': 'confirming',
        'finish': 'confirmed',
        'finished': 'confirmed',
        'confirmed': 'confirmed',
        'failed': 'failed'
    }
    
    CONFIRMATIONS_MAP = {
        'BSC': 15,
        'ETH': 12,
        'TRC20': 20,
        'TRX': 20,
        'LTC': 6,
        'BTC': 3,
        'CSC': 10
    }
    
    def __init__(self, api_client: CoinExAPIv2 = None, db_path: str = None):
        """
        تهيئة خدمة جلب الإيداعات
        
        Args:
            api_client: عميل CoinEx API
            db_path: مسار قاعدة البيانات
        """
        self.api = api_client or CoinExAPIv2()
        self.db_path = db_path or DATABASE_FILE
        self.last_fetch_time = {}
    
    def fetch_deposits(self, currency: str = None, status: str = None,
                      page: int = 1, limit: int = 100) -> List[dict]:
        """
        جلب الإيداعات من CoinEx
        
        Args:
            currency: العملة (اختياري)
            status: حالة الإيداع (اختياري)
            page: رقم الصفحة
            limit: عدد النتائج
        
        Returns:
            قائمة الإيداعات
        """
        try:
            response = self.api.get_deposit_history(
                currency=currency,
                status=status,
                page=page,
                limit=limit
            )
            
            if response.get("code") == 0:
                deposits = response.get("data", [])
                if deposits:
                    logger.info(f"✅ تم جلب {len(deposits)} إيداع من CoinEx")
                return deposits or []
            else:
                logger.error(f"❌ خطأ CoinEx: {response.get('message')}")
                return []
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الإيداعات: {e}")
            return []
    
    def fetch_all_currencies(self) -> List[dict]:
        """جلب الإيداعات لجميع العملات المدعومة"""
        all_deposits = []
        
        for currency in self.SUPPORTED_CURRENCIES:
            deposits = self.fetch_deposits(currency=currency)
            all_deposits.extend(deposits)
            time.sleep(0.2)
        
        return all_deposits
    
    def fetch_new_deposits(self) -> List[dict]:
        """جلب الإيداعات الجديدة (المعلقة والجارية والمكتملة)"""
        all_deposits = []
        
        for status in ['processing', 'confirming', 'finished']:
            deposits = self.fetch_deposits(status=status, limit=100)
            all_deposits.extend(deposits)
            time.sleep(0.2)
        
        return all_deposits
    
    def store_deposits(self, deposits: List[dict]) -> int:
        """
        تخزين الإيداعات في قاعدة البيانات
        
        Args:
            deposits: قائمة الإيداعات من API
            
        Returns:
            عدد الإيداعات المخزنة الجديدة
        """
        stored_count = 0
        syria_time = get_syria_time()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for d in deposits:
            try:
                deposit_id = str(d.get('deposit_id', ''))
                if not deposit_id:
                    continue
                
                cursor.execute(
                    "SELECT id, status FROM coinex_deposits WHERE deposit_id = ?",
                    (deposit_id,)
                )
                existing = cursor.fetchone()
                
                if existing:
                    new_status = self._map_status(d.get('status', ''))
                    if existing[1] != new_status:
                        cursor.execute('''
                            UPDATE coinex_deposits 
                            SET status = ?, confirmations = ?, updated_at = ?
                            WHERE deposit_id = ?
                        ''', (new_status, d.get('confirmations', 0), 
                              syria_time.strftime('%Y-%m-%d %H:%M:%S'), deposit_id))
                    continue
                
                created_at = d.get('created_at', 0)
                if isinstance(created_at, (int, float)) and created_at > 0:
                    timestamp_received = datetime.fromtimestamp(created_at / 1000)
                    if PYTZ_AVAILABLE and SYRIA_TZ:
                        timestamp_received = timestamp_received.astimezone(SYRIA_TZ)
                else:
                    timestamp_received = syria_time
                
                cursor.execute('''
                    INSERT INTO coinex_deposits (
                        deposit_id, tx_hash, sender_email, amount, currency, chain,
                        status, confirmations, timestamp_received, raw_payload, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    deposit_id,
                    d.get('tx_id', ''),
                    d.get('from_address', ''),
                    str(d.get('amount', '0')),
                    d.get('ccy', ''),
                    d.get('chain', ''),
                    self._map_status(d.get('status', '')),
                    d.get('confirmations', 0),
                    timestamp_received.strftime('%Y-%m-%d %H:%M:%S'),
                    json.dumps(d, ensure_ascii=False),
                    syria_time.strftime('%Y-%m-%d %H:%M:%S')
                ))
                stored_count += 1
                
            except Exception as e:
                logger.error(f"❌ خطأ في تخزين الإيداع {d.get('deposit_id')}: {e}")
        
        conn.commit()
        conn.close()
        
        if stored_count > 0:
            logger.info(f"✅ تم تخزين {stored_count} إيداع جديد")
        
        return stored_count
    
    def _map_status(self, coinex_status: str) -> str:
        """تحويل حالة CoinEx إلى حالة النظام"""
        return self.STATUS_MAP.get(coinex_status.lower(), 'pending')
    
    def _get_required_confirmations(self, chain: str) -> int:
        """الحصول على عدد التأكيدات المطلوبة حسب السلسلة"""
        return self.CONFIRMATIONS_MAP.get(chain.upper(), 10)
    
    def run_polling(self, interval: int = 30, max_iterations: int = None):
        """
        تشغيل حلقة الاستعلام الدورية (متزامنة)
        
        Args:
            interval: الفاصل الزمني بين الاستعلامات بالثواني
            max_iterations: الحد الأقصى للتكرارات (None = لا نهائي)
        """
        logger.info(f"🔄 بدء حلقة جلب الإيداعات (كل {interval} ثانية)")
        
        iteration = 0
        while max_iterations is None or iteration < max_iterations:
            try:
                deposits = self.fetch_new_deposits()
                if deposits:
                    self.store_deposits(deposits)
                    
            except Exception as e:
                logger.error(f"❌ خطأ في حلقة الاستعلام: {e}")
            
            iteration += 1
            time.sleep(interval)


# ============================================
# 📍 قسم 3: PaymentMatcher - مطابقة المدفوعات
# ============================================

class PaymentMatcher:
    """
    محرك مطابقة المدفوعات
    
    يطابق الإيداعات الواردة مع طلبات الدفع المعلقة
    
    أولويات المطابقة:
    1. tx_hash (100% confidence)
    2. sender_email (95% confidence)
    3. amount + time_window (70-85% confidence)
    """
    
    MATCH_CONFIDENCE = {
        'tx_hash': 1.00,
        'sender_email': 0.95,
        'amount_exact': 0.85,
        'amount_time': 0.75,
        'amount_only': 0.70,
        'manual': 1.00
    }
    
    def __init__(self, db_path: str = None):
        """
        تهيئة محرك المطابقة
        
        Args:
            db_path: مسار قاعدة البيانات
        """
        self.db_path = db_path or DATABASE_FILE
    
    def match_payment(self, user_id: int, expected_amount: Decimal, currency: str,
                     tx_hash: str = None, sender_email: str = None,
                     time_window_hours: int = 24) -> Tuple[Optional[dict], str, float]:
        """
        البحث عن إيداع مطابق لطلب دفع
        
        Args:
            user_id: معرف المستخدم
            expected_amount: المبلغ المتوقع
            currency: العملة
            tx_hash: معرف المعاملة (اختياري)
            sender_email: بريد المرسل (اختياري)
            time_window_hours: نافذة الوقت بالساعات
            
        Returns:
            (الإيداع, نوع المطابقة, نسبة الثقة)
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            if tx_hash:
                cursor.execute('''
                    SELECT * FROM coinex_deposits 
                    WHERE tx_hash = ? AND currency = ? AND matched_request_id IS NULL
                    LIMIT 1
                ''', (tx_hash, currency))
                deposit = cursor.fetchone()
                if deposit:
                    return dict(deposit), 'tx_hash', self.MATCH_CONFIDENCE['tx_hash']
            
            if sender_email:
                cursor.execute('''
                    SELECT * FROM coinex_deposits 
                    WHERE sender_email = ? AND currency = ? 
                    AND status = 'confirmed' AND matched_request_id IS NULL
                    ORDER BY timestamp_received DESC LIMIT 1
                ''', (sender_email, currency))
                deposit = cursor.fetchone()
                if deposit:
                    return dict(deposit), 'sender_email', self.MATCH_CONFIDENCE['sender_email']
            
            syria_time = get_syria_time()
            time_window_start = syria_time - timedelta(hours=time_window_hours)
            
            amount_tolerance = expected_amount * Decimal('0.01')
            min_amount = expected_amount - amount_tolerance
            max_amount = expected_amount + amount_tolerance
            
            cursor.execute('''
                SELECT * FROM coinex_deposits 
                WHERE currency = ? 
                AND CAST(amount AS REAL) BETWEEN ? AND ?
                AND status = 'confirmed'
                AND matched_request_id IS NULL
                AND datetime(timestamp_received) >= datetime(?)
                ORDER BY timestamp_received DESC
            ''', (currency, float(min_amount), float(max_amount),
                  time_window_start.strftime('%Y-%m-%d %H:%M:%S')))
            
            deposits = cursor.fetchall()
            
            if len(deposits) == 1:
                deposit = dict(deposits[0])
                deposit_amount = Decimal(str(deposit['amount']))
                if deposit_amount == expected_amount:
                    return deposit, 'amount_exact', self.MATCH_CONFIDENCE['amount_exact']
                else:
                    return deposit, 'amount_time', self.MATCH_CONFIDENCE['amount_time']
            elif len(deposits) > 1:
                logger.warning(f"⚠️ وجدنا {len(deposits)} إيداعات بنفس المبلغ - تحتاج تحقق يدوي")
                return None, 'multiple_matches', 0.0
            
            return None, 'no_match', 0.0
            
        except Exception as e:
            logger.error(f"❌ خطأ في مطابقة الدفع: {e}")
            return None, 'error', 0.0
        finally:
            conn.close()
    
    def confirm_match(self, deposit_id: int, request_id: int, 
                     match_type: str, confidence: float) -> bool:
        """
        تأكيد المطابقة بين إيداع وطلب
        
        Args:
            deposit_id: معرف الإيداع
            request_id: معرف الطلب
            match_type: نوع المطابقة
            confidence: نسبة الثقة
            
        Returns:
            نجاح العملية
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        syria_time = get_syria_time()
        
        try:
            cursor.execute('''
                UPDATE coinex_deposits 
                SET matched_request_id = ?, status = 'matched', updated_at = ?
                WHERE id = ?
            ''', (request_id, syria_time.strftime('%Y-%m-%d %H:%M:%S'), deposit_id))
            
            cursor.execute('''
                UPDATE coinex_payment_requests 
                SET matched_deposit_id = ?, status = 'matched', 
                    match_confidence = ?, matched_at = ?
                WHERE id = ?
            ''', (deposit_id, confidence, 
                  syria_time.strftime('%Y-%m-%d %H:%M:%S'), request_id))
            
            cursor.execute('''
                INSERT INTO coinex_payment_matches 
                (deposit_id, request_id, match_type, confidence, matched_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (deposit_id, request_id, match_type, confidence,
                  syria_time.strftime('%Y-%m-%d %H:%M:%S')))
            
            conn.commit()
            logger.info(f"✅ تم تأكيد المطابقة: Deposit {deposit_id} <-> Request {request_id}")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ خطأ في تأكيد المطابقة: {e}")
            return False
        finally:
            conn.close()
    
    def auto_match_pending(self) -> int:
        """
        مطابقة تلقائية للطلبات المعلقة مع الإيداعات المتاحة
        
        Returns:
            عدد المطابقات الناجحة
        """
        matched_count = 0
        
        pending_requests = get_pending_requests()
        
        for request in pending_requests:
            try:
                expected_amount = Decimal(str(request['expected_amount']))
                
                deposit, match_type, confidence = self.match_payment(
                    user_id=request['user_id'],
                    expected_amount=expected_amount,
                    currency=request['currency'],
                    tx_hash=request.get('tx_hash_provided'),
                    sender_email=request.get('sender_email')
                )
                
                if deposit and confidence >= 0.70:
                    success = self.confirm_match(
                        deposit_id=deposit['id'],
                        request_id=request['id'],
                        match_type=match_type,
                        confidence=confidence
                    )
                    if success:
                        matched_count += 1
                        
            except Exception as e:
                logger.error(f"❌ خطأ في المطابقة التلقائية للطلب {request.get('id')}: {e}")
        
        return matched_count


# ============================================
# 📍 قسم 4: دوال قاعدة البيانات
# ============================================

def get_db_connection(db_path: str = None) -> sqlite3.Connection:
    """الحصول على اتصال قاعدة البيانات"""
    conn = sqlite3.connect(db_path or DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_coinex_tables(db_path: str = None):
    """
    إنشاء جداول CoinEx في قاعدة البيانات
    
    Args:
        db_path: مسار قاعدة البيانات (اختياري)
    """
    conn = sqlite3.connect(db_path or DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coinex_deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deposit_id TEXT UNIQUE NOT NULL,
            tx_hash TEXT,
            sender_email TEXT,
            amount TEXT NOT NULL,
            currency TEXT NOT NULL,
            chain TEXT,
            status TEXT DEFAULT 'pending',
            confirmations INTEGER DEFAULT 0,
            timestamp_received TEXT,
            matched_request_id INTEGER,
            raw_payload TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coinex_payment_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            expected_amount TEXT NOT NULL,
            currency TEXT NOT NULL,
            payment_method TEXT DEFAULT 'coinex',
            sender_email TEXT,
            tx_hash_provided TEXT,
            status TEXT DEFAULT 'pending',
            matched_deposit_id INTEGER,
            match_confidence REAL,
            order_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT,
            matched_at TEXT,
            FOREIGN KEY (matched_deposit_id) REFERENCES coinex_deposits(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coinex_payment_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deposit_id INTEGER NOT NULL,
            request_id INTEGER NOT NULL,
            match_type TEXT NOT NULL,
            confidence REAL NOT NULL,
            matched_at TEXT DEFAULT CURRENT_TIMESTAMP,
            matched_by TEXT DEFAULT 'auto',
            notes TEXT,
            FOREIGN KEY (deposit_id) REFERENCES coinex_deposits(id),
            FOREIGN KEY (request_id) REFERENCES coinex_payment_requests(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coinex_settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_coinex_deposits_tx_hash ON coinex_deposits(tx_hash)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_coinex_deposits_status ON coinex_deposits(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_coinex_deposits_currency ON coinex_deposits(currency)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_coinex_requests_user_id ON coinex_payment_requests(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_coinex_requests_status ON coinex_payment_requests(status)')
    
    default_settings = [
        ('coinex_access_id', ''),
        ('coinex_secret_key', ''),
        ('auto_match_enabled', 'true'),
        ('polling_interval', '30'),
        ('time_window_hours', '24'),
        ('min_match_confidence', '0.70'),
        ('notify_admin_on_deposit', 'true'),
        ('notify_user_on_match', 'true')
    ]
    
    for key, value in default_settings:
        cursor.execute('''
            INSERT OR IGNORE INTO coinex_settings (key, value, updated_at) 
            VALUES (?, ?, ?)
        ''', (key, value, get_syria_time_str()))
    
    conn.commit()
    conn.close()
    logger.info("✅ تم إنشاء/تحديث جداول CoinEx")


def save_deposit(deposit_data: dict, db_path: str = None) -> Optional[int]:
    """
    حفظ إيداع جديد في قاعدة البيانات
    
    Args:
        deposit_data: بيانات الإيداع
        db_path: مسار قاعدة البيانات
        
    Returns:
        معرف الإيداع المُدخل أو None
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    syria_time = get_syria_time()
    
    try:
        cursor.execute('''
            INSERT INTO coinex_deposits (
                deposit_id, tx_hash, sender_email, amount, currency, chain,
                status, confirmations, timestamp_received, raw_payload, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            deposit_data.get('deposit_id', ''),
            deposit_data.get('tx_hash', ''),
            deposit_data.get('sender_email', ''),
            str(deposit_data.get('amount', '0')),
            deposit_data.get('currency', ''),
            deposit_data.get('chain', ''),
            deposit_data.get('status', 'pending'),
            deposit_data.get('confirmations', 0),
            deposit_data.get('timestamp_received', syria_time.strftime('%Y-%m-%d %H:%M:%S')),
            json.dumps(deposit_data.get('raw_payload', {}), ensure_ascii=False),
            syria_time.strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        conn.commit()
        deposit_id = cursor.lastrowid
        logger.info(f"✅ تم حفظ الإيداع: {deposit_data.get('deposit_id')}")
        return deposit_id
        
    except sqlite3.IntegrityError:
        logger.warning(f"⚠️ الإيداع موجود بالفعل: {deposit_data.get('deposit_id')}")
        return None
    except Exception as e:
        logger.error(f"❌ خطأ في حفظ الإيداع: {e}")
        return None
    finally:
        conn.close()


def get_pending_deposits(db_path: str = None) -> List[dict]:
    """
    الحصول على الإيداعات المعلقة (غير مطابقة)
    
    Args:
        db_path: مسار قاعدة البيانات
        
    Returns:
        قائمة الإيداعات المعلقة
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT * FROM coinex_deposits 
            WHERE matched_request_id IS NULL 
            AND status IN ('confirmed', 'pending', 'confirming')
            ORDER BY timestamp_received DESC
        ''')
        
        deposits = [dict(row) for row in cursor.fetchall()]
        return deposits
        
    except Exception as e:
        logger.error(f"❌ خطأ في جلب الإيداعات المعلقة: {e}")
        return []
    finally:
        conn.close()


def mark_deposit_matched(deposit_id: int, request_id: int, db_path: str = None) -> bool:
    """
    وسم إيداع كمطابق
    
    Args:
        deposit_id: معرف الإيداع
        request_id: معرف الطلب
        db_path: مسار قاعدة البيانات
        
    Returns:
        نجاح العملية
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    syria_time = get_syria_time()
    
    try:
        cursor.execute('''
            UPDATE coinex_deposits 
            SET matched_request_id = ?, status = 'matched', updated_at = ?
            WHERE id = ?
        ''', (request_id, syria_time.strftime('%Y-%m-%d %H:%M:%S'), deposit_id))
        
        conn.commit()
        return cursor.rowcount > 0
        
    except Exception as e:
        logger.error(f"❌ خطأ في وسم الإيداع كمطابق: {e}")
        return False
    finally:
        conn.close()


def save_payment_request(request_data: dict, db_path: str = None) -> Optional[int]:
    """
    حفظ طلب دفع جديد
    
    Args:
        request_data: بيانات طلب الدفع
        db_path: مسار قاعدة البيانات
        
    Returns:
        معرف الطلب المُدخل أو None
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    syria_time = get_syria_time()
    
    expires_hours = int(request_data.get('expires_hours', 24))
    expires_at = syria_time + timedelta(hours=expires_hours)
    
    try:
        cursor.execute('''
            INSERT INTO coinex_payment_requests (
                user_id, expected_amount, currency, payment_method,
                sender_email, tx_hash_provided, status, order_id,
                created_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request_data.get('user_id'),
            str(request_data.get('expected_amount', '0')),
            request_data.get('currency', 'USDT'),
            request_data.get('payment_method', 'coinex'),
            request_data.get('sender_email', ''),
            request_data.get('tx_hash_provided', ''),
            'pending',
            request_data.get('order_id', ''),
            syria_time.strftime('%Y-%m-%d %H:%M:%S'),
            expires_at.strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        conn.commit()
        request_id = cursor.lastrowid
        logger.info(f"✅ تم حفظ طلب الدفع للمستخدم: {request_data.get('user_id')}")
        return request_id
        
    except Exception as e:
        logger.error(f"❌ خطأ في حفظ طلب الدفع: {e}")
        return None
    finally:
        conn.close()


def get_pending_requests(db_path: str = None) -> List[dict]:
    """
    الحصول على طلبات الدفع المعلقة
    
    Args:
        db_path: مسار قاعدة البيانات
        
    Returns:
        قائمة الطلبات المعلقة
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    syria_time = get_syria_time()
    
    try:
        cursor.execute('''
            SELECT * FROM coinex_payment_requests 
            WHERE status = 'pending' 
            AND datetime(expires_at) > datetime(?)
            ORDER BY created_at ASC
        ''', (syria_time.strftime('%Y-%m-%d %H:%M:%S'),))
        
        requests = [dict(row) for row in cursor.fetchall()]
        return requests
        
    except Exception as e:
        logger.error(f"❌ خطأ في جلب طلبات الدفع المعلقة: {e}")
        return []
    finally:
        conn.close()


def update_request_status(request_id: int, status: str, db_path: str = None) -> bool:
    """
    تحديث حالة طلب الدفع
    
    Args:
        request_id: معرف الطلب
        status: الحالة الجديدة
        db_path: مسار قاعدة البيانات
        
    Returns:
        نجاح العملية
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    syria_time = get_syria_time()
    
    try:
        cursor.execute('''
            UPDATE coinex_payment_requests 
            SET status = ?, matched_at = ?
            WHERE id = ?
        ''', (status, syria_time.strftime('%Y-%m-%d %H:%M:%S') if status == 'matched' else None, request_id))
        
        conn.commit()
        return cursor.rowcount > 0
        
    except Exception as e:
        logger.error(f"❌ خطأ في تحديث حالة الطلب: {e}")
        return False
    finally:
        conn.close()


def get_coinex_settings(db_path: str = None) -> dict:
    """
    الحصول على إعدادات CoinEx
    
    Args:
        db_path: مسار قاعدة البيانات
        
    Returns:
        قاموس الإعدادات
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT key, value FROM coinex_settings')
        settings = {row['key']: row['value'] for row in cursor.fetchall()}
        return settings
        
    except Exception as e:
        logger.error(f"❌ خطأ في جلب إعدادات CoinEx: {e}")
        return {}
    finally:
        conn.close()


def save_coinex_settings(settings: dict, db_path: str = None) -> bool:
    """
    حفظ إعدادات CoinEx
    
    Args:
        settings: قاموس الإعدادات
        db_path: مسار قاعدة البيانات
        
    Returns:
        نجاح العملية
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    syria_time = get_syria_time()
    
    try:
        for key, value in settings.items():
            cursor.execute('''
                INSERT OR REPLACE INTO coinex_settings (key, value, updated_at)
                VALUES (?, ?, ?)
            ''', (key, str(value), syria_time.strftime('%Y-%m-%d %H:%M:%S')))
        
        conn.commit()
        logger.info("✅ تم حفظ إعدادات CoinEx")
        return True
        
    except Exception as e:
        logger.error(f"❌ خطأ في حفظ إعدادات CoinEx: {e}")
        return False
    finally:
        conn.close()


def get_deposit_by_tx_hash(tx_hash: str, db_path: str = None) -> Optional[dict]:
    """
    البحث عن إيداع بواسطة tx_hash
    
    Args:
        tx_hash: معرف المعاملة
        db_path: مسار قاعدة البيانات
        
    Returns:
        بيانات الإيداع أو None
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT * FROM coinex_deposits WHERE tx_hash = ?', (tx_hash,))
        row = cursor.fetchone()
        return dict(row) if row else None
        
    except Exception as e:
        logger.error(f"❌ خطأ في البحث عن الإيداع: {e}")
        return None
    finally:
        conn.close()


def get_user_payment_requests(user_id: int, db_path: str = None) -> List[dict]:
    """
    الحصول على طلبات الدفع لمستخدم معين
    
    Args:
        user_id: معرف المستخدم
        db_path: مسار قاعدة البيانات
        
    Returns:
        قائمة طلبات الدفع
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT * FROM coinex_payment_requests 
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        
        requests = [dict(row) for row in cursor.fetchall()]
        return requests
        
    except Exception as e:
        logger.error(f"❌ خطأ في جلب طلبات المستخدم: {e}")
        return []
    finally:
        conn.close()


def expire_old_requests(db_path: str = None) -> int:
    """
    انتهاء صلاحية الطلبات القديمة
    
    Args:
        db_path: مسار قاعدة البيانات
        
    Returns:
        عدد الطلبات المنتهية
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    syria_time = get_syria_time()
    
    try:
        cursor.execute('''
            UPDATE coinex_payment_requests 
            SET status = 'expired'
            WHERE status = 'pending' 
            AND datetime(expires_at) <= datetime(?)
        ''', (syria_time.strftime('%Y-%m-%d %H:%M:%S'),))
        
        expired_count = cursor.rowcount
        conn.commit()
        
        if expired_count > 0:
            logger.info(f"⏰ تم انتهاء صلاحية {expired_count} طلب دفع")
        
        return expired_count
        
    except Exception as e:
        logger.error(f"❌ خطأ في انتهاء صلاحية الطلبات: {e}")
        return 0
    finally:
        conn.close()


# ============================================
# 📍 قسم 5: دوال الإشعارات
# ============================================

async def send_admin_notification(bot, deposit: dict, is_new: bool = True):
    """
    إرسال إشعار للأدمن عن إيداع جديد
    
    Args:
        bot: كائن البوت
        deposit: بيانات الإيداع
        is_new: هل الإيداع جديد
    """
    if not ADMIN_IDS:
        logger.warning("⚠️ لا يوجد أدمن لإرسال الإشعار")
        return
    
    syria_time = get_syria_time()
    
    status_emoji = {
        'pending': '⏳',
        'confirming': '🔄',
        'confirmed': '✅',
        'matched': '🎯',
        'failed': '❌'
    }
    
    emoji = status_emoji.get(deposit.get('status', 'pending'), '📥')
    title = "📥 إيداع جديد" if is_new else "🔄 تحديث إيداع"
    
    message = f"""
{title} - CoinEx
━━━━━━━━━━━━━━━━━━━━

{emoji} <b>الحالة:</b> {escape_html(deposit.get('status', 'pending'))}

💰 <b>المبلغ:</b> {escape_html(deposit.get('amount', '0'))} {escape_html(deposit.get('currency', ''))}
⛓ <b>الشبكة:</b> {escape_html(deposit.get('chain', '-'))}
🔢 <b>التأكيدات:</b> {deposit.get('confirmations', 0)}

📝 <b>TX Hash:</b>
<code>{escape_html(deposit.get('tx_hash', '-'))}</code>

📧 <b>العنوان:</b>
<code>{escape_html(deposit.get('sender_email', '-'))}</code>

🕐 <b>الوقت:</b> {escape_html(deposit.get('timestamp_received', syria_time.strftime('%Y-%m-%d %H:%M:%S')))}

━━━━━━━━━━━━━━━━━━━━
📋 معرف الإيداع: <code>{escape_html(deposit.get('deposit_id', '-'))}</code>
"""
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=message.strip(),
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"❌ فشل إرسال إشعار للأدمن {admin_id}: {e}")


async def send_user_notification(bot, user_id: int, deposit: dict, request: dict):
    """
    إرسال إشعار للمستخدم عند مطابقة الدفع
    
    Args:
        bot: كائن البوت
        user_id: معرف المستخدم
        deposit: بيانات الإيداع
        request: بيانات الطلب
    """
    syria_time = get_syria_time()
    
    message = f"""
🎉 <b>تم تأكيد الدفع بنجاح!</b>
━━━━━━━━━━━━━━━━━━━━

✅ <b>تم استلام دفعتك ومطابقتها</b>

💰 <b>المبلغ:</b> {escape_html(deposit.get('amount', '0'))} {escape_html(deposit.get('currency', ''))}
⛓ <b>الشبكة:</b> {escape_html(deposit.get('chain', '-'))}

📝 <b>TX Hash:</b>
<code>{escape_html(deposit.get('tx_hash', '-'))}</code>

🕐 <b>وقت التأكيد:</b> {syria_time.strftime('%Y-%m-%d %H:%M:%S')}

━━━━━━━━━━━━━━━━━━━━
📋 رقم الطلب: <code>{escape_html(request.get('order_id', '-'))}</code>

شكراً لاستخدامك خدماتنا! 🙏
"""
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text=message.strip(),
            parse_mode='HTML'
        )
        logger.info(f"✅ تم إرسال إشعار المطابقة للمستخدم {user_id}")
    except Exception as e:
        logger.error(f"❌ فشل إرسال إشعار للمستخدم {user_id}: {e}")


async def send_payment_pending_notification(bot, user_id: int, request: dict):
    """
    إرسال إشعار للمستخدم بانتظار الدفع
    
    Args:
        bot: كائن البوت
        user_id: معرف المستخدم
        request: بيانات الطلب
    """
    syria_time = get_syria_time()
    expires_at = request.get('expires_at', '')
    
    message = f"""
⏳ <b>بانتظار الدفع</b>
━━━━━━━━━━━━━━━━━━━━

💰 <b>المبلغ المطلوب:</b> {escape_html(request.get('expected_amount', '0'))} {escape_html(request.get('currency', 'USDT'))}
📦 <b>طريقة الدفع:</b> CoinEx Transfer

📋 <b>رقم الطلب:</b> <code>{escape_html(request.get('order_id', '-'))}</code>

━━━━━━━━━━━━━━━━━━━━
⏰ <b>ينتهي في:</b> {escape_html(expires_at)}

💡 <b>ملاحظة:</b> سيتم التحقق تلقائياً عند وصول الإيداع
"""
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text=message.strip(),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"❌ فشل إرسال إشعار الانتظار للمستخدم {user_id}: {e}")


def send_admin_notification_sync(bot_token: str, deposit: dict, is_new: bool = True):
    """
    إرسال إشعار للأدمن بشكل متزامن (للاستخدام خارج async context)
    
    Args:
        bot_token: توكن البوت
        deposit: بيانات الإيداع
        is_new: هل الإيداع جديد
    """
    if not ADMIN_IDS:
        return
    
    import requests as req
    
    syria_time = get_syria_time()
    
    status_emoji = {
        'pending': '⏳',
        'confirming': '🔄',
        'confirmed': '✅',
        'matched': '🎯',
        'failed': '❌'
    }
    
    emoji = status_emoji.get(deposit.get('status', 'pending'), '📥')
    title = "📥 إيداع جديد" if is_new else "🔄 تحديث إيداع"
    
    message = f"""
{title} - CoinEx
━━━━━━━━━━━━━━━━━━━━

{emoji} <b>الحالة:</b> {escape_html(deposit.get('status', 'pending'))}

💰 <b>المبلغ:</b> {escape_html(deposit.get('amount', '0'))} {escape_html(deposit.get('currency', ''))}
⛓ <b>الشبكة:</b> {escape_html(deposit.get('chain', '-'))}
🔢 <b>التأكيدات:</b> {deposit.get('confirmations', 0)}

📝 <b>TX Hash:</b>
<code>{escape_html(deposit.get('tx_hash', '-'))}</code>

🕐 <b>الوقت:</b> {escape_html(deposit.get('timestamp_received', syria_time.strftime('%Y-%m-%d %H:%M:%S')))}
"""
    
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    for admin_id in ADMIN_IDS:
        try:
            req.post(api_url, json={
                "chat_id": admin_id,
                "text": message.strip(),
                "parse_mode": "HTML"
            })
        except Exception as e:
            logger.error(f"❌ فشل إرسال إشعار للأدمن {admin_id}: {e}")


# ============================================
# 📍 قسم 6: خدمة المراقبة الشاملة
# ============================================

class CoinExPaymentService:
    """
    خدمة الدفع الشاملة عبر CoinEx
    
    تجمع بين جلب الإيداعات والمطابقة والإشعارات
    """
    
    def __init__(self, access_id: str = None, secret_key: str = None,
                 db_path: str = None, bot_token: str = None):
        """
        تهيئة الخدمة
        
        Args:
            access_id: معرف API
            secret_key: المفتاح السري
            db_path: مسار قاعدة البيانات
            bot_token: توكن البوت للإشعارات
        """
        self.db_path = db_path or DATABASE_FILE
        self.bot_token = bot_token or getattr(Config, 'TOKEN', '')
        
        init_coinex_tables(self.db_path)
        
        settings = get_coinex_settings(self.db_path)
        
        self.api = CoinExAPIv2(
            access_id=access_id or settings.get('coinex_access_id', ''),
            secret_key=secret_key or settings.get('coinex_secret_key', '')
        )
        
        self.fetcher = CoinExDepositFetcher(self.api, self.db_path)
        self.matcher = PaymentMatcher(self.db_path)
        
        self.polling_interval = int(settings.get('polling_interval', 30))
        self.auto_match = settings.get('auto_match_enabled', 'true').lower() == 'true'
        self.notify_admin = settings.get('notify_admin_on_deposit', 'true').lower() == 'true'
        self.notify_user = settings.get('notify_user_on_match', 'true').lower() == 'true'
    
    def update_credentials(self, access_id: str, secret_key: str):
        """تحديث بيانات الاعتماد وحفظها في قاعدة البيانات"""
        self.api.set_credentials(access_id, secret_key)
        save_coinex_settings({
            'coinex_access_id': access_id,
            'coinex_secret_key': secret_key
        }, self.db_path)
    
    def test_connection(self) -> Tuple[bool, str]:
        """اختبار الاتصال بـ API"""
        return self.api.test_connection()
    
    def fetch_and_store_deposits(self) -> int:
        """جلب وتخزين الإيداعات الجديدة"""
        deposits = self.fetcher.fetch_new_deposits()
        if deposits:
            stored = self.fetcher.store_deposits(deposits)
            
            if stored > 0 and self.notify_admin and self.bot_token:
                for deposit in deposits[:stored]:
                    send_admin_notification_sync(self.bot_token, deposit, is_new=True)
            
            return stored
        return 0
    
    def run_auto_matching(self) -> int:
        """تشغيل المطابقة التلقائية"""
        if not self.auto_match:
            return 0
        return self.matcher.auto_match_pending()
    
    def create_payment_request(self, user_id: int, amount: Union[str, Decimal, float],
                               currency: str = 'USDT', order_id: str = None,
                               sender_email: str = None, expires_hours: int = 24) -> Optional[int]:
        """
        إنشاء طلب دفع جديد
        
        Args:
            user_id: معرف المستخدم
            amount: المبلغ المطلوب
            currency: العملة
            order_id: معرف الطلب
            sender_email: بريد المرسل (اختياري)
            expires_hours: مدة الصلاحية بالساعات
            
        Returns:
            معرف الطلب أو None
        """
        return save_payment_request({
            'user_id': user_id,
            'expected_amount': str(amount),
            'currency': currency,
            'order_id': order_id or '',
            'sender_email': sender_email or '',
            'expires_hours': expires_hours
        }, self.db_path)
    
    def check_payment(self, user_id: int, amount: Union[str, Decimal, float],
                      currency: str = 'USDT', tx_hash: str = None,
                      sender_email: str = None) -> Tuple[bool, Optional[dict], str]:
        """
        التحقق من وجود دفعة مطابقة
        
        Args:
            user_id: معرف المستخدم
            amount: المبلغ المتوقع
            currency: العملة
            tx_hash: معرف المعاملة (اختياري)
            sender_email: بريد المرسل (اختياري)
            
        Returns:
            (تم العثور, بيانات الإيداع, نوع المطابقة)
        """
        try:
            expected_amount = Decimal(str(amount))
        except (InvalidOperation, ValueError):
            return False, None, 'invalid_amount'
        
        deposit, match_type, confidence = self.matcher.match_payment(
            user_id=user_id,
            expected_amount=expected_amount,
            currency=currency,
            tx_hash=tx_hash,
            sender_email=sender_email
        )
        
        if deposit and confidence >= 0.70:
            return True, deposit, match_type
        return False, None, match_type
    
    def run_polling_service(self, interval: int = None, max_iterations: int = None):
        """
        تشغيل خدمة الاستعلام الدورية
        
        Args:
            interval: الفاصل الزمني بالثواني
            max_iterations: الحد الأقصى للتكرارات
        """
        interval = interval or self.polling_interval
        logger.info(f"🚀 بدء خدمة مراقبة CoinEx (كل {interval} ثانية)")
        
        iteration = 0
        while max_iterations is None or iteration < max_iterations:
            try:
                expire_old_requests(self.db_path)
                
                stored = self.fetch_and_store_deposits()
                
                if stored > 0:
                    matched = self.run_auto_matching()
                    if matched > 0:
                        logger.info(f"🎯 تم مطابقة {matched} طلب دفع")
                
            except Exception as e:
                logger.error(f"❌ خطأ في دورة المراقبة: {e}")
            
            iteration += 1
            time.sleep(interval)


# ============================================
# 📍 قسم 7: دوال مساعدة للتكامل مع البوت
# ============================================

def get_payment_service(access_id: str = None, secret_key: str = None) -> CoinExPaymentService:
    """
    الحصول على كائن خدمة الدفع
    
    Args:
        access_id: معرف API (اختياري)
        secret_key: المفتاح السري (اختياري)
        
    Returns:
        كائن CoinExPaymentService
    """
    return CoinExPaymentService(
        access_id=access_id,
        secret_key=secret_key,
        bot_token=getattr(Config, 'TOKEN', '')
    )


def verify_payment_quick(tx_hash: str, expected_amount: Union[str, Decimal],
                         currency: str = 'USDT') -> Tuple[bool, str]:
    """
    تحقق سريع من الدفع بواسطة tx_hash
    
    Args:
        tx_hash: معرف المعاملة
        expected_amount: المبلغ المتوقع
        currency: العملة
        
    Returns:
        (نجاح, رسالة)
    """
    deposit = get_deposit_by_tx_hash(tx_hash)
    
    if not deposit:
        return False, "❌ لم يتم العثور على المعاملة"
    
    if deposit.get('currency', '').upper() != currency.upper():
        return False, f"❌ العملة غير متطابقة: {deposit.get('currency')} != {currency}"
    
    try:
        deposit_amount = Decimal(str(deposit.get('amount', '0')))
        expected = Decimal(str(expected_amount))
        
        tolerance = expected * Decimal('0.01')
        if abs(deposit_amount - expected) > tolerance:
            return False, f"❌ المبلغ غير متطابق: {deposit_amount} != {expected}"
    except (InvalidOperation, ValueError):
        return False, "❌ خطأ في مقارنة المبالغ"
    
    if deposit.get('matched_request_id'):
        return False, "⚠️ هذا الإيداع مطابق مسبقاً لطلب آخر"
    
    if deposit.get('status') not in ['confirmed', 'finish', 'finished']:
        return False, f"⏳ الإيداع قيد التأكيد ({deposit.get('confirmations', 0)} تأكيدات)"
    
    return True, "✅ تم التحقق من الدفع بنجاح"


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    init_coinex_tables()
    print("✅ تم إنشاء جداول CoinEx بنجاح")
    
    api = CoinExAPIv2()
    print(f"📡 CoinEx API Client initialized (Base URL: {api.BASE_URL})")
