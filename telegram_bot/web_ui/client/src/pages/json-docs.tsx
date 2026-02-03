import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Download, FileText, Copy, Check } from "lucide-react";
import { useLanguage } from "@/lib/language-context";
import { useState } from "react";
import { useToast } from "@/hooks/use-toast";

const jsonDocumentation = `# دليل تعليمات JSON لبوت تيليغرام - Telegram Bot JSON Instructions Guide

## مقدمة / Introduction
هذا الملف يحتوي على جميع التعليمات اللازمة لإنشاء ملفات JSON صالحة لبوت التيليغرام.
This file contains all instructions needed to create valid JSON files for the Telegram bot.

---

## هيكل الزر الأساسي / Basic Button Structure

كل زر في النظام يتبع هذا الهيكل:
Each button in the system follows this structure:

\`\`\`json
{
  "buttonKey": "unique_key",
  "textAr": "النص العربي",
  "textEn": "English Text",
  "buttonType": "menu",
  "isEnabled": true,
  "isHidden": false,
  "disabledMessage": "هذه الخدمة متوقفة مؤقتاً",
  "isService": false,
  "price": 0,
  "askQuantity": false,
  "defaultQuantity": 1,
  "showBackOnQuantity": true,
  "showCancelOnQuantity": true,
  "messageAr": "الرسالة العربية",
  "messageEn": "English message",
  "orderIndex": 0,
  "icon": "🔹",
  "callbackData": "dyn_unique",
  "backBehavior": "step",
  "buttonSize": "large",
  "children": []
}
\`\`\`

---

## شرح الحقول / Field Descriptions

### الحقول المطلوبة / Required Fields

| الحقل | النوع | الوصف | المثال |
|-------|------|-------|--------|
| buttonKey | string | معرف فريد للزر (بدون مسافات، أحرف إنجليزية) | "static_proxy", "socks_us" |
| textAr | string | النص الذي يظهر للمستخدم بالعربية | "بروكسي ثابت" |
| textEn | string | النص الذي يظهر للمستخدم بالإنجليزية | "Static Proxy" |
| buttonType | string | نوع الزر (انظر أنواع الأزرار) | "menu", "service", "message" |

### الحقول الاختيارية / Optional Fields

| الحقل | النوع | الافتراضي | الوصف |
|-------|------|----------|-------|
| isEnabled | boolean | true | هل الزر مفعل ويظهر للمستخدمين |
| isHidden | boolean | false | هل الزر مخفي |
| disabledMessage | string | "هذه الخدمة متوقفة مؤقتاً" | الرسالة عند الضغط على زر معطل |
| isService | boolean | false | هل هذا الزر خدمة مدفوعة |
| price | number | 0 | سعر الخدمة بالدولار |
| askQuantity | boolean | false | هل يطلب الكمية من المستخدم |
| defaultQuantity | number | 1 | الكمية الافتراضية |
| showBackOnQuantity | boolean | true | إظهار زر رجوع عند طلب الكمية |
| showCancelOnQuantity | boolean | true | إظهار زر إلغاء عند طلب الكمية |
| messageAr | string | "" | الرسالة العربية التي تظهر عند الضغط |
| messageEn | string | "" | الرسالة الإنجليزية |
| orderIndex | number | 0 | ترتيب الزر (0 = الأول) |
| icon | string | "" | أيقونة أو إيموجي للزر |
| callbackData | string | auto | بيانات الاستدعاء (يتم توليدها تلقائياً) |
| backBehavior | string | "step" | سلوك الرجوع: "step" أو "root" |
| buttonSize | string | "large" | حجم الزر: "large" أو "small" |
| children | array | [] | الأزرار الفرعية |

---

## أنواع الأزرار / Button Types

### 1. menu (قائمة)
يفتح قائمة فرعية تحتوي على أزرار أخرى.

\`\`\`json
{
  "buttonKey": "main_services",
  "textAr": "🛒 الخدمات",
  "textEn": "🛒 Services",
  "buttonType": "menu",
  "messageAr": "اختر الخدمة المطلوبة:",
  "messageEn": "Choose the service:",
  "children": [
    // الأزرار الفرعية هنا
  ]
}
\`\`\`

### 2. service (خدمة)
خدمة قابلة للشراء مع سعر.

\`\`\`json
{
  "buttonKey": "proxy_us_30",
  "textAr": "🇺🇸 بروكسي أمريكي 30 يوم",
  "textEn": "🇺🇸 US Proxy 30 Days",
  "buttonType": "service",
  "isService": true,
  "price": 5.99,
  "askQuantity": true,
  "defaultQuantity": 1,
  "messageAr": "تم اختيار البروكسي الأمريكي",
  "messageEn": "US Proxy selected"
}
\`\`\`

### 3. message (رسالة)
يرسل رسالة فقط بدون إجراء إضافي.

\`\`\`json
{
  "buttonKey": "about_us",
  "textAr": "ℹ️ من نحن",
  "textEn": "ℹ️ About Us",
  "buttonType": "message",
  "messageAr": "نحن متجر إلكتروني متخصص في...",
  "messageEn": "We are an online store specialized in..."
}
\`\`\`

### 4. link (رابط)
يفتح رابط خارجي.

\`\`\`json
{
  "buttonKey": "support_channel",
  "textAr": "📢 قناة الدعم",
  "textEn": "📢 Support Channel",
  "buttonType": "link",
  "messageAr": "https://t.me/your_channel",
  "messageEn": "https://t.me/your_channel"
}
\`\`\`

### 5. back (رجوع)
زر للعودة للقائمة السابقة.

\`\`\`json
{
  "buttonKey": "back_button",
  "textAr": "🔙 رجوع",
  "textEn": "🔙 Back",
  "buttonType": "back",
  "backBehavior": "step"
}
\`\`\`

### 6. cancel (إلغاء)
زر لإنهاء التدفق وحذف الرسالة.

\`\`\`json
{
  "buttonKey": "cancel_button",
  "textAr": "❌ إلغاء",
  "textEn": "❌ Cancel",
  "buttonType": "cancel"
}
\`\`\`

### 7. page_separator (فاصل صفحات)
يفصل الأزرار إلى صفحات متعددة.

\`\`\`json
{
  "buttonKey": "page_sep_1",
  "textAr": "---",
  "textEn": "---",
  "buttonType": "page_separator",
  "children": [
    // أزرار الصفحة التالية
  ]
}
\`\`\`

---

## حجم الأزرار / Button Sizes

### large (كبير)
الزر يأخذ سطر كامل.

\`\`\`json
{
  "buttonSize": "large"
}
\`\`\`

### small (صغير)
الزر يأخذ نصف سطر (يمكن وضع زرين في سطر واحد).

\`\`\`json
{
  "buttonSize": "small"
}
\`\`\`

---

## سلوك الرجوع / Back Behavior

### step (خطوة)
الرجوع للقائمة السابقة مباشرة.

\`\`\`json
{
  "backBehavior": "step"
}
\`\`\`

### root (الجذر)
الرجوع للقائمة الرئيسية مباشرة.

\`\`\`json
{
  "backBehavior": "root"
}
\`\`\`

---

## أمثلة كاملة / Complete Examples

### مثال 1: قائمة بروكسيات بسيطة

\`\`\`json
[
  {
    "buttonKey": "proxy_menu",
    "textAr": "🌐 البروكسيات",
    "textEn": "🌐 Proxies",
    "buttonType": "menu",
    "isEnabled": true,
    "messageAr": "اختر نوع البروكسي:",
    "messageEn": "Choose proxy type:",
    "orderIndex": 0,
    "icon": "🌐",
    "buttonSize": "large",
    "children": [
      {
        "buttonKey": "static_proxy",
        "textAr": "📍 بروكسي ثابت",
        "textEn": "📍 Static Proxy",
        "buttonType": "service",
        "isService": true,
        "price": 2.99,
        "askQuantity": true,
        "orderIndex": 0,
        "buttonSize": "large"
      },
      {
        "buttonKey": "rotating_proxy",
        "textAr": "🔄 بروكسي متغير",
        "textEn": "🔄 Rotating Proxy",
        "buttonType": "service",
        "isService": true,
        "price": 4.99,
        "askQuantity": false,
        "orderIndex": 1,
        "buttonSize": "large"
      }
    ]
  }
]
\`\`\`

### مثال 2: قائمة مع فواصل صفحات

\`\`\`json
[
  {
    "buttonKey": "countries_menu",
    "textAr": "🌍 اختر الدولة",
    "textEn": "🌍 Choose Country",
    "buttonType": "menu",
    "messageAr": "الدول المتاحة:",
    "messageEn": "Available countries:",
    "children": [
      {
        "buttonKey": "us",
        "textAr": "🇺🇸 أمريكا",
        "textEn": "🇺🇸 USA",
        "buttonType": "service",
        "isService": true,
        "price": 1.99,
        "orderIndex": 0
      },
      {
        "buttonKey": "uk",
        "textAr": "🇬🇧 بريطانيا",
        "textEn": "🇬🇧 UK",
        "buttonType": "service",
        "isService": true,
        "price": 1.99,
        "orderIndex": 1
      },
      {
        "buttonKey": "page_sep_1",
        "textAr": "---",
        "textEn": "---",
        "buttonType": "page_separator",
        "orderIndex": 2,
        "children": [
          {
            "buttonKey": "de",
            "textAr": "🇩🇪 ألمانيا",
            "textEn": "🇩🇪 Germany",
            "buttonType": "service",
            "isService": true,
            "price": 1.99,
            "orderIndex": 0
          },
          {
            "buttonKey": "fr",
            "textAr": "🇫🇷 فرنسا",
            "textEn": "🇫🇷 France",
            "buttonType": "service",
            "isService": true,
            "price": 1.99,
            "orderIndex": 1
          }
        ]
      }
    ]
  }
]
\`\`\`

### مثال 3: متجر كامل

\`\`\`json
[
  {
    "buttonKey": "store_main",
    "textAr": "🛒 المتجر",
    "textEn": "🛒 Store",
    "buttonType": "menu",
    "isEnabled": true,
    "messageAr": "مرحباً بك في متجرنا! اختر القسم:",
    "messageEn": "Welcome to our store! Choose a section:",
    "orderIndex": 0,
    "icon": "🛒",
    "buttonSize": "large",
    "children": [
      {
        "buttonKey": "proxies_section",
        "textAr": "🌐 البروكسيات",
        "textEn": "🌐 Proxies",
        "buttonType": "menu",
        "messageAr": "اختر نوع البروكسي:",
        "messageEn": "Choose proxy type:",
        "orderIndex": 0,
        "buttonSize": "small",
        "children": []
      },
      {
        "buttonKey": "accounts_section",
        "textAr": "👤 الحسابات",
        "textEn": "👤 Accounts",
        "buttonType": "menu",
        "messageAr": "اختر نوع الحساب:",
        "messageEn": "Choose account type:",
        "orderIndex": 1,
        "buttonSize": "small",
        "children": []
      }
    ]
  },
  {
    "buttonKey": "support",
    "textAr": "📞 الدعم الفني",
    "textEn": "📞 Support",
    "buttonType": "message",
    "messageAr": "للتواصل مع الدعم الفني:\\n📱 @support_username\\n📧 support@example.com",
    "messageEn": "To contact support:\\n📱 @support_username\\n📧 support@example.com",
    "orderIndex": 1,
    "icon": "📞",
    "buttonSize": "large"
  },
  {
    "buttonKey": "balance",
    "textAr": "💰 رصيدي",
    "textEn": "💰 My Balance",
    "buttonType": "message",
    "messageAr": "رصيدك الحالي: {balance}$",
    "messageEn": "Your current balance: {balance}$",
    "orderIndex": 2,
    "icon": "💰",
    "buttonSize": "small"
  },
  {
    "buttonKey": "orders",
    "textAr": "📦 طلباتي",
    "textEn": "📦 My Orders",
    "buttonType": "message",
    "messageAr": "سجل طلباتك:",
    "messageEn": "Your order history:",
    "orderIndex": 3,
    "icon": "📦",
    "buttonSize": "small"
  }
]
\`\`\`

---

## تنسيق الرسائل / Message Formatting

يمكن استخدام HTML في الرسائل:

\`\`\`json
{
  "messageAr": "<b>عنوان غامق</b>\\n<i>نص مائل</i>\\n<code>كود</code>\\n<a href='https://example.com'>رابط</a>",
  "messageEn": "<b>Bold title</b>\\n<i>Italic text</i>\\n<code>Code</code>\\n<a href='https://example.com'>Link</a>"
}
\`\`\`

### علامات HTML المدعومة:
- \`<b>\` أو \`<strong>\` - نص غامق
- \`<i>\` أو \`<em>\` - نص مائل
- \`<u>\` - نص مسطر
- \`<s>\` أو \`<strike>\` - نص مشطوب
- \`<code>\` - كود
- \`<pre>\` - كود متعدد الأسطر
- \`<a href="url">\` - رابط

---

## قواعد مهمة / Important Rules

1. **buttonKey فريد**: كل زر يجب أن يكون له معرف فريد لا يتكرر
2. **الترتيب**: استخدم orderIndex لترتيب الأزرار (0 = الأول)
3. **الأزرار الفرعية**: ضعها في مصفوفة children
4. **الأسعار**: استخدم أرقام عشرية (مثل 2.99)
5. **الأيقونات**: يمكن استخدام إيموجي أو تركها فارغة
6. **اللغات**: يجب ملء كل من textAr و textEn

---

## أوامر سريعة للذكاء الاصطناعي / Quick AI Commands

عند طلب إنشاء JSON من الذكاء الاصطناعي، استخدم هذه الصيغ:

### إضافة زر جديد:
"أضف زر خدمة باسم [الاسم] بسعر [السعر]$ في قائمة [اسم القائمة]"

### إضافة قائمة:
"أنشئ قائمة جديدة باسم [الاسم] تحتوي على [عدد] خدمات"

### تعديل زر:
"غير سعر زر [buttonKey] إلى [السعر الجديد]"

### حذف زر:
"احذف الزر [buttonKey] من الهيكل"

### إضافة فاصل صفحات:
"أضف فاصل صفحات بعد الزر رقم [الرقم] في قائمة [الاسم]"

### تغيير الترتيب:
"رتب الأزرار في قائمة [الاسم] حسب [المعيار]"

---

## ملاحظات ختامية / Final Notes

- تأكد من صحة بنية JSON قبل الاستيراد
- احتفظ بنسخة احتياطية دائماً
- اختبر التغييرات على نسخة تطويرية أولاً
- استخدم أدوات التحقق من JSON للتأكد من الصياغة

---

نهاية الدليل / End of Guide
`;

