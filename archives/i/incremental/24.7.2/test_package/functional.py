"""Exercise the packaged incremental library without network access."""

import json
import os
import sys
from pathlib import Path


def main():
    package = Path(sys.argv[1]).resolve()
    report = Path(sys.argv[2])
    import incremental
    from incremental import Version, getVersionString

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
        imported = Path(incremental.__file__).resolve()
        module_root = (package / "lib" / "python").resolve()
        assert os.path.commonpath([str(imported), str(module_root)]) == str(module_root)
        assert (module_root / "incremental" / "py.typed").is_file()
        assert all((module_root / "incremental" / name).is_file()
                   for name in ("__init__.py", "_version.py"))
        assert all(not (module_root / "incremental" / name).exists()
                   for name in ("update.py", "_hatch.py"))
        assert (package / "licenses" / "LICENSE").is_file()
        assert not (module_root / "incremental" / "tests").exists()
        assert incremental.__version__.public() == "24.7.2"

    def public_version():
        version = Version("demo", 1, 2, 3)
        assert version.public() == "1.2.3"
        assert getVersionString(version) == "demo 1.2.3"

    def prerelease_order():
        candidate = Version("demo", 1, 2, 3, release_candidate=2)
        release = Version("demo", 1, 2, 3)
        assert candidate.public() == "1.2.3rc2"
        assert candidate < release

    def post_and_dev_format():
        version = Version("demo", 1, 2, 3, post=1, dev=4)
        assert version.public() == "1.2.3.post1.dev4"
        assert version.local() == "1.2.3.post1.dev4"

    def next_version():
        assert Version("demo", "NEXT", 0, 0).public() == "NEXT"

    def ordering():
        assert Version("demo", 2, 0, 0) > Version("demo", 1, 9, 9)

    for name, action in (
        ("packaged_import", packaged_import),
        ("public_version", public_version),
        ("prerelease_order", prerelease_order),
        ("post_and_dev_format", post_and_dev_format),
        ("next_version", next_version),
        ("ordering", ordering),
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
