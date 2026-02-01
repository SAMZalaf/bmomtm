import { Link, useLocation } from "wouter";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  SidebarFooter,
} from "@/components/ui/sidebar";
import {
  LayoutDashboard,
  Settings,
  Download,
  Upload,
  Bot,
  HelpCircle,
  BookOpen,
  FileCode,
} from "lucide-react";
import { useLanguage } from "@/lib/language-context";

export function AppSidebar() {
  const [location] = useLocation();
  const { t } = useLanguage();

  const menuItems = [
    {
      title: t("sidebar.dashboard"),
      url: "/",
      icon: LayoutDashboard,
    },
    {
      title: t("sidebar.settings"),
      url: "/settings",
      icon: Settings,
    },
    {
      title: t("sidebar.help"),
      url: "/help",
      icon: BookOpen,
    },
  ];

  const toolItems = [
    {
      title: t("sidebar.export"),
      url: "/export",
      icon: Download,
    },
    {
      title: t("sidebar.import"),
      url: "/import",
      icon: Upload,
    },
    {
      title: t("sidebar.jsonDocs"),
      url: "/json-docs",
      icon: FileCode,
    },
  ];

  return (
    <Sidebar>
      <SidebarHeader className="border-b border-sidebar-border p-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <Bot className="w-6 h-6 text-primary" />
          </div>
          <div>
            <h2 className="font-semibold text-sidebar-foreground">{t("sidebar.title")}</h2>
            <p className="text-xs text-sidebar-foreground/60">{t("sidebar.subtitle")}</p>
          </div>
        </div>
      </SidebarHeader>
      
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>{t("sidebar.mainMenu")}</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {menuItems.map((item) => (
                <SidebarMenuItem key={item.url}>
                  <SidebarMenuButton
                    asChild
                    isActive={location === item.url}
                  >
                    <Link href={item.url} data-testid={`nav-${item.url.replace("/", "") || "home"}`}>
                      <item.icon className="w-4 h-4" />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>{t("sidebar.tools")}</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {toolItems.map((item) => (
                <SidebarMenuItem key={item.url}>
                  <SidebarMenuButton
                    asChild
                    isActive={location === item.url}
                  >
                    <Link href={item.url} data-testid={`nav-${item.url.replace("/", "")}`}>
                      <item.icon className="w-4 h-4" />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t border-sidebar-border p-4">
        <div className="flex flex-col gap-2 text-xs text-sidebar-foreground/60">
          <div className="flex items-center gap-2">
            <HelpCircle className="w-4 h-4" />
            <span>{t("sidebar.version")} 1.1.1</span>
          </div>
          <p data-testid="text-developer-name">Mohamad Zalaf ©2025</p>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
