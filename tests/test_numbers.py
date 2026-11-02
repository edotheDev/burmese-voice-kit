import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from numbers_my import to_words, replace_numbers  # noqa: E402


def test_cases():
    assert to_words(2027) == "နှစ်ထောင့်နှစ်ဆယ့်ခုနစ်"
    assert to_words(30) == "သုံးဆယ်"
    assert to_words(200000) == "နှစ်သိန်း"
    assert to_words(15) == "ဆယ့်ငါး"
    assert to_words(10) == "တစ်ဆယ်"
    assert to_words(4000000) == "လေးသန်း"
    assert replace_numbers("30%")[0] == "သုံးဆယ် ရာခိုင်နှုန်း"


def test_myanmar_digits_and_flags():
    assert replace_numbers("၃၀")[0] == "သုံးဆယ်"
    assert replace_numbers("2,027")[0] == to_words(2027)
    text, flags = replace_numbers("10000000 and 3.5")
    assert text == "10000000 and 3.5" and len(flags) == 2
    assert to_words(0) == "သုည"


if __name__ == "__main__":
    test_cases()
    test_myanmar_digits_and_flags()
    print("all passed")
