#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكريبت لإضافة زر SMSPool إلى القائمة الرئيسية
"""

import sys
import os
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dynamic_buttons import DynamicButtonsManager

def add_smspool_button():
    """إضافة زر SMSPool إلى القائمة الرئيسية"""
    
    print("=" * 80)
    print("  إضافة زر SMSPool إلى القائمة الرئيسية")
    print("=" * 80)
    
    try:
        manager = DynamicButtonsManager()
        
        # التحقق من وجود الزر بالفعل
        existing = manager.get_button_by_key('smspool_main')
        if existing:
            print("⚠️ زر SMSPool موجود بالفعل!")
            print(f"   المفتاح: {existing['button_key']}")
            print(f"   النص العربي: {existing['text_ar']}")
            print(f"   النص الإنجليزي: {existing['text_en']}")
            print(f"   الحالة: {'مفعل' if existing['is_enabled'] else 'معطل'}")
            return True
        
        # إضافة الزر الجديد
        button_data = {
            'button_key': 'smspool_main',
            'text_ar': '📱 أرقام SMSPool',
            'text_en': '📱 SMSPool Numbers',
            'button_type': 'action',
            'is_enabled': True,
            'is_service': True,
            'price': 0.0,
            'ask_quantity': False,
            'default_quantity': 1,
            'message_ar': 'خدمة SMSPool - احصل على أرقام للتحقق',
            'message_en': 'SMSPool Service - Get numbers for verification',
            'order_index': 10,
            'icon': '📱',
            'callback_data': 'smspool_start',
            'parent_id': None  # زر رئيسي
        }
        
        button_id = manager.add_button(button_data)
        
        if button_id:
            print("✅ تم إضافة زر SMSPool بنجاح!")
            print(f"   المعرف: {button_id}")
            print(f"   المفتاح: {button_data['button_key']}")
            print(f"   النص العربي: {button_data['text_ar']}")
            print(f"   النص الإنجليزي: {button_data['text_en']}")
            return True
        else:
            print("❌ فشل إضافة الزر")
            return False
            
    except Exception as e:
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """التشغيل الرئيسي"""
    if add_smspool_button():
        print("\n" + "=" * 80)
        print("✅ العملية اكتملت بنجاح!")
        print("=" * 80)
        return 0
    else:
        print("\n" + "=" * 80)
        print("❌ فشلت العملية")
        print("=" * 80)
        return 1

if __name__ == "__main__":
    sys.exit(main())
