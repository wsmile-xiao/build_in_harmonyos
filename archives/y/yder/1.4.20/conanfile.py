#!/usr/bin/env python3
"""Conan recipe for yder 1.4.20 — logging library (babelouest suite).

yder logs to console/syslog/file/callback; headers-only dependency on
orcania for its base strings.  CMake build; WITH_JOURNALD is pinned OFF
(the platform has no systemd — upstream auto-detects and would disable
it anyway, pinning keeps the build deterministic).

Platform notes:
- Upstream test suite (test/yder_test.c) links against the `check`
  framework, which does not exist on this platform — upstream tests are
  declared non-executable (see MANIFEST.yml); verification is carried by
  the consumer test_package.
- Nothing is stripped on install (llvm-strip output is refused by the
  platform's exec policy — yices 2.7.0 evidence + knowledge draft).
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get


class YderConan(ConanFile):
    name = "yder"
    version = "1.4.20"
    description = ("yder - logging library with console, syslog, file and "
                   "callback backends")
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/babelouest/yder"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        pass

    def requirements(self):
        # yder 1.4.20 CMakeLists: ORCANIA_VERSION_REQUIRED "2.3.3"
        self.requires("orcania/2.3.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # url may arrive as a candidate list (the CI pre-download step
        # rewrites conandata's url into [mirror, official]) — conan's
        # get() handles both shapes natively.
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # platform has no systemd; pin the upstream auto-detect OFF.
        # upstream uses its own BUILD_SHARED/BUILD_STATIC switches
        tc.variables["WITH_JOURNALD"] = False
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BUILD_SHARED"] = bool(self.options.shared)
        tc.variables["BUILD_STATIC"] = not bool(self.options.shared)
        # upstream CMakeLists asserts ${ORCANIA_VERSION_STRING} >= 2.3.3,
        # but that variable is set by orcania's own install-tree config,
        # which CMakeDeps' generated config does not define — provide it
        # from the conan dependency version instead.
        tc.variables["ORCANIA_VERSION_STRING"] = str(
            self.dependencies["orcania"].ref.version)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # PUBLIC_HEADER covers the generated yder-cfg.h; also copy the
        # static-archive layout variant if present
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"),
             keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Yder")
        self.cpp_info.set_property("cmake_target_name", "Yder::Yder")
        self.cpp_info.libs = ["yder"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
