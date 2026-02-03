import { useMemo, useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Smartphone, MessageSquare, ChevronLeft, Maximize2, Minimize2 } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import { useLanguage } from "@/lib/language-context";
import type { Button as ButtonType, ButtonTree } from "@shared/schema";

interface TelegramPreviewProps {
  selectedButton: ButtonType | null;
  buttonTree: ButtonTree;
}

function TelegramButton({ 
  text, 
  disabled,
  size = "large",
  onToggleSize,
  buttonId,
  showControls = false,
}: { 
  text: string; 
  disabled?: boolean;
  size?: "large" | "small";
  onToggleSize?: () => void;
  buttonId?: number;
  showControls?: boolean;
}) {
  return (
    <div className={`${size === "large" ? "w-full" : "flex-1 min-w-[48%]"} flex items-center gap-1`}>
      {showControls && onToggleSize && (
        <button
          onClick={onToggleSize}
          className="flex-shrink-0 w-6 h-6 rounded bg-gray-700/80 hover:bg-gray-600 flex items-center justify-center text-gray-300 hover:text-white transition-colors"
          data-testid={`toggle-size-${buttonId}`}
        >
          {size === "large" ? (
            <Minimize2 className="w-3 h-3" />
          ) : (
            <Maximize2 className="w-3 h-3" />
          )}
        </button>
      )}
      <div className="flex-1">
        <div
          className={`flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg text-sm font-medium ${
            disabled
              ? "bg-gray-200 text-gray-400 dark:bg-gray-700 dark:text-gray-500"
              : "bg-[#2481cc] text-white hover:bg-[#1a6cb5]"
          }`}
        >
          <span className="truncate">{text}</span>
        </div>
      </div>
    </div>
  );
}

