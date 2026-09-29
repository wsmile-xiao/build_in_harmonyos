#!/usr/bin/env python3
"""Conan recipe — QWinFF 0.2.1-git20201215 for HarmonyOS PC (aarch64-linux-ohos).

QWinFF is a Qt5 GUI front-end for ffmpeg (media converter).

Adaptation (OHOS):
- Qt5 Widgets + Network only. The upstream CMake build requires the
  LinguistTools (qttools lrelease/lupdate) which is not published for OHOS,
  so the translations subproject is dropped (patch 0001).
- The bundled qmpwidget library compiles its OpenGL video widget only when
  QT_OPENGL_LIB is defined (upstream #ifdef guard); we do not link
  Qt5::OpenGL, so the GL path is compiled out automatically (no patch needed).
- DBus power management is avoided by upstream already using
  powermanagement-dummy.cpp in the CMake build.
- Patch 0001 additionally defines DATA_PATH so the installed binary locates
  share/qwinff/{constants,presets}.xml inside the package folder.
- Upstream unit tests (src/tests: testversioncompare, testupdateinfoparser,
  QtTest-based, headless with QT_QPA_PLATFORM=offscreen) are rebuilt and run
  in test_package.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class QwinffConan(ConanFile):
    name = "qwinff"
    version = "0.2.1-git20201215"
    description = "QWinFF - Qt5 GUI front-end for ffmpeg"
    license = "GPL-3.0-or-later"
    homepage = "https://qwinff.github.io"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {}
    default_options = {}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # codeload URL has no file extension, so pass an explicit filename to
        # prevent get() from mis-detecting the tarball as a zip file.
        get(self, self.conan_data["sources"]["url"],
            sha256=self.conan_data["sources"]["sha256"],
            filename=f"{self.name}-{self.version}.tar.gz",
            strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # qt5-qtbase only exports per-module cmake configs (Qt5Core/...); the
        # upstream CMakeLists uses find_package(Qt5 COMPONENTS ...), so an
        # aggregate Qt5Config is required (same approach as archives/b/ball).
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

        tc = CMakeToolchain(self)
        # Upstream CMakeLists requires CMake>=3.1; pass via cache variable
        # (plain set() inside the toolchain does not take effect).
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # E092: CMake has no HarmonyOS platform module; OHOS is Linux-kernel
        # based so use the Linux platform module (compiler still comes from
        # conan_toolchain pointing at the OHOS clang).
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # AUTOMOC/AUTORCC/AUTOUIC are enabled by upstream CMakeLists, but
        # CMakeDeps does not export Qt5::*Tool executables - point them at
        # the qt5-qtbase package explicitly.
        qt5_pkg = self.dependencies["qt5-qtbase"].package_folder
        qt5_bin = os.path.join(qt5_pkg, "bin")
        tc.variables["CMAKE_AUTOMOC"] = "ON"
        tc.variables["CMAKE_AUTORCC"] = "ON"
        tc.variables["CMAKE_AUTOUIC"] = "ON"
        tc.variables["CMAKE_AUTOMOC_EXECUTABLE"] = os.path.join(qt5_bin, "moc")
        tc.variables["CMAKE_AUTORCC_EXECUTABLE"] = os.path.join(qt5_bin, "rcc")
        tc.variables["CMAKE_AUTOUIC_EXECUTABLE"] = os.path.join(qt5_bin, "uic")
        # E298: keep link-time rpath so the binary finds its conan dependency
        # libs (libQt5*.so) from the package location.
        tc.variables["CMAKE_INSTALL_RPATH_USE_LINK_PATH"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
