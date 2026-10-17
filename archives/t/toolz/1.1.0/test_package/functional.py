#!/usr/bin/env python3
"""Exercise public toolz APIs through the installed package environment."""

import json
import os
import sys
import traceback


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: functional.py <package-folder> <report.json>")

    package_folder = os.path.realpath(sys.argv[1])
    report_path = sys.argv[2]
    python_root = os.path.join(package_folder, "lib", "python")
    results = []
    assertions = 0

    def equal(actual, expected):
        nonlocal assertions
        assertions += 1
        if actual != expected:
            raise AssertionError(f"expected {expected!r}, got {actual!r}")

    def true(value):
        nonlocal assertions
        assertions += 1
        if not value:
            raise AssertionError("expected a true value")

    def check(name, action):
        before = assertions
        try:
            action()
            results.append({"name": name, "status": "passed",
                            "assertions": assertions - before})
        except Exception as exc:
            results.append({"name": name, "status": "failed",
                            "assertions": assertions - before,
                            "error": f"{type(exc).__name__}: {exc}",
                            "traceback": traceback.format_exc()})

    def provenance():
        import toolz
        import tlz
        expected = os.path.realpath(python_root)
        for module in (toolz, tlz):
            module_path = os.path.realpath(module.__file__)
            true(os.path.commonpath((expected, module_path)) == expected)

    def functional_pipeline():
        from toolz import compose, frequencies
        from toolz.curried import map as curried_map
        words = "This cat jumped over this other cat!".lower().split()

        def clean_word(word):
            return word.rstrip(".,!?:;")

        count_words = compose(frequencies, curried_map(clean_word))
        equal(count_words(words), {
            "this": 2, "cat": 2, "jumped": 1, "over": 1, "other": 1})

    def iterable_operations():
        from toolz import partition_all, unique
        equal(list(partition_all(2, range(5))), [(0, 1), (2, 3), (4,)])
        equal(list(unique([1, 2, 1, 3, 2])), [1, 2, 3])

    def dictionary_operations():
        from toolz import assoc, get_in, merge, update_in
        value = {"user": {"name": "Ada", "visits": 2}}
        changed = update_in(value, ["user", "visits"], lambda n: n + 1)
        equal(get_in(["user", "visits"], changed), 3)
        equal(get_in(["missing"], changed, default="none"), "none")
        true(assoc(value, "active", True)["active"] is True)
        equal(merge({"a": 1}, {"b": 2}), {"a": 1, "b": 2})

    def functional_alias():
        import toolz
        import tlz
        from tlz.curried import map as tlz_map
        equal(tlz.pipe([1, 2, 3], list), [1, 2, 3])
        equal(list(tlz_map(lambda n: n * 2, [1, 2, 3])), [2, 4, 6])
        true(tlz.curry is toolz.curry)

    check("installed-package-provenance", provenance)
    check("functional-pipeline", functional_pipeline)
    check("iterable-operations", iterable_operations)
    check("dictionary-operations", dictionary_operations)
    check("tlz-compatibility-alias", functional_alias)

    summary = {
        "schema_version": 1,
        "package": "toolz/1.1.0",
        "test_groups": len(results),
        "assertions": assertions,
        "passed": sum(item["status"] == "passed" for item in results),
        "failed": sum(item["status"] == "failed" for item in results),
        "results": results,
    }
    os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
