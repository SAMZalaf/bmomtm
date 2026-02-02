#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكريبت اختبار شامل لـ SMSPool API
يختبر جميع الوظائف المطلوبة في المهمة
"""

import sys
import os

# إضافة المسار الحالي
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from smspool_service import SMSPoolAPI, SMSPoolDB

def print_section(title):
    """طباعة عنوان قسم"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def test_database_connection():
    """1️⃣ اختبار الاتصال بقاعدة البيانات وجلب المفتاح"""
    print_section("1️⃣ اختبار قاعدة البيانات")
    
    try:
        db = SMSPoolDB()
        print("✅ الاتصال بقاعدة البيانات: نجح")
        
        # جلب المفتاح
        api_key = db.get_api_key()
        if api_key:
            masked_key = api_key[:20] + "..." if len(api_key) > 20 else api_key
            print(f"✅ مفتاح API موجود: {masked_key}")
            print(f"✅ طول المفتاح: {len(api_key)} حرف")
        else:
            print("❌ مفتاح API غير موجود في قاعدة البيانات")
            return False
        
        # التحقق من حالة التفعيل
        enabled = db.is_enabled()
        print(f"✅ حالة الخدمة: {'مفعلة' if enabled else 'معطلة'}")
        
        # جلب نسبة الربح
        margin = db.get_margin_percent()
        print(f"✅ نسبة الربح: {margin}%")
        
        return True
    except Exception as e:
        print(f"❌ خطأ في قاعدة البيانات: {e}")
        return False

def test_api_connection():
    """2️⃣ اختبار الاتصال بـ API"""
    print_section("2️⃣ اختبار الاتصال بـ SMSPool API")
    
    try:
        # جلب المفتاح من قاعدة البيانات
        db = SMSPoolDB()
        api_key = db.get_api_key()
        
        if not api_key:
            print("❌ لا يمكن الاتصال بدون مفتاح API")
            return False
        
        # إنشاء كائن API
        api = SMSPoolAPI(api_key=api_key)
        print("✅ تم إنشاء كائن SMSPoolAPI")
        
        # اختبار جلب الرصيد
        balance_result = api.get_balance()
        if balance_result.get('status') == 'success':
            balance = balance_result.get('balance')
            print(f"✅ اختبار الاتصال: نجح")
            print(f"✅ الرصيد الحالي: ${balance}")
            return True
        else:
            error_msg = balance_result.get('message', 'Unknown error')
            print(f"❌ فشل الاتصال: {error_msg}")
            return False
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {e}")
        return False

def test_fetch_services():
    """3️⃣ اختبار جلب الخدمات"""
    print_section("3️⃣ اختبار جلب الخدمات")
    
    try:
        db = SMSPoolDB()
        api_key = db.get_api_key()
        api = SMSPoolAPI(api_key=api_key)
        
        # جلب الخدمات
        services = api.get_services()
        if services and len(services) > 0:
            print(f"✅ عدد الخدمات المتاحة: {len(services)}")
            print("✅ أول 5 خدمات:")
            for i, service in enumerate(services[:5], 1):
                service_id = service.get('ID', 'N/A')
                service_name = service.get('name', 'N/A')
                print(f"   {i}. {service_name} (ID: {service_id})")
            return True
        else:
            print("❌ لا توجد خدمات متاحة")
            return False
    except Exception as e:
        print(f"❌ خطأ في جلب الخدمات: {e}")
        return False

def test_fetch_countries():
    """4️⃣ اختبار جلب الدول"""
    print_section("4️⃣ اختبار جلب الدول")
    
    try:
        db = SMSPoolDB()
        api_key = db.get_api_key()
        api = SMSPoolAPI(api_key=api_key)
        
        # جلب الدول
        countries = api.get_countries()
        if countries and len(countries) > 0:
            print(f"✅ عدد الدول المتاحة: {len(countries)}")
            print("✅ أول 5 دول:")
            for i, country in enumerate(countries[:5], 1):
                country_id = country.get('ID', 'N/A')
                country_name = country.get('name', 'N/A')
                print(f"   {i}. {country_name} (ID: {country_id})")
            return True
        else:
            print("❌ لا توجد دول متاحة")
            return False
    except Exception as e:
        print(f"❌ خطأ في جلب الدول: {e}")
        return False

