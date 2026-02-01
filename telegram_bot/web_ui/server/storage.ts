import Database from "better-sqlite3";
import type { Button, InsertButton, ButtonTree, Order, OrderButtonPath, BotStatus, ActivityLog, InsertActivityLog, ActivityLogAction } from "@shared/schema";
import path from "path";

// قاعدة بيانات البوت - مسار ثابت وحصري
// على السيرفر البعيد التشغيل من داخل telegram_bot لذا المسار هو proxy_bot.db مباشرة
const BOT_DB_PATH = path.resolve(process.cwd(), "proxy_bot.db");
console.log(`📂 Using database at: ${BOT_DB_PATH}`);

export interface IStorage {
  getAllButtons(): Promise<Button[]>;
  getButtonTree(): Promise<ButtonTree>;
  getButtonById(id: number): Promise<Button | null>;
  getButtonsByParentId(parentId: number | null): Promise<Button[]>;
  createButton(button: InsertButton): Promise<Button>;
  updateButton(id: number, updates: Partial<InsertButton>): Promise<Button | null>;
  deleteButton(id: number): Promise<boolean>;
  deleteAllButtons(): Promise<void>;
  importButtons(buttons: ButtonTree): Promise<void>;
  resetToDefaults(): Promise<void>;
  reorderButtons(buttonId: number, targetId: number, position: 'before' | 'after' | 'inside'): Promise<boolean>;
  getSettings(): Promise<Record<string, string>>;
  saveSetting(key: string, value: string): Promise<void>;
  getAdminPassword(): Promise<string>;
  saveAdminPassword(password: string): Promise<void>;
  getOrders(limit?: number, offset?: number): Promise<Order[]>;
  getOrderById(orderId: string): Promise<Order | null>;
  getOrderButtonPath(orderId: string): Promise<OrderButtonPath | null>;
  getOrdersCount(): Promise<number>;
  getBotStatus(): Promise<BotStatus>;
  setBotStatus(isRunning: boolean): Promise<BotStatus>;
  setBotRestartTimer(seconds: number): Promise<BotStatus>;
  logActivity(log: InsertActivityLog): Promise<ActivityLog>;
  getActivityLogs(limit?: number, offset?: number): Promise<ActivityLog[]>;
  getActivityLogsCount(): Promise<number>;
}

class SQLiteStorage implements IStorage {
  private db: Database.Database;

  constructor() {
    // استخدام قاعدة بيانات البوت مباشرة
    this.db = new Database(BOT_DB_PATH);
    this.db.pragma("journal_mode = WAL");
    this.db.pragma("busy_timeout = 5000");
    this.ensureTablesExist();
  }

