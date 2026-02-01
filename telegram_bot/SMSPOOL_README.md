# 📱 SMSPool Integration - Quick Start Guide

## 🚀 التشغيل السريع

### 1. تكوين API Key

```python
# في config.py أضف:
SMSPOOL_API_KEY = 'your_32_character_api_key_here'
```

**الحصول على API Key:**
- زيارة: https://www.smspool.net/my/settings
- إنشاء مفتاح جديد
- نسخه ولصقه في config.py

### 2. تفعيل الخدمة

```python
from smspool_service import smspool_db

# تعيين المفتاح
smspool_db.set_api_key('your_api_key_here')

# تفعيل الخدمة
smspool_db.set_enabled(True)

# تعيين نسبة الربح (افتراضي: 30%)
smspool_db.set_margin_percent(30)
```

### 3. التحقق من العمل

```python
from smspool_service import SMSPoolAPI

api = SMSPoolAPI()
balance = api.get_balance()
print(f"الرصيد: ${balance.get('balance')}")
```

---

## 📚 الاستخدام الأساسي

### للزبائن (Bot Commands)

```
/numbers  → فتح قائمة الأرقام
```

**الخطوات:**
1. اختر الدولة 🌍
2. اختر الخدمة 📱
3. أكّد الشراء ✅
4. استلم الرقم 📲
5. انتظر الرسالة ⏳ (تلقائي)
6. اعرض الكود 🔐

### للآدمن

```
/admin → SMSPool Settings
```

**الإعدادات:**
- 🔑 تعيين API Key
- ✅ تفعيل/تعطيل
- 💹 نسبة الربح
- 💰 الرصيد الحالي
- 📊 الطلبات النشطة

---

## 🎯 الميزات الرئيسية

### 1. أرقام مؤقتة (Temporary Numbers)
- **المدة**: 20 دقيقة - 5 أيام (حسب Pool)
- **الاستخدام**: للتحقق لمرة واحدة
- **الإلغاء**: ممكن قبل استقبال SMS

```python
api.purchase_sms(
    country='US',
    service='google',
    pool='7'  # اختياري: Pool 7 للجودة العالية
)
```

### 2. أرقام مستأجرة (Rentals) ⭐
- **المدة**: 1-30 يوم (قابلة للتمديد)
- **الرسائل**: حتى 25 رسالة يومياً
- **الاستخدام**: للحسابات طويلة الأمد

```python
# شراء
api.purchase_rental(
    rental_id=123,
    days=30,
    service_id='google'
)

# جلب الرسائل
messages = api.get_rental_messages(rental_code='ABC123')

# تمديد
api.extend_rental(rental_code='ABC123', days=15)
```

### 3. إعادة إرسال (Resend)
```python
api.resend_sms(order_id='XYZ789')
```

### 4. أرشفة
```python
api.archive_orders()
```

---

## 📊 الإحصائيات

```python
from smspool_service import smspool_db

stats = smspool_db.get_statistics()

# عرض الإحصائيات اليومية
print(f"الطلبات اليوم: {stats['daily']['orders']}")
print(f"الإيرادات: ${stats['daily']['revenue']}")
print(f"الربح: ${stats['daily']['profit']}")
```

---

## 🔧 API Reference السريع

### SMSPoolAPI

```python
from smspool_service import SMSPoolAPI

api = SMSPoolAPI(api_key='optional')

# الرصيد
api.get_balance()

# الخدمات
api.get_services()

# الدول
api.get_countries()

# شراء رقم مؤقت
api.purchase_sms(country='US', service='google')

# فحص الرسالة
api.check_sms(order_id='ABC123')

# إلغاء
api.cancel_sms(order_id='ABC123')

# إعادة إرسال
api.resend_sms(order_id='ABC123')

# الأرقام المستأجرة
api.get_rentals()
api.purchase_rental(rental_id=123, days=30, service_id='google')
api.get_rental_messages(rental_code='ABC123')
api.extend_rental(rental_code='ABC123', days=15)
api.refund_rental(rental_code='ABC123')
```

