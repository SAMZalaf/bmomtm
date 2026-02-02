import { createContext, useContext, useState, useEffect, type ReactNode } from "react";

type Language = "ar" | "en";

interface Translations {
  [key: string]: {
    ar: string;
    en: string;
  };
}

const translations: Translations = {
  // Header
  "header.title": {
    ar: "لوحة تحكم البوت",
    en: "Bot Control Panel",
  },
  "header.running": {
    ar: "يعمل",
    en: "Running",
  },
  "header.stopped": {
    ar: "متوقف",
    en: "Stopped",
  },
  "header.restart": {
    ar: "إعادة تشغيل",
    en: "Restart",
  },
  "header.seconds": {
    ar: "ث",
    en: "s",
  },
  
  // Sidebar
  "sidebar.title": {
    ar: "بوت تيليغرام",
    en: "Telegram Bot",
  },
  "sidebar.subtitle": {
    ar: "إدارة الأزرار",
    en: "Button Management",
  },
  "sidebar.mainMenu": {
    ar: "القائمة الرئيسية",
    en: "Main Menu",
  },
  "sidebar.tools": {
    ar: "الأدوات",
    en: "Tools",
  },
  "sidebar.dashboard": {
    ar: "لوحة التحكم",
    en: "Dashboard",
  },
  "sidebar.settings": {
    ar: "الإعدادات",
    en: "Settings",
  },
  "sidebar.export": {
    ar: "تصدير JSON",
    en: "Export JSON",
  },
  "sidebar.import": {
    ar: "استيراد JSON",
    en: "Import JSON",
  },
  "sidebar.version": {
    ar: "إصدار",
    en: "Version",
  },
  "sidebar.jsonDocs": {
    ar: "دليل JSON",
    en: "JSON Guide",
  },
  
  // Settings Page
  "settings.title": {
    ar: "الإعدادات",
    en: "Settings",
  },
  "settings.language": {
    ar: "اللغة",
    en: "Language",
  },
  "settings.languageDesc": {
    ar: "اختر لغة الواجهة",
    en: "Choose interface language",
  },
  "settings.arabic": {
    ar: "العربية",
    en: "Arabic",
  },
  "settings.english": {
    ar: "الإنجليزية",
    en: "English",
  },
  "settings.appearance": {
    ar: "المظهر",
    en: "Appearance",
  },
  "settings.theme": {
    ar: "السمة",
    en: "Theme",
  },
  "settings.themeDesc": {
    ar: "اختر السمة المفضلة",
    en: "Choose preferred theme",
  },
  "settings.developer": {
    ar: "المطور",
    en: "Developer",
  },
  "settings.version": {
    ar: "الإصدار",
    en: "Version",
  },
  
  // Dashboard Stats
  "dashboard.totalButtons": {
    ar: "إجمالي الأزرار",
    en: "Total Buttons",
  },
  "dashboard.enabledButtons": {
    ar: "الأزرار المفعلة",
    en: "Enabled Buttons",
  },
  "dashboard.services": {
    ar: "الخدمات",
    en: "Services",
  },
  "dashboard.buttonExplorer": {
    ar: "مستكشف الأزرار",
    en: "Button Explorer",
  },
  "dashboard.preview": {
    ar: "المعاينة",
    en: "Preview",
  },
  "dashboard.newButton": {
    ar: "عنصر جديد",
    en: "New Item",
  },
  "dashboard.noButtonsYet": {
    ar: "لا توجد عناصر بعد",
    en: "No items yet",
  },
  "dashboard.startAddingButton": {
    ar: "ابدأ بإضافة أول عنصر لبوت التيليغرام",
    en: "Start by adding your first item for the Telegram bot",
  },
  "dashboard.addNewButton": {
    ar: "إضافة عنصر جديد",
    en: "Add New Item",
  },
  
  // Dashboard - Tree Node Actions
  "dashboard.editButton": {
    ar: "تعديل العنصر",
    en: "Edit Item",
  },
  "dashboard.addChildButton": {
    ar: "إضافة عنصر فرعي",
    en: "Add Child Item",
  },
  "dashboard.copyButton": {
    ar: "نسخ الزر",
    en: "Copy Button",
  },
  "dashboard.disableButton": {
    ar: "إيقاف الزر",
    en: "Disable Button",
  },
  "dashboard.enableButton": {
    ar: "تفعيل الزر",
    en: "Enable Button",
  },
  "dashboard.deleteButton": {
    ar: "حذف الزر",
    en: "Delete Button",
  },
  "dashboard.edit": {
    ar: "تعديل",
    en: "Edit",
  },
  
  // Dashboard - Tooltips
  "dashboard.asksQuantity": {
    ar: "يطلب كمية",
    en: "Asks for quantity",
  },
  "dashboard.paidService": {
    ar: "خدمة مدفوعة",
    en: "Paid service",
  },
  
  // Dashboard - Selected Button Details
  "dashboard.key": {
    ar: "المفتاح:",
    en: "Key:",
  },
  "dashboard.type": {
    ar: "النوع:",
    en: "Type:",
  },
  "dashboard.price": {
    ar: "السعر:",
    en: "Price:",
  },
  "dashboard.status": {
    ar: "الحالة:",
    en: "Status:",
  },
  "dashboard.enabled": {
    ar: "مفعل",
    en: "Enabled",
  },
  "dashboard.disabled": {
    ar: "معطل",
    en: "Disabled",
  },
  "dashboard.message": {
    ar: "الرسالة:",
    en: "Message:",
  },
  
  // Button Types
  "buttonType.menu": {
    ar: "قائمة",
    en: "Menu",
  },
  "buttonType.service": {
    ar: "خدمة",
    en: "Service",
  },
  "buttonType.message": {
    ar: "رسالة",
    en: "Message",
  },
  "buttonType.link": {
    ar: "رابط",
    en: "Link",
  },
  "buttonType.back": {
    ar: "رجوع",
    en: "Back",
  },
  "buttonType.cancel": {
    ar: "إلغاء",
    en: "Cancel",
  },
  "buttonType.pageSeparator": {
    ar: "فاصل صفحات",
    en: "Page Separator",
  },
  "dashboard.pagesCount": {
    ar: "صفحات",
    en: "pages",
  },
  
  // Button Editor Dialog
  "editor.title.add": {
    ar: "إضافة عنصر جديد",
    en: "Add New Item",
  },
  "editor.title.edit": {
    ar: "تعديل العنصر",
    en: "Edit Item",
  },
  "editor.buttonKey": {
    ar: "معرف الزر (فريد)",
    en: "Button ID (unique)",
  },
  "editor.buttonKeyPlaceholder": {
    ar: "مثال: static_proxy",
    en: "Example: static_proxy",
  },
  "editor.icon": {
    ar: "الأيقونة",
    en: "Icon",
  },
  "editor.selectIcon": {
    ar: "اختر أيقونة",
    en: "Select an icon",
  },
  "editor.textAr": {
    ar: "النص العربي",
    en: "Arabic Text",
  },
  "editor.textArPlaceholder": {
    ar: "اسم الزر بالعربية",
    en: "Button name in Arabic",
  },
  "editor.textEn": {
    ar: "النص الإنجليزي",
    en: "English Text",
  },
  "editor.textEnPlaceholder": {
    ar: "Button name in English",
    en: "Button name in English",
  },
  "editor.buttonType": {
    ar: "نوع الزر",
    en: "Button Type",
  },
  "editor.selectButtonType": {
    ar: "اختر نوع الزر",
    en: "Select button type",
  },
  "editor.menuDesc": {
    ar: "قائمة - يفتح قائمة فرعية",
    en: "Menu - Opens a sub-menu",
  },
  "editor.serviceDesc": {
    ar: "خدمة - منتج قابل للشراء",
    en: "Service - Purchasable product",
  },
  "editor.messageDesc": {
    ar: "رسالة - يرسل رسالة فقط",
    en: "Message - Sends a message only",
  },
  "editor.linkDesc": {
    ar: "رابط - يفتح رابط خارجي",
    en: "Link - Opens an external link",
  },
  "editor.backDesc": {
    ar: "رجوع - يرجع للخلف درجة واحدة",
    en: "Back - Goes back one step",
  },
  "editor.cancelDesc": {
    ar: "إلغاء - ينهي التدفق ويحذف الرسالة",
    en: "Cancel - Ends the flow and deletes the message",
  },
  "editor.buttonTypeNote": {
    ar: "أزرار الرجوع والإلغاء يتم ترتيبها تلقائياً في النهاية (الإلغاء يكون الأخير)",
    en: "Back and Cancel buttons are automatically ordered at the end (Cancel is last)",
  },
  "editor.buttonSize": {
    ar: "حجم الزر",
    en: "Button Size",
  },
  "editor.selectButtonSize": {
    ar: "اختر حجم الزر",
    en: "Select button size",
  },
  "editor.sizeLarge": {
    ar: "كبير - سطر كامل",
    en: "Large - Full row",
  },
  "editor.sizeSmall": {
    ar: "صغير - نصف سطر",
    en: "Small - Half row",
  },
  "editor.sizeNote": {
    ar: "الحجم الكبير يملأ سطر كامل، الصغير نصف سطر",
    en: "Large size fills a full row, small fills half a row",
  },
  "editor.insertPosition": {
    ar: "موقع الإضافة",
    en: "Insert Position",
  },
  "editor.selectInsertPosition": {
    ar: "اختر موقع الإضافة",
    en: "Select insert position",
  },
  "editor.positionTop": {
    ar: "أعلى - في بداية الكيبورد",
    en: "Top - At the beginning of the keyboard",
  },
  "editor.positionCenter": {
    ar: "وسط - في منتصف الكيبورد",
    en: "Center - In the middle of the keyboard",
  },
  "editor.positionEnd": {
    ar: "نهاية - في آخر الكيبورد",
    en: "End - At the end of the keyboard",
  },
  "editor.positionNote": {
    ar: "أين سيظهر الزر الجديد في الكيبورد الرئيسي",
    en: "Where the new button will appear in the main keyboard",
  },
  "editor.enableButton": {
    ar: "تفعيل الزر",
    en: "Enable Button",
  },
  "editor.enableButtonDesc": {
    ar: "عند التعطيل لن يظهر الزر للمستخدمين",
    en: "When disabled, the button won't appear to users",
  },
  "editor.paidService": {
    ar: "خدمة مدفوعة",
    en: "Paid Service",
  },
  "editor.paidServiceDesc": {
    ar: "تحديد سعر للخدمة",
    en: "Set a price for the service",
  },
  "editor.price": {
    ar: "السعر ($)",
    en: "Price ($)",
  },
  "editor.askQuantity": {
    ar: "طلب الكمية",
    en: "Ask Quantity",
  },
  "editor.defaultQuantity": {
    ar: "الكمية الافتراضية",
    en: "Default Quantity",
  },
  "editor.backOnQuantity": {
    ar: "زر رجوع عند الكمية",
    en: "Back button on quantity",
  },
  "editor.cancelOnQuantity": {
    ar: "زر إلغاء عند الكمية",
    en: "Cancel button on quantity",
  },
  "editor.backBehavior": {
    ar: "سلوك الرجوع",
    en: "Back Behavior",
  },
  "editor.selectBackBehavior": {
    ar: "اختر سلوك الرجوع",
    en: "Select back behavior",
  },
  "editor.backStep": {
    ar: "رجوع خطوة واحدة للخلف",
    en: "Go back one step",
  },
  "editor.backRoot": {
    ar: "رجوع للقائمة الرئيسية مباشرة",
    en: "Go directly to main menu",
  },
  "editor.backBehaviorNote": {
    ar: "حدد إلى أين يرجع المستخدم عند الضغط على هذا الزر",
    en: "Specify where the user goes when pressing this button",
  },
  "editor.messageAr": {
    ar: "الرسالة العربية",
    en: "Arabic Message",
  },
  "editor.messageArPlaceholder": {
    ar: "الرسالة التي ستظهر عند اختيار هذا الزر (بالعربية)",
    en: "Message displayed when this button is selected (in Arabic)",
  },
  "editor.messageEn": {
    ar: "الرسالة الإنجليزية",
    en: "English Message",
  },
  "editor.messageEnPlaceholder": {
    ar: "Message displayed when this button is selected (in English)",
    en: "Message displayed when this button is selected (in English)",
  },
  "editor.htmlNote": {
    ar: "يمكنك استخدام HTML للتنسيق",
    en: "You can use HTML for formatting",
  },
  "editor.cancel": {
    ar: "إلغاء",
    en: "Cancel",
  },
  "editor.addButton": {
    ar: "إضافة العنصر",
    en: "Add Item",
  },
  "editor.saveChanges": {
    ar: "حفظ التعديلات",
    en: "Save Changes",
  },
  
  // Editor Validation Messages
  "validation.buttonKeyRequired": {
    ar: "معرف الزر مطلوب",
    en: "Button ID is required",
  },
  "validation.textArRequired": {
    ar: "النص العربي مطلوب",
    en: "Arabic text is required",
  },
  "validation.textEnRequired": {
    ar: "النص الإنجليزي مطلوب",
    en: "English text is required",
  },
  "validation.priceMin": {
    ar: "السعر يجب أن يكون 0 أو أكثر",
    en: "Price must be 0 or more",
  },
  "validation.quantityMin": {
    ar: "الكمية الافتراضية يجب أن تكون 1 أو أكثر",
    en: "Default quantity must be 1 or more",
  },
  
  // Delete Dialog
  "delete.title": {
    ar: "تأكيد الحذف",
    en: "Confirm Delete",
  },
  "delete.message": {
    ar: "هل أنت متأكد من حذف الزر",
    en: "Are you sure you want to delete the button",
  },
  "delete.warning": {
    ar: "سيتم حذف جميع الأزرار الفرعية أيضاً. هذا الإجراء لا يمكن التراجع عنه.",
    en: "All child buttons will also be deleted. This action cannot be undone.",
  },
  "delete.confirm": {
    ar: "نعم، احذف",
    en: "Yes, Delete",
  },
  "delete.cancel": {
    ar: "إلغاء",
    en: "Cancel",
  },
  
  // Telegram Preview
  "preview.title": {
    ar: "معاينة التيليغرام",
    en: "Telegram Preview",
  },
  "preview.botName": {
    ar: "بوت المتجر",
    en: "Store Bot",
  },
  "preview.onlineNow": {
    ar: "متصل الآن",
    en: "Online now",
  },
  "preview.mainMenu": {
    ar: "القائمة الرئيسية",
    en: "Main Menu",
  },
  "preview.welcomeMessage": {
    ar: "مرحباً بك في البوت! اختر من القائمة أدناه:",
    en: "Welcome to the bot! Choose from the menu below:",
  },
  "preview.selectFrom": {
    ar: "اختر من",
    en: "Select from",
  },
  "preview.noButtons": {
    ar: "لا توجد أزرار",
    en: "No buttons",
  },
  "preview.typeMessage": {
    ar: "اكتب رسالة...",
    en: "Type a message...",
  },
  
  // Export Page
  "export.title": {
    ar: "تصدير الأزرار",
    en: "Export Buttons",
  },
  "export.description": {
    ar: "تصدير شجرة الأزرار كملف JSON",
    en: "Export button tree as JSON file",
  },
  "export.jsonData": {
    ar: "بيانات JSON",
    en: "JSON Data",
  },
  "export.copyOrDownload": {
    ar: "يمكنك نسخ البيانات أو تحميلها كملف",
    en: "You can copy the data or download it as a file",
  },
  "export.copy": {
    ar: "نسخ",
    en: "Copy",
  },
  "export.copied": {
    ar: "تم النسخ",
    en: "Copied",
  },
  "export.download": {
    ar: "تحميل كملف",
    en: "Download as file",
  },
  "export.loading": {
    ar: "جاري التحميل...",
    en: "Loading...",
  },
  "export.rootButtonsCount": {
    ar: "عدد الأزرار الرئيسية:",
    en: "Root buttons count:",
  },
  
  // Import Page
  "import.title": {
    ar: "استيراد الأزرار",
    en: "Import Buttons",
  },
  "import.description": {
    ar: "استيراد شجرة الأزرار من ملف JSON",
    en: "Import button tree from JSON file",
  },
  "import.fromJson": {
    ar: "استيراد من JSON",
    en: "Import from JSON",
  },
  "import.pasteOrUpload": {
    ar: "الصق بيانات JSON أو ارفع ملف",
    en: "Paste JSON data or upload a file",
  },
  "import.uploadFile": {
    ar: "رفع ملف",
    en: "Upload File",
  },
  "import.importButtons": {
    ar: "استيراد الأزرار",
    en: "Import Buttons",
  },
  "import.importantNotes": {
    ar: "ملاحظات مهمة:",
    en: "Important notes:",
  },
  "import.note1": {
    ar: "سيتم استبدال جميع الأزرار الحالية بالأزرار المستوردة",
    en: "All current buttons will be replaced with imported buttons",
  },
  "import.note2": {
    ar: "تأكد من صحة بنية JSON قبل الاستيراد",
    en: "Make sure the JSON structure is valid before importing",
  },
  "import.note3": {
    ar: "يُنصح بتصدير الأزرار الحالية أولاً كنسخة احتياطية",
    en: "It is recommended to export current buttons first as a backup",
  },
  "import.confirmTitle": {
    ar: "تأكيد الاستيراد",
    en: "Confirm Import",
  },
  "import.confirmMessage": {
    ar: "سيتم استبدال جميع الأزرار الحالية بالأزرار المستوردة. هل أنت متأكد من المتابعة؟",
    en: "All current buttons will be replaced with imported buttons. Are you sure you want to continue?",
  },
  "import.yesImport": {
    ar: "نعم، استيراد",
    en: "Yes, Import",
  },
  "import.cancel": {
    ar: "إلغاء",
    en: "Cancel",
  },
  "import.errorArray": {
    ar: "البيانات يجب أن تكون مصفوفة من الأزرار",
    en: "Data must be an array of buttons",
  },
  "import.errorJson": {
    ar: "صيغة JSON غير صحيحة",
    en: "Invalid JSON format",
  },
  
  // Toast Messages
  "toast.updated": {
    ar: "تم التحديث",
    en: "Updated",
  },
  "toast.buttonStatusUpdated": {
    ar: "تم تحديث حالة الزر بنجاح",
    en: "Button status updated successfully",
  },
  "toast.buttonSizeUpdated": {
    ar: "تم تغيير حجم الزر بنجاح",
    en: "Button size changed successfully",
  },
  "toast.error": {
    ar: "خطأ",
    en: "Error",
  },
  "toast.buttonStatusError": {
    ar: "فشل تحديث حالة الزر",
    en: "Failed to update button status",
  },
  "toast.buttonSizeError": {
    ar: "فشل تغيير حجم الزر",
    en: "Failed to change button size",
  },
  "toast.deleted": {
    ar: "تم الحذف",
    en: "Deleted",
  },
  "toast.buttonDeleted": {
    ar: "تم حذف الزر بنجاح",
    en: "Button deleted successfully",
  },
  "toast.buttonDeleteError": {
    ar: "فشل حذف الزر",
    en: "Failed to delete button",
  },
  "toast.created": {
    ar: "تم الإنشاء",
    en: "Created",
  },
  "toast.buttonCreated": {
    ar: "تم إنشاء الزر بنجاح",
    en: "Button created successfully",
  },
  "toast.buttonCreateError": {
    ar: "فشل إنشاء الزر",
    en: "Failed to create button",
  },
  "toast.buttonUpdated": {
    ar: "تم تحديث الزر بنجاح",
    en: "Button updated successfully",
  },
  "toast.buttonUpdateError": {
    ar: "فشل تحديث الزر",
    en: "Failed to update button",
  },
  "toast.dataCopied": {
    ar: "تم نسخ البيانات إلى الحافظة",
    en: "Data copied to clipboard",
  },
  "toast.copyError": {
    ar: "فشل نسخ البيانات",
    en: "Failed to copy data",
  },
  "toast.downloaded": {
    ar: "تم التحميل",
    en: "Downloaded",
  },
  "toast.fileDownloaded": {
    ar: "تم تحميل ملف JSON بنجاح",
    en: "JSON file downloaded successfully",
  },
  "toast.imported": {
    ar: "تم الاستيراد",
    en: "Imported",
  },
  "toast.buttonsImported": {
    ar: "تم استيراد الأزرار بنجاح",
    en: "Buttons imported successfully",
  },
  "toast.importError": {
    ar: "فشل استيراد الأزرار. تأكد من صحة البيانات.",
    en: "Failed to import buttons. Make sure the data is valid.",
  },
  "toast.fileReadError": {
    ar: "فشل قراءة الملف",
    en: "Failed to read file",
  },
  "toast.dataReadError": {
    ar: "فشل في قراءة البيانات",
    en: "Failed to read data",
  },
  "toast.botStopped": {
    ar: "تم إيقاف البوت",
    en: "Bot Stopped",
  },
  "toast.botStarted": {
    ar: "تم تشغيل البوت",
    en: "Bot Started",
  },
  "toast.botStoppedDesc": {
    ar: "تم إيقاف البوت للمستخدمين العاديين (الآدمنز لا يتأثرون)",
    en: "Bot stopped for regular users (Admins are not affected)",
  },
  "toast.botStartedDesc": {
    ar: "البوت يعمل الآن لجميع المستخدمين",
    en: "Bot is now running for all users",
  },
  "toast.botToggleError": {
    ar: "فشل في تغيير حالة البوت",
    en: "Failed to change bot status",
  },
  "toast.restartTitle": {
    ar: "إعادة تشغيل البوت",
    en: "Bot Restart",
  },
  "toast.restartDesc": {
    ar: "سيتم إعادة تشغيل البوت خلال 15 ثانية",
    en: "Bot will restart in 15 seconds",
  },
  "toast.restartError": {
    ar: "فشل في إعادة تشغيل البوت",
    en: "Failed to restart bot",
  },
  "toast.syncTitle": {
    ar: "تم المزامنة",
    en: "Synced",
  },
  "toast.syncDesc": {
    ar: "تم تحديث بيانات الواجهة من البوت",
    en: "Interface data synced from bot",
  },
  "toast.syncError": {
    ar: "فشل في مزامنة البيانات",
    en: "Failed to sync data",
  },
  "header.sync": {
    ar: "مزامنة",
    en: "Sync",
  },
  "header.syncing": {
    ar: "جاري...",
    en: "Syncing...",
  },
  "header.applyChanges": {
    ar: "إعادة التشغيل",
    en: "Restart and Apply Changes",
  },
  "toast.languageChanged": {
    ar: "تم تغيير اللغة",
    en: "Language Changed",
  },
  "toast.languageChangedDesc": {
    ar: "تم تغيير لغة الواجهة بنجاح",
    en: "Interface language changed successfully",
  },
  
  // Common
  "common.copy": {
    ar: "(نسخة)",
    en: "(copy)",
  },
  
  // Help Page
  "sidebar.help": {
    ar: "دليل الاستخدام",
    en: "User Guide",
  },
  "help.title": {
    ar: "دليل استخدام لوحة التحكم",
    en: "Control Panel User Guide",
  },
  "help.subtitle": {
    ar: "تعرف على كيفية استخدام جميع ميزات لوحة التحكم",
    en: "Learn how to use all control panel features",
  },
  "help.dashboard.title": {
    ar: "لوحة التحكم الرئيسية",
    en: "Main Dashboard",
  },
  "help.dashboard.desc": {
    ar: "الصفحة الرئيسية لإدارة جميع الأزرار والخدمات في البوت",
    en: "The main page for managing all bot buttons and services",
  },
  "help.dashboard.stats": {
    ar: "الإحصائيات",
    en: "Statistics",
  },
  "help.dashboard.statsDesc": {
    ar: "في أعلى الصفحة تجد إحصائيات سريعة عن عدد الأزرار الإجمالي، الأزرار المفعلة، عدد الخدمات، وعدد القوائم الفرعية",
    en: "At the top of the page you'll find quick statistics about total buttons, enabled buttons, services count, and sub-menus count",
  },
  "help.dashboard.tree": {
    ar: "شجرة الأزرار",
    en: "Button Tree",
  },
  "help.dashboard.treeDesc": {
    ar: "تعرض جميع الأزرار بشكل هرمي. يمكنك النقر على أي زر لتعديله أو عرض أزراره الفرعية",
    en: "Displays all buttons hierarchically. You can click any button to edit it or view its child buttons",
  },
  "help.dashboard.preview": {
    ar: "معاينة تيليغرام",
    en: "Telegram Preview",
  },
  "help.dashboard.previewDesc": {
    ar: "على الجانب الأيسر (أو الأيمن في الإنجليزية) تجد معاينة لشكل الأزرار كما ستظهر في تيليغرام",
    en: "On the left side (or right in English) you'll find a preview of how buttons will appear in Telegram",
  },
  "help.buttons.title": {
    ar: "إدارة الأزرار",
    en: "Button Management",
  },
  "help.buttons.add": {
    ar: "إضافة عنصر جديد",
    en: "Add New Item",
  },
  "help.buttons.addDesc": {
    ar: "اضغط على زر '+' بجانب أي عنصر لإضافة عنصر فرعي جديد، أو استخدم زر 'إضافة عنصر رئيسي' لإضافة عنصر في المستوى الأول",
    en: "Click the '+' button next to any item to add a new child item, or use 'Add Root Item' to add an item at the first level",
  },
  "help.buttons.edit": {
    ar: "تعديل زر",
    en: "Edit Button",
  },
  "help.buttons.editDesc": {
    ar: "اضغط على أي زر لفتح نافذة التعديل. يمكنك تغيير الاسم (بالعربية والإنجليزية)، السعر، النوع، والإعدادات الأخرى",
    en: "Click any button to open the edit dialog. You can change the name (Arabic and English), price, type, and other settings",
  },
  "help.buttons.delete": {
    ar: "حذف زر",
    en: "Delete Button",
  },
  "help.buttons.deleteDesc": {
    ar: "اضغط على أيقونة سلة المهملات لحذف زر. سيتم حذف جميع الأزرار الفرعية أيضاً",
    en: "Click the trash icon to delete a button. All child buttons will also be deleted",
  },
  "help.buttons.reorder": {
    ar: "إعادة ترتيب الأزرار",
    en: "Reorder Buttons",
  },
  "help.buttons.reorderDesc": {
    ar: "استخدم أزرار الأسهم لتحريك الأزرار لأعلى أو لأسفل لتغيير ترتيب ظهورها",
    en: "Use the arrow buttons to move buttons up or down to change their display order",
  },
  "help.buttons.toggle": {
    ar: "تفعيل/تعطيل زر",
    en: "Enable/Disable Button",
  },
  "help.buttons.toggleDesc": {
    ar: "استخدم مفتاح التبديل لتفعيل أو تعطيل أي زر. الأزرار المعطلة لن تظهر في البوت",
    en: "Use the toggle switch to enable or disable any button. Disabled buttons won't appear in the bot",
  },
  "help.buttonTypes.title": {
    ar: "أنواع الأزرار",
    en: "Button Types",
  },
  "help.buttonTypes.menu": {
    ar: "قائمة (Menu)",
    en: "Menu",
  },
  "help.buttonTypes.menuDesc": {
    ar: "زر يحتوي على أزرار فرعية. عند الضغط عليه يعرض قائمة بالخيارات المتاحة",
    en: "A button containing child buttons. When clicked, it shows a list of available options",
  },
  "help.buttonTypes.service": {
    ar: "خدمة (Service)",
    en: "Service",
  },
  "help.buttonTypes.serviceDesc": {
    ar: "زر خدمة مدفوعة. يمكن تحديد السعر وسؤال المستخدم عن الكمية المطلوبة",
    en: "A paid service button. You can set the price and ask the user for the desired quantity",
  },
  "help.buttonTypes.message": {
    ar: "رسالة (Message)",
    en: "Message",
  },
  "help.buttonTypes.messageDesc": {
    ar: "زر يعرض رسالة نصية فقط بدون إنشاء طلب",
    en: "A button that only displays a text message without creating an order",
  },
  "help.buttonTypes.link": {
    ar: "رابط (Link)",
    en: "Link",
  },
  "help.buttonTypes.linkDesc": {
    ar: "زر يفتح رابط خارجي عند الضغط عليه. يمكن استخدامه لتوجيه المستخدمين لمواقع خارجية",
    en: "A button that opens an external link when clicked. Can be used to direct users to external websites",
  },
  "help.buttonTypes.back": {
    ar: "رجوع (Back)",
    en: "Back",
  },
  "help.buttonTypes.backDesc": {
    ar: "زر للرجوع للقائمة السابقة. يمكن تحديد سلوك الرجوع (خطوة واحدة أو للقائمة الرئيسية)",
    en: "A button to go back to the previous menu. You can set the back behavior (one step or to the main menu)",
  },
  "help.buttonTypes.cancel": {
    ar: "إلغاء (Cancel)",
    en: "Cancel",
  },
  "help.buttonTypes.cancelDesc": {
    ar: "زر لإلغاء العملية الحالية والعودة للقائمة الرئيسية",
    en: "A button to cancel the current operation and return to the main menu",
  },
  "help.buttonTypes.pageSeparator": {
    ar: "فاصل صفحات (Page Separator)",
    en: "Page Separator",
  },
  "help.buttonTypes.pageSeparatorDesc": {
    ar: "زر غير مرئي يستخدم لتقسيم الأزرار إلى صفحات. الأزرار بعد الفاصل ستظهر في صفحة جديدة مع أزرار التنقل",
    en: "An invisible button used to split buttons into pages. Buttons after the separator will appear on a new page with navigation controls",
  },
  "help.botControl.title": {
    ar: "التحكم بالبوت",
    en: "Bot Control",
  },
  "help.botControl.status": {
    ar: "حالة البوت",
    en: "Bot Status",
  },
  "help.botControl.statusDesc": {
    ar: "الزر الأخضر 'يعمل' يعني أن البوت نشط. اضغط عليه لإيقاف البوت مؤقتاً (المدراء لا يتأثرون)",
    en: "The green 'Running' button means the bot is active. Click to temporarily stop the bot (admins are not affected)",
  },
  "help.botControl.restart": {
    ar: "إعادة التشغيل",
    en: "Restart",
  },
  "help.botControl.restartDesc": {
    ar: "اضغط على 'إعادة تشغيل' لإيقاف البوت 15 ثانية ثم تشغيله تلقائياً. مفيد لتطبيق التغييرات",
    en: "Click 'Restart' to stop the bot for 15 seconds then automatically start it. Useful for applying changes",
  },
  "help.exportImport.title": {
    ar: "التصدير والاستيراد",
    en: "Export & Import",
  },
  "help.exportImport.export": {
    ar: "تصدير البيانات",
    en: "Export Data",
  },
  "help.exportImport.exportDesc": {
    ar: "من صفحة 'تصدير JSON' يمكنك حفظ نسخة احتياطية من جميع الأزرار في ملف JSON",
    en: "From the 'Export JSON' page you can save a backup of all buttons in a JSON file",
  },
  "help.exportImport.import": {
    ar: "استيراد البيانات",
    en: "Import Data",
  },
  "help.exportImport.importDesc": {
    ar: "من صفحة 'استيراد JSON' يمكنك استعادة الأزرار من ملف JSON سابق. انتبه: هذا سيستبدل جميع الأزرار الحالية",
    en: "From the 'Import JSON' page you can restore buttons from a previous JSON file. Note: This will replace all current buttons",
  },
  "help.settings.title": {
    ar: "الإعدادات",
    en: "Settings",
  },
  "help.settings.language": {
    ar: "تغيير اللغة",
    en: "Change Language",
  },
  "help.settings.languageDesc": {
    ar: "يمكنك تغيير لغة الواجهة بين العربية والإنجليزية من صفحة الإعدادات",
    en: "You can switch the interface language between Arabic and English from the Settings page",
  },
  "help.settings.theme": {
    ar: "تغيير السمة",
    en: "Change Theme",
  },
  "help.settings.themeDesc": {
    ar: "استخدم زر الشمس/القمر في الأعلى للتبديل بين الوضع الفاتح والداكن",
    en: "Use the sun/moon button at the top to switch between light and dark mode",
  },
  "help.tips.title": {
    ar: "نصائح مهمة",
    en: "Important Tips",
  },
  "help.tips.tip1": {
    ar: "احفظ نسخة احتياطية بشكل دوري باستخدام ميزة التصدير",
    en: "Regularly save a backup using the export feature",
  },
  "help.tips.tip2": {
    ar: "تأكد من إضافة اسم الزر باللغتين العربية والإنجليزية لدعم جميع المستخدمين",
    en: "Make sure to add button names in both Arabic and English to support all users",
  },
  "help.tips.tip3": {
    ar: "استخدم المعاينة للتأكد من شكل الأزرار قبل تفعيلها",
    en: "Use the preview to check button appearance before enabling them",
  },
  "help.tips.tip4": {
    ar: "الأزرار المعطلة لا تظهر للمستخدمين لكنها محفوظة ويمكن تفعيلها لاحقاً",
    en: "Disabled buttons are not visible to users but are saved and can be enabled later",
  },
  "help.tips.tip5": {
    ar: "عند حذف زر رئيسي، سيتم حذف جميع أزراره الفرعية تلقائياً",
    en: "When deleting a parent button, all its child buttons will be automatically deleted",
  },
  
  // Dashboard - Zoom
  "dashboard.zoomIn": {
    ar: "تكبير",
    en: "Zoom In",
  },
  "dashboard.zoomOut": {
    ar: "تصغير",
    en: "Zoom Out",
  },
  "dashboard.expandAll": {
    ar: "توسيع الكل",
    en: "Expand All",
  },
  "dashboard.collapseAll": {
    ar: "طي الكل",
    en: "Collapse All",
  },
  "dashboard.itemsCount": {
    ar: "عناصر",
    en: "items",
  },
  
  // Drag and Drop
  "dashboard.moveButton": {
    ar: "نقل العنصر",
    en: "Move Item",
  },
  "toast.buttonMoved": {
    ar: "تم نقل العنصر بنجاح",
    en: "Item moved successfully",
  },
  "toast.buttonMoveError": {
    ar: "فشل نقل العنصر",
    en: "Failed to move item",
  },
};

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string) => string;
  dir: "rtl" | "ltr";
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => {
    const saved = localStorage.getItem("language");
    return (saved as Language) || "ar";
  });

  useEffect(() => {
    localStorage.setItem("language", language);
    document.documentElement.dir = language === "ar" ? "rtl" : "ltr";
    document.documentElement.lang = language;
  }, [language]);

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
  };

  const t = (key: string): string => {
    const translation = translations[key];
    if (!translation) {
      console.warn(`Translation missing for key: ${key}`);
      return key;
    }
    return translation[language];
  };

  const dir = language === "ar" ? "rtl" : "ltr";

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t, dir }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (context === undefined) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
}
