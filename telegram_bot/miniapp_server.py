#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================
Flask Server for Mini App - miniapp_server.py
============================================
خادم API لواجهة إدارة الأزرار الديناميكية
============================================
"""

import os
import json
import hmac
import hashlib
import logging
from functools import wraps
from urllib.parse import parse_qsl

from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_cors import CORS

from dynamic_buttons import dynamic_buttons_manager
from config import ADMIN_IDS, BOT_TOKEN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

app.config['JSON_AS_ASCII'] = False
app.config['JSON_SORT_KEYS'] = False


def validate_telegram_data(init_data: str) -> dict:
    """التحقق من صحة بيانات Telegram Mini App"""
    if not init_data:
        return None
    
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        
        received_hash = parsed.pop('hash', None)
        if not received_hash:
            return None
        
        data_check_string = '\n'.join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )
        
        secret_key = hmac.new(
            b"WebAppData",
            BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()
        
        expected_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if hmac.compare_digest(received_hash, expected_hash):
            if 'user' in parsed:
                parsed['user'] = json.loads(parsed['user'])
            return parsed
        
        return None
        
    except Exception as e:
        logger.error(f"Error validating Telegram data: {e}")
        return None


def require_admin(f):
    """ديكوراتور للتحقق من صلاحيات الآدمن"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        init_data = request.headers.get('X-Telegram-Init-Data', '')
        
        if os.environ.get('DEV_MODE') == '1':
            return f(*args, **kwargs)
        
        if not ADMIN_IDS:
            logger.warning("⚠️ No admins configured - allowing access for setup")
            return f(*args, **kwargs)
        
        telegram_data = validate_telegram_data(init_data)
        
        if not telegram_data:
            return jsonify({'error': 'Invalid authentication', 'error_ar': 'فشل التحقق'}), 401
        
        user = telegram_data.get('user', {})
        user_id = user.get('id')
        
        if user_id not in ADMIN_IDS:
            return jsonify({'error': 'Access denied', 'error_ar': 'غير مسموح بالوصول'}), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


@app.route('/')
def index():
    """الصفحة الرئيسية - Mini App"""
    return render_template('miniapp.html')


@app.route('/static/<path:filename>')
def serve_static(filename):
    """تقديم الملفات الثابتة"""
    return send_from_directory('static', filename)


@app.route('/api/buttons/tree', methods=['GET'])
@require_admin
def get_button_tree():
    """الحصول على شجرة الأزرار الكاملة"""
    language = request.args.get('lang', 'ar')
    tree = dynamic_buttons_manager.get_full_tree(language, enabled_only=False)
    return jsonify({'success': True, 'tree': tree})


@app.route('/api/buttons/root', methods=['GET'])
@require_admin
def get_root_buttons():
    """الحصول على الأزرار الجذرية"""
    language = request.args.get('lang', 'ar')
    enabled_only = request.args.get('enabled_only', 'false').lower() == 'true'
    buttons = dynamic_buttons_manager.get_root_buttons(language, enabled_only)
    return jsonify({'success': True, 'buttons': buttons})


@app.route('/api/buttons/<int:parent_id>/children', methods=['GET'])
@require_admin
def get_children(parent_id):
    """الحصول على الأزرار الفرعية"""
    language = request.args.get('lang', 'ar')
    enabled_only = request.args.get('enabled_only', 'false').lower() == 'true'
    children = dynamic_buttons_manager.get_children(parent_id, language, enabled_only)
    return jsonify({'success': True, 'children': children})


@app.route('/api/buttons/<int:button_id>', methods=['GET'])
@require_admin
def get_button(button_id):
    """الحصول على تفاصيل زر محدد"""
    language = request.args.get('lang', 'ar')
    button = dynamic_buttons_manager.get_button_by_id(button_id, language)
    
    if button:
        button['path'] = dynamic_buttons_manager.get_button_path(button_id, language)
        return jsonify({'success': True, 'button': button})
    
    return jsonify({'success': False, 'error': 'Button not found', 'error_ar': 'الزر غير موجود'}), 404


@app.route('/api/buttons', methods=['POST'])
@require_admin
def add_button():
    """إضافة زر جديد"""
    data = request.get_json()
    
    required_fields = ['button_key', 'text_ar', 'text_en']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False, 
                'error': f'Missing field: {field}',
                'error_ar': f'حقل مفقود: {field}'
            }), 400
    
    try:
        button_id = dynamic_buttons_manager.add_button(data)
        button = dynamic_buttons_manager.get_button_by_id(button_id)
        return jsonify({'success': True, 'button': button})
    except Exception as e:
        logger.error(f"Error adding button: {e}")
        return jsonify({
            'success': False, 
            'error': str(e),
            'error_ar': 'فشل إضافة الزر'
        }), 500


@app.route('/api/buttons/<int:button_id>', methods=['PUT'])
@require_admin
def update_button(button_id):
    """تحديث زر موجود"""
    data = request.get_json()
    
    try:
        success = dynamic_buttons_manager.update_button(button_id, data)
        
        if success:
            button = dynamic_buttons_manager.get_button_by_id(button_id)
            return jsonify({'success': True, 'button': button})
        
        return jsonify({
            'success': False, 
            'error': 'Button not found',
            'error_ar': 'الزر غير موجود'
        }), 404
        
    except Exception as e:
        logger.error(f"Error updating button: {e}")
        return jsonify({
            'success': False, 
            'error': str(e),
            'error_ar': 'فشل تحديث الزر'
        }), 500


