#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكريبت لإصلاح وتحسين smspool_service.py
"""

import re

# قراءة الملف
with open('smspool_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. إضافة دالة process_rent_purchase قبل process_purchase
rent_purchase_function = '''

async def process_rent_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE,
                               country_id: str, service_id: str, days: str) -> None:
    """معالجة شراء إيجار رقم"""
    query = update.callback_query
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    # جلب السعر من API مباشرة للإيجار
    api_key = smspool_db.get_api_key()
    api = SMSPoolAPI(api_key)
    
    # استخدام endpoint خاص بالإيجار
    price_info = api._api_request("request/rent_price", data={
        'service': service_id,
        'country': country_id,
        'duration': days
    })
    
    if not price_info or price_info.get('price') is None:
        msg = (
            'خدمة الإيجار غير متاحة حالياً' if language == 'ar' else 'Rent service not available right now'
        )
        await query.edit_message_text(
            get_smspool_message('error', language).format(message=msg),
            parse_mode='HTML',
        )
        return
    
    cost_price = float(price_info.get('price'))
    margin = smspool_db.get_margin_percent()
    sale_price = round(cost_price * (1 + margin / 100), 2)
    
    balance = get_user_balance(user_id)
    if balance < sale_price:
        await query.edit_message_text(
            get_smspool_message('insufficient_balance', language).format(
                balance=balance,
                required=sale_price
            ),
            parse_mode='HTML'
        )
        return
    
    # الحصول على معلومات الخدمة والدولة
    services = api.get_services()
    service_name = 'Unknown'
    for s in services:
        if str(s.get('ID', s.get('id', ''))) == service_id:
            service_name = s.get('name', 'Unknown')
            break
    
    countries = api.get_countries()
    country_name = 'Unknown'
    for c in countries:
        if str(c.get('ID', c.get('id', ''))) == country_id:
            country_name = c.get('name', 'Unknown')
            break
    
    # عرض رسالة معالجة
    processing_msg = "⏳ " + ("جاري معالجة الطلب..." if language == 'ar' else "Processing order...")
    await query.edit_message_text(processing_msg)
    
    try:
        result = api.purchase_sms(country_id, service_id, order_type='rent', days=days)
        
        if result.get('status') == 'success':
            # خصم الرصيد
            update_user_balance(user_id, sale_price, 'subtract')
            
            order_id = result.get('order_id')
            number = result.get('number')
            country = result.get('country', country_name)
            service = result.get('service', service_name)
            pool = result.get('pool', '')
            expires_in = result.get('expires_in', int(days) * 24 * 3600)  # بالثواني
            
            # حفظ الطلب في قاعدة البيانات
            smspool_db.create_order(
                user_id=user_id,
                order_id=order_id,
                number=number,
                country=country,
                country_id=country_id,
                service=service,
                service_id=service_id,
                pool=str(pool),
                cost_price=cost_price,
                sale_price=sale_price,
                expires_in=expires_in
            )
            
            expires_days = int(days)
            
            text = get_smspool_message('purchase_success', language).format(
                number=number,
                country=country,
                service=service,
                expires=f"{expires_days} " + ("يوم" if language == 'ar' else "day(s)")
            )
            
            keyboard = [
                [InlineKeyboardButton(
                    "🔄 " + ("فحص الرسالة" if language == 'ar' else "Check SMS"),
                    callback_data=f"sp_check_{order_id}"
                )],
                [InlineKeyboardButton(
                    "📤 " + ("إعادة إرسال" if language == 'ar' else "Resend"),
                    callback_data=f"sp_resend_{order_id}"
                )],
                [InlineKeyboardButton(
                    "❌ " + ("إلغاء واسترداد" if language == 'ar' else "Cancel & Refund"),
                    callback_data=f"sp_cancel_{order_id}"
                )],
                [InlineKeyboardButton(
                    get_smspool_message('back', language),
                    callback_data="sp_main"
                )]
            ]
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
            
            # بدء المراقبة التلقائية للرسائل
            if hasattr(context, 'job_queue') and context.job_queue:
                context.job_queue.run_repeating(
                    check_sms_job,
                    interval=10,
                    first=5,
                    data={'order_id': order_id, 'user_id': user_id, 'chat_id': query.message.chat_id},
                    name=f"sms_check_{order_id}"
                )
        else:
            error_msg = result.get('message', 'Purchase failed')
            error_code = get_error_code_from_message(error_msg)
            
            await query.edit_message_text(
                get_smspool_message('error', language).format(message=ERROR_CODES.get(error_code, error_msg)),
                parse_mode='HTML'
            )
    
    except Exception as e:
        logger.error(f"خطأ في معالجة شراء إيجار SMSPool: {e}")
        error_text = "❌ " + ("حدث خطأ غير متوقع" if language == 'ar' else "An unexpected error occurred")
        await query.edit_message_text(error_text)

'''

# إضافة الدالة قبل process_purchase
content = content.replace(
    'async def process_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE,',
    rent_purchase_function + 'async def process_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE,'
)

# 2. تغيير التسميات في SMSPOOL_MESSAGES
# استبدال "SMS pool" بـ "Server 2 🆕"
content = re.sub(
    r"'menu_title': '📱 أرقام SMS',",
    "'menu_title': 'سيرڤر US only (1) | Server 2 🆕',",
    content
)

# 3. تحديث handle_smspool_inline_query لدعم البحث من أول حرف
# البحث من أول حرف موجود بالفعل، لكن سنحسنه
old_search = '''        for country in countries:
            country_name = country.get('name', '').lower()
            short_name = country.get('short_name', '').lower()
            
            if query_text in country_name or query_text in short_name:
                matching_countries.append(country)'''

new_search = '''        for country in countries:
            country_name = country.get('name', '').lower()
            short_name = country.get('short_name', '').lower()
            
            # البحث من أول حرف (startswith) أو في أي مكان (in)
            if country_name.startswith(query_text) or short_name.startswith(query_text) or query_text in country_name or query_text in short_name:
                matching_countries.append(country)'''

content = content.replace(old_search, new_search)

# كتابة الملف المحدث
with open('smspool_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ تم تطبيق الإصلاحات بنجاح على smspool_service.py")
