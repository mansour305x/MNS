from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

BTN_HELP = "📌 المساعدة"
BTN_SETTINGS = "⚙️ الإعدادات"
BTN_NOTIFICATIONS = "🔔 إشعاراتي"
BTN_STATUS = "📊 حالتي"


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(BTN_HELP), KeyboardButton(BTN_SETTINGS)],
        [KeyboardButton(BTN_NOTIFICATIONS), KeyboardButton(BTN_STATUS)],
    ]
    if is_admin:
        rows.append([KeyboardButton("🛠 لوحة الإدارة")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, input_field_placeholder="اختر من القائمة")


def settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("العربية 🇸🇦", callback_data="user:lang:ar"), InlineKeyboardButton("English 🇬🇧", callback_data="user:lang:en")],
            [InlineKeyboardButton("تعليم كمقروء ✅", callback_data="user:read_notifications")],
            [InlineKeyboardButton("إغلاق", callback_data="common:close")],
        ]
    )


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin:stats"), InlineKeyboardButton("👥 المستخدمون", callback_data="admin:users")],
            [InlineKeyboardButton("📣 رسالة جماعية", callback_data="admin:broadcast"), InlineKeyboardButton("🚫 حظر مستخدم", callback_data="admin:ban")],
            [InlineKeyboardButton("✅ فك الحظر", callback_data="admin:unban"), InlineKeyboardButton("👮 الصلاحيات", callback_data="admin:role")],
            [InlineKeyboardButton("⚙️ رسالة الترحيب", callback_data="admin:welcome"), InlineKeyboardButton("🧰 الصيانة", callback_data="admin:maintenance")],
            [InlineKeyboardButton("📁 نسخة احتياطية", callback_data="admin:backup"), InlineKeyboardButton("🧾 آخر الأخطاء", callback_data="admin:logs")],
            [InlineKeyboardButton("إغلاق", callback_data="common:close")],
        ]
    )


def confirm_keyboard(confirm_callback: str, cancel_callback: str = "admin:cancel") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("تأكيد ✅", callback_data=confirm_callback), InlineKeyboardButton("إلغاء ❌", callback_data=cancel_callback)]]
    )
