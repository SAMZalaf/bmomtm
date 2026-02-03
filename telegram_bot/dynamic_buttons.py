#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================
نظام الأزرار الديناميكية - dynamic_buttons.py
============================================
يسمح للآدمن بـ:
1. إضافة/حذف أزرار في أي مستوى
2. تفعيل/إيقاف أي زر
3. تحديد الأسعار والرسائل لكل زر
4. سؤال الكمية أو استخدام الافتراضي (1)
5. تتبع مسار المستخدم في الطلب
============================================
"""

import sqlite3
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from config import DATABASE_FILE

logger = logging.getLogger(__name__)


class DynamicButtonsManager:
    """مدير الأزرار الديناميكية"""
    
    def __init__(self, db_file: str = DATABASE_FILE):
        self.db_file = db_file
        self.init_tables()
    
    def _get_connection(self):
        """إنشاء اتصال بقاعدة البيانات مع إعدادات لتجنب التضارب"""
        conn = sqlite3.connect(self.db_file, timeout=10.0)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA synchronous = NORMAL")
        return conn
    
    def init_tables(self):
        """إنشاء جداول الأزرار الديناميكية"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dynamic_buttons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER DEFAULT NULL,
                button_key TEXT UNIQUE NOT NULL,
                text_ar TEXT NOT NULL,
                text_en TEXT NOT NULL,
                button_type TEXT DEFAULT 'menu',
                is_enabled BOOLEAN DEFAULT TRUE,
                is_service BOOLEAN DEFAULT FALSE,
                price REAL DEFAULT 0.0,
                ask_quantity BOOLEAN DEFAULT FALSE,
                default_quantity INTEGER DEFAULT 1,
                show_back_on_quantity INTEGER DEFAULT 1,
                show_cancel_on_quantity INTEGER DEFAULT 1,
                message_ar TEXT DEFAULT '',
                message_en TEXT DEFAULT '',
                order_index INTEGER DEFAULT 0,
                icon TEXT DEFAULT '',
                callback_data TEXT DEFAULT '',
                back_behavior TEXT DEFAULT 'step',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES dynamic_buttons(id) ON DELETE CASCADE
            )
        ''')
        
        # إضافة أعمدة جديدة إذا لم تكن موجودة (للتوافق مع قواعد البيانات القديمة)
        try:
            cursor.execute("ALTER TABLE dynamic_buttons ADD COLUMN back_behavior TEXT DEFAULT 'step'")
        except sqlite3.OperationalError:
            pass  # العمود موجود بالفعل
        
        try:
            cursor.execute("ALTER TABLE dynamic_buttons ADD COLUMN show_back_on_quantity INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass  # العمود موجود بالفعل
        
        try:
            cursor.execute("ALTER TABLE dynamic_buttons ADD COLUMN show_cancel_on_quantity INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass  # العمود موجود بالفعل
        
        try:
            cursor.execute("ALTER TABLE dynamic_buttons ADD COLUMN button_size TEXT DEFAULT 'large'")
        except sqlite3.OperationalError:
            pass  # العمود موجود بالفعل
        
        try:
            cursor.execute("ALTER TABLE dynamic_buttons ADD COLUMN is_hidden INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # العمود موجود بالفعل
        
        try:
            cursor.execute("ALTER TABLE dynamic_buttons ADD COLUMN disabled_message TEXT DEFAULT 'هذه الخدمة متوقفة مؤقتاً'")
        except sqlite3.OperationalError:
            pass  # العمود موجود بالفعل
        
        # إنشاء جدول bot_settings إذا لم يكن موجوداً
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # إضافة القيم الافتراضية
        cursor.execute('''
            INSERT OR IGNORE INTO bot_settings (setting_key, setting_value, updated_at) 
            VALUES ('bot_running', 'true', datetime('now'))
        ''')
        cursor.execute('''
            INSERT OR IGNORE INTO bot_settings (setting_key, setting_value, updated_at) 
            VALUES ('restart_at', 'null', datetime('now'))
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_button_path (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                button_path TEXT NOT NULL,
                button_names_ar TEXT NOT NULL,
                button_names_en TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_dynamic_buttons_parent 
            ON dynamic_buttons(parent_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_dynamic_buttons_enabled 
            ON dynamic_buttons(is_enabled)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_order_button_path_order 
            ON order_button_path(order_id)
        ''')
        
        if not self._has_root_buttons(cursor):
            self._insert_default_buttons(cursor)
        
        conn.commit()
        conn.close()
        logger.info("✅ تم تهيئة جداول الأزرار الديناميكية")
    
    def _has_root_buttons(self, cursor) -> bool:
        """التحقق من وجود أزرار جذرية"""
        cursor.execute("SELECT COUNT(*) FROM dynamic_buttons WHERE parent_id IS NULL")
        return cursor.fetchone()[0] > 0
    
    def _insert_default_buttons(self, cursor):
        """إدراج الأزرار الافتراضية (ستاتيك وسوكس)"""
        root_buttons = [
            ('static_proxy', '🌐 ستاتيك بروكسي', '🌐 Static Proxy', 'menu', True, False, 0, False, 1, 'اختر نوع الخدمة', 'Choose service type', 0, '🌐'),
            ('socks_proxy', '🧦 سوكس بروكسي', '🧦 SOCKS Proxy', 'menu', True, False, 0, False, 1, 'اختر الدولة', 'Choose country', 1, '🧦'),
        ]
        
        for btn in root_buttons:
            cursor.execute('''
                INSERT OR IGNORE INTO dynamic_buttons 
                (button_key, text_ar, text_en, button_type, is_enabled, is_service, price, ask_quantity, default_quantity, message_ar, message_en, order_index, icon)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', btn)
        
        cursor.execute("SELECT id FROM dynamic_buttons WHERE button_key = 'static_proxy'")
        static_id = cursor.fetchone()[0]
        
        static_services = [
            ('static_monthly_residential', '📍 ريزيدنتال شهري - $4', '📍 Monthly Residential - $4', 'menu', True, False, 4.0, False, 1, 'اختر الولاية', 'Choose state', 0, '📍'),
            ('static_weekly', '📅 أسبوعي - $2.5', '📅 Weekly - $2.5', 'menu', True, False, 2.5, False, 1, 'اختر الموقع', 'Choose location', 1, '📅'),
            ('static_daily', '📆 يومي - $0.25', '📆 Daily - $0.25', 'service', True, True, 0.25, True, 1, 'أدخل الكمية المطلوبة', 'Enter quantity', 2, '📆'),
            ('static_isp', '🏢 ISP - $6', '🏢 ISP - $6', 'menu', True, False, 6.0, False, 1, 'اختر المزود', 'Choose provider', 3, '🏢'),
        ]
        
        for btn in static_services:
            cursor.execute('''
                INSERT OR IGNORE INTO dynamic_buttons 
                (parent_id, button_key, text_ar, text_en, button_type, is_enabled, is_service, price, ask_quantity, default_quantity, message_ar, message_en, order_index, icon)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (static_id,) + btn)
        
        cursor.execute("SELECT id FROM dynamic_buttons WHERE button_key = 'static_monthly_residential'")
        monthly_res_id = cursor.fetchone()[0]
        
        us_states = [
            ('res_ny', '🗽 نيويورك', '🗽 New York', 'service', True, True, 4.0, True, 1, '', '', 0, '🗽'),
            ('res_va', '🏛️ فيرجينيا', '🏛️ Virginia', 'service', True, True, 4.0, True, 1, '', '', 1, '🏛️'),
            ('res_wa', '🌲 واشنطن', '🌲 Washington', 'service', True, True, 4.0, True, 1, '', '', 2, '🌲'),
            ('res_il', '🏙️ إلينوي', '🏙️ Illinois', 'service', True, True, 4.0, True, 1, '', '', 3, '🏙️'),
            ('res_tx', '⛺ تكساس', '⛺ Texas', 'service', True, True, 4.0, True, 1, '', '', 4, '⛺'),
            ('res_ca', '🌴 كاليفورنيا', '🌴 California', 'service', True, True, 4.0, True, 1, '', '', 5, '🌴'),
        ]
        
        for btn in us_states:
            cursor.execute('''
                INSERT OR IGNORE INTO dynamic_buttons 
                (parent_id, button_key, text_ar, text_en, button_type, is_enabled, is_service, price, ask_quantity, default_quantity, message_ar, message_en, order_index, icon)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (monthly_res_id,) + btn)
        
        cursor.execute("SELECT id FROM dynamic_buttons WHERE button_key = 'socks_proxy'")
        socks_id = cursor.fetchone()[0]
        
        socks_countries = [
            ('socks_us', '🇺🇸 الولايات المتحدة', '🇺🇸 United States', 'menu', True, False, 0, False, 1, 'اختر الولاية', 'Choose state', 0, '🇺🇸'),
            ('socks_uk', '🇬🇧 بريطانيا', '🇬🇧 United Kingdom', 'service', True, True, 1.5, True, 1, '', '', 1, '🇬🇧'),
            ('socks_de', '🇩🇪 ألمانيا', '🇩🇪 Germany', 'service', True, True, 1.5, True, 1, '', '', 2, '🇩🇪'),
            ('socks_fr', '🇫🇷 فرنسا', '🇫🇷 France', 'service', True, True, 1.5, True, 1, '', '', 3, '🇫🇷'),
            ('socks_ca', '🇨🇦 كندا', '🇨🇦 Canada', 'service', True, True, 1.5, True, 1, '', '', 4, '🇨🇦'),
        ]
        
        for btn in socks_countries:
            cursor.execute('''
                INSERT OR IGNORE INTO dynamic_buttons 
                (parent_id, button_key, text_ar, text_en, button_type, is_enabled, is_service, price, ask_quantity, default_quantity, message_ar, message_en, order_index, icon)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (socks_id,) + btn)
        
        cursor.execute("SELECT id FROM dynamic_buttons WHERE button_key = 'socks_us'")
        socks_us_id = cursor.fetchone()[0]
        
        us_socks_states = [
            ('socks_us_ny', '🗽 نيويورك', '🗽 New York', 'service', True, True, 1.5, True, 1, '', '', 0, '🗽'),
            ('socks_us_ca', '🌴 كاليفورنيا', '🌴 California', 'service', True, True, 1.5, True, 1, '', '', 1, '🌴'),
            ('socks_us_tx', '⛺ تكساس', '⛺ Texas', 'service', True, True, 1.5, True, 1, '', '', 2, '⛺'),
            ('socks_us_fl', '🌊 فلوريدا', '🌊 Florida', 'service', True, True, 1.5, True, 1, '', '', 3, '🌊'),
        ]
        
        for btn in us_socks_states:
            cursor.execute('''
                INSERT OR IGNORE INTO dynamic_buttons 
                (parent_id, button_key, text_ar, text_en, button_type, is_enabled, is_service, price, ask_quantity, default_quantity, message_ar, message_en, order_index, icon)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (socks_us_id,) + btn)
        
        logger.info("✅ تم إدراج الأزرار الافتراضية")
    
    def get_root_buttons(self, language: str = 'ar', enabled_only: bool = True) -> List[Dict]:
        """الحصول على الأزرار الجذرية (المستوى الأول)"""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM dynamic_buttons WHERE parent_id IS NULL"
        if enabled_only:
            query += " AND is_enabled = 1"
        query += " ORDER BY order_index"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_dict(row, language) for row in rows]
    
    def get_children(self, parent_id: int, language: str = 'ar', enabled_only: bool = True) -> List[Dict]:
        """الحصول على الأزرار الفرعية"""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM dynamic_buttons WHERE parent_id = ?"
        if enabled_only:
            query += " AND is_enabled = 1"
        query += " ORDER BY order_index"
        
        cursor.execute(query, (parent_id,))
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_dict(row, language) for row in rows]
    
    def get_button_by_id(self, button_id: int, language: str = 'ar') -> Optional[Dict]:
        """الحصول على زر بالمعرف"""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM dynamic_buttons WHERE id = ?", (button_id,))
        row = cursor.fetchone()
        conn.close()
        
        return self._row_to_dict(row, language) if row else None
    
    def get_button_by_key(self, button_key: str, language: str = 'ar') -> Optional[Dict]:
        """الحصول على زر بالمفتاح"""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM dynamic_buttons WHERE button_key = ?", (button_key,))
        row = cursor.fetchone()
        conn.close()
        
        return self._row_to_dict(row, language) if row else None
    
    def get_full_tree(self, language: str = 'ar', enabled_only: bool = False) -> List[Dict]:
        """الحصول على شجرة الأزرار الكاملة"""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM dynamic_buttons"
        if enabled_only:
            query += " WHERE is_enabled = 1"
        query += " ORDER BY parent_id NULLS FIRST, order_index"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        all_buttons = [self._row_to_dict(row, language) for row in rows]
        return self._build_tree(all_buttons)
    
    def _build_tree(self, buttons: List[Dict], parent_id: Optional[int] = None) -> List[Dict]:
        """بناء شجرة من قائمة مسطحة"""
        tree = []
        for btn in buttons:
            if btn.get('parent_id') == parent_id:
                children = self._build_tree(buttons, btn['id'])
                if children:
                    btn['children'] = children
                tree.append(btn)
        return tree
    
    def _row_to_dict(self, row: sqlite3.Row, language: str = 'ar') -> Dict:
        """تحويل صف قاعدة البيانات إلى قاموس"""
        # الحصول على back_behavior بشكل آمن (للتوافق مع قواعد البيانات القديمة)
        try:
            back_behavior = row['back_behavior'] or 'step'
        except (IndexError, KeyError):
            back_behavior = 'step'
        
        # الحصول على show_back_on_quantity و show_cancel_on_quantity بشكل آمن
        try:
            show_back_on_quantity = row['show_back_on_quantity']
            show_back_on_quantity = show_back_on_quantity != 0 if show_back_on_quantity is not None else True
        except (IndexError, KeyError):
            show_back_on_quantity = True
        
        try:
            show_cancel_on_quantity = row['show_cancel_on_quantity']
            show_cancel_on_quantity = show_cancel_on_quantity != 0 if show_cancel_on_quantity is not None else True
        except (IndexError, KeyError):
            show_cancel_on_quantity = True
        
        try:
            button_size = row['button_size'] or 'large'
        except (IndexError, KeyError):
            button_size = 'large'
        
        try:
            is_hidden = bool(row['is_hidden'])
        except (IndexError, KeyError):
            is_hidden = False
        
        try:
            disabled_message = row['disabled_message'] or 'هذه الخدمة متوقفة مؤقتاً'
        except (IndexError, KeyError):
            disabled_message = 'هذه الخدمة متوقفة مؤقتاً'
        
        return {
            'id': row['id'],
            'parent_id': row['parent_id'],
            'button_key': row['button_key'],
            'text': row['text_ar'] if language == 'ar' else row['text_en'],
            'text_ar': row['text_ar'],
            'text_en': row['text_en'],
            'button_type': row['button_type'],
            'is_enabled': bool(row['is_enabled']),
            'is_hidden': is_hidden,
            'disabled_message': disabled_message,
            'is_service': bool(row['is_service']),
            'price': row['price'],
            'ask_quantity': bool(row['ask_quantity']),
            'default_quantity': row['default_quantity'],
            'show_back_on_quantity': show_back_on_quantity,
            'show_cancel_on_quantity': show_cancel_on_quantity,
            'message': row['message_ar'] if language == 'ar' else row['message_en'],
            'message_ar': row['message_ar'],
            'message_en': row['message_en'],
            'order_index': row['order_index'],
            'icon': row['icon'],
            'callback_data': row['callback_data'] or f"dyn_{row['button_key']}",
            'back_behavior': back_behavior,
            'button_size': button_size
        }
    
    def add_button(self, data: Dict) -> int:
        """إضافة زر جديد"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO dynamic_buttons 
            (parent_id, button_key, text_ar, text_en, button_type, is_enabled, is_hidden, is_service, 
             price, ask_quantity, default_quantity, show_back_on_quantity, show_cancel_on_quantity,
             message_ar, message_en, order_index, icon, callback_data, back_behavior, disabled_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('parent_id'),
            data['button_key'],
            data['text_ar'],
            data['text_en'],
            data.get('button_type', 'menu'),
            data.get('is_enabled', True),
            data.get('is_hidden', False),
            data.get('is_service', False),
            data.get('price', 0.0),
            data.get('ask_quantity', False),
            data.get('default_quantity', 1),
            data.get('show_back_on_quantity', True),
            data.get('show_cancel_on_quantity', True),
            data.get('message_ar', ''),
            data.get('message_en', ''),
            data.get('order_index', 0),
            data.get('icon', ''),
            data.get('callback_data', ''),
            data.get('back_behavior', 'step'),
            data.get('disabled_message', 'هذه الخدمة متوقفة مؤقتاً')
        ))
        
        button_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"✅ تم إضافة زر جديد: {data['button_key']} (ID: {button_id})")
        return button_id
    
    def update_button(self, button_id: int, data: Dict) -> bool:
        """تحديث زر موجود"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        update_fields = []
        values = []
        
        field_mapping = {
            'parent_id': 'parent_id',
            'text_ar': 'text_ar',
            'text_en': 'text_en',
            'button_type': 'button_type',
            'is_enabled': 'is_enabled',
            'is_hidden': 'is_hidden',
            'is_service': 'is_service',
            'price': 'price',
            'ask_quantity': 'ask_quantity',
            'default_quantity': 'default_quantity',
            'show_back_on_quantity': 'show_back_on_quantity',
            'show_cancel_on_quantity': 'show_cancel_on_quantity',
            'message_ar': 'message_ar',
            'message_en': 'message_en',
            'order_index': 'order_index',
            'icon': 'icon',
            'callback_data': 'callback_data',
            'back_behavior': 'back_behavior',
            'disabled_message': 'disabled_message'
        }
        
        for key, field in field_mapping.items():
            if key in data:
                update_fields.append(f"{field} = ?")
                values.append(data[key])
        
        if not update_fields:
            conn.close()
            return False
        
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(button_id)
        
        query = f"UPDATE dynamic_buttons SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(query, values)
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if success:
            logger.info(f"✅ تم تحديث الزر ID: {button_id}")
        
        return success
    
    def delete_button(self, button_id: int) -> bool:
        """حذف زر وجميع أبنائه"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM dynamic_buttons WHERE id = ?", (button_id,))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if success:
            logger.info(f"✅ تم حذف الزر ID: {button_id}")
        
        return success
    
    def toggle_button(self, button_id: int) -> bool:
        """تبديل حالة الزر (تفعيل/إيقاف)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE dynamic_buttons 
            SET is_enabled = NOT is_enabled, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (button_id,))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def reorder_buttons(self, button_ids: List[int]) -> bool:
        """إعادة ترتيب الأزرار"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for index, button_id in enumerate(button_ids):
            cursor.execute(
                "UPDATE dynamic_buttons SET order_index = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (index, button_id)
            )
        
        conn.commit()
        conn.close()
        
        return True
    
    def save_order_path(self, order_id: str, user_id: int, button_ids: List[int]) -> bool:
        """حفظ مسار الأزرار للطلب"""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        button_names_ar = []
        button_names_en = []
        
        for btn_id in button_ids:
            cursor.execute("SELECT text_ar, text_en FROM dynamic_buttons WHERE id = ?", (btn_id,))
            row = cursor.fetchone()
            if row:
                button_names_ar.append(row['text_ar'])
                button_names_en.append(row['text_en'])
        
        cursor.execute('''
            INSERT INTO order_button_path (order_id, user_id, button_path, button_names_ar, button_names_en)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            order_id,
            user_id,
            json.dumps(button_ids),
            ' → '.join(button_names_ar),
            ' → '.join(button_names_en)
        ))
        
        conn.commit()
        conn.close()
        
        return True
    
    def get_order_path(self, order_id: str, language: str = 'ar') -> Optional[str]:
        """الحصول على مسار الطلب"""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM order_button_path WHERE order_id = ?", (order_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return row['button_names_ar'] if language == 'ar' else row['button_names_en']
        return None
    
    def get_button_path(self, button_id: int, language: str = 'ar') -> List[Dict]:
        """الحصول على المسار من الجذر إلى الزر المحدد"""
        path = []
        current_id = button_id
        
        while current_id:
            button = self.get_button_by_id(current_id, language)
            if button:
                path.insert(0, button)
                current_id = button.get('parent_id')
            else:
                break
        
        return path
    
    def update_price(self, button_id: int, price: float) -> bool:
        """تحديث سعر الزر"""
        return self.update_button(button_id, {'price': price})
    
    def get_all_services(self, language: str = 'ar', enabled_only: bool = True) -> List[Dict]:
        """الحصول على جميع الخدمات (الأزرار التي is_service=True)"""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM dynamic_buttons WHERE is_service = 1"
        if enabled_only:
            query += " AND is_enabled = 1"
        query += " ORDER BY order_index"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        services = []
        for row in rows:
            service = self._row_to_dict(row, language)
            service['path'] = self.get_button_path(row['id'], language)
            services.append(service)
        
        return services
    
    def export_tree(self) -> str:
        """تصدير شجرة الأزرار كـ JSON"""
        tree = self.get_full_tree('ar', enabled_only=False)
        return json.dumps(tree, ensure_ascii=False, indent=2)
    
    def import_tree(self, json_data: str) -> bool:
        """استيراد شجرة الأزرار من JSON"""
        try:
            tree = json.loads(json_data)
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM dynamic_buttons")
            
            def insert_button(button: Dict, parent_id: Optional[int] = None):
                cursor.execute('''
                    INSERT INTO dynamic_buttons 
                    (parent_id, button_key, text_ar, text_en, button_type, is_enabled, is_service, 
                     price, ask_quantity, default_quantity, show_back_on_quantity, show_cancel_on_quantity,
                     message_ar, message_en, order_index, icon, callback_data, back_behavior)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    parent_id,
                    button['button_key'],
                    button['text_ar'],
                    button['text_en'],
                    button.get('button_type', 'menu'),
                    button.get('is_enabled', True),
                    button.get('is_service', False),
                    button.get('price', 0.0),
                    button.get('ask_quantity', False),
                    button.get('default_quantity', 1),
                    button.get('show_back_on_quantity', True),
                    button.get('show_cancel_on_quantity', True),
                    button.get('message_ar', ''),
                    button.get('message_en', ''),
                    button.get('order_index', 0),
                    button.get('icon', ''),
                    button.get('callback_data', ''),
                    button.get('back_behavior', 'step')
                ))
                
                new_id = cursor.lastrowid
                
                for child in button.get('children', []):
                    insert_button(child, new_id)
            
            for button in tree:
                insert_button(button)
            
            conn.commit()
            conn.close()
            
            logger.info("✅ تم استيراد شجرة الأزرار بنجاح")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في استيراد شجرة الأزرار: {e}")
            return False


dynamic_buttons_manager = DynamicButtonsManager()
