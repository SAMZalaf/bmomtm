import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useLanguage } from "@/lib/language-context";
import {
  LayoutDashboard,
  MousePointer2,
  Plus,
  Edit,
  Trash2,
  ArrowUpDown,
  ToggleLeft,
  Menu,
  ShoppingCart,
  MessageSquare,
  Power,
  RotateCcw,
  Download,
  Upload,
  Globe,
  Palette,
  Lightbulb,
  BarChart3,
  GitBranch,
  Eye,
  Link,
  ArrowLeft,
  XCircle,
  MoreHorizontal,
} from "lucide-react";

interface HelpSectionProps {
  icon: React.ReactNode;
  title: string;
  description?: string;
  children: React.ReactNode;
}

function HelpSection({ icon, title, description, children }: HelpSectionProps) {
  return (
    <Card className="mb-6" data-testid={`help-section-${title.toLowerCase().replace(/\s/g, '-')}`}>
      <CardHeader>
        <CardTitle className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
            {icon}
          </div>
          {title}
        </CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent className="space-y-4">
        {children}
      </CardContent>
    </Card>
  );
}

interface HelpItemProps {
  icon: React.ReactNode;
  title: string;
  description: string;
}

function HelpItem({ icon, title, description }: HelpItemProps) {
  return (
    <div className="flex gap-4 p-3 rounded-lg bg-muted/50">
      <div className="w-8 h-8 rounded-md bg-background flex items-center justify-center shrink-0">
        {icon}
      </div>
      <div>
        <h4 className="font-medium mb-1">{title}</h4>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}

export default function Help() {
  const { t } = useLanguage();

  return (
    <div className="max-w-4xl mx-auto" data-testid="page-help">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2" data-testid="text-help-title">{t("help.title")}</h1>
        <p className="text-muted-foreground" data-testid="text-help-subtitle">{t("help.subtitle")}</p>
      </div>

      <HelpSection
        icon={<LayoutDashboard className="w-5 h-5 text-primary" />}
        title={t("help.dashboard.title")}
        description={t("help.dashboard.desc")}
      >
        <HelpItem
          icon={<BarChart3 className="w-4 h-4 text-blue-500" />}
          title={t("help.dashboard.stats")}
          description={t("help.dashboard.statsDesc")}
        />
        <HelpItem
          icon={<GitBranch className="w-4 h-4 text-green-500" />}
          title={t("help.dashboard.tree")}
          description={t("help.dashboard.treeDesc")}
        />
        <HelpItem
          icon={<Eye className="w-4 h-4 text-purple-500" />}
          title={t("help.dashboard.preview")}
          description={t("help.dashboard.previewDesc")}
        />
      </HelpSection>

      <HelpSection
        icon={<MousePointer2 className="w-5 h-5 text-primary" />}
        title={t("help.buttons.title")}
      >
        <HelpItem
          icon={<Plus className="w-4 h-4 text-green-500" />}
          title={t("help.buttons.add")}
          description={t("help.buttons.addDesc")}
        />
        <HelpItem
          icon={<Edit className="w-4 h-4 text-blue-500" />}
          title={t("help.buttons.edit")}
          description={t("help.buttons.editDesc")}
        />
        <HelpItem
          icon={<Trash2 className="w-4 h-4 text-red-500" />}
          title={t("help.buttons.delete")}
          description={t("help.buttons.deleteDesc")}
        />
        <HelpItem
          icon={<ArrowUpDown className="w-4 h-4 text-orange-500" />}
          title={t("help.buttons.reorder")}
          description={t("help.buttons.reorderDesc")}
        />
        <HelpItem
          icon={<ToggleLeft className="w-4 h-4 text-purple-500" />}
          title={t("help.buttons.toggle")}
          description={t("help.buttons.toggleDesc")}
        />
      </HelpSection>

      <HelpSection
        icon={<Menu className="w-5 h-5 text-primary" />}
        title={t("help.buttonTypes.title")}
      >
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <div className="p-4 rounded-lg border bg-card">
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="outline" className="bg-blue-500/10 text-blue-600 border-blue-500/30">
                <Menu className="w-3 h-3 me-1" />
                {t("help.buttonTypes.menu")}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">{t("help.buttonTypes.menuDesc")}</p>
          </div>
          <div className="p-4 rounded-lg border bg-card">
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="outline" className="bg-green-500/10 text-green-600 border-green-500/30">
                <ShoppingCart className="w-3 h-3 me-1" />
                {t("help.buttonTypes.service")}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">{t("help.buttonTypes.serviceDesc")}</p>
          </div>
          <div className="p-4 rounded-lg border bg-card">
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="outline" className="bg-purple-500/10 text-purple-600 border-purple-500/30">
                <MessageSquare className="w-3 h-3 me-1" />
                {t("help.buttonTypes.message")}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">{t("help.buttonTypes.messageDesc")}</p>
          </div>
          <div className="p-4 rounded-lg border bg-card">
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="outline" className="bg-cyan-500/10 text-cyan-600 border-cyan-500/30">
                <Link className="w-3 h-3 me-1" />
                {t("help.buttonTypes.link")}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">{t("help.buttonTypes.linkDesc")}</p>
          </div>
          <div className="p-4 rounded-lg border bg-card">
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="outline" className="bg-amber-500/10 text-amber-600 border-amber-500/30">
                <ArrowLeft className="w-3 h-3 me-1" />
                {t("help.buttonTypes.back")}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">{t("help.buttonTypes.backDesc")}</p>
          </div>
          <div className="p-4 rounded-lg border bg-card">
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="outline" className="bg-red-500/10 text-red-600 border-red-500/30">
                <XCircle className="w-3 h-3 me-1" />
                {t("help.buttonTypes.cancel")}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">{t("help.buttonTypes.cancelDesc")}</p>
          </div>
          <div className="p-4 rounded-lg border bg-card md:col-span-2 lg:col-span-3">
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="outline" className="bg-orange-500/10 text-orange-600 border-orange-500/30">
                <MoreHorizontal className="w-3 h-3 me-1" />
                {t("help.buttonTypes.pageSeparator")}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">{t("help.buttonTypes.pageSeparatorDesc")}</p>
          </div>
        </div>
      </HelpSection>

      <HelpSection
        icon={<Power className="w-5 h-5 text-primary" />}
        title={t("help.botControl.title")}
      >
        <HelpItem
          icon={<Power className="w-4 h-4 text-green-500" />}
          title={t("help.botControl.status")}
          description={t("help.botControl.statusDesc")}
        />
        <HelpItem
          icon={<RotateCcw className="w-4 h-4 text-blue-500" />}
          title={t("help.botControl.restart")}
          description={t("help.botControl.restartDesc")}
        />
      </HelpSection>

      <HelpSection
        icon={<Download className="w-5 h-5 text-primary" />}
        title={t("help.exportImport.title")}
      >
        <HelpItem
          icon={<Download className="w-4 h-4 text-green-500" />}
          title={t("help.exportImport.export")}
          description={t("help.exportImport.exportDesc")}
        />
        <HelpItem
          icon={<Upload className="w-4 h-4 text-blue-500" />}
          title={t("help.exportImport.import")}
          description={t("help.exportImport.importDesc")}
        />
      </HelpSection>

      <HelpSection
        icon={<Globe className="w-5 h-5 text-primary" />}
        title={t("help.settings.title")}
      >
        <HelpItem
          icon={<Globe className="w-4 h-4 text-blue-500" />}
          title={t("help.settings.language")}
          description={t("help.settings.languageDesc")}
        />
        <HelpItem
          icon={<Palette className="w-4 h-4 text-purple-500" />}
          title={t("help.settings.theme")}
          description={t("help.settings.themeDesc")}
        />
      </HelpSection>

      <HelpSection
        icon={<Lightbulb className="w-5 h-5 text-primary" />}
        title={t("help.tips.title")}
      >
        <div className="space-y-3">
          <div className="flex items-start gap-3 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
            <span className="text-lg">1.</span>
            <p className="text-sm">{t("help.tips.tip1")}</p>
          </div>
          <div className="flex items-start gap-3 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
            <span className="text-lg">2.</span>
            <p className="text-sm">{t("help.tips.tip2")}</p>
          </div>
          <div className="flex items-start gap-3 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
            <span className="text-lg">3.</span>
            <p className="text-sm">{t("help.tips.tip3")}</p>
          </div>
          <div className="flex items-start gap-3 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
            <span className="text-lg">4.</span>
            <p className="text-sm">{t("help.tips.tip4")}</p>
          </div>
          <div className="flex items-start gap-3 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
            <span className="text-lg">5.</span>
            <p className="text-sm">{t("help.tips.tip5")}</p>
          </div>
        </div>
      </HelpSection>
    </div>
  );
}