  private ensureTablesExist() {
    // التأكد من وجود الجداول المطلوبة للواجهة
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT UNIQUE NOT NULL,
        odoo_order TEXT,
        user_id INTEGER NOT NULL,
        proxy_type TEXT,
        proxy_country TEXT,
        proxy_duration TEXT,
        status TEXT DEFAULT 'pending',
        total_price REAL DEFAULT 0,
        payment_method TEXT,
        notes TEXT,
        expiry_date TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // إضافة الأعمدة الجديدة للطلبات إذا كانت مفقودة
    const columnsToAdd = [
      { name: 'proxy_country', type: 'TEXT' },
      { name: 'proxy_duration', type: 'TEXT' },
      { name: 'expiry_date', type: 'TEXT' },
      { name: 'odoo_order', type: 'TEXT' },
      { name: 'payment_method', type: 'TEXT' },
      { name: 'notes', type: 'TEXT' }
    ];

    for (const col of columnsToAdd) {
      try {
        this.db.exec(`ALTER TABLE orders ADD COLUMN ${col.name} ${col.type}`);
      } catch (e) {
        // العمود موجود بالفعل
      }
    }

    this.db.exec(`
      CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        details TEXT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // إنشاء جدول bot_settings إذا لم يكن موجوداً
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS bot_settings (
        setting_key TEXT PRIMARY KEY,
        setting_value TEXT NOT NULL,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // إضافة القيم الافتراضية لـ bot_settings
    try {
      this.db.exec(`
        INSERT OR IGNORE INTO bot_settings (setting_key, setting_value, updated_at) 
        VALUES ('bot_running', 'true', datetime('now'))
      `);
      this.db.exec(`
        INSERT OR IGNORE INTO bot_settings (setting_key, setting_value, updated_at) 
        VALUES ('restart_at', 'null', datetime('now'))
      `);
    } catch (e) {
      // تجاهل الأخطاء
    }

    // إضافة عمود disabled_message إذا لم يكن موجوداً
    try {
      this.db.exec("ALTER TABLE dynamic_buttons ADD COLUMN disabled_message TEXT DEFAULT 'هذه الخدمة متوقفة مؤقتاً'");
    } catch (e) {
      // العمود موجود بالفعل
    }

    try {
      this.db.exec("ALTER TABLE dynamic_buttons ADD COLUMN is_hidden INTEGER DEFAULT 0");
    } catch (e) {
      // العمود موجود بالفعل
    }
  }

  private rowToButton(row: any): Button {
    return {
      id: row.id,
      parentId: row.parent_id,
      buttonKey: row.button_key,
      textAr: row.text_ar,
      textEn: row.text_en,
      buttonType: row.button_type,
      isEnabled: !!row.is_enabled,
      isHidden: !!row.is_hidden,
      disabledMessage: row.disabled_message || "هذه الخدمة متوقفة مؤقتاً",
      isService: !!row.is_service,
      price: row.price,
      askQuantity: !!row.ask_quantity,
      defaultQuantity: row.default_quantity,
      showBackOnQuantity: row.show_back_on_quantity !== 0,
      showCancelOnQuantity: row.show_cancel_on_quantity !== 0,
      messageAr: row.message_ar,
      messageEn: row.message_en,
      orderIndex: row.order_index,
      icon: row.icon,
      callbackData: row.callback_data || `dyn_${row.id}`,
      backBehavior: row.back_behavior || "step",
      buttonSize: row.button_size || "large",
      createdAt: row.created_at,
      updatedAt: row.updated_at,
    };
  }

  async getAllButtons(): Promise<Button[]> {
    const rows = this.db.prepare("SELECT * FROM dynamic_buttons ORDER BY order_index").all();
    return rows.map((row) => this.rowToButton(row));
  }

  async getButtonTree(): Promise<ButtonTree> {
    const allButtons = await this.getAllButtons();
    
    const buildTree = (parentId: number | null): ButtonTree => {
      return allButtons
        .filter(btn => btn.parentId === parentId)
        .sort((a, b) => a.orderIndex - b.orderIndex)
        .map(btn => ({
          ...btn,
          children: buildTree(btn.id)
        }));
    };
    
    return buildTree(null);
  }

  async getButtonById(id: number): Promise<Button | null> {
    const row = this.db.prepare("SELECT * FROM dynamic_buttons WHERE id = ?").get(id);
    return row ? this.rowToButton(row) : null;
  }

  async getButtonsByParentId(parentId: number | null): Promise<Button[]> {
    const query = parentId === null 
      ? "SELECT * FROM dynamic_buttons WHERE parent_id IS NULL ORDER BY order_index"
      : "SELECT * FROM dynamic_buttons WHERE parent_id = ? ORDER BY order_index";
    
    const rows = parentId === null 
      ? this.db.prepare(query).all()
      : this.db.prepare(query).all(parentId);
    
    return rows.map((row) => this.rowToButton(row));
  }

  async createButton(data: InsertButton): Promise<Button> {
    const maxOrder = this.db.prepare(
      "SELECT COALESCE(MAX(order_index), -1) + 1 as next FROM dynamic_buttons WHERE parent_id IS ?"
    ).get(data.parentId ?? null) as { next: number };
    
    const orderIndex = data.orderIndex ?? maxOrder.next;
    
    const result = this.db.prepare(`
      INSERT INTO dynamic_buttons 
      (parent_id, button_key, text_ar, text_en, button_type, is_enabled, is_hidden, disabled_message, is_service, 
       price, ask_quantity, default_quantity, show_back_on_quantity, show_cancel_on_quantity,
       message_ar, message_en, order_index, icon, callback_data, back_behavior, button_size)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      data.parentId ?? null,
      data.buttonKey,
      data.textAr,
      data.textEn,
      data.buttonType ?? "menu",
      data.isEnabled !== false ? 1 : 0,
      data.isHidden ? 1 : 0,
      data.disabledMessage ?? "هذه الخدمة متوقفة مؤقتاً",
      data.isService ? 1 : 0,
      data.price ?? 0,
      data.askQuantity ? 1 : 0,
      data.defaultQuantity ?? 1,
      data.showBackOnQuantity !== false ? 1 : 0,
      data.showCancelOnQuantity !== false ? 1 : 0,
      data.messageAr ?? "",
      data.messageEn ?? "",
      orderIndex,
      data.icon ?? "",
      "temp_callback",
      data.backBehavior ?? "step",
      data.buttonSize ?? "large"
    );

    const newId = result.lastInsertRowid as number;
    this.db.prepare("UPDATE dynamic_buttons SET callback_data = ? WHERE id = ?")
      .run(`dyn_${newId}`, newId);

    const button = await this.getButtonById(newId);
    return button!;
  }

