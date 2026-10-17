#!/usr/bin/env python3
"""Conan package recipe for KDE Frameworks 5 KDocTools on HarmonyOS."""

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KDocTools5Conan(ConanFile):
    name = "kdoctools5"
    version = "5.116.0"
    description = "KDE Frameworks 5 DocBook documentation processing tools"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kdoctools"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2")
        # Keep the full cache/archive implementation enabled in meinproc5.
        # Use the plain name/version recipe published in the ohpcd registry.
        self.requires("karchive5/5.116.0")
        # Keep Qt5 and KArchive on the PIC rebuild used by the reviewed
        # KArchive binary. Otherwise Qt's transitive zlib/1.3.1 requirement
        # wins in a consumer graph and Conan rebuilds KArchive against the
        # non-PIC archive, which fails when linking its shared library.
        self.requires("zlib/1.3.1.1", force=True)
        self.requires("libxml2/2.15.3")
        self.requires("libxslt/1.1.45.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    @staticmethod
    def _cmake_dir(package_folder, *candidates):
        for relative in candidates:
            path = os.path.join(package_folder, relative)
            if os.path.isdir(path):
                return path
        return os.path.join(package_folder, candidates[0])

    def generate(self):
        deps = CMakeDeps(self)
        # Qt's native Qt5Core config is required by upstream's NO_MODULE lookup.
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["QT_MAJOR_VERSION"] = "5"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["MEINPROC_NO_KARCHIVE"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["KDE_INSTALL_LIBDIR"] = "lib"
        tc.variables["KDE_INSTALL_LIBEXECDIR"] = "libexec"
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        ecm = self.dependencies.build["ecm"]
        ecm_root = os.path.join(ecm.package_folder, "share", "ECM")
        tc.variables["ECM_DIR"] = os.path.join(ecm_root, "cmake")
        tc.variables["ECM_MODULE_PATH"] = ";".join(
            os.path.join(ecm_root, path)
            for path in ("modules", "find-modules", "kde-modules")
        )

        qt = self.dependencies["qt5-qtbase"]
        qt_core_dir = self._cmake_dir(
            qt.package_folder,
            "lib/cmake/Qt5Core",
            "share/cmake/Qt5Core",
        )
        tc.variables["Qt5Core_DIR"] = qt_core_dir

        # The OHOS runner has no shared-mime/docbook package metadata. Use the
        # Conan package roots for CMake's FindLibXml2/FindLibXslt modules and
        # the device xmllint binary for upstream's configure-time requirement.
        xml = self.dependencies["libxml2"]
        xslt = self.dependencies["libxslt"]
        archive = self.dependencies["karchive5"]
        roots = [qt.package_folder, archive.package_folder, xml.package_folder, xslt.package_folder]
        paths = [
            'set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)',
            'set(ECM_DIR "{}")'.format(os.path.join(ecm_root, "cmake")),
            'set(ECM_MODULE_PATH "{}")'.format(tc.variables["ECM_MODULE_PATH"]),
        ]
        for root in roots:
            paths.extend(
                [
                    'list(PREPEND CMAKE_PREFIX_PATH "{}")'.format(root),
                    'list(PREPEND CMAKE_LIBRARY_PATH "{}")'.format(os.path.join(root, "lib")),
                    'list(PREPEND CMAKE_INCLUDE_PATH "{}")'.format(os.path.join(root, "include")),
                ]
            )
        paths.append(
            'list(PREPEND CMAKE_INCLUDE_PATH "{}")'.format(
                os.path.join(xml.package_folder, "include", "libxml2")
            )
        )
        paths.append(
            'set(LIBXML2_XMLLINT_EXECUTABLE "{}" CACHE FILEPATH "xmllint")'.format(
                shutil.which("xmllint") or "xmllint"
            )
        )
        include_file = os.path.join(self.generators_folder, "kdoctools5-cmake-paths.cmake")
        with open(include_file, "w", encoding="utf-8") as handle:
            handle.write("\n".join(paths) + "\n")
        tc.variables["CMAKE_PROJECT_INCLUDE"] = include_file
        tc.generate()

    def _build_env(self):
        env = Environment()
        if os.path.isdir("/system/lib64"):
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        for dependency in self.dependencies.values():
            if dependency and dependency.package_folder:
                lib_dir = os.path.join(dependency.package_folder, "lib")
                bin_dir = os.path.join(dependency.package_folder, "bin")
                if os.path.isdir(lib_dir):
                    env.prepend_path("LD_LIBRARY_PATH", lib_dir)
                if os.path.isdir(bin_dir):
                    env.prepend_path("PATH", bin_dir)
        for relative in ("bin", "lib", os.path.join("src", "lib")):
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, relative))
        return env

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
            if can_run(self):
                self.run(
                    'ctest --test-dir "{}" --output-on-failure'.format(
                        self.build_folder
                    )
                )

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