export default function JsonDocs() {
  const { language, t } = useLanguage();
  const { toast } = useToast();
  const [copied, setCopied] = useState(false);

  const handleDownload = () => {
    const blob = new Blob([jsonDocumentation], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "telegram-bot-json-instructions.txt";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    toast({
      title: language === "ar" ? "تم التحميل" : "Downloaded",
      description: language === "ar" ? "تم تحميل ملف التعليمات بنجاح" : "Instructions file downloaded successfully",
    });
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(jsonDocumentation);
      setCopied(true);
      toast({
        title: language === "ar" ? "تم النسخ" : "Copied",
        description: language === "ar" ? "تم نسخ التعليمات إلى الحافظة" : "Instructions copied to clipboard",
      });
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      toast({
        title: t("toast.error"),
        description: language === "ar" ? "فشل نسخ التعليمات" : "Failed to copy instructions",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="h-full relative">
      <Card className="h-full flex flex-col">
        <CardHeader className="flex-shrink-0">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <FileText className="w-5 h-5 text-primary" />
              </div>
              <div>
                <CardTitle>
                  {language === "ar" ? "دليل تعليمات JSON" : "JSON Instructions Guide"}
                </CardTitle>
                <CardDescription>
                  {language === "ar" 
                    ? "تعليمات شاملة لإنشاء ملفات JSON للبوت - مناسب للذكاء الاصطناعي" 
                    : "Comprehensive instructions for creating bot JSON files - AI-friendly"}
                </CardDescription>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopy}
              className="hidden sm:flex"
              data-testid="button-copy-docs"
            >
              {copied ? <Check className="w-4 h-4 ml-2" /> : <Copy className="w-4 h-4 ml-2" />}
              {copied ? (language === "ar" ? "تم النسخ" : "Copied") : (language === "ar" ? "نسخ" : "Copy")}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="flex-1 overflow-hidden p-0">
          <ScrollArea className="h-full px-6 pb-6">
            <div className="prose prose-sm dark:prose-invert max-w-none" dir="ltr">
              <pre className="whitespace-pre-wrap text-sm leading-relaxed font-mono bg-muted/50 p-4 rounded-lg overflow-x-auto">
                {jsonDocumentation}
              </pre>
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
      
      {/* Floating Download Button */}
      <Button
        onClick={handleDownload}
        className="fixed bottom-6 left-6 shadow-lg z-50 gap-2"
        size="lg"
        data-testid="button-download-docs"
      >
        <Download className="w-5 h-5" />
        {language === "ar" ? "تحميل كملف TXT" : "Download as TXT"}
      </Button>
    </div>
  );
}
