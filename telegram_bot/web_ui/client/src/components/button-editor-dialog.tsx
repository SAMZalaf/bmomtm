import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { z } from "zod";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { Loader2, Settings } from "lucide-react";
import type { Button as ButtonType } from "@shared/schema";

interface RepeatedButtonName {
  index: number;
  textAr: string;
  textEn: string;
  buttonKey: string;
}

const formSchema = z.object({
  buttonKey: z.string(),
  textAr: z.string(),
  textEn: z.string(),
  buttonType: z.enum(["menu", "service", "message", "link", "back", "cancel", "page_separator"]),
  isEnabled: z.boolean(),
  isHidden: z.boolean(),
  disabledMessage: z.string(),
  isService: z.boolean(),
  price: z.coerce.number().min(0, "السعر يجب أن يكون 0 أو أكثر"),
  askQuantity: z.boolean(),
  defaultQuantity: z.coerce.number().min(1, "الكمية الافتراضية يجب أن تكون 1 أو أكثر"),
  showBackOnQuantity: z.boolean(),
  showCancelOnQuantity: z.boolean(),
  backBehavior: z.enum(["step", "root"]),
  messageAr: z.string(),
  messageEn: z.string(),
  icon: z.string(),
  orderIndex: z.coerce.number(),
  buttonSize: z.enum(["large", "small"]),
  insertPosition: z.enum(["top", "center", "end"]),
  isRepeated: z.boolean(),
  repeatCount: z.coerce.number().min(1).max(50),
}).superRefine((data, ctx) => {
  // أزرار الرجوع والإلغاء وفاصل الصفحات لا تحتاج حقول إضافية
  if (data.buttonType !== "page_separator" && data.buttonType !== "back" && data.buttonType !== "cancel") {
    if (!data.buttonKey || data.buttonKey.trim() === "") {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "معرف الزر مطلوب",
        path: ["buttonKey"],
      });
    }
    if (!data.textAr || data.textAr.trim() === "") {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "النص العربي مطلوب",
        path: ["textAr"],
      });
    }
    if (!data.textEn || data.textEn.trim() === "") {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "النص الإنجليزي مطلوب",
        path: ["textEn"],
      });
    }
  }
});

type FormData = z.infer<typeof formSchema>;

interface ButtonEditorDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  button: ButtonType | null;
  parentId: number | null;
  parentIsRootLevel?: boolean;
  onSave: () => void;
}

const EMOJI_OPTIONS = [
  "", "📁", "📂", "🌐", "🧦", "💎", "🔥", "⭐", "🎯", "🚀",
  "💰", "💳", "🛒", "📱", "💻", "🔧", "⚙️", "📊", "📈", "🎁",
  "🏆", "✅", "❌", "⚡", "🔒", "🔓", "📍", "🗂️", "📋", "🔔",
  "💡", "📅", "📆", "🏢", "🗽", "🏛️", "🌲", "🏙️", "⛺", "🌴",
  "🌊", "🇺🇸", "🇬🇧", "🇩🇪", "🇫🇷", "🇨🇦", "🇦🇪", "🇸🇦", "🇪🇬", "🇯🇴",
  "🇱🇧", "🇸🇾", "🇮🇶", "🇰🇼", "🇶🇦", "🇧🇭", "🇴🇲", "🇾🇪", "🇵🇸", "🇲🇦",
  "🇹🇳", "🇩🇿", "🇱🇾", "🇸🇩", "🇮🇹", "🇪🇸", "🇳🇱", "🇧🇪", "🇨🇭", "🇦🇹",
  "🇵🇱", "🇷🇺", "🇺🇦", "🇹🇷", "🇮🇳", "🇨🇳", "🇯🇵", "🇰🇷", "🇧🇷", "🇲🇽",
  "🇦🇺", "🔄", "📞", "💬", "📧", "🌍", "🌎", "🌏", "💵", "💴",
  "💶", "💷", "🪙", "💲", "📦", "🎫", "🎟️", "🏷️", "📌", "🔗",
];

