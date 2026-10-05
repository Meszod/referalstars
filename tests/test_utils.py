from app.utils.referral import build_referral_link, parse_start_arg
from app.utils.validators import parse_milestones, parse_positive_int


def test_parse_positive_int():
    assert parse_positive_int("100") == 100
    for bad in ("0", "-5", "12.5", "abc", "", " ", "1e3", "١٢٣", "9999999999"):
        assert parse_positive_int(bad) is None


def test_parse_milestones():
    assert parse_milestones("10:5, 20:10") == {10: 5, 20: 10}
    assert parse_milestones("0") == {}
    assert parse_milestones("abc") is None
    assert parse_milestones("10:x") is None


def test_referral_link_and_arg():
    assert build_referral_link("@bot", 5) == "https://t.me/bot?start=5"
    assert parse_start_arg("123") == 123
    assert parse_start_arg("abc") is None and parse_start_arg(None) is None
