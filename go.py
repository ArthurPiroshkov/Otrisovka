from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from PIL import Image, ImageDraw, ImageFont, ImageOps
import asyncio
import random
import re
import os
from io import BytesIO
import sqlite3

from aiogram.client.session.aiohttp import AiohttpSession


def init_db():
    conn = sqlite3.connect("access.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS allowed_users (
            tg_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()


def add_user(tg_id: int):
    conn = sqlite3.connect("access.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO allowed_users (tg_id) VALUES (?)", (tg_id,))
    conn.commit()
    conn.close()


def remove_user(tg_id: int):
    conn = sqlite3.connect("access.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM allowed_users WHERE tg_id = ?", (tg_id,))
    conn.commit()
    conn.close()


def is_allowed(tg_id: int) -> bool:
    conn = sqlite3.connect("access.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM allowed_users WHERE tg_id = ?", (tg_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


ADMIN_IDS = [1568156117, 8103911059]


class TransferStates(StatesGroup):
    WAITING_FOR_INPUT = State()


class BankBot:
    def __init__(self):
        # self.bot = Bot("7740729484:AAFSmUf88ha7LC6Ex7sP8WArwf4twOgdAas")
        # self.bot = Bot("8336684622:AAGbPuJcMp3fNkfZPWPlamWSfT0f4fG9isk")
        session = AiohttpSession(
            proxy="socks5://223.205.84.178:8081",
        )
        self.bot = Bot("8336684622:AAGbPuJcMp3fNkfZPWPlamWSfT0f4fG9isk")
        self.dp = Dispatcher()

        # === Ozon история переводов (порт из test.py) ===
        self.ozon_template = "assets/imgs/ozon_history_new1.png"
        self.ozon_row_ys = [922, 1097, 1367, 1559]
        self.ozon_name_x = 228
        self.ozon_right_padding = 87
        self.ozon_row_center_offset = -15

        # Шрифты
        self.ozon_name_font_path = "assets/fonts/Onest.ttf"
        self.ozon_name_font_size = 47
        self.ozon_amount_font_path = "assets/fonts/Onest-Regular.ttf"
        self.ozon_amount_font_size = 48

        # Плюс — рисуем отдельно
        self.ozon_plus_font_path = "assets/fonts/gteestiprodisplay_light.otf"
        self.ozon_plus_font_size = 33
        self.ozon_plus_bold = 0.9
        self.ozon_plus_gap = 4
        self.ozon_plus_y_offset = 6

        # Общие настройки
        self.time_position = (125, 67)
        self.ozon_time_position = (120, 55)
        self.time_font_size = 53
        self.text_color = (255, 255, 255)

        # Настройки для истории переводов
        self.history_amount_base_x = 1130
        self.history_amount_y = 894
        self.history_amount_font_size = 50
        self.history_name_base_x = 227
        self.history_name_y = 894
        self.history_name_font_size = 48
        self.history_amount_color = (29, 237, 98)

        self.tbank_history_amount_base_x = 1130
        self.tbank_history_amount_y = 820
        self.tbank_history_amount_font_size = 75
        self.tbank_history_name_base_x = 217
        self.tbank_history_name_y = 894
        self.tbank_history_name_font_size = 66
        self.tbank_history_amount_color = (0, 186, 6)

        self.ozon_history_amount_color = (29, 237, 98)

        # Настройки для банковских переводов
        self.bank_amount_base_x = 663
        self.bank_amount_y = 1203
        self.bank_amount_font_size = 71
        self.bank_amount_angle = 1
        self.bank_name_base_x = 365
        self.bank_name_y = 1471
        self.bank_name_font_size = 48
        self.bank_phone_base_x = 390
        self.bank_phone_y = 1568
        self.bank_phone_font_size = 48

        self.register_handlers()

    def register_handlers(self):
        self.dp.message.register(self.cmd_start, Command("start"))
        self.dp.message.register(self.cmd_true, Command("true"))
        self.dp.message.register(self.cmd_off, Command("off"))
        self.dp.message.register(
            self.handle_transfer_type,
            F.text.in_(
                [
                    "Сбер отправка (Озон)",
                    "Тбанк отправка (Озон)",
                    "ВТБ отправка (Озон)",
                    "Альфа отправка (Озон)",
                    "Тбанк история переводов",
                    "Сбер история переводов",
                    "Ozon история переводов",
                    "Сбер отправка (Тбанк)",
                    "Тбанк отправка (Тбанк)",
                    "ВТБ отправка (Тбанк)",
                    "Альфа отправка (Тбанк)",
                ]
            ),
        )
        self.dp.message.register(self.process_input, TransferStates.WAITING_FOR_INPUT)

    def get_main_keyboard(self):
        return ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="Ozon история переводов"),
                    KeyboardButton(text="Тбанк история переводов"),
                    KeyboardButton(text="Сбер история переводов"),
                ],
                [
                    KeyboardButton(text="ВТБ отправка (Озон)"),
                    KeyboardButton(text="Озон Отправка (Озон)"),
                ],
                [
                    KeyboardButton(text="Тбанк отправка (Озон)"),
                    KeyboardButton(text="Альфа отправка (Озон)"),
                    KeyboardButton(text="Сбер отправка (Озон)"),
                ],
                [
                    KeyboardButton(text="ВТБ отправка (Тбанк)"),
                ],
                [
                    KeyboardButton(text="Тбанк отправка (Тбанк)"),
                    KeyboardButton(text="Альфа отправка (Тбанк)"),
                    KeyboardButton(text="Сбер отправка (Тбанк)"),
                ],
            ],
            resize_keyboard=True,
        )

    async def cmd_start(self, message: types.Message, state: FSMContext):
        if is_allowed(message.from_user.id) or message.from_user.id in ADMIN_IDS:
            await state.set_state(TransferStates.WAITING_FOR_INPUT)
            await message.answer(
                "👋 Выберите тип операции:", reply_markup=self.get_main_keyboard()
            )

    async def cmd_true(self, message: types.Message):
        if message.from_user.id not in ADMIN_IDS:
            return await message.answer("⛔ Нет доступа.")

        args = message.text.split()
        if len(args) != 2 or not args[1].isdigit():
            return await message.answer("⚠️ Используй: /true <tg_id>")

        tg_id = int(args[1])
        add_user(tg_id)
        await message.answer(f"✅ Пользователю {tg_id} выдан доступ.")

    async def cmd_off(self, message: types.Message):
        if message.from_user.id not in ADMIN_IDS:
            return await message.answer("⛔ Нет доступа.")

        args = message.text.split()
        if len(args) != 2 or not args[1].isdigit():
            return await message.answer("⚠️ Используй: /off <tg_id>")

        tg_id = int(args[1])
        remove_user(tg_id)
        await message.answer(f"🚫 Доступ пользователя {tg_id} удалён.")

    async def handle_transfer_type(self, message: types.Message, state: FSMContext):
        if is_allowed(message.from_user.id) or message.from_user.id in ADMIN_IDS:
            await state.update_data(transfer_type=message.text)

            if message.text in ["Ozon история переводов"]:
                await message.answer(
                    "📝 Отправьте данные в следующем формате:\n"
                    "Время \nФИО 1\nСумма 1\nФИО 2\nСумма 2\nФИО 3\nСумма 3\nФИО 4\nСумма 4\n\n"
                    "Пример:\n"
                    "<code>11:11\n"
                    "Степан Кио Ф.\n"
                    "100\n"
                    "Иван Иванов\n"
                    "200\n"
                    "Петр Петров\n"
                    "300\n"
                    "Олександр Чипов\n"
                    "300\n</code>",
                    parse_mode="HTML",
                )
            elif message.text in ["Тбанк история переводов"]:
                await message.answer(
                    "📝 Отправьте данные в следующем формате:\n"
                    "Время\nФИО 1\nСумма 1\nФИО 2\nСумма 2\nФИО 3\nСумма 3\nФИО 4\nСумма 4\n\n"
                    "Пример:\n"
                    "<code>11:11\n"
                    "Степан Кио Ф.\n"
                    "100\n"
                    "Иван Иванов\n"
                    "200\n"
                    "Петр Петров\n"
                    "300\n"
                    "Олег Петров\n"
                    "400</code>",
                    parse_mode="HTML",
                )
            elif message.text in ["Сбер история переводов"]:
                await message.answer(
                    "📝 Отправьте данные в следующем формате:\n"
                    "Время\nФИО 1\nСумма 1\nФИО 2\nСумма 2\n\n"
                    "Пример:\n"
                    "<code>11:11\n"
                    "Степан Кио Ф.\n"
                    "100\n"
                    "Иван Иванов\n"
                    "200</code>",
                    parse_mode="HTML",
                )
            source_match = re.search(r"\((.+?)\)", message.text)
            source = source_match.group(1) if source_match else None
            if source == "Озон":
                await message.answer(
                    "📝 Отправьте данные в следующем формате:\n"
                    "Время\nФИО\nНомер телефона\nСумма\n\n"
                    "Пример:\n"
                    "<code>11:11\n"
                    "Иван Иванов\n"
                    "+79991234567\n"
                    "100</code>",
                    parse_mode="HTML",
                )
            elif source == "Тбанк":
                await message.answer(
                    "📝 Отправьте данные в следующем формате:\n"
                    "Время\nФИО\nНомер телефона\nСумма\n\n"
                    "Пример:\n"
                    "<code>4 октября\n"
                    "11:11\n"
                    "Иван Иванов\n"
                    "+79991234567\n"
                    "100</code>",
                    parse_mode="HTML",
                )

            await state.set_state(TransferStates.WAITING_FOR_INPUT)

    def format_phone_number(self, phone: str) -> str:
        digits = "".join(filter(str.isdigit, phone))
        if len(digits) == 10:
            digits = "7" + digits
        return (
            f"+{digits[0]} ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
        )

    def format_phone_number_tbank(self, phone: str) -> str:
        digits = "".join(filter(str.isdigit, phone))
        if len(digits) == 10:
            digits = "7" + digits
        return f"+{digits[0]} {digits[1:4]} {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"

    def format_amount_tbank(self, amount: int) -> str:
        formatted_temp = f"{int(amount):,}"
        formatted_number = formatted_temp.replace(",", " ")
        return f"–{formatted_number} ₽"

    def validate_time(self, time_str: str) -> bool:
        return bool(re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", time_str))

    def validate_phone(self, phone: str) -> bool:
        digits = "".join(filter(str.isdigit, phone))
        return len(digits) in [10, 11]

    def validate_amount(self, amount_str: str) -> bool:
        try:
            amount = int(amount_str)
            return amount > 0
        except ValueError:
            return False

    async def process_input(self, message: types.Message, state: FSMContext):
        if is_allowed(message.from_user.id) or message.from_user.id in ADMIN_IDS:
            data = await state.get_data()
            transfer_type = data.get("transfer_type")

            if not transfer_type:
                await message.answer(
                    "Сначала выберите тип операции",
                    reply_markup=self.get_main_keyboard(),
                )
                return

            lines = message.text.strip().split("\n")

            if transfer_type in ["Ozon история переводов"]:
                lines = [l.strip() for l in message.text.splitlines() if l.strip()]
                if len(lines) != 9:
                    await message.answer(
                        "❌ Неверный формат. Отправьте данные в формате:\n"
                        "Время\nФИО 1\nСумма 1\nФИО 2\nСумма 2\nФИО 3\nСумма 3\nФИО 4\nСумма 4"
                    )
                    return
                time = lines[0]
                names = [lines[1], lines[3], lines[5], lines[7]]
                amount_raw = [lines[2], lines[4], lines[6], lines[8]]

                if not self.validate_time(time):
                    await message.answer(
                        "❌ Неверный формат времени. Используйте ЧЧ:ММ (например, 20:11)"
                    )
                    return

                # валидация и форматирование сумм
                for a in amount_raw:
                    if not self.validate_amount(a):
                        await message.answer(f"amounts:{amount_raw}")
                        await message.answer(
                            "❌ Неверный формат суммы. Введите положительное число"
                        )
                        return

                formatted_amounts = [
                    "{:,}".format(int(a)).replace(",", " ") for a in amount_raw
                ]

                # используем общий рендерер, но логика отрисовки будет внутри ветки Ozon
                image_path = await self.create_history_image(
                    time, names, formatted_amounts, self.ozon_template, transfer_type
                )

                await message.answer_document(FSInputFile(image_path))
                os.remove(image_path)

            elif transfer_type in ["Тбанк история переводов"]:
                if len(lines) != 9:
                    await message.answer(
                        "❌ Неверный формат. Отправьте данные в формате:\n"
                        "Время\nФИО 1\nСумма 1\nФИО 2\nСумма 2\nФИО 3\nСумма 3\nФИО 4\nСумма 4"
                    )
                    return
                time = lines[0]
                names = [lines[1], lines[3], lines[5], lines[7]]
                amounts = [lines[2], lines[4], lines[6], lines[8]]
                if not self.validate_time(time):
                    await message.answer(
                        "❌ Неверный формат времени. Используйте ЧЧ:ММ (например, 20:11)"
                    )
                    return

                for amount in amounts:
                    if not self.validate_amount(amount):
                        await message.answer(
                            "❌ Неверный формат суммы. Введите положительное число"
                        )
                        return

                template = "assets/imgs/tbank_sample.png"
                # template = 'assets/imgs/test.png'
                formatted_amounts = [
                    "{:,}".format(int(amount)).replace(",", " ") for amount in amounts
                ]
                image_path = await self.create_history_image(
                    time,
                    names,
                    [f"+{amt}\u2009₽" for amt in formatted_amounts],
                    template,
                    transfer_type,
                )

                await message.answer_document(FSInputFile(image_path))
                os.remove(image_path)

            elif transfer_type in "Сбер история переводов":
                if len(lines) != 5:
                    await message.answer(
                        "❌ Неверный формат. Отправьте данные в формате:\n"
                        "Время\n"
                        "ФИО 1\n"
                        "Сумма 1\n"
                        "ФИО 2\n"
                        "Сумма 2"
                    )
                    return

                time = lines[0]
                names = [lines[1], lines[3]]
                amounts = [lines[2], lines[4]]

                if not self.validate_time(time):
                    await message.answer(
                        "❌ Неверный формат времени. Используйте ЧЧ:ММ (например, 20:11)"
                    )
                    return

                for amount in amounts:
                    if not self.validate_amount(amount):
                        await message.answer(
                            "❌ Неверный формат суммы. Введите положительное число"
                        )
                        return

                template = "assets/imgs/sber_history_template.png"
                formatted = [f"+{int(a):,} ₽".replace(",", " ") for a in amounts]
                image_path = await self.create_history_image(
                    time, names, formatted, template, transfer_type
                )

                await message.answer_document(FSInputFile(image_path))
                os.remove(image_path)

            source_match = re.search(r"\((.+?)\)", transfer_type)
            source = source_match.group(1) if source_match else None
            if source == "Тбанк":
                if len(lines) != 5:
                    await message.answer(
                        "❌ Неверный формат. Отправьте данные в формате:\n"
                        "Дата\nВремя\nФИО\nНомер телефона\nСумма"
                    )
                    return

                date, time, name, phone, amount = lines

                if not self.validate_time(time):
                    await message.answer(
                        "❌ Неверный формат времени. Используйте ЧЧ:ММ (например, 20:11)"
                    )
                    return

                if not self.validate_phone(phone):
                    await message.answer(
                        "❌ Неверный формат номера. Примеры:\n"
                        "+79991111111\n"
                        "89991111111\n"
                        "9991111111"
                    )
                    return

                if not self.validate_amount(amount):
                    await message.answer(
                        "❌ Неверный формат суммы. Введите положительное число"
                    )
                    return

                formatted_phone = self.format_phone_number_tbank(phone)
                template = None

                if transfer_type == "Сбер отправка (Тбанк)":
                    template = "assets/imgs/tbank_sber.png"
                elif transfer_type == "Альфа отправка (Тбанк)":
                    template = "assets/imgs/tbank_alpha.png"
                elif transfer_type == "ВТБ отправка (Тбанк)":
                    template = "assets/imgs/tbank_vtb.png"
                else:  # Тбанк
                    template = "assets/imgs/tbank_tbank.png"

                image_path = await self.create_tinkoff_image(
                    template=template,
                    time_text=time,
                    datetime_text=f"{date} ∙ {time}",
                    name_text=name,
                    phone_text=formatted_phone,
                    amount_text=self.format_amount_tbank(amount),
                )

                await message.answer_document(FSInputFile(image_path))
                os.remove(image_path)

            elif source == "Озон":
                if len(lines) != 4:
                    await message.answer(
                        "❌ Неверный формат. Отправьте данные в формате:\n"
                        "Время\nФИО\nНомер телефона\nСумма"
                    )
                    return

                time, name, phone, amount = lines

                if not self.validate_time(time):
                    await message.answer(
                        "❌ Неверный формат времени. Используйте ЧЧ:ММ (например, 20:11)"
                    )
                    return

                if not self.validate_phone(phone):
                    await message.answer(
                        "❌ Неверный формат номера. Примеры:\n"
                        "+79991111111\n"
                        "89991111111\n"
                        "9991111111"
                    )
                    return

                if not self.validate_amount(amount):
                    await message.answer(
                        "❌ Неверный формат суммы. Введите положительное число"
                    )
                    return

                formatted_phone = self.format_phone_number(phone)
                formatted_amount = "{:,}".format(int(amount)).replace(",", " ")

                if transfer_type == "Сбер отправка (Озон)":
                    template = "assets/imgs/sber5.png"
                elif transfer_type == "Альфа отправка (Озон)":
                    template = "assets/imgs/alfa1.png"
                elif transfer_type == "ВТБ отправка (Озон)":
                    template = "assets/imgs/vtb_otp.png"
                else:  # Тбанк
                    template = "assets/imgs/tbank1.png"

                image_path = await self.create_bank_image(
                    template, time, name, formatted_phone, f"- {formatted_amount} ₽"
                )

                await message.answer_document(FSInputFile(image_path))
                os.remove(image_path)

            await message.answer(
                "Выберите следующую операцию:", reply_markup=self.get_main_keyboard()
            )

    def rotate_text(self, draw, text, x, y, angle, font, fill):
        txt = Image.new("RGBA", (400, 100), (0, 0, 0, 0))
        d = ImageDraw.Draw(txt)
        d.text((0, 0), text, font=font, fill=fill)
        rotated = txt.rotate(angle, expand=True, fillcolor=(0, 0, 0, 0))
        draw._image.paste(rotated, (x, y), rotated)

    async def create_history_image(
        self, time_text, names, amounts, template, transfer_type
    ):
        image = Image.open(template)
        draw = ImageDraw.Draw(image)
        time_font_name = "assets/fonts/SFPRODISPLAYBOLD.otf"
        # if transfer_type == "История переводов":
        #     name_font_name = "assets/fonts/gteestiprodisplay_regular.otf"
        #     amount_font_name = "assets/fonts/gteestiprodisplay_regular.otf"
        #     offsets = [894, 500 + 1155, 700 + 1139]

        if transfer_type == "Ozon история переводов":
            name_font_name = "assets/fonts/gteestiprodisplay_regular.otf"
            amount_font_name = "assets/fonts/gteestiprodisplay_regular.otf"
            offsets = [886, 500 + 1155, 700 + 1146]

        elif transfer_type == "Тбанк история переводов":
            name_font_name = "assets/fonts/SFUIText-Semibold.ttf"
            amount_font_name = "assets/fonts/SFUIText-Regular.ttf"
            offsets = [894, 500 + 1155, 700 + 1139, 800 + 1100]

        elif transfer_type == "Сбер история переводов":
            name_font_name = "assets/fonts/SB Sans Interface.ttf"
            amount_font_name = "assets/fonts/SB Sans Interface.ttf"
            # offsets = [894, 894 + 260]
        try:
            time_font = ImageFont.truetype(
                "assets/fonts/SFPRODISPLAYBOLD.OTF", self.time_font_size
            )
            if name_font_name == "assets/fonts/SFUIText-Semibold.ttf":
                name_font = ImageFont.truetype(name_font_name, 51)
                amount_font = ImageFont.truetype(amount_font_name, 52)
            else:
                name_font = ImageFont.truetype(
                    name_font_name, self.history_name_font_size
                )
                amount_font = ImageFont.truetype(
                    amount_font_name, self.history_amount_font_size
                )
        except Exception as e:
            print(f"Ошибка загрузки шрифта: {e}")
            time_font = name_font = amount_font = ImageFont.load_default()

        if transfer_type == "Ozon история переводов":
            # Шрифты из конфига
            try:
                name_font = ImageFont.truetype(
                    self.ozon_name_font_path, self.ozon_name_font_size
                )
                amount_font = ImageFont.truetype(
                    self.ozon_amount_font_path, self.ozon_amount_font_size
                )
                plus_font = ImageFont.truetype(
                    self.ozon_plus_font_path, self.ozon_plus_font_size
                )
                time_font = ImageFont.truetype(
                    "assets/fonts/SFPRODISPLAYBOLD.OTF", self.time_font_size
                )
            except Exception as e:
                print(f"Ошибка загрузки шрифта Ozon: {e}")
                name_font = amount_font = plus_font = ImageFont.load_default()

            img_width, _ = image.size
            sw = int(round(self.ozon_plus_bold))  # stroke_width для плюса

            draw.text(
                self.time_position, time_text, font=time_font, fill=self.text_color
            )

            for i, (name, amount) in enumerate(zip(names, amounts)):
                # 1) Имя — слева по Y из списка
                y_top = self.ozon_row_ys[i]
                draw.text(
                    (self.ozon_name_x, y_top),
                    name,
                    font=name_font,
                    fill=self.text_color,
                )

                # 2) Общая серединка строки по высоте имени
                name_ascent, name_descent = name_font.getmetrics()
                line_h = name_ascent + name_descent
                mid_y = y_top + line_h // 2 + self.ozon_row_center_offset

                amount_text = f"{amount}"
                amt_bbox = draw.textbbox((0, 0), amount_text, font=amount_font)
                amt_w = amt_bbox[2] - amt_bbox[0]
                amt_h = amt_bbox[3] - amt_bbox[1]

                amount_x = img_width - self.ozon_right_padding - amt_w
                amount_y = int(mid_y - amt_h / 2)

                draw.text(
                    (amount_x, amount_y),
                    amount_text,
                    font=amount_font,
                    fill=self.ozon_history_amount_color,
                )

                # 4) «+» слева от суммы, центрируем по той же mid_y и делаем «жирнее» stroke'ом
                plus_text = "+"
                plus_bbox = draw.textbbox(
                    (0, 0), plus_text, font=plus_font, stroke_width=sw
                )
                plus_w = plus_bbox[2] - plus_bbox[0]
                plus_h = plus_bbox[3] - plus_bbox[1]

                plus_x = amount_x - self.ozon_plus_gap - plus_w
                plus_y = int(mid_y - plus_h / 2) + self.ozon_plus_y_offset

                draw.text(
                    (plus_x, plus_y),
                    plus_text,
                    font=plus_font,
                    fill=self.ozon_history_amount_color,
                    stroke_width=sw,
                    stroke_fill=self.ozon_history_amount_color,
                )

        elif transfer_type == "Тбанк история переводов":
            draw.text(
                self.time_position, time_text, font=time_font, fill=self.text_color
            )

            for i, (name, amount) in enumerate(zip(names, amounts)):
                if i == 0:
                    offset_y = offsets[i] + 383
                    image_width = image.size[0]

                    amount_bbox = draw.textbbox((0, 0), amount, font=amount_font)
                    amount_width = amount_bbox[2] - amount_bbox[0]

                    right_padding = 109
                    amount_x = image_width - amount_width - right_padding

                    draw.text(
                        (amount_x, offset_y),
                        amount,
                        font=amount_font,
                        fill=self.tbank_history_amount_color,
                    )

                    x_position = self.tbank_history_name_base_x
                    for letter in name:
                        draw.text(
                            (x_position, offset_y),
                            letter,
                            font=name_font,
                            fill=(51, 51, 51),
                        )
                        x_position += name_font.getlength(letter) - 1.6
                elif i == 1:
                    offset_y = offsets[i] - 120
                    image_width = image.size[0]

                    amount_bbox = draw.textbbox((0, 0), amount, font=amount_font)
                    amount_width = amount_bbox[2] - amount_bbox[0]

                    right_padding = 109
                    amount_x = image_width - amount_width - right_padding

                    draw.text(
                        (amount_x, offset_y),
                        amount,
                        font=amount_font,
                        fill=self.tbank_history_amount_color,
                    )

                    x_position = self.tbank_history_name_base_x
                    for letter in name:
                        draw.text(
                            (x_position, offset_y),
                            letter,
                            font=name_font,
                            fill=(51, 51, 51),
                        )
                        x_position += name_font.getlength(letter) - 1.6
                elif i == 2:
                    offset_y = offsets[i] + 60
                    image_width = image.size[0]

                    amount_bbox = draw.textbbox((0, 0), amount, font=amount_font)
                    amount_width = amount_bbox[2] - amount_bbox[0]

                    right_padding = 109
                    amount_x = image_width - amount_width - right_padding

                    draw.text(
                        (amount_x, offset_y),
                        amount,
                        font=amount_font,
                        fill=self.tbank_history_amount_color,
                    )

                    x_position = self.tbank_history_name_base_x
                    for letter in name:
                        draw.text(
                            (x_position, offset_y),
                            letter,
                            font=name_font,
                            fill=(51, 51, 51),
                        )
                        x_position += name_font.getlength(letter) - 1.6
                elif i == 3:
                    offset_y = offsets[i] + 220
                    image_width = image.size[0]

                    amount_bbox = draw.textbbox((0, 0), amount, font=amount_font)
                    amount_width = amount_bbox[2] - amount_bbox[0]

                    right_padding = 109
                    amount_x = image_width - amount_width - right_padding

                    draw.text(
                        (amount_x, offset_y),
                        amount,
                        font=amount_font,
                        fill=self.tbank_history_amount_color,
                    )

                    x_position = self.tbank_history_name_base_x
                    for letter in name:
                        draw.text(
                            (x_position, offset_y),
                            letter,
                            font=name_font,
                            fill=(51, 51, 51),
                        )
                        x_position += name_font.getlength(letter) - 1.6

        elif transfer_type == "Сбер история переводов":
            draw.text((150, 45), time_text, font=time_font, fill=(0, 0, 0, 255))

            sber_positions = [
                ((225, 380), (935, 408)),
                ((225, 590), (935, 608)),
            ]
            for (name_pos, amt_pos), (name, amount) in zip(
                sber_positions, zip(names, amounts)
            ):
                draw.text(
                    name_pos,
                    name,
                    font=name_font,
                    stroke_width=0.3,
                    fill=(0, 0, 0, 255),
                )
                draw.text(
                    amt_pos,
                    amount,
                    font=amount_font,
                    fill=(34, 155, 76, 255),
                    stroke_width=0.5,
                    stroke_fill=(34, 155, 76, 255),
                )

        else:
            draw.text(
                self.time_position, time_text, font=time_font, fill=self.text_color
            )

            for i, (name, amount) in enumerate(zip(names, amounts)):
                offset_y = offsets[i]

                amount_bbox = draw.textbbox((0, 0), amount, font=amount_font)
                amount_width = amount_bbox[2] - amount_bbox[0]
                amount_x = self.tbank_history_amount_base_x - amount_width

                draw.text(
                    (amount_x, offset_y),
                    amount,
                    font=amount_font,
                    fill=self.tbank_history_amount_color,
                )

                x_position = self.tbank_history_name_base_x
                for letter in name:
                    draw.text(
                        (x_position, offset_y),
                        letter,
                        font=name_font,
                        fill=(51, 51, 51),
                    )
                    x_position += name_font.getlength(letter) - 1.4

        temp_path = "assets/imgs/temp_history.png"
        image.save(temp_path, quality=100)
        return temp_path

    async def create_bank_image(
        self, template, time_text, name_text, phone_text, amount_text
    ):
        image = Image.open(template)
        draw = ImageDraw.Draw(image)

        time_font = ImageFont.truetype(
            "assets/fonts/SFPRODISPLAYBOLD.OTF", self.time_font_size
        )
        name_font = ImageFont.truetype(
            "assets/fonts/Onest-SemiBold.ttf", self.bank_name_font_size
        )
        phone_font = ImageFont.truetype(
            "assets/fonts/Onest-SemiBold.ttf", self.bank_phone_font_size
        )
        amount_font = ImageFont.truetype(
            "assets/fonts/Onest-Bold.ttf", self.bank_amount_font_size
        )

        draw.text(self.time_position, time_text, font=time_font, fill=self.text_color)

        img_width, img_height = image.size

        amount_bbox = draw.textbbox((0, 0), amount_text, font=amount_font)
        amount_width = amount_bbox[2] - amount_bbox[0]
        amount_x = (img_width - amount_width) // 2
        amount_y = self.bank_amount_y

        padding = 20
        text_bbox = amount_font.getbbox(amount_text)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        img_size = (text_width + padding * 2, text_height + padding * 2)
        text_image = Image.new("RGBA", img_size, (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_image)

        text_position = (padding - text_bbox[0], padding - text_bbox[1])
        text_draw.text(
            text_position, amount_text, font=amount_font, fill=self.text_color
        )

        rotated = text_image.rotate(
            self.bank_amount_angle, resample=Image.BICUBIC, expand=True
        )

        draw.bitmap(
            (
                amount_x - rotated.width // 2 + text_width // 2,
                amount_y - rotated.height // 2 + text_height // 2,
            ),
            rotated,
        )

        name_bbox = draw.textbbox((0, 0), name_text, font=name_font)
        name_width = name_bbox[2] - name_bbox[0]
        name_x = (img_width - name_width) // 2
        name_y = self.bank_name_y

        draw.text((name_x, name_y), name_text, font=name_font, fill=self.text_color)

        phone_bbox = draw.textbbox((0, 0), phone_text, font=phone_font)
        phone_width = phone_bbox[2] - phone_bbox[0]
        phone_x = (img_width - phone_width) // 2
        phone_y = self.bank_phone_y

        draw.text((phone_x, phone_y), phone_text, font=phone_font, fill=self.text_color)

        temp_path = "assets/imgs/temp_bank.png"
        image.save(temp_path, quality=100)
        return temp_path

    async def create_tinkoff_image(
        self,
        template: str,
        time_text: str,
        datetime_text: str,
        name_text: str,
        phone_text: str,
        amount_text: str,
    ):
        image = Image.open(template)
        draw = ImageDraw.Draw(image)

        TEXT_COLOR = (40, 40, 40)

        DATETIME_SIZE = 50
        NAME_SIZE = 48
        PHONE_SIZE = 50
        AMOUNT_SIZE = 88

        DATETIME_Y = 247
        NAME_Y = 675
        AMOUNT_Y = 845

        PHONE_POSITION = (110, 2130)

        time_font = ImageFont.truetype(
            "assets/fonts/SFPRODISPLAYBOLD.OTF", self.time_font_size
        )
        datetime_font = ImageFont.truetype(
            "assets/fonts/SF Pro Text Medium2.ttf", DATETIME_SIZE
        )
        name_font = ImageFont.truetype("assets/fonts/SFProText-Regular.ttf", NAME_SIZE)
        phone_font = ImageFont.truetype(
            "assets/fonts/SFProText-Regular.ttf", PHONE_SIZE
        )
        amount_font = ImageFont.truetype(
            "assets/fonts/SFProText Bold-2.ttf", AMOUNT_SIZE
        )

        draw.text(self.time_position, time_text, font=time_font, fill=self.text_color)
        draw.text(PHONE_POSITION, phone_text, font=phone_font, fill=TEXT_COLOR)

        img_width, img_height = image.size

        datetime_bbox = draw.textbbox((0, 0), datetime_text, font=datetime_font)
        datetime_width = datetime_bbox[2] - datetime_bbox[0]
        datetime_x = (img_width - datetime_width) // 2
        datetime_y = DATETIME_Y

        draw.text(
            (datetime_x, datetime_y), datetime_text, font=datetime_font, fill=TEXT_COLOR
        )

        name_bbox = draw.textbbox((0, 0), name_text, font=name_font)
        name_width = name_bbox[2] - name_bbox[0]
        name_x = (img_width - name_width) // 2
        name_y = NAME_Y

        draw.text((name_x, name_y), name_text, font=name_font, fill=TEXT_COLOR)

        amount_bbox = draw.textbbox((0, 0), amount_text, font=amount_font)
        amount_width = amount_bbox[2] - amount_bbox[0]
        amount_x = (img_width - amount_width) // 2
        amount_y = AMOUNT_Y

        draw.text((amount_x, amount_y), amount_text, font=amount_font, fill=TEXT_COLOR)

        temp_path = "assets/imgs/temp_tbank.png"
        image.save(temp_path, quality=100)
        return temp_path

    async def start_bot(self):
        await self.dp.start_polling(self.bot)


def main():
    bot = BankBot()
    init_db()
    asyncio.run(bot.start_bot())


if __name__ == "__main__":
    main()