@app.route('/api/buttons/<int:button_id>', methods=['DELETE'])
@require_admin
def delete_button(button_id):
    """حذف زر"""
    try:
        success = dynamic_buttons_manager.delete_button(button_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Button deleted', 'message_ar': 'تم حذف الزر'})
        
        return jsonify({
            'success': False, 
            'error': 'Button not found',
            'error_ar': 'الزر غير موجود'
        }), 404
        
    except Exception as e:
        logger.error(f"Error deleting button: {e}")
        return jsonify({
            'success': False, 
            'error': str(e),
            'error_ar': 'فشل حذف الزر'
        }), 500


@app.route('/api/buttons/<int:button_id>/toggle', methods=['POST'])
@require_admin
def toggle_button(button_id):
    """تبديل حالة الزر"""
    try:
        success = dynamic_buttons_manager.toggle_button(button_id)
        
        if success:
            button = dynamic_buttons_manager.get_button_by_id(button_id)
            return jsonify({'success': True, 'button': button})
        
        return jsonify({
            'success': False, 
            'error': 'Button not found',
            'error_ar': 'الزر غير موجود'
        }), 404
        
    except Exception as e:
        logger.error(f"Error toggling button: {e}")
        return jsonify({
            'success': False, 
            'error': str(e),
            'error_ar': 'فشل تبديل حالة الزر'
        }), 500


@app.route('/api/buttons/reorder', methods=['POST'])
@require_admin
def reorder_buttons():
    """إعادة ترتيب الأزرار"""
    data = request.get_json()
    button_ids = data.get('button_ids', [])
    
    if not button_ids:
        return jsonify({
            'success': False, 
            'error': 'No button IDs provided',
            'error_ar': 'لم يتم توفير معرفات الأزرار'
        }), 400
    
    try:
        success = dynamic_buttons_manager.reorder_buttons(button_ids)
        return jsonify({'success': success})
        
    except Exception as e:
        logger.error(f"Error reordering buttons: {e}")
        return jsonify({
            'success': False, 
            'error': str(e),
            'error_ar': 'فشل إعادة ترتيب الأزرار'
        }), 500


@app.route('/api/buttons/export', methods=['GET'])
@require_admin
def export_tree():
    """تصدير شجرة الأزرار"""
    tree_json = dynamic_buttons_manager.export_tree()
    return jsonify({'success': True, 'data': json.loads(tree_json)})


@app.route('/api/buttons/import', methods=['POST'])
@require_admin
def import_tree():
    """استيراد شجرة الأزرار"""
    data = request.get_json()
    tree_data = data.get('tree')
    
    if not tree_data:
        return jsonify({
            'success': False, 
            'error': 'No tree data provided',
            'error_ar': 'لم يتم توفير بيانات الشجرة'
        }), 400
    
    try:
        success = dynamic_buttons_manager.import_tree(json.dumps(tree_data))
        
        if success:
            return jsonify({'success': True, 'message': 'Tree imported', 'message_ar': 'تم استيراد الشجرة'})
        
        return jsonify({
            'success': False, 
            'error': 'Import failed',
            'error_ar': 'فشل الاستيراد'
        }), 500
        
    except Exception as e:
        logger.error(f"Error importing tree: {e}")
        return jsonify({
            'success': False, 
            'error': str(e),
            'error_ar': 'فشل استيراد الشجرة'
        }), 500


@app.route('/api/services', methods=['GET'])
@require_admin
def get_services():
    """الحصول على جميع الخدمات"""
    language = request.args.get('lang', 'ar')
    enabled_only = request.args.get('enabled_only', 'true').lower() == 'true'
    services = dynamic_buttons_manager.get_all_services(language, enabled_only)
    return jsonify({'success': True, 'services': services})


@app.route('/api/services/<int:button_id>/price', methods=['PUT'])
@require_admin
def update_service_price(button_id):
    """تحديث سعر خدمة"""
    data = request.get_json()
    price = data.get('price')
    
    if price is None:
        return jsonify({
            'success': False, 
            'error': 'Price not provided',
            'error_ar': 'لم يتم توفير السعر'
        }), 400
    
    try:
        success = dynamic_buttons_manager.update_price(button_id, float(price))
        
        if success:
            button = dynamic_buttons_manager.get_button_by_id(button_id)
            return jsonify({'success': True, 'button': button})
        
        return jsonify({
            'success': False, 
            'error': 'Service not found',
            'error_ar': 'الخدمة غير موجودة'
        }), 404
        
    except Exception as e:
        logger.error(f"Error updating price: {e}")
        return jsonify({
            'success': False, 
            'error': str(e),
            'error_ar': 'فشل تحديث السعر'
        }), 500


@app.route('/health')
def health_check():
    """فحص صحة الخادم"""
    return jsonify({'status': 'ok', 'service': 'Button Manager Mini App'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEV_MODE', '0') == '1'
    
    logger.info(f"🚀 Starting Mini App Server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
