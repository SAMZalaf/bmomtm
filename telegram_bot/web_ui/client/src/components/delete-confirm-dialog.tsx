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
import { Loader2, AlertTriangle } from "lucide-react";

interface DeleteConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  buttonName: string;
  isLoading?: boolean;
}

export function DeleteConfirmDialog({
  open,
  onOpenChange,
  onConfirm,
  buttonName,
  isLoading = false,
}: DeleteConfirmDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-destructive/10 rounded-full">
              <AlertTriangle className="w-6 h-6 text-destructive" />
            </div>
            <AlertDialogTitle>تأكيد الحذف</AlertDialogTitle>
          </div>
          <AlertDialogDescription className="text-base">
            هل أنت متأكد من حذف الزر <strong>"{buttonName}"</strong>؟
            <br />
            <span className="text-destructive">
              سيتم حذف جميع الأزرار الفرعية أيضاً. هذا الإجراء لا يمكن التراجع عنه.
            </span>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="gap-2">
          <AlertDialogCancel disabled={isLoading}>إلغاء</AlertDialogCancel>
          <AlertDialogAction
            onClick={(e) => {
              e.preventDefault();
              onConfirm();
            }}
            disabled={isLoading}
            className="bg-destructive hover:bg-destructive/90"
            data-testid="confirm-delete"
          >
            {isLoading && <Loader2 className="w-4 h-4 ml-2 animate-spin" />}
            نعم، احذف
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
