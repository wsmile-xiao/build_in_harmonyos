#!/usr/bin/env python3
"""Conan recipe for fingerterm 1.4.16 on HarmonyOS PC (arm64).

fingerterm is a Qt Quick terminal emulator originally written for the
Sailfish OS (qmake, Qt5). This recipe builds it against the Qt 6.11 stack
published in the ohpcd registry (qtbase/6.11.1 + qtdeclarative/6.11.1):

- The upstream qmake project (fingerterm.pro) is replaced by a top-level
  CMakeLists.txt (patch 0001) building the same sources.
- Qt5-only APIs are ported in the same patch: QTextCodec ->
  QStringDecoder/QStringEncoder, qplatformdefs.h dropped,
  QScreen::setOrientationUpdateMask (Sailfish extension) guarded off,
  QtQuick.XmlListModel -> QtQml.XmlListModel (Qt6 module name),
  QString::KeepEmptyParts -> Qt::KeepEmptyParts (enum namespace move).
- forkpty()/openpty() come from the OHOS musl sysroot <pty.h> (verified
  on device; symbols live in libc, the sysroot also ships a stub
  libutil.a consumed by the upstream "-lutil" link line).
- Runtime data (QML UI, keyboard layouts, icons) installs under
  share/fingerterm; the DEPLOYMENT_PATH macro is wired to that layout.
"""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class FingertermConan(ConanFile):
    name = "fingerterm"
    version = "1.4.16"
    description = "Qt Quick terminal emulator (Sailfish OS fingerterm) for HarmonyOS PC"
    license = "GPL-2.0-only"
    homepage = "https://github.com/sailfishos/fingerterm"
    url = "https://github.com/sailfishos/fingerterm"
    topics = ("terminal", "terminal-emulator", "qt", "qtquick", "qml")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 Core/Gui come from qtbase; Qml/Quick (and the QML runtime
        # modules incl. QtQml.XmlListModel) come from qtdeclarative.
        # The app uses no SQL/DBus widgets, plain qtbase suffices.
        # qtshadertools is an explicit require because the generated
        # CMake environment needs its prefix on the Qt package search
        # path (Qt6Quick's config files reference it).
        self.requires("qtbase/6.11.1", transitive_headers=True, transitive_libs=True)
        self.requires("qtdeclarative/6.11.1", transitive_headers=True, transitive_libs=True)
        self.requires("qtshadertools/6.11.1", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "fingerterm/1.4.16 in this recipe is a HarmonyOS PC adaptation"
            )

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        qtbase = self.dependencies["qtbase"].package_folder
        qtdec = self.dependencies["qtdeclarative"].package_folder
        shadertools = self.dependencies["qtshadertools"].package_folder

        tc = CMakeToolchain(self)
        tc.variables["CMAKE_PREFIX_PATH"] = ";".join(
            os.path.join(p, "lib", "cmake") for p in (qtbase, qtdec, shadertools) if p
        )
        tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(
            p for p in (qtbase, qtdec, shadertools) if p
        )
        # The CMake project hard-codes share/fingerterm as DEPLOYMENT_PATH
        # relative to CMAKE_INSTALL_PREFIX (the conan package folder).
        tc.variables["FINGERTERM_DEPLOYMENT_PATH"] = os.path.join(
            self.package_folder, "share", "fingerterm"
        )
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        # CMake has no Platform/HarmonyOS.cmake rules; presenting the host
        # as Linux selects the standard shared/exe platform rules while the
        # OHOS clang driver still targets aarch64-linux-ohos (same approach
        # as the qtdeclarative recipe).
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["CMAKE_CROSSCOMPILING"] = "FALSE"
        tc.generate()

        # Build-time helpers (moc from qtbase, qml tools from
        # qtdeclarative) are OHOS binaries run on the OHOS host worker;
        # they need the Qt libs and the SDK libc++_shared.so on
        # LD_LIBRARY_PATH to resolve their own DT_NEEDED entries.
        env = Environment()
        for sdk_lib in self._ohos_sdk_lib_dirs():
            env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
        for pkg in (qtbase, qtdec, shadertools):
            if pkg:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(pkg, "lib"))
        env.vars(self).save_script("conanbuild_qt_libs")

    @staticmethod
    def _ohos_sdk_lib_dirs():
        """Locate OHOS SDK llvm lib dirs providing libc++_shared.so.

        The qtbase/qtdeclarative host tools (moc etc.) are OHOS binaries
        whose DT_NEEDED includes libc++_shared.so; only the SDK ships it.
        Falls back to globbing all installed SDK versions (same approach
        as the attica recipe).
        """
        candidates = [
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos",
        ]
        candidates.extend(
            glob.glob(
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/aarch64-linux-ohos"
            )
        )
        dirs = []
        for cand in candidates:
            if os.path.isdir(cand) and cand not in dirs:
                dirs.append(cand)
        return dirs

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # License
        copy(
            self,
            "COPYING",
            dst=os.path.join(self.package_folder, "licenses"),
            src=self.source_folder,
        )
        # Drop the desktop entry — the OHOS desktop does not consume
        # XDG .desktop files and JC-style archives keep the package lean.
        desktop = os.path.join(self.package_folder, "share", "applications")
        if os.path.isdir(desktop):
            shutil.rmtree(desktop, ignore_errors=True)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # Runtime hints for consumers launching fingerterm from a conan
        # environment: the QML import path must cover the Qt6 QML modules
        # shipped inside the qtdeclarative package.
        qtdec = self.dependencies.get("qtdeclarative")
        if qtdec and qtdec.package_folder:
            self.runenv_info.prepend_path(
                "QML2_IMPORT_PATH", os.path.join(qtdec.package_folder, "qml")
            )