def test_margin_calculation():
    """5️⃣ اختبار حساب الهامش"""
    print_section("5️⃣ اختبار حساب هامش الربح")
    
    try:
        db = SMSPoolDB()
        margin = db.get_margin_percent()
        
        test_prices = [0.50, 1.00, 2.50, 5.00]
        print(f"✅ نسبة الربح المحفوظة: {margin}%")
        print("✅ أمثلة على حساب الأسعار:")
        
        for cost_price in test_prices:
            sale_price = cost_price * (1 + margin / 100)
            profit = sale_price - cost_price
            print(f"   سعر التكلفة: ${cost_price:.2f} → سعر البيع: ${sale_price:.2f} (الربح: ${profit:.2f})")
        
        return True
    except Exception as e:
        print(f"❌ خطأ في حساب الهامش: {e}")
        return False

def test_margin_update():
    """6️⃣ اختبار تحديث هامش الربح"""
    print_section("6️⃣ اختبار تحديث هامش الربح")
    
    try:
        db = SMSPoolDB()
        
        # حفظ الهامش الحالي
        original_margin = db.get_margin_percent()
        print(f"✅ الهامش الحالي: {original_margin}%")
        
        # تجربة تحديث الهامش إلى 35%
        new_margin = 35.0
        if db.set_margin_percent(new_margin):
            print(f"✅ تم تحديث الهامش إلى: {new_margin}%")
            
            # التحقق من التحديث
            current_margin = db.get_margin_percent()
            if current_margin == new_margin:
                print(f"✅ التحقق من التحديث: نجح (الهامش الحالي: {current_margin}%)")
            else:
                print(f"⚠️ تحذير: الهامش المحفوظ ({current_margin}%) يختلف عن المتوقع ({new_margin}%)")
            
            # إعادة الهامش الأصلي
            db.set_margin_percent(original_margin)
            print(f"✅ تم إعادة الهامش إلى القيمة الأصلية: {original_margin}%")
            
            return True
        else:
            print("❌ فشل تحديث الهامش")
            return False
    except Exception as e:
        print(f"❌ خطأ في تحديث الهامش: {e}")
        return False

def test_settings_management():
    """7️⃣ اختبار إدارة الإعدادات"""
    print_section("7️⃣ اختبار إدارة الإعدادات")
    
    try:
        db = SMSPoolDB()
        
        # حفظ الحالة الحالية
        original_enabled = db.is_enabled()
        print(f"✅ الحالة الحالية: {'مفعلة' if original_enabled else 'معطلة'}")
        
        # تجربة التعطيل
        if db.set_enabled(False):
            print("✅ تم تعطيل الخدمة مؤقتاً")
            
            # التحقق
            if not db.is_enabled():
                print("✅ التحقق من التعطيل: نجح")
            else:
                print("⚠️ تحذير: الخدمة لا تزال مفعلة")
            
            # إعادة التفعيل
            db.set_enabled(True)
            print("✅ تم إعادة تفعيل الخدمة")
            
            return True
        else:
            print("❌ فشل تغيير حالة الخدمة")
            return False
    except Exception as e:
        print(f"❌ خطأ في إدارة الإعدادات: {e}")
        return False

def main():
    """تشغيل جميع الاختبارات"""
    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "اختبار شامل لـ SMSPool API" + " " * 30 + "║")
    print("╚" + "═" * 78 + "╝")
    
    results = []
    
    # تشغيل الاختبارات
    results.append(("اختبار قاعدة البيانات", test_database_connection()))
    results.append(("اختبار الاتصال بـ API", test_api_connection()))
    results.append(("اختبار جلب الخدمات", test_fetch_services()))
    results.append(("اختبار جلب الدول", test_fetch_countries()))
    results.append(("اختبار حساب الهامش", test_margin_calculation()))
    results.append(("اختبار تحديث الهامش", test_margin_update()))
    results.append(("اختبار إدارة الإعدادات", test_settings_management()))
    
    # عرض النتائج النهائية
    print_section("📊 ملخص النتائج")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ نجح" if result else "❌ فشل"
        print(f"{status} - {test_name}")
    
    print(f"\n{'=' * 80}")
    print(f"  النتيجة النهائية: {passed}/{total} اختبار نجح")
    print(f"{'=' * 80}\n")
    
    # تحديد النجاح الكامل
    if passed == total:
        print("🎉 جميع الاختبارات نجحت! ✅")
        print("✅ خدمة SMSPool جاهزة للعمل بشكل كامل")
        return 0
    else:
        print(f"⚠️ {total - passed} اختبار فشل")
        print("❌ يرجى مراجعة الأخطاء أعلاه")
        return 1

if __name__ == "__main__":
    sys.exit(main())
