"""Exercise public parso APIs from the packaged module."""

import json
import os
import sys
from pathlib import Path


def main():
    package = Path(sys.argv[1]).resolve()
    report = Path(sys.argv[2])
    python_dir = package / "lib" / "python"
    sys.path.insert(0, str(python_dir))

    import parso

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
        imported = Path(parso.__file__).resolve()
        package_path = (python_dir / "parso").resolve()
        assert os.path.commonpath([str(imported), str(package_path)]) == str(package_path)
        assert parso.__version__ == "0.8.7"

    def grammar_resources():
        for version in ("3.6", "3.8", "3.11", "3.14"):
            grammar = parso.load_grammar(version=version)
            assert grammar is not None

    def parse_and_roundtrip():
        code = "def add(a, b):\n    return a + b\n"
        module = parso.parse(code, version="3.8")
        assert module.get_code() == code
        assert "add" in module.get_used_names()

    def error_recovery():
        grammar = parso.load_grammar(version="3.8")
        module = grammar.parse("if :\n    pass\n")
        errors = list(grammar.iter_errors(module))
        assert errors
        assert errors[0].message.startswith("SyntaxError:")

    for name, action in (
        ("packaged_import", packaged_import),
        ("grammar_resources", grammar_resources),
        ("parse_and_roundtrip", parse_and_roundtrip),
        ("error_recovery", error_recovery),
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
