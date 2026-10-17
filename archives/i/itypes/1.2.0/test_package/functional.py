"""Exercise public itypes behavior through the packaged Python module."""

import json
import os
import sys
from pathlib import Path


def main():
    package = Path(sys.argv[1]).resolve()
    report = Path(sys.argv[2])
    module_dir = package / "lib" / "python"
    sys.path.insert(0, str(module_dir))

    import itypes

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
        imported = Path(itypes.__file__).resolve()
        assert os.path.commonpath(
            [str(imported), str(module_dir)]) == str(module_dir)
        assert itypes.__version__ == "1.2.0"
        run_paths = [Path(item).resolve() for item in
                     os.environ.get("PYTHONPATH", "").split(os.pathsep) if item]
        assert module_dir.resolve() in run_paths

    def nested_immutable_conversion():
        value = itypes.Dict({"items": [1, {"name": "a"}]})
        assert isinstance(value["items"], itypes.List)
        assert isinstance(value["items"][1], itypes.Dict)

    def copy_on_write():
        original = itypes.Dict({"a": 1, "b": 2})
        changed = original.set("a", 3)
        removed = original.delete("b")
        assert original == {"a": 1, "b": 2}
        assert changed == {"a": 3, "b": 2}
        assert removed == {"a": 1}

    def immutable_assignment():
        value = itypes.Dict({"a": 1})
        try:
            value["a"] = 2
        except TypeError:
            return
        raise AssertionError("item assignment unexpectedly succeeded")

    def nested_updates():
        value = itypes.Dict({"items": ["a", "b", "c"]})
        assert value.get_in(["items", -1]) == "c"
        assert value.get_in(["missing"], "fallback") == "fallback"
        assert value.set_in(["items", 1], "x") == {"items": ["a", "x", "c"]}
        assert value.delete_in(["items", 0]) == {"items": ["b", "c"]}

    def equality_hash_and_conversion():
        value = itypes.Dict({"a": 1, "b": [2, 3]})
        assert value == {"a": 1, "b": [2, 3]}
        assert isinstance(hash(value), int)
        mutable = itypes.to_mutable(value)
        assert mutable == {"a": 1, "b": [2, 3]}
        assert itypes.to_immutable(mutable) == value

    def immutable_object_properties():
        class Document(itypes.Object):
            def __init__(self, title):
                self._title = title

            @property
            def title(self):
                return self._title

        document = Document("itypes")
        assert document.title == "itypes"
        try:
            document.title = "changed"
        except TypeError:
            return
        raise AssertionError("property assignment unexpectedly succeeded")

    for name, action in (
        ("packaged_import", packaged_import),
        ("nested_immutable_conversion", nested_immutable_conversion),
        ("copy_on_write", copy_on_write),
        ("immutable_assignment", immutable_assignment),
        ("nested_updates", nested_updates),
        ("equality_hash_and_conversion", equality_hash_and_conversion),
        ("immutable_object_properties", immutable_object_properties),
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
    raise SystemExit(main())
