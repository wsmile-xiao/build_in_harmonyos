#!/usr/bin/env python3
"""Conan recipe for plusaes 1.0.0 — header-only C++ AES cipher library.

plusaes (https://github.com/kkAyataka/plusaes) is a header-only C++11 library
covering the ECB / CBC / CTR / GCM block cipher modes.  The release tarball
ships ``include/plusaes/plusaes.hpp`` (1301 lines) plus an upstream GoogleTest
suite under ``unit_test/`` that bundles its own gtest copy
(``unit_test/lib/include/gtest`` + ``unit_test/src/gtest/gtest-all.cc``).

OHOS adaptation (evidence in notes.md):

* The package is delivered header-only exactly as upstream defines it, so
  ``package()`` installs the public header tree and the Boost license file and
  produces no ``lib/`` or ``bin/`` at all (no commands.json, R38/L0k).
* Upstream's Linux build (``lin/``) is an autotools skeleton that only works
  after ``bootstrap`` (autoheader/aclocal/automake -a/autoconf).  The CI worker
  PATH carries no automake (device-facts §一.4), so the recipe does not use it:
  the six upstream test translation units are compiled directly with the Conan
  resolved C++ compiler, exactly as ``lin/unit_test/Makefile.am`` lists them,
  and the resulting ``unit_test`` binary is run at the end of ``build()``.
* No source file is patched — ``patches_applied: []``.

Tests: the upstream GoogleTest suite registers 111 cases in 8 suites
(parameterized instantiations included).  ``--gtest_list_tests`` and the full
run are both executed inside ``build()`` so ``conan create`` carries the
authoritative readings; counts are parsed from the real output, never
hardcoded.
"""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class PlusaesConan(ConanFile):
    name = "plusaes"
    version = "1.0.0"
    description = "Header-only C++ AES cipher library (ECB/CBC/CTR/GCM)"
    license = "BSL-1.0"
    homepage = "https://github.com/kkAyataka/plusaes"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("aes", "encryption", "header-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        # No patches today (patches_applied: []), but the hook is part of the
        # standard recipe shape and keeps conandata patch entries exportable.
        export_conandata_patches(self)

    def package_id(self):
        self.info.clear()

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "plusaes is developed and verified on Linux and OHOS, not %s"
                % self.settings.os
            )
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, "11")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def build(self):
        # 0 patches: no-op, kept as the standard hook (see export_sources).
        apply_conandata_patches(self)

        # R33: take the toolchain from the Conan conf, never from shell
        # environment variables (release workers export none).
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = str(executables.get("cpp") or "clang++").split()[0].strip("\"'")

        src = self.source_folder
        test_src = os.path.join(src, "unit_test", "src")
        include_dirs = [
            os.path.join(src, "include"),
            os.path.join(src, "unit_test", "lib", "include"),
            os.path.join(test_src, "gtest"),
        ]
        # Exactly the TUs of lin/unit_test/Makefile.am:unit_test_SOURCES.
        sources = [
            os.path.join(test_src, "gtest", "gtest-all.cc"),
            os.path.join(test_src, "main.cpp"),
            os.path.join(test_src, "test-ctr.cpp"),
            os.path.join(test_src, "test-gcm.cpp"),
            os.path.join(test_src, "test-inc.cpp"),
            os.path.join(test_src, "test-plusaes.cpp"),
        ]
        binary = os.path.join(self.build_folder, "plusaes_unit_test")

        include_flags = " ".join(
            "-I%s" % shlex.quote(path) for path in include_dirs
        )
        source_args = " ".join(shlex.quote(path) for path in sources)
        self.run(
            "%s -std=c++11 -O2 -Wall %s %s -lpthread -o %s"
            % (shlex.quote(cxx), include_flags, source_args, shlex.quote(binary)),
            env="conanbuild",
        )

        # Layer 1 — upstream official GoogleTest suite (docs/TEST_QUALITY_SPEC
        # §3.1).  The listing gives the registered case count (N), the run
        # gives PASS/FAIL; both go verbatim into the conan create log.
        self.run("%s --gtest_list_tests" % shlex.quote(binary), env="conanbuild")
        self.run(shlex.quote(binary), env="conanbuild")

    def package(self):
        copy(
            self,
            "*.hpp",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
            keep_path=True,
        )
        copy(
            self,
            "LICENSE_1_0.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "plusaes")
        self.cpp_info.set_property("cmake_target_name", "plusaes::plusaes")
        self.cpp_info.set_property("pkg_config_name", "plusaes")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
