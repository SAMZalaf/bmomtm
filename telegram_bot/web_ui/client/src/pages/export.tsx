import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { Download, Copy, Check, FileJson } from "lucide-react";
import type { ButtonTree } from "@shared/schema";

export default function Export() {
  const { toast } = useToast();
  const [copied, setCopied] = useState(false);

  const { data: buttonTree, isLoading } = useQuery<ButtonTree>({
    queryKey: ["/api/buttons/tree"],
  });

  const jsonString = buttonTree ? JSON.stringify(buttonTree, null, 2) : "";

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(jsonString);
      setCopied(true);
      toast({
        title: "تم النسخ",
        description: "تم نسخ البيانات إلى الحافظة",
      });
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast({
        title: "خطأ",
        description: "فشل نسخ البيانات",
        variant: "destructive",
      });
    }
  };

  const handleDownload = () => {
    const blob = new Blob([jsonString], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `telegram-bot-buttons-${new Date().toISOString().split("T")[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    toast({
      title: "تم التحميل",
      description: "تم تحميل ملف JSON بنجاح",
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">تصدير الأزرار</h1>
        <p className="text-muted-foreground">تصدير شجرة الأزرار كملف JSON</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileJson className="w-5 h-5" />
            بيانات JSON
          </CardTitle>
          <CardDescription>
            يمكنك نسخ البيانات أو تحميلها كملف
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Button onClick={handleCopy} variant="outline" data-testid="button-copy">
              {copied ? (
                <Check className="w-4 h-4 ml-2" />
              ) : (
                <Copy className="w-4 h-4 ml-2" />
              )}
              {copied ? "تم النسخ" : "نسخ"}
            </Button>
            <Button onClick={handleDownload} data-testid="button-download">
              <Download className="w-4 h-4 ml-2" />
              تحميل كملف
            </Button>
          </div>

          <Textarea
            value={isLoading ? "جاري التحميل..." : jsonString}
            readOnly
            className="min-h-[400px] font-mono text-sm resize-y"
            dir="ltr"
            data-testid="textarea-json"
          />

          <div className="text-sm text-muted-foreground">
            عدد الأزرار الرئيسية: {buttonTree?.length ?? 0}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
