# دليل البدء السريع - SMSPool Service

## 🚀 البدء خلال 5 دقائق

### الخطوة 1: التحقق من الملفات ✅
```bash
cd /home/engine/project/telegram_bot
ls -la smspool_service.py  # يجب أن يكون موجوداً
```

### الخطوة 2: الحصول على مفتاح API
1. اذهب إلى: https://www.smspool.net/my/settings
2. انسخ مفتاح API الخاص بك
3. احفظه في مكان آمن

### الخطوة 3: التكامل في البوت

#### A. في bot.py (للعملاء)

```python
# في بداية الملف
from smspool_service import (
    handle_smspool_callback,
    handle_smspool_inline_query
)

# بعد إنشاء application
def main():
    application = Application.builder().token(TOKEN).build()
    
    # ... handlers الموجودة ...
    
    # إضافة SMSPool handlers
    application.add_handler(
        CallbackQueryHandler(
            handle_smspool_callback,
            pattern=r'^sp_'
        )
    )
    
    application.add_handler(
        InlineQueryHandler(
            handle_smspool_inline_query
        )
    )
    
    # تشغيل البوت
    application.run_polling()
```

#### B. في القائمة الرئيسية

```python
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... الأزرار الموجودة ...
    
    keyboard = [
        # ... أزرار أخرى ...
        [InlineKeyboardButton(
            "📱 سيرڤر US only (1) | Server 2 🆕",
            callback_data="sp_main"
        )],
        # ... المزيد من الأزرار ...
    ]
    
    await update.message.reply_text(
        "القائمة الرئيسية",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
```

#### C. في bot_admin.py (للآدمن)

```python
# في بداية الملف
from telegram.ext import ConversationHandler, MessageHandler, filters
from smspool_service import (
    handle_smspool_admin_callback,
    handle_admin_api_key_input,
    handle_admin_margin_input
)

# States
SMSPOOL_SET_KEY = 100
SMSPOOL_SET_MARGIN = 101

# بعد إنشاء application
def main():
    application = Application.builder().token(TOKEN).build()
    
    # ... handlers الموجودة ...
    
    # إضافة SMSPool Admin ConversationHandler
    smspool_admin_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                handle_smspool_admin_callback,
                pattern=r'^sp_admin_'
            )
        ],
        states={
            SMSPOOL_SET_KEY: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_admin_api_key_input
                )
            ],
            SMSPOOL_SET_MARGIN: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_admin_margin_input
                )
            ],
        },
        fallbacks=[
            CallbackQueryHandler(
                handle_smspool_admin_callback,
                pattern=r'^sp_admin_menu$'
            )
        ],
        allow_reentry=True,
        conversation_timeout=180
    )
    
    application.add_handler(smspool_admin_conv)
    
    # تشغيل البوت
    application.run_polling()
```

#### D. في قائمة الآدمن

```python
async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... الأزرار الموجودة ...
    
    keyboard = [
        # ... أزرار أخرى ...
        [InlineKeyboardButton(
            "📱 إدارة SMSPool",
            callback_data="sp_admin_menu"
        )],
        # ... المزيد من الأزرار ...
    ]
    
    await update.message.reply_text(
        "قائمة الآدمن",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
```

### الخطوة 4: تفعيل Inline Mode في BotFather

```
1. افتح محادثة مع @BotFather
2. أرسل: /setinline
3. اختر البوت الخاص بك
4. أرسل: Search SMSPool numbers
```

### الخطوة 5: تعيين مفتاح API

```
1. شغّل البوت
2. كآدمن، افتح قائمة الإعدادات
3. اضغط "📱 إدارة SMSPool"
4. اضغط "🔑 تعيين مفتاح API"
5. الصق المفتاح الذي حصلت عليه من الموقع
6. تأكد من ظهور رسالة النجاح ✅
```

### الخطوة 6: الاختبار

```
1. كعميل، افتح البوت
2. اضغط "📱 سيرڤر US only (1) | Server 2 🆕"
3. اضغط "🛒 شراء رقم"
4. اختر النوع المطلوب
5. ابحث عن دولة
6. ابحث عن خدمة
7. أكد الشراء
8. تحقق من استلام الرقم
```

---

## 🔧 الإعدادات الإضافية (اختيارية)

### 1. تعديل نسبة الربح
```
آدمن → إدارة SMSPool → تعديل نسبة الربح → أدخل الرقم (مثل: 35)
```

### 2. تفعيل/تعطيل الخدمة
```
آدمن → إدارة SMSPool → تعطيل الخدمة / تفعيل الخدمة
```

### 3. اختبار الاتصال
```
آدمن → إدارة SMSPool → اختبار الاتصال
```

---

## 🐛 حل المشاكل الشائعة

### مشكلة: "Inline Query لا يعمل"
**الحل:**
```
1. تأكد من تفعيل Inline Mode في BotFather
2. أعد تشغيل البوت
3. جرب مرة أخرى
```

### مشكلة: "خطأ في حفظ مفتاح API"
**الحل:**
```
1. تأكد من أن المفتاح صحيح (32+ حرف)
2. تحقق من الاتصال بالإنترنت
3. جرب نسخ المفتاح مرة أخرى
```

### مشكلة: "الخدمة غير متاحة"
**الحل:**
```
1. تأكد من أن الخدمة مفعّلة في لوحة الآدمن
2. تحقق من رصيد API على الموقع
3. اختبر الاتصال من لوحة الآدمن
```

---

## 📚 المراجع الإضافية

- **التوثيق الكامل**: `SMSPOOL_FIXES_README.md`
- **ملخص التغييرات**: `CHANGES_SUMMARY.md`
- **مثال التكامل**: `smspool_integration_example.py`
- **قائمة التحقق**: `VERIFICATION_CHECKLIST.md`

---

## 💡 نصائح مهمة

1. **النسخ الاحتياطي**: احتفظ بنسخة من `smspool_service.py.backup`
2. **المراقبة**: تابع logs البوت للأخطاء
3. **الرصيد**: راقب رصيد API على الموقع
4. **التحديثات**: احفظ مفتاح API في مكان آمن
5. **الاختبار**: اختبر جميع المميزات قبل التشغيل الفعلي

---

## ✅ قائمة التحقق النهائية

- [ ] تم استيراد الدوال في bot.py ✅
- [ ] تم إضافة handlers للعملاء ✅
- [ ] تم إضافة handlers للآدمن ✅
- [ ] تم إضافة زر في القائمة الرئيسية ✅
- [ ] تم إضافة زر في قائمة الآدمن ✅
- [ ] تم تفعيل Inline Mode ✅
- [ ] تم تعيين مفتاح API ✅
- [ ] تم اختبار شراء رقم مؤقت ✅
- [ ] تم اختبار شراء رقم إيجار ✅
- [ ] تم اختبار إعدادات الآدمن ✅

---

## 🎉 مبروك!

الآن خدمة SMSPool جاهزة للاستخدام بالكامل!

للدعم والمساعدة، راجع الملفات التوثيقية المرفقة.

---

📅 **تاريخ**: 2026-02-03
✅ **الحالة**: جاهز للاستخدام
🚀 **الإصدار**: 2.0.0
