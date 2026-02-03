import { useState, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { queryClient, apiRequest } from "@/lib/queryClient";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { Upload, FileJson, AlertTriangle, Loader2 } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

export default function Import() {
  const { toast } = useToast();
  const [jsonInput, setJsonInput] = useState("");
  const [parseError, setParseError] = useState<string | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const importMutation = useMutation({
    mutationFn: async (data: unknown) => {
      return apiRequest("POST", "/api/buttons/import", { buttons: data });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/buttons/tree"] });
      setJsonInput("");
      setShowConfirm(false);
      toast({
        title: "تم الاستيراد",
        description: "تم استيراد الأزرار بنجاح",
      });
    },
    onError: () => {
      toast({
        title: "خطأ",
        description: "فشل استيراد الأزرار. تأكد من صحة البيانات.",
        variant: "destructive",
      });
    },
  });

  const validateJson = (input: string): boolean => {
    try {
      const parsed = JSON.parse(input);
      if (!Array.isArray(parsed)) {
        setParseError("البيانات يجب أن تكون مصفوفة من الأزرار");
        return false;
      }
      setParseError(null);
      return true;
    } catch {
      setParseError("صيغة JSON غير صحيحة");
      return false;
    }
  };

  const handleImport = () => {
    if (!validateJson(jsonInput)) return;
    setShowConfirm(true);
  };

  const confirmImport = () => {
    try {
      const parsed = JSON.parse(jsonInput);
      importMutation.mutate(parsed);
    } catch {
      toast({
        title: "خطأ",
        description: "فشل في قراءة البيانات",
        variant: "destructive",
      });
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      setJsonInput(content);
      validateJson(content);
    };
    reader.onerror = () => {
      toast({
        title: "خطأ",
        description: "فشل قراءة الملف",
        variant: "destructive",
      });
    };
    reader.readAsText(file);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">استيراد الأزرار</h1>
        <p className="text-muted-foreground">استيراد شجرة الأزرار من ملف JSON</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileJson className="w-5 h-5" />
            استيراد من JSON
          </CardTitle>
          <CardDescription>
            الصق بيانات JSON أو ارفع ملف
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
              data-testid="button-upload-file"
            >
              <Upload className="w-4 h-4 ml-2" />
              رفع ملف
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              onChange={handleFileUpload}
              className="hidden"
            />
          </div>

          <Textarea
            value={jsonInput}
            onChange={(e) => {
              setJsonInput(e.target.value);
              if (e.target.value) validateJson(e.target.value);
              else setParseError(null);
            }}
            placeholder='[{"buttonKey": "example", "textAr": "مثال", "textEn": "Example", ...}]'
            className="min-h-[300px] font-mono text-sm resize-y"
            dir="ltr"
            data-testid="textarea-import"
          />

          {parseError && (
            <div className="flex items-center gap-2 text-destructive text-sm">
              <AlertTriangle className="w-4 h-4" />
              {parseError}
            </div>
          )}

          <Button
            onClick={handleImport}
            disabled={!jsonInput || !!parseError || importMutation.isPending}
            data-testid="button-import"
          >
            {importMutation.isPending && (
              <Loader2 className="w-4 h-4 ml-2 animate-spin" />
            )}
            استيراد الأزرار
          </Button>

          <div className="p-4 bg-muted rounded-lg space-y-2">
            <h4 className="font-medium">ملاحظات مهمة:</h4>
            <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1">
              <li>سيتم استبدال جميع الأزرار الحالية بالأزرار المستوردة</li>
              <li>تأكد من صحة بنية JSON قبل الاستيراد</li>
              <li>يُنصح بتصدير الأزرار الحالية أولاً كنسخة احتياطية</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      <AlertDialog open={showConfirm} onOpenChange={setShowConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>تأكيد الاستيراد</AlertDialogTitle>
            <AlertDialogDescription>
              سيتم استبدال جميع الأزرار الحالية بالأزرار المستوردة.
              هل أنت متأكد من المتابعة؟
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>إلغاء</AlertDialogCancel>
            <AlertDialogAction onClick={confirmImport}>
              نعم، استيراد
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
