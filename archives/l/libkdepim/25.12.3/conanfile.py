#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibkdepimConan(ConanFile):
    name = "libkdepim"
    version = "25.12.3"
    description = "KDE PIM support library"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/pim/libkdepim"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("kcompletion/6.18.0")
        self.requires("ki18n/6.18.0")
        self.requires("kwidgetsaddons/6.18.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        urls = source.get("urls")
        if urls is None:
            urls = [source["url"]]
        failures = []
        for url in urls:
            try:
                get(self, url=url, sha256=source["sha256"], strip_root=True)
                return
            except Exception as error:
                failures.append("{}: {}".format(url, error))
                self.output.warning("Source download failed; trying next URL: {}".format(url))
        raise RuntimeError("All source download URLs failed: {}".format("; ".join(failures)))

    def generate(self):
        VirtualBuildEnv(self).generate()
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"

        # ECMQueryQt cannot obtain Qt6::qtpaths through the reduced Qt package
        # config. Point it at the packaged qtpaths6 executable explicitly.
        qtbase = self.dependencies.get("qtbase-sql-dbus")
        if qtbase and qtbase.package_folder:
            tc.variables["QUERY_EXECUTABLE"] = os.path.join(
                qtbase.package_folder, "bin", "qtpaths6"
            )
            tc.variables["_cli_option"] = "--query"

        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        self._write_cmake_paths()
        tc.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        tc.generate()

    def _write_cmake_paths(self):
        prefixes = []
        modules = []
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                prefixes.extend((
                    os.path.join(dep.package_folder, "lib", "cmake"),
                    dep.package_folder,
                ))
        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            prefixes.append(os.path.join(ecm_share, "cmake"))
            modules.extend(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )
        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            'list(PREPEND CMAKE_PREFIX_PATH "{}")'.format(";".join(prefixes)),
            'list(PREPEND CMAKE_MODULE_PATH "{}")'.format(";".join(modules)),
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        with open(
            os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake"), "w"
        ) as paths_file:
            paths_file.write("\n".join(lines) + "\n")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KPim6Libkdepim"]
        self.cpp_info.includedirs = ["include"]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