  async updateButton(id: number, updates: Partial<InsertButton>): Promise<Button | null> {
    const existing = await this.getButtonById(id);
    if (!existing) return null;

    const fields: string[] = [];
    const values: any[] = [];

    const fieldMap: Record<string, string> = {
      parentId: "parent_id",
      buttonKey: "button_key",
      textAr: "text_ar",
      textEn: "text_en",
      buttonType: "button_type",
      isEnabled: "is_enabled",
      isHidden: "is_hidden",
      disabledMessage: "disabled_message",
      isService: "is_service",
      price: "price",
      askQuantity: "ask_quantity",
      defaultQuantity: "default_quantity",
      showBackOnQuantity: "show_back_on_quantity",
      showCancelOnQuantity: "show_cancel_on_quantity",
      messageAr: "message_ar",
      messageEn: "message_en",
      orderIndex: "order_index",
      icon: "icon",
      callbackData: "callback_data",
      backBehavior: "back_behavior",
      buttonSize: "button_size",
    };

    for (const [key, dbField] of Object.entries(fieldMap)) {
      if (key in updates) {
        fields.push(`${dbField} = ?`);
        let value = (updates as any)[key];
        if (key === "isEnabled" || key === "isHidden" || key === "isService" || key === "askQuantity" || 
            key === "showBackOnQuantity" || key === "showCancelOnQuantity") {
          value = value ? 1 : 0;
        }
        values.push(value);
      }
    }

    if (fields.length === 0) return existing;

    fields.push("updated_at = CURRENT_TIMESTAMP");
    values.push(id);

    const query = `UPDATE dynamic_buttons SET ${fields.join(", ")} WHERE id = ?`;
    this.db.prepare(query).run(...values);

    return this.getButtonById(id);
  }

  async deleteButton(id: number): Promise<boolean> {
    const result = this.db
      .prepare("DELETE FROM dynamic_buttons WHERE id = ?")
      .run(id);
    
    return result.changes > 0;
  }

  async deleteAllButtons(): Promise<void> {
    this.db.prepare("DELETE FROM dynamic_buttons").run();
  }

  async importButtons(buttons: ButtonTree): Promise<void> {
    await this.deleteAllButtons();

    const insertRecursive = (items: ButtonTree, parentId: number | null) => {
      for (const item of items) {
        const stmt = this.db.prepare(`
          INSERT INTO dynamic_buttons 
          (parent_id, button_key, text_ar, text_en, button_type, is_enabled, is_hidden, disabled_message,
           is_service, price, ask_quantity, default_quantity, show_back_on_quantity, show_cancel_on_quantity,
           message_ar, message_en, order_index, icon, callback_data, back_behavior, button_size)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `);

        const result = stmt.run(
          parentId,
          item.buttonKey,
          item.textAr,
          item.textEn,
          item.buttonType,
          item.isEnabled ? 1 : 0,
          item.isHidden ? 1 : 0,
          item.disabledMessage || "هذه الخدمة متوقفة مؤقتاً",
          item.isService ? 1 : 0,
          item.price,
          item.askQuantity ? 1 : 0,
          item.defaultQuantity,
          item.showBackOnQuantity !== false ? 1 : 0,
          item.showCancelOnQuantity !== false ? 1 : 0,
          item.messageAr,
          item.messageEn,
          item.orderIndex,
          item.icon,
          "temp_callback",
          item.backBehavior || "step",
          item.buttonSize || "large"
        );

        const newId = result.lastInsertRowid as number;
        this.db.prepare("UPDATE dynamic_buttons SET callback_data = ? WHERE id = ?")
          .run(`dyn_${newId}`, newId);

        if (item.children && item.children.length > 0) {
          insertRecursive(item.children, newId);
        }
      }
    };

    insertRecursive(buttons, null);
  }

