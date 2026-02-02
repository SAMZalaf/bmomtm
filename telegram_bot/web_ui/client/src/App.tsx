import { Switch, Route } from "wouter";
import { queryClient, apiRequest } from "./lib/queryClient";
import { QueryClientProvider, useQuery, useMutation } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { Power, RotateCcw, Loader2, RefreshCw, LogOut } from "lucide-react";
import { useState, useEffect } from "react";
import type { BotStatus } from "@shared/schema";
import { LanguageProvider, useLanguage } from "@/lib/language-context";
import NotFound from "@/pages/not-found";
import Dashboard from "@/pages/dashboard";
import Settings from "@/pages/settings";
import Export from "@/pages/export";
import Import from "@/pages/import";
import Help from "@/pages/help";
import JsonDocs from "@/pages/json-docs";
import Login from "@/pages/login";

function Router() {
  return (
    <Switch>
      <Route path="/" component={Dashboard} />
      <Route path="/settings" component={Settings} />
      <Route path="/export" component={Export} />
      <Route path="/import" component={Import} />
      <Route path="/help" component={Help} />
      <Route path="/json-docs" component={JsonDocs} />
      <Route component={NotFound} />
    </Switch>
  );
}

function BotControls() {
  const { toast } = useToast();
  const { t } = useLanguage();
  const [countdown, setCountdown] = useState<number | null>(null);
  const [restartPhase, setRestartPhase] = useState<'idle' | 'restarting' | 'completed'>('idle');
  const [isSyncing, setIsSyncing] = useState(false);

  const { data: botStatus, refetch } = useQuery<BotStatus>({
    queryKey: ["/api/bot/status"],
    refetchInterval: countdown !== null ? 1000 : false,
    staleTime: Infinity,
  });

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      await refetch();
      await queryClient.invalidateQueries({ queryKey: ["/api/buttons/tree"] });
      toast({
        title: t("toast.syncTitle"),
        description: t("toast.syncDesc"),
      });
    } catch {
      toast({
        title: t("toast.error"),
        description: t("toast.syncError"),
        variant: "destructive",
      });
    } finally {
      setIsSyncing(false);
    }
  };

  const toggleMutation = useMutation({
    mutationFn: async (isRunning: boolean) => {
      return apiRequest("POST", "/api/bot/status", { isRunning });
    },
    onSuccess: () => {
      refetch();
      toast({
        title: botStatus?.isRunning ? t("toast.botStopped") : t("toast.botStarted"),
        description: botStatus?.isRunning 
          ? t("toast.botStoppedDesc")
          : t("toast.botStartedDesc"),
      });
    },
    onError: () => {
      toast({
        title: t("toast.error"),
        description: t("toast.botToggleError"),
        variant: "destructive",
      });
    },
  });

  const restartMutation = useMutation({
    mutationFn: async () => {
      return apiRequest("POST", "/api/bot/restart", { seconds: 15 });
    },
    onSuccess: () => {
      setCountdown(15);
      setRestartPhase('restarting');
      refetch();
      toast({
        title: t("toast.restartTitle"),
        description: t("toast.restartDesc"),
      });
    },
    onError: () => {
      toast({
        title: t("toast.error"),
        description: t("toast.restartError"),
        variant: "destructive",
      });
    },
  });

  useEffect(() => {
    if (botStatus?.restartAt) {
      const remaining = Math.max(0, Math.ceil((botStatus.restartAt - Date.now()) / 1000));
      if (remaining > 0) {
        setCountdown(remaining);
        setRestartPhase('restarting');
      } else if (restartPhase === 'restarting') {
        setCountdown(null);
        setRestartPhase('completed');
      }
    }
  }, [botStatus?.restartAt, restartPhase]);

  useEffect(() => {
    if (countdown !== null && countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    } else if (countdown === 0) {
      setCountdown(null);
      setRestartPhase('completed');
      refetch();
    }
  }, [countdown, refetch]);

  useEffect(() => {
    if (restartPhase === 'completed') {
      const timer = setTimeout(() => setRestartPhase('idle'), 3000);
      return () => clearTimeout(timer);
    }
  }, [restartPhase]);

  const isRunning = botStatus?.isRunning ?? true;
  const isRestarting = countdown !== null && countdown > 0;

  const getRestartButtonStyle = () => {
    if (restartPhase === 'restarting') {
      return "bg-red-600 hover:bg-red-700 text-white border-red-600";
    }
    if (restartPhase === 'completed') {
      return "bg-green-600 hover:bg-green-700 text-white border-green-600";
    }
    return "bg-amber-600 hover:bg-amber-700 text-white border-amber-600";
  };

  return (
    <div className="flex items-center gap-1">
      <Button
        size="sm"
        variant={isRunning ? "default" : "destructive"}
        onClick={() => toggleMutation.mutate(!isRunning)}
        disabled={toggleMutation.isPending || isRestarting}
        className={`h-7 px-2 text-xs ${isRunning ? "bg-green-600 hover:bg-green-700" : "bg-red-600 hover:bg-red-700"}`}
        data-testid="button-bot-toggle"
      >
        {toggleMutation.isPending ? (
          <Loader2 className="w-3 h-3 animate-spin" />
        ) : (
          <Power className="w-3 h-3" />
        )}
        <span className="mr-1">{isRunning ? t("header.running") : t("header.stopped")}</span>
      </Button>
      
      <Button
        size="sm"
        variant="outline"
        onClick={() => restartMutation.mutate()}
        disabled={restartMutation.isPending || isRestarting}
        className={`h-7 px-2 text-xs ${getRestartButtonStyle()}`}
        data-testid="button-bot-restart"
      >
        <RotateCcw 
          className={`w-3 h-3 ${restartPhase !== 'idle' ? 'animate-spin-reverse' : ''}`} 
        />
        <span className="mr-1">
          {isRestarting ? (
            <>{countdown}{t("header.seconds")}</>
          ) : (
            <>{t("header.applyChanges")}</>
          )}
        </span>
      </Button>
      
      <Button
        size="sm"
        variant="outline"
        onClick={handleSync}
        disabled={isSyncing || isRestarting}
        className="h-7 px-2 text-xs bg-blue-600 hover:bg-blue-700 text-white border-blue-600"
        data-testid="button-sync"
      >
        <RefreshCw 
          className={`w-3 h-3 ${isSyncing ? 'animate-spin' : ''}`} 
        />
        <span className="mr-1">{isSyncing ? t("header.syncing") : t("header.sync")}</span>
      </Button>
    </div>
  );
}

