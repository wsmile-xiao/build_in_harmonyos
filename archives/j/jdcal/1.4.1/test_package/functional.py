"""Exercise public jdcal APIs from the packaged module."""

import json
import os
import sys
from pathlib import Path


def main():
    package = Path(sys.argv[1]).resolve()
    report = Path(sys.argv[2])
    python_dir = package / "lib" / "python"
    import jdcal

    results = []

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
        imported = Path(jdcal.__file__).resolve()
        assert os.path.commonpath([str(imported), str(python_dir)]) == str(python_dir)
        assert jdcal.__version__ == "1.4.1"

    def gregorian_epoch():
        assert jdcal.gcal2jd(2000, 1, 1) == (2400000.5, 51544.0)
        assert jdcal.MJD_0 == 2400000.5
        assert jdcal.MJD_JD2000 == 51544.5

    def leap_year_centuries():
        assert jdcal.is_leap(2000)
        assert not jdcal.is_leap(1900)
        assert not jdcal.is_leap(2001)

    def gregorian_roundtrip():
        assert jdcal.jd2gcal(*jdcal.gcal2jd(1950, 1, 1)) == (1950, 1, 1, 0.0)
        assert jdcal.jd2gcal(*jdcal.gcal2jd(2000, 2, 29)) == (2000, 2, 29, 0.0)

    def normalized_dates():
        assert jdcal.gcal2jd(2000, 2, 30) == jdcal.gcal2jd(2000, 3, 1)
        assert jdcal.gcal2jd(2000, -2, -4) == jdcal.gcal2jd(1999, 9, 26)

    def julian_roundtrip():
        value = jdcal.jcal2jd(2000, 1, 1)
        assert value == (2400000.5, 51557.0)
        assert jdcal.jd2jcal(*value) == (2000, 1, 1, 0.0)

    def fractional_day():
        result = jdcal.jd2gcal(2400000.5, 51544.5)
        assert result[:3] == (2000, 1, 1)
        assert round(result[3], 12) == 0.5

    for name, action in (
        ("packaged_import", packaged_import),
        ("gregorian_epoch", gregorian_epoch),
        ("leap_year_centuries", leap_year_centuries),
        ("gregorian_roundtrip", gregorian_roundtrip),
        ("normalized_dates", normalized_dates),
        ("julian_roundtrip", julian_roundtrip),
        ("fractional_day", fractional_day),
    ):
        check(name, action)

    summary = {"package_folder": str(package), "total": len(results),
               "passed": sum(item["passed"] for item in results),
               "cases": results}
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"{summary['passed']}/{summary['total']} passed", flush=True)
    return 0 if summary["passed"] == summary["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
