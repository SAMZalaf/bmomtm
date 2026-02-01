"""
نظام الدفع الأوتوماتيكي للعملات الرقمية
Automatic Crypto Payment System

يدعم:
- CoinEx (عبر API)
- BEP-20 (BSC) (عبر BSCScan API أو يدوي)
- Litecoin (عبر Blockchair API أو يدوي)

جميع الأوقات بتوقيت سوريا (Asia/Damascus)
"""

import sqlite3
import logging
import hashlib
import random
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN
from typing import Optional, Dict, List, Tuple, Any
import json

try:
    import pytz
    SYRIA_TZ = pytz.timezone('Asia/Damascus')
except ImportError:
    SYRIA_TZ = None

logger = logging.getLogger(__name__)

# استخدام مسار مطلق لقاعدة البيانات
import os
DATABASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "proxy_bot.db")


def get_db_connection():
    """إنشاء اتصال بقاعدة البيانات مع إعدادات لتجنب التضارب"""
    conn = sqlite3.connect(DATABASE_FILE, timeout=10.0)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def get_syria_time() -> datetime:
    """الحصول على الوقت الحالي بتوقيت سوريا"""
    if SYRIA_TZ:
        return datetime.now(SYRIA_TZ)
    return datetime.utcnow() + timedelta(hours=3)

def init_auto_payment_tables():
    """إنشاء جداول قاعدة البيانات للدفع الأوتوماتيكي"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auto_payment_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            order_id TEXT UNIQUE NOT NULL,
            method TEXT NOT NULL,
            currency TEXT NOT NULL,
            expected_amount_usd REAL NOT NULL,
            unique_amount REAL NOT NULL,
            amount_received REAL DEFAULT 0,
            status TEXT DEFAULT 'pending',
            tx_hash TEXT,
            deposit_address TEXT,
            deposit_email TEXT,
            user_sender_email TEXT,
            user_tx_hash TEXT,
            message_id INTEGER,
            chat_id INTEGER,
            expires_at TEXT,
            created_at TEXT,
            matched_at TEXT,
            metadata TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    try:
        cursor.execute('ALTER TABLE auto_payment_requests ADD COLUMN user_sender_email TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE auto_payment_requests ADD COLUMN user_tx_hash TEXT')
    except:
        pass
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auto_payment_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            deposit_source TEXT NOT NULL,
            tx_hash TEXT,
            amount REAL,
            currency TEXT,
            sender_info TEXT,
            confidence REAL DEFAULT 1.0,
            raw_payload TEXT,
            matched_at TEXT,
            FOREIGN KEY (request_id) REFERENCES auto_payment_requests(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auto_payment_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE NOT NULL,
            setting_value TEXT,
            updated_at TEXT
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_apr_status ON auto_payment_requests(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_apr_method ON auto_payment_requests(method)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_apr_user ON auto_payment_requests(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_apr_tx ON auto_payment_requests(tx_hash)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_apr_expires ON auto_payment_requests(expires_at)')
    
    default_settings = {
        'bep20_address': '0xd0d85b3c9df21947087cbb1df5c8bf443d7d17e4',
        'litecoin_address': 'ltc1q4z6ncnp4sj58e96f2xnlhvr7txh53r3drfvjta',
        'coinex_email': 'sohilskaf123@gmail.com',
        'payment_expiry_minutes': '60',
        'amount_tolerance': '0.01',
        'auto_credit_enabled': 'true',
        'bscscan_api_key': '',
        'blockchair_api_key': '',
        'unique_amount_min_offset': '0.01',
        'unique_amount_max_offset': '0.99'
    }
    
    for key, value in default_settings.items():
        cursor.execute('''
            INSERT OR IGNORE INTO auto_payment_settings (setting_key, setting_value, updated_at)
            VALUES (?, ?, ?)
        ''', (key, value, get_syria_time().isoformat()))
    
    conn.commit()
    conn.close()
    logger.info("✅ تم إنشاء/تحديث جداول الدفع الأوتوماتيكي")


def get_auto_payment_setting(key: str, default: str = '') -> str:
    """الحصول على إعداد معين"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT setting_value FROM auto_payment_settings WHERE setting_key = ?', (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else default


def save_auto_payment_setting(key: str, value: str):
    """حفظ إعداد"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO auto_payment_settings (setting_key, setting_value, updated_at)
        VALUES (?, ?, ?)
    ''', (key, value, get_syria_time().isoformat()))
    conn.commit()
    conn.close()


def get_all_auto_payment_settings() -> Dict[str, str]:
    """الحصول على جميع الإعدادات"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT setting_key, setting_value FROM auto_payment_settings')
    results = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in results}


def generate_unique_amount(base_amount: float, method: str) -> float:
    """
    توليد مبلغ فريد للتعرف على الدفعة
    يضيف سنتات عشوائية للمبلغ الأساسي
    """
    min_offset = float(get_auto_payment_setting('unique_amount_min_offset', '0.01'))
    max_offset = float(get_auto_payment_setting('unique_amount_max_offset', '0.99'))
    
    random_cents = random.uniform(min_offset, max_offset)
    unique_amount = round(base_amount + random_cents, 2)
    
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    two_hours_ago = (get_syria_time() - timedelta(hours=2)).isoformat()
    cursor.execute('''
        SELECT COUNT(*) FROM auto_payment_requests 
        WHERE method = ? AND unique_amount = ? AND created_at > ? AND status = 'pending'
    ''', (method, unique_amount, two_hours_ago))
    
    count = cursor.fetchone()[0]
    conn.close()
    
    if count > 0:
        return generate_unique_amount(base_amount, method)
    
    return unique_amount


