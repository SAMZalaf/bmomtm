#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================
خادم واجهة الويب - Python/Flask
============================================
بديل لخادم Node.js - يخدم نفس الواجهة
============================================
"""

import os
import sys
import json
import sqlite3
import secrets
import logging
import time
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory, send_file

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='dist/public', static_url_path='')

BOT_DIR = os.environ.get('BOT_DIR', str(Path(__file__).parent.parent))
DB_PATH = os.path.join(BOT_DIR, 'proxy_bot.db')

active_tokens = {}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_admin_password():
    """قراءة كلمة مرور الأدمن من قاعدة البيانات"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'admin_password'")
        row = cursor.fetchone()
        conn.close()
        if row:
            return row['value']
    except Exception as e:
        logger.warning(f"Could not read admin password from database: {e}")
    return os.environ.get('ADMIN_PASSWORD', 'sohilSOHIL')

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dynamic_buttons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER DEFAULT NULL,
            button_key TEXT UNIQUE NOT NULL,
            text_ar TEXT NOT NULL,
            text_en TEXT NOT NULL,
            button_type TEXT DEFAULT 'menu',
            is_enabled INTEGER DEFAULT 1,
            is_service INTEGER DEFAULT 0,
            price REAL DEFAULT 0.0,
            ask_quantity INTEGER DEFAULT 0,
            default_quantity INTEGER DEFAULT 1,
            show_back_on_quantity INTEGER DEFAULT 1,
            show_cancel_on_quantity INTEGER DEFAULT 1,
            message_ar TEXT DEFAULT '',
            message_en TEXT DEFAULT '',
            order_index INTEGER DEFAULT 0,
            icon TEXT DEFAULT '',
            callback_data TEXT DEFAULT '',
            back_behavior TEXT DEFAULT 'step',
            button_size TEXT DEFAULT 'large',
            is_hidden INTEGER DEFAULT 0,
            disabled_message TEXT DEFAULT 'هذه الخدمة متوقفة مؤقتاً',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_id) REFERENCES dynamic_buttons(id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dashboard_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            entity_type TEXT DEFAULT 'button',
            entity_id INTEGER DEFAULT NULL,
            entity_name TEXT DEFAULT '',
            details TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # إضافة الأعمدة المفقودة للجداول القديمة (migration)
    try:
        cursor.execute("ALTER TABLE activity_logs ADD COLUMN entity_type TEXT DEFAULT 'button'")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE activity_logs ADD COLUMN entity_id INTEGER DEFAULT NULL")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE activity_logs ADD COLUMN entity_name TEXT DEFAULT ''")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE activity_logs ADD COLUMN details TEXT DEFAULT ''")
    except:
        pass
    
    conn.commit()
    conn.close()

def safe_get(row, key, default=None):
    """الحصول على قيمة من sqlite3.Row بشكل آمن"""
    try:
        value = row[key]
        return value if value is not None else default
    except (KeyError, IndexError):
        return default

def row_to_button(row):
    if row is None:
        return None
    return {
        'id': row['id'],
        'parentId': row['parent_id'],
        'buttonKey': row['button_key'],
        'textAr': row['text_ar'],
        'textEn': row['text_en'],
        'buttonType': row['button_type'] or 'menu',
        'isEnabled': bool(row['is_enabled']),
        'isHidden': bool(safe_get(row, 'is_hidden', 0)),
        'disabledMessage': safe_get(row, 'disabled_message', 'هذه الخدمة متوقفة مؤقتاً'),
        'isService': bool(row['is_service']),
        'price': row['price'] or 0,
        'askQuantity': bool(row['ask_quantity']),
        'defaultQuantity': row['default_quantity'] or 1,
        'showBackOnQuantity': safe_get(row, 'show_back_on_quantity', 1) != 0,
        'showCancelOnQuantity': safe_get(row, 'show_cancel_on_quantity', 1) != 0,
        'messageAr': row['message_ar'] or '',
        'messageEn': row['message_en'] or '',
        'orderIndex': row['order_index'] or 0,
        'icon': row['icon'] or '',
        'callbackData': row['callback_data'] or f"dyn_{row['button_key']}",
        'backBehavior': safe_get(row, 'back_behavior', 'step'),
        'buttonSize': safe_get(row, 'button_size', 'large'),
        'createdAt': row['created_at'],
        'updatedAt': row['updated_at'],
    }

