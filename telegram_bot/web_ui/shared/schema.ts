import { z } from "zod";

export const buttonTypeEnum = z.enum(['menu', 'service', 'message', 'link', 'back', 'cancel', 'page_separator']);
export type ButtonType = z.infer<typeof buttonTypeEnum>;

export const backBehaviorEnum = z.enum(['step', 'root']);
export type BackBehavior = z.infer<typeof backBehaviorEnum>;

export const buttonSizeEnum = z.enum(['large', 'small']);
export type ButtonSize = z.infer<typeof buttonSizeEnum>;

export const insertPositionEnum = z.enum(['top', 'center', 'end']);
export type InsertPosition = z.infer<typeof insertPositionEnum>;

export const buttonSchema = z.object({
  id: z.number(),
  parentId: z.number().nullable(),
  buttonKey: z.string(),
  textAr: z.string(),
  textEn: z.string(),
  buttonType: buttonTypeEnum,
  isEnabled: z.boolean(),
  isHidden: z.boolean().optional(),
  disabledMessage: z.string().optional(),
  isService: z.boolean(),
  price: z.number(),
  askQuantity: z.boolean(),
  defaultQuantity: z.number(),
  showBackOnQuantity: z.boolean().optional(),
  showCancelOnQuantity: z.boolean().optional(),
  backBehavior: backBehaviorEnum.optional(),
  messageAr: z.string(),
  messageEn: z.string(),
  orderIndex: z.number(),
  icon: z.string(),
  callbackData: z.string(),
  buttonSize: buttonSizeEnum.optional(),
  createdAt: z.string().optional(),
  updatedAt: z.string().optional(),
  children: z.array(z.lazy(() => buttonSchema)).optional(),
});

export type Button = z.infer<typeof buttonSchema>;

export const insertButtonSchema = z.object({
  parentId: z.number().nullable().optional(),
  buttonKey: z.string().min(1, "Button key is required"),
  textAr: z.string().min(1, "Arabic text is required"),
  textEn: z.string().min(1, "English text is required"),
  buttonType: buttonTypeEnum.default('menu'),
  isEnabled: z.boolean().default(true),
  isHidden: z.boolean().default(false),
  disabledMessage: z.string().default('هذه الخدمة متوقفة مؤقتاً'),
  isService: z.boolean().default(false),
  price: z.number().min(0).default(0),
  askQuantity: z.boolean().default(false),
  defaultQuantity: z.number().min(1).default(1),
  showBackOnQuantity: z.boolean().default(true),
  showCancelOnQuantity: z.boolean().default(true),
  backBehavior: backBehaviorEnum.default('step'),
  messageAr: z.string().default(''),
  messageEn: z.string().default(''),
  orderIndex: z.number().default(0),
  icon: z.string().default(''),
  callbackData: z.string().default(''),
  buttonSize: buttonSizeEnum.default('large'),
  insertPosition: insertPositionEnum.optional(),
});

export type InsertButton = z.infer<typeof insertButtonSchema>;

export const updateButtonSchema = insertButtonSchema.partial().extend({
  id: z.number(),
});

export type UpdateButton = z.infer<typeof updateButtonSchema>;

export const buttonTreeSchema = z.array(buttonSchema);
export type ButtonTree = z.infer<typeof buttonTreeSchema>;

export const templateSchema = z.object({
  id: z.number(),
  name: z.string(),
  description: z.string(),
  buttonTree: buttonTreeSchema,
  createdAt: z.string().optional(),
});

export type Template = z.infer<typeof templateSchema>;

export const orderButtonPathSchema = z.object({
  id: z.number(),
  orderId: z.string(),
  userId: z.number(),
  buttonPath: z.string(),
  buttonNamesAr: z.string(),
  buttonNamesEn: z.string(),
  createdAt: z.string().optional(),
});

export type OrderButtonPath = z.infer<typeof orderButtonPathSchema>;

export const orderSchema = z.object({
  id: z.number(),
  orderId: z.string(),
  odooOrder: z.string().optional(),
  userId: z.number(),
  proxyType: z.string(),
  proxyCountry: z.string().optional(),
  proxyDuration: z.string().optional(),
  status: z.string(),
  totalPrice: z.number(),
  paymentMethod: z.string().optional(),
  notes: z.string().optional(),
  expiryDate: z.string().optional(),
  createdAt: z.string().optional(),
  updatedAt: z.string().optional(),
  buttonPath: orderButtonPathSchema.optional(),
});

export type Order = z.infer<typeof orderSchema>;

export const users = {
  id: '',
  username: '',
  password: '',
};

export const insertUserSchema = z.object({
  username: z.string(),
  password: z.string(),
});

export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = { id: string; username: string; password: string };

// Bot settings schema
export const botSettingsSchema = z.object({
  id: z.number(),
  settingKey: z.string(),
  settingValue: z.string(),
  updatedAt: z.string().optional(),
});

export type BotSettings = z.infer<typeof botSettingsSchema>;

export const botStatusSchema = z.object({
  isRunning: z.boolean(),
  restartAt: z.number().nullable(),
  lastUpdated: z.string(),
});

export type BotStatus = z.infer<typeof botStatusSchema>;

export const activityLogActionEnum = z.enum([
  'button_created',
  'button_updated', 
  'button_deleted',
  'button_enabled',
  'button_disabled',
  'button_clicked',
  'buttons_imported',
  'buttons_reset',
  'buttons_batch_created',
  'bot_started',
  'bot_stopped',
  'bot_restarted',
  'settings_updated'
]);

export type ActivityLogAction = z.infer<typeof activityLogActionEnum>;

export const activityLogSchema = z.object({
  id: z.number(),
  action: activityLogActionEnum,
  entityType: z.string(),
  entityId: z.number().nullable(),
  entityName: z.string(),
  details: z.string(),
  createdAt: z.string(),
});

export type ActivityLog = z.infer<typeof activityLogSchema>;

export const insertActivityLogSchema = z.object({
  action: activityLogActionEnum,
  entityType: z.string().default('button'),
  entityId: z.number().nullable().optional(),
  entityName: z.string().default(''),
  details: z.string().default(''),
});

export type InsertActivityLog = z.infer<typeof insertActivityLogSchema>;
