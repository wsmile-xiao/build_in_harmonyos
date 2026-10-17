#!/usr/bin/env python3
"""Conan recipe for libapogee3 3.2+20221221183454."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)


class LibApogee3Conan(ConanFile):
    name = "libapogee3"
    version = "3.2+20221221183454"
    description = "Apogee Instruments Gen2/Gen3 CCD camera driver library (INDI ecosystem)"
    # Debian's debian/copyright for this exact source declares the whole tree
    # MPL-2.0 (Apogee Instruments, 2003-2012), matching the 133 source-file
    # headers; the bundled LICENSE file's GPL-2.0 text is a mislabeled leftover.
    license = "MPL-2.0"
    homepage = "https://www.apogeeinstruments.com/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libapogee3 supports Linux and OHOS targets, got {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # GenOne USB transport (linux/GenOneLinuxUSB.cpp, linux/linuxHelpers.cpp)
        self.requires("libusb/1.0.27")
        # Ethernet camera transport (Alta/Aspen *EthernetIo.cpp via libCurlWrap)
        self.requires("curl/8.15.0")
        # INDI is a compile-time-macro-only dependency for this library: the
        # sources include "indimacros.h" for two macros (__BASE_FILE__,
        # INDI_UNUSED) and target_link_libraries lists only ${USB1_LIBRARIES}
        # and ${CURL} — no INDI symbols are ever linked. A real INDI install
        # would drag in Qt5/boost (not adapted here), so generate() emits a
        # stub indimacros.h next to the INDI_INCLUDE_DIR cache variable that
        # CMakeLists.txt feeds to include_directories().

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _ohos_cmake_rules(self):
        # Same relocatable-SONAME / RPATH rules as the curl/8.15.0 recipe:
        # HMDFS denies the SOVERSION symlink layout, so the installed shared
        # library is unversioned with a relocatable SONAME.
        rules = os.path.join(self.generators_folder, "ohos-cmake-rules.cmake")
        save(
            self,
            rules,
            "\n".join(
                (
                    'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                    'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
                    'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
                    "set(CMAKE_SHARED_LIBRARY_RPATH_LINK_C_FLAG "
                    '"-Wl,-rpath-link,")',
                    'set(CMAKE_SHARED_LIBRARY_RPATH_ORIGIN_TOKEN "$ORIGIN")',
                )
            )
            + "\n",
        )
        return rules

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)

        if self.settings.os == "OHOS":
            rules = self._ohos_cmake_rules()
            tc.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules
            tc.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_CXX"] = rules

        # Upstream never links INDI (see requirements()); CMakeLists.txt only
        # needs the include directory that its include_directories() call
        # consumes. Point it at the stub macro header instead of a real
        # INDI install (which would drag in Qt5/boost, not adapted here).
        stub_inc = os.path.join(self.generators_folder, "indi_stub_inc")
        tc.cache_variables["INDI_INCLUDE_DIR"] = stub_inc

        libusb_folder = self.dependencies["libusb"].package_folder
        # The bundled FindUSB1.cmake resolves via find_path/find_library;
        # seed the cache so it pins the Conan package artifacts directly.
        # Upstream omits include_directories(${USB1_INCLUDE_DIRS}); 0002 adds
        # it. The source includes <libusb-1.0/libusb.h>, so the search root
        # must be the package include dir (the one that CONTAINS libusb-1.0/).
        tc.cache_variables["USB1_INCLUDE_DIR"] = os.path.join(
            libusb_folder, "include"
        )
        tc.cache_variables["USB1_LIBRARY"] = os.path.join(
            libusb_folder, "lib", "libusb-1.0.so"
        )

        shared = bool(self.options.shared)
        tc.cache_variables["BUILD_SHARED_LIBS"] = shared
        if shared and self.settings.os == "OHOS":
            # OHOS re-signs each shared object with a content-hash
            # (.codesign section, written by lld at link time) that the
            # kernel enforces on executable mmap. CMake's install step
            # rewrites the build-tree RUNPATH (the absolute conan cache
            # paths that CMakeDeps pins for libusb/curl) to empty, which
            # modifies the file *after* the signature was written and
            # invalidates it: dlopen then fails with a misleading
            # "Permission denied". Skipping both RPATHs keeps the install
            # byte-identical to the build tree so the signature stays
            # valid; consumers resolve the dependency via LD_LIBRARY_PATH
            # (conanrunenv), like every other conan library on OHOS.
            tc.cache_variables["CMAKE_SKIP_BUILD_RPATH"] = True
            tc.cache_variables["CMAKE_SKIP_INSTALL_RPATH"] = True
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = shared or bool(
            self.options.get_safe("fPIC", True)
        )
        tc.generate()

        # Materialize the INDI macro stub where INDI_INCLUDE_DIR points.
        save(
            self,
            os.path.join(stub_inc, "indimacros.h"),
            "\n".join(
                (
                    "/* OHOS build stub: INDI macro-only dependency for libapogee3.",
                    " * Only these two macros are referenced by the sources; no INDI",
                    " * symbols are ever linked. */",
                    "#ifndef INDI_MACROS_H",
                    "#define INDI_MACROS_H",
                    "#ifndef __BASE_FILE__",
                    "#define __BASE_FILE__ __FILE__",
                    "#endif",
                    "#ifndef INDI_UNUSED",
                    "#define INDI_UNUSED(x) (void)x",
                    "#endif",
                    "#endif /* INDI_MACROS_H */",
                    "",
                )
            ),
        )

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        CMake(self).install()

    def package_info(self):
        # Upstream installs headers under include/libapogee/ while the public
        # headers use flat #include "CameraInfo.h" (and each other), so the
        # include root must be the subdirectory, not the package include/.
        self.cpp_info.includedirs = ["include/libapogee"]
        self.cpp_info.libs = ["apogee"]
        self.cpp_info.set_property("cmake_file_name", "libapogee3")
        self.cpp_info.set_property("cmake_target_name", "libapogee3::libapogee3")
        self.cpp_info.set_property("pkg_config_name", "libapogee")
