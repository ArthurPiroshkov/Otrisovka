from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

# =========================
# Конфигурация рендеринга
# =========================

@dataclass
class OzonHistoryConfig:
    template_path: str = "ozon_history_new.png"

    # Базовые Y для строк 1..4 (подгони под свой шаблон)
    row_ys: List[int] = field(default_factory=lambda: [920, 1113, 1286, 1555])

    # Координаты
    name_x: int = 230
    right_padding: int = 87  # от правого края экрана до конца суммы

    # Шрифты и размеры
    name_font_path: str = "gteestiprodisplay_light.otf"
    amount_font_path: str = "Onest-Regular.ttf"
    name_font_size: int = 50
    amount_font_size: int = 47
    row_center_offset: int = -15

    # ОТДЕЛЬНЫЙ шрифт для знака '+'
    plus_font_path: str = "gteestiprodisplay_light.otf"
    plus_font_size: int = 34 
    plus_bold: int = 0.8 
    plus_gap: int = 4
    plus_y_offset: int = 6

    # Цвета
    name_color: Tuple[int, int, int] = (255, 255, 255)
    amount_color: Tuple[int, int, int] = (0, 236, 113)


# =========================
# Валидация и парсинг
# =========================

class OzonHistoryInputError(ValueError):
    pass

def parse_ozon_text_payload(payload: str) -> Tuple[List[str], List[int]]:
    lines = [line.strip() for line in payload.strip().splitlines() if line.strip()]
    if len(lines) != 8:
        raise OzonHistoryInputError(
            "Ожидается 8 строк: ФИО1, Сумма1, ..., ФИО4, Сумма4."
        )

    names = [lines[i] for i in (0, 2, 4, 6)]
    amount_strs = [lines[i] for i in (1, 3, 5, 7)]

    amounts: List[int] = []
    for a in amount_strs:
        try:
            val = int(a.replace(" ", ""))
        except ValueError:
            raise OzonHistoryInputError(f"Сумма должна быть целым числом: «{a}».")
        if val <= 0:
            raise OzonHistoryInputError(f"Сумма должна быть > 0: «{a}».")
        amounts.append(val)

    return names, amounts

# =========================
# Форматирование и отрисовка
# =========================

def format_ruble_amount(amount: int) -> str:
    """12345 -> '12 345' (без знака и без ₽; '+' рисуем отдельно)."""
    return f"{amount:,}".replace(",", " ")

def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def render_ozon_history(
    names: List[str],
    amounts: List[int],
    out_path: str = "ozon_history_out.png",
    cfg: Optional[OzonHistoryConfig] = None,
) -> str:
    if cfg is None:
        cfg = OzonHistoryConfig()

    if len(names) != 4 or len(amounts) != 4:
        raise OzonHistoryInputError("Нужно ровно 4 имени и 4 суммы.")

    image = Image.open(cfg.template_path).convert("RGBA")
    draw = ImageDraw.Draw(image)

    name_font   = _load_font(cfg.name_font_path,   cfg.name_font_size)
    amount_font = _load_font(cfg.amount_font_path, cfg.amount_font_size)
    plus_font = _load_font(cfg.plus_font_path, cfg.plus_font_size)

    img_width, _ = image.size
    row_ys = cfg.row_ys
    if len(row_ys) != 4:
        raise ValueError("В конфиге должно быть ровно 4 координаты Y для строк.")

    for i in range(4):
        name = names[i]
        amount_text = format_ruble_amount(amounts[i])
        y_top = row_ys[i]

        # Имя — слева
        draw.text((cfg.name_x, y_top), name, font=name_font, fill=cfg.name_color)

        # Общая «середина строки» по имени
        name_bbox = draw.textbbox((0, 0), name, font=name_font)
        name_h = name_bbox[3] - name_bbox[1]
        mid_y = y_top + name_h // 2 + cfg.row_center_offset

        # ---- сумма справа (правое выравнивание, вертикально по центру mid_y)
        x_right = img_width - cfg.right_padding
        amt_bbox = draw.textbbox((0, 0), amount_text, font=amount_font)
        amt_w = amt_bbox[2] - amt_bbox[0]
        amt_h = amt_bbox[3] - amt_bbox[1]

        amount_x = x_right - amt_w
        amount_y = int(mid_y - amt_h / 2)
        draw.text((amount_x, amount_y), amount_text, font=amount_font, fill=cfg.amount_color)

        # ---- плюс слева от суммы, тот же центр mid_y
        plus_text = "+"
        sw = int(round(cfg.plus_bold))
        plus_bbox = draw.textbbox((0, 0), plus_text, font=plus_font, stroke_width=sw)
        plus_w = plus_bbox[2] - plus_bbox[0]
        plus_h = plus_bbox[3] - plus_bbox[1]

        plus_x = amount_x - cfg.plus_gap - plus_w
        plus_y = int(mid_y - plus_h / 2) + cfg.plus_y_offset

        draw.text(
            (plus_x, plus_y),
            plus_text,
            font=plus_font,
            fill=cfg.amount_color,
            stroke_width=sw,            
            stroke_fill=cfg.amount_color,
        )

    image.save(out_path, quality=100)
    return out_path

def render_ozon_from_text(payload: str, out_path: str = "ozon_history_out.png", cfg: Optional[OzonHistoryConfig] = None) -> str:
    names, amounts = parse_ozon_text_payload(payload)
    return render_ozon_history(names, amounts, out_path=out_path, cfg=cfg)

if __name__ == "__main__":
    demo = """Никита Никитович
10
Тарас Григорьевич
10
Азамат Абдуллаев
10
Антон Вишня
10
"""
    path = render_ozon_from_text(demo, out_path="ozon_demo.png")
    print(f"готово: {path}")
