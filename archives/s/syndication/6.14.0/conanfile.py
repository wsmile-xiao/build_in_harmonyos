#!/usr/bin/env python3
"""Conan recipe for syndication 6.14.0 on HarmonyOS PC.

syndication is a KDE Frameworks 6 library for parsing RSS/Atom/RDF feed
formats (libKF6Syndication.so).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - ECM injected via CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH through a private
    build_folder paths.cmake (R49): qtbase uses cmake_find_mode=none, which
    prevents CMakeDeps from adding its lib/cmake builddir to
    CMAKE_PREFIX_PATH, so the paths are injected manually
  - QT_ADDITIONAL_PACKAGES_PREFIX_PATH (semicolon-separated) so Qt6 module
    configs (Qt6Xml/Qt6Test/Qt6Network) are found in the qtbase package
  - BUILD_TESTING=ON + ctest run in build() so upstream autotests
    (testpersonimpl / syndicationtest / loaderutiltest) are executed as part
    of the package verification
  - BUILD_QCH=OFF (Qt Assistant docs need extra tooling, not needed here)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class SyndicationConan(ConanFile):
    name = "syndication"
    version = "6.14.0"
    description = "KDE Frameworks 6 - RSS/Atom feed parsing library"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/syndication"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("kcodecs/6.14.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.20.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"

        # Make Qt6 module configs findable in the qtbase/kcodecs package
        # prefixes (semicolon-separated, Qt6 convention).
        qt_prefixes = [
            dep.package_folder
            for dep in list(self.dependencies.values())
            + list(self.dependencies.build.values())
            if dep and dep.package_folder
        ]
        if qt_prefixes:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_prefixes)

        # Private build_folder paths.cmake (R49): inject dependency cmake dirs
        # into CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH. qtbase is consumed with
        # cmake_find_mode=none, so CMakeDeps does not generate these paths.
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        deps = list(self.dependencies.values()) + list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")')
                lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")')
        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            for rel in ("modules", "find-modules", "kde-modules"):
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{os.path.join(ecm.package_folder, "share", "ECM", rel)}")')
        lines.append(f'list(PREPEND CMAKE_MODULE_PATH "${{CMAKE_CURRENT_LIST_DIR}}")')
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "${{CMAKE_CURRENT_LIST_DIR}}")')
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")
        tc.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = paths_file
        tc.generate()

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms (e.g. BSD) are not affected.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # Upstream autotests (CTest): testpersonimpl / syndicationtest /
        # loaderutiltest. Run headless with the dependency libs on the path.
        env = Environment()
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml"))
        env.define("QT_QPA_PLATFORM", "offscreen")
        with env.vars(self).apply():
            self.run('ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(self.build_folder), env="")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KF6SyndicationConfig.cmake with proper
        # dependency tracking (find_dependency on KF6Codecs/Qt6Xml). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6Syndication"]