function AppContent({ onLogout }: { onLogout: () => void }) {
  const { t } = useLanguage();
  const { toast } = useToast();
  
  const style = {
    "--sidebar-width": "16rem",
    "--sidebar-width-icon": "3rem",
  };

  const handleLogout = async () => {
    try {
      const token = localStorage.getItem("auth_token");
      await fetch("/api/auth/logout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token }),
      });
      localStorage.removeItem("auth_token");
      onLogout();
      toast({
        title: "تم تسجيل الخروج",
        description: "تم تسجيل خروجك بنجاح",
      });
    } catch (error) {
      localStorage.removeItem("auth_token");
      onLogout();
    }
  };

  return (
    <SidebarProvider style={style as React.CSSProperties}>
      <div className="flex h-screen w-full">
        <AppSidebar />
        <div className="flex flex-col flex-1 min-w-0">
          <header className="flex items-center justify-between gap-4 p-4 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-40">
            <div className="flex items-center gap-3">
              <SidebarTrigger data-testid="button-sidebar-toggle" />
              <h1 className="text-lg font-semibold hidden sm:block">{t("header.title")}</h1>
            </div>
            <div className="flex items-center gap-4">
              <BotControls />
              <ThemeToggle />
              <Button
                size="sm"
                variant="outline"
                onClick={handleLogout}
                className="h-7 px-2 text-xs"
                data-testid="button-logout"
              >
                <LogOut className="w-3 h-3" />
                <span className="mr-1 hidden sm:inline">خروج</span>
              </Button>
            </div>
          </header>
          <main className="flex-1 overflow-auto p-4 md:p-6">
            <Router />
          </main>
        </div>
      </div>
    </SidebarProvider>
  );
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem("auth_token");
      
      if (!token) {
        setIsAuthenticated(false);
        return;
      }

      try {
        const response = await fetch("/api/auth/verify", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });
        
        const data = await response.json();
        setIsAuthenticated(data.valid);
        
        if (!data.valid) {
          localStorage.removeItem("auth_token");
        }
      } catch (error) {
        setIsAuthenticated(false);
        localStorage.removeItem("auth_token");
      }
    };

    checkAuth();
  }, []);

  // Loading state
  if (isAuthenticated === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  // Not authenticated - show login
  if (!isAuthenticated) {
    return (
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <Login onLogin={(success) => setIsAuthenticated(success)} />
          <Toaster />
        </TooltipProvider>
      </QueryClientProvider>
    );
  }

  // Authenticated - show main app
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <LanguageProvider>
          <AppContent onLogout={() => setIsAuthenticated(false)} />
          <Toaster />
        </LanguageProvider>
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
