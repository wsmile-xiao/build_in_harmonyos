#!/usr/bin/env python3
"""Conan test_package for neovim-qt 0.2.19."""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class NeovimQtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self._package_folder()
        executable = self._find_executable(package_folder)
        self._assert_nonempty_file(executable, "nvim-qt executable")
        self._assert_installed_assets(package_folder)
        if can_run(self):
            script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_neovim_qt_assets.sh")
            self.run("sh {} {}".format(shlex.quote(script), shlex.quote(executable)), env="conanrun")
            self.run('"{}" --version'.format(executable), env="conanrun")
        else:
            self.output.info("nvim-qt package content validated for cross profile")

    def _package_folder(self):
        for dependency in self.dependencies.values():
            if dependency.package_folder:
                return dependency.package_folder
        raise ConanException("neovim-qt package folder was not available")

    def _find_executable(self, package_folder):
        candidates = []
        for dependency in self.dependencies.values():
            for bindir in dependency.cpp_info.bindirs:
                candidates.append(os.path.join(bindir, "nvim-qt"))
        candidates.append(os.path.join(package_folder, "bin", "nvim-qt"))
        executable = next((path for path in candidates if os.path.isfile(path)), None)
        if not executable:
            raise ConanException("nvim-qt executable was not packaged")
        return executable

    def _assert_nonempty_file(self, path, description):
        if not os.path.isfile(path):
            raise ConanException("{} missing: {}".format(description, path))
        if os.path.getsize(path) <= 0:
            raise ConanException("{} is empty: {}".format(description, path))

    def _assert_installed_assets(self, package_folder):
        required = {
            "desktop launcher": (".desktop",),
            "icon resource": (".png", ".svg", ".ico"),
        }
        found = {name: False for name in required}
        for root, _, files in os.walk(package_folder):
            for filename in files:
                lower = filename.lower()
                for name, suffixes in required.items():
                    if lower.endswith(suffixes):
                        found[name] = True
        missing = [name for name, present in found.items() if not present]
        if missing:
            raise ConanException("missing installed neovim-qt assets: {}".format(", ".join(missing)))
