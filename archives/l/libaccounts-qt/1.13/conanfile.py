#!/usr/bin/env python3
"""Conan recipe for libaccounts-qt 1.13 on HarmonyOS PC.

libaccounts-qt is a Qt5 library for managing online account configurations
and authentication tokens. It wraps libaccounts-glib with a Qt-style API.

Upstream uses qmake, but the conan qt5-qtbase package does not ship qmake.
This recipe provides a custom CMakeLists.txt that replicates the qmake build:
  - moc processing for Q_OBJECT headers (account.h, account-service.h, manager.h)
  - compilation of all source files
  - linking against Qt5Core, Qt5Xml, and libaccounts-glib
  - installation of headers and library

Build system: qmake (upstream) -> CMake (custom)
License: LGPL-2.1-or-later
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LibAccountsQtConan(ConanFile):
    name = "libaccounts-qt"
    version = "1.13"
    description = "Qt library for managing online account configurations and authentication"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.com/accounts-sso/libaccounts-qt"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "CMakeLists.txt"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2")
        self.requires("libaccounts-glib/1.27")
        # glib2 needed for gio-unix-2.0 headers (gdesktopappinfo.h)
        self.requires("glib2/2.88.0", transitive_headers=True)

    def validate(self):
        # R32: support Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libaccounts-qt only supports Linux and OHOS, got {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        source_data = self.conan_data["sources"]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get(self, url=url, sha256=source_data["sha256"], strip_root=True)
                return
            except Exception as error:
                self.output.warning(
                    f"Failed to download libaccounts-qt source from {url}: {error}"
                )
        raise ConanInvalidConfiguration(
            "Unable to download libaccounts-qt source from all mirrors"
        )

    def generate(self):
        deps = CMakeDeps(self)
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"

        # Provide moc path for AUTOMOC
        qt5 = self.dependencies["qt5-qtbase"]
        moc_path = os.path.join(qt5.package_folder, "bin", "moc")
        if not os.path.isfile(moc_path):
            raise ConanInvalidConfiguration(
                "qt5-qtbase/5.15.2.2 does not provide the required bin/moc tool"
            )
        tc.variables["CMAKE_AUTOMOC_EXECUTABLE"] = moc_path

        # glib2's gio-unix-2.0 headers (gdesktopappinfo.h etc.) live in a
        # separate include dir not exposed via CMakeDeps; pass it to CMake.
        glib2 = self.dependencies["glib2"]
        gio_unix_inc = os.path.join(glib2.package_folder, "include", "gio-unix-2.0")
        if os.path.isdir(gio_unix_inc):
            tc.variables["GLIB_GIO_UNIX_INCLUDE_DIR"] = gio_unix_inc

        # OHOS platform name mapping
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
            # SONAME emission for shared libraries
            tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        tc.generate()

        # CI workers: OHOS SDK's lld dynamically links libxml2.so;
        # add dep lib dirs to LD_LIBRARY_PATH so lld can find them.
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    self.buildenv_info.prepend_path("LD_LIBRARY_PATH", lib_dir)

    def build(self):
        apply_conandata_patches(self)
        # OHOS SDK's lld dynamically links libxml2.so.16 from its own lib dir;
        # add it to LD_LIBRARY_PATH so CMake TryCompile can link successfully.
        import glob
        for sdk_lib in glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"):
            if os.path.isdir(sdk_lib):
                cur = os.environ.get("LD_LIBRARY_PATH", "")
                os.environ["LD_LIBRARY_PATH"] = sdk_lib + (":" + cur if cur else "")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # Install LICENSE
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        # OHOS: sign shared libraries
        if self.settings.os == "OHOS" and self.options.shared:
            self._sign_shared_libs()

    def _sign_shared_libs(self):
        """OHOS platform: code-sign .so files"""
        import glob
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            if os.path.islink(so):
                continue
            self.run(f'{objcopy} --remove-section .codesign "{so}" 2>/dev/null || true')
            self.run(f'{signer} sign -inFile "{so}" -outFile "{so}" -selfSign 1')

    def package_info(self):
        self.cpp_info.libs = ["accounts-qt5"]
        self.cpp_info.includedirs = ["include/accounts-qt"]
        self.cpp_info.set_property("cmake_file_name", "AccountsQt5")
        self.cpp_info.set_property("cmake_target_name", "AccountsQt5::AccountsQt5")
        self.cpp_info.set_property("pkg_config_name", "accounts-qt5")
        self.cpp_info.requires = [
            "qt5-qtbase::Qt5Core",
            "qt5-qtbase::Qt5Xml",
            "libaccounts-glib::libaccounts-glib",
            "glib2::glib2",
        ]
