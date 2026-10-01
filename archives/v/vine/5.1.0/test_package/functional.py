#!/usr/bin/env python3
"""Exercise Vine through the installed Conan package environment."""

import json
import os
import sys
from pathlib import Path


def main():
    package = Path(sys.argv[1]).resolve()
    report = Path(sys.argv[2])
    import vine

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
        imported = Path(vine.__file__).resolve()
        assert os.path.commonpath([str(imported), str(package)]) == str(package), imported

    def version():
        assert vine.__version__ == "5.1.0"
        assert tuple(vine.version_info[:3]) == (5, 1, 0)

    def promise_callback():
        calls = []
        result = vine.promise(lambda value: calls.append(value))
        result("consumer-value")
        assert result.ready
        assert calls == ["consumer-value"]

    def promise_chain():
        calls = []
        result = vine.promise()
        result.then(lambda value: calls.append(value + 1))
        result(40)
        assert calls == [41]

    def barrier_completion():
        calls = []
        first, second = vine.promise(), vine.promise()
        joined = vine.barrier([first, second], callback=vine.promise(lambda: calls.append("done")))
        first()
        assert not joined.ready and calls == []
        second()
        assert joined.ready and calls == ["done"]

    def conversion_helpers():
        callback = lambda: None
        assert vine.maybe_promise(callback).fun is callback
        assert vine.maybe_promise(None) is None
        assert vine.ensure_promise(None).ready is False

    for name, action in (("packaged_import", packaged_import),
                         ("version", version),
                         ("promise_callback", promise_callback),
                         ("promise_chain", promise_chain),
                         ("barrier_completion", barrier_completion),
                         ("conversion_helpers", conversion_helpers)):
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
