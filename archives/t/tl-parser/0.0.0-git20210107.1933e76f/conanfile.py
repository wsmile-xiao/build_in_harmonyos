#!/usr/bin/env python3
"""Conan recipe — tl-parser 0.0.0-git20210107.1933e76f (CMake application).

tl-parser is the Telegram TL (Type Language) schema compiler: it parses a TL
schema file and exports it as a serialized `.tlo` binary (TLS_SCHEMA_V2).
Upstream (https://github.com/vysheng/tl-parser at commit 1933e76f) ships a
single CMake executable with no install rule and no automated test suite; a
patch adds the install rule and the no-tests audit is done by the recipe.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class TlParserConan(ConanFile):
    name = "tl-parser"
    version = "0.0.0-git20210107.1933e76f"
    description = "TL (Type Language) schema compiler: parses a TL schema and exports a serialized .tlo file"
    license = "GPL-2.0-only"
    homepage = "https://github.com/vysheng/tl-parser"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("tl-parser is supported only on Linux/OHOS")
        if self.settings.arch != "armv8" and self.settings.os == "OHOS":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake has no OHOS platform module. The package is built natively on
        # OHOS with clang and only uses standard C + POSIX (getopt/unistd/
        # fcntl/libm), so presenting the target as Linux is the supported path
        # (same approach as abcmidi / other pure-POSIX CMake apps).
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream ships no automated test suite (see test_package/MANIFEST.yml
        # upstream_test_audit); run an audit over the real source tree so the
        # conan create log carries machine evidence that no tests exist.
        self._audit_upstream_tests()

    def _audit_upstream_tests(self):
        # CMakeLists.txt only declares a single executable target; there is no
        # enable_testing()/add_test() and the source tree has no tests/ dir.
        audit_cmd = (
            "grep -rnE 'enable_testing|add_test|check_PROGRAMS|check-local|"
            "^TESTS|check_SCRIPTS' \"%s\" 2>/dev/null || true"
            % os.path.join(self.source_folder, "CMakeLists.txt")
        )
        self.run(audit_cmd)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