def get_all_buttons():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM dynamic_buttons ORDER BY order_index")
    rows = cursor.fetchall()
    conn.close()
    return [row_to_button(row) for row in rows]

def get_button_tree():
    all_buttons = get_all_buttons()
    
    def build_tree(parent_id):
        children = [b for b in all_buttons if b['parentId'] == parent_id]
        children.sort(key=lambda x: x['orderIndex'])
        for child in children:
            child['children'] = build_tree(child['id'])
        return children
    
    return build_tree(None)

def log_activity(action, entity_type='button', entity_id=None, entity_name='', details=''):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO activity_logs (action, entity_type, entity_id, entity_name, details)
        VALUES (?, ?, ?, ?, ?)
    ''', (action, entity_type, entity_id, entity_name, details))
    conn.commit()
    conn.close()


@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(os.path.join(app.static_folder, 'assets'), filename)

@app.route('/<path:path>')
def serve_static(path):
    file_path = os.path.join(app.static_folder, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        password = data.get('password')
        
        if not password:
            return jsonify({'success': False, 'message': 'كلمة المرور مطلوبة'}), 400
        
        admin_password = get_admin_password()
        if password == admin_password:
            token = secrets.token_hex(32)
            active_tokens[token] = datetime.now() + timedelta(hours=24)
            return jsonify({'success': True, 'token': token})
        else:
            return jsonify({'success': False, 'message': 'كلمة المرور غير صحيحة'}), 401
    except Exception as e:
        logger.error(f"Error during login: {e}")
        return jsonify({'success': False, 'message': 'حدث خطأ في الخادم'}), 500

@app.route('/api/auth/verify', methods=['POST'])
def verify_token():
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'valid': False}), 400
        
        if token in active_tokens and active_tokens[token] > datetime.now():
            return jsonify({'valid': True})
        return jsonify({'valid': False})
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        return jsonify({'valid': False}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    try:
        data = request.get_json()
        token = data.get('token')
        
        if token and token in active_tokens:
            del active_tokens[token]
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        return jsonify({'success': False}), 500


@app.route('/api/auth/password', methods=['POST'])
def update_password():
    try:
        data = request.get_json()
        new_password = data.get('newPassword')
        
        if not new_password or len(new_password) < 6:
            return jsonify({'success': False, 'message': 'كلمة المرور يجب أن تكون 6 أحرف على الأقل'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('admin_password', new_password))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'تم تغيير كلمة المرور بنجاح'})
    except Exception as e:
        logger.error(f"Error updating password: {e}")
        return jsonify({'success': False, 'message': 'حدث خطأ في تغيير كلمة المرور'}), 500


@app.route('/api/buttons/tree', methods=['GET'])
def get_buttons_tree():
    try:
        tree = get_button_tree()
        return jsonify(tree)
    except Exception as e:
        logger.error(f"Error fetching button tree: {e}")
        return jsonify({'error': 'Failed to fetch buttons'}), 500

@app.route('/api/buttons', methods=['GET'])
def get_buttons():
    try:
        buttons = get_all_buttons()
        return jsonify(buttons)
    except Exception as e:
        logger.error(f"Error fetching buttons: {e}")
        return jsonify({'error': 'Failed to fetch buttons'}), 500

@app.route('/api/buttons/<int:button_id>', methods=['GET'])
def get_button(button_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dynamic_buttons WHERE id = ?", (button_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': 'Button not found'}), 404
        
        return jsonify(row_to_button(row))
    except Exception as e:
        logger.error(f"Error fetching button: {e}")
        return jsonify({'error': 'Failed to fetch button'}), 500

@app.route('/api/buttons', methods=['POST'])
def create_button():
    try:
        data = request.get_json()
        conn = get_db()
        cursor = conn.cursor()
        
        parent_id = data.get('parentId')
        if parent_id is None:
            cursor.execute("SELECT MAX(order_index) as max_order FROM dynamic_buttons WHERE parent_id IS NULL")
        else:
            cursor.execute("SELECT MAX(order_index) as max_order FROM dynamic_buttons WHERE parent_id = ?", (parent_id,))
        
        result = cursor.fetchone()
        order_index = (result['max_order'] or -1) + 1
        
        cursor.execute('''
            INSERT INTO dynamic_buttons 
            (parent_id, button_key, text_ar, text_en, button_type, is_enabled, is_hidden, disabled_message,
             is_service, price, ask_quantity, default_quantity, show_back_on_quantity, show_cancel_on_quantity,
             message_ar, message_en, order_index, icon, callback_data, back_behavior, button_size)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            parent_id,
            data.get('buttonKey'),
            data.get('textAr'),
            data.get('textEn'),
            data.get('buttonType', 'menu'),
            1 if data.get('isEnabled', True) else 0,
            1 if data.get('isHidden', False) else 0,
            data.get('disabledMessage', 'هذه الخدمة متوقفة مؤقتاً'),
            1 if data.get('isService', False) else 0,
            data.get('price', 0),
            1 if data.get('askQuantity', False) else 0,
            data.get('defaultQuantity', 1),
            1 if data.get('showBackOnQuantity', True) else 0,
            1 if data.get('showCancelOnQuantity', True) else 0,
            data.get('messageAr', ''),
            data.get('messageEn', ''),
            order_index,
            data.get('icon', ''),
            'temp_callback',
            data.get('backBehavior', 'step'),
            data.get('buttonSize', 'large')
        ))
        
        new_id = cursor.lastrowid
        cursor.execute("UPDATE dynamic_buttons SET callback_data = ? WHERE id = ?", (f"dyn_{new_id}", new_id))
        conn.commit()
        
        cursor.execute("SELECT * FROM dynamic_buttons WHERE id = ?", (new_id,))
        row = cursor.fetchone()
        conn.close()
        
        button = row_to_button(row)
        log_activity('button_created', 'button', button['id'], button['textAr'], 
                    f"Button \"{button['textAr']}\" ({button['buttonKey']}) created")
        
        return jsonify(button), 201
    except Exception as e:
        logger.error(f"Error creating button: {e}")
        return jsonify({'error': 'Failed to create button'}), 500

