#!/usr/bin/env python3
"""test_package for kirigami-gallery 26.04.0 on HarmonyOS PC.

Consumer-side validation (R34): builds test_runner.c, which EXECUTES the
packaged kirigami2gallery binary and verifies that the full QML stack
(qtdeclarative + org.kde.kirigami + org.kde.kitemmodels) actually loads.

Failure semantics of the app under test (src/main.cpp):
  - engine.rootObjects().isEmpty() -> main() returns -1 (QML load failure)
  - QML loads successfully -> app.exec() blocks in the event loop
So: still running after 8 s == PASS (terminated with SIGTERM by the runner),
exit code 255 within 8 s == FAIL (QML engine failed to load).

Upstream has no test suite (R51 evidence in MANIFEST.yml); this consumer
test is the supplemented coverage.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KirigamiGalleryTestConan(ConanFile):
    name = "kirigami-gallery-test"
    version = "26.04.0"
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _runtime_env(self):
        """Environment for executing the packaged GUI binary headlessly."""
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins"))
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml"))
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "lib", "qml"))
        env.define("QT_QPA_PLATFORM", "offscreen")
        # main.cpp only defaults to the org.kde.desktop QQC2 style when this
        # env var is empty; force the built-in "Basic" style so no
        # qqc2-desktop-style dependency is pulled in.
        # NOTE: value must be "Basic" (capital B, matching the
        # QtQuick/Controls/Basic module directory) — on this Qt 6.11 OHOS
        # build the env-var style lookup is case-sensitive and "basic"
        # fails with "module basic is not installed" (verified via the
        # standalone qml runner: lowercase fails, capitalized loads).
        env.define("QT_QUICK_CONTROLS_STYLE", "Basic")
        # Writable XDG dirs for the QML engine cache (HMDFS-safe, E002/E046).
        home = os.path.join(self.build_folder, "test-home")
        runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(home, exist_ok=True)
        os.makedirs(runtime, exist_ok=True)
        env.define("HOME", home)
        env.define("XDG_RUNTIME_DIR", runtime)
        env.define("XDG_CACHE_HOME", os.path.join(home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(home, ".config"))
        return env

    def test(self):
        app_dep = self.dependencies["kirigami-gallery"]
        app_bin = os.path.join(app_dep.package_folder, "bin", "kirigami2gallery")
        if not os.path.isfile(app_bin):
            raise Exception(f"kirigami2gallery binary missing from package: {app_bin}")

        runner = os.path.join(self.cpp.build.bindirs[0], "test_runner")
        if not os.path.isfile(runner):
            raise Exception(f"test_runner binary not built: {runner}")

        env = self._runtime_env()
        env_vars = env.vars(self, scope="run")
        with env_vars.apply():
            self.run(f'"{runner}" "{app_bin}"')
