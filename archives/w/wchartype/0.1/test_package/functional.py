"""Exercise the packaged wchartype module without external dependencies."""

import doctest
import json
import os
import sys
from collections import Counter
from pathlib import Path

import wchartype


def _character_category(char):
    if wchartype.is_kanji(char):
        return "kanji"
    if wchartype.is_hiragana(char):
        return "hiragana"
    if wchartype.is_katakana(char):
        return "katakana"
    if wchartype.is_hangul(char):
        return "hangul"
    if wchartype.is_full_digit(char):
        return "full_width_digit"
    if wchartype.is_full_letter(char):
        return "full_width_letter"
    if wchartype.is_full_punct(char):
        return "full_width_punctuation"
    if char == chr(wchartype.IDEOGRAPHIC_SPACE):
        return "ideographic_space"
    if char.isascii():
        return "ascii"
    return "other"


def _process_text_file(input_path, output_path):
    text = input_path.read_text(encoding="utf-8")
    characters = [
        {
            "index": index,
            "character": char,
            "codepoint": f"U+{ord(char):04X}",
            "category": _character_category(char),
            "is_asian": wchartype.is_asian(char),
            "is_full_width": wchartype.is_full_width(char),
        }
        for index, char in enumerate(text)
    ]
    payload = {
        "source": input_path.name,
        "character_count": len(characters),
        "category_counts": dict(sorted(Counter(
            item["category"] for item in characters).items())),
        "characters": characters,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    return payload


def main():
    package = Path(sys.argv[1]).resolve()
    report = Path(sys.argv[2])
    results = []
    doctest_summary = {}

    def check(name, action):
        try:
            action()
            results.append({"name": name, "passed": True})
            print("PASS", name, flush=True)
        except Exception as exc:
            results.append({"name": name, "passed": False,
                            "error": f"{type(exc).__name__}: {exc}"})
            print("FAIL", name, flush=True)

    def packaged_import():
        imported = Path(wchartype.__file__).resolve()
        assert os.path.commonpath([str(imported), str(package)]) == str(package), imported

    def upstream_doctests():
        result = doctest.testmod(wchartype)
        doctest_summary.update({"total": result.attempted,
                                "passed": result.attempted - result.failed,
                                "failed": result.failed})
        assert result.failed == 0, f"{result.failed}/{result.attempted} doctests failed"
        assert result.attempted == 37, result.attempted

    def character_categories():
        assert wchartype.is_kanji("漢") and wchartype.is_hanzi("漢")
        assert wchartype.is_hiragana("わ")
        assert wchartype.is_katakana("リ")
        assert wchartype.is_half_katakana("ﾑ")
        assert wchartype.is_hangul("류") and wchartype.is_hangul("ﾸ")

    def width_and_ascii_boundaries():
        assert not wchartype.is_full_width("a")
        assert wchartype.is_full_width("　")
        assert not wchartype.is_asian("　")
        assert wchartype.is_full_digit("５")
        assert wchartype.is_full_letter("Ｑ")
        assert wchartype.is_full_punct("％")

    def mixed_text_consumer_workflow():
        input_path = Path(__file__).resolve().parent / "data" / "mixed-script.txt"
        output_path = report.with_name("mixed-text-report.json")
        produced = _process_text_file(input_path, output_path)
        written = json.loads(output_path.read_text(encoding="utf-8"))
        expected_categories = {
            "ascii": 1,
            "full_width_digit": 1,
            "full_width_punctuation": 1,
            "hangul": 1,
            "hiragana": 1,
            "ideographic_space": 1,
            "katakana": 1,
            "kanji": 1,
        }
        if produced != written or written["character_count"] != 8:
            raise AssertionError("consumer output does not describe the processed input")
        if written["category_counts"] != expected_categories:
            raise AssertionError("consumer output has unexpected character categories")
        reconstructed = "".join(item["character"] for item in written["characters"])
        if reconstructed != input_path.read_text(encoding="utf-8"):
            raise AssertionError("consumer output did not preserve the input text")
        print("consumer workflow processed 8 mixed-script characters and wrote JSON",
              flush=True)

    for name, action in (("packaged_import", packaged_import),
                         ("upstream_doctests", upstream_doctests),
                         ("character_categories", character_categories),
                         ("width_and_ascii_boundaries", width_and_ascii_boundaries),
                         ("mixed_text_consumer_workflow", mixed_text_consumer_workflow)):
        check(name, action)

    summary = {"package_folder": str(package), "total": len(results),
               "passed": sum(item["passed"] for item in results), "cases": results,
               "upstream_doctests": doctest_summary}
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"{summary['passed']}/{summary['total']} consumer checks passed", flush=True)
    if doctest_summary:
        print("upstream doctests: "
              f"{doctest_summary['passed']}/{doctest_summary['total']} passed",
              flush=True)
    return 0 if summary["passed"] == summary["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
