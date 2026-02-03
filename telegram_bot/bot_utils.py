# ============================================
# bot_utils.py - الأدوات المساعدة وإدارة قاعدة البيانات
# تم استخراجه من bot.py - المرحلة الثانية
# ============================================

import sqlite3
import logging
import random
import string
import json
import re
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import pytz

# استيراد الإعدادات
from config import Config

DATABASE_FILE = getattr(Config, 'DATABASE_FILE', 'proxy_bot.db')

# إعداد اللوغز
logger = logging.getLogger(__name__)

# ============================================
# متغير قاعدة البيانات العام (سيتم تهيئته في النهاية)
# ============================================
db = None

def escape_markdown_v2(text: str) -> str:
    """
    عمل escape للأحرف الخاصة في MarkdownV2
    
    Args:
        text: النص المراد عمل escape له
        
    Returns:
        النص بعد عمل escape للأحرف الخاصة
    """
    if not text:
        return text
    
    # الأحرف التي تحتاج escape في MarkdownV2
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    
    return text


# تم نقل جميع القواميس (STATIC_COUNTRIES, SOCKS_COUNTRIES, US_STATES_*, UK_STATES, MESSAGES) إلى config.py

# ====== دوال مساعدة عامة ======

def get_res4_price(duration_type):
    """جلب سعر Residential Super حسب المدة"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    price_keys = {
        'weekly': 'res4_weekly_price',
        '15days': 'res4_15days_price',
        'monthly': 'res4_monthly_price'
    }
    
    key = price_keys.get(duration_type)
    if not key:
        return "0.0"
    
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else "0.0"



def get_syria_time() -> datetime:
    """الحصول على الوقت الحالي بتوقيت سوريا (UTC+3)"""
    syria_tz = pytz.timezone('Asia/Damascus')
    return datetime.now(syria_tz)

def get_syria_time_str(format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """الحصول على الوقت الحالي بتوقيت سوريا كنص"""
    return get_syria_time().strftime(format_str)

def escape_html(text: Any) -> str:
    """
    تهريب الأحرف الخاصة بـ HTML لإرسال الرسائل بأمان.
    
    في وضع HTML، فقط 3 أحرف خاصة تحتاج للتهريب:
    & < >
    
    الشرطة السفلية (_) والأقواس والرموز الأخرى لا تحتاج تهريب!
    هذا يحل مشكلة ظهور \ في أسماء المستخدمين والنصوص.
    
    Args:
        text: النص المراد تهريبه (يقبل أي نوع: str, int, float, None, إلخ)
        
    Returns:
        النص المهرب بشكل آمن لـ HTML
        
    مثال:
        >>> escape_html("wu_y21")
        'wu_y21'  # لا تغيير! الشرطة السفلية آمنة في HTML
        >>> escape_html("Price: $5 < $10")
        'Price: $5 &lt; $10'  # فقط < تم تهريبها
        >>> escape_html(123)
        '123'  # يعمل مع الأرقام أيضاً
        >>> escape_html(None)
        ''  # يعيد نص فارغ للقيم None
    """
    # التحقق من صحة المدخلات
    if text is None:
        return ""
    
    if not isinstance(text, str):
        text = str(text)
    
    if not text:
        return ""
    
    # ترتيب التهريب مهم: & يجب أن يكون أولاً
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    
    return text


def escape_markdown(text: Any) -> str:
    """دالة للتوافق مع الكود القديم - تستخدم escape_html"""
    return escape_html(text)
def log_with_syria_time(level: str, message: str, user_id: int = None, action: str = None):
    """
    تسجيل رسالة في اللوغز مع الوقت بتوقيت سوريا
    """
    syria_time = get_syria_time_str()
    
    if user_id and action:
        log_message = f"[{syria_time}] [{level}] User {user_id} - {action}: {message}"
    else:
        log_message = f"[{syria_time}] [{level}] {message}"
    
    if level == 'INFO':
        logger.info(log_message)
    elif level == 'ERROR':
        logger.error(log_message)
    elif level == 'WARNING':
        logger.warning(log_message)
    elif level == 'DEBUG':
        logger.debug(log_message)
    else:
        logger.info(log_message)
    
    # تسجيل في قاعدة البيانات إذا كان هناك user_id وaction
    if user_id and action:
        try:
            db.log_action(user_id, action, message)
        except:
            pass

# ====== نهاية دوال المساعدة ======

# ============================================
# DatabaseManager class
# ============================================

class DatabaseManager:
    """مدير قاعدة البيانات"""
    
    def __init__(self, db_file: str):
        self.db_file = db_file
        self.init_database()
    
    def init_database(self):
        """إنشاء جداول قاعدة البيانات"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # جدول المستخدمين
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language TEXT DEFAULT 'ar',
                referral_balance REAL DEFAULT 0.0,
                credits_balance REAL DEFAULT 0.0,
                referred_by INTEGER,
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_admin BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # جدول الطلبات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                proxy_type TEXT,
                country TEXT,
                state TEXT,
                payment_method TEXT,
                payment_amount REAL,
                payment_proof TEXT,
                quantity TEXT DEFAULT 'واحد',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                proxy_details TEXT,
                truly_processed BOOLEAN DEFAULT FALSE,
                duration TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # جدول الإحالات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                amount REAL DEFAULT 0.1,
                activated BOOLEAN DEFAULT FALSE,
                activated_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                FOREIGN KEY (referred_id) REFERENCES users (user_id)
            )
        ''')
        
        # جدول الإعدادات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # جدول المعاملات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                transaction_number TEXT UNIQUE NOT NULL,
                transaction_type TEXT NOT NULL,  -- 'proxy' or 'withdrawal'
                status TEXT DEFAULT 'completed',  -- 'completed' or 'failed'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول السجلات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # إضافة العمود الجديد للطلبات المعالجة فعلياً إذا لم يكن موجوداً
        try:
            cursor.execute("SELECT truly_processed FROM orders LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE orders ADD COLUMN truly_processed BOOLEAN DEFAULT FALSE")
        
        # إضافة عمود الكمية إذا لم يكن موجوداً
        try:
            cursor.execute("SELECT quantity FROM orders LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE orders ADD COLUMN quantity TEXT DEFAULT 'واحد'")

        # إضافة أعمدة الإحالة المؤجلة إذا لم تكن موجودة
        try:
            cursor.execute("SELECT activated FROM referrals LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE referrals ADD COLUMN activated BOOLEAN DEFAULT FALSE")
        
        try:
            cursor.execute("SELECT activated_at FROM referrals LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE referrals ADD COLUMN activated_at TIMESTAMP")

        # إضافة عمود رصيد الكريديت إذا لم يكن موجوداً
        try:
            cursor.execute("SELECT credits_balance FROM users LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE users ADD COLUMN credits_balance REAL DEFAULT 0.0")
        
        # إضافة عمود is_banned إذا لم يكن موجوداً
        try:
            cursor.execute("SELECT is_banned FROM users LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT 0")
            print("✅ تم إضافة عمود is_banned")
        
        # إضافة عمود static_type إذا لم يكن موجوداً
        try:
            cursor.execute("SELECT static_type FROM orders LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE orders ADD COLUMN static_type TEXT DEFAULT ''")
            print("✅ تم إضافة عمود static_type")
        
        # جدول البروكسيات المجانية
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS free_proxies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول نظام الحظر المتدرج
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_bans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                ban_level INTEGER DEFAULT 0,  -- 0: تحذير، 1: 10 دقائق، 2: ساعتين، 3: 24 ساعة
                ban_start_time TIMESTAMP,
                ban_end_time TIMESTAMP,
                is_banned BOOLEAN DEFAULT FALSE,
                warning_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # جدول تتبع النقرات المتكررة
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS click_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                last_click_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                click_count INTEGER DEFAULT 1,
                reset_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        # جدول معاملات النقاط
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS credits_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                transaction_type TEXT NOT NULL,  -- 'charge', 'spend', 'refund'
                amount REAL NOT NULL,
                order_id TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (order_id) REFERENCES orders (id)
            )
        ''')

        # جدول إدارة حالة الخدمات (تشغيل/إيقاف)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS service_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_type TEXT NOT NULL,  -- 'static' or 'socks' or 'nonvoip'
                service_subtype TEXT,  -- 'monthly_residential', 'weekly_static', 'basic', etc.
                country_code TEXT,  -- 'US', 'UK', 'FR', etc.
                state_code TEXT,  -- 'CA', 'NY', 'TX', etc. (NULL for countries without states)
                is_enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(service_type, service_subtype, country_code, state_code)
            )
        ''')
        
        # Migration: التحقق من البنية القديمة وتحويلها
        cursor.execute("PRAGMA table_info(service_status)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # إذا كانت البنية القديمة (sub_type, country, state)، حولها للبنية الجديدة
        if 'sub_type' in columns and 'service_subtype' not in columns:
            logger.info("🔄 اكتشاف بنية قديمة لجدول service_status - بدء الترحيل...")
            
            # إنشاء نسخة احتياطية من الجدول القديم
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS service_status_backup AS 
                SELECT * FROM service_status
            """)
            
            # إنشاء جدول جديد بالبنية الصحيحة
            cursor.execute("DROP TABLE IF EXISTS service_status_new")
            cursor.execute("""
                CREATE TABLE service_status_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_type TEXT NOT NULL,
                    service_subtype TEXT,
                    country_code TEXT,
                    state_code TEXT,
                    is_enabled BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(service_type, service_subtype, country_code, state_code)
                )
            """)
            
            # نقل البيانات من الجدول القديم للجديد مع تحويل أسماء الأعمدة
            cursor.execute("""
                INSERT INTO service_status_new 
                (service_type, service_subtype, country_code, state_code, is_enabled, created_at, updated_at)
                SELECT 
                    service_type, 
                    sub_type, 
                    country, 
                    state, 
                    is_enabled, 
                    COALESCE(last_updated, CURRENT_TIMESTAMP),
                    COALESCE(last_updated, CURRENT_TIMESTAMP)
                FROM service_status
            """)
            
            # حذف الجدول القديم واستبداله بالجديد
            cursor.execute("DROP TABLE service_status")
            cursor.execute("ALTER TABLE service_status_new RENAME TO service_status")
            
            logger.info("✅ تم ترحيل جدول service_status بنجاح!")
            conn.commit()


        # ===== التحقق وإضافة عمود duration بأمان =====
        try:
            # التحقق من وجود عمود duration في جدول orders
            cursor.execute("PRAGMA table_info(orders)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'duration' not in columns:
                logger.info("🔧 عمود duration غير موجود - جاري إضافته بأمان...")
                cursor.execute("ALTER TABLE orders ADD COLUMN duration TEXT DEFAULT ''")
                conn.commit()
                logger.info("✅ تم إضافة عمود duration بنجاح!")
            else:
                logger.info("✅ عمود duration موجود بالفعل")
        except Exception as e:
            logger.warning(f"⚠️ خطأ في التحقق من عمود duration: {e}")
        # ===== نهاية التحقق من عمود duration =====

        # إضافة الإعدادات الافتراضية
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('credit_price', '1.0')")  # سعر الكريديت الواحد بالدولار
        
        # أسعار Residential Super ($4) حسب المدة - يمكن للآدمن تعديلها من لوحة التحكم
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('res4_weekly_price', '2.5')")
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('res4_15days_price', '3.5')")
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('res4_monthly_price', '4.0')")
        
        # ملاحظة: أسعار البروكسيات (verizon_price, att_price, isp_price) تستخدم القيم الافتراضية من اسم البند
        # الآدمن يمكنه تعديلها من لوحة التحكم فتُحفظ في قاعدة البيانات
        
        # إدراج البيانات الافتراضية لحالة الخدمات (جميع الخدمات مفعلة بشكل افتراضي)
        self._insert_default_service_status(cursor)
        
        # جدول لتتبع الرسائل المحددة من الآدمن (لنظام إدارة الرسائل)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_selected_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (admin_id) REFERENCES users (user_id)
            )
        ''')
        
        # جدول لتتبع نسخ رسائل البوت الموزعة للمستخدمين (لتطبيق العمليات على الجميع)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_message_copies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_message_id INTEGER NOT NULL,
                original_chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                user_chat_id INTEGER NOT NULL,
                user_message_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # جدول لوغز شراء أرقام NonVoip
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nonvoip_purchase_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                order_id TEXT UNIQUE NOT NULL,
                number_type TEXT,
                service_type TEXT,
                price_usd REAL,
                price_credits REAL,
                credit_deducted REAL,
                credit_refunded REAL DEFAULT 0,
                sms_received BOOLEAN DEFAULT 0,
                cancelled BOOLEAN DEFAULT 0,
                refunded BOOLEAN DEFAULT 0,
                refund_amount REAL DEFAULT 0,
                notes TEXT
            )
        ''')
        
        # جدول لوغز التجديد والتفعيل والاستخدام
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nonvoip_renewal_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                order_id TEXT NOT NULL,
                operation_type TEXT,
                original_number TEXT,
                new_number TEXT,
                price_usd REAL,
                price_credits REAL,
                credit_deducted REAL,
                reuse_count INTEGER DEFAULT 0,
                activation_time DATETIME,
                expiry_time DATETIME,
                status TEXT DEFAULT 'active',
                notes TEXT
            )
        ''')
        
        # جدول لتخزين معرفات رسائل إشعارات الآدمن للطلبات (لتحديثها عند إلغاء الطلب)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_admin_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                admin_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _insert_default_service_status(self, cursor):
        """إدراج حالة الخدمات الافتراضية (جميعها مفعلة)"""
        # خدمات ستاتيك
        static_services = [
            ('static', 'monthly_residential', None, None),
            ('static', 'monthly_verizon', None, None), 
            ('static', 'weekly_crocker', None, None),
            ('static', 'daily_static', None, None),
            ('static', 'isp_att', None, None),
            ('static', 'datacenter', None, None)
        ]
        
        # إضافة دول ستاتيك
        for country in ['US', 'UK', 'FR', 'DE', 'AT']:
            static_services.append(('static', 'basic', country, None))
        
        # إضافة ولايات أمريكا للخدمات المختلفة
        us_states = ['NY', 'CA', 'TX', 'FL', 'AZ', 'DE', 'VA', 'WA', 'MA']
        for state in us_states:
            static_services.extend([
                ('static', 'monthly_residential', 'US', state),
                ('static', 'monthly_verizon', 'US', state),
                ('static', 'weekly_crocker', 'US', state),
                ('static', 'datacenter', 'US', state),
                ('static', 'isp_att', 'US', state)
            ])
        
        # خدمات سوكس
        socks_services = [
            ('socks', 'basic', None, None),
            ('socks', 'single', None, None),
            ('socks', 'package_2', None, None),
            ('socks', 'package_5', None, None),
            ('socks', 'package_10', None, None)
        ]
        
        # إضافة دول سوكس لجميع الأنواع الفرعية
        for country in ['US', 'FR', 'ES', 'UK', 'CA', 'DE', 'IT', 'SE']:
            for socks_type in ['basic', 'single', 'package_2', 'package_5', 'package_10']:
                socks_services.append(('socks', socks_type, country, None))
        
        # إضافة ولايات أمريكا للسوكس لجميع الأنواع الفرعية
        for state in us_states:
            for socks_type in ['basic', 'single', 'package_2', 'package_5', 'package_10']:
                socks_services.append(('socks', socks_type, 'US', state))
        
        # إدراج جميع الخدمات
        all_services = static_services + socks_services
        for service in all_services:
            cursor.execute("""
                INSERT OR IGNORE INTO service_status 
                (service_type, service_subtype, country_code, state_code, is_enabled) 
                VALUES (?, ?, ?, ?, TRUE)
            """, service)
    
    def execute_query(self, query: str, params: tuple = ()) -> List[tuple]:
        """تنفيذ استعلام قاعدة البيانات"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_file, timeout=30.0)
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchall()
            conn.commit()
            return result
        except sqlite3.Error as e:
            logger.error(f"Database error in execute_query: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            if conn:
                conn.rollback()
            return []
        except Exception as e:
            logger.error(f"Unexpected error in execute_query: {e}")
            if conn:
                conn.rollback()
            return []
        finally:
            if conn:
                conn.close()
    
    def add_user(self, user_id: int, username: str, first_name: str, last_name: str, referred_by: int = None, language: str = None):
        """إضافة مستخدم جديد"""
        if language:
            query = '''
                INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, referred_by, language)
                VALUES (?, ?, ?, ?, ?, ?)
            '''
            self.execute_query(query, (user_id, username, first_name, last_name, referred_by, language))
        else:
            query = '''
                INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, referred_by)
                VALUES (?, ?, ?, ?, ?)
            '''
            self.execute_query(query, (user_id, username, first_name, last_name, referred_by))
    
    def get_user(self, user_id: int) -> Optional[tuple]:
        """الحصول على بيانات المستخدم"""
        query = "SELECT * FROM users WHERE user_id = ?"
        result = self.execute_query(query, (user_id,))
        return result[0] if result else None
    
    def update_user_language(self, user_id: int, language: str):
        """تحديث لغة المستخدم"""
        query = "UPDATE users SET language = ? WHERE user_id = ?"
        self.execute_query(query, (language, user_id))
    
    # دوال إدارة الرصيد والكريديت
    def get_user_balance(self, user_id: int) -> Dict[str, float]:
        """الحصول على رصيد المستخدم (رصيد الإحالات + رصيد الكريديت)"""
        user_data = self.get_user(user_id)
        if user_data:
            # user_data structure: (user_id, username, first_name, last_name, language, referral_balance, credits_balance, referred_by, join_date, is_admin)
            referral_balance = float(user_data[5] or 0.0)
            credits_balance = float(user_data[6] or 0.0)
            total_balance = referral_balance + credits_balance
            
            return {
                'referral_balance': referral_balance,
                'charged_balance': credits_balance,
                'total_balance': total_balance
            }
        return {'referral_balance': 0.0, 'charged_balance': 0.0, 'total_balance': 0.0}
    
    def add_credits(self, user_id: int, amount: float, transaction_type: str, order_id: str = None, description: str = ""):
        """إضافة كريديت إلى رصيد المستخدم"""
        # تحديث رصيد الكريديت
        query = "UPDATE users SET credits_balance = credits_balance + ? WHERE user_id = ?"
        self.execute_query(query, (amount, user_id))
        
        # إضافة معاملة الكريديت
        self.add_credits_transaction(user_id, transaction_type, amount, order_id, description)
    
    def deduct_credits(self, user_id: int, amount: float, transaction_type: str, order_id: str = None, description: str = "", allow_negative: bool = True):
        """خصم كريديت من رصيد المستخدم (من الرصيد المشحون أولاً ثم الإحالات)"""
        balance = self.get_user_balance(user_id)
        total_balance = balance['total_balance']
        charged_balance = balance['charged_balance']
        referral_balance = balance['referral_balance']
        
        # فحص كفاية الرصيد فقط إذا لم يكن مسموح بالقيم السالبة
        if not allow_negative and total_balance < amount:
            raise ValueError(f"Insufficient total balance. Required: {amount}, Available: {total_balance}")
        
        # حساب المبالغ المطلوبة للخصم
        if charged_balance >= amount:
            # الرصيد المشحون يكفي لوحده
            charged_deduction = amount
            referral_deduction = 0.0
        else:
            # نحتاج للخصم من كلا الرصيدين (حتى لو أصبح سالباً)
            charged_deduction = charged_balance  # خصم كامل الرصيد المشحون
            referral_deduction = amount - charged_balance  # خصم الباقي من الإحالات (قد يصبح سالباً)
        
        # تنفيذ عمليات الخصم (يقبل القيم السالبة)
        if charged_deduction > 0:
            query = "UPDATE users SET credits_balance = credits_balance - ? WHERE user_id = ?"
            self.execute_query(query, (charged_deduction, user_id))
            
        if referral_deduction > 0:
            query = "UPDATE users SET referral_balance = referral_balance - ? WHERE user_id = ?"
            self.execute_query(query, (referral_deduction, user_id))
        
        # إضافة معاملة النقاط (بقيمة سالبة للدلالة على الخصم)
        deduction_description = f"خصم: {charged_deduction:.2f} من الرصيد المشحون"
        if referral_deduction > 0:
            deduction_description += f" + {referral_deduction:.2f} من رصيد الإحالات"
        if description:
            deduction_description += f" - {description}"
            
        self.add_credits_transaction(user_id, transaction_type, -amount, order_id, deduction_description)
    
    def add_credits_transaction(self, user_id: int, transaction_type: str, amount: float, order_id: str = None, description: str = ""):
        """إضافة معاملة كريديت جديدة"""
        query = '''
            INSERT INTO credits_transactions (user_id, transaction_type, amount, order_id, description)
            VALUES (?, ?, ?, ?, ?)
        '''
        self.execute_query(query, (user_id, transaction_type, amount, order_id, description))
    
    def get_credit_price(self) -> float:
        """الحصول على سعر الكريديت الواحد"""
        query = "SELECT value FROM settings WHERE key = 'credit_price'"
        result = self.execute_query(query)
        if result:
            return float(result[0][0])
        return 1.0  # القيمة الافتراضية
    
    def set_credit_price(self, price: float):
        """تعديل سعر الكريديت الواحد"""
        query = "INSERT OR REPLACE INTO settings (key, value) VALUES ('credit_price', ?)"
        self.execute_query(query, (str(price),))
    
    # دوال إدارة حالة الخدمات (تشغيل/إيقاف)
    def get_service_status(self, service_type: str, service_subtype: str = None, 
                          country_code: str = None, state_code: str = None) -> bool:
        """الحصول على حالة خدمة معينة"""
        query = """
            SELECT is_enabled FROM service_status 
            WHERE service_type = ? AND 
                  (service_subtype = ? OR (service_subtype IS NULL AND ? IS NULL)) AND
                  (country_code = ? OR (country_code IS NULL AND ? IS NULL)) AND
                  (state_code = ? OR (state_code IS NULL AND ? IS NULL))
        """
        result = self.execute_query(query, (service_type, service_subtype, service_subtype, 
                                           country_code, country_code, state_code, state_code))
        return bool(result[0][0]) if result else True  # افتراضياً مفعل
    
    def set_service_status(self, service_type: str, is_enabled: bool, 
                          service_subtype: str = None, country_code: str = None, 
                          state_code: str = None):
        """تحديد حالة خدمة معينة"""
        # التحقق من وجود السجل أولاً
        check_query = """
            SELECT id FROM service_status 
            WHERE service_type = ? 
            AND (service_subtype = ? OR (service_subtype IS NULL AND ? IS NULL))
            AND (country_code = ? OR (country_code IS NULL AND ? IS NULL))
            AND (state_code = ? OR (state_code IS NULL AND ? IS NULL))
        """
        existing = self.execute_query(check_query, (service_type, service_subtype, service_subtype, 
                                                     country_code, country_code, state_code, state_code))
        
        if existing:
            # تحديث السجل الموجود
            update_query = """
                UPDATE service_status 
                SET is_enabled = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """
            self.execute_query(update_query, (is_enabled, existing[0][0]))
        else:
            # إدراج سجل جديد
            insert_query = """
                INSERT INTO service_status 
                (service_type, service_subtype, country_code, state_code, is_enabled, updated_at) 
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """
            self.execute_query(insert_query, (service_type, service_subtype, country_code, state_code, is_enabled))
    
    def get_service_subtypes_status(self, service_type: str) -> Dict[str, bool]:
        """الحصول على حالة جميع الأنواع الفرعية لخدمة معينة"""
        query = """
            SELECT service_subtype, is_enabled FROM service_status 
            WHERE service_type = ? AND country_code IS NULL AND state_code IS NULL
        """
        result = self.execute_query(query, (service_type,))
        return {subtype: bool(enabled) for subtype, enabled in result if subtype}
    
    def get_countries_status(self, service_type: str, service_subtype: str = None) -> Dict[str, bool]:
        """الحصول على حالة جميع الدول لخدمة معينة"""
        if service_subtype:
            query = """
                SELECT country_code, is_enabled FROM service_status 
                WHERE service_type = ? AND service_subtype = ? AND country_code IS NOT NULL AND state_code IS NULL
            """
            result = self.execute_query(query, (service_type, service_subtype))
        else:
            query = """
                SELECT country_code, is_enabled FROM service_status 
                WHERE service_type = ? AND country_code IS NOT NULL AND state_code IS NULL
            """
            result = self.execute_query(query, (service_type,))
        return {country: bool(enabled) for country, enabled in result if country}
    
    def get_states_status(self, service_type: str, country_code: str, 
                         service_subtype: str = None) -> Dict[str, bool]:
        """الحصول على حالة جميع الولايات لدولة معينة"""
        if service_subtype:
            query = """
                SELECT state_code, is_enabled FROM service_status 
                WHERE service_type = ? AND service_subtype = ? AND country_code = ? AND state_code IS NOT NULL
            """
            result = self.execute_query(query, (service_type, service_subtype, country_code))
        else:
            query = """
                SELECT state_code, is_enabled FROM service_status 
                WHERE service_type = ? AND country_code = ? AND state_code IS NOT NULL
            """
            result = self.execute_query(query, (service_type, country_code))
        return {state: bool(enabled) for state, enabled in result if state}
    
    def toggle_all_service_subtypes(self, service_type: str, is_enabled: bool):
        """تشغيل/إيقاف جميع الأنواع الفرعية لخدمة معينة"""
        query = """
            UPDATE service_status SET is_enabled = ?, updated_at = CURRENT_TIMESTAMP
            WHERE service_type = ?
        """
        self.execute_query(query, (is_enabled, service_type))
    
    def toggle_all_countries(self, service_type: str, service_subtype: str, is_enabled: bool):
        """تشغيل/إيقاف جميع دول نوع خدمة معين"""
        if service_subtype:
            query = """
                UPDATE service_status SET is_enabled = ?, updated_at = CURRENT_TIMESTAMP
                WHERE service_type = ? AND service_subtype = ?
            """
            self.execute_query(query, (is_enabled, service_type, service_subtype))
        else:
            query = """
                UPDATE service_status SET is_enabled = ?, updated_at = CURRENT_TIMESTAMP
                WHERE service_type = ?
            """
            self.execute_query(query, (is_enabled, service_type))
    
    def toggle_all_states(self, service_type: str, country_code: str, 
                         service_subtype: str, is_enabled: bool):
        """تشغيل/إيقاف جميع ولايات دولة معينة"""
        query = """
            UPDATE service_status SET is_enabled = ?, updated_at = CURRENT_TIMESTAMP
            WHERE service_type = ? AND service_subtype = ? AND country_code = ? AND state_code IS NOT NULL
        """
        self.execute_query(query, (is_enabled, service_type, service_subtype, country_code))
    
    def get_service_statistics(self, service_type: str) -> dict:
        """إحصائيات الخدمة لنوع خدمة معين"""
        try:
            # عدد الطلبات المعالجة لهذا النوع
            query_orders = """
                SELECT COUNT(*) FROM orders 
                WHERE proxy_type = ? AND status = 'processed'
            """
            processed_orders = self.execute_query(query_orders, (service_type,))
            processed_count = processed_orders[0][0] if processed_orders else 0
            
            # عدد الطلبات المعلقة لهذا النوع
            query_pending = """
                SELECT COUNT(*) FROM orders 
                WHERE proxy_type = ? AND status = 'pending'
            """
            pending_orders = self.execute_query(query_pending, (service_type,))
            pending_count = pending_orders[0][0] if pending_orders else 0
            
            # عدد الخدمات المفعلة لهذا النوع
            query_enabled = """
                SELECT COUNT(*) FROM service_status 
                WHERE service_type = 'static' AND service_subtype = ? AND is_enabled = 1
            """
            enabled_services = self.execute_query(query_enabled, (service_type,))
            enabled_count = enabled_services[0][0] if enabled_services else 0
            
            # عدد الخدمات المعطلة لهذا النوع
            query_disabled = """
                SELECT COUNT(*) FROM service_status 
                WHERE service_type = 'static' AND service_subtype = ? AND is_enabled = 0
            """
            disabled_services = self.execute_query(query_disabled, (service_type,))
            disabled_count = disabled_services[0][0] if disabled_services else 0
            
            return {
                'processed_orders': processed_count,
                'pending_orders': pending_count,
                'enabled_services': enabled_count,
                'disabled_services': disabled_count,
                'total_services': enabled_count + disabled_count
            }
        except Exception as e:
            logger.error(f"Error getting service statistics for {service_type}: {e}")
            return {
                'processed_orders': 0,
                'pending_orders': 0,
                'enabled_services': 0,
                'disabled_services': 0,
                'total_services': 0
            }
    
    def create_recharge_order(self, order_id: str, user_id: int, amount: float, expected_credits: float):
        """إنشاء طلب شحن رصيد"""
        query = '''
            INSERT INTO orders (id, user_id, proxy_type, country, state, payment_method, payment_amount, quantity)
            VALUES (?, ?, 'balance_recharge', '', '', '', ?, ?)
        '''
        self.execute_query(query, (order_id, user_id, amount, f'{expected_credits:.2f} points'))
    
    def create_order(self, order_id: str, user_id: int, proxy_type: str, country: str, state: str, payment_method: str, payment_amount: float = 0.0, quantity: str = "5"):
        """إنشاء طلب جديد"""
        # التحقق من وجود عمود static_type وإضافته إذا لزم الأمر (بطريقة آمنة)
        conn = None
        try:
            conn = sqlite3.connect(self.db_file, timeout=30.0)
            cursor = conn.cursor()
            
            # فحص وجود العمود باستخدام PRAGMA
            cursor.execute("PRAGMA table_info(orders)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # إضافة العمود فقط إذا لم يكن موجوداً
            if 'static_type' not in columns:
                try:
                    cursor.execute("ALTER TABLE orders ADD COLUMN static_type TEXT DEFAULT ''")
                    conn.commit()
                    logger.info("✅ Column 'static_type' added to orders table successfully")
                except sqlite3.OperationalError as e:
                    # تجاهل الخطأ إذا كان العمود موجوداً بالفعل
                    if "duplicate column" not in str(e).lower():
                        raise
                    logger.info("ℹ️ Column 'static_type' already exists")
        except sqlite3.Error as e:
            logger.error(f"⚠️ Database error in create_order: {e}")
        finally:
            if conn:
                conn.close()
            
        # إنشاء الطلب
        query = '''
            INSERT INTO orders (id, user_id, proxy_type, country, state, payment_method, payment_amount, quantity, static_type, duration)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        self.execute_query(query, (order_id, user_id, proxy_type, country, state, payment_method, payment_amount, quantity, '', ''))
    
    def update_order_payment_proof(self, order_id: str, payment_proof: str):
        """تحديث إثبات الدفع للطلب"""
        query = "UPDATE orders SET payment_proof = ? WHERE id = ?"
        self.execute_query(query, (payment_proof, order_id))
    
    def get_pending_orders(self) -> List[tuple]:
        """الحصول على الطلبات المعلقة"""
        try:
            query = "SELECT * FROM orders WHERE status = 'pending' ORDER BY created_at DESC"
            result = self.execute_query(query)
            return result if result else []
        except Exception as e:
            logger.error(f"Error in get_pending_orders: {e}")
            print(f"❌ خطأ في استعلام الطلبات المعلقة: {e}")
            return []
    
    def log_action(self, user_id: int, action: str, details: str = ""):
        """تسجيل إجراء في السجل"""
        syria_time = get_syria_time_str()
        query = "INSERT INTO logs (user_id, action, details, timestamp) VALUES (?, ?, ?, ?)"
        self.execute_query(query, (user_id, action, f"[{syria_time}] {details}", syria_time))
    
    def save_order_admin_message(self, order_id: str, admin_id: int, message_id: int):
        """حفظ معرف رسالة الإشعار المرسلة للآدمن"""
        query = "INSERT INTO order_admin_messages (order_id, admin_id, message_id) VALUES (?, ?, ?)"
        self.execute_query(query, (order_id, admin_id, message_id))
    
    def get_order_admin_messages(self, order_id: str) -> List[tuple]:
        """الحصول على معرفات رسائل الإشعارات للطلب"""
        query = "SELECT admin_id, message_id FROM order_admin_messages WHERE order_id = ?"
        result = self.execute_query(query, (order_id,))
        return result if result else []
    
    def delete_order_admin_messages(self, order_id: str):
        """حذف معرفات رسائل الإشعارات للطلب بعد التحديث"""
        query = "DELETE FROM order_admin_messages WHERE order_id = ?"
        self.execute_query(query, (order_id,))
    
    def get_old_payment_proofs(self, days_old: int = 30) -> List[tuple]:
        """
        الحصول على صور التأكيد القديمة (أقدم من X يوم)
        لحذفها وتحرير المساحة
        """
        query = """
            SELECT id, payment_proof, created_at, status 
            FROM orders 
            WHERE payment_proof LIKE 'photo:%' 
            AND created_at < datetime('now', '-' || ? || ' days')
            AND status IN ('completed', 'rejected')
        """
        return self.execute_query(query, (days_old,))
    
    def clear_old_payment_proofs(self, days_old: int = 30) -> int:
        """
        حذف صور التأكيد القديمة من الطلبات المكتملة/المرفوضة
        إرجاع: عدد السجلات المحدثة
        """
        # الحصول على الصور القديمة أولاً
        old_proofs = self.get_old_payment_proofs(days_old)
        
        if not old_proofs:
            return 0
        
        # حذف المرجع للصورة من قاعدة البيانات
        query = """
            UPDATE orders 
            SET payment_proof = NULL 
            WHERE payment_proof LIKE 'photo:%' 
            AND created_at < datetime('now', '-' || ? || ' days')
            AND status IN ('completed', 'rejected')
        """
        self.execute_query(query, (days_old,))
        
        logger.info(f"Cleared {len(old_proofs)} old payment proofs (older than {days_old} days)")
        return len(old_proofs)
    
    def get_payment_proofs_stats(self) -> dict:
        """
        إحصائيات صور التأكيد في قاعدة البيانات
        """
        stats = {
            'total_with_photos': 0,
            'pending_with_photos': 0,
            'completed_with_photos': 0,
            'rejected_with_photos': 0,
            'old_photos_30days': 0,
            'old_photos_60days': 0,
            'old_photos_90days': 0
        }
        
        # إجمالي الطلبات مع صور
        result = self.execute_query("SELECT COUNT(*) FROM orders WHERE payment_proof LIKE 'photo:%'")
        stats['total_with_photos'] = result[0][0] if result else 0
        
        # حسب الحالة
        for status in ['pending', 'completed', 'rejected']:
            result = self.execute_query(
                "SELECT COUNT(*) FROM orders WHERE payment_proof LIKE 'photo:%' AND status = ?",
                (status,)
            )
            stats[f'{status}_with_photos'] = result[0][0] if result else 0
        
        # الصور القديمة
        for days in [30, 60, 90]:
            result = self.execute_query(
                """SELECT COUNT(*) FROM orders 
                   WHERE payment_proof LIKE 'photo:%' 
                   AND created_at < datetime('now', '-' || ? || ' days')
                   AND status IN ('completed', 'rejected')""",
                (days,)
            )
            stats[f'old_photos_{days}days'] = result[0][0] if result else 0
        
        return stats
    
    def get_truly_processed_orders(self) -> List[tuple]:
        """الحصول على الطلبات المعالجة فعلياً فقط (وفقاً للشرطين المحددين)"""
        return self.execute_query("SELECT * FROM orders WHERE truly_processed = TRUE")
    
    def get_unprocessed_orders(self) -> List[tuple]:
        """الحصول على الطلبات غير المعالجة فعلياً (بغض النظر عن الحالة)"""
        return self.execute_query("SELECT * FROM orders WHERE truly_processed = FALSE OR truly_processed IS NULL")
    
    def validate_database_integrity(self) -> dict:
        """فحص سلامة قاعدة البيانات"""
        try:
            validation_results = {
                'database_accessible': True,
                'tables_exist': True,
                'data_integrity': True,
                'errors': []
            }
            
            # فحص إمكانية الوصول لقاعدة البيانات
            try:
                conn = sqlite3.connect(self.db_file, timeout=10.0)
                conn.close()
            except Exception as e:
                validation_results['database_accessible'] = False
                validation_results['errors'].append(f"Database access error: {e}")
                return validation_results
            
            # فحص وجود الجداول المطلوبة
            required_tables = ['users', 'orders', 'referrals', 'settings', 'transactions', 'logs']
            existing_tables = self.execute_query("SELECT name FROM sqlite_master WHERE type='table'")
            existing_table_names = [table[0] for table in existing_tables]
            
            for table in required_tables:
                if table not in existing_table_names:
                    validation_results['tables_exist'] = False
                    validation_results['errors'].append(f"Missing table: {table}")
            
            # فحص سلامة البيانات
            try:
                # فحص الطلبات بدون مستخدمين
                orphaned_orders = self.execute_query("""
                    SELECT COUNT(*) FROM orders 
                    WHERE user_id NOT IN (SELECT user_id FROM users)
                """)
                if orphaned_orders and orphaned_orders[0][0] > 0:
                    validation_results['data_integrity'] = False
                    validation_results['errors'].append(f"Orphaned orders: {orphaned_orders[0][0]}")
                
                # فحص الطلبات التالفة
                corrupt_orders = self.execute_query("""
                    SELECT COUNT(*) FROM orders 
                    WHERE id IS NULL OR user_id IS NULL OR proxy_type IS NULL
                """)
                if corrupt_orders and corrupt_orders[0][0] > 0:
                    validation_results['data_integrity'] = False
                    validation_results['errors'].append(f"Corrupt orders: {corrupt_orders[0][0]}")
                    
            except Exception as e:
                validation_results['data_integrity'] = False
                validation_results['errors'].append(f"Data integrity check failed: {e}")
            
            return validation_results
            
        except Exception as e:
            return {
                'database_accessible': False,
                'tables_exist': False,
                'data_integrity': False,
                'errors': [f"Validation failed: {e}"]
            }


# ============================================
# نظام الحظر المتدرج
# ============================================

def track_user_click(user_id: int) -> tuple:
    """تتبع النقرات المتكررة للمستخدم وإرجاع (عدد النقرات, الوقت منذ آخر نقرة)"""
    from datetime import datetime, timedelta
    
    current_time = datetime.now()
    
    # فحص النقرات الموجودة للمستخدم
    query = "SELECT click_count, last_click_time, reset_time FROM click_tracking WHERE user_id = ?"
    result = db.execute_query(query, (user_id,))
    
    if result:
        click_count, last_click_str, reset_time_str = result[0]
        last_click_time = datetime.fromisoformat(last_click_str)
        reset_time = datetime.fromisoformat(reset_time_str)
        
        # إعادة تعيين العداد إذا مر أكثر من 5 ثانية على آخر نقرة
        if (current_time - last_click_time).seconds > 5:
            click_count = 1
            reset_time = current_time
        else:
            click_count += 1
        
        # تحديث السجل
        update_query = "UPDATE click_tracking SET click_count = ?, last_click_time = ?, reset_time = ? WHERE user_id = ?"
        db.execute_query(update_query, (click_count, current_time.isoformat(), reset_time.isoformat(), user_id))
        
    else:
        # إنشاء سجل جديد للمستخدم
        click_count = 1
        reset_time = current_time
        insert_query = "INSERT INTO click_tracking (user_id, click_count, last_click_time, reset_time) VALUES (?, ?, ?, ?)"
        db.execute_query(insert_query, (user_id, click_count, current_time.isoformat(), reset_time.isoformat()))
    
    return click_count, (current_time - reset_time).seconds

def is_user_banned(user_id: int) -> tuple:
    """فحص ما إذا كان المستخدم محظوراً - إرجاع (محظور؟, مستوى الحظر, وقت انتهاء الحظر)"""
    from datetime import datetime
    
    query = "SELECT is_banned, ban_level, ban_end_time FROM user_bans WHERE user_id = ? ORDER BY created_at DESC LIMIT 1"
    result = db.execute_query(query, (user_id,))
    
    if result:
        is_banned, ban_level, ban_end_time_str = result[0]
        if is_banned and ban_end_time_str:
            ban_end_time = datetime.fromisoformat(ban_end_time_str)
            # فحص ما إذا كان الحظر انتهى
            if datetime.now() >= ban_end_time:
                # رفع الحظر تلقائياً مع الإشعارات
                was_lifted = lift_user_ban(user_id)
                if was_lifted:
                    # إضافة مهمة الإشعار إلى قائمة الانتظار
                    global pending_unban_notifications
                    if 'pending_unban_notifications' not in globals():
                        pending_unban_notifications = []
                    pending_unban_notifications.append(user_id)
                return False, 0, None
            else:
                return True, ban_level, ban_end_time
        else:
            return False, 0, None
    else:
        return False, 0, None

def apply_progressive_ban(user_id: int, click_count: int) -> str:
    """تطبيق نظام الحظر المتدرج بناءً على عدد النقرات"""
    from datetime import datetime, timedelta
    
    current_time = datetime.now()
    
    # فحص مستوى الحظر الحالي
    query = "SELECT ban_level, warning_count FROM user_bans WHERE user_id = ? ORDER BY created_at DESC LIMIT 1"
    result = db.execute_query(query, (user_id,))
    
    if result:
        current_ban_level, warning_count = result[0]
    else:
        current_ban_level = 0
        warning_count = 0
    
    # تحديد المرحلة بناءً على عدد النقرات (15-17 مرة)
    if 15 <= click_count <= 17:
        if current_ban_level == 0:  # تحذير
            warning_count += 1
            if warning_count >= 2:  # بعد تحذيرين، ننتقل للحظر الأول
                # حظر 10 دقائق
                ban_end_time = current_time + timedelta(minutes=10)
                insert_or_update_ban(user_id, 1, current_time, ban_end_time, True, warning_count)
                return "ban_10_min"
            else:
                # تحذير
                insert_or_update_ban(user_id, 0, current_time, None, False, warning_count)
                return "warning"
                
        elif current_ban_level == 1:  # من 10 دقائق إلى ساعتين
            ban_end_time = current_time + timedelta(hours=2)
            insert_or_update_ban(user_id, 2, current_time, ban_end_time, True, warning_count)
            return "ban_2_hours"
            
        elif current_ban_level == 2:  # من ساعتين إلى 24 ساعة
            ban_end_time = current_time + timedelta(hours=24)
            insert_or_update_ban(user_id, 3, current_time, ban_end_time, True, warning_count)
            return "ban_24_hours"
    
    return "no_action"

def insert_or_update_ban(user_id: int, ban_level: int, start_time: datetime, end_time: datetime = None, is_banned: bool = False, warning_count: int = 0):
    """إدراج أو تحديث سجل الحظر"""
    # فحص ما إذا كان هناك سجل موجود
    existing_query = "SELECT id FROM user_bans WHERE user_id = ?"
    result = db.execute_query(existing_query, (user_id,))
    
    if result:
        # تحديث السجل الموجود
        update_query = """
            UPDATE user_bans 
            SET ban_level = ?, ban_start_time = ?, ban_end_time = ?, is_banned = ?, warning_count = ?, updated_at = ?
            WHERE user_id = ?
        """
        end_time_str = end_time.isoformat() if end_time else None
        db.execute_query(update_query, (ban_level, start_time.isoformat(), end_time_str, is_banned, warning_count, start_time.isoformat(), user_id))
    else:
        # إنشاء سجل جديد
        insert_query = """
            INSERT INTO user_bans (user_id, ban_level, ban_start_time, ban_end_time, is_banned, warning_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        end_time_str = end_time.isoformat() if end_time else None
        db.execute_query(insert_query, (user_id, ban_level, start_time.isoformat(), end_time_str, is_banned, warning_count))

def lift_user_ban(user_id: int) -> bool:
    """رفع الحظر عن المستخدم - إرجاع True إذا تم رفع الحظر فعلاً"""
    from datetime import datetime
    
    # فحص ما إذا كان المستخدم محظوراً حالياً
    check_query = "SELECT is_banned FROM user_bans WHERE user_id = ? AND is_banned = TRUE"
    result = db.execute_query(check_query, (user_id,))
    
    if result:
        # رفع الحظر
        update_query = "UPDATE user_bans SET is_banned = FALSE, updated_at = ? WHERE user_id = ?"
        db.execute_query(update_query, (datetime.now().isoformat(), user_id))
        return True  # تم رفع الحظر
    
    return False  # لم يكن محظوراً أساساً

def reset_user_clicks(user_id: int):
    """إعادة تعيين عداد النقرات للمستخدم"""
    from datetime import datetime
    
    query = "UPDATE click_tracking SET click_count = 0, reset_time = ? WHERE user_id = ?"
    db.execute_query(query, (datetime.now().isoformat(), user_id))

# ============================================
# دوال الخدمات
# ============================================

def get_residential_service_status(service_code: str) -> bool:
    """
    الحصول على حالة خدمة Residential ISP محددة
    
    Args:
        service_code: كود الخدمة (مثل CO_EB, VA_WS, UK_BC)
    
    Returns:
        True إذا كانت الخدمة مفعّلة، False إذا كانت معطّلة
    """
    try:
        result = db.get_service_status('static', 'residential_isp', None, service_code)
        return bool(result) if result is not None else True
    except Exception as e:
        logger.error(f"خطأ في get_residential_service_status: {e}")
        return True

def set_residential_service_status(service_code: str, enabled: bool) -> bool:
    """
    تعيين حالة خدمة Residential ISP محددة
    
    Args:
        service_code: كود الخدمة (مثل CO_EB, VA_WS, UK_BC)
        enabled: True للتفعيل، False للتعطيل
    
    Returns:
        True عند النجاح
    """
    try:
        db.set_service_status('static', enabled, 'residential_isp', None, service_code)
        logger.info(f"تم {'تفعيل' if enabled else 'تعطيل'} الخدمة {service_code}")
        return True
    except Exception as e:
        logger.error(f"خطأ في set_residential_service_status: {e}")
        return False

def get_current_price(price_type: str) -> str:
    """الحصول على السعر الحالي من قاعدة البيانات"""
    try:
        # للأسعار الخاصة، نحتاج للبحث في static_prices
        if price_type in ['weekly', 'datacenter', 'virgin_residential']:
            static_prices = get_static_prices()
            if price_type == 'weekly':
                return static_prices.get('Weekly', '2.5')
            elif price_type == 'datacenter':
                return static_prices.get('Datacenter', '12')
            elif price_type == 'virgin_residential':
                return static_prices.get('Virgin_Res', '9')
            elif price_type == 'daily':
                return static_prices.get('Daily', '0.25')
        
        result = db.execute_query(f"SELECT value FROM settings WHERE key = '{price_type}_price'")
        if result:
            return result[0][0]
        else:
            # أسعار افتراضية
            defaults = {
                'verizon': '4',
                'att': '6', 
                'isp': '3',
                'weekly': '2.5',
                'virgin_residential': '9',
                'daily': '0.25'
            }
            return defaults.get(price_type, '3')
    except:
        defaults = {
            'verizon': '4',
            'att': '6',
            'isp': '3',
            'weekly': '2.5',
            'virgin_residential': '9',
            'daily': '0.25'
        }
        return defaults.get(price_type, '3')

# ============================================
# دوال الأسعار
# ============================================

def get_static_prices():
    """الحصول على جميع أسعار البروكسي الستاتيك من قاعدة البيانات"""
    try:
        static_prices_result = db.execute_query("SELECT value FROM settings WHERE key = 'static_prices'")
        if static_prices_result:
            static_prices_text = static_prices_result[0][0]
            if "," in static_prices_text:
                price_parts = static_prices_text.split(",")
                static_prices = {}
                for part in price_parts:
                    if ":" in part:
                        key, value = part.split(":", 1)
                        static_prices[key.strip()] = value.strip()
                return static_prices
            else:
                # إذا لم تكن في التنسيق الجديد، عودة للتنسيق الافتراضي
                return {
                    'ISP': '3',
                    'Res_1': '4',
                    'Res_2': '6',
                    'Daily': '0.25',
                    'Weekly': '2.5',
                    'Datacenter': '12',
                    'Virgin_Res': '9'
                }
        else:
            # قيم افتراضية إذا لم توجد في قاعدة البيانات
            return {
                'ISP': '3',
                'Res_1': '4',
                'Res_2': '6',
                'Daily': '0.25',
                'Weekly': '2.5',
                'Datacenter': '12',
                'Virgin_Res': '9'
            }
    except:
        # في حالة الخطأ، قيم افتراضية
        return {
            'ISP': '3',
            'Res_1': '4',
            'Res_2': '6',
            'Daily': '0.25',
            'Weekly': '2.5',
            'Datacenter': '12',
            'Virgin_Res': '9'
        }

def get_socks_prices():
    """الحصول على جميع أسعار بروكسي السوكس من قاعدة البيانات"""
    try:
        socks_prices_result = db.execute_query("SELECT value FROM settings WHERE key = 'socks_prices'")
        if socks_prices_result:
            socks_prices_text = socks_prices_result[0][0]
            if "," in socks_prices_text:
                price_parts = socks_prices_text.split(",")
                socks_prices = {}
                for part in price_parts:
                    if ":" in part:
                        key, value = part.split(":", 1)
                        socks_prices[key.strip()] = value.strip()
                return socks_prices
            else:
                return {
                    'single_proxy': socks_prices_text.strip(),
                    'double_proxy': str(float(socks_prices_text.strip()) * 1.8),
                    '5proxy': socks_prices_text.strip(),
                    '10proxy': '0.7'
                }
        else:
            return {
                'single_proxy': '0.15',
                'double_proxy': '0.25',
                '5proxy': '0.4',
                '10proxy': '0.7'
            }
    except:
        return {
            'single_proxy': '0.15',
            'double_proxy': '0.25',
            '5proxy': '0.4',
            '10proxy': '0.7'
        }

def get_detailed_proxy_type(proxy_type: str, static_type: str = "", country: str = "") -> str:
    """تحويل نوع البروكسي إلى وصف مفصل"""
    if proxy_type == 'dynamic_service':
        # للطلبات الديناميكية: استخراج اسم الزر الأول من المسار
        if country:
            # المسار يكون بشكل "1. اسم الزر الأول\n2. اسم الزر الثاني..."
            lines = country.strip().split('\n')
            if lines:
                first_line = lines[0]
                # إزالة الرقم والنقطة من البداية (مثل "1. ")
                if '. ' in first_line:
                    return first_line.split('. ', 1)[1].strip()
                return first_line.strip()
        # إذا لم يوجد مسار، استخدم الخدمة (state) أو مفتاح الزر
        return static_type if static_type else "طلب خدمة"
    elif proxy_type == 'static':
        if static_type == 'residential_verizon':
            return "ستاتيك ريزيدنتال Verizon"
        elif static_type == 'residential_crocker':
            return "ستاتيك ريزيدنتال Crocker"
        elif static_type == 'residential_att':
            return "ستاتيك ريزيدنتال"
        elif static_type == 'isp':
            return "ستاتيك ISP"
        elif static_type == 'daily':
            return "ستاتيك يومي"
        elif static_type == 'weekly':
            return "ستاتيك اسبوعي"
        elif static_type == 'verizon_weekly':
            return "ستاتيك أسبوعي"
        else:
            return "ستاتيك"
    elif proxy_type == 'socks':
        return "سوكس"
    elif proxy_type == 'http':
        return "HTTP"
    elif proxy_type == 'ستاتيك يومي':
        return "ستاتيك يومي"
    elif proxy_type == 'ستاتيك اسبوعي':
        return "ستاتيك اسبوعي"
    else:
        return proxy_type

def get_proxy_price(proxy_type: str, country: str = "", state: str = "", static_type: str = "", duration_type: str = "") -> float:
    """حساب سعر البروكسي بناءً على النوع والدولة"""
    try:
        if proxy_type == 'static':
            # تحديد السعر بناءً على نوع الستاتيك الجديد
            if static_type == 'virgin_residential':
                # Virgin Residential: الحصول من static_prices
                static_prices = get_static_prices()
                price = float(static_prices.get('Virgin_Res', '9'))
                logger.info(f"✅ PRICE: virgin_residential = ${price}")
                return price
            elif static_type == 'residential_verizon':
                verizon_price_result = db.execute_query("SELECT value FROM settings WHERE key = 'verizon_price'")
                if verizon_price_result:
                    price = float(verizon_price_result[0][0])
                    logger.info(f"✅ PRICE: residential_verizon (from DB) = ${price}")
                    return price
                logger.warning("⚠️ PRICE: residential_verizon fallback to $4")
                return 4.0  # سعر افتراضي
            elif static_type == 'residential_crocker':
                # سعر Crocker - استخدام السعر حسب المدة (Residential Super)
                logger.info("residential_crocker should use Residential Super duration-based pricing")
                return None  # سيتم استخدام السعر المحفوظ في payment_amount
            elif static_type == 'residential_level3':
                # سعر Level 3 ISP - استخدام السعر حسب المدة (Residential Super)
                logger.info("residential_level3 should use Residential Super duration-based pricing")
                return None  # سيتم استخدام السعر المحفوظ في payment_amount
            elif static_type == 'residential_frontier':
                # سعر Frontier Communications - استخدام السعر حسب المدة (Residential Super)
                logger.info("residential_frontier should use Residential Super duration-based pricing")
                return None  # سيتم استخدام السعر المحفوظ في payment_amount
            elif static_type == 'residential_ntt':
                # سعر NTT England - استخدام السعر حسب المدة (Residential Super)
                # هذا جزء من نظام Residential Super الذي يحسب السعر حسب المدة
                logger.info("residential_ntt should use Residential Super duration-based pricing")
                return None  # سيتم استخدام السعر المحفوظ في payment_amount
            elif static_type == 'residential_att':
                att_price_result = db.execute_query("SELECT value FROM settings WHERE key = 'att_price'")
                if att_price_result:
                    price = float(att_price_result[0][0])
                    logger.info(f"✅ PRICE: residential_att (AT&T) (from DB) = ${price}")
                    return price
                logger.warning("⚠️ PRICE: residential_att (AT&T) fallback to $6")
                return 6.0  # سعر افتراضي
            elif static_type == 'isp':
                isp_price_result = db.execute_query("SELECT value FROM settings WHERE key = 'isp_price'")
                if isp_price_result:
                    price = float(isp_price_result[0][0])
                    logger.info(f"✅ PRICE: isp (from DB) = ${price}")
                    return price
                logger.warning("⚠️ PRICE: isp fallback to $3")
                return 3.0  # سعر افتراضي
            elif static_type == 'verizon_weekly':
                # السعر من إعدادات الستاتيك Weekly
                static_prices = get_static_prices()
                price = float(static_prices.get('Weekly', '2.5'))
                logger.info(f"✅ PRICE: verizon_weekly = ${price}")
                return price
            elif static_type == 'daily':
                # السعر من إعدادات الستاتيك Daily
                static_prices = get_static_prices()
                price = float(static_prices.get('Daily', '0.25'))
                logger.info(f"✅ PRICE: daily = ${price}")
                return price
            elif static_type.startswith('residential_'):
                # تحديد ما إذا كان من فئة $6 (AT&T) أو $4 (Verizon)
                # فئة $6 (AT&T): جميع RES6 USA states + UK providers
                res6_types = [
                    'residential_att',  # AT&T الأصلي
                    # RES6 USA States:
                    'residential_elite', 'residential_windstream', 'residential_cox',
                    'residential_frontier_va', 'residential_jymobile_tx', 'residential_wstelcom_ny',
                    'residential_century', 'residential_access', 'residential_jymobile_az', 'residential_wstelcom_fl',
                    # RES6 UK Providers:
                    'residential_british', 'residential_proper', 'residential_linkweb',
                    'residential_uk_wstelcom', 'residential_base', 'residential_virgin_uk',
                    # RES6 New Countries:
                    'residential_france', 'residential_germany', 'residential_austria'
                ]
                
                if static_type in res6_types:
                    # استخدم سعر AT&T ($6)
                    att_price_result = db.execute_query("SELECT value FROM settings WHERE key = 'att_price'")
                    if att_price_result:
                        price = float(att_price_result[0][0])
                        logger.info(f"✅ PRICE: {static_type} (Residential $6 / AT&T tier, from DB att_price) = ${price}")
                        return price
                    logger.warning(f"⚠️ PRICE: {static_type} (Residential $6 / AT&T tier) fallback to $6")
                    return 6.0
                else:
                    # جميع الأنواع الأخرى → استخدم سعر Residential Super حسب المدة
                    # فئة $4: USA (Verizon, Crocker, Level3, Frontier, NTT) + England (نفس المزودين) + 15 دولة
                    # التحقق من وجود مدة محددة لـ Residential Super
                    if duration_type in ['weekly', '15days', 'monthly']:
                        price_key_map = {
                            'weekly': 'res4_weekly_price',
                            '15days': 'res4_15days_price',
                            'monthly': 'res4_monthly_price'
                        }
                        price_key = price_key_map[duration_type]
                        duration_price_result = db.execute_query("SELECT value FROM settings WHERE key = ?", (price_key,))
                        if duration_price_result:
                            price = float(duration_price_result[0][0])
                            logger.info(f"✅ PRICE: {static_type} Residential Super ({duration_type}) = ${price}")
                            return price
                        else:
                            logger.warning(f"⚠️ PRICE: {duration_type} not found in DB, using verizon_price fallback")
                    
                    # استخدام verizon_price كقيمة افتراضية
                    verizon_price_result = db.execute_query("SELECT value FROM settings WHERE key = 'verizon_price'")
                    if verizon_price_result:
                        price = float(verizon_price_result[0][0])
                        logger.info(f"✅ PRICE: {static_type} (Residential $4 / Verizon tier, from DB verizon_price) = ${price}")
                        return price
                    logger.warning(f"⚠️ PRICE: {static_type} (Residential $4 / Verizon tier) fallback to $4")
                    return 4.0
            else:
                # للتوافق مع النظام القديم
                logger.warning(f"⚠️ PRICE WARNING: static_type='{static_type}' not recognized, using legacy pricing logic")
                static_prices_result = db.execute_query("SELECT value FROM settings WHERE key = 'static_prices'")
                if static_prices_result:
                    static_prices_text = static_prices_result[0][0]
                    if "," in static_prices_text:
                        price_parts = static_prices_text.split(",")
                        static_prices = {}
                        for part in price_parts:
                            if ":" in part:
                                key, value = part.split(":", 1)
                                static_prices[key.strip()] = float(value.strip())
                        # تحديد السعر بناءً على نوع الستاتيك
                        if "Crocker" in state or "crocker" in state.lower():
                            price = static_prices.get('Crocker', 4.0)
                            logger.info(f"✅ PRICE (legacy): Crocker from state match = ${price}")
                            return price
                        elif "AT&T" in state or "att" in state.lower():
                            price = static_prices.get('ATT', 6.0)
                            logger.info(f"✅ PRICE (legacy): AT&T from state match = ${price}")
                            return price
                        else:
                            price = static_prices.get('ISP', 3.0)
                            logger.info(f"✅ PRICE (legacy): ISP default = ${price}")
                            return price
                    else:
                        return float(static_prices_text.strip())
            logger.error(f"🚨 PRICE ERROR: Falling back to $3 for static_type='{static_type}', country='{country}', state='{state}' - THIS MAY BE INCORRECT!")
            return 3.0  # سعر افتراضي للستاتيك
        
        elif proxy_type == 'socks':
            # تحميل أسعار السوكس من قاعدة البيانات
            socks_prices_result = db.execute_query("SELECT value FROM settings WHERE key = 'socks_prices'")
            if socks_prices_result:
                socks_prices_text = socks_prices_result[0][0]
                if "," in socks_prices_text:
                    price_parts = socks_prices_text.split(",")
                    socks_prices = {}
                    for part in price_parts:
                        if ":" in part:
                            key, value = part.split(":", 1)
                            socks_prices[key.strip()] = float(value.strip())
                    return socks_prices.get('5proxy', 0.4)  # افتراضي 5 بروكسيات
                else:
                    return float(socks_prices_text.strip())
            return 0.4  # سعر افتراضي للسوكس
        
        return 0.0
    except Exception as e:
        print(f"خطأ في حساب سعر البروكسي: {e}")
        return 3.0 if proxy_type == 'static' else 0.4

def load_saved_prices():
    """تحميل الأسعار المحفوظة من قاعدة البيانات عند بدء تشغيل البوت"""
    try:
        # تحميل أسعار الستاتيك
        static_prices_result = db.execute_query("SELECT value FROM settings WHERE key = 'static_prices'")
        if static_prices_result:
            static_prices_text = static_prices_result[0][0]
            try:
                if "," in static_prices_text:
                    price_parts = static_prices_text.split(",")
                    static_prices = {}
                    for part in price_parts:
                        if ":" in part:
                            key, value = part.split(":", 1)
                            static_prices[key.strip()] = value.strip()
                else:
                    static_prices = {
                        "ISP": static_prices_text.strip(),
                        "Crocker": static_prices_text.strip(), 
                        "ATT": static_prices_text.strip()
                    }
                
                # تحديث رسائل الستاتيك
                update_static_messages(static_prices)
                print(f"📊 تم تحميل أسعار الستاتيك: {static_prices}")
            except Exception as e:
                print(f"خطأ في تحليل أسعار الستاتيك: {e}")
        
        # تحميل أسعار السوكس
        socks_prices_result = db.execute_query("SELECT value FROM settings WHERE key = 'socks_prices'")
        if socks_prices_result:
            socks_prices_text = socks_prices_result[0][0]
            try:
                if "," in socks_prices_text:
                    price_parts = socks_prices_text.split(",")
                    socks_prices = {}
                    for part in price_parts:
                        if ":" in part:
                            key, value = part.split(":", 1)
                            socks_prices[key.strip()] = value.strip()
                else:
                    socks_prices = {
                        "5proxy": socks_prices_text.strip(),
                        "10proxy": "0.7"
                    }
                
                # تحديث رسائل السوكس
                update_socks_messages(socks_prices)
                print(f"📊 تم تحميل أسعار السوكس: {socks_prices}")
            except Exception as e:
                print(f"خطأ في تحليل أسعار السوكس: {e}")
        
        # تحميل قيمة الإحالة
        referral_amount_result = db.execute_query("SELECT value FROM settings WHERE key = 'referral_amount'")
        if referral_amount_result:
            referral_amount = float(referral_amount_result[0][0])
            print(f"💰 تم تحميل قيمة الإحالة: {referral_amount}$")
        
    except Exception as e:
        print(f"خطأ في تحميل الأسعار المحفوظة: {e}")

def update_static_messages(static_prices):
    """تحديث رسائل البروكسي الستاتيك"""
    new_static_message_ar = f"""📦 باكج البروكسي الستاتيك

━━━━━━━━━━━━━━━
📋 بعد اختيار الخدمة:
✅ سيستقبل الأدمن طلبك
⚡ سنعالج الطلب ونرسل لك البروكسي
📬 ستصلك رسالة تأكيد عند الانتهاء

معرف الطلب: {{order_id}}"""

    new_static_message_en = f"""📦 Static Proxy Package

━━━━━━━━━━━━━━━
📋 After selecting service:
✅ Admin will receive your order
⚡ We'll process and send you the proxy
📬 You'll get confirmation when ready

Order ID: {{order_id}}"""

    # تحديث الرسائل في الكود
    MESSAGES['ar']['static_package'] = new_static_message_ar
    MESSAGES['en']['static_package'] = new_static_message_en

def update_socks_messages(socks_prices):
    """تحديث رسائل بروكسي السوكس"""
    new_socks_message_ar = f"""📦 باكج البروكسي السوكس
🌍 جميع دول العالم | اختيار الولاية والمزود

🔹 الأسعار المتوفرة:
• بروكسي واحد: {socks_prices.get('single_proxy', '0.15')}$
• بروكسيان اثنان: {socks_prices.get('double_proxy', '0.25')}$  
• باكج 5 بروكسيات يومية: {socks_prices.get('5proxy', '0.4')}$
• باكج 10 بروكسيات يومية: {socks_prices.get('10proxy', '0.7')}$

━━━━━━━━━━━━━━━
📋 بعد اختيار الخدمة:
✅ سيستقبل الأدمن طلبك
⚡ سنعالج الطلب ونرسل لك البروكسي
📬 ستصلك رسالة تأكيد عند الانتهاء

معرف الطلب: {{order_id}}"""

    new_socks_message_en = f"""📦 Socks Proxy Package
🌍 Worldwide | Choose State & Provider

🔹 Available Prices:
• One Proxy: {socks_prices.get('single_proxy', '0.15')}$
• Two Proxies: {socks_prices.get('double_proxy', '0.25')}$
• 5 Daily Proxies Package: {socks_prices.get('5proxy', '0.4')}$
• 10 Daily Proxies Package: {socks_prices.get('10proxy', '0.7')}$

━━━━━━━━━━━━━━━
📋 After selecting service:
✅ Admin will receive your order
⚡ We'll process and send you the proxy
📬 You'll get confirmation when ready

Order ID: {{order_id}}"""

    # تحديث الرسائل في الكود
    MESSAGES['ar']['socks_package'] = new_socks_message_ar
    MESSAGES['en']['socks_package'] = new_socks_message_en

def generate_order_id() -> str:
    """إنشاء معرف طلب فريد مكون من 16 خانة"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))


# ============================================
# إعدادات قناة البوت والاشتراك الإجباري
# ============================================

def get_bot_setting(key: str, default: str = None) -> Optional[str]:
    """الحصول على إعداد من جدول settings"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else default

def set_bot_setting(key: str, value: str):
    """حفظ إعداد في جدول settings"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
    ''', (key, value))
    conn.commit()
    conn.close()

def get_bot_channel() -> str:
    """الحصول على قناة البوت"""
    return get_bot_setting('bot_channel', '')

def set_bot_channel(channel: str):
    """تعيين قناة البوت"""
    set_bot_setting('bot_channel', channel)

def is_forced_subscription_enabled() -> bool:
    """التحقق من تفعيل الاشتراك الإجباري"""
    return get_bot_setting('forced_subscription', '0') == '1'

def set_forced_subscription(enabled: bool):
    """تعيين حالة الاشتراك الإجباري"""
    set_bot_setting('forced_subscription', '1' if enabled else '0')

def update_user_subscription_status(user_id: int, is_subscribed: bool):
    """تحديث حالة اشتراك المستخدم في قاعدة البيانات"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    # إضافة عمود is_subscribed إذا لم يكن موجوداً
    try:
        cursor.execute("SELECT is_subscribed FROM users LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE users ADD COLUMN is_subscribed INTEGER DEFAULT 0")
    
    cursor.execute('UPDATE users SET is_subscribed = ? WHERE user_id = ?', 
                   (1 if is_subscribed else 0, user_id))
    conn.commit()
    conn.close()

def get_user_subscription_status(user_id: int) -> bool:
    """الحصول على حالة اشتراك المستخدم"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT is_subscribed FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] == 1 if result and result[0] is not None else False
    except sqlite3.OperationalError:
        conn.close()
        return False


# ============================================
# تهيئة قاعدة البيانات
# ============================================

# إنشاء كائن قاعدة البيانات
db = DatabaseManager(DATABASE_FILE)
