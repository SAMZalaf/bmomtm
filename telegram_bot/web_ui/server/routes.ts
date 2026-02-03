import type { Express } from "express";
import type { Server } from "http";
import { storage } from "./storage";
import { insertButtonSchema } from "@shared/schema";
import type { ActivityLogAction } from "@shared/schema";
import { z } from "zod";
import crypto from "crypto";

// توليد توكن عشوائي
function generateToken(): string {
  return crypto.randomBytes(32).toString("hex");
}

// تخزين التوكنات النشطة
const activeTokens = new Set<string>();

export async function registerRoutes(server: Server, app: Express): Promise<void> {
  // ============ Authentication Endpoints ============
  
  // Login endpoint
  app.post("/api/auth/login", async (req, res) => {
    try {
      const { password } = req.body;
      
      if (!password) {
        return res.status(400).json({ success: false, message: "كلمة المرور مطلوبة" });
      }
      
      // قراءة كلمة المرور من قاعدة البيانات
      const adminPassword = await storage.getAdminPassword();
      
      if (password === adminPassword) {
        const token = generateToken();
        activeTokens.add(token);
        
        // حذف التوكن بعد 24 ساعة
        setTimeout(() => {
          activeTokens.delete(token);
        }, 24 * 60 * 60 * 1000);
        
        return res.json({ success: true, token });
      } else {
        return res.status(401).json({ success: false, message: "كلمة المرور غير صحيحة" });
      }
    } catch (error) {
      console.error("Error during login:", error);
      res.status(500).json({ success: false, message: "حدث خطأ في الخادم" });
    }
  });
  
  // Verify token endpoint
  app.post("/api/auth/verify", async (req, res) => {
    try {
      const { token } = req.body;
      
      if (!token) {
        return res.status(400).json({ valid: false });
      }
      
      const isValid = activeTokens.has(token);
      return res.json({ valid: isValid });
    } catch (error) {
      console.error("Error verifying token:", error);
      res.status(500).json({ valid: false });
    }
  });
  
  // Logout endpoint
  app.post("/api/auth/logout", async (req, res) => {
    try {
      const { token } = req.body;
      
      if (token) {
        activeTokens.delete(token);
      }
      
      return res.json({ success: true });
    } catch (error) {
      console.error("Error during logout:", error);
      res.status(500).json({ success: false });
    }
  });
  
  
  // Update password
  app.post("/api/auth/password", async (req, res) => {
    try {
      const { newPassword } = req.body;
      
      if (!newPassword || newPassword.length < 6) {
        return res.status(400).json({ success: false, message: "كلمة المرور يجب أن تكون 6 أحرف على الأقل" });
      }
      
      // حفظ كلمة المرور في قاعدة البيانات
      await storage.saveAdminPassword(newPassword);
      return res.json({ success: true, message: "تم تغيير كلمة المرور بنجاح" });
    } catch (error) {
      console.error("Error updating password:", error);
      res.status(500).json({ success: false, message: "حدث خطأ في تغيير كلمة المرور" });
    }
  });
  // Get all buttons as tree
  app.get("/api/buttons/tree", async (req, res) => {
    try {
      const tree = await storage.getButtonTree();
      res.json(tree);
    } catch (error) {
      console.error("Error fetching button tree:", error);
      res.status(500).json({ error: "Failed to fetch buttons" });
    }
  });

  // Get all buttons flat
  app.get("/api/buttons", async (req, res) => {
    try {
      const buttons = await storage.getAllButtons();
      res.json(buttons);
    } catch (error) {
      console.error("Error fetching buttons:", error);
      res.status(500).json({ error: "Failed to fetch buttons" });
    }
  });

  // Get button by ID
  app.get("/api/buttons/:id", async (req, res) => {
    try {
      const id = parseInt(req.params.id);
      if (isNaN(id)) {
        return res.status(400).json({ error: "Invalid button ID" });
      }
      
      const button = await storage.getButtonById(id);
      if (!button) {
        return res.status(404).json({ error: "Button not found" });
      }
      
      res.json(button);
    } catch (error) {
      console.error("Error fetching button:", error);
      res.status(500).json({ error: "Failed to fetch button" });
    }
  });

  // Create button
  app.post("/api/buttons", async (req, res) => {
    try {
      const validatedData = insertButtonSchema.parse(req.body);
      const button = await storage.createButton(validatedData);
      
      await storage.logActivity({
        action: 'button_created',
        entityType: 'button',
        entityId: button.id,
        entityName: button.textAr,
        details: `Button "${button.textAr}" (${button.buttonKey}) created with type: ${button.buttonType}`
      });
      
      console.log(`[LOG] Button created: ${button.textAr} (ID: ${button.id})`);
      res.status(201).json(button);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ error: "Validation failed", details: error.errors });
      }
      console.error("Error creating button:", error);
      res.status(500).json({ error: "Failed to create button" });
    }
  });

  // Update button
  app.patch("/api/buttons/:id", async (req, res) => {
    try {
      const id = parseInt(req.params.id);
      if (isNaN(id)) {
        return res.status(400).json({ error: "Invalid button ID" });
      }
      
      const updates = insertButtonSchema.partial().parse(req.body);
      const oldButton = await storage.getButtonById(id);
      const button = await storage.updateButton(id, updates);
      
      if (!button) {
        return res.status(404).json({ error: "Button not found" });
      }
      
      if ('isEnabled' in updates && oldButton) {
        const action = updates.isEnabled ? 'button_enabled' : 'button_disabled';
        await storage.logActivity({
          action,
          entityType: 'button',
          entityId: button.id,
          entityName: button.textAr,
          details: `Button "${button.textAr}" ${updates.isEnabled ? 'enabled' : 'disabled'}`
        });
        console.log(`[LOG] Button ${updates.isEnabled ? 'enabled' : 'disabled'}: ${button.textAr} (ID: ${button.id})`);
      } else {
        await storage.logActivity({
          action: 'button_updated',
          entityType: 'button',
          entityId: button.id,
          entityName: button.textAr,
          details: `Button "${button.textAr}" updated`
        });
        console.log(`[LOG] Button updated: ${button.textAr} (ID: ${button.id})`);
      }
      
      res.json(button);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ error: "Validation failed", details: error.errors });
      }
      console.error("Error updating button:", error);
      res.status(500).json({ error: "Failed to update button" });
    }
  });

  // Delete button
  app.delete("/api/buttons/:id", async (req, res) => {
    try {
      const id = parseInt(req.params.id);
      if (isNaN(id)) {
        return res.status(400).json({ error: "Invalid button ID" });
      }
      
      const button = await storage.getButtonById(id);
      const success = await storage.deleteButton(id);
      if (!success) {
        return res.status(404).json({ error: "Button not found" });
      }
      
      if (button) {
        await storage.logActivity({
          action: 'button_deleted',
          entityType: 'button',
          entityId: id,
          entityName: button.textAr,
          details: `Button "${button.textAr}" (${button.buttonKey}) deleted`
        });
        console.log(`[LOG] Button deleted: ${button.textAr} (ID: ${id})`);
      }
      
      res.status(204).send();
    } catch (error) {
      console.error("Error deleting button:", error);
      res.status(500).json({ error: "Failed to delete button" });
    }
  });

  // Import buttons
  app.post("/api/buttons/import", async (req, res) => {
    try {
      const { buttons } = req.body;
      if (!Array.isArray(buttons)) {
        return res.status(400).json({ error: "Invalid import data" });
      }
      
      await storage.importButtons(buttons);
      
      await storage.logActivity({
        action: 'buttons_imported',
        entityType: 'system',
        entityId: null,
        entityName: 'Buttons Import',
        details: `${buttons.length} root buttons imported`
      });
      console.log(`[LOG] Buttons imported: ${buttons.length} root buttons`);
      
      res.json({ success: true, message: "Buttons imported successfully" });
    } catch (error) {
      console.error("Error importing buttons:", error);
      res.status(500).json({ error: "Failed to import buttons" });
    }
  });

  // Reset buttons to default
  app.post("/api/buttons/reset", async (req, res) => {
    try {
      await storage.resetToDefaults();
      
      await storage.logActivity({
        action: 'buttons_reset',
        entityType: 'system',
        entityId: null,
        entityName: 'Buttons Reset',
        details: 'All buttons reset to default values'
      });
      console.log('[LOG] Buttons reset to default');
      
      res.json({ success: true, message: "Buttons reset to default" });
    } catch (error) {
      console.error("Error resetting buttons:", error);
      res.status(500).json({ error: "Failed to reset buttons" });
    }
  });

  // Batch create buttons - لإنشاء عدة أزرار دفعة واحدة (للتكرار)
  app.post("/api/buttons/batch", async (req, res) => {
    try {
      const { buttons } = req.body;
      if (!Array.isArray(buttons) || buttons.length === 0) {
        return res.status(400).json({ error: "Invalid buttons data" });
      }
      
      const createdButtons = [];
      for (const buttonData of buttons) {
        const validatedData = insertButtonSchema.parse(buttonData);
        const button = await storage.createButton(validatedData);
        createdButtons.push(button);
      }
      
      await storage.logActivity({
        action: 'buttons_batch_created',
        entityType: 'system',
        entityId: null,
        entityName: 'Batch Create',
        details: `${createdButtons.length} buttons created in batch`
      });
      
      console.log(`[LOG] Batch created: ${createdButtons.length} buttons`);
      res.status(201).json({ success: true, buttons: createdButtons });
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ error: "Validation failed", details: error.errors });
      }
      console.error("Error batch creating buttons:", error);
      res.status(500).json({ error: "Failed to batch create buttons" });
    }
  });

  // Copy button with children - نسخ زر مع جميع أبنائه
  app.post("/api/buttons/copy-with-children", async (req, res) => {
    try {
      const { sourceButtonId, copyCount, copyNames, targetParentId, copyChildren, insertAfterButtonId, insertPosition, overrideServicePrice, newServicePrice: rawNewServicePrice } = req.body;
      
      // تحويل السعر إلى رقم إذا كان موجوداً
      const newServicePrice = rawNewServicePrice !== undefined ? parseFloat(rawNewServicePrice) : undefined;
      const isValidPrice = newServicePrice !== undefined && !isNaN(newServicePrice);
      
      console.log("[LOG] Copy with children request:", { sourceButtonId, copyCount, overrideServicePrice, rawNewServicePrice, newServicePrice, isValidPrice });
      
      if (typeof sourceButtonId !== 'number' || typeof copyCount !== 'number') {
        return res.status(400).json({ error: "Invalid parameters" });
      }
      
      const sourceButton = await storage.getButtonById(sourceButtonId);
      if (!sourceButton) {
        return res.status(404).json({ error: "Source button not found" });
      }
      
      // الحصول على ترتيب البداية للإدراج
      let startOrderIndex = 0;
      const finalParentId = targetParentId !== undefined ? targetParentId : sourceButton.parentId;
      
      if (insertAfterButtonId && insertPosition === "after") {
        // الإدراج بعد زر معين - الحصول على ترتيب الزر الهدف
        const targetButton = await storage.getButtonById(insertAfterButtonId);
        if (targetButton) {
          startOrderIndex = targetButton.orderIndex + 1;
          // تحريك الأزرار الموجودة لإفساح المجال
          const allButtons = await storage.getAllButtons();
          const siblingsToUpdate = allButtons.filter(
            b => b.parentId === finalParentId && b.orderIndex >= startOrderIndex
          );
          for (const sibling of siblingsToUpdate) {
            await storage.updateButton(sibling.id, { orderIndex: sibling.orderIndex + copyCount });
          }
        }
      } else if (insertPosition === "end" || !insertAfterButtonId) {
        // الإدراج في نهاية القائمة المستهدفة
        const allButtons = await storage.getAllButtons();
        const siblings = allButtons.filter(b => b.parentId === finalParentId);
        if (siblings.length > 0) {
          startOrderIndex = Math.max(...siblings.map(b => b.orderIndex)) + 1;
        }
      }
      
      const createdButtons = [];
      
      // دالة مساعدة لنسخ زر مع أبنائه بشكل تكراري
      const copyButtonRecursive = async (
        button: any, 
        newParentId: number | null, 
        orderIndex: number,
        customData?: { buttonKey: string; textAr: string; textEn: string }
      ): Promise<any> => {
        // تطبيق السعر الجديد إذا كان العنصر من نوع خدمة مدفوعة وتم تفعيل تغيير السعر
        const shouldApplyPrice = overrideServicePrice && button.isService && isValidPrice;
        const finalPrice = shouldApplyPrice ? newServicePrice : button.price;
        
        console.log("[LOG] copyButtonRecursive:", { 
          buttonKey: button.buttonKey, 
          isService: button.isService, 
          originalPrice: button.price, 
          finalPrice, 
          overrideServicePrice, 
          newServicePrice,
          isValidPrice,
          shouldApplyPrice
        });
        
        const buttonData = {
          buttonKey: customData?.buttonKey || `${button.buttonKey}_copy_${Date.now()}`,
          textAr: customData?.textAr || button.textAr,
          textEn: customData?.textEn || button.textEn,
          buttonType: button.buttonType,
          isEnabled: button.isEnabled,
          isHidden: button.isHidden,
          disabledMessage: button.disabledMessage,
          isService: button.isService,
          price: finalPrice,
          askQuantity: button.askQuantity,
          defaultQuantity: button.defaultQuantity,
          showBackOnQuantity: button.showBackOnQuantity,
          showCancelOnQuantity: button.showCancelOnQuantity,
          backBehavior: button.backBehavior,
          messageAr: button.messageAr,
          messageEn: button.messageEn,
          icon: button.icon,
          orderIndex: orderIndex,
          buttonSize: button.buttonSize,
          parentId: newParentId,
        };
        
        const newButton = await storage.createButton(buttonData);
        
        // نسخ الأبناء إذا كان copyChildren مفعلاً
        if (copyChildren && button.children && button.children.length > 0) {
          let childOrderIndex = 0;
          for (const child of button.children) {
            await copyButtonRecursive(child, newButton.id, childOrderIndex);
            childOrderIndex++;
          }
        }
        
        return newButton;
      };
      
      // الحصول على الزر مع أبنائه
      const buttonTree = await storage.getButtonTree();
      const findButtonWithChildren = (buttons: any[], id: number): any => {
        for (const btn of buttons) {
          if (btn.id === id) return btn;
          if (btn.children) {
            const found = findButtonWithChildren(btn.children, id);
            if (found) return found;
          }
        }
        return null;
      };
      
      const sourceWithChildren = findButtonWithChildren(buttonTree, sourceButtonId);
      
      // إنشاء النسخ
      for (let i = 0; i < copyCount; i++) {
        const customData = copyNames && copyNames[i] ? {
          buttonKey: copyNames[i].buttonKey,
          textAr: copyNames[i].textAr,
          textEn: copyNames[i].textEn,
        } : undefined;
        
        const newButton = await copyButtonRecursive(
          sourceWithChildren || sourceButton, 
          finalParentId,
          startOrderIndex + i,
          customData
        );
        createdButtons.push(newButton);
      }
      
      await storage.logActivity({
        action: 'buttons_batch_created',
        entityType: 'system',
        entityId: null,
        entityName: 'Copy with Children',
        details: `${createdButtons.length} buttons copied${copyChildren ? ' with children' : ''}`
      });
      
      console.log(`[LOG] Copied with children: ${createdButtons.length} buttons`);
      res.status(201).json({ success: true, buttons: createdButtons });
    } catch (error) {
      console.error("Error copying buttons with children:", error);
      res.status(500).json({ error: "Failed to copy buttons" });
    }
  });

  // Reorder buttons (drag and drop)
  app.post("/api/buttons/reorder", async (req, res) => {
    try {
      const { buttonId, targetId, position } = req.body;
      
      if (typeof buttonId !== 'number' || typeof targetId !== 'number') {
        return res.status(400).json({ error: "Invalid button IDs" });
      }
      
      if (!['before', 'after', 'inside'].includes(position)) {
        return res.status(400).json({ error: "Invalid position. Use 'before', 'after', or 'inside'" });
      }
      
      const success = await storage.reorderButtons(buttonId, targetId, position);
      
      if (!success) {
        return res.status(400).json({ error: "Failed to reorder buttons" });
      }
      
      const button = await storage.getButtonById(buttonId);
      if (button) {
        await storage.logActivity({
          action: 'button_updated',
          entityType: 'button',
          entityId: button.id,
          entityName: button.textAr,
          details: `Button "${button.textAr}" reordered (${position} target)`
        });
        console.log(`[LOG] Button reordered: ${button.textAr} (ID: ${button.id})`);
      }
      
      res.json({ success: true, message: "Button reordered successfully" });
    } catch (error) {
      console.error("Error reordering buttons:", error);
      res.status(500).json({ error: "Failed to reorder buttons" });
    }
  });

  // Get settings
  app.get("/api/settings", async (req, res) => {
    try {
      const settings = await storage.getSettings();
      res.json(settings);
    } catch (error) {
      console.error("Error fetching settings:", error);
      res.status(500).json({ error: "Failed to fetch settings" });
    }
  });

  // Save settings
  app.post("/api/settings", async (req, res) => {
    try {
      const settings = req.body;
      for (const [key, value] of Object.entries(settings)) {
        if (typeof value === "string") {
          await storage.saveSetting(key, value);
        } else {
          await storage.saveSetting(key, JSON.stringify(value));
        }
      }
      res.json({ success: true });
    } catch (error) {
      console.error("Error saving settings:", error);
      res.status(500).json({ error: "Failed to save settings" });
    }
  });

  // Export buttons as JSON
  app.get("/api/export", async (req, res) => {
    try {
      const tree = await storage.getButtonTree();
      res.setHeader("Content-Type", "application/json");
      res.setHeader(
        "Content-Disposition",
        `attachment; filename="telegram-bot-buttons-${new Date().toISOString().split("T")[0]}.json"`
      );
      res.json(tree);
    } catch (error) {
      console.error("Error exporting buttons:", error);
      res.status(500).json({ error: "Failed to export buttons" });
    }
  });

  // Get orders with pagination
  app.get("/api/orders", async (req, res) => {
    try {
      const limit = parseInt(req.query.limit as string) || 50;
      const offset = parseInt(req.query.offset as string) || 0;
      
      const orders = await storage.getOrders(limit, offset);
      const total = await storage.getOrdersCount();
      
      res.json({ orders, total, limit, offset });
    } catch (error) {
      console.error("Error fetching orders:", error);
      res.status(500).json({ error: "Failed to fetch orders" });
    }
  });

  // Get single order by ID
  app.get("/api/orders/:orderId", async (req, res) => {
    try {
      const orderId = req.params.orderId;
      const order = await storage.getOrderById(orderId);
      
      if (!order) {
        return res.status(404).json({ error: "Order not found" });
      }
      
      res.json(order);
    } catch (error) {
      console.error("Error fetching order:", error);
      res.status(500).json({ error: "Failed to fetch order" });
    }
  });

  // Get order button path
  app.get("/api/orders/:orderId/path", async (req, res) => {
    try {
      const orderId = req.params.orderId;
      const path = await storage.getOrderButtonPath(orderId);
      
      if (!path) {
        return res.status(404).json({ error: "Order path not found" });
      }
      
      res.json(path);
    } catch (error) {
      console.error("Error fetching order path:", error);
      res.status(500).json({ error: "Failed to fetch order path" });
    }
  });

  // ============ Bot Control Endpoints ============
  
  // Get bot status
  app.get("/api/bot/status", async (req, res) => {
    try {
      const status = await storage.getBotStatus();
      res.json(status);
    } catch (error) {
      console.error("Error fetching bot status:", error);
      res.status(500).json({ error: "Failed to fetch bot status" });
    }
  });

  // Set bot status (start/stop)
  app.post("/api/bot/status", async (req, res) => {
    try {
      const { isRunning } = req.body;
      if (typeof isRunning !== "boolean") {
        return res.status(400).json({ error: "isRunning must be a boolean" });
      }
      
      const status = await storage.setBotStatus(isRunning);
      
      await storage.logActivity({
        action: isRunning ? 'bot_started' : 'bot_stopped',
        entityType: 'bot',
        entityId: null,
        entityName: 'Bot',
        details: `Bot ${isRunning ? 'started' : 'stopped'}`
      });
      console.log(`[LOG] Bot ${isRunning ? 'started' : 'stopped'}`);
      
      res.json(status);
    } catch (error) {
      console.error("Error setting bot status:", error);
      res.status(500).json({ error: "Failed to set bot status" });
    }
  });

  // Restart bot with timer (stops for X seconds then restarts)
  app.post("/api/bot/restart", async (req, res) => {
    try {
      const { seconds } = req.body;
      const restartSeconds = typeof seconds === "number" ? seconds : 15;
      
      const status = await storage.setBotRestartTimer(restartSeconds);
      
      await storage.logActivity({
        action: 'bot_restarted',
        entityType: 'bot',
        entityId: null,
        entityName: 'Bot',
        details: `Bot restarting in ${restartSeconds} seconds`
      });
      console.log(`[LOG] Bot restarting in ${restartSeconds} seconds`);
      
      res.json(status);
    } catch (error) {
      console.error("Error setting bot restart timer:", error);
      res.status(500).json({ error: "Failed to set bot restart timer" });
    }
  });

  // ============ Activity Logs Endpoints ============

  // Get activity logs
  app.get("/api/logs", async (req, res) => {
    try {
      const limit = parseInt(req.query.limit as string) || 50;
      const offset = parseInt(req.query.offset as string) || 0;
      
      const logs = await storage.getActivityLogs(limit, offset);
      const total = await storage.getActivityLogsCount();
      
      res.json({ logs, total, limit, offset });
    } catch (error) {
      console.error("Error fetching activity logs:", error);
      res.status(500).json({ error: "Failed to fetch activity logs" });
    }
  });

  // Log button click (for tracking button usage)
  app.post("/api/buttons/:id/click", async (req, res) => {
    try {
      const id = parseInt(req.params.id);
      if (isNaN(id)) {
        return res.status(400).json({ error: "Invalid button ID" });
      }
      
      const button = await storage.getButtonById(id);
      if (!button) {
        return res.status(404).json({ error: "Button not found" });
      }
      
      await storage.logActivity({
        action: 'button_clicked',
        entityType: 'button',
        entityId: button.id,
        entityName: button.textAr,
        details: `Button "${button.textAr}" clicked`
      });
      console.log(`[LOG] Button clicked: ${button.textAr} (ID: ${button.id})`);
      
      res.json({ success: true, message: "Button click logged" });
    } catch (error) {
      console.error("Error logging button click:", error);
      res.status(500).json({ error: "Failed to log button click" });
    }
  });
}