  async resetToDefaults(): Promise<void> {
    await this.deleteAllButtons();
    
    const defaultButtons: InsertButton[] = [
      {
        buttonKey: "static_proxy",
        textAr: "🌐 ستاتيك بروكسي",
        textEn: "🌐 Static Proxy",
        buttonType: "menu",
        isEnabled: true,
        isService: false,
        messageAr: "اختر نوع الخدمة",
        messageEn: "Choose service type",
        orderIndex: 0,
        icon: "🌐",
      },
      {
        buttonKey: "socks_proxy",
        textAr: "🧦 سوكس بروكسي",
        textEn: "🧦 SOCKS Proxy",
        buttonType: "menu",
        isEnabled: true,
        isService: false,
        messageAr: "اختر الدولة",
        messageEn: "Choose country",
        orderIndex: 1,
        icon: "🧦",
      },
    ];

    for (const btn of defaultButtons) {
      await this.createButton(btn);
    }
  }

  async reorderButtons(buttonId: number, targetId: number, position: 'before' | 'after' | 'inside'): Promise<boolean> {
    const button = await this.getButtonById(buttonId);
    const target = await this.getButtonById(targetId);
    
    if (!button || !target) return false;

    let newParentId: number | null;
    let newOrderIndex: number;

    if (position === 'inside') {
      newParentId = targetId;
      const maxOrder = this.db.prepare(
        "SELECT COALESCE(MAX(order_index), -1) + 1 as next FROM dynamic_buttons WHERE parent_id = ?"
      ).get(targetId) as { next: number };
      newOrderIndex = maxOrder.next;
    } else {
      newParentId = target.parentId;
      const siblings = await this.getButtonsByParentId(newParentId);
      const targetIndex = siblings.findIndex(s => s.id === targetId);
      newOrderIndex = position === 'before' ? targetIndex : targetIndex + 1;
      
      for (let i = newOrderIndex; i < siblings.length; i++) {
        this.db.prepare("UPDATE dynamic_buttons SET order_index = ? WHERE id = ?")
          .run(i + 1, siblings[i].id);
      }
    }

    this.db.prepare("UPDATE dynamic_buttons SET parent_id = ?, order_index = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?")
      .run(newParentId, newOrderIndex, buttonId);

    return true;
  }

  async getSettings(): Promise<Record<string, string>> {
    try {
      const rows = this.db.prepare("SELECT key, value FROM dashboard_settings").all() as { key: string; value: string }[];
      return Object.fromEntries(rows.map(r => [r.key, r.value]));
    } catch {
      return {};
    }
  }

  async saveSetting(key: string, value: string): Promise<void> {
    this.db.prepare("INSERT OR REPLACE INTO dashboard_settings (key, value) VALUES (?, ?)").run(key, value);
  }

  async getAdminPassword(): Promise<string> {
    try {
      const row = this.db.prepare("SELECT value FROM settings WHERE key = 'admin_password'").get() as { value: string } | undefined;
      return row?.value || "sohilSOHIL";
    } catch (error) {
      return "sohilSOHIL";
    }
  }

  async saveAdminPassword(password: string): Promise<void> {
    try {
      this.db.prepare("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)").run("admin_password", password);
    } catch (error) {
      console.error("[Storage] Error saving admin password:", error);
    }
  }

  async getOrders(limit = 50, offset = 0): Promise<Order[]> {
    try {
      const rows = this.db.prepare(`
        SELECT * FROM orders ORDER BY created_at DESC LIMIT ? OFFSET ?
      `).all(limit, offset) as any[];
      
      return rows.map(row => ({
        id: row.id,
        orderId: row.order_id,
        odooOrder: row.odoo_order,
        userId: row.user_id,
        proxyType: row.proxy_type,
        proxyCountry: row.proxy_country,
        proxyDuration: row.proxy_duration,
        status: row.status,
        totalPrice: row.total_price,
        paymentMethod: row.payment_method,
        notes: row.notes,
        expiryDate: row.expiry_date,
        createdAt: row.created_at,
        updatedAt: row.updated_at,
      }));
    } catch (error) {
      console.error("[Storage] Error fetching orders:", error);
      return [];
    }
  }