export function ButtonEditorDialog({
  open,
  onOpenChange,
  button,
  parentId,
  parentIsRootLevel = false,
  onSave,
}: ButtonEditorDialogProps) {
  const { toast } = useToast();
  const isEditing = !!button;

  const [isRepeatedMode, setIsRepeatedMode] = useState(false);
  const [repeatCount, setRepeatCount] = useState(2);
  const [showRepeatSettings, setShowRepeatSettings] = useState(false);
  const [repeatedButtonNames, setRepeatedButtonNames] = useState<RepeatedButtonName[]>([]);

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      buttonKey: "",
      textAr: "",
      textEn: "",
      buttonType: "menu",
      isEnabled: true,
      isHidden: false,
      disabledMessage: "هذه الخدمة متوقفة مؤقتاً",
      isService: false,
      price: 0,
      askQuantity: false,
      defaultQuantity: 1,
      showBackOnQuantity: true,
      showCancelOnQuantity: true,
      backBehavior: "root",
      messageAr: "",
      messageEn: "",
      icon: "",
      orderIndex: 0,
      buttonSize: "large",
      insertPosition: "end",
      isRepeated: false,
      repeatCount: 2,
    },
  });

  const isRootLevel = parentId === null;

  useEffect(() => {
    if (open) {
      setIsRepeatedMode(false);
      setRepeatCount(2);
      setShowRepeatSettings(false);
      setRepeatedButtonNames([]);
      if (button) {
        form.reset({
          buttonKey: button.buttonKey,
          textAr: button.textAr,
          textEn: button.textEn,
          buttonType: button.buttonType,
          isEnabled: button.isEnabled,
          isHidden: button.isHidden ?? false,
          disabledMessage: button.disabledMessage || "هذه الخدمة متوقفة مؤقتاً",
          isService: button.isService,
          price: button.price,
          askQuantity: button.askQuantity,
          defaultQuantity: button.defaultQuantity,
          showBackOnQuantity: button.showBackOnQuantity ?? true,
          showCancelOnQuantity: button.showCancelOnQuantity ?? true,
          backBehavior: button.backBehavior || "step",
          messageAr: button.messageAr,
          messageEn: button.messageEn,
          icon: button.icon || "",
          orderIndex: button.orderIndex,
          buttonSize: button.buttonSize || "large",
          insertPosition: "end",
          isRepeated: false,
          repeatCount: 2,
        });
      } else {
        form.reset({
          buttonKey: "",
          textAr: "",
          textEn: "",
          buttonType: "menu",
          isEnabled: true,
          isHidden: false,
          disabledMessage: "هذه الخدمة متوقفة مؤقتاً",
          isService: false,
          price: 0,
          askQuantity: false,
          defaultQuantity: 1,
          showBackOnQuantity: true,
          showCancelOnQuantity: true,
          backBehavior: "root",
          messageAr: "",
          messageEn: "",
          icon: "",
          orderIndex: 0,
          buttonSize: "large",
          insertPosition: "end",
          isRepeated: false,
          repeatCount: 2,
        });
      }
    }
  }, [open, button, form]);

  // تحديث أسماء الأزرار المكررة عند تغيير عدد التكرارات أو النص الأساسي
  useEffect(() => {
    if (isRepeatedMode && repeatCount > 0) {
      const baseKey = form.getValues("buttonKey") || "re_object";
      const baseTextAr = form.getValues("textAr") || "عنصر";
      const baseTextEn = form.getValues("textEn") || "Item";
      
      const newNames: RepeatedButtonName[] = [];
      for (let i = 1; i <= repeatCount; i++) {
        const existingName = repeatedButtonNames.find(n => n.index === i);
        newNames.push({
          index: i,
          textAr: existingName?.textAr || `${baseTextAr} ${i}`,
          textEn: existingName?.textEn || `${baseTextEn} ${i}`,
          buttonKey: existingName?.buttonKey || `${baseKey}_${i}`,
        });
      }
      setRepeatedButtonNames(newNames);
    }
  }, [isRepeatedMode, repeatCount]);

  const createMutation = useMutation({
    mutationFn: async (data: FormData) => {
      return apiRequest("POST", "/api/buttons", {
        ...data,
        parentId,
      });
    },
    onSuccess: () => {
      toast({
        title: "تم الإنشاء",
        description: "تم إنشاء الزر بنجاح",
      });
      onSave();
    },
    onError: () => {
      toast({
        title: "خطأ",
        description: "فشل إنشاء الزر",
        variant: "destructive",
      });
    },
  });

  const updateMutation = useMutation({
    mutationFn: async (data: FormData) => {
      return apiRequest("PATCH", `/api/buttons/${button!.id}`, data);
    },
    onSuccess: () => {
      toast({
        title: "تم التحديث",
        description: "تم تحديث الزر بنجاح",
      });
      onSave();
    },
    onError: () => {
      toast({
        title: "خطأ",
        description: "فشل تحديث الزر",
        variant: "destructive",
      });
    },
  });

  // Mutation لإنشاء عدة أزرار دفعة واحدة
  const batchCreateMutation = useMutation({
    mutationFn: async (buttons: any[]) => {
      return apiRequest("POST", "/api/buttons/batch", { buttons });
    },
    onSuccess: (_, variables) => {
      toast({
        title: "تم الإنشاء",
        description: `تم إنشاء ${variables.length} أزرار بنجاح`,
      });
      onSave();
    },
    onError: () => {
      toast({
        title: "خطأ",
        description: "فشل إنشاء الأزرار",
        variant: "destructive",
      });
    },
  });

  const onSubmit = (data: FormData) => {
    const processedData = { ...data };
    
    // تحويل "none" إلى سلسلة فارغة للأيقونة
    if (processedData.icon === "none") {
      processedData.icon = "";
    }
    
    // معالجة زر الرابط - نسخ URL إلى كلا الحقلين
    if (data.buttonType === "link") {
      processedData.messageEn = processedData.messageAr;
    }
    
    // معالجة فاصل الصفحات
    if (data.buttonType === "page_separator") {
      processedData.buttonKey = `page_sep_${Date.now()}`;
      processedData.textAr = "---";
      processedData.textEn = "---";
      processedData.isService = false;
      processedData.icon = "";
    }
    
    // معالجة زر الرجوع
    if (data.buttonType === "back") {
      processedData.buttonKey = `back_${Date.now()}`;
      processedData.textAr = "🔙 رجوع";
      processedData.textEn = "🔙 Back";
      processedData.icon = "🔙";
      processedData.orderIndex = 9998;
      processedData.isEnabled = true;
      processedData.isHidden = false;
      processedData.isService = false;
      processedData.messageAr = "";
      processedData.messageEn = "";
      processedData.buttonSize = "small";
    }
    
    // معالجة زر الإلغاء
    if (data.buttonType === "cancel") {
      processedData.buttonKey = `cancel_${Date.now()}`;
      processedData.textAr = "❌ إلغاء";
      processedData.textEn = "❌ Cancel";
      processedData.icon = "❌";
      processedData.orderIndex = 9999;
      processedData.isEnabled = true;
      processedData.isHidden = false;
      processedData.isService = false;
      processedData.messageAr = "";
      processedData.messageEn = "";
      processedData.buttonSize = "small";
    }
    
    if (isEditing) {
      updateMutation.mutate(processedData);
    } else if (isRepeatedMode && repeatedButtonNames.length > 0) {
      // إنشاء أزرار متعددة
      const buttonsToCreate = repeatedButtonNames.map((btnName, idx) => ({
        ...processedData,
        buttonKey: btnName.buttonKey,
        textAr: btnName.textAr,
        textEn: btnName.textEn,
        orderIndex: processedData.orderIndex + idx,
        parentId,
      }));
      batchCreateMutation.mutate(buttonsToCreate);
    } else {
      createMutation.mutate(processedData);
    }
  };

  const isLoading = createMutation.isPending || updateMutation.isPending || batchCreateMutation.isPending;
  const isService = form.watch("isService");
  const buttonType = form.watch("buttonType");
  const askQuantity = form.watch("askQuantity");
  const watchIsEnabled = form.watch("isEnabled");

  useEffect(() => {
    if (buttonType === "service") {
      form.setValue("isService", true);
    }
  }, [buttonType, form]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isEditing 
              ? (buttonType === "page_separator" ? "تعديل فاصل الصفحات" : "تعديل الزر")
              : (buttonType === "page_separator" ? "إضافة فاصل صفحات" : "إضافة زر جديد")}
          </DialogTitle>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <FormField
              control={form.control}
              name="buttonType"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>نوع العنصر</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    value={field.value}
                  >
                    <FormControl>
                      <SelectTrigger data-testid="select-button-type">
                        <SelectValue placeholder="اختر نوع العنصر أولاً" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="menu">قائمة - يفتح قائمة فرعية</SelectItem>
                      <SelectItem value="service">خدمة - منتج قابل للشراء</SelectItem>
                      <SelectItem value="message">رسالة - يرسل رسالة فقط</SelectItem>
                      <SelectItem value="link">رابط - يفتح رابط خارجي</SelectItem>
                      <SelectItem value="back">رجوع - يرجع للخلف</SelectItem>
                      <SelectItem value="cancel">إلغاء - ينهي التدفق</SelectItem>
                      <SelectItem value="page_separator">فاصل صفحات - لتقسيم الأزرار</SelectItem>
                    </SelectContent>
                  </Select>
                  {(buttonType === "back" || buttonType === "cancel") && (
                    <FormDescription>
                      أزرار الرجوع والإلغاء يتم ترتيبها تلقائياً في النهاية
                    </FormDescription>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />

            {buttonType !== "page_separator" && buttonType !== "back" && buttonType !== "cancel" && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="buttonKey"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>معرف الزر (فريد)</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="مثال: static_proxy"
                          {...field}
                          data-testid="input-button-key"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="icon"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>الأيقونة</FormLabel>
                      <Select
                        onValueChange={field.onChange}
                        value={field.value}
                      >
                        <FormControl>
                          <SelectTrigger data-testid="select-icon">
                            <SelectValue placeholder="اختر أيقونة" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <div className="grid grid-cols-6 gap-2 p-2 max-h-60 overflow-y-auto">
                            {EMOJI_OPTIONS.map((emoji, index) => (
                              <SelectItem
                                key={emoji || "none"}
                                value={emoji || "none"}
                                className="text-center text-xl cursor-pointer"
                              >
                                {emoji || "—"}
                              </SelectItem>
                            ))}
                          </div>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            )}

            {buttonType !== "page_separator" && buttonType !== "back" && buttonType !== "cancel" && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="textAr"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>النص العربي</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="اسم الزر بالعربية"
                          {...field}
                          data-testid="input-text-ar"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="textEn"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>النص الإنجليزي</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Button name in English"
                          dir="ltr"
                          {...field}
                          data-testid="input-text-en"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            )}

            {buttonType !== "page_separator" && buttonType !== "back" && buttonType !== "cancel" && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="buttonSize"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>حجم الزر</FormLabel>
                      <Select
                        onValueChange={field.onChange}
                        value={field.value}
                      >
                        <FormControl>
                          <SelectTrigger data-testid="select-button-size">
                            <SelectValue placeholder="اختر حجم الزر" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="large">كبير - سطر كامل</SelectItem>
                          <SelectItem value="small">صغير - نصف سطر</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormDescription>
                        الحجم الكبير يملأ سطر كامل، الصغير نصف سطر
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {(isRootLevel || parentIsRootLevel) && !isEditing && (
                  <FormField
                    control={form.control}
                    name="insertPosition"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>موقع الإضافة</FormLabel>
                        <Select
                          onValueChange={field.onChange}
                          value={field.value}
                        >
                          <FormControl>
                            <SelectTrigger data-testid="select-insert-position">
                              <SelectValue placeholder="اختر موقع الإضافة" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="top">أعلى - في بداية الكيبورد</SelectItem>
                            <SelectItem value="center">وسط - في منتصف الكيبورد</SelectItem>
                            <SelectItem value="end">نهاية - في آخر الكيبورد</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormDescription>
                          {isRootLevel ? "أين سيظهر الزر الجديد في الكيبورد الرئيسي" : "أين سيظهر الزر الجديد في هذه القائمة"}
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                )}
              </div>
            )}

            {/* خيار العنصر المكرر - فقط عند الإضافة وليس التعديل */}
            {!isEditing && buttonType !== "page_separator" && buttonType !== "back" && buttonType !== "cancel" && (
              <div className="space-y-4 p-4 rounded-lg border-2 border-yellow-400 bg-yellow-50 dark:bg-yellow-900/20">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Switch
                      checked={isRepeatedMode}
                      onCheckedChange={setIsRepeatedMode}
                      className="data-[state=checked]:bg-yellow-500"
                      data-testid="switch-repeated"
                    />
                    <div>
                      <p className="font-medium text-sm">عنصر مكرر</p>
                      <p className="text-xs text-muted-foreground">إنشاء عدة أزرار متشابهة دفعة واحدة</p>
                    </div>
                  </div>
                  {isRepeatedMode && (
                    <div className="flex items-center gap-2">
                      <Input
                        type="number"
                        min="2"
                        max="50"
                        value={repeatCount}
                        onChange={(e) => setRepeatCount(Math.min(50, Math.max(2, parseInt(e.target.value) || 2)))}
                        className="w-20 h-8"
                        data-testid="input-repeat-count"
                      />
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => setShowRepeatSettings(!showRepeatSettings)}
                        data-testid="button-repeat-settings"
                      >
                        <Settings className="w-4 h-4" />
                      </Button>
                    </div>
                  )}
                </div>

                {/* Settings Panel - Editable Names - مطابق لنسخ العنصر */}
                {isRepeatedMode && showRepeatSettings && (
                  <div className="mt-4 space-y-3">
                    <Label className="text-sm font-medium">
                      إعدادات الأسماء والمفاتيح
                    </Label>
                    <ScrollArea className="h-64 rounded-lg border">
                      <div className="p-3 space-y-4">
                        {repeatedButtonNames.map((btnName, idx) => (
                          <div key={btnName.index} className="space-y-2 p-3 bg-muted/50 rounded-lg">
                            {/* Separator line */}
                            <div className="flex items-center gap-2 text-muted-foreground text-xs">
                              <div className="flex-1 h-px bg-yellow-400/60" />
                              <span>_-_</span>
                              <div className="flex-1 h-px bg-yellow-400/60" />
                            </div>
                            
                            {/* Key Field */}
                            <div className="space-y-1">
                              <Label className="text-xs text-yellow-600 dark:text-yellow-400">
                                المفتاح
                              </Label>
                              <Input
                                value={btnName.buttonKey}
                                onChange={(e) => {
                                  const newNames = [...repeatedButtonNames];
                                  newNames[idx] = { ...newNames[idx], buttonKey: e.target.value };
                                  setRepeatedButtonNames(newNames);
                                }}
                                className="text-sm font-mono border-yellow-300"
                                dir="ltr"
                                data-testid={`input-repeated-key-${idx}`}
                              />
                            </div>
                            
                            {/* Names Row */}
                            <div className="grid grid-cols-2 gap-3">
                              {/* English Name - Left */}
                              <div className="space-y-1">
                                <Label className="text-xs text-muted-foreground">EN</Label>
                                <Input
                                  value={btnName.textEn}
                                  onChange={(e) => {
                                    const newNames = [...repeatedButtonNames];
                                    newNames[idx] = { ...newNames[idx], textEn: e.target.value };
                                    setRepeatedButtonNames(newNames);
                                  }}
                                  className="text-sm"
                                  dir="ltr"
                                  data-testid={`input-repeated-en-${idx}`}
                                />
                              </div>
                              
                              {/* Arabic Name - Right */}
                              <div className="space-y-1">
                                <Label className="text-xs text-muted-foreground">عربي</Label>
                                <Input
                                  value={btnName.textAr}
                                  onChange={(e) => {
                                    const newNames = [...repeatedButtonNames];
                                    newNames[idx] = { ...newNames[idx], textAr: e.target.value };
                                    setRepeatedButtonNames(newNames);
                                  }}
                                  className="text-sm"
                                  dir="rtl"
                                  data-testid={`input-repeated-ar-${idx}`}
                                />
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </ScrollArea>
                  </div>
                )}
              </div>
            )}

            {buttonType !== "page_separator" && buttonType !== "back" && buttonType !== "cancel" && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="isEnabled"
                  render={({ field }) => (
                    <FormItem className="flex items-center justify-between rounded-lg border p-4">
                      <div className="space-y-0.5">
                        <FormLabel>تفعيل الزر</FormLabel>
                        <FormDescription>
                          عند التعطيل لن يعمل الزر
                        </FormDescription>
                      </div>
                      <FormControl>
                        <Switch
                          checked={field.value}
                          onCheckedChange={field.onChange}
                          data-testid="switch-enabled"
                        />
                      </FormControl>
                    </FormItem>
                  )}
                />

                {!watchIsEnabled && (
                  <FormField
                    control={form.control}
                    name="disabledMessage"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>رسالة عند اختيار الزر المعطل</FormLabel>
                        <FormControl>
                          <Textarea
                            {...field}
                            dir="rtl"
                            placeholder="هذه الخدمة متوقفة مؤقتاً"
                            data-testid="input-disabled-message"
                          />
                        </FormControl>
                        <FormDescription>
                          الرسالة التي سيتم إرسالها للمستخدم عند الضغط على الزر المعطل
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                )}

                <FormField
                  control={form.control}
                  name="isHidden"
                  render={({ field }) => (
                    <FormItem className="flex items-center justify-between rounded-lg border p-4">
                      <div className="space-y-0.5">
                        <FormLabel>إخفاء الزر</FormLabel>
                        <FormDescription>
                          عند التفعيل لن يظهر الزر للمستخدمين
                        </FormDescription>
                      </div>
                      <FormControl>
                        <Switch
                          checked={field.value}
                          onCheckedChange={field.onChange}
                          data-testid="switch-hidden"
                        />
                      </FormControl>
                    </FormItem>
                  )}
                />
              </div>
            )}

            {buttonType === "page_separator" && (
              <div className="space-y-4">
                <FormField
                  control={form.control}
                  name="orderIndex"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>ترتيب العرض</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min="0"
                          {...field}
                          data-testid="input-order-index"
                        />
                      </FormControl>
                      <FormDescription>
                        الرقم الأصغر يظهر أولاً (الافتراضي: من الأقدم للأحدث)
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                
                <FormField
                  control={form.control}
                  name="isEnabled"
                  render={({ field }) => (
                    <FormItem className="flex items-center justify-between rounded-lg border p-4">
                      <div className="space-y-0.5">
                        <FormLabel>تفعيل فاصل الصفحة</FormLabel>
                        <FormDescription>
                          عند التعطيل لن يعمل الفاصل
                        </FormDescription>
                      </div>
                      <FormControl>
                        <Switch
                          checked={field.value}
                          onCheckedChange={field.onChange}
                          data-testid="switch-enabled-separator"
                        />
                      </FormControl>
                    </FormItem>
                  )}
                />
                
                <FormField
                  control={form.control}
                  name="isHidden"
                  render={({ field }) => (
                    <FormItem className="flex items-center justify-between rounded-lg border p-4">
                      <div className="space-y-0.5">
                        <FormLabel>إخفاء فاصل الصفحة</FormLabel>
                        <FormDescription>
                          عند التفعيل لن يظهر الفاصل وتفرعاته في البوت
                        </FormDescription>
                      </div>
                      <FormControl>
                        <Switch
                          checked={field.value}
                          onCheckedChange={field.onChange}
                          data-testid="switch-hidden-separator"
                        />
                      </FormControl>
                    </FormItem>
                  )}
                />
              </div>
            )}

            {(buttonType === "service" || buttonType === "menu" || buttonType === "message" || buttonType === "link") && (
              <FormField
                control={form.control}
                name="isService"
                render={({ field }) => (
                  <FormItem className="flex items-center justify-between rounded-lg border p-4">
                    <div className="space-y-0.5">
                      <FormLabel>خدمة مدفوعة</FormLabel>
                      <FormDescription>
                        تحديد سعر للخدمة
                      </FormDescription>
                    </div>
                    <FormControl>
                      <Switch
                        checked={field.value}
                        onCheckedChange={field.onChange}
                        data-testid="switch-service"
                      />
                    </FormControl>
                  </FormItem>
                )}
              />
            )}

            {isService && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-muted/50 rounded-lg">
                <FormField
                  control={form.control}
                  name="price"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>السعر ($)</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          step="0.01"
                          min="0"
                          {...field}
                          data-testid="input-price"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="askQuantity"
                  render={({ field }) => (
                    <FormItem className="flex items-center justify-between rounded-lg border bg-background p-4">
                      <div className="space-y-0.5">
                        <FormLabel>طلب الكمية</FormLabel>
                      </div>
                      <FormControl>
                        <Switch
                          checked={field.value}
                          onCheckedChange={field.onChange}
                          data-testid="switch-ask-quantity"
                        />
                      </FormControl>
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="defaultQuantity"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>الكمية الافتراضية</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min="1"
                          {...field}
                          data-testid="input-default-quantity"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {askQuantity && (
                  <>
                    <FormField
                      control={form.control}
                      name="showBackOnQuantity"
                      render={({ field }) => (
                        <FormItem className="flex items-center justify-between rounded-lg border bg-background p-4">
                          <div className="space-y-0.5">
                            <FormLabel>زر رجوع عند الكمية</FormLabel>
                          </div>
                          <FormControl>
                            <Switch
                              checked={field.value}
                              onCheckedChange={field.onChange}
                              data-testid="switch-back-on-quantity"
                            />
                          </FormControl>
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="showCancelOnQuantity"
                      render={({ field }) => (
                        <FormItem className="flex items-center justify-between rounded-lg border bg-background p-4">
                          <div className="space-y-0.5">
                            <FormLabel>زر إلغاء عند الكمية</FormLabel>
                          </div>
                          <FormControl>
                            <Switch
                              checked={field.value}
                              onCheckedChange={field.onChange}
                              data-testid="switch-cancel-on-quantity"
                            />
                          </FormControl>
                        </FormItem>
                      )}
                    />
                  </>
                )}
              </div>
            )}

            {buttonType === "back" && (
              <FormField
                control={form.control}
                name="backBehavior"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>سلوك الرجوع</FormLabel>
                    <Select
                      onValueChange={field.onChange}
                      value={field.value}
                    >
                      <FormControl>
                        <SelectTrigger data-testid="select-back-behavior">
                          <SelectValue placeholder="اختر سلوك الرجوع" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="step">رجوع خطوة واحدة للخلف</SelectItem>
                        <SelectItem value="root">رجوع للقائمة الرئيسية مباشرة</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      حدد إلى أين يرجع المستخدم عند الضغط على هذا الزر
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

            {/* URL field for link buttons */}
            {buttonType === "link" && (
              <div className="space-y-4">
                <div className="space-y-3 p-4 rounded-lg border bg-muted/30">
                  <FormLabel>نوع الرابط</FormLabel>
                  <div className="grid grid-cols-2 gap-2">
                    <Button
                      type="button"
                      variant={form.watch("messageAr")?.startsWith("https://t.me/") ? "default" : "outline"}
                      size="sm"
                      onClick={() => {
                        form.setValue("messageAr", "https://t.me/");
                      }}
                      data-testid="btn-link-telegram"
                    >
                      📱 تيليغرام
                    </Button>
                    <Button
                      type="button"
                      variant={form.watch("messageAr")?.startsWith("https://instagram.com/") || form.watch("messageAr")?.startsWith("https://www.instagram.com/") ? "default" : "outline"}
                      size="sm"
                      onClick={() => {
                        form.setValue("messageAr", "https://instagram.com/");
                      }}
                      data-testid="btn-link-instagram"
                    >
                      📷 إنستغرام
                    </Button>
                    <Button
                      type="button"
                      variant={form.watch("messageAr")?.startsWith("https://facebook.com/") || form.watch("messageAr")?.startsWith("https://www.facebook.com/") ? "default" : "outline"}
                      size="sm"
                      onClick={() => {
                        form.setValue("messageAr", "https://facebook.com/");
                      }}
                      data-testid="btn-link-facebook"
                    >
                      👥 فيسبوك
                    </Button>
                    <Button
                      type="button"
                      variant={!form.watch("messageAr")?.startsWith("https://t.me/") && !form.watch("messageAr")?.startsWith("https://instagram.com/") && !form.watch("messageAr")?.startsWith("https://www.instagram.com/") && !form.watch("messageAr")?.startsWith("https://facebook.com/") && !form.watch("messageAr")?.startsWith("https://www.facebook.com/") ? "default" : "outline"}
                      size="sm"
                      onClick={() => {
                        form.setValue("messageAr", "https://");
                      }}
                      data-testid="btn-link-web"
                    >
                      🌐 صفحة ويب
                    </Button>
                  </div>
                </div>
                
                <FormField
                  control={form.control}
                  name="messageAr"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>الرابط الكامل</FormLabel>
                      <FormControl>
                        <Input
                          type="url"
                          placeholder="أكمل الرابط هنا..."
                          dir="ltr"
                          {...field}
                          data-testid="input-link-url"
                        />
                      </FormControl>
                      <FormDescription>
                        {form.watch("messageAr")?.startsWith("https://t.me/") && "أضف اسم القناة أو المستخدم بعد https://t.me/"}
                        {form.watch("messageAr")?.startsWith("https://instagram.com/") && "أضف اسم الحساب بعد https://instagram.com/"}
                        {form.watch("messageAr")?.startsWith("https://facebook.com/") && "أضف اسم الصفحة بعد https://facebook.com/"}
                        {!form.watch("messageAr")?.startsWith("https://t.me/") && !form.watch("messageAr")?.startsWith("https://instagram.com/") && !form.watch("messageAr")?.startsWith("https://facebook.com/") && "أدخل الرابط الكامل"}
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            )}

            {/* Message fields for other button types */}
            {(buttonType === "menu" || buttonType === "service" || buttonType === "message" || buttonType === "page_separator") && (
              <div className="space-y-4">
                <FormField
                  control={form.control}
                  name="messageAr"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>
                        {buttonType === "page_separator" ? "رسالة الصفحة بالعربية" : "الرسالة العربية"}
                      </FormLabel>
                      <FormControl>
                        <Textarea
                          placeholder={buttonType === "page_separator" 
                            ? "الرسالة التي ستظهر في هذه الصفحة..."
                            : "الرسالة التي ستظهر عند الضغط على الزر..."}
                          className="min-h-24 resize-y"
                          {...field}
                          data-testid="textarea-message-ar"
                        />
                      </FormControl>
                      <FormDescription>
                        {buttonType === "page_separator" 
                          ? "هذه الرسالة ستظهر فوق أزرار هذه الصفحة"
                          : "يمكنك استخدام HTML للتنسيق"}
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="messageEn"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>
                        {buttonType === "page_separator" ? "رسالة الصفحة بالإنجليزية" : "الرسالة الإنجليزية"}
                      </FormLabel>
                      <FormControl>
                        <Textarea
                          placeholder={buttonType === "page_separator"
                            ? "Message that will appear on this page..."
                            : "Message that appears when button is clicked..."}
                          className="min-h-24 resize-y"
                          dir="ltr"
                          {...field}
                          data-testid="textarea-message-en"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            )}

            {buttonType !== "back" && buttonType !== "cancel" && buttonType !== "page_separator" && (
              <FormField
                control={form.control}
                name="orderIndex"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>ترتيب العرض</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min="0"
                        {...field}
                        data-testid="input-order-index"
                      />
                    </FormControl>
                    <FormDescription>
                      الأرقام الأصغر تظهر أولاً
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

            <DialogFooter className="gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isLoading}
              >
                إلغاء
              </Button>
              <Button type="submit" disabled={isLoading} data-testid="button-save">
                {isLoading && <Loader2 className="w-4 h-4 ml-2 animate-spin" />}
                {isEditing 
                  ? "حفظ التعديلات" 
                  : (buttonType === "page_separator" ? "إضافة الفاصل" : "إضافة الزر")}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
