#!/usr/bin/env python3
"""Consumer and HarmonyOS-specific tests for KDSingleApplication."""

import os
import platform
import socket

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KDSingleApplicationTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        qt_cmake = os.path.join(
            self.dependencies["qtbase"].package_folder, "lib", "cmake"
        )
        package_cmake = os.path.join(
            self.dependencies["kdsingleapplication"].package_folder,
            "lib",
            "cmake",
            "KDSingleApplication-qt6",
        )
        tc.cache_variables["QT_DIR"] = os.path.join(qt_cmake, "Qt6")
        tc.cache_variables["Qt6_DIR"] = os.path.join(qt_cmake, "Qt6")
        tc.cache_variables["Qt6Core_DIR"] = os.path.join(qt_cmake, "Qt6Core")
        tc.cache_variables["Qt6Network_DIR"] = os.path.join(
            qt_cmake, "Qt6Network"
        )
        tc.cache_variables["KDSingleApplication-qt6_DIR"] = package_cmake
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        if not can_run(self):
            return
        if str(self.settings.os) == "OHOS" and platform.system() != "HarmonyOS":
            self.output.info(
                "Skipping execution on a non-HarmonyOS cross-build host"
            )
            return
        env = Environment()
        for dependency in self.dependencies.values():
            if dependency.package_folder:
                libdir = os.path.join(dependency.package_folder, "lib")
                if os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.define("TMPDIR", self._socket_capable_temp_dir())
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("QT_LOGGING_RULES", "qt.qpa.*=false")
        with env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure '
                "--no-tests=error -j1".format(self.build_folder)
            )

    def _socket_capable_temp_dir(self):
        for directory in (
            os.environ.get("TMPDIR"),
            os.environ.get("XDG_RUNTIME_DIR"),
            "/data/storage/el2/base/cache",
        ):
            if directory and self._supports_unix_socket(directory):
                return directory
        raise ConanInvalidConfiguration(
            "No writable temporary directory with Unix-domain socket support"
        )

    @staticmethod
    def _supports_unix_socket(directory):
        if not os.path.isdir(directory) or not os.access(directory, os.W_OK):
            return False
        path = os.path.join(directory, "kdsa-test-socket-probe")
        if len(path.encode()) >= 100:
            return False
        probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            if os.path.lexists(path):
                os.unlink(path)
            probe.bind(path)
            return True
        except OSError:
            return False
        finally:
            probe.close()
            if os.path.lexists(path):
                os.unlink(path)