def create_auto_payment_request(
    user_id: int,
    order_id: str,
    method: str,
    expected_amount_usd: float,
    currency: str = 'USDT',
    expiry_minutes: int = None,
    chat_id: int = None,
    message_id: int = None,
    user_sender_email: str = None,
    user_tx_hash: str = None
) -> Dict[str, Any]:
    """
    إنشاء طلب دفع أوتوماتيكي جديد
    
    Args:
        user_sender_email: البريد الذي أرسل منه المستخدم (للـ CoinEx)
        user_tx_hash: معرف الحوالة الذي يقدمه المستخدم (للـ BEP-20 و Litecoin)
    """
    init_auto_payment_tables()
    
    if expiry_minutes is None:
        expiry_minutes = int(get_auto_payment_setting('payment_expiry_minutes', '60'))
    
    unique_amount = generate_unique_amount(expected_amount_usd, method)
    
    now = get_syria_time()
    expires_at = now + timedelta(minutes=expiry_minutes)
    
    if method == 'coinex':
        deposit_address = None
        deposit_email = get_auto_payment_setting('coinex_email', 'sohilskaf123@gmail.com')
    elif method == 'bep20':
        deposit_address = get_auto_payment_setting('bep20_address')
        deposit_email = None
        currency = 'USDT'
    elif method == 'litecoin':
        deposit_address = get_auto_payment_setting('litecoin_address')
        deposit_email = None
        currency = 'LTC'
    else:
        raise ValueError(f"طريقة دفع غير مدعومة: {method}")
    
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id FROM auto_payment_requests 
        WHERE user_id = ? AND method = ? AND status = 'pending'
    ''', (user_id, method))
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute('''
            UPDATE auto_payment_requests 
            SET status = 'cancelled', metadata = json_set(COALESCE(metadata, '{}'), '$.cancel_reason', 'replaced_by_new_request')
            WHERE id = ?
        ''', (existing[0],))
    
    cursor.execute('''
        INSERT INTO auto_payment_requests (
            user_id, order_id, method, currency, expected_amount_usd, unique_amount,
            deposit_address, deposit_email, user_sender_email, user_tx_hash,
            message_id, chat_id, expires_at, created_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
    ''', (
        user_id, order_id, method, currency, expected_amount_usd, unique_amount,
        deposit_address, deposit_email, user_sender_email, user_tx_hash,
        message_id, chat_id, expires_at.isoformat(), now.isoformat()
    ))
    
    request_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    logger.info(f"✅ تم إنشاء طلب دفع أوتوماتيكي #{request_id} للمستخدم {user_id} - {method} - ${unique_amount}")
    
    return {
        'id': request_id,
        'order_id': order_id,
        'user_id': user_id,
        'method': method,
        'currency': currency,
        'expected_amount_usd': expected_amount_usd,
        'unique_amount': unique_amount,
        'deposit_address': deposit_address,
        'deposit_email': deposit_email,
        'user_sender_email': user_sender_email,
        'user_tx_hash': user_tx_hash,
        'expires_at': expires_at.isoformat(),
        'created_at': now.isoformat(),
        'expiry_minutes': expiry_minutes
    }


def get_pending_auto_payment_requests(method: str = None) -> List[Dict]:
    """الحصول على طلبات الدفع المعلقة"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    now = get_syria_time().isoformat()
    
    if method:
        cursor.execute('''
            SELECT id, user_id, order_id, method, currency, expected_amount_usd, 
                   unique_amount, deposit_address, deposit_email, expires_at, created_at,
                   user_sender_email, user_tx_hash
            FROM auto_payment_requests 
            WHERE status = 'pending' AND method = ? AND expires_at > ?
            ORDER BY created_at ASC
        ''', (method, now))
    else:
        cursor.execute('''
            SELECT id, user_id, order_id, method, currency, expected_amount_usd, 
                   unique_amount, deposit_address, deposit_email, expires_at, created_at,
                   user_sender_email, user_tx_hash
            FROM auto_payment_requests 
            WHERE status = 'pending' AND expires_at > ?
            ORDER BY created_at ASC
        ''', (now,))
    
    results = cursor.fetchall()
    conn.close()
    
    requests = []
    for row in results:
        requests.append({
            'id': row[0],
            'user_id': row[1],
            'order_id': row[2],
            'method': row[3],
            'currency': row[4],
            'expected_amount_usd': row[5],
            'unique_amount': row[6],
            'deposit_address': row[7],
            'deposit_email': row[8],
            'expires_at': row[9],
            'created_at': row[10],
            'user_sender_email': row[11] if len(row) > 11 else None,
            'user_tx_hash': row[12] if len(row) > 12 else None
        })
    
    return requests


def expire_old_requests():
    """تحديث حالة الطلبات المنتهية"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    now = get_syria_time().isoformat()
    
    cursor.execute('''
        UPDATE auto_payment_requests 
        SET status = 'expired'
        WHERE status = 'pending' AND expires_at < ?
    ''', (now,))
    
    expired_count = cursor.rowcount
    conn.commit()
    conn.close()
    
    if expired_count > 0:
        logger.info(f"⏰ تم تحديث {expired_count} طلب دفع منتهي الصلاحية")
    
    return expired_count


def find_request_by_sender_email(sender_email: str) -> Optional[Dict]:
    """
    البحث عن طلب دفع CoinEx معلق بواسطة البريد الإلكتروني للمرسل
    مطابقة 100% - يجب أن يتطابق البريد تماماً
    """
    if not sender_email:
        return None
    
    sender_email = sender_email.strip().lower()
    
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    now = get_syria_time().isoformat()
    
    cursor.execute('''
        SELECT id, user_id, order_id, method, currency, expected_amount_usd, 
               unique_amount, deposit_address, deposit_email, expires_at, created_at,
               user_sender_email, user_tx_hash
        FROM auto_payment_requests 
        WHERE status = 'pending' 
          AND method = 'coinex' 
          AND LOWER(user_sender_email) = ?
          AND expires_at > ?
        ORDER BY created_at ASC
        LIMIT 1
    ''', (sender_email, now))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        logger.info(f"🔍 لم يتم العثور على طلب CoinEx للبريد: {sender_email}")
        return None
    
    logger.info(f"✅ تم العثور على طلب CoinEx #{row[0]} للبريد: {sender_email}")
    
    return {
        'id': row[0],
        'user_id': row[1],
        'order_id': row[2],
        'method': row[3],
        'currency': row[4],
        'expected_amount_usd': row[5],
        'unique_amount': row[6],
        'deposit_address': row[7],
        'deposit_email': row[8],
        'expires_at': row[9],
        'created_at': row[10],
        'user_sender_email': row[11],
        'user_tx_hash': row[12]
    }


def find_request_by_tx_hash(tx_hash: str, method: str = None) -> Optional[Dict]:
    """
    البحث عن طلب دفع BEP-20 أو Litecoin معلق بواسطة معرف الحوالة
    مطابقة 100% - يجب أن يتطابق الـ tx_hash تماماً
    
    Args:
        tx_hash: معرف الحوالة
        method: طريقة الدفع (bep20 أو litecoin) - اختياري
    """
    if not tx_hash:
        return None
    
    tx_hash = tx_hash.strip().lower()
    
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    now = get_syria_time().isoformat()
    
    if method:
        cursor.execute('''
            SELECT id, user_id, order_id, method, currency, expected_amount_usd, 
                   unique_amount, deposit_address, deposit_email, expires_at, created_at,
                   user_sender_email, user_tx_hash
            FROM auto_payment_requests 
            WHERE status = 'pending' 
              AND method = ?
              AND LOWER(user_tx_hash) = ?
              AND expires_at > ?
            ORDER BY created_at ASC
            LIMIT 1
        ''', (method, tx_hash, now))
    else:
        cursor.execute('''
            SELECT id, user_id, order_id, method, currency, expected_amount_usd, 
                   unique_amount, deposit_address, deposit_email, expires_at, created_at,
                   user_sender_email, user_tx_hash
            FROM auto_payment_requests 
            WHERE status = 'pending' 
              AND method IN ('bep20', 'litecoin')
              AND LOWER(user_tx_hash) = ?
              AND expires_at > ?
            ORDER BY created_at ASC
            LIMIT 1
        ''', (tx_hash, now))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        logger.info(f"🔍 لم يتم العثور على طلب لـ tx_hash: {tx_hash[:20]}...")
        return None
    
    logger.info(f"✅ تم العثور على طلب #{row[0]} لـ tx_hash: {tx_hash[:20]}...")
    
    return {
        'id': row[0],
        'user_id': row[1],
        'order_id': row[2],
        'method': row[3],
        'currency': row[4],
        'expected_amount_usd': row[5],
        'unique_amount': row[6],
        'deposit_address': row[7],
        'deposit_email': row[8],
        'expires_at': row[9],
        'created_at': row[10],
        'user_sender_email': row[11],
        'user_tx_hash': row[12]
    }


def match_payment(
    request_id: int,
    tx_hash: str,
    amount_received: float,
    deposit_source: str,
    sender_info: str = None,
    raw_payload: str = None
) -> bool:
    """
    مطابقة دفعة مع طلب
    """
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, user_id, order_id, expected_amount_usd, unique_amount, status
        FROM auto_payment_requests WHERE id = ?
    ''', (request_id,))
    request = cursor.fetchone()
    
    if not request:
        conn.close()
        return False
    
    if request[5] != 'pending':
        conn.close()
        logger.warning(f"⚠️ محاولة مطابقة طلب غير معلق: {request_id}")
        return False
    
    now = get_syria_time()
    
    cursor.execute('''
        UPDATE auto_payment_requests 
        SET status = 'matched', tx_hash = ?, amount_received = ?, matched_at = ?
        WHERE id = ?
    ''', (tx_hash, amount_received, now.isoformat(), request_id))
    
    cursor.execute('''
        INSERT INTO auto_payment_matches (
            request_id, deposit_source, tx_hash, amount, sender_info, raw_payload, matched_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (request_id, deposit_source, tx_hash, amount_received, sender_info, raw_payload, now.isoformat()))
    
    conn.commit()
    conn.close()
    
    logger.info(f"✅ تمت مطابقة الدفعة للطلب #{request_id} - TX: {tx_hash[:20]}...")
    
    return True


def confirm_and_credit_payment(request_id: int) -> Tuple[bool, str]:
    """
    تأكيد الدفعة وإضافة الرصيد للمستخدم
    """
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_id, order_id, expected_amount_usd, amount_received, method, status
        FROM auto_payment_requests WHERE id = ?
    ''', (request_id,))
    request = cursor.fetchone()
    
    if not request:
        conn.close()
        return False, "طلب غير موجود"
    
    user_id, order_id, expected_usd, received, method, status = request
    
    if status not in ['matched', 'pending']:
        conn.close()
        return False, f"حالة الطلب غير صالحة: {status}"
    
    try:
        from config import DatabaseManager
        db = DatabaseManager()
        
        credit_price = db.get_credit_price()
        credits_to_add = expected_usd / credit_price
        
        db.add_credits(
            user_id, 
            credits_to_add, 
            'auto_recharge', 
            order_id, 
            f"شحن أوتوماتيكي عبر {method} بقيمة ${expected_usd:.2f}"
        )
        
        cursor.execute('''
            UPDATE auto_payment_requests 
            SET status = 'completed'
            WHERE id = ?
        ''', (request_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ تم إضافة {credits_to_add:.2f} نقطة للمستخدم {user_id} من الطلب #{request_id}")
        
        return True, f"تم إضافة {credits_to_add:.2f} نقطة"
        
    except Exception as e:
        conn.close()
        logger.error(f"❌ خطأ في إضافة الرصيد: {e}")
        return False, str(e)


def get_coinex_credentials() -> Dict[str, str]:
    """
    الحصول على بيانات اعتماد CoinEx من قاعدة البيانات
    
    Returns:
        dict مع access_id و secret_key
    """
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    credentials = {'access_id': '', 'secret_key': ''}
    
    try:
        cursor.execute("SELECT key, value FROM coinex_settings WHERE key IN ('coinex_access_id', 'coinex_secret_key')")
        rows = cursor.fetchall()
        for key, value in rows:
            if key == 'coinex_access_id':
                credentials['access_id'] = value or ''
            elif key == 'coinex_secret_key':
                credentials['secret_key'] = value or ''
    except Exception as e:
        logger.warning(f"⚠️ خطأ في قراءة بيانات CoinEx من coinex_settings: {e}")
        try:
            cursor.execute("SELECT key, value FROM dashboard_settings WHERE key IN ('coinex_access_id', 'coinex_secret_key')")
            rows = cursor.fetchall()
            for key, value in rows:
                if key == 'coinex_access_id':
                    credentials['access_id'] = value or ''
                elif key == 'coinex_secret_key':
                    credentials['secret_key'] = value or ''
        except Exception as e2:
            logger.warning(f"⚠️ خطأ في قراءة بيانات CoinEx من dashboard_settings: {e2}")
    
    conn.close()
    return credentials


def fetch_and_store_coinex_deposits() -> Tuple[int, str]:
    """
    جلب الإيداعات من CoinEx وتخزينها في قاعدة البيانات
    
    Returns:
        (عدد الإيداعات المخزنة, رسالة)
    """
    try:
        from CoinEx.coinex_payment import CoinExAPIv2, CoinExDepositFetcher
        
        coinex_creds = get_coinex_credentials()
        if not coinex_creds.get('access_id') or not coinex_creds.get('secret_key'):
            logger.warning("⚠️ بيانات CoinEx API غير مكتملة - لا يمكن جلب الإيداعات")
            return 0, "بيانات CoinEx API غير مكتملة"
        
        api = CoinExAPIv2()
        api.set_credentials(coinex_creds['access_id'], coinex_creds['secret_key'])
        
        fetcher = CoinExDepositFetcher(api)
        
        deposits = fetcher.fetch_new_deposits()
        
        if deposits:
            stored_count = fetcher.store_deposits(deposits)
            logger.info(f"✅ تم جلب {len(deposits)} إيداع وتخزين {stored_count} إيداع جديد")
            return stored_count, f"تم جلب {len(deposits)} إيداع وتخزين {stored_count} جديد"
        else:
            logger.info("ℹ️ لا توجد إيداعات جديدة من CoinEx")
            return 0, "لا توجد إيداعات جديدة"
            
    except Exception as e:
        logger.error(f"❌ خطأ في جلب إيداعات CoinEx: {e}")
        return 0, str(e)


def verify_coinex_payment(request: Dict) -> Tuple[bool, str, Optional[Dict]]:
    """
    التحقق من دفعة CoinEx بواسطة البريد الإلكتروني للمرسل
    
    Args:
        request: بيانات طلب الدفع
    
    Returns:
        (نجح, رسالة, بيانات الإيداع)
    """
    try:
        from CoinEx.coinex_payment import CoinExAPIv2, CoinExDepositFetcher
        
        user_email = request.get('user_sender_email', '').strip().lower()
        expected_amount = request.get('unique_amount', 0)
        
        if not user_email:
            return False, "لم يتم تحديد بريد المرسل", None
        
        api = CoinExAPIv2()
        
        coinex_creds = get_coinex_credentials()
        if coinex_creds.get('access_id') and coinex_creds.get('secret_key'):
            api.set_credentials(coinex_creds['access_id'], coinex_creds['secret_key'])
        else:
            logger.warning("⚠️ بيانات CoinEx API غير مكتملة - تحقق من الإعدادات")
            return False, "بيانات CoinEx API غير مكتملة", None
        
        fetcher = CoinExDepositFetcher(api)
        deposits = fetcher.fetch_new_deposits()
        
        if not deposits:
            return False, "لا توجد إيداعات جديدة", None
        
        tolerance = float(get_auto_payment_setting('amount_tolerance', '0.02'))
        
        for deposit in deposits:
            sender = deposit.get('from_address', '').strip().lower()
            amount = float(deposit.get('amount', 0))
            status = deposit.get('status', '')
            
            if sender == user_email:
                if status in ['finish', 'finished', 'confirming', 'processing', 'confirmed']:
                    if abs(amount - expected_amount) <= tolerance:
                        logger.info(f"✅ CoinEx: تم العثور على إيداع مطابق من {user_email} بقيمة {amount}")
                        return True, "تم العثور على الدفعة", {
                            'tx_hash': deposit.get('tx_id', ''),
                            'amount': amount,
                            'sender': sender,
                            'status': status,
                            'source': 'coinex',
                            'raw': deposit
                        }
        
        return False, "لم يتم العثور على دفعة مطابقة", None
        
    except Exception as e:
        logger.error(f"❌ خطأ في التحقق من CoinEx: {e}")
        return False, str(e), None


def verify_bep20_payment(request: Dict) -> Tuple[bool, str, Optional[Dict]]:
    """
    التحقق من دفعة BEP-20 بواسطة معرف الحوالة
    
    Args:
        request: بيانات طلب الدفع
    
    Returns:
        (نجح, رسالة, بيانات الإيداع)
    """
    import requests
    
    try:
        tx_hash = request.get('user_tx_hash', '').strip()
        expected_amount = request.get('unique_amount', 0)
        deposit_address = get_auto_payment_setting('bep20_address', '').lower()
        
        if not tx_hash:
            return False, "لم يتم تحديد معرف الحوالة", None
        
        api_key = get_auto_payment_setting('bscscan_api_key', '')
        if not api_key:
            return False, "BSCScan API key غير مكون", None
        
        url = "https://api.bscscan.com/api"
        params = {
            'module': 'proxy',
            'action': 'eth_getTransactionByHash',
            'txhash': tx_hash,
            'apikey': api_key
        }
        
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        if data.get('result') is None:
            return False, "الحوالة غير موجودة أو لم تتأكد بعد", None
        
        tx_data = data.get('result', {})
        to_address = tx_data.get('to', '').lower()
        
        receipt_params = {
            'module': 'proxy',
            'action': 'eth_getTransactionReceipt',
            'txhash': tx_hash,
            'apikey': api_key
        }
        
        receipt_response = requests.get(url, params=receipt_params, timeout=30)
        receipt_data = receipt_response.json()
        receipt = receipt_data.get('result', {})
        
        if receipt.get('status') != '0x1':
            return False, "الحوالة فشلت أو لم تتأكد", None
        
        logs = receipt.get('logs', [])
        USDT_CONTRACT = "0x55d398326f99059ff775485246999027b3197955".lower()
        
        for log in logs:
            if log.get('address', '').lower() == USDT_CONTRACT:
                topics = log.get('topics', [])
                if len(topics) >= 3:
                    to_topic = topics[2]
                    to_addr = '0x' + to_topic[-40:].lower()
                    
                    if to_addr == deposit_address:
                        raw_amount = log.get('data', '0x0')
                        amount = int(raw_amount, 16) / (10 ** 18)
                        
                        tolerance = float(get_auto_payment_setting('amount_tolerance', '0.02'))
                        if abs(amount - expected_amount) <= tolerance:
                            logger.info(f"✅ BEP-20: تم التحقق من الحوالة {tx_hash[:20]}... بقيمة {amount}")
                            return True, "تم التحقق من الحوالة", {
                                'tx_hash': tx_hash,
                                'amount': amount,
                                'to': deposit_address,
                                'status': 'confirmed',
                                'source': 'bep20'
                            }
                        else:
                            return False, f"المبلغ غير مطابق: متوقع {expected_amount}, وصل {amount}", None
        
        return False, "لم يتم العثور على تحويل USDT للعنوان المطلوب", None
        
    except Exception as e:
        logger.error(f"❌ خطأ في التحقق من BEP-20: {e}")
        return False, str(e), None


def verify_litecoin_payment(request: Dict) -> Tuple[bool, str, Optional[Dict]]:
    """
    التحقق من دفعة Litecoin بواسطة معرف الحوالة
    
    Args:
        request: بيانات طلب الدفع
    
    Returns:
        (نجح, رسالة, بيانات الإيداع)
    """
    import requests
    
    try:
        tx_hash = request.get('user_tx_hash', '').strip()
        expected_amount = request.get('unique_amount', 0)
        deposit_address = get_auto_payment_setting('litecoin_address', '')
        
        if not tx_hash:
            return False, "لم يتم تحديد معرف الحوالة", None
        
        url = f"https://api.blockcypher.com/v1/ltc/main/txs/{tx_hash}"
        
        api_key = get_auto_payment_setting('blockchair_api_key', '')
        params = {}
        if api_key:
            params['token'] = api_key
        
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 404:
            return False, "الحوالة غير موجودة", None
        
        if response.status_code != 200:
            return False, f"خطأ في API: {response.status_code}", None
        
        tx_data = response.json()
        
        confirmations = tx_data.get('confirmations', 0)
        if confirmations < 6:
            return False, f"الحوالة تحتاج تأكيدات أكثر ({confirmations}/6)", None
        
        outputs = tx_data.get('outputs', [])
        for output in outputs:
            addresses = output.get('addresses', [])
            if deposit_address in addresses:
                amount = output.get('value', 0) / 100000000
                
                tolerance = float(get_auto_payment_setting('amount_tolerance', '0.02'))
                if abs(amount - expected_amount) <= tolerance:
                    logger.info(f"✅ Litecoin: تم التحقق من الحوالة {tx_hash[:20]}... بقيمة {amount}")
                    return True, "تم التحقق من الحوالة", {
                        'tx_hash': tx_hash,
                        'amount': amount,
                        'to': deposit_address,
                        'confirmations': confirmations,
                        'status': 'confirmed',
                        'source': 'litecoin'
                    }
                else:
                    return False, f"المبلغ غير مطابق: متوقع {expected_amount}, وصل {amount}", None
        
        return False, "لم يتم العثور على تحويل للعنوان المطلوب", None
        
    except Exception as e:
        logger.error(f"❌ خطأ في التحقق من Litecoin: {e}")
        return False, str(e), None


def verify_auto_payment_request(request_id: int) -> Tuple[bool, str, Optional[Dict]]:
    """
    التحقق من طلب دفع أوتوماتيكي
    الدالة الرئيسية التي توجه للتحقق المناسب حسب طريقة الدفع
    
    Args:
        request_id: معرف الطلب
    
    Returns:
        (نجح, رسالة, بيانات الإيداع)
    """
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, user_id, order_id, method, currency, expected_amount_usd, 
               unique_amount, status, user_sender_email, user_tx_hash, expires_at
        FROM auto_payment_requests WHERE id = ?
    ''', (request_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return False, "الطلب غير موجود", None
    
    request = {
        'id': row[0],
        'user_id': row[1],
        'order_id': row[2],
        'method': row[3],
        'currency': row[4],
        'expected_amount_usd': row[5],
        'unique_amount': row[6],
        'status': row[7],
        'user_sender_email': row[8],
        'user_tx_hash': row[9],
        'expires_at': row[10]
    }
    
    if request['status'] == 'completed':
        return True, "تم إتمام الدفع مسبقاً", None
    
    if request['status'] != 'pending':
        return False, f"حالة الطلب: {request['status']}", None
    
    now = get_syria_time()
    try:
        expires_at = datetime.fromisoformat(request['expires_at'].replace('Z', '+00:00'))
        if SYRIA_TZ:
            if expires_at.tzinfo is None:
                expires_at = SYRIA_TZ.localize(expires_at)
        if now > expires_at:
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            cursor.execute("UPDATE auto_payment_requests SET status = 'expired' WHERE id = ?", (request_id,))
            conn.commit()
            conn.close()
            return False, "انتهت صلاحية الطلب", None
    except:
        pass
    
    method = request['method']
    
    if method == 'coinex':
        success, message, deposit_data = verify_coinex_payment(request)
    elif method == 'bep20':
        success, message, deposit_data = verify_bep20_payment(request)
    elif method == 'litecoin':
        success, message, deposit_data = verify_litecoin_payment(request)
    else:
        return False, f"طريقة دفع غير مدعومة: {method}", None
    
    if success and deposit_data:
        match_success = match_payment(
            request_id=request_id,
            tx_hash=deposit_data.get('tx_hash', ''),
            amount_received=deposit_data.get('amount', 0),
            deposit_source=method,
            sender_info=deposit_data.get('sender', ''),
            raw_payload=json.dumps(deposit_data.get('raw', deposit_data))
        )
        
        if match_success:
            credit_success, credit_message = confirm_and_credit_payment(request_id)
            if credit_success:
                return True, f"✅ تم التحقق وإضافة الرصيد: {credit_message}", deposit_data
            else:
                return False, f"تم المطابقة لكن فشل إضافة الرصيد: {credit_message}", deposit_data
        else:
            return False, "فشل في تسجيل المطابقة", deposit_data
    
    return False, message, None


def get_payment_request_by_order(order_id: str) -> Optional[Dict]:
    """الحصول على طلب دفع بواسطة معرف الطلب"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, user_id, order_id, method, currency, expected_amount_usd, 
               unique_amount, amount_received, status, tx_hash, deposit_address,
               deposit_email, expires_at, created_at, matched_at
        FROM auto_payment_requests WHERE order_id = ?
    ''', (order_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return {
        'id': row[0],
        'user_id': row[1],
        'order_id': row[2],
        'method': row[3],
        'currency': row[4],
        'expected_amount_usd': row[5],
        'unique_amount': row[6],
        'amount_received': row[7],
        'status': row[8],
        'tx_hash': row[9],
        'deposit_address': row[10],
        'deposit_email': row[11],
        'expires_at': row[12],
        'created_at': row[13],
        'matched_at': row[14]
    }


def get_user_pending_requests(user_id: int) -> List[Dict]:
    """الحصول على طلبات المستخدم المعلقة"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    now = get_syria_time().isoformat()
    
    cursor.execute('''
        SELECT id, order_id, method, currency, expected_amount_usd, unique_amount,
               deposit_address, deposit_email, expires_at, created_at
        FROM auto_payment_requests 
        WHERE user_id = ? AND status = 'pending' AND expires_at > ?
        ORDER BY created_at DESC
    ''', (user_id, now))
    
    results = cursor.fetchall()
    conn.close()
    
    return [
        {
            'id': row[0],
            'order_id': row[1],
            'method': row[2],
            'currency': row[3],
            'expected_amount_usd': row[4],
            'unique_amount': row[5],
            'deposit_address': row[6],
            'deposit_email': row[7],
            'expires_at': row[8],
            'created_at': row[9]
        }
        for row in results
    ]


def cancel_payment_request(request_id: int, reason: str = None) -> bool:
    """إلغاء طلب دفع"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    metadata = json.dumps({'cancel_reason': reason}) if reason else None
    
    cursor.execute('''
        UPDATE auto_payment_requests 
        SET status = 'cancelled', metadata = ?
        WHERE id = ? AND status = 'pending'
    ''', (metadata, request_id))
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return success


def get_auto_payment_stats() -> Dict:
    """الحصول على إحصائيات الدفع الأوتوماتيكي"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
            COUNT(CASE WHEN status = 'matched' THEN 1 END) as matched,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
            COUNT(CASE WHEN status = 'expired' THEN 1 END) as expired,
            COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled,
            SUM(CASE WHEN status = 'completed' THEN expected_amount_usd ELSE 0 END) as total_completed_usd
        FROM auto_payment_requests
    ''')
    
    row = cursor.fetchone()
    
    cursor.execute('''
        SELECT method, COUNT(*) as count, SUM(expected_amount_usd) as total
        FROM auto_payment_requests 
        WHERE status = 'completed'
        GROUP BY method
    ''')
    
    by_method = cursor.fetchall()
    conn.close()
    
    return {
        'pending': row[0] or 0,
        'matched': row[1] or 0,
        'completed': row[2] or 0,
        'expired': row[3] or 0,
        'cancelled': row[4] or 0,
        'total_completed_usd': row[5] or 0,
        'by_method': {m[0]: {'count': m[1], 'total_usd': m[2]} for m in by_method}
    }


def find_matching_request_by_amount(
    method: str,
    amount: float,
    tolerance: float = None,
    time_window_hours: int = 2
) -> Optional[Dict]:
    """
    البحث عن طلب مطابق بناءً على المبلغ الفريد
    """
    if tolerance is None:
        tolerance = float(get_auto_payment_setting('amount_tolerance', '0.01'))
    
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    time_threshold = (get_syria_time() - timedelta(hours=time_window_hours)).isoformat()
    
    cursor.execute('''
        SELECT id, user_id, order_id, expected_amount_usd, unique_amount, currency,
               deposit_address, deposit_email, expires_at, created_at
        FROM auto_payment_requests 
        WHERE method = ? 
        AND status = 'pending'
        AND ABS(unique_amount - ?) <= ?
        AND created_at > ?
        AND expires_at > ?
        ORDER BY ABS(unique_amount - ?) ASC
        LIMIT 1
    ''', (method, amount, tolerance, time_threshold, get_syria_time().isoformat(), amount))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return {
        'id': row[0],
        'user_id': row[1],
        'order_id': row[2],
        'expected_amount_usd': row[3],
        'unique_amount': row[4],
        'currency': row[5],
        'deposit_address': row[6],
        'deposit_email': row[7],
        'expires_at': row[8],
        'created_at': row[9]
    }


class BEP20Fetcher:
    """
    جلب إيداعات BEP-20 من BSCScan API
    """
    
    BSCSCAN_API = "https://api.bscscan.com/api"
    USDT_CONTRACT = "0x55d398326f99059ff775485246999027b3197955"
    REQUIRED_CONFIRMATIONS = 15
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or get_auto_payment_setting('bscscan_api_key')
    
    def get_token_transfers(self, address: str, start_block: int = 0) -> List[Dict]:
        """جلب تحويلات التوكن إلى عنوان معين"""
        import requests
        
        if not self.api_key:
            logger.warning("⚠️ BSCScan API key not configured")
            return []
        
        params = {
            'module': 'account',
            'action': 'tokentx',
            'contractaddress': self.USDT_CONTRACT,
            'address': address,
            'startblock': start_block,
            'endblock': 99999999,
            'sort': 'desc',
            'apikey': self.api_key
        }
        
        try:
            response = requests.get(self.BSCSCAN_API, params=params, timeout=30)
            data = response.json()
            
            if data.get('status') == '1':
                transfers = data.get('result', [])
                incoming = [t for t in transfers if t.get('to', '').lower() == address.lower()]
                logger.info(f"✅ BEP-20: تم جلب {len(incoming)} تحويل وارد")
                return incoming
            else:
                logger.error(f"❌ BSCScan Error: {data.get('message')}")
                return []
        except Exception as e:
            logger.error(f"❌ خطأ في جلب BEP-20: {e}")
            return []
    
    def check_for_matching_deposit(self, pending_requests: List[Dict]) -> List[Tuple[Dict, Dict]]:
        """البحث عن تحويلات مطابقة للطلبات المعلقة"""
        matches = []
        
        bep20_requests = [r for r in pending_requests if r['method'] == 'bep20']
        if not bep20_requests:
            return matches
        
        address = get_auto_payment_setting('bep20_address')
        if not address:
            return matches
        
        transfers = self.get_token_transfers(address)
        
        for transfer in transfers:
            try:
                amount = float(transfer.get('value', 0)) / (10 ** int(transfer.get('tokenDecimal', 18)))
                tx_hash = transfer.get('hash', '')
                timestamp = int(transfer.get('timeStamp', 0))
                confirmations = int(transfer.get('confirmations', 0))
                
                if confirmations < self.REQUIRED_CONFIRMATIONS:
                    continue
                
                for request in bep20_requests:
                    tolerance = float(get_auto_payment_setting('amount_tolerance', '0.01'))
                    if abs(amount - request['unique_amount']) <= tolerance:
                        matches.append((request, {
                            'tx_hash': tx_hash,
                            'amount': amount,
                            'from': transfer.get('from', ''),
                            'confirmations': confirmations,
                            'timestamp': timestamp,
                            'source': 'bep20'
                        }))
                        break
            except Exception as e:
                logger.error(f"❌ خطأ في معالجة تحويل BEP-20: {e}")
        
        return matches


class LitecoinFetcher:
    """
    جلب إيداعات Litecoin من BlockCypher API
    """
    
    BLOCKCYPHER_API = "https://api.blockcypher.com/v1/ltc/main"
    REQUIRED_CONFIRMATIONS = 6
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or get_auto_payment_setting('blockchair_api_key')
    
    def get_address_transactions(self, address: str) -> List[Dict]:
        """جلب المعاملات لعنوان معين"""
        import requests
        
        url = f"{self.BLOCKCYPHER_API}/addrs/{address}/full"
        params = {}
        if self.api_key:
            params['token'] = self.api_key
        
        try:
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                txs = data.get('txs', [])
                logger.info(f"✅ Litecoin: تم جلب {len(txs)} معاملة")
                return txs
            else:
                logger.error(f"❌ BlockCypher Error: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"❌ خطأ في جلب Litecoin: {e}")
            return []
    
    def get_incoming_deposits(self, address: str) -> List[Dict]:
        """جلب الإيداعات الواردة فقط"""
        txs = self.get_address_transactions(address)
        deposits = []
        
        for tx in txs:
            confirmations = tx.get('confirmations', 0)
            if confirmations < self.REQUIRED_CONFIRMATIONS:
                continue
            
            for output in tx.get('outputs', []):
                if address in output.get('addresses', []):
                    deposits.append({
                        'tx_hash': tx.get('hash', ''),
                        'amount': output.get('value', 0) / 100000000,
                        'confirmations': confirmations,
                        'timestamp': tx.get('received', ''),
                        'source': 'litecoin'
                    })
        
        return deposits
    
    def check_for_matching_deposit(self, pending_requests: List[Dict]) -> List[Tuple[Dict, Dict]]:
        """البحث عن إيداعات مطابقة للطلبات المعلقة"""
        matches = []
        
        ltc_requests = [r for r in pending_requests if r['method'] == 'litecoin']
        if not ltc_requests:
            return matches
        
        address = get_auto_payment_setting('litecoin_address')
        if not address:
            return matches
        
        deposits = self.get_incoming_deposits(address)
        
        for deposit in deposits:
            for request in ltc_requests:
                tolerance = float(get_auto_payment_setting('amount_tolerance', '0.01'))
                if abs(deposit['amount'] - request['unique_amount']) <= tolerance:
                    matches.append((request, deposit))
                    break
        
        return matches


class AutoPaymentMonitor:
    """
    مراقب الدفع الأوتوماتيكي
    يتحقق من الدفعات الواردة ويطابقها مع الطلبات
    """
    
    def __init__(self):
        init_auto_payment_tables()
        self.bep20_fetcher = BEP20Fetcher()
        self.ltc_fetcher = LitecoinFetcher()
    
    async def check_coinex_deposits(self) -> int:
        """فحص إيداعات CoinEx"""
        try:
            from CoinEx.coinex_payment import CoinExPaymentService
            
            service = CoinExPaymentService()
            stored = service.fetch_and_store_deposits()
            matched = service.run_auto_matching()
            
            pending_requests = get_pending_auto_payment_requests('coinex')
            for request in pending_requests:
                if service.check_deposit_for_request(request):
                    success, msg = confirm_and_credit_payment(request['id'])
                    if success:
                        logger.info(f"✅ CoinEx: تم إكمال الطلب #{request['id']}")
            
            return matched
        except Exception as e:
            logger.error(f"❌ خطأ في فحص CoinEx: {e}")
            return 0
    
    async def check_bep20_deposits(self) -> int:
        """فحص إيداعات BEP-20 (BSC)"""
        bscscan_key = get_auto_payment_setting('bscscan_api_key')
        if not bscscan_key:
            return 0
        
        try:
            pending_requests = get_pending_auto_payment_requests('bep20')
            if not pending_requests:
                return 0
            
            matches = self.bep20_fetcher.check_for_matching_deposit(pending_requests)
            matched_count = 0
            
            for request, deposit in matches:
                success = match_payment(
                    request_id=request['id'],
                    tx_hash=deposit['tx_hash'],
                    amount_received=deposit['amount'],
                    deposit_source='bep20',
                    sender_info=deposit.get('from', ''),
                    raw_payload=json.dumps(deposit)
                )
                
                if success:
                    credit_success, msg = confirm_and_credit_payment(request['id'])
                    if credit_success:
                        logger.info(f"✅ BEP-20: تم إكمال الطلب #{request['id']}")
                        matched_count += 1
            
            return matched_count
        except Exception as e:
            logger.error(f"❌ خطأ في فحص BEP-20: {e}")
            return 0
    
    async def check_litecoin_deposits(self) -> int:
        """فحص إيداعات Litecoin"""
        try:
            pending_requests = get_pending_auto_payment_requests('litecoin')
            if not pending_requests:
                return 0
            
            matches = self.ltc_fetcher.check_for_matching_deposit(pending_requests)
            matched_count = 0
            
            for request, deposit in matches:
                success = match_payment(
                    request_id=request['id'],
                    tx_hash=deposit['tx_hash'],
                    amount_received=deposit['amount'],
                    deposit_source='litecoin',
                    sender_info='',
                    raw_payload=json.dumps(deposit)
                )
                
                if success:
                    credit_success, msg = confirm_and_credit_payment(request['id'])
                    if credit_success:
                        logger.info(f"✅ Litecoin: تم إكمال الطلب #{request['id']}")
                        matched_count += 1
            
            return matched_count
        except Exception as e:
            logger.error(f"❌ خطأ في فحص Litecoin: {e}")
            return 0
    
    async def run_all_checks(self) -> Dict[str, int]:
        """تشغيل جميع الفحوصات"""
        expire_old_requests()
        
        results = {
            'coinex': await self.check_coinex_deposits(),
            'bep20': await self.check_bep20_deposits(),
            'litecoin': await self.check_litecoin_deposits()
        }
        
        return results


def format_payment_instructions(request: Dict, language: str = 'ar') -> str:
    """
    تنسيق تعليمات الدفع للمستخدم
    """
    method = request['method']
    unique_amount = request['unique_amount']
    expires_at = request['expires_at']
    
    try:
        expires_dt = datetime.fromisoformat(expires_at)
        if SYRIA_TZ:
            expires_dt = expires_dt.astimezone(SYRIA_TZ)
        expires_str = expires_dt.strftime('%H:%M:%S')
    except:
        expires_str = expires_at
    
    if language == 'ar':
        if method == 'coinex':
            return f"""🪙 <b>الدفع عبر CoinEx (تلقائي)</b>

💰 <b>المبلغ المطلوب:</b> <code>${unique_amount:.2f}</code>

📧 <b>أرسل إلى البريد:</b>
<code>{request.get('deposit_email', 'sohilskaf123@gmail.com')}</code>

⚠️ <b>تنبيه هام:</b>
• أرسل المبلغ <b>بالضبط</b> كما هو مذكور
• أدخل <b>بريد المرسل</b> للتأكيد
• سيتم إضافة الرصيد تلقائياً خلال دقائق

⏰ ينتهي الطلب: {expires_str}"""
        
        elif method == 'bep20':
            return f"""🔗 <b>الدفع عبر BEP-20 BSC (تلقائي)</b>

💰 <b>المبلغ المطلوب:</b> <code>{unique_amount:.2f} USDT</code>

📋 <b>العنوان:</b>
<code>{request.get('deposit_address', '')}</code>

⚠️ <b>تنبيه هام:</b>
• أرسل عبر شبكة <b>BSC (BEP-20)</b> فقط
• أرسل المبلغ <b>بالضبط</b> كما هو مذكور
• سيتم التحقق من العملية تلقائياً

⏰ ينتهي الطلب: {expires_str}"""
        
        elif method == 'litecoin':
            return f"""🔗 <b>الدفع عبر Litecoin (تلقائي)</b>

💰 <b>المبلغ المطلوب:</b> <code>${unique_amount:.2f}</code>

📋 <b>العنوان:</b>
<code>{request.get('deposit_address', '')}</code>

⚠️ <b>تنبيه هام:</b>
• أرسل المبلغ <b>بالضبط</b> كما هو مذكور
• سيتم التحقق من العملية تلقائياً

⏰ ينتهي الطلب: {expires_str}"""
    
    else:
        if method == 'coinex':
            return f"""🪙 <b>Payment via CoinEx (Automatic)</b>

💰 <b>Amount Required:</b> <code>${unique_amount:.2f}</code>

📧 <b>Send to Email:</b>
<code>{request.get('deposit_email', 'sohilskaf123@gmail.com')}</code>

⚠️ <b>Important:</b>
• Send the <b>exact</b> amount as shown
• Enter your <b>sender email</b> for confirmation
• Balance will be added automatically within minutes

⏰ Request expires at: {expires_str}"""
        
        elif method == 'bep20':
            return f"""🔗 <b>Payment via BEP-20 BSC (Automatic)</b>

💰 <b>Amount Required:</b> <code>{unique_amount:.2f} USDT</code>

📋 <b>Address:</b>
<code>{request.get('deposit_address', '')}</code>

⚠️ <b>Important:</b>
• Send via <b>BSC (BEP-20)</b> network only
• Send the <b>exact</b> amount as shown
• Transaction will be verified automatically

⏰ Request expires at: {expires_str}"""
        
        elif method == 'litecoin':
            return f"""🔗 <b>Payment via Litecoin (Automatic)</b>

💰 <b>Amount Required:</b> <code>${unique_amount:.2f}</code>

📋 <b>Address:</b>
<code>{request.get('deposit_address', '')}</code>

⚠️ <b>Important:</b>
• Send the <b>exact</b> amount as shown
• Transaction will be verified automatically

⏰ Request expires at: {expires_str}"""
    
    return "❌ طريقة دفع غير معروفة"


if __name__ == "__main__":
    init_auto_payment_tables()
    print("✅ تم تهيئة نظام الدفع الأوتوماتيكي")
