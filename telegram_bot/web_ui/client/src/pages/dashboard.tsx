import { useState, useMemo, useCallback, useRef, useEffect, memo } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { queryClient, apiRequest } from "@/lib/queryClient";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Slider } from "@/components/ui/slider";
import { useToast } from "@/hooks/use-toast";
import { useLanguage } from "@/lib/language-context";
import {
  ChevronDown,
  ChevronLeft,
  Plus,
  Pencil,
  Trash2,
  Folder,
  FolderOpen,
  FileText,
  ExternalLink,
  FolderTree,
  DollarSign,
  Eye,
  EyeOff,
  MoreVertical,
  Power,
  PowerOff,
  Copy,
  Search,
  X,
  Hash,
  Wallet,
  ShoppingCart,
  Maximize2,
  Minimize2,
  GripVertical,
  Settings,
  CheckSquare,
  Square,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { Button as ButtonType, ButtonTree } from "@shared/schema";
import { ButtonEditorDialog } from "@/components/button-editor-dialog";
import { TelegramPreview } from "@/components/telegram-preview";
import { DeleteConfirmDialog } from "@/components/delete-confirm-dialog";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";

interface TreeNodeProps {
  button: ButtonType;
  level: number;
  onEdit: (button: ButtonType) => void;
  onDelete: (button: ButtonType) => void;
  onToggle: (id: number, enabled: boolean) => void;
  onAddChild: (parentId: number) => void;
  onCopy: (button: ButtonType) => void;
  onMultiCopy: (button: ButtonType) => void;
  selectedId: number | null;
  onSelect: (button: ButtonType) => void;
  isLast: boolean;
  parentLines: boolean[];
  searchQuery: string;
  language: "ar" | "en";
  t: (key: string) => string;
  siblings: ButtonType[];
  zoomLevel: number;
  globalExpandState: "expanded" | "collapsed" | null;
  globalExpandTrigger: number;
  onDragStart: (e: React.DragEvent, button: ButtonType) => void;
  onDragEnd: () => void;
  onDragOver: (e: React.DragEvent, targetButton: ButtonType) => void;
  onDrop: (e: React.DragEvent, targetButton: ButtonType) => void;
  draggedButtonId: number | null;
  dragOverButtonId?: number | null;
  dropPosition?: 'before' | 'after' | 'inside' | null;
  selectionMode?: boolean;
  selectedIds?: Set<number>;
  onSelectionChange?: (id: number, selected: boolean) => void;
}

const TreeNode = memo(function TreeNode({
  button,
  level,
  onEdit,
  onDelete,
  onToggle,
  onAddChild,
  onCopy,
  onMultiCopy,
  selectedId,
  onSelect,
  isLast,
  parentLines,
  searchQuery,
  language,
  t,
  siblings,
  zoomLevel,
  globalExpandState,
  globalExpandTrigger,
  onDragStart,
  onDragEnd,
  onDragOver,
  onDrop,
  draggedButtonId,
  dragOverButtonId,
  dropPosition,
  selectionMode = false,
  selectedIds = new Set(),
  onSelectionChange,
}: TreeNodeProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  
  useEffect(() => {
    // توسيع/طي فقط المستوى الأول (الجذر) - level === 0
    if (level === 0) {
      if (globalExpandState === "expanded") {
        setIsExpanded(true);
      } else if (globalExpandState === "collapsed") {
        setIsExpanded(false);
      }
    }
  }, [globalExpandState, globalExpandTrigger, level]);
  
  const totalChildrenCount = useMemo(() => {
    const countAllChildren = (btn: ButtonType): number => {
      if (!btn.children || btn.children.length === 0) return 0;
      let count = btn.children.length;
      for (const child of btn.children) {
        count += countAllChildren(child);
      }
      return count;
    };
    return countAllChildren(button);
  }, [button]);
  const isPageSeparator = button.buttonType === "page_separator";
  const hasChildren = button.children && button.children.length > 0;
  const isSelected = selectedId === button.id;
  const isFolder = button.buttonType === "menu" || hasChildren;
  
  const pageCount = hasChildren 
    ? button.children!.filter(c => c.buttonType === "page_separator").length + 1 
    : 0;
  const hasPages = pageCount > 1;
  
  const pageSeparatorNumber = useMemo(() => {
    if (!isPageSeparator || !siblings || siblings.length === 0) return 1;
    const sortedSeparators = siblings
      .filter(s => s.buttonType === "page_separator")
      .sort((a, b) => a.orderIndex - b.orderIndex);
    const index = sortedSeparators.findIndex(s => s.id === button.id);
    return index >= 0 ? index + 1 : 1;
  }, [isPageSeparator, siblings, button.id]);
  
  const matchesSearch = searchQuery
    ? button.textAr.toLowerCase().includes(searchQuery.toLowerCase()) ||
      button.textEn.toLowerCase().includes(searchQuery.toLowerCase()) ||
      button.buttonKey.toLowerCase().includes(searchQuery.toLowerCase())
    : true;

  const hasMatchingChildren = (btn: ButtonType): boolean => {
    if (!btn.children) return false;
    return btn.children.some(
      (child) =>
        child.textAr.toLowerCase().includes(searchQuery.toLowerCase()) ||
        child.textEn.toLowerCase().includes(searchQuery.toLowerCase()) ||
        child.buttonKey.toLowerCase().includes(searchQuery.toLowerCase()) ||
        hasMatchingChildren(child)
    );
  };

  const shouldShow = searchQuery
    ? matchesSearch || hasMatchingChildren(button)
    : true;

  if (!shouldShow) return null;

  // عرض خاص لفاصل الصفحة - خط أفقي واضح مع دعم الأبناء
  if (isPageSeparator) {
    const sepIsDragging = draggedButtonId === button.id;
    const sepIsDropTarget = dragOverButtonId === button.id;
    const sepShowDropBefore = sepIsDropTarget && dropPosition === 'before';
    const sepShowDropAfter = sepIsDropTarget && dropPosition === 'after';
    
    return (
      <div className="w-full select-none relative">
        {/* Drop indicator - before */}
        {sepShowDropBefore && (
          <div className="absolute top-0 left-0 right-0 h-0.5 bg-orange-500 z-10" />
        )}
        
        <div
          className={`group flex items-center gap-2 py-1 px-2 ${
            !button.isEnabled ? "opacity-50" : ""
          } ${sepIsDragging ? "opacity-40" : ""}`}
          draggable
          onDragStart={(e) => onDragStart(e, button)}
          onDragEnd={onDragEnd}
          onDragOver={(e) => onDragOver(e, button)}
          onDrop={(e) => onDrop(e, button)}
          data-testid={`tree-node-${button.id}`}
        >
          {/* Drag handle */}
          <div 
            className="flex-shrink-0 cursor-grab active:cursor-grabbing opacity-0 group-hover:opacity-60 hover:opacity-100 transition-opacity"
            onMouseDown={(e) => e.stopPropagation()}
          >
            <GripVertical className="w-4 h-4 text-orange-400" />
          </div>
          
          {/* Tree lines for indentation - like file explorer */}
          <div className="flex items-center h-6">
            {(language === "ar" ? [...parentLines].reverse() : parentLines).map((showLine, i) => {
              const actualIndex = language === "ar" ? parentLines.length - 1 - i : i;
              const maxLevels = parentLines.length;
              // Arabic: outer (first column) = dark, inner = lighter
              // English: outer (first column) = lighter, inner = darker (opposite)
              const lineOpacity = language === "ar"
                ? Math.max(0.3, 0.8 - (actualIndex * 0.12))
                : Math.min(0.8, 0.3 + (actualIndex * 0.12));
              return (
                <div key={i} className="w-5 h-full flex justify-center relative">
                  {showLine && <div className="w-px h-full bg-emerald-400" style={{ opacity: lineOpacity }} />}
                </div>
              );
            })}
            {level > 0 && (
              <div className="w-5 h-full flex items-center relative">
                {/* Vertical line going up */}
                <div 
                  className={`absolute w-px bg-emerald-400 ${isLast ? 'h-1/2 top-0' : 'h-full'} ${language === "ar" ? "right-1/2" : "left-1/2"}`}
                  style={{ opacity: language === "ar" ? Math.max(0.3, 0.8 - (level * 0.12)) : Math.min(0.8, 0.3 + (level * 0.12)) }}
                />
                {/* Horizontal line to the item */}
                <div 
                  className={`absolute top-1/2 w-1/2 h-px bg-emerald-400 ${language === "ar" ? "left-0" : "right-0"}`}
                  style={{ opacity: language === "ar" ? Math.max(0.3, 0.8 - (level * 0.12)) : Math.min(0.8, 0.3 + (level * 0.12)) }}
                />
              </div>
            )}
          </div>
          
          {/* Expand/Collapse button for page separator with children */}
          {hasChildren ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setIsExpanded(!isExpanded);
              }}
              className="p-0.5 hover:bg-muted rounded flex-shrink-0"
              data-testid={`toggle-expand-${button.id}`}
            >
              {isExpanded ? (
                <ChevronDown className="w-4 h-4 text-orange-500" />
              ) : (
                <ChevronLeft className="w-4 h-4 text-orange-500" />
              )}
            </button>
          ) : (
            <div className="w-5" />
          )}
          
          {/* Page separator visual - خط فاصل واضح */}
          <div className="flex-1 flex items-center gap-2">
            <div className="flex-1 h-px bg-orange-400/60" />
            <span className="text-xs text-orange-500 font-medium whitespace-nowrap px-2 bg-orange-500/10 rounded">
              {language === "ar" ? `فاصل صفحة ${pageSeparatorNumber}` : `Page ${pageSeparatorNumber}`}
              {hasChildren && (
                <span className="mr-1 text-orange-400">
                  ({button.children!.length})
                </span>
              )}
            </span>
            <div className="flex-1 h-px bg-orange-400/60" />
          </div>

          {/* Quick actions */}
          <div className="flex items-center gap-0.5">
            {/* Selection checkbox or Enable/Disable toggle */}
            <div
              onClick={(e) => e.stopPropagation()}
              className="flex items-center"
            >
              {selectionMode ? (
                <button
                  onClick={() => onSelectionChange?.(button.id, !selectedIds.has(button.id))}
                  className="p-1 rounded hover:bg-yellow-100 dark:hover:bg-yellow-900/30 transition-colors"
                  data-testid={`select-checkbox-${button.id}`}
                >
                  {selectedIds.has(button.id) ? (
                    <CheckSquare className="w-5 h-5 text-yellow-500" />
                  ) : (
                    <Square className="w-5 h-5 text-muted-foreground" />
                  )}
                </button>
              ) : (
                <Switch
                  checked={button.isEnabled}
                  onCheckedChange={(checked) => onToggle(button.id, checked)}
                  className="scale-75"
                  data-testid={`toggle-enable-${button.id}`}
                />
              )}
            </div>

            {/* More actions dropdown - same as regular buttons */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity"
                  onClick={(e) => e.stopPropagation()}
                  data-testid={`menu-button-${button.id}`}
                >
                  <MoreVertical className="w-4 h-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuItem onClick={() => onEdit(button)} data-testid={`edit-button-${button.id}`}>
                  <Pencil className="w-4 h-4 ml-2" />
                  {t("dashboard.editButton")}
                </DropdownMenuItem>
                
                <DropdownMenuItem
                  onClick={() => onAddChild(button.id)}
                  data-testid={`add-child-${button.id}`}
                >
                  <Plus className="w-4 h-4 ml-2" />
                  {t("dashboard.addChildButton")}
                </DropdownMenuItem>

                <DropdownMenuItem
                  onClick={() => onToggle(button.id, !button.isEnabled)}
                >
                  {button.isEnabled ? (
                    <>
                      <PowerOff className="w-4 h-4 ml-2" />
                      {t("dashboard.disableButton")}
                    </>
                  ) : (
                    <>
                      <Power className="w-4 h-4 ml-2" />
                      {t("dashboard.enableButton")}
                    </>
                  )}
                </DropdownMenuItem>
                
                <DropdownMenuSeparator />
                
                {/* نسخ العنصر - Yellow Theme */}
                <DropdownMenuItem
                  onClick={() => onMultiCopy(button)}
                  className="text-yellow-600 dark:text-yellow-400 focus:text-yellow-700 focus:bg-yellow-50 dark:focus:bg-yellow-900/20"
                  data-testid={`multi-copy-button-${button.id}`}
                >
                  <Copy className="w-4 h-4 ml-2 text-yellow-500" />
                  {language === "ar" ? "نسخ العنصر" : "Copy Element"}
                </DropdownMenuItem>
                
                <DropdownMenuItem 
                  onClick={() => onDelete(button)} 
                  className="text-destructive focus:text-destructive" 
                  data-testid={`delete-button-${button.id}`}
                >
                  <Trash2 className="w-4 h-4 ml-2" />
                  {t("dashboard.deleteButton")}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
        
        {/* Children of page separator - keep mounted for global expand/collapse */}
        {hasChildren && (
          <div className={`relative ${!isExpanded ? 'hidden' : ''}`}>
            {button.children!.map((child, index) => (
              <TreeNode
                key={child.id}
                button={child}
                level={level + 1}
                onEdit={onEdit}
                onDelete={onDelete}
                onToggle={onToggle}
                onAddChild={onAddChild}
                onCopy={onCopy}
                onMultiCopy={onMultiCopy}
                selectedId={selectedId}
                onSelect={onSelect}
                isLast={index === button.children!.length - 1}
                parentLines={[...parentLines, !isLast]}
                searchQuery={searchQuery}
                language={language}
                t={t}
                siblings={button.children!}
                zoomLevel={zoomLevel}
                globalExpandState={globalExpandState}
                globalExpandTrigger={globalExpandTrigger}
                onDragStart={onDragStart}
                onDragEnd={onDragEnd}
                onDragOver={onDragOver}
                onDrop={onDrop}
                draggedButtonId={draggedButtonId}
                dragOverButtonId={dragOverButtonId}
                dropPosition={dropPosition}
                selectionMode={selectionMode}
                selectedIds={selectedIds}
                onSelectionChange={onSelectionChange}
              />
            ))}
          </div>
        )}
        
        {/* Drop indicator - after */}
        {sepShowDropAfter && (
          <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-orange-500 z-10" />
        )}
      </div>
    );
  }

  const isDragging = draggedButtonId === button.id;
  const isDropTarget = dragOverButtonId === button.id;
  const showDropBefore = isDropTarget && dropPosition === 'before';
  const showDropAfter = isDropTarget && dropPosition === 'after';
  const showDropInside = isDropTarget && dropPosition === 'inside';

  return (
    <div className="w-full select-none relative">
      {/* Drop indicator - before */}
      {showDropBefore && (
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-primary z-10" />
      )}
      
      <div
        className={`group flex items-center gap-1 rounded-md transition-all cursor-pointer ${
          isSelected
            ? "bg-primary/15 ring-1 ring-primary/40"
            : "hover:bg-muted/50"
        } ${!button.isEnabled ? "opacity-50" : ""} ${isDragging ? "opacity-40" : ""} ${showDropInside ? "ring-2 ring-primary/50 bg-primary/10" : ""}`}
        style={{
          padding: `${Math.max(2, zoomLevel * 0.06)}px ${Math.max(4, zoomLevel * 0.08)}px`,
        }}
        onClick={() => onSelect(button)}
        draggable
        onDragStart={(e) => onDragStart(e, button)}
        onDragEnd={onDragEnd}
        onDragOver={(e) => onDragOver(e, button)}
        onDrop={(e) => onDrop(e, button)}
        data-testid={`tree-node-${button.id}`}
      >
        {/* Drag handle */}
        <div 
          className="flex-shrink-0 cursor-grab active:cursor-grabbing opacity-0 group-hover:opacity-60 hover:opacity-100 transition-opacity"
          onMouseDown={(e) => e.stopPropagation()}
        >
          <GripVertical className="w-4 h-4 text-muted-foreground" />
        </div>
        
        {/* Tree lines for indentation - like file explorer */}
        <div className="flex items-center h-6">
          {(language === "ar" ? [...parentLines].reverse() : parentLines).map((showLine, i) => {
            const actualIndex = language === "ar" ? parentLines.length - 1 - i : i;
            // Arabic: outer (first column) = dark, inner = lighter
            // English: outer (first column) = lighter, inner = darker (opposite)
            const lineOpacity = language === "ar"
              ? Math.max(0.3, 0.8 - (actualIndex * 0.12))
              : Math.min(0.8, 0.3 + (actualIndex * 0.12));
            return (
              <div key={i} className="w-5 h-full flex justify-center relative">
                {showLine && (
                  <div className="w-px h-full bg-emerald-400" style={{ opacity: lineOpacity }} />
                )}
              </div>
            );
          })}
          
          {level > 0 && (
            <div className="w-5 h-full flex items-center relative">
              {/* Vertical line going up */}
              <div 
                className={`absolute w-px bg-emerald-400 ${isLast ? 'h-1/2 top-0' : 'h-full'} ${language === "ar" ? "right-1/2" : "left-1/2"}`}
                style={{ opacity: language === "ar" ? Math.max(0.3, 0.8 - (level * 0.12)) : Math.min(0.8, 0.3 + (level * 0.12)) }}
              />
              {/* Horizontal line to the item */}
              <div 
                className={`absolute top-1/2 w-1/2 h-px bg-emerald-400 ${language === "ar" ? "left-0" : "right-0"}`}
                style={{ opacity: language === "ar" ? Math.max(0.3, 0.8 - (level * 0.12)) : Math.min(0.8, 0.3 + (level * 0.12)) }}
              />
            </div>
          )}
        </div>

        {/* Expand/Collapse button */}
        {hasChildren ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(!isExpanded);
            }}
            className="p-0.5 hover:bg-muted rounded flex-shrink-0"
            data-testid={`toggle-expand-${button.id}`}
          >
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            ) : (
              <ChevronLeft className="w-4 h-4 text-muted-foreground" />
            )}
          </button>
        ) : (
          <div className="w-5" />
        )}

        {/* Folder/File icon */}
        <div className="flex-shrink-0">
          {isPageSeparator ? (
            <div className="w-5 h-5 flex items-center justify-center text-orange-500 font-bold text-xs">---</div>
          ) : button.buttonType === "back" ? (
            <div className="w-5 h-5 flex items-center justify-center text-purple-500 font-bold text-xs">◀</div>
          ) : button.buttonType === "cancel" ? (
            <div className="w-5 h-5 flex items-center justify-center text-red-500 font-bold text-xs">✕</div>
          ) : button.buttonType === "link" ? (
            <ExternalLink className="w-5 h-5 text-cyan-500" />
          ) : isFolder ? (
            isExpanded && hasChildren ? (
              <FolderOpen className="w-5 h-5 text-amber-500" />
            ) : (
              <Folder className="w-5 h-5 text-amber-500" />
            )
          ) : (
            <FileText className="w-5 h-5 text-blue-500" />
          )}
        </div>

        {/* Button icon/emoji */}
        <span className="text-base flex-shrink-0">{button.icon || ""}</span>
        
        {/* Button name */}
        <div className="flex-1 min-w-0 flex items-center gap-2">
          <span 
            className={`font-medium truncate ${
              button.buttonType === "back" ? "text-purple-600 dark:text-purple-400" : 
              button.buttonType === "cancel" ? "text-red-600 dark:text-red-400" : 
              button.buttonType === "link" ? "text-cyan-600 dark:text-cyan-400" :
              isPageSeparator ? "text-orange-600 dark:text-orange-400" : ""
            }`}
            style={{ fontSize: `${Math.max(10, zoomLevel * 0.14)}px` }}
            data-testid={`button-name-${button.id}`}
          >
            {language === "en" ? button.textEn : button.textAr}
          </span>
          {/* Button children count - separate from button name */}
          {hasChildren && (
            <span 
              className="text-muted-foreground text-xs flex-shrink-0"
              style={{ fontSize: `${Math.max(9, zoomLevel * 0.11)}px` }}
            >
              ({totalChildrenCount})
            </span>
          )}
          
          {/* Feature indicators - small icons */}
          <div className="flex items-center gap-1">
            {button.askQuantity && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <div 
                    className="flex items-center justify-center w-5 h-5 rounded bg-purple-500/15 text-purple-600 dark:text-purple-400"
                  >
                    <Hash className="w-3 h-3" />
                  </div>
                </TooltipTrigger>
                <TooltipContent side="top">
                  <p>{t("dashboard.asksQuantity")}</p>
                </TooltipContent>
              </Tooltip>
            )}
            
            {button.isService && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <div 
                    className="flex items-center justify-center w-5 h-5 rounded bg-green-500/15 text-green-600 dark:text-green-400"
                  >
                    <ShoppingCart className="w-3 h-3" />
                  </div>
                </TooltipTrigger>
                <TooltipContent side="top">
                  <p>{t("dashboard.paidService")}</p>
                </TooltipContent>
              </Tooltip>
            )}
          </div>
          
          {/* Badges */}
          <div className="hidden sm:flex items-center gap-1.5">
            {button.isService && button.price > 0 && (
              <Badge variant="secondary" className="text-xs py-0 h-5">
                ${button.price}
              </Badge>
            )}
            {hasPages && (
              <Badge variant="outline" className="text-xs py-0 h-5 border-orange-400 text-orange-600 dark:text-orange-400">
                ({pageCount} {t("dashboard.pagesCount")})
              </Badge>
            )}
          </div>
        </div>

        {/* Quick actions - always visible */}
        <div className="flex items-center gap-0.5">
          {/* Selection checkbox or Enable/Disable toggle */}
          <div
            onClick={(e) => e.stopPropagation()}
            className="flex items-center"
          >
            {selectionMode ? (
              <button
                onClick={() => onSelectionChange?.(button.id, !selectedIds.has(button.id))}
                className="p-1 rounded hover:bg-yellow-100 dark:hover:bg-yellow-900/30 transition-colors"
                data-testid={`select-checkbox-${button.id}`}
              >
                {selectedIds.has(button.id) ? (
                  <CheckSquare className="w-5 h-5 text-yellow-500" />
                ) : (
                  <Square className="w-5 h-5 text-muted-foreground" />
                )}
              </button>
            ) : (
              <Switch
                checked={button.isEnabled}
                onCheckedChange={(checked) => onToggle(button.id, checked)}
                className="scale-75"
                data-testid={`toggle-enable-${button.id}`}
              />
            )}
          </div>

          {/* More actions dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                size="icon"
                variant="ghost"
                className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={(e) => e.stopPropagation()}
                data-testid={`menu-button-${button.id}`}
              >
                <MoreVertical className="w-4 h-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem
                onClick={() => onEdit(button)}
                data-testid={`edit-button-${button.id}`}
              >
                <Pencil className="w-4 h-4 ml-2" />
                {t("dashboard.editButton")}
              </DropdownMenuItem>
              
              <DropdownMenuItem
                onClick={() => onAddChild(button.id)}
                data-testid={`add-child-${button.id}`}
              >
                <Plus className="w-4 h-4 ml-2" />
                {t("dashboard.addChildButton")}
              </DropdownMenuItem>

              <DropdownMenuItem
                onClick={() => onToggle(button.id, !button.isEnabled)}
              >
                {button.isEnabled ? (
                  <>
                    <PowerOff className="w-4 h-4 ml-2" />
                    {t("dashboard.disableButton")}
                  </>
                ) : (
                  <>
                    <Power className="w-4 h-4 ml-2" />
                    {t("dashboard.enableButton")}
                  </>
                )}
              </DropdownMenuItem>
              
              <DropdownMenuSeparator />
              
              {/* نسخ العنصر - Yellow Theme */}
              <DropdownMenuItem
                onClick={() => onMultiCopy(button)}
                className="text-yellow-600 dark:text-yellow-400 focus:text-yellow-700 focus:bg-yellow-50 dark:focus:bg-yellow-900/20"
                data-testid={`multi-copy-button-${button.id}`}
              >
                <Copy className="w-4 h-4 ml-2 text-yellow-500" />
                {language === "ar" ? "نسخ العنصر" : "Copy Element"}
              </DropdownMenuItem>
              
              <DropdownMenuItem
                onClick={() => onDelete(button)}
                className="text-destructive focus:text-destructive"
                data-testid={`delete-button-${button.id}`}
              >
                <Trash2 className="w-4 h-4 ml-2" />
                {t("dashboard.deleteButton")}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Children - keep mounted for global expand/collapse */}
      {hasChildren && (
        <div className={`relative ${!isExpanded ? 'hidden' : ''}`}>
          {button.children!.map((child, index) => (
            <TreeNode
              key={child.id}
              button={child}
              level={level + 1}
              onEdit={onEdit}
              onDelete={onDelete}
              onToggle={onToggle}
              onAddChild={onAddChild}
              onCopy={onCopy}
              onMultiCopy={onMultiCopy}
              selectedId={selectedId}
              onSelect={onSelect}
              isLast={index === button.children!.length - 1}
              parentLines={[...parentLines, !isLast]}
              searchQuery={searchQuery}
              language={language}
              t={t}
              siblings={button.children!}
              zoomLevel={zoomLevel}
              globalExpandState={globalExpandState}
              globalExpandTrigger={globalExpandTrigger}
              onDragStart={onDragStart}
              onDragEnd={onDragEnd}
              onDragOver={onDragOver}
              onDrop={onDrop}
              draggedButtonId={draggedButtonId}
              dragOverButtonId={dragOverButtonId}
              dropPosition={dropPosition}
              selectionMode={selectionMode}
              selectedIds={selectedIds}
              onSelectionChange={onSelectionChange}
            />
          ))}
        </div>
      )}
      
      {/* Drop indicator - after */}
      {showDropAfter && (
        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary z-10" />
      )}
    </div>
  );
});

