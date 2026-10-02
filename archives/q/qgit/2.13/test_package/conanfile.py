#!/usr/bin/env python3
"""Conan test_package for qgit 2.13.

qgit is a Qt5 GUI application; upstream ships no test suite (no tests/
directory, no ctest registration — see notes.md).  The smoke test runs
the packaged `qgit` binary with --version and --help: both options are
handled by QCommandLineParser before any window is created, so they
work headless under QT_QPA_PLATFORM=offscreen.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class QgitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _runtime_env(self, build_folder):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
        env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(build_folder, "test-home")
        xdg_runtime = os.path.join(build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", test_home)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        return env

    def generate(self):
        self._runtime_env(self.build_folder).vars(self).save_script(
            "conanrun_qgit_test"
        )

    def test(self):
        if not can_run(self):
            return
        qgit = self.dependencies.get("qgit")
        qgit_bin = (
            os.path.join(qgit.package_folder, "bin", "qgit") if qgit else None
        )
        if not qgit_bin or not os.path.isfile(qgit_bin):
            raise ConanException("qgit binary not found in package")
        env_vars = self._runtime_env(self.build_folder).vars(self, scope="run")
        smoke = os.path.join(os.path.dirname(__file__), "smoke_test.sh")
        with env_vars.apply():
            self.output.info("Running test_package smoke_test.sh")
            self.run('sh "%s" "%s"' % (smoke, qgit_bin))
