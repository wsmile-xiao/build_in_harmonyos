"""Verify the installed package and run Yapsy's upstream tests."""

import base64
import hashlib
import json
import os
import sys
import unittest
from pathlib import Path


def restore_zip_fixtures(upstream_tests):
    """Restore the exact upstream ZIP bytes from reviewable text fixtures."""
    fixture_dir = upstream_tests / "test" / "pluginstoinstall"
    fixtures = {
        "autoinstallWRONGzipplugin.zip": "40887b7dbc2242203e5f6a1ea8e6d8872b42a88907b67188fb5b444f7495283e",
        "autoinstallZIPplugin.zip": "89322eb703a8363b9c3b60486c79fcdc5aca8189621f1e2dc3aa8266cf07b29d",
    }
    for name, expected_sha in fixtures.items():
        encoded = (fixture_dir / (name + ".b64")).read_bytes()
        raw = base64.b64decode(b"".join(encoded.split()), validate=True)
        if hashlib.sha256(raw).hexdigest() != expected_sha:
            raise AssertionError("upstream ZIP fixture digest mismatch: " + name)
        (fixture_dir / name).write_bytes(raw)


def main():
    package_folder = Path(sys.argv[1]).resolve()
    upstream_tests = Path(sys.argv[2]).resolve()
    report_path = Path(sys.argv[3])
    python_path = package_folder / "lib" / "python"
    sys.path.insert(0, str(python_path))

    import yapsy

    imported_path = Path(yapsy.__file__).resolve()
    if os.path.commonpath([str(imported_path), str(python_path)]) != str(python_path):
        raise AssertionError("Yapsy was not imported from the Conan package: %s" % imported_path)

    restore_zip_fixtures(upstream_tests)
    sys.path.insert(1, str(upstream_tests))
    from test.test_All import MainTestSuite

    result = unittest.TextTestRunner(verbosity=2).run(MainTestSuite)
    summary = {
        "package_import": str(imported_path),
        "package_import_check": "pass",
        "upstream_total": result.testsRun,
        "upstream_passed": result.testsRun - len(result.failures) - len(result.errors),
        "upstream_failed": len(result.failures),
        "upstream_errors": len(result.errors),
        "upstream_skipped": len(result.skipped),
        "successful": result.wasSuccessful(),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("packaged import: %s" % imported_path, flush=True)
    print("upstream suite: %d run, %d failed, %d errors, %d skipped" % (
        summary["upstream_total"], summary["upstream_failed"],
        summary["upstream_errors"], summary["upstream_skipped"]), flush=True)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