  async getOrderById(orderId: string): Promise<Order | null> {
    try {
      const row = this.db.prepare("SELECT * FROM orders WHERE order_id = ?").get(orderId) as any;
      if (!row) return null;
      
      return {
        id: row.id,
        orderId: row.order_id,
        odooOrder: row.odoo_order,
        userId: row.user_id,
        proxyType: row.proxy_type,
        proxyCountry: row.proxy_country,
        proxyDuration: row.proxy_duration,
        status: row.status,
        totalPrice: row.total_price,
        paymentMethod: row.payment_method,
        notes: row.notes,
        expiryDate: row.expiry_date,
        createdAt: row.created_at,
        updatedAt: row.updated_at,
      };
    } catch (error) {
      console.error("[Storage] Error fetching order by ID:", error);
      return null;
    }
  }

  async getOrderButtonPath(orderId: string): Promise<OrderButtonPath | null> {
    try {
      const row = this.db.prepare("SELECT * FROM order_button_path WHERE order_id = ?").get(orderId) as any;
      if (!row) return null;
      
      return {
        id: row.id,
        orderId: row.order_id,
        userId: row.user_id,
        buttonPath: row.button_path,
        buttonNamesAr: row.button_names_ar,
        buttonNamesEn: row.button_names_en,
        createdAt: row.created_at,
      };
    } catch (error) {
      return null;
    }
  }

  async getOrdersCount(): Promise<number> {
    try {
      const row = this.db.prepare("SELECT COUNT(*) as count FROM orders").get() as { count: number };
      return row.count;
    } catch (error) {
      return 0;
    }
  }

  async getBotStatus(): Promise<BotStatus> {
    try {
      const running = this.db.prepare("SELECT setting_value FROM bot_settings WHERE setting_key = 'bot_running'").get() as { setting_value: string } | undefined;
      const restartAt = this.db.prepare("SELECT setting_value FROM bot_settings WHERE setting_key = 'restart_at'").get() as { setting_value: string } | undefined;
      const updated = this.db.prepare("SELECT updated_at FROM bot_settings WHERE setting_key = 'bot_running'").get() as { updated_at: string } | undefined;

      return {
        isRunning: running?.setting_value === "true",
        restartAt: restartAt?.setting_value === "null" ? null : restartAt?.setting_value || null,
        lastUpdated: updated?.updated_at || new Date().toISOString(),
      };
    } catch {
      return {
        isRunning: true,
        restartAt: null,
        lastUpdated: new Date().toISOString(),
      };
    }
  }

  async setBotStatus(isRunning: boolean): Promise<BotStatus> {
    try {
      this.db.prepare("INSERT OR REPLACE INTO bot_settings (setting_key, setting_value, updated_at) VALUES ('bot_running', ?, CURRENT_TIMESTAMP)")
        .run(isRunning ? "true" : "false");
    } catch {}
    return this.getBotStatus();
  }

  async setBotRestartTimer(seconds: number): Promise<BotStatus> {
    const restartAt = new Date(Date.now() + seconds * 1000).toISOString();
    try {
      this.db.prepare("INSERT OR REPLACE INTO bot_settings (setting_key, setting_value, updated_at) VALUES ('restart_at', ?, CURRENT_TIMESTAMP)")
        .run(restartAt);
    } catch {}
    return this.getBotStatus();
  }

  async logActivity(log: InsertActivityLog): Promise<ActivityLog> {
    const result = this.db.prepare(
      "INSERT INTO activity_logs (action, details) VALUES (?, ?)"
    ).run(log.action, log.details || null);

    const id = result.lastInsertRowid as number;
    const row = this.db.prepare("SELECT * FROM activity_logs WHERE id = ?").get(id) as any;
    
    return {
      id: row.id,
      action: row.action as ActivityLogAction,
      details: row.details,
      timestamp: row.timestamp,
    };
  }

  async getActivityLogs(limit = 50, offset = 0): Promise<ActivityLog[]> {
    try {
      const rows = this.db.prepare(
        "SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT ? OFFSET ?"
      ).all(limit, offset) as any[];

      return rows.map(row => ({
        id: row.id,
        action: row.action as ActivityLogAction,
        details: row.details,
        timestamp: row.timestamp,
      }));
    } catch {
      return [];
    }
  }

  async getActivityLogsCount(): Promise<number> {
    try {
      const row = this.db.prepare("SELECT COUNT(*) as count FROM activity_logs").get() as { count: number };
      return row.count;
    } catch {
      return 0;
    }
  }
}

export const storage: IStorage = new SQLiteStorage();
