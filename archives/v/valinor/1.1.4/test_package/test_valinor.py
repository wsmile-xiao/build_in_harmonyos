#!/usr/bin/env python3
"""Consumer test for valinor 1.1.4 (5 real checks, no hardware/IDE needed).

1. import valinor works from the packaged site-packages
2. valinor.main exposes main()
3. elf.get_files_from_executable on a non-ELF file returns []
4. gdb.launcher('gdb') factory returns a callable
5. logging_setup.init() runs without raising

The script counts real passing assertions in `passed` and prints
HMBS_TEST_PACKAGE_RESULT itself with discovered/passedCount from that
counter (deterministic, no stdout string counting). Exit 0 only when
all 5 pass.
"""
import json
import os
import sys
import tempfile


def main():
    discovered = 5
    passed = 0
    failures = []

    try:
        import valinor
        assert hasattr(valinor, "main")
        passed += 1
    except Exception as e:
        failures.append("import valinor: %s" % e)

    try:
        # valinor/__init__.py does from .main import main, so valinor.main
        # (and from valinor import main) is the entry function itself, not
        # the submodule. Accept either shape: function directly, or module
        # exposing .main.
        from valinor import main as main_obj
        _fn = main_obj if callable(main_obj) else getattr(main_obj, "main", None)
        assert callable(_fn), type(main_obj)
        passed += 1
    except Exception as e:
        failures.append("valinor.main callable: %s" % e)

    try:
        from valinor import elf as elf_mod
        fd, path = tempfile.mkstemp(suffix=".bin")
        try:
            with os.fdopen(fd, "w") as f:
                f.write("ELF")
            files = elf_mod.get_files_from_executable(path)
            assert files == [], files
            passed += 1
        finally:
            os.unlink(path)
    except Exception as e:
        failures.append("elf non-ELF returns []: %s" % e)

    try:
        from valinor import gdb as gdb_mod
        launch = gdb_mod.launcher("gdb")
        assert callable(launch)
        passed += 1
    except Exception as e:
        failures.append("gdb.launcher factory: %s" % e)

    try:
        from valinor import logging_setup
        logging_setup.init()
        passed += 1
    except Exception as e:
        failures.append("logging_setup.init: %s" % e)

    ok = (passed == discovered)
    for f in failures:
        print("FAIL: %s" % f)
    print("valinor consumer: %d/%d passed" % (passed, discovered))
    marker = {
        "executed": True,
        "passed": ok,
        "command": "python3 test_valinor.py",
        "discovered": discovered,
        "passedCount": passed,
    }
    print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
