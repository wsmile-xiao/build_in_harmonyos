#!/usr/bin/env python3
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class GravatarConan(ConanFile):
    name = "gravatar"
    version = "25.12.3"
    description = "KDE PIM Gravatar Support Library"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/pim/libgravatar"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("kcoreaddons/6.18.0")
        self.requires("ki18n/6.18.0")
        self.requires("kconfig/6.18.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kwidgetsaddons/6.18.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"

        qtbase = self.dependencies.get("qtbase")
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
        for dependency in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dependency and dependency.package_folder:
                prefixes.extend((
                    os.path.join(dependency.package_folder, "lib", "cmake"),
                    dependency.package_folder,
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

    def _stage_runtime_libraries(self):
        # Several framework packages use ../../bin in their runtime RPATH.
        # CTest runs from the CMake build folder, so mirror dynamic libraries
        # at that resolved location before running the upstream suite.
        runtime_bins = (
            os.path.abspath(os.path.join(self.build_folder, "..", "..", "bin")),
            os.path.abspath(os.path.join(self.build_folder, "autotests", "..", "..", "bin")),
        )
        for runtime_bin in runtime_bins:
            os.makedirs(runtime_bin, exist_ok=True)
        for dependency in self.dependencies.values():
            if not dependency or not dependency.package_folder:
                continue
            lib_dir = os.path.join(dependency.package_folder, "lib")
            if not os.path.isdir(lib_dir):
                continue
            for filename in os.listdir(lib_dir):
                if ".so" not in filename:
                    continue
                source = os.path.join(lib_dir, filename)
                if not os.path.isfile(source):
                    continue
                for runtime_bin in runtime_bins:
                    target = os.path.join(runtime_bin, filename)
                    if not os.path.exists(target):
                        shutil.copy2(source, target)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        build_env = Environment()
        for dependency in self.dependencies.values():
            if dependency and dependency.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dependency.package_folder, "lib")
                )
        self._stage_runtime_libraries()
        build_env.define("QT_QPA_PLATFORM", "offscreen")
        with build_env.vars(self).apply():
            cmake.build()
            self.run("ctest --output-on-failure", cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KPim6Gravatar"]
        self.cpp_info.includedirs = ["include"]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
