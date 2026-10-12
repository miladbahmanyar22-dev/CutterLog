# ==================================================
# FILE: core/persian_utils.py
# ==================================================
from datetime import datetime, date
from typing import Optional
import jdatetime


def to_persian_numbers(input_val) -> str:
    """تبدیل تمام ارقام انگلیسی به فارسی"""
    if input_val is None:
        return ""
    text = str(input_val)
    en_to_fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    return text.translate(en_to_fa)


def normalize_to_english_digits(input_val) -> str:
    """تبدیل تمام ارقام فارسی و عربی به انگلیسی جهت اعتبارسنجی و تبدیل عددی"""
    if input_val is None:
        return ""
    text = str(input_val).strip()
    fa_to_en = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    return text.translate(fa_to_en)


def format_toman(amount: int) -> str:
    """فرمت‌دهی ۳ رقم ۳ رقم مبالغ با پسوند تومان و ارقام فارسی"""
    if not amount:
        return "۰ تومان"
    formatted = f"{int(amount):,}"
    return f"{to_persian_numbers(formatted)} تومان"


def gregorian_to_jalali(dt: Optional[datetime]) -> str:
    """تبدیل تاریخ میلادی به تاریخ شمسی خوانا"""
    if not dt:
        return "-"
    try:
        j_dt = jdatetime.datetime.fromgregorian(datetime=dt)
        return to_persian_numbers(j_dt.strftime("%Y/%m/%d"))
    except Exception:
        return "-"


def number_to_persian_words(number: int) -> str:
    """تبدیل مبالغ عددی به حروف فارسی با پسوند تومان"""
    if not number or number <= 0:
        return ""

    ones = ["", "یک", "دو", "سه", "چهار", "پنج", "شش", "هفت", "هشت", "نه"]
    teens = ["ده", "یازده", "دوازده", "سیزده", "چهارده", "پانزده", "شانزده", "هفده", "هجده", "نوزده"]
    tens = ["", "", "بیست", "سی", "چهل", "پنجاه", "شصت", "هفتاد", "هشتاد", "نود"]
    hundreds = ["", "صد", "دویست", "سیصد", "چهارصد", "پانصد", "ششصد", "هفتصد", "هشتصد", "نهصد"]
    thousands = ["", "هزار", "میلیون", "میلیارد", "تریلیون"]

    def _convert_group(n: int) -> str:
        parts = []
        c = n // 100
        r = n % 100
        if c > 0:
            parts.append(hundreds[c])
        if 10 <= r <= 19:
            parts.append(teens[r - 10])
        else:
            t = r // 10
            o = r % 10
            if t > 0:
                parts.append(tens[t])
            if o > 0:
                parts.append(ones[o])
        return " و ".join(parts)

    num_str = str(int(number))
    groups = []
    while len(num_str) > 0:
        groups.append(int(num_str[-3:]))
        num_str = num_str[:-3]

    words = []
    for i, g in enumerate(groups):
        if g > 0:
            converted = _convert_group(g)
            scale = thousands[i]
            if scale:
                words.append(f"{converted} {scale}")
            else:
                words.append(converted)

    words.reverse()
    result = " و ".join(words)
    return f"{result} تومان" if result else ""


def parse_jalali_text(text_val: str) -> Optional[jdatetime.date]:
    """تبدیل رشته تاریخ شمسی (مانند ۱۴۰۵/۰۵/۲۵) به شیء jdatetime.date"""
    if not text_val:
        return None
    clean_text = normalize_to_english_digits(text_val).replace("-", "/").strip()
    try:
        parts = [int(p) for p in clean_text.split("/") if p.strip()]
        if len(parts) == 3:
            return jdatetime.date(parts[0], parts[1], parts[2])
    except Exception:
        return None
    return None


def get_persian_date_readable(j_date: Optional[jdatetime.date]) -> str:
    """تبدیل تاریخ شمسی به متن روز هفته و ماه (مثلاً: شنبه، ۲۵ مرداد ۱۴۰۵)"""
    if not j_date:
        return ""
    weekdays = {
        0: "شنبه", 1: "یکشنبه", 2: "دوشنبه", 3: "سه‌شنبه",
        4: "چهارشنبه", 5: "پنج‌شنبه", 6: "جمعه"
    }
    month_names = {
        1: "فروردین", 2: "اردیبهشت", 3: "خرداد", 4: "تیر", 5: "مرداد", 6: "شهریور",
        7: "مهر", 8: "آبان", 9: "آذر", 10: "دی", 11: "بهمن", 12: "اسفند"
    }
    weekday_name = weekdays.get(j_date.weekday(), "")
    month_name = month_names.get(j_date.month, "")
    day_str = to_persian_numbers(j_date.day)
    year_str = to_persian_numbers(j_date.year)
    return f"{weekday_name}، {day_str} {month_name} {year_str}"


def get_deadline_relative_text(deadline_j_date: Optional[jdatetime.date]) -> str:
    """محاسبه دقیق فاصله زمانی تا ددلاین بر مبنای تاریخ امروز سیستم"""
    if not deadline_j_date:
        return ""
    today_j = jdatetime.date.today()
    delta_days = (deadline_j_date - today_j).days

    if delta_days == 0:
        return "امروز مهلت تحویل است ⏳"
    elif delta_days > 0:
        return f"{to_persian_numbers(delta_days)} روز مانده تا تحویل ⏳"
    else:
        passed = abs(delta_days)
        return f"{to_persian_numbers(passed)} روز از مهلت تحویل گذشته ⚠️"


def clean_studio_display_name(name: Optional[str], default: str = "بدون استودیو") -> str:
    """
    پاکسازی پیشوندهای تکراری نظیر 'استودیو' و 'آتلیه' از ابتدای نام جهت استفاده در برچسب‌های
    استودیو: {name} یا (استودیو {name}) بدون ایجاد تکرار
    """
    if not name:
        return default
    text = str(name).strip()
    prefixes = ["استودیوی ", "استودیو ", "اتلیه ", "آتلیه "]
    modified = True
    while modified:
        modified = False
        for prefix in prefixes:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
                modified = True
    return text if text else default


def format_studio_title(name: Optional[str], default: str = "بدون استودیو") -> str:
    """
    تولید یک عنوان یکپارچه با پیشوند استاندارد 'استودیو'
    """
    cleaned = clean_studio_display_name(name, default=default)
    if cleaned in ["بدون استودیو", "متفرقه", "عمومی", "استودیوی عمومی"]:
        return cleaned
    return f"استودیو {cleaned}"