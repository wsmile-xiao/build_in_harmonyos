#!/usr/bin/env python3
"""Consumer test for qtdeclarative on HarmonyOS PC."""

import os
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QtdeclarativeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        qtbase_pkg = self.dependencies["qtbase"].package_folder
        pkg = self.dependencies["qtdeclarative"].package_folder
        # Qt6Config lives in the qtbase package; Qt6QmlConfig lives in the
        # qtdeclarative package. Qt only searches the additional prefixes
        # listed in QT_ADDITIONAL_PACKAGES_PREFIX_PATH for module configs.
        tc.cache_variables["CMAKE_PREFIX_PATH"] = qtbase_pkg
        tc.cache_variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = pkg
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self) and str(self.settings.os) == "OHOS":
            for binary in self._test_binaries():
                self._sign(binary)

    def _test_binaries(self):
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise ConanInvalidConfiguration(
                "qtdeclarative test package has no build bindir"
            )
        return [os.path.join(bindirs[0], "test_qtdeclarative")]

    def _sign(self, path):
        """Self-sign the test binary so the OHOS loader permits execution."""
        original_mode = stat.S_IMODE(os.stat(path).st_mode)
        signer = shutil.which("binary-sign-tool")
        if not signer:
            raise ConanInvalidConfiguration(
                "binary-sign-tool not found; it is required to run OHOS ELF binaries"
            )
        with tempfile.TemporaryDirectory(
            prefix=".conan-sign-", dir=os.path.dirname(path)
        ) as temp_dir:
            unsigned = os.path.join(temp_dir, "unsigned")
            signed = os.path.join(temp_dir, "signed")
            shutil.copy2(path, unsigned)
            subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    unsigned,
                    "-outFile",
                    signed,
                    "-selfSign",
                    "1",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            os.replace(signed, path)
            os.chmod(path, original_mode)

    def test(self):
        if not can_run(self):
            raise ConanInvalidConfiguration(
                "The Conan test_package must run on an OHOS device or emulator; "
                "cross-build execution cannot be silently skipped"
            )

        # QQmlEngine needs QML_IMPORT_PATH pointing at the packaged QML
        # modules (qml/QtQml, qml/QtQuick, ...) to resolve imports.
        qtbase_pkg = self.dependencies["qtbase"].package_folder
        pkg = self.dependencies["qtdeclarative"].package_folder
        qml_paths = []
        for prefix in (pkg, qtbase_pkg):
            for relative in ("qml", os.path.join("lib", "qml")):
                candidate = os.path.join(prefix, relative)
                if os.path.isdir(candidate) and candidate not in qml_paths:
                    qml_paths.append(candidate)
        if not qml_paths:
            raise ConanInvalidConfiguration(
                f"qml directory not found under {pkg} or {qtbase_pkg}"
            )
        qml_import_path = os.pathsep.join(qml_paths)
        os.environ["QML_IMPORT_PATH"] = qml_import_path
        os.environ["QML2_IMPORT_PATH"] = qml_import_path

        platforms_dir = os.path.join(qtbase_pkg, "plugins", "platforms")
        if os.path.isdir(platforms_dir):
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = platforms_dir
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

        executable = os.path.join(self.cpp.build.bindirs[0], "test_qtdeclarative")
        self.run(executable, env="conanrun", ignore_errors=False)
