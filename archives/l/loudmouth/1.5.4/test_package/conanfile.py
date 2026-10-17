#!/usr/bin/env python3
"""Conan test_package for loudmouth — consumer smoke test.

Builds test.c (real loudmouth-1 API calls: connection construction/state,
XML message-node construction + serialization) and runs it through the bash
wrapper (reliable ELF execution on OHOS). The test binary writes an
authoritative counts JSON {"passed":N,"failed":M}; this file reads it and
emits the HMBS_TEST_PACKAGE_RESULT machine marker from those exact numbers
(no stdout parsing / arithmetic).
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import load


class LoudmouthTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        package = self.dependencies["loudmouth"].package_folder
        required = [
            "include/loudmouth-1.0/loudmouth/loudmouth.h",
            "include/loudmouth-1.0/loudmouth/lm-connection.h",
            "include/loudmouth-1.0/loudmouth/lm-message-node.h",
            # NOTE: upstream installs the pkg-config module as
            # `loudmouth-1.0.pc` (from loudmouth-1.0.pc.in in configure's
            # pkgconfig_DATA).  It is NOT `loudmouth-1.pc` — that name is only
            # the Conan `pkg_config_name` used for the generated consumer .pc
            # (PkgConfigDeps), which does not rename the installed upstream
            # file.  Validation checks the file that `make install` actually
            # produces inside the package.
            "lib/pkgconfig/loudmouth-1.0.pc",
        ]
        missing = [x for x in required if not os.path.exists(os.path.join(package, x))]
        if missing:
            raise ConanException(f"PACKAGE_VALIDATION missing={missing}")
        la_files = [
            os.path.join(root, name)
            for root, _, names in os.walk(package)
            for name in names
            if name.endswith(".la")
        ]
        if la_files:
            raise ConanException(f"PACKAGE_VALIDATION unexpected_libtool_archives={la_files}")

        # Run the smoke test through the injected /bin/sh (toybox ash, whose
        # getcwd works on HMDFS) with the conanrun env (provides glib's
        # LD_LIBRARY_PATH). HMBS platform diagnostic [shell_getcwd]: use the
        # injected CONFIG_SHELL=/bin/sh; do not hardcode /data/service/hnp/bin/bash.
        bash = os.environ.get("CONFIG_SHELL", "/bin/sh")
        exe = os.path.join(self.cpp.build.bindirs[0], "test_loudmouth")
        script = os.path.join(self.source_folder, "test.sh")
        result_file = os.path.join(self.build_folder, "lm_test_result.json")
        if os.path.exists(result_file):
            os.remove(result_file)

        # Run the smoke test through bash with the conanrun env (provides
        # glib's LD_LIBRARY_PATH). Output passes through to the conan log.
        self.run(f'"{bash}" "{script}" "{exe}" "{result_file}"', env="conanrun")

        if not os.path.isfile(result_file):
            raise ConanException(
                f"test_loudmouth did not write its counts file: {result_file}"
            )
        counts = json.loads(load(self, result_file))
        passed = int(counts["passed"])
        failed = int(counts["failed"])
        discovered = passed + failed

        result = {
            "executed": True,
            "passed": failed == 0,
            "command": "test_loudmouth",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False))
        if failed != 0:
            raise ConanException(
                f"test_package assertions failed: {passed}/{discovered}"
            )