function TreeSkeleton() {
  return (
    <div className="space-y-1 p-2">
      {[1, 2].map((i) => (
        <div key={i} className="space-y-1">
          <Skeleton className="h-8 w-full rounded-md" />
          <div className="mr-6 space-y-1">
            <Skeleton className="h-8 w-full rounded-md" />
            <Skeleton className="h-8 w-full rounded-md" />
            <div className="mr-6 space-y-1">
              <Skeleton className="h-8 w-full rounded-md" />
              <Skeleton className="h-8 w-full rounded-md" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function Dashboard() {
  const { toast } = useToast();
  const { language, t } = useLanguage();
  const [selectedButton, setSelectedButton] = useState<ButtonType | null>(null);
  const [editingButton, setEditingButton] = useState<ButtonType | null>(null);
  const [deletingButton, setDeletingButton] = useState<ButtonType | null>(null);
  const [isAddingNew, setIsAddingNew] = useState(false);
  const [newButtonParentId, setNewButtonParentId] = useState<number | null>(null);
  const [showPreview, setShowPreview] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [zoomLevel, setZoomLevel] = useState(100);
  const [globalExpandState, setGlobalExpandState] = useState<"expanded" | "collapsed" | null>(null);
  const [globalExpandTrigger, setGlobalExpandTrigger] = useState(0);
  const [draggedButtonId, setDraggedButtonId] = useState<number | null>(null);
  const [dragOverButtonId, setDragOverButtonId] = useState<number | null>(null);
  const [dropPosition, setDropPosition] = useState<'before' | 'after' | 'inside' | null>(null);
  const [multiCopyButton, setMultiCopyButton] = useState<ButtonType | null>(null);
  const [multiCopyCount, setMultiCopyCount] = useState(2);
  const [showMultiCopySettings, setShowMultiCopySettings] = useState(false);
  const [multiCopyNames, setMultiCopyNames] = useState<Array<{index: number; buttonKey: string; textAr: string; textEn: string}>>([]);
  const [multiCopyPosition, setMultiCopyPosition] = useState<"top" | "center" | "end">("end");
  const [multiCopyTargetButton, setMultiCopyTargetButton] = useState<ButtonType | null>(null);
  const [multiCopyInsideMenu, setMultiCopyInsideMenu] = useState(false);
  const [multiCopyExpandedIds, setMultiCopyExpandedIds] = useState<Set<number>>(new Set());
  const [copyWithChildren, setCopyWithChildren] = useState(true);
  const [overrideServicePrice, setOverrideServicePrice] = useState(false);
  const [newServicePrice, setNewServicePrice] = useState(0);
  const [newServicePriceInput, setNewServicePriceInput] = useState("0");
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  const { data: buttonTree, isLoading } = useQuery<ButtonTree>({
    queryKey: ["/api/buttons/tree"],
  });

  const reorderMutation = useMutation({
    mutationFn: async ({ buttonId, targetId, position }: { buttonId: number; targetId: number; position: 'before' | 'after' | 'inside' }) => {
      return apiRequest("POST", "/api/buttons/reorder", { buttonId, targetId, position });
    },
    onSuccess: () => {
      toast({
        title: language === "ar" ? "تم إعادة الترتيب" : "Reordered",
        description: language === "ar" ? "تم نقل الزر بنجاح (اضغط مزامنة لتحديث العرض)" : "Button moved successfully (press sync to refresh)",
      });
    },
    onError: () => {
      toast({
        title: t("toast.error"),
        description: language === "ar" ? "فشل في نقل الزر" : "Failed to move button",
        variant: "destructive",
      });
    },
  });

  const handleDragStart = useCallback((e: React.DragEvent, button: ButtonType) => {
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', button.id.toString());
    setDraggedButtonId(button.id);
  }, []);

  const handleDragEnd = useCallback(() => {
    setDraggedButtonId(null);
    setDragOverButtonId(null);
    setDropPosition(null);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent, targetButton: ButtonType) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    
    if (draggedButtonId === targetButton.id) return;
    
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const y = e.clientY - rect.top;
    const height = rect.height;
    
    let position: 'before' | 'after' | 'inside';
    if (y < height * 0.25) {
      position = 'before';
    } else if (y > height * 0.75) {
      position = 'after';
    } else {
      position = targetButton.buttonType === 'menu' || (targetButton.children && targetButton.children.length > 0) ? 'inside' : 'after';
    }
    
    setDragOverButtonId(targetButton.id);
    setDropPosition(position);
  }, [draggedButtonId]);

  const handleDrop = useCallback((e: React.DragEvent, targetButton: ButtonType) => {
    e.preventDefault();
    
    if (!draggedButtonId || draggedButtonId === targetButton.id || !dropPosition) {
      handleDragEnd();
      return;
    }
    
    reorderMutation.mutate({
      buttonId: draggedButtonId,
      targetId: targetButton.id,
      position: dropPosition,
    });
    
    handleDragEnd();
  }, [draggedButtonId, dropPosition, reorderMutation, handleDragEnd]);

  const toggleMutation = useMutation({
    mutationFn: async ({ id, enabled }: { id: number; enabled: boolean }) => {
      return apiRequest("PATCH", `/api/buttons/${id}`, { isEnabled: enabled });
    },
    onMutate: async ({ id, enabled }) => {
      await queryClient.cancelQueries({ queryKey: ["/api/buttons/tree"] });
      const previousTree = queryClient.getQueryData<ButtonTree>(["/api/buttons/tree"]);
      
      const updateButtonInTree = (buttons: ButtonTree): ButtonTree => {
        return buttons.map(btn => {
          if (btn.id === id) {
            return { ...btn, isEnabled: enabled };
          }
          if (btn.children) {
            return { ...btn, children: updateButtonInTree(btn.children) };
          }
          return btn;
        });
      };
      
      if (previousTree) {
        queryClient.setQueryData<ButtonTree>(["/api/buttons/tree"], updateButtonInTree(previousTree));
      }
      
      return { previousTree };
    },
    onError: (err, variables, context) => {
      if (context?.previousTree) {
        queryClient.setQueryData(["/api/buttons/tree"], context.previousTree);
      }
      toast({
        title: t("toast.error"),
        description: t("toast.buttonStatusError"),
        variant: "destructive",
      });
    },
    onSuccess: () => {
      toast({
        title: t("toast.updated"),
        description: t("toast.buttonStatusUpdated"),
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      return apiRequest("DELETE", `/api/buttons/${id}`);
    },
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: ["/api/buttons/tree"] });
      const previousTree = queryClient.getQueryData<ButtonTree>(["/api/buttons/tree"]);
      
      const removeButtonFromTree = (buttons: ButtonTree): ButtonTree => {
        return buttons
          .filter(btn => btn.id !== id)
          .map(btn => {
            if (btn.children) {
              return { ...btn, children: removeButtonFromTree(btn.children) };
            }
            return btn;
          });
      };
      
      if (previousTree) {
        queryClient.setQueryData<ButtonTree>(["/api/buttons/tree"], removeButtonFromTree(previousTree));
      }
      
      return { previousTree };
    },
    onError: (err, id, context) => {
      if (context?.previousTree) {
        queryClient.setQueryData(["/api/buttons/tree"], context.previousTree);
      }
      toast({
        title: t("toast.error"),
        description: t("toast.buttonDeleteError"),
        variant: "destructive",
      });
    },
    onSuccess: () => {
      setDeletingButton(null);
      setSelectedButton(null);
      toast({
        title: t("toast.deleted"),
        description: t("toast.buttonDeleted"),
      });
    },
  });

  const handleAddRoot = useCallback(() => {
    setNewButtonParentId(null);
    setIsAddingNew(true);
  }, []);

  const handleAddChild = useCallback((parentId: number) => {
    setNewButtonParentId(parentId);
    setIsAddingNew(true);
  }, []);

  const handleEdit = useCallback((button: ButtonType) => {
    setEditingButton(button);
  }, []);

  const handleDelete = useCallback((button: ButtonType) => {
    setDeletingButton(button);
  }, []);

  const handleToggle = useCallback((id: number, enabled: boolean) => {
    toggleMutation.mutate({ id, enabled });
  }, [toggleMutation]);

  const handleSelect = useCallback((button: ButtonType) => {
    setSelectedButton(button);
  }, []);

  const handleCopy = useCallback((button: ButtonType) => {
    setNewButtonParentId(button.parentId);
    setEditingButton({
      ...button,
      id: 0,
      buttonKey: `${button.buttonKey}_copy`,
      textAr: `${button.textAr} (نسخة)`,
      textEn: `${button.textEn} (copy)`,
    });
    setIsAddingNew(true);
  }, []);

  const multiCopyMutation = useMutation({
    mutationFn: async (buttons: any[]) => {
      return apiRequest("POST", "/api/buttons/batch", { buttons });
    },
    onSuccess: (_, variables) => {
      toast({
        title: language === "ar" ? "تم النسخ" : "Copied",
        description: language === "ar" ? `تم نسخ ${variables.length} أزرار` : `${variables.length} buttons copied`,
      });
      queryClient.invalidateQueries({ queryKey: ["/api/buttons/tree"] });
      setMultiCopyButton(null);
      setCopyWithChildren(true);
    },
    onError: () => {
      toast({
        title: t("toast.error"),
        description: language === "ar" ? "فشل نسخ الأزرار" : "Failed to copy buttons",
        variant: "destructive",
      });
    },
  });

  const copyWithChildrenMutation = useMutation({
    mutationFn: async (data: { sourceButtonId: number; copyCount: number; copyNames: any[]; targetParentId: number | null; copyChildren: boolean; overrideServicePrice?: boolean; newServicePrice?: number }) => {
      console.log("Copy with children data:", data);
      return apiRequest("POST", "/api/buttons/copy-with-children", data);
    },
    onSuccess: () => {
      toast({
        title: language === "ar" ? "تم النسخ" : "Copied",
        description: language === "ar" ? `تم نسخ ${multiCopyCount} عناصر مع التفرعات` : `${multiCopyCount} elements copied with branches`,
      });
      queryClient.invalidateQueries({ queryKey: ["/api/buttons/tree"] });
      setMultiCopyButton(null);
      setCopyWithChildren(true);
    },
    onError: () => {
      toast({
        title: t("toast.error"),
        description: language === "ar" ? "فشل نسخ الأزرار" : "Failed to copy buttons",
        variant: "destructive",
      });
    },
  });

  const generateDefaultCopyNames = useCallback((button: ButtonType, count: number) => {
    const names = [];
    const isSpecialType = button.buttonType === "back" || button.buttonType === "cancel" || button.buttonType === "page_separator";
    for (let i = 0; i < count; i++) {
      names.push({
        index: i,
        buttonKey: isSpecialType ? `${button.buttonKey}_${i}` : `Co_ob_${i}`,
        textAr: isSpecialType ? button.textAr : `العنصر المنسوخ رقم #${i}`,
        textEn: isSpecialType ? button.textEn : `Copied object #${i}`,
      });
    }
    return names;
  }, []);

  const handleMultiCopy = useCallback((button: ButtonType) => {
    setMultiCopyButton(button);
    setMultiCopyCount(2);
    setMultiCopyNames(generateDefaultCopyNames(button, 2));
    setShowMultiCopySettings(false);
    setMultiCopyTargetButton(null);
    setMultiCopyInsideMenu(false);
    setMultiCopyExpandedIds(new Set());
    setCopyWithChildren(true);
    setOverrideServicePrice(false);
    const initialPrice = button.isService ? button.price : 0;
    setNewServicePrice(initialPrice);
    setNewServicePriceInput(initialPrice.toString());
  }, [generateDefaultCopyNames]);

  const handleMultiCopyCountChange = useCallback((newCount: number) => {
    const count = Math.min(50, Math.max(1, newCount));
    setMultiCopyCount(count);
    if (multiCopyButton) {
      setMultiCopyNames(generateDefaultCopyNames(multiCopyButton, count));
    }
  }, [multiCopyButton, generateDefaultCopyNames]);

  const handleSelectionChange = useCallback((id: number, selected: boolean) => {
    setSelectedIds(prev => {
      const newSet = new Set(prev);
      if (selected) {
        newSet.add(id);
      } else {
        newSet.delete(id);
      }
      return newSet;
    });
  }, []);

  const updateCopyName = useCallback((index: number, field: 'buttonKey' | 'textAr' | 'textEn', value: string) => {
    setMultiCopyNames(prev => prev.map(item => 
      item.index === index ? { ...item, [field]: value } : item
    ));
  }, []);

  const executeMultiCopy = useCallback(() => {
    if (!multiCopyButton || multiCopyNames.length === 0) return;
    
    // تحديد الموقع بناءً على العنصر المحدد من مستكشف الأزرار
    let targetParentId: number | null = null; // افتراضياً: الجذر
    let targetOrderIndex = 0;
    let insertAfterButtonId: number | null = null;
    
    if (multiCopyTargetButton) {
      // تم تحديد عنصر هدف من المستكشف
      if (multiCopyInsideMenu && (multiCopyTargetButton.buttonType === "menu" || multiCopyTargetButton.buttonType === "page_separator")) {
        // إدراج داخل القائمة أو فاصل الصفحة
        targetParentId = multiCopyTargetButton.id;
        targetOrderIndex = 0;
        insertAfterButtonId = null;
      } else {
        // إدراج بعد العنصر المحدد
        targetParentId = multiCopyTargetButton.parentId;
        insertAfterButtonId = multiCopyTargetButton.id;
        targetOrderIndex = multiCopyTargetButton.orderIndex;
      }
    }
    // إذا لم يتم تحديد عنصر هدف، يتم الإدراج في نهاية القائمة الرئيسية (targetParentId = null)
    
    const shouldCopyChildren = copyWithChildren && 
      (multiCopyButton.buttonType === "menu" || multiCopyButton.buttonType === "page_separator");
    
    // تحديد السعر المستخدم (الجديد أو الأصلي)
    const priceToUse = overrideServicePrice && multiCopyButton.isService ? newServicePrice : multiCopyButton.price;
    
    if (shouldCopyChildren) {
      copyWithChildrenMutation.mutate({
        sourceButtonId: multiCopyButton.id,
        copyCount: multiCopyCount,
        copyNames: multiCopyNames,
        targetParentId: targetParentId,
        copyChildren: true,
        insertAfterButtonId: insertAfterButtonId,
        insertPosition: insertAfterButtonId ? "after" : "end",
        overrideServicePrice: overrideServicePrice,
        newServicePrice: newServicePrice,
      });
    } else {
      const buttonsToCreate = multiCopyNames.map((copyName, idx) => ({
        parentId: targetParentId,
        buttonKey: copyName.buttonKey,
        textAr: copyName.textAr,
        textEn: copyName.textEn,
        buttonType: multiCopyButton.buttonType,
        isEnabled: multiCopyButton.isEnabled,
        isHidden: multiCopyButton.isHidden,
        disabledMessage: multiCopyButton.disabledMessage,
        isService: multiCopyButton.isService,
        price: priceToUse,
        askQuantity: multiCopyButton.askQuantity,
        defaultQuantity: multiCopyButton.defaultQuantity,
        showBackOnQuantity: multiCopyButton.showBackOnQuantity,
        showCancelOnQuantity: multiCopyButton.showCancelOnQuantity,
        backBehavior: multiCopyButton.backBehavior,
        messageAr: multiCopyButton.messageAr,
        messageEn: multiCopyButton.messageEn,
        icon: multiCopyButton.icon,
        orderIndex: targetOrderIndex + idx + 1,
        buttonSize: multiCopyButton.buttonSize,
        insertPosition: insertAfterButtonId ? "after" : multiCopyPosition,
        insertAfterButtonId: insertAfterButtonId,
      }));
      multiCopyMutation.mutate(buttonsToCreate);
    }
  }, [multiCopyButton, multiCopyNames, multiCopyMutation, copyWithChildrenMutation, multiCopyPosition, multiCopyTargetButton, multiCopyInsideMenu, copyWithChildren, multiCopyCount, overrideServicePrice, newServicePrice]);

  const handleEditorClose = useCallback(() => {
    setEditingButton(null);
    setIsAddingNew(false);
    setNewButtonParentId(null);
  }, []);

  const handleEditorSave = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["/api/buttons/tree"] });
    handleEditorClose();
  }, [handleEditorClose]);

  const findButtonById = useCallback((id: number, buttons: ButtonTree): ButtonType | null => {
    for (const btn of buttons) {
      if (btn.id === id) return btn;
      if (btn.children) {
        const found = findButtonById(id, btn.children);
        if (found) return found;
      }
    }
    return null;
  }, []);

  const parentIsRootLevel = useMemo(() => {
    if (!buttonTree || newButtonParentId === null) return false;
    const parentButton = findButtonById(newButtonParentId, buttonTree);
    return parentButton?.parentId === null;
  }, [buttonTree, newButtonParentId, findButtonById]);

  const stats = useMemo(() => {
    if (!buttonTree) return { total: 0, enabled: 0, services: 0 };
    
    let total = 0;
    let enabled = 0;
    let services = 0;

    const count = (buttons: ButtonTree) => {
      for (const btn of buttons) {
        total++;
        if (btn.isEnabled) enabled++;
        if (btn.isService) services++;
        if (btn.children) count(btn.children);
      }
    };

    count(buttonTree);
    return { total, enabled, services };
  }, [buttonTree]);

  const getButtonTypeLabel = (type: string) => {
    switch (type) {
      case "menu": return t("buttonType.menu");
      case "service": return t("buttonType.service");
      case "message": return t("buttonType.message");
      case "link": return t("buttonType.link");
      case "back": return t("buttonType.back");
      case "cancel": return t("buttonType.cancel");
      case "page_separator": return t("buttonType.pageSeparator");
      default: return type;
    }
  };

  const countPages = (children: ButtonType[] | undefined): number => {
    if (!children || children.length === 0) return 0;
    const separators = children.filter(c => c.buttonType === "page_separator");
    return separators.length > 0 ? separators.length + 1 : 0;
  };

  return (
    <div className="flex flex-col lg:flex-row gap-6 h-full">
      <div className="flex-1 min-w-0 space-y-6">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-primary/10 rounded-lg">
                  <FolderTree className="w-6 h-6 text-primary" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">{t("dashboard.totalButtons")}</p>
                  <p className="text-2xl font-bold" data-testid="stat-total">{stats.total}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-green-500/10 rounded-lg">
                  <Eye className="w-6 h-6 text-green-500" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">{t("dashboard.enabledButtons")}</p>
                  <p className="text-2xl font-bold" data-testid="stat-enabled">{stats.enabled}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-amber-500/10 rounded-lg">
                  <DollarSign className="w-6 h-6 text-amber-500" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">{t("dashboard.services")}</p>
                  <p className="text-2xl font-bold" data-testid="stat-services">{stats.services}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Button Tree - File Explorer Style */}
        <Card className="overflow-hidden">
          <CardHeader className="flex flex-col gap-3 space-y-0 pb-4 border-b bg-muted/30">
            {/* First Row: Title, Selection Mode and Add Button */}
            <div className="flex flex-row items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <FolderTree className="w-5 h-5 text-muted-foreground" />
                <CardTitle className="text-base font-medium">{t("dashboard.buttonExplorer")}</CardTitle>
                
                {/* Selection Mode Toggle */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      size="sm"
                      variant={selectionMode ? "default" : "outline"}
                      onClick={() => {
                        setSelectionMode(!selectionMode);
                        if (selectionMode) setSelectedIds(new Set());
                      }}
                      className={selectionMode ? "bg-yellow-500 hover:bg-yellow-600 text-black" : "border-yellow-400 text-yellow-600 hover:bg-yellow-50"}
                      data-testid="toggle-selection-mode"
                    >
                      <CheckSquare className="w-4 h-4 ml-1" />
                      <span className="hidden sm:inline">{language === "ar" ? "تحديد" : "Select"}</span>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{language === "ar" ? "وضع التحديد المتعدد" : "Multi-select mode"}</p>
                  </TooltipContent>
                </Tooltip>
              </div>
              
              <div className="flex items-center gap-2">
                {/* Batch Operations - Show when selection mode is active */}
                {selectionMode && selectedIds.size > 0 && (
                  <div className="flex items-center gap-1 px-2 py-1 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-300">
                    <span className="text-xs text-yellow-700 dark:text-yellow-400">
                      {selectedIds.size} {language === "ar" ? "محدد" : "selected"}
                    </span>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        selectedIds.forEach(id => {
                          const btn = findButtonById(id, buttonTree || []);
                          if (btn) deleteMutation.mutate(id);
                        });
                        setSelectedIds(new Set());
                      }}
                      className="h-6 px-2 text-destructive hover:text-destructive"
                      data-testid="batch-delete"
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setSelectedIds(new Set())}
                      className="h-6 px-2"
                      data-testid="clear-selection"
                    >
                      <X className="w-3 h-3" />
                    </Button>
                  </div>
                )}
                
                <Button size="sm" onClick={handleAddRoot} data-testid="add-root-button">
                  <Plus className="w-4 h-4 ml-2" />
                  <span className="hidden sm:inline">{t("dashboard.newButton")}</span>
                </Button>
              </div>
            </div>
            
            {/* Second Row: Controls - wraps on mobile */}
            <div className="flex items-center gap-2 flex-wrap justify-between sm:justify-end">
              {/* Zoom Slider with +/- buttons */}
              <div className="flex items-center gap-1 order-2 sm:order-1">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      size="icon"
                      variant="ghost"
                      onClick={() => setZoomLevel(Math.max(50, zoomLevel - 10))}
                      disabled={zoomLevel <= 50}
                      data-testid="zoom-out-button"
                    >
                      <Minimize2 className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{t("dashboard.zoomOut")}</p>
                  </TooltipContent>
                </Tooltip>
                
                <Slider
                  value={[zoomLevel]}
                  onValueChange={(value) => setZoomLevel(value[0])}
                  min={50}
                  max={150}
                  step={10}
                  className="w-20 sm:w-24"
                  data-testid="zoom-slider"
                />
                
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      size="icon"
                      variant="ghost"
                      onClick={() => setZoomLevel(Math.min(150, zoomLevel + 10))}
                      disabled={zoomLevel >= 150}
                      data-testid="zoom-in-button"
                    >
                      <Maximize2 className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{t("dashboard.zoomIn")}</p>
                  </TooltipContent>
                </Tooltip>
              </div>
              
              {/* Separator - hidden on mobile */}
              <div className="hidden sm:block w-px h-6 bg-border order-2" />
              
              {/* Expand/Collapse All Button */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    size="icon"
                    variant="ghost"
                    onClick={() => {
                      if (globalExpandState === "collapsed") {
                        setGlobalExpandState("expanded");
                      } else {
                        setGlobalExpandState("collapsed");
                      }
                      setGlobalExpandTrigger(prev => prev + 1);
                    }}
                    data-testid="toggle-expand-all-button"
                    className="order-3"
                  >
                    {globalExpandState === "collapsed" ? (
                      <ChevronDown className="w-4 h-4" />
                    ) : (
                      <ChevronLeft className="w-4 h-4" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{globalExpandState === "collapsed" ? t("dashboard.expandAll") : t("dashboard.collapseAll")}</p>
                </TooltipContent>
              </Tooltip>
              
              {/* Separator - hidden on mobile */}
              <div className="hidden sm:block w-px h-6 bg-border order-4" />
              
              {/* Search Input */}
              <div className="relative order-1 sm:order-5 w-full sm:w-auto">
                <Search className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder={language === "ar" ? "بحث..." : "Search..."}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full sm:w-40 pl-8 pr-3 h-9"
                  data-testid="search-input"
                />
                {searchQuery && (
                  <button
                    className="absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    onClick={() => setSearchQuery("")}
                    data-testid="clear-search-button"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
              
              {/* Preview Toggle (mobile only) */}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowPreview(!showPreview)}
                className="lg:hidden order-6"
              >
                {showPreview ? <EyeOff className="w-4 h-4 ml-2" /> : <Eye className="w-4 h-4 ml-2" />}
                <span className="hidden xs:inline">{t("dashboard.preview")}</span>
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="min-h-[300px]">
              {isLoading ? (
                <TreeSkeleton />
              ) : buttonTree && buttonTree.length > 0 ? (
                <div className="p-2">
                  {buttonTree.map((button, index) => (
                    <TreeNode
                      key={button.id}
                      button={button}
                      level={0}
                      onEdit={handleEdit}
                      onDelete={handleDelete}
                      onToggle={handleToggle}
                      onAddChild={handleAddChild}
                      onCopy={handleCopy}
                      onMultiCopy={handleMultiCopy}
                      selectedId={selectedButton?.id ?? null}
                      onSelect={handleSelect}
                      isLast={index === buttonTree.length - 1}
                      parentLines={[]}
                      searchQuery={searchQuery}
                      language={language}
                      t={t}
                      siblings={buttonTree}
                      zoomLevel={zoomLevel}
                      globalExpandState={globalExpandState}
                      onDragStart={handleDragStart}
                      onDragEnd={handleDragEnd}
                      onDragOver={handleDragOver}
                      onDrop={handleDrop}
                      draggedButtonId={draggedButtonId}
                      dragOverButtonId={dragOverButtonId}
                      dropPosition={dropPosition}
                      selectionMode={selectionMode}
                      selectedIds={selectedIds}
                      onSelectionChange={handleSelectionChange}
                    />
                  ))}
                </div>
              ) : (
                <div className="text-center py-16">
                  <Folder className="w-16 h-16 mx-auto text-muted-foreground/30 mb-4" />
                  <h3 className="text-lg font-medium mb-2">{t("dashboard.noButtonsYet")}</h3>
                  <p className="text-muted-foreground mb-4 text-sm">
                    {t("dashboard.startAddingButton")}
                  </p>
                  <Button onClick={handleAddRoot}>
                    <Plus className="w-4 h-4 ml-2" />
                    {t("dashboard.addNewButton")}
                  </Button>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Selected button details */}
        {selectedButton && (
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <span className="text-xl">{selectedButton.icon}</span>
                  {language === "en" ? selectedButton.textEn : selectedButton.textAr}
                </CardTitle>
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="outline" onClick={() => handleEdit(selectedButton)}>
                    <Pencil className="w-4 h-4 ml-2" />
                    {t("dashboard.edit")}
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">{t("dashboard.key")}</span>
                  <span className="mr-2 font-mono text-xs bg-muted px-2 py-1 rounded">
                    {selectedButton.buttonKey}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground">{t("dashboard.type")}</span>
                  <span className="mr-2">
                    {getButtonTypeLabel(selectedButton.buttonType)}
                  </span>
                </div>
                {selectedButton.isService && (
                  <div>
                    <span className="text-muted-foreground">{t("dashboard.price")}</span>
                    <span className="mr-2 font-bold text-green-600">${selectedButton.price}</span>
                  </div>
                )}
                <div>
                  <span className="text-muted-foreground">{t("dashboard.status")}</span>
                  <Badge variant={selectedButton.isEnabled ? "default" : "secondary"} className="mr-2">
                    {selectedButton.isEnabled ? t("dashboard.enabled") : t("dashboard.disabled")}
                  </Badge>
                </div>
              </div>
              {(selectedButton.messageAr || selectedButton.messageEn) && (
                <div className="mt-4 p-3 bg-muted/50 rounded-lg">
                  <span className="text-muted-foreground text-xs">{t("dashboard.message")}</span>
                  <p className="mt-1">{language === "en" ? selectedButton.messageEn : selectedButton.messageAr}</p>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>

      {/* Telegram Preview */}
      {showPreview && (
        <div className="lg:w-96 flex-shrink-0">
          <TelegramPreview
            selectedButton={selectedButton}
            buttonTree={buttonTree ?? []}
          />
        </div>
      )}

      {/* Dialogs */}
      <ButtonEditorDialog
        open={isAddingNew || !!editingButton}
        onOpenChange={(open) => {
          if (!open) handleEditorClose();
        }}
        button={editingButton}
        parentId={newButtonParentId}
        parentIsRootLevel={parentIsRootLevel}
        onSave={handleEditorSave}
      />

      <DeleteConfirmDialog
        open={!!deletingButton}
        onOpenChange={(open) => {
          if (!open) setDeletingButton(null);
        }}
        onConfirm={() => {
          if (deletingButton) {
            deleteMutation.mutate(deletingButton.id);
          }
        }}
        buttonName={deletingButton?.textAr ?? ""}
        isLoading={deleteMutation.isPending}
      />

      {/* Multi Copy Dialog - Enhanced with Yellow Theme */}
      <Dialog open={!!multiCopyButton} onOpenChange={(open) => {
        if (!open) {
          setMultiCopyButton(null);
          setShowMultiCopySettings(false);
          setMultiCopyTargetButton(null);
          setMultiCopyInsideMenu(false);
          setMultiCopyExpandedIds(new Set());
          setCopyWithChildren(true);
        }
      }}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Copy className="w-5 h-5 text-yellow-500" />
              {language === "ar" ? "نسخ العنصر" : "Copy Element"}
            </DialogTitle>
          </DialogHeader>
          
          <div className="flex-1 overflow-y-auto">
            {/* Main Section - Yellow Theme */}
            <div className="space-y-4 p-4 rounded-lg border-2 border-yellow-400 bg-yellow-50 dark:bg-yellow-900/20">
              <div className="space-y-2">
                <Label className="text-yellow-700 dark:text-yellow-400">
                  {language === "ar" ? "الزر المراد نسخه" : "Button to copy"}
                </Label>
                <div className="p-3 bg-white dark:bg-background rounded-lg border border-yellow-300">
                  <span className="text-lg ml-2">{multiCopyButton?.icon}</span>
                  <span className="font-medium">{language === "ar" ? multiCopyButton?.textAr : multiCopyButton?.textEn}</span>
                </div>
              </div>
              
              <div className="flex items-center gap-4">
                <div className="flex-1 space-y-2">
                  <Label className="text-yellow-700 dark:text-yellow-400">
                    {language === "ar" ? "عدد النسخ" : "Number of copies"}
                  </Label>
                  <Input
                    type="number"
                    min={1}
                    max={50}
                    value={multiCopyCount}
                    onChange={(e) => handleMultiCopyCountChange(parseInt(e.target.value) || 1)}
                    className="border-yellow-300 focus:border-yellow-500"
                    data-testid="input-multi-copy-count"
                  />
                </div>
                
                {/* Settings Button */}
                <div className="pt-6">
                  <Button
                    type="button"
                    variant={showMultiCopySettings ? "default" : "outline"}
                    size="icon"
                    onClick={() => setShowMultiCopySettings(!showMultiCopySettings)}
                    className={showMultiCopySettings ? "bg-yellow-500 hover:bg-yellow-600" : "border-yellow-400 text-yellow-600 hover:bg-yellow-50"}
                    data-testid="button-copy-settings"
                  >
                    <Settings className="w-4 h-4" />
                  </Button>
                </div>
              </div>
              
              {/* Copy with children switch - يظهر فقط للقوائم وفواصل الصفحات */}
              {multiCopyButton && (multiCopyButton.buttonType === "menu" || multiCopyButton.buttonType === "page_separator") && (
                <div className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-300">
                  <div className="flex items-center gap-2">
                    <FolderTree className="w-4 h-4 text-green-600" />
                    <Label className="text-sm text-green-700 dark:text-green-400 cursor-pointer" htmlFor="copy-children-switch">
                      {language === "ar" ? "نسخ العناصر الفرعية (الأبناء والتفرعات)" : "Copy child elements (children & branches)"}
                    </Label>
                  </div>
                  <Switch
                    id="copy-children-switch"
                    checked={copyWithChildren}
                    onCheckedChange={setCopyWithChildren}
                    className="data-[state=checked]:bg-green-500"
                    data-testid="switch-copy-children"
                  />
                </div>
              )}
              
              {/* Override service price - يظهر للخدمات المدفوعة أو القوائم/فواصل الصفحات (للعناصر الفرعية) */}
              {multiCopyButton && (multiCopyButton.isService || multiCopyButton.buttonType === "menu" || multiCopyButton.buttonType === "page_separator") && (
                <div className="space-y-3 p-3 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg border border-emerald-300">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <DollarSign className="w-4 h-4 text-emerald-600" />
                      <Label className="text-sm text-emerald-700 dark:text-emerald-400 cursor-pointer" htmlFor="override-price-switch">
                        {language === "ar" ? "تغيير سعر الخدمات المدفوعة" : "Override service prices"}
                      </Label>
                    </div>
                    <Switch
                      id="override-price-switch"
                      checked={overrideServicePrice}
                      onCheckedChange={setOverrideServicePrice}
                      className="data-[state=checked]:bg-emerald-500"
                      data-testid="switch-override-price"
                    />
                  </div>
                  
                  {overrideServicePrice && (
                    <div className="flex items-center gap-3">
                      <Label className="text-sm text-emerald-700 dark:text-emerald-400 whitespace-nowrap">
                        {language === "ar" ? "السعر الجديد:" : "New price:"}
                      </Label>
                      <div className="flex items-center gap-1 flex-1">
                        <span className="text-emerald-600 font-bold">$</span>
                        <Input
                          type="text"
                          inputMode="decimal"
                          value={newServicePriceInput}
                          onChange={(e) => {
                            const val = e.target.value;
                            // السماح بإدخال الأرقام والنقطة العشرية فقط
                            if (val === '' || /^[0-9]*\.?[0-9]*$/.test(val)) {
                              setNewServicePriceInput(val);
                              const parsed = parseFloat(val);
                              if (!isNaN(parsed)) {
                                setNewServicePrice(parsed);
                              } else if (val === '' || val === '.') {
                                setNewServicePrice(0);
                              }
                            }
                          }}
                          onBlur={() => {
                            // عند مغادرة الحقل، تأكد من أن القيمة صحيحة
                            if (newServicePriceInput === '' || newServicePriceInput === '.') {
                              setNewServicePriceInput('0');
                              setNewServicePrice(0);
                            } else {
                              const parsed = parseFloat(newServicePriceInput);
                              if (!isNaN(parsed)) {
                                setNewServicePriceInput(parsed.toString());
                                setNewServicePrice(parsed);
                              }
                            }
                          }}
                          className="border-emerald-300 focus:border-emerald-500 h-8"
                          data-testid="input-new-price"
                        />
                      </div>
                    </div>
                  )}
                  
                  <p className="text-xs text-emerald-600/80">
                    {language === "ar" 
                      ? "سيتم تطبيق هذا السعر على جميع العناصر من نوع خدمة مدفوعة" 
                      : "This price will be applied to all service-type elements"}
                  </p>
                </div>
              )}
              
              {/* Position Selector - Compact Button Tree Explorer */}
              <div className="space-y-2">
                <Label className="text-yellow-700 dark:text-yellow-400">
                  {language === "ar" ? "موقع الإضافة" : "Insert Position"}
                </Label>
                
                {/* Compact Tree Explorer */}
                <div className="bg-white dark:bg-background rounded-lg border border-yellow-300 max-h-48 overflow-y-auto">
                  {/* Root option - insert at root level */}
                  <div
                    className={`flex items-center gap-2 p-2 cursor-pointer transition-colors ${
                      !multiCopyTargetButton 
                        ? "bg-yellow-200 dark:bg-yellow-800/50" 
                        : "hover:bg-yellow-100 dark:hover:bg-yellow-900/30"
                    }`}
                    onClick={() => {
                      setMultiCopyTargetButton(null);
                      setMultiCopyInsideMenu(false);
                    }}
                    data-testid="copy-target-root"
                  >
                    <FolderTree className="w-4 h-4 text-yellow-600" />
                    <span className="text-sm font-medium">
                      {language === "ar" ? "القائمة الرئيسية (النهاية)" : "Root Menu (End)"}
                    </span>
                  </div>
                  
                  {/* Tree items */}
                  {buttonTree && (
                    <div className="border-t border-yellow-200 dark:border-yellow-700">
                      {(() => {
                        const renderMiniTree = (buttons: ButtonTree, level: number = 0): JSX.Element[] => {
                          return buttons.flatMap((btn) => {
                            const isSelected = multiCopyTargetButton?.id === btn.id;
                            const hasChildren = btn.children && btn.children.length > 0;
                            const isExpandable = btn.buttonType === "menu" || btn.buttonType === "page_separator";
                            const isExpanded = multiCopyExpandedIds.has(btn.id);
                            
                            const elements: JSX.Element[] = [
                              <div
                                key={btn.id}
                                className={`flex items-center gap-1 p-1.5 cursor-pointer transition-colors ${
                                  isSelected 
                                    ? "bg-yellow-200 dark:bg-yellow-800/50" 
                                    : "hover:bg-yellow-100 dark:hover:bg-yellow-900/30"
                                }`}
                                style={{ paddingRight: `${(level * 16) + 8}px` }}
                                onClick={() => {
                                  setMultiCopyTargetButton(btn);
                                  // دائماً إعادة تعيين خيار "إدراج داخل" إلى false عند تحديد زر جديد
                                  // المستخدم يجب أن يفعله يدوياً إذا أراد الإدراج داخل القائمة
                                  setMultiCopyInsideMenu(false);
                                }}
                                data-testid={`copy-target-${btn.id}`}
                              >
                                {/* Expand/Collapse button for menus */}
                                {isExpandable && hasChildren ? (
                                  <Button
                                    type="button"
                                    variant="ghost"
                                    size="icon"
                                    className="h-5 w-5 p-0"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setMultiCopyExpandedIds(prev => {
                                        const next = new Set(prev);
                                        if (next.has(btn.id)) {
                                          next.delete(btn.id);
                                        } else {
                                          next.add(btn.id);
                                        }
                                        return next;
                                      });
                                    }}
                                  >
                                    {isExpanded ? (
                                      <ChevronDown className="w-3 h-3" />
                                    ) : (
                                      <ChevronLeft className="w-3 h-3" />
                                    )}
                                  </Button>
                                ) : (
                                  <div className="w-5" />
                                )}
                                
                                {/* Icon */}
                                <span className="text-sm">{btn.icon || (btn.buttonType === "menu" ? "📁" : "📄")}</span>
                                
                                {/* Name */}
                                <span className="text-xs truncate flex-1">
                                  {language === "ar" ? btn.textAr : btn.textEn}
                                </span>
                                
                                {/* Type badge */}
                                {btn.buttonType === "menu" && (
                                  <Badge variant="outline" className="text-[10px] px-1 py-0 h-4">
                                    {language === "ar" ? "قائمة" : "menu"}
                                  </Badge>
                                )}
                                {btn.buttonType === "page_separator" && (
                                  <Badge variant="outline" className="text-[10px] px-1 py-0 h-4">
                                    {language === "ar" ? "فاصل" : "sep"}
                                  </Badge>
                                )}
                              </div>
                            ];
                            
                            // Render children if expanded
                            if (isExpanded && hasChildren) {
                              elements.push(...renderMiniTree(btn.children!, level + 1));
                            }
                            
                            return elements;
                          });
                        };
                        
                        return renderMiniTree(buttonTree);
                      })()}
                    </div>
                  )}
                </div>
                
                {/* Insert Inside Switch - shows only for menu or page_separator */}
                {multiCopyTargetButton && (multiCopyTargetButton.buttonType === "menu" || multiCopyTargetButton.buttonType === "page_separator") && (
                  <div className="flex items-center justify-between p-2 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg mt-2">
                    <Label className="text-sm text-yellow-700 dark:text-yellow-400 cursor-pointer" htmlFor="insert-inside-switch">
                      {multiCopyTargetButton.buttonType === "menu" 
                        ? (language === "ar" ? "إدراج داخل القائمة" : "Insert inside menu")
                        : (language === "ar" ? "إدراج داخل فاصل الصفحة" : "Insert inside page separator")
                      }
                    </Label>
                    <Switch
                      id="insert-inside-switch"
                      checked={multiCopyInsideMenu}
                      onCheckedChange={setMultiCopyInsideMenu}
                      data-testid="switch-insert-inside"
                    />
                  </div>
                )}
                
                {/* Selected location display */}
                {multiCopyTargetButton && (
                  <div className="text-xs text-muted-foreground p-2 bg-muted/50 rounded">
                    {multiCopyInsideMenu 
                      ? (language === "ar" 
                          ? `سيتم الإدراج داخل: ${multiCopyTargetButton.textAr}` 
                          : `Will insert inside: ${multiCopyTargetButton.textEn}`)
                      : (language === "ar" 
                          ? `سيتم الإدراج بعد: ${multiCopyTargetButton.textAr}` 
                          : `Will insert after: ${multiCopyTargetButton.textEn}`)
                    }
                  </div>
                )}
              </div>
            </div>
            
            {/* Settings Panel - Editable Names */}
            {showMultiCopySettings && (
              <div className="mt-4 space-y-3">
                <Label className="text-sm font-medium">
                  {language === "ar" ? "إعدادات الأسماء والمفاتيح" : "Names & Keys Settings"}
                </Label>
                <ScrollArea className="h-64 rounded-lg border">
                  <div className="p-3 space-y-4">
                    {multiCopyNames.map((copyName, idx) => {
                      const isSpecialType = multiCopyButton?.buttonType === "back" || 
                                           multiCopyButton?.buttonType === "cancel" || 
                                           multiCopyButton?.buttonType === "page_separator";
                      return (
                        <div key={copyName.index} className="space-y-2 p-3 bg-muted/50 rounded-lg">
                          {/* Separator line */}
                          <div className="flex items-center gap-2 text-muted-foreground text-xs">
                            <div className="flex-1 h-px bg-yellow-400/60" />
                            <span>_-_</span>
                            <div className="flex-1 h-px bg-yellow-400/60" />
                          </div>
                          
                          {/* Key Field */}
                          <div className="space-y-1">
                            <Label className="text-xs text-yellow-600 dark:text-yellow-400">
                              {language === "ar" ? "المفتاح" : "Key"}
                            </Label>
                            <Input
                              value={copyName.buttonKey}
                              onChange={(e) => updateCopyName(copyName.index, 'buttonKey', e.target.value)}
                              disabled={isSpecialType}
                              className={`text-sm font-mono ${isSpecialType ? 'opacity-50 cursor-not-allowed' : 'border-yellow-300'}`}
                              dir="ltr"
                              data-testid={`input-copy-key-${idx}`}
                            />
                          </div>
                          
                          {/* Names Row */}
                          <div className="grid grid-cols-2 gap-3">
                            {/* English Name - Left */}
                            <div className="space-y-1">
                              <Label className="text-xs text-muted-foreground">EN</Label>
                              <Input
                                value={copyName.textEn}
                                onChange={(e) => updateCopyName(copyName.index, 'textEn', e.target.value)}
                                disabled={isSpecialType}
                                className={`text-sm ${isSpecialType ? 'opacity-50 cursor-not-allowed' : ''}`}
                                dir="ltr"
                                data-testid={`input-copy-en-${idx}`}
                              />
                            </div>
                            
                            {/* Arabic Name - Right */}
                            <div className="space-y-1">
                              <Label className="text-xs text-muted-foreground">عربي</Label>
                              <Input
                                value={copyName.textAr}
                                onChange={(e) => updateCopyName(copyName.index, 'textAr', e.target.value)}
                                disabled={isSpecialType}
                                className={`text-sm ${isSpecialType ? 'opacity-50 cursor-not-allowed' : ''}`}
                                dir="rtl"
                                data-testid={`input-copy-ar-${idx}`}
                              />
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </ScrollArea>
              </div>
            )}
          </div>
          
          <DialogFooter className="gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => {
              setMultiCopyButton(null);
              setShowMultiCopySettings(false);
              setMultiCopyTargetButton(null);
              setMultiCopyInsideMenu(false);
              setMultiCopyExpandedIds(new Set());
              setCopyWithChildren(true);
            }}>
              {language === "ar" ? "إلغاء" : "Cancel"}
            </Button>
            <Button 
              onClick={executeMultiCopy} 
              disabled={multiCopyMutation.isPending}
              className="bg-yellow-500 hover:bg-yellow-600 text-black"
            >
              {multiCopyMutation.isPending && <span className="animate-spin ml-2">...</span>}
              <Copy className="w-4 h-4 ml-2" />
              {language === "ar" ? `نسخ ${multiCopyCount} عناصر` : `Copy ${multiCopyCount} elements`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