@app.route('/api/buttons/batch', methods=['POST'])
def create_buttons_batch():
    """إنشاء عدة أزرار دفعة واحدة (للنسخ والتكرار)"""
    try:
        data = request.get_json()
        buttons_data = data.get('buttons', [])
        
        if not isinstance(buttons_data, list) or len(buttons_data) == 0:
            return jsonify({'error': 'Invalid buttons data'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        created_buttons = []
        
        for btn_data in buttons_data:
            parent_id = btn_data.get('parentId')
            if parent_id is None:
                cursor.execute("SELECT MAX(order_index) as max_order FROM dynamic_buttons WHERE parent_id IS NULL")
            else:
                cursor.execute("SELECT MAX(order_index) as max_order FROM dynamic_buttons WHERE parent_id = ?", (parent_id,))
            
            result = cursor.fetchone()
            order_index = (result['max_order'] or -1) + 1
            
            cursor.execute('''
                INSERT INTO dynamic_buttons 
                (parent_id, button_key, text_ar, text_en, button_type, is_enabled, is_hidden, disabled_message,
                 is_service, price, ask_quantity, default_quantity, show_back_on_quantity, show_cancel_on_quantity,
                 message_ar, message_en, order_index, icon, callback_data, back_behavior, button_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                parent_id,
                btn_data.get('buttonKey'),
                btn_data.get('textAr'),
                btn_data.get('textEn'),
                btn_data.get('buttonType', 'menu'),
                1 if btn_data.get('isEnabled', True) else 0,
                1 if btn_data.get('isHidden', False) else 0,
                btn_data.get('disabledMessage', 'هذه الخدمة متوقفة مؤقتاً'),
                1 if btn_data.get('isService', False) else 0,
                btn_data.get('price', 0),
                1 if btn_data.get('askQuantity', False) else 0,
                btn_data.get('defaultQuantity', 1),
                1 if btn_data.get('showBackOnQuantity', True) else 0,
                1 if btn_data.get('showCancelOnQuantity', True) else 0,
                btn_data.get('messageAr', ''),
                btn_data.get('messageEn', ''),
                order_index,
                btn_data.get('icon', ''),
                'temp_callback',
                btn_data.get('backBehavior', 'step'),
                btn_data.get('buttonSize', 'large')
            ))
            
            new_id = cursor.lastrowid
            cursor.execute("UPDATE dynamic_buttons SET callback_data = ? WHERE id = ?", (f"dyn_{new_id}", new_id))
            
            cursor.execute("SELECT * FROM dynamic_buttons WHERE id = ?", (new_id,))
            row = cursor.fetchone()
            created_buttons.append(row_to_button(row))
        
        conn.commit()
        conn.close()
        
        log_activity('buttons_batch_created', 'system', None, 'Batch Create',
                    f"{len(created_buttons)} buttons created in batch")
        
        return jsonify({'success': True, 'buttons': created_buttons}), 201
    except Exception as e:
        logger.error(f"Error batch creating buttons: {e}")
        return jsonify({'error': 'Failed to batch create buttons'}), 500

@app.route('/api/buttons/copy-with-children', methods=['POST'])
def copy_button_with_children():
    """نسخ زر مع جميع أبنائه بشكل تكراري"""
    try:
        data = request.get_json()
        source_button_id = data.get('sourceButtonId')
        copy_count = data.get('copyCount', 1)
        copy_names = data.get('copyNames', [])
        target_parent_id = data.get('targetParentId')
        copy_children = data.get('copyChildren', False)
        insert_inside = data.get('insertInside', False)
        has_target_parent = 'targetParentId' in data
        
        # خيارات تغيير السعر
        override_service_price = data.get('overrideServicePrice', False)
        new_service_price = data.get('newServicePrice')
        
        logger.info(f"[COPY] overrideServicePrice={override_service_price}, newServicePrice={new_service_price}")
        
        if not isinstance(source_button_id, int) or not isinstance(copy_count, int):
            return jsonify({'error': 'Invalid parameters'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM dynamic_buttons WHERE id = ?", (source_button_id,))
        source_row = cursor.fetchone()
        if not source_row:
            conn.close()
            return jsonify({'error': 'Source button not found'}), 404
        
        source_button = row_to_button(source_row)
        created_buttons = []
        
        def get_children_recursive(parent_id):
            """جلب جميع الأبناء بشكل تكراري"""
            cursor.execute("SELECT * FROM dynamic_buttons WHERE parent_id = ? ORDER BY order_index", (parent_id,))
            children = []
            for row in cursor.fetchall():
                child = row_to_button(row)
                child['children'] = get_children_recursive(child['id'])
                children.append(child)
            return children
        
        def copy_button_recursive(button, new_parent_id, custom_data=None):
            """نسخ زر مع أبنائه بشكل تكراري"""
            cursor.execute("SELECT MAX(order_index) as max_order FROM dynamic_buttons WHERE parent_id IS ?" if new_parent_id is None else "SELECT MAX(order_index) as max_order FROM dynamic_buttons WHERE parent_id = ?", 
                          (new_parent_id,) if new_parent_id is not None else (None,))
            result = cursor.fetchone()
            order_index = (result['max_order'] or -1) + 1
            
            button_key = custom_data.get('buttonKey') if custom_data else f"{button['buttonKey']}_copy_{int(time.time() * 1000)}"
            text_ar = custom_data.get('textAr') if custom_data else button['textAr']
            text_en = custom_data.get('textEn') if custom_data else button['textEn']
            
            # تحديد السعر: إذا كان تغيير السعر مفعلاً والعنصر خدمة مدفوعة، نستخدم السعر الجديد
            is_service = button.get('isService', False)
            original_price = button.get('price', 0)
            if override_service_price and is_service and new_service_price is not None:
                final_price = new_service_price
                logger.info(f"[COPY] Applying new price {final_price} to service button: {button.get('buttonKey')}")
            else:
                final_price = original_price
            
            cursor.execute('''
                INSERT INTO dynamic_buttons 
                (parent_id, button_key, text_ar, text_en, button_type, is_enabled, is_hidden, disabled_message,
                 is_service, price, ask_quantity, default_quantity, show_back_on_quantity, show_cancel_on_quantity,
                 message_ar, message_en, order_index, icon, callback_data, back_behavior, button_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                new_parent_id,
                button_key,
                text_ar,
                text_en,
                button.get('buttonType', 'menu'),
                1 if button.get('isEnabled', True) else 0,
                1 if button.get('isHidden', False) else 0,
                button.get('disabledMessage', 'هذه الخدمة متوقفة مؤقتاً'),
                1 if is_service else 0,
                final_price,
                1 if button.get('askQuantity', False) else 0,
                button.get('defaultQuantity', 1),
                1 if button.get('showBackOnQuantity', True) else 0,
                1 if button.get('showCancelOnQuantity', True) else 0,
                button.get('messageAr', ''),
                button.get('messageEn', ''),
                order_index,
                button.get('icon', ''),
                'temp_callback',
                button.get('backBehavior', 'step'),
                button.get('buttonSize', 'large')
            ))
            
            new_id = cursor.lastrowid
            cursor.execute("UPDATE dynamic_buttons SET callback_data = ? WHERE id = ?", (f"dyn_{new_id}", new_id))
            
            cursor.execute("SELECT * FROM dynamic_buttons WHERE id = ?", (new_id,))
            new_row = cursor.fetchone()
            new_button = row_to_button(new_row)
            
            if copy_children and button.get('children'):
                for child in button['children']:
                    copy_button_recursive(child, new_id)
            
            return new_button
        
        if copy_children:
            source_button['children'] = get_children_recursive(source_button_id)
        
        # تحديد الموقع الهدف:
        # - إذا تم تحديد targetParentId (حتى لو كان null)، نستخدمه
        # - إذا لم يتم تحديد targetParentId في الطلب، نستخدم المسار الأصلي
        if has_target_parent:
            actual_parent_id = target_parent_id
        else:
            actual_parent_id = source_button.get('parentId')
        
        for i in range(copy_count):
            custom_data = copy_names[i] if i < len(copy_names) else None
            new_button = copy_button_recursive(source_button, actual_parent_id, custom_data)
            created_buttons.append(new_button)
        
        conn.commit()
        conn.close()
        
        children_text = ' with children' if copy_children else ''
        log_activity('buttons_batch_created', 'system', None, 'Copy with Children',
                    f"{len(created_buttons)} buttons copied{children_text}")
        
        return jsonify({'success': True, 'buttons': created_buttons}), 201
    except Exception as e:
        logger.error(f"Error copying buttons with children: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to copy buttons'}), 500

@app.route('/api/buttons/<int:button_id>', methods=['PATCH'])
def update_button(button_id):
    try:
        data = request.get_json()
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM dynamic_buttons WHERE id = ?", (button_id,))
        old_row = cursor.fetchone()
        if not old_row:
            conn.close()
            return jsonify({'error': 'Button not found'}), 404
        
        field_map = {
            'parentId': 'parent_id',
            'buttonKey': 'button_key',
            'textAr': 'text_ar',
            'textEn': 'text_en',
            'buttonType': 'button_type',
            'isEnabled': 'is_enabled',
            'isHidden': 'is_hidden',
            'disabledMessage': 'disabled_message',
            'isService': 'is_service',
            'price': 'price',
            'askQuantity': 'ask_quantity',
            'defaultQuantity': 'default_quantity',
            'showBackOnQuantity': 'show_back_on_quantity',
            'showCancelOnQuantity': 'show_cancel_on_quantity',
            'messageAr': 'message_ar',
            'messageEn': 'message_en',
            'orderIndex': 'order_index',
            'icon': 'icon',
            'callbackData': 'callback_data',
            'backBehavior': 'back_behavior',
            'buttonSize': 'button_size',
        }
        
        updates = []
        values = []
        for key, db_field in field_map.items():
            if key in data:
                value = data[key]
                if key in ['isEnabled', 'isHidden', 'isService', 'askQuantity', 'showBackOnQuantity', 'showCancelOnQuantity']:
                    value = 1 if value else 0
                updates.append(f"{db_field} = ?")
                values.append(value)
        
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            values.append(button_id)
            query = f"UPDATE dynamic_buttons SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
        
        cursor.execute("SELECT * FROM dynamic_buttons WHERE id = ?", (button_id,))
        row = cursor.fetchone()
        conn.close()
        
        button = row_to_button(row)
        
        if 'isEnabled' in data:
            action = 'button_enabled' if data['isEnabled'] else 'button_disabled'
            log_activity(action, 'button', button['id'], button['textAr'],
                        f"Button \"{button['textAr']}\" {'enabled' if data['isEnabled'] else 'disabled'}")
        else:
            log_activity('button_updated', 'button', button['id'], button['textAr'],
                        f"Button \"{button['textAr']}\" updated")
        
        return jsonify(button)
    except Exception as e:
        logger.error(f"Error updating button: {e}")
        return jsonify({'error': 'Failed to update button'}), 500

@app.route('/api/buttons/<int:button_id>', methods=['DELETE'])
def delete_button(button_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM dynamic_buttons WHERE id = ?", (button_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({'error': 'Button not found'}), 404
        
        button = row_to_button(row)
        
        cursor.execute("DELETE FROM dynamic_buttons WHERE id = ?", (button_id,))
        conn.commit()
        conn.close()
        
        log_activity('button_deleted', 'button', button_id, button['textAr'],
                    f"Button \"{button['textAr']}\" ({button['buttonKey']}) deleted")
        
        return '', 204
    except Exception as e:
        logger.error(f"Error deleting button: {e}")
        return jsonify({'error': 'Failed to delete button'}), 500

@app.route('/api/buttons/import', methods=['POST'])
def import_buttons():
    try:
        data = request.get_json()
        buttons = data.get('buttons', [])
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM dynamic_buttons")
        
        def insert_recursive(items, parent_id):
            for item in items:
                cursor.execute('''
                    INSERT INTO dynamic_buttons 
                    (parent_id, button_key, text_ar, text_en, button_type, is_enabled, is_service, 
                     price, ask_quantity, default_quantity, show_back_on_quantity, show_cancel_on_quantity,
                     message_ar, message_en, order_index, icon, callback_data, back_behavior)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    parent_id,
                    item.get('buttonKey'),
                    item.get('textAr'),
                    item.get('textEn'),
                    item.get('buttonType', 'menu'),
                    1 if item.get('isEnabled', True) else 0,
                    1 if item.get('isService', False) else 0,
                    item.get('price', 0),
                    1 if item.get('askQuantity', False) else 0,
                    item.get('defaultQuantity', 1),
                    1 if item.get('showBackOnQuantity', True) else 0,
                    1 if item.get('showCancelOnQuantity', True) else 0,
                    item.get('messageAr', ''),
                    item.get('messageEn', ''),
                    item.get('orderIndex', 0),
                    item.get('icon', ''),
                    'temp_callback',
                    item.get('backBehavior', 'step')
                ))
                new_id = cursor.lastrowid
                cursor.execute("UPDATE dynamic_buttons SET callback_data = ? WHERE id = ?", (f"dyn_{new_id}", new_id))
                
                children = item.get('children', [])
                if children:
                    insert_recursive(children, new_id)
        
        insert_recursive(buttons, None)
        conn.commit()
        conn.close()
        
        log_activity('buttons_imported', 'system', None, 'Buttons Import', f"{len(buttons)} root buttons imported")
        
        return jsonify({'success': True, 'message': 'Buttons imported successfully'})
    except Exception as e:
        logger.error(f"Error importing buttons: {e}")
        return jsonify({'error': 'Failed to import buttons'}), 500

@app.route('/api/buttons/reset', methods=['POST'])
def reset_buttons():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM dynamic_buttons")
        conn.commit()
        conn.close()
        
        log_activity('buttons_reset', 'system', None, 'Buttons Reset', 'All buttons reset to default values')
        
        return jsonify({'success': True, 'message': 'Buttons reset to default'})
    except Exception as e:
        logger.error(f"Error resetting buttons: {e}")
        return jsonify({'error': 'Failed to reset buttons'}), 500

@app.route('/api/buttons/reorder', methods=['POST'])
def reorder_buttons():
    try:
        data = request.get_json()
        button_id = data.get('buttonId')
        target_id = data.get('targetId')
        position = data.get('position')
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM dynamic_buttons WHERE id = ?", (button_id,))
        button = cursor.fetchone()
        cursor.execute("SELECT * FROM dynamic_buttons WHERE id = ?", (target_id,))
        target = cursor.fetchone()
        
        if not button or not target:
            conn.close()
            return jsonify({'error': 'Button not found'}), 404
        
        if position == 'inside':
            cursor.execute("SELECT MAX(order_index) as max_order FROM dynamic_buttons WHERE parent_id = ?", (target_id,))
            result = cursor.fetchone()
            new_order = (result['max_order'] or -1) + 1
            cursor.execute("UPDATE dynamic_buttons SET parent_id = ?, order_index = ? WHERE id = ?",
                          (target_id, new_order, button_id))
        else:
            new_parent_id = target['parent_id']
            target_order = target['order_index']
            
            if position == 'before':
                cursor.execute("UPDATE dynamic_buttons SET order_index = order_index + 1 WHERE parent_id IS ? AND order_index >= ?",
                              (new_parent_id, target_order))
                cursor.execute("UPDATE dynamic_buttons SET parent_id = ?, order_index = ? WHERE id = ?",
                              (new_parent_id, target_order, button_id))
            else:
                cursor.execute("UPDATE dynamic_buttons SET order_index = order_index + 1 WHERE parent_id IS ? AND order_index > ?",
                              (new_parent_id, target_order))
                cursor.execute("UPDATE dynamic_buttons SET parent_id = ?, order_index = ? WHERE id = ?",
                              (new_parent_id, target_order + 1, button_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Button reordered successfully'})
    except Exception as e:
        logger.error(f"Error reordering buttons: {e}")
        return jsonify({'error': 'Failed to reorder buttons'}), 500


@app.route('/api/settings', methods=['GET'])
def get_settings():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dashboard_settings")
        rows = cursor.fetchall()
        conn.close()
        
        settings = {row['key']: row['value'] for row in rows}
        return jsonify(settings)
    except Exception as e:
        logger.error(f"Error fetching settings: {e}")
        return jsonify({'error': 'Failed to fetch settings'}), 500

@app.route('/api/settings', methods=['POST'])
def save_settings():
    try:
        data = request.get_json()
        conn = get_db()
        cursor = conn.cursor()
        
        for key, value in data.items():
            if not isinstance(value, str):
                value = json.dumps(value)
            cursor.execute("INSERT OR REPLACE INTO dashboard_settings (key, value) VALUES (?, ?)", (key, value))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return jsonify({'error': 'Failed to save settings'}), 500


@app.route('/api/export', methods=['GET'])
def export_buttons():
    try:
        tree = get_button_tree()
        response = jsonify(tree)
        response.headers['Content-Disposition'] = f'attachment; filename="telegram-bot-buttons-{datetime.now().strftime("%Y-%m-%d")}.json"'
        return response
    except Exception as e:
        logger.error(f"Error exporting buttons: {e}")
        return jsonify({'error': 'Failed to export buttons'}), 500


@app.route('/api/bot/status', methods=['GET'])
def get_bot_status():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bot_settings WHERE setting_key IN ('bot_running', 'restart_at')")
        rows = cursor.fetchall()
        conn.close()
        
        settings = {row['setting_key']: row['setting_value'] for row in rows}
        
        return jsonify({
            'isRunning': settings.get('bot_running', 'true') == 'true',
            'restartAt': settings.get('restart_at')
        })
    except Exception as e:
        logger.error(f"Error fetching bot status: {e}")
        return jsonify({'error': 'Failed to fetch bot status'}), 500

@app.route('/api/bot/status', methods=['POST'])
def set_bot_status():
    try:
        data = request.get_json()
        is_running = data.get('isRunning', True)
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)",
                      ('bot_running', 'true' if is_running else 'false'))
        conn.commit()
        conn.close()
        
        log_activity('bot_started' if is_running else 'bot_stopped', 'bot', None, 'Bot',
                    f"Bot {'started' if is_running else 'stopped'}")
        
        return jsonify({'isRunning': is_running, 'restartAt': None})
    except Exception as e:
        logger.error(f"Error setting bot status: {e}")
        return jsonify({'error': 'Failed to set bot status'}), 500

@app.route('/api/bot/restart', methods=['POST'])
def restart_bot():
    try:
        data = request.get_json()
        seconds = data.get('seconds', 15)
        
        restart_at = (datetime.now() + timedelta(seconds=seconds)).isoformat()
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)",
                      ('restart_at', restart_at))
        cursor.execute("INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)",
                      ('bot_running', 'false'))
        conn.commit()
        conn.close()
        
        log_activity('bot_restarted', 'bot', None, 'Bot', f"Bot restarting in {seconds} seconds")
        
        return jsonify({'isRunning': False, 'restartAt': restart_at})
    except Exception as e:
        logger.error(f"Error restarting bot: {e}")
        return jsonify({'error': 'Failed to restart bot'}), 500


@app.route('/api/logs', methods=['GET'])
def get_logs():
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM activity_logs ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))
        rows = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(*) as count FROM activity_logs")
        total = cursor.fetchone()['count']
        
        conn.close()
        
        logs = [{
            'id': row['id'],
            'action': row['action'],
            'entityType': row['entity_type'],
            'entityId': row['entity_id'],
            'entityName': row['entity_name'],
            'details': row['details'],
            'createdAt': row['created_at']
        } for row in rows]
        
        return jsonify({'logs': logs, 'total': total, 'limit': limit, 'offset': offset})
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        return jsonify({'error': 'Failed to fetch logs'}), 500


@app.route('/api/orders', methods=['GET'])
def get_orders():
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM orders 
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        rows = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(*) as count FROM orders")
        total_row = cursor.fetchone()
        total = total_row['count'] if total_row else 0
        
        conn.close()
        
        orders = [dict(row) for row in rows]
        
        return jsonify({'orders': orders, 'total': total, 'limit': limit, 'offset': offset})
    except sqlite3.OperationalError:
        return jsonify({'orders': [], 'total': 0, 'limit': limit, 'offset': offset})
    except Exception as e:
        logger.error(f"Error fetching orders: {e}")
        return jsonify({'error': 'Failed to fetch orders'}), 500


if __name__ == '__main__':
    init_db()
    
    port = int(os.environ.get('PORT', 5000))
    
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   🌐  واجهة إدارة البوت - Python/Flask                           ║
║                                                                   ║
║   📦 الخدمة: Flask Web Server (Port {port})                       ║
║                                                                   ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    logger.info(f"Starting Flask server on port {port}")
    logger.info(f"Database: {DB_PATH}")
    logger.info(f"Static files: {app.static_folder}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        threaded=True
    )