export function TelegramPreview({ selectedButton, buttonTree }: TelegramPreviewProps) {
  const { toast } = useToast();
  const { language, t } = useLanguage();
  const [currentPage, setCurrentPage] = useState(0);

  const resizeMutation = useMutation({
    mutationFn: async ({ buttonId, buttonSize }: { buttonId: number; buttonSize: "large" | "small" }) => {
      return apiRequest("PATCH", `/api/buttons/${buttonId}`, { buttonSize });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/buttons/tree"] });
      toast({
        title: t("toast.updated"),
        description: t("toast.buttonSizeUpdated"),
      });
    },
    onError: () => {
      toast({
        title: t("toast.error"),
        description: t("toast.buttonSizeError"),
        variant: "destructive",
      });
    },
  });

  const allButtons = useMemo(() => {
    if (selectedButton) {
      return (selectedButton.children ?? []).filter((b) => b.isEnabled);
    }
    return buttonTree.filter((b) => b.isEnabled);
  }, [selectedButton, buttonTree]);

  const pages = useMemo(() => {
    const sortedButtons = [...allButtons].sort((a, b) => a.orderIndex - b.orderIndex);
    
    const pageSeparators = sortedButtons.filter(b => b.buttonType === "page_separator");
    
    if (pageSeparators.length === 0) {
      const regularButtons = sortedButtons.filter(b => b.buttonType !== "page_separator");
      return regularButtons.length > 0 ? [regularButtons] : [[]];
    }
    
    const result: ButtonType[][] = [];
    let currentPageButtons: ButtonType[] = [];
    
    for (const btn of sortedButtons) {
      if (btn.buttonType === "page_separator") {
        if (currentPageButtons.length > 0) {
          result.push(currentPageButtons);
          currentPageButtons = [];
        }
        
        const separatorChildren = (btn.children ?? [])
          .filter(c => c.isEnabled && c.buttonType !== "page_separator")
          .sort((a, b) => a.orderIndex - b.orderIndex);
        
        if (separatorChildren.length > 0) {
          currentPageButtons = [...separatorChildren];
        }
      } else {
        currentPageButtons.push(btn);
      }
    }
    
    if (currentPageButtons.length > 0) {
      result.push(currentPageButtons);
    }
    
    if (result.length === 0) {
      result.push([]);
    }
    
    return result;
  }, [allButtons]);

  useEffect(() => {
    setCurrentPage(0);
  }, [selectedButton?.id, allButtons.length]);

  const totalPages = pages.length;
  const safeCurrentPage = Math.max(0, Math.min(currentPage, totalPages - 1));
  const displayButtons = pages[safeCurrentPage] || [];

  const getMessage = useMemo(() => {
    if (selectedButton) {
      const message = language === "en" ? selectedButton.messageEn : selectedButton.messageAr;
      return message || `${t("preview.selectFrom")} ${language === "en" ? selectedButton.textEn : selectedButton.textAr}`;
    }
    return t("preview.welcomeMessage");
  }, [selectedButton, language, t]);

  const path = useMemo(() => {
    if (!selectedButton) return [t("preview.mainMenu")];
    
    const pathMap = new Map<number, string>();
    const buildPath = (tree: ButtonTree) => {
      for (const btn of tree) {
        pathMap.set(btn.id, language === "en" ? btn.textEn : btn.textAr);
        if (btn.children) buildPath(btn.children);
      }
    };
    
    buildPath(buttonTree);
    if (!pathMap.has(selectedButton.id)) return [t("preview.mainMenu")];
    
    return [t("preview.mainMenu"), pathMap.get(selectedButton.id) || ""];
  }, [selectedButton, buttonTree, language, t]);

  const buttonRows = useMemo(() => {
    const rows: ButtonType[][] = [];
    let currentRow: ButtonType[] = [];
    
    for (const btn of displayButtons) {
      const size = btn.buttonSize || "large";
      if (size === "large") {
        if (currentRow.length > 0) {
          rows.push([...currentRow]);
          currentRow = [];
        }
        rows.push([btn]);
      } else {
        currentRow.push(btn);
        if (currentRow.length === 2) {
          rows.push([...currentRow]);
          currentRow = [];
        }
      }
    }
    
    if (currentRow.length > 0) {
      rows.push([...currentRow]);
    }
    
    return rows;
  }, [displayButtons]);

  return (
    <Card className="sticky top-6">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <Smartphone className="w-5 h-5" />
          {t("preview.title")}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="mx-auto" style={{ maxWidth: "340px" }}>
          <div className="bg-gray-900 rounded-[2.5rem] p-2">
            <div className="bg-[#17212b] rounded-[2rem] overflow-hidden flex flex-col" style={{ height: "560px" }}>
              <div className="bg-[#242f3d] px-4 py-3 flex items-center gap-3 flex-shrink-0">
                <ChevronLeft className="w-5 h-5 text-[#6ab3f3]" />
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center text-white font-bold flex-shrink-0">
                  <Smartphone className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-white font-medium truncate">{t("preview.botName")}</div>
                  <div className="text-xs text-gray-400">{t("preview.onlineNow")}</div>
                </div>
              </div>

              {path.length > 1 && (
                <div className="bg-[#1e2c3a] px-4 py-2 text-xs text-gray-400 flex-shrink-0 border-b border-gray-700">
                  {path.filter(p => p).join(" \u2190 ")}
                </div>
              )}

              <div className="bg-[#0e1621] p-4 space-y-2 overflow-y-auto flex-1">
                <div className="flex justify-start">
                  <div className="bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-2xl px-4 py-2.5 text-sm rounded-br-sm">
                    {getMessage}
                  </div>
                </div>

                {displayButtons.length > 0 && (
                  <div className="space-y-2 mt-4">
                    {buttonRows.map((row, rowIndex) => (
                      <div key={rowIndex} className="flex gap-1">
                        {row.map((btn) => (
                          <TelegramButton
                            key={btn.id}
                            buttonId={btn.id}
                            text={language === "en" ? btn.textEn : btn.textAr}
                            disabled={!btn.isEnabled}
                            size={btn.buttonSize || "large"}
                            onToggleSize={() => {
                              const newSize = btn.buttonSize === "small" ? "large" : "small";
                              resizeMutation.mutate({
                                buttonId: btn.id,
                                buttonSize: newSize,
                              });
                            }}
                            showControls={true}
                          />
                        ))}
                      </div>
                    ))}
                    
                    {totalPages > 1 && (
                      <div className="flex items-center justify-center gap-2 mt-3">
                        <button
                          onClick={() => setCurrentPage(p => Math.max(0, p - 1))}
                          disabled={safeCurrentPage === 0}
                          className={`py-2 px-4 rounded-lg text-sm font-medium ${
                            safeCurrentPage === 0
                              ? "bg-gray-600 text-gray-400 cursor-not-allowed"
                              : "bg-[#2481cc] text-white hover:bg-[#1a6cb5]"
                          }`}
                          data-testid="btn-prev-page"
                        >
                          {language === "ar" ? "\u0627\u0644\u0633\u0627\u0628\u0642" : "Previous"}
                        </button>
                        <span className="text-gray-400 text-sm px-2">
                          {safeCurrentPage + 1}/{totalPages}
                        </span>
                        <button
                          onClick={() => setCurrentPage(p => Math.min(totalPages - 1, p + 1))}
                          disabled={safeCurrentPage === totalPages - 1}
                          className={`py-2 px-4 rounded-lg text-sm font-medium ${
                            safeCurrentPage === totalPages - 1
                              ? "bg-gray-600 text-gray-400 cursor-not-allowed"
                              : "bg-[#2481cc] text-white hover:bg-[#1a6cb5]"
                          }`}
                          data-testid="btn-next-page"
                        >
                          {language === "ar" ? "\u0627\u0644\u062a\u0627\u0644\u064a" : "Next"}
                        </button>
                      </div>
                    )}
                  </div>
                )}

                {displayButtons.length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <div className="text-sm">{t("preview.noButtons")}</div>
                  </div>
                )}
              </div>

              <div className="bg-[#17212b] px-3 py-2 flex items-center gap-2 flex-shrink-0">
                <div className="flex-1 bg-[#242f3d] rounded-full px-4 py-2 text-sm text-gray-400">
                  {t("preview.typeMessage")}
                </div>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