### SMSPoolDB

```python
from smspool_service import smspool_db

# الإعدادات
smspool_db.set_api_key('key')
smspool_db.set_enabled(True)
smspool_db.set_margin_percent(30)

# الطلبات
smspool_db.create_order(...)
smspool_db.get_user_orders(user_id)
smspool_db.update_order_status(order_id, 'received')

# الإيجارات
smspool_db.create_rental(...)
smspool_db.get_user_rentals(user_id)
smspool_db.update_rental_status(rental_code, 'active')

# الرسائل (آخر 3)
smspool_db.save_message(user_id, message_text, ...)
smspool_db.get_messages(order_id=...)

# السجلات
smspool_db.log_operation(user_id, 'purchase', 'order', ...)

# الإحصائيات
smspool_db.update_statistics(is_rental=False, sale_price=5.0, cost_price=3.0)
smspool_db.get_statistics()
```

---

## 🆚 المقارنة مع NonVoip

| الميزة | NonVoip | SMSPool |
|--------|---------|---------|
| أرقام مؤقتة | 15 دقيقة | 20 دقيقة - 5 أيام ✅ |
| أرقام طويلة | 3 أيام / 30 يوم | شهرية (قابلة للتمديد) ✅ |
| تفعيل يدوي | مطلوب | تلقائي ✅ |
| رسائل متعددة | ❌ واحدة فقط | ✅ 25 يومياً |
| إعادة إرسال | ❌ | ✅ |
| Pool System | ❌ | ✅ |
| دولي | US focus | 200+ دولة ✅ |

---

## ⚠️ ملاحظات مهمة

### 1. التوافق مع الكود القديم
✅ **جميع استدعاءات NonVoip تعمل تلقائياً!**

```python
# الكود القديم:
from non_voip_unified import NonVoipAPI

# يتم توجيهه تلقائياً إلى SMSPool - لا تعديل مطلوب!
```

### 2. الدوال المحذوفة
```python
# ❌ غير موجودة (غير مطلوبة):
activate()                      # التفعيل تلقائي
check_expired_activations()     # لا نظام تفعيل منفصل
reuse()                         # استخدم resend_sms()
```

### 3. Pool System
- **Pool 7 (Foxtrot)**: أرقام أمريكية عالية الجودة (3-5 أيام)
- الأرقام العادية: 20 دقيقة - ساعات قليلة
- اختر Pool للحصول على جودة أفضل

---

## 🐛 Troubleshooting

### مشكلة: "API Key غير صحيح"
```python
# تحقق من المفتاح
from smspool_service import smspool_db
print(smspool_db.get_api_key())

# تأكد أن المفتاح 32 حرف
# احصل على مفتاح جديد من: https://www.smspool.net/my/settings
```

### مشكلة: "رصيد غير كافٍ"
```python
# افحص الرصيد
api.get_balance()

# أضف رصيد من: https://www.smspool.net/my/topup
```

### مشكلة: "الخدمة معطلة"
```python
# تفعيل الخدمة
smspool_db.set_enabled(True)
```

---

## 📖 المزيد من الوثائق

- **التقرير الكامل**: `MIGRATION_REPORT.md`
- **الأرشيف**: `non_voip_trash.py`
- **التوسعات**: `smspool_extensions.py`
- **التوافق**: `non_voip_unified.py`

---

## 🎉 الخلاصة

**SMSPool جاهز للعمل!**

- ✅ أسهل في الاستخدام من NonVoip
- ✅ ميزات أكثر (Rentals, Pools, Resend)
- ✅ دعم دولي أفضل (200+ دولة)
- ✅ توافق كامل مع الكود القديم
- ✅ رسائل متعددة للأرقام المستأجرة

**ابدأ الآن:**
1. احصل على API Key
2. أضفه في config.py
3. فعّل الخدمة
4. جرّب شراء رقم!

---

**Need Help?**
- 📧 SMSPool Support: support@smspool.net
- 📚 API Docs: https://www.smspool.net/article/how-to-use-the-smspool-api
- 💬 Telegram: @smspoolnet
