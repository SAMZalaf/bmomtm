import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { useLanguage } from "@/lib/language-context";
import { useToast } from "@/hooks/use-toast";
import { Globe, Palette } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";

export default function Settings() {
  const { language, setLanguage, t } = useLanguage();
  const { toast } = useToast();

  const handleLanguageChange = (value: string) => {
    setLanguage(value as "ar" | "en");
    toast({
      title: t("toast.languageChanged"),
      description: t("toast.languageChangedDesc"),
    });
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">{t("settings.title")}</h1>
      
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <Globe className="w-5 h-5 text-primary" />
            <div>
              <CardTitle>{t("settings.language")}</CardTitle>
              <CardDescription>{t("settings.languageDesc")}</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <RadioGroup
            value={language}
            onValueChange={handleLanguageChange}
            className="flex flex-col gap-3"
          >
            <div className="flex items-center gap-3 p-3 rounded-lg border hover-elevate cursor-pointer">
              <RadioGroupItem value="ar" id="lang-ar" data-testid="radio-lang-ar" />
              <Label htmlFor="lang-ar" className="flex-1 cursor-pointer flex items-center gap-2">
                <span className="text-lg">🇸🇦</span>
                <span>{t("settings.arabic")}</span>
              </Label>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-lg border hover-elevate cursor-pointer">
              <RadioGroupItem value="en" id="lang-en" data-testid="radio-lang-en" />
              <Label htmlFor="lang-en" className="flex-1 cursor-pointer flex items-center gap-2">
                <span className="text-lg">🇺🇸</span>
                <span>{t("settings.english")}</span>
              </Label>
            </div>
          </RadioGroup>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <Palette className="w-5 h-5 text-primary" />
            <div>
              <CardTitle>{t("settings.theme")}</CardTitle>
              <CardDescription>{t("settings.themeDesc")}</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <ThemeToggle />
          </div>
        </CardContent>
      </Card>

      <div className="mt-auto pt-10 text-center text-sm text-muted-foreground space-y-1">
        <p data-testid="text-developer-name">Mohamad Zalaf ©2025</p>
        <p data-testid="text-version">{t("settings.version")}: 1.1.1</p>
      </div>
    </div>
  );
}
