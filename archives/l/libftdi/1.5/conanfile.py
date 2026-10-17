#!/usr/bin/env python3
# libftdi 1.5 — Conan 2 recipe for HarmonyOS PC (ohos-aarch64)
#
# Upstream: https://www.intra2net.com/en/developer/libftdi/
# Build:   CMake (upstream root CMakeLists.txt)
# License: LGPL-2.1-or-later (src), GPL-2.0-or-later (ftdi_eeprom tool, not built)
#
# Key adaptation decisions (see notes.md for the full record):
#   - Only the core library target (src/) is built. ftdi_eeprom needs libconfuse
#     (not available for OHOS in this registry), examples/tests need hardware or
#     Boost unit_test_framework — all disabled via FTDI_EEPROM/EXAMPLES/TESTS.
#   - Upstream STATICLIBS option is ignored; library type follows self.options.shared.
#   - The pkg-config file is rewritten from the installed .pc because upstream
#     libftdi1.pc.in hardcodes @prefix@ and leaks build-machine paths otherwise.

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get, replace_in_file
from conan.tools.scm import Version
import os
import shutil


class LibFtdiConan(ConanFile):
    name = "libftdi"
    version = "1.5"
    license = "LGPL-2.1-or-later"
    url = "https://atomgit.com/ohos-porter/archives"
    description = "A library to talk to FTDI chips (FT232BM, FT245BM, FT2232C, FT2232H, FT4232H, FT232H, FT230X) using libusb."
    topics = ("usb", "ftdi", "serial", "hardware")
    homepage = "https://www.intra2net.com/en/developer/libftdi/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }
    implements = ["auto_shared_fpic"]
    exports_sources = "patches/*"

    def requirements(self):
        # Repo-provided libusb with HarmonyOS kernel patches (OHOS PC has no
        # /dev/bus/* USB access, but the library API and linking still work).
        self.requires("libusb/1.0.27")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.info.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "libftdi/1.5 archive targets HarmonyOS (OHOS) only; "
                f"got os={self.info.settings.os}"
            )
        if Version(self.version) != "1.5":
            raise ConanInvalidConfiguration(
                f"Only libftdi 1.5 was verified for OHOS, got {self.version}"
            )

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)],
            strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Disable every optional subproject: ftdi_eeprom (needs libconfuse,
        # unavailable for OHOS), examples and tests (need real USB hardware /
        # Boost unit_test_framework). Core library only.
        tc.variables["FTDI_EEPROM"] = False
        tc.variables["EXAMPLES"] = False
        tc.variables["TESTS"] = False
        tc.variables["BUILD_TESTS"] = False
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Boost"] = True
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Confuse"] = True
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Doxygen"] = True
        # Library type is driven by Conan, not by upstream STATICLIBS.
        # Upstream hardcodes add_library(ftdi1 SHARED ...); the patch adds a
        # DONT_BUILD_SHARED switch so STATICLIBS=ON yields a static-only
        # build (the ftdi1-static duplicate target is skipped entirely).
        tc.variables["STATICLIBS"] = not bool(self.options.shared)
        tc.variables["DONT_BUILD_SHARED"] = not bool(self.options.shared)
        # Upstream CMakeLists.txt (2020) declares cmake_minimum_required(2.x),
        # removed from CMake >= 4. Keep the build identical but accepted.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # The OHOS profile may point tools.build:compiler_executables at
        # /data/service/hnp/bin/clang, which only exists on CI workers.
        # Fall back to a resolvable clang from PATH (libxext pattern). The
        # toolchain file's plain set() would override any -D cache entry,
        # so patch the generated file itself.
        # CMake has no Platform/HarmonyOS module, so it never defines the
        # SONAME flag for this system; the resulting .so would have no
        # DT_SONAME (CI L5a gate). Set it explicitly like Linux does.
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
            tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
            tc.generate()
            self._patch_toolchain_compilers()
        else:
            tc.generate()
        deps = CMakeDeps(self)
        deps.set_property("libusb", "cmake_file_name", "USB1")
        deps.set_property("libusb", "cmake_target_name", "libusb::libusb")
        # Upstream does find_package(USB1 REQUIRED) and then consumes the
        # classic-module variables LIBUSB_INCLUDE_DIR / LIBUSB_LIBRARIES
        # (from upstream cmake/FindUSB1.cmake). Provide them from CMakeDeps.
        deps.set_property("libusb", "cmake_extra_variables", {
            "LIBUSB_INCLUDE_DIR": "${libusb_INCLUDE_DIRS}",
            "LIBUSB_LIBRARIES": "libusb::libusb",
        })
        deps.generate()

    def build(self):
        # Upstream cmake/FindUSB1.cmake looks for libusb-1.0 via pkg-config or
        # LIBUSB_INCLUDE_DIR/LIBUSB_LIBRARY; CMakeDeps generates USB1::USB1
        # with those properties so find_package(USB1) resolves to Conan's
        # libusb. No source patch needed for dependency resolution.
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING.LIB", self.source_folder, os.path.join(self.package_folder, "licenses"))
        # Replace upstream .pc (hardcoded @prefix@, leaks build paths) with a
        # relocatable package-folder-absolute version.
        pc_file = os.path.join(self.package_folder, "lib", "pkgconfig", "libftdi1.pc")
        os.makedirs(os.path.dirname(pc_file), exist_ok=True)
        prefix = self.package_folder.replace("\\", "/")
        with open(pc_file, "w") as f:
            f.write(
                f"prefix={prefix}\n"
                "libdir=${prefix}/lib\n"
                "includedir=${prefix}/include\n"
                "\n"
                "Name: libftdi1\n"
                "Description: Library to program and control the FTDI USB controller\n"
                "Version: 1.5\n"
                "Requires: libusb-1.0\n"
                "Libs: -L${libdir} -lftdi1\n"
                "Cflags: -I${includedir} -I${includedir}/libusb-1.0\n"
            )
        if self.options.shared:
            lib_dir = os.path.join(self.package_folder, "lib")
            for leftover in ("libftdi1.a", "libftdi1-static.a"):
                leftover_path = os.path.join(lib_dir, leftover)
                if os.path.isfile(leftover_path):
                    os.unlink(leftover_path)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libftdi1")
        self.cpp_info.set_property("cmake_target_name", "libftdi1::libftdi1")
        self.cpp_info.set_property("pkg_config_name", "libftdi1")
        self.cpp_info.libs = ["ftdi1"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = ["libusb::libusb"]

    # ------------------------------------------------------------------
    def _compiler_executable(self, key, fallback_name):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _patch_toolchain_compilers(self):
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        replacements = {
            "/data/service/hnp/bin/clang++": self._compiler_executable("cpp", "clang++"),
            "/data/service/hnp/bin/clang": self._compiler_executable("c", "clang"),
        }
        for old, new in replacements.items():
            replace_in_file(self, toolchain, old, new, strict=False)
