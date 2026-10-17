#!/usr/bin/env python3
"""Conan test_package — snowball 2.2.0 (libstemmer)

L1 consumer test: compile test.c directly against the installed package
(same R33 pattern as the main recipe — no CMake involved, robust on both
the adaptation machine and CI workers), run API-level assertions
(29-language inventory, alias resolution, stem expectations for 13
languages pinned from the release-dated data run, emoji/numeric
regression mirrors of upstream tests/stemtest.c, KOI8-R availability),
then exercise the stemwords CLI end-to-end on a fixture word list.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class SnowballTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R33: compiler from Conan conf (same as main recipe), never env.
        ce = self.conf.get("tools.build:compiler_executables",
                           default={}, check_type=dict)
        cc = ce.get("c") or "clang"

        pkg = self.dependencies["snowball"].package_folder
        inc = os.path.join(pkg, "include")
        lib = os.path.join(pkg, "lib")
        src = os.path.join(self.source_folder, "test.c")
        exe = os.path.join(self.build_folder, "test_snowball")

        # 1) consumer compile+link against the installed package
        self.run(f'"{cc}" -O2 -Wall -I"{inc}" "{src}" -L"{lib}" -lstemmer -o "{exe}"')

        if can_run(self):
            # 2) library consumer binary (native OHOS arm64: runs directly)
            ret = self.run(f'"{exe}"', ignore_errors=True)
            tp_passed = (ret == 0)
            print(f'HMBS_TEST_PACKAGE_RESULT={{"executed":true,"passed":{str(tp_passed).lower()},"command":"{exe}"}}')
            if not tp_passed:
                raise Exception("test_package: test_snowball failed")

            # 3) stemwords CLI end-to-end on the fixture word list
            stemwords = os.path.join(pkg, "bin", "stemwords")
            fixture = os.path.join(self.source_folder, "fixture_english_voc.txt")
            expected = os.path.join(self.source_folder, "fixture_english_expected.txt")
            out = os.path.join(self.build_folder, "fixture_out.txt")
            self.run(f'"{stemwords}" -c UTF_8 -l english -i "{fixture}" -o "{out}"')
            with open(expected, "rb") as f:
                want = f.read()
            with open(out, "rb") as f:
                got = f.read()
            if want != got:
                raise Exception(
                    "test_package: stemwords CLI output mismatch:\n"
                    f"want: {want!r}\n got: {got!r}")
            print("HMBS_TEST_PACKAGE_CLI_RESULT=pass")
        else:
            print("HMBS_TEST_PACKAGE_RESULT={\"executed\":false,\"passed\":true,"
                  "\"command\":\"cross-build: compile-only verification\"}")
