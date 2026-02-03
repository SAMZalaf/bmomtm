# Design Guidelines: Telegram Bot Management Dashboard

## Design Approach
**System-Based Approach**: Material Design-inspired admin interface optimized for Arabic RTL layout and data management efficiency.

**Core Principles**:
- Information clarity over visual flair
- Efficient workflows for CRUD operations
- Clear visual hierarchy for nested data structures
- RTL-first design for Arabic content

---

## Typography

**Font Family**: 
- Primary: 'IBM Plex Sans Arabic' via Google Fonts for excellent Arabic support
- Fallback: system-ui, -apple-system

**Hierarchy**:
- Page Headers: text-2xl font-semibold (24px)
- Section Titles: text-lg font-medium (18px)
- Body Text: text-base (16px)
- Labels/Captions: text-sm (14px)
- Helper Text: text-xs text-gray-600 (12px)

---

## Layout System

**Spacing Primitives**: Use Tailwind units of **2, 4, 6, 8, 12, 16** (e.g., p-4, gap-6, mt-8)

**Structure**:
- Sidebar Navigation: Fixed width 64 (256px) on desktop, collapsible on mobile
- Main Content Area: max-w-7xl with px-6 py-8 padding
- Cards/Panels: Rounded-lg with p-6 internal spacing
- Form Groups: space-y-6 between major sections, space-y-4 for related fields

**Grid Layouts**:
- Button Management: 2-column layout on lg+, single column on mobile
- Tree View + Preview: 60/40 split on desktop, stacked on mobile

---

## Component Library

### Navigation
- **Sidebar**: Dark theme (#1f2937) with white/gray-200 text, active state with bg-blue-600
- **Top Bar**: User info, save status indicator, breadcrumbs

### Tree Structure Display
- **Tree View Component**: 
  - Expandable/collapsible nodes with chevron icons
  - Indent levels using pl-6 per depth
  - Visual connector lines (border-r with custom styling)
  - Drag handles for reordering
  - Toggle switches for enable/disable inline with each item
  - Context menu (three dots) for edit/delete actions

### Forms & Inputs
- **Text Fields**: Full-width with clear labels above, border-gray-300, focus:ring-2 focus:ring-blue-500
- **Text Areas**: min-h-32 for message content, auto-expanding
- **Number Inputs**: Compact width (w-32) for prices with currency indicator
- **Toggle Switches**: Material-style rounded-full with smooth transition
- **Select Dropdowns**: Custom styled with chevron-down icon

### Action Buttons
- **Primary CTA**: bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-md
- **Secondary**: border border-gray-300 hover:bg-gray-50 px-6 py-2.5
- **Destructive**: bg-red-600 hover:bg-red-700 text-white
- **Icon Buttons**: p-2 rounded-md hover:bg-gray-100 for tree actions

### Data Display
- **Cards**: bg-white border border-gray-200 rounded-lg shadow-sm
- **Tables**: Striped rows (even:bg-gray-50), sticky headers on scroll
- **Status Badges**: Rounded-full px-3 py-1 text-sm (green for active, gray for disabled)

### Preview Panel
- **Telegram Mock**: Recreate Telegram's UI with message bubbles, button layout preview
- **Live Updates**: Real-time preview as user edits button text/layout
- **Mobile Frame**: iPhone/Android frame styling to show realistic appearance

### Modals & Overlays
- **Add/Edit Dialogs**: Centered overlay with max-w-2xl, p-6, backdrop blur
- **Confirmation Dialogs**: Smaller max-w-md for delete confirmations
- **Toast Notifications**: Top-right positioned, auto-dismiss after 4s

---

## Page Structure

**Main Dashboard Layout**:
1. **Left Sidebar** (256px fixed): Navigation menu, bot status, quick stats
2. **Center Panel** (flex-1): Tree view of button hierarchy with inline controls
3. **Right Panel** (400px): Live Telegram preview + properties editor

**Button Editor Modal**:
- Button Label (Arabic text input)
- Button Type (inline keyboard vs reply keyboard)
- Message Text (rich text area with emoji support)
- Price Field (if applicable)
- Next Step Selection (dropdown linking to other buttons)
- Save/Cancel actions at bottom

---

## Key Interactions

- **Drag-and-Drop**: Reorder buttons in tree with visual drop zones
- **Inline Editing**: Double-click button name to rename in-place
- **Bulk Actions**: Checkbox selection with toolbar for batch enable/disable
- **Keyboard Shortcuts**: Ctrl+S to save, Esc to close modals

---

## Accessibility

- ARIA labels for all interactive elements (Arabic)
- Focus indicators with 2px ring offset
- Keyboard navigation through tree structure
- Screen reader announcements for status changes
- Minimum touch target 44x44px for mobile

---

## No Images Required

This is a data-focused admin interface - no hero images or decorative imagery needed. Focus on clean UI elements, icons (Heroicons), and functional layouts.