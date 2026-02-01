from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

MOOD_OPTIONS = [
    "😊 Хорошо",
    "😐 Удовлетворительно",
    "😟 Тревожно",
    "😰 Плохо",
    "😨 Очень плохо",
]


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💊 Настроить напоминания", callback_data="menu_set_reminder"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Быстрый опрос настроения",
                    callback_data="menu_quick_survey",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 Развёрнутый опрос", callback_data="menu_detail_survey"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📅 Текущее расписание", callback_data="menu_show_schedule"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Суммаризация (отчёт)", callback_data="menu_summarize"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑️ Сбросить напоминания", callback_data="menu_cancel_reminder"
                )
            ],
        ]
    )


def mood_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=m, callback_data=f"mood:{m}")]
            for m in MOOD_OPTIONS
        ]
    )


def skip_details_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="mood_skip")]
        ]
    )
