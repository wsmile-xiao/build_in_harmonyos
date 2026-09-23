#!/usr/bin/env python3
"""Conan test_package — libzahl 1.0.

Consumer-side verification (R34): compiles and runs a real program that
calls libzahl APIs (zsetup/zsets/zadd/zmul/zsub/zpowu/zgcd/zstr/zcmp).
"""

import json
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException


class LibzahlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies[self.tested_reference_str]
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = executables.get("c", "clang")
        include_dir = dep.cpp_info.includedirs[0]
        lib_dir = dep.cpp_info.libdirs[0]
        self.run(
            " ".join(
                [
                    shlex.quote(cc),
                    "-std=c99",
                    f"-I{shlex.quote(include_dir)}",
                    "test.c",
                    f"-L{shlex.quote(lib_dir)}",
                    "-lzahl",
                    f"-o{shlex.quote(os.path.join(self.build_folder, 'test_libzahl'))}",
                ]
            ),
            cwd=self.source_folder,
        )

    def test(self):
        test_bin = os.path.join(self.build_folder, "test_libzahl")
        discovered = 6
        passed = 0
        try:
            self.run(test_bin)
            passed = discovered
        except Exception as exc:
            self.output.error(f"test_libzahl failed: {exc}")

        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": "./test_libzahl",
            "discovered": discovered,
            "passedCount": passed,
        }
        marker = f"HMBS_TEST_PACKAGE_RESULT={json.dumps(tp_result)}"
        self.output.info(marker)
        print(marker, flush=True)

        if passed != discovered:
            raise ConanException("test_package checks failed")
