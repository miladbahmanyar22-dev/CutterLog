# ==================================================
# FILE: tests/test_utils.py
# ==================================================
from core.persian_utils import (
    to_persian_numbers, normalize_to_english_digits,
    format_toman, number_to_persian_words, parse_jalali_text
)


def test_digit_conversions():
    assert to_persian_numbers("1234567890") == "۱۲۳۴۵۶۷۸۹۰"
    assert normalize_to_english_digits("۱۲۳۴۵۶۷۸۹۰") == "1234567890"
    assert normalize_to_english_digits("١٢٣٤٥٦٧٨٩٠") == "1234567890"


def test_format_toman():
    assert format_toman(15000000) == "۱۵,۰۰۰,۰۰۰ تومان"
    assert format_toman(0) == "۰ تومان"


def test_number_to_persian_words():
    assert "پانزده میلیون تومان" in number_to_persian_words(15000000)
    assert "یک میلیون و پانصد هزار تومان" in number_to_persian_words(1500000)


def test_parse_jalali_text():
    j_date = parse_jalali_text("۱۴۰۵/۰۵/۲۵")
    assert j_date is not None
    assert j_date.year == 1405
    assert j_date.month == 5
    assert j_date.day == 25