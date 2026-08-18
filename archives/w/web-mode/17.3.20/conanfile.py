#!/usr/bin/env python3
"""Conan recipe for web-mode 17.3.20."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class WebModeConan(ConanFile):
    name = "web-mode"
    version = "17.3.20"
    description = "Emacs major mode for editing web templates"
    license = "GPL-3.0-or-later"
    homepage = "https://web-mode.org/"
    url = "https://github.com/fxbois/web-mode"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("emacs/29.1")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"web-mode supports Linux and OHOS, got {self.settings.os}"
            )
        if self.options.shared:
            raise ConanInvalidConfiguration("web-mode is an architecture-independent Elisp package")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
        )

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def _emacs(self):
        dependency = self.dependencies["emacs"]
        emacs = os.path.join(dependency.package_folder, "bin", "emacs")
        if not os.path.isfile(emacs):
            raise ConanInvalidConfiguration(f"Emacs executable is missing: {emacs}")
        return shlex.quote(emacs)

    def build(self):
        apply_conandata_patches(self)
        self._run_upstream_tests()
        self.run(
            f"{self._emacs()} -Q --batch "
            f"-f batch-byte-compile {shlex.quote(os.path.join(self.source_folder, 'web-mode.el'))}",
            env="conanbuild",
        )
        compiled = os.path.join(self.source_folder, "web-mode.elc")
        if not os.path.isfile(compiled) or os.path.getsize(compiled) == 0:
            raise ConanException("web-mode.elc was not produced")

    def _run_upstream_tests(self):
        tests_dir = os.path.join(self.source_folder, "tests")
        fixtures = sorted(
            name
            for name in os.listdir(tests_dir)
            if os.path.isfile(os.path.join(tests_dir, name))
            and not name.startswith("_")
        )
        if len(fixtures) != 31:
            raise ConanException(
                f"Expected 31 upstream web-mode fixtures, found {len(fixtures)}"
            )
        for name in os.listdir(tests_dir):
            if name.startswith("_err."):
                os.remove(os.path.join(tests_dir, name))
        command = (
            f"{self._emacs()} -Q --batch "
            "--eval '(setq standard-indent 2)' "
            "--eval '(setq-default indent-tabs-mode nil)' "
            f"--eval '(setq web-mode-tests-directory {self._elisp_string(tests_dir)})' "
            f"-l {shlex.quote(os.path.join(self.source_folder, 'web-mode.el'))} "
            "-f web-mode-test"
        )
        self.run(command, cwd=self.source_folder, env="conanbuild")
        failures = sorted(
            name for name in os.listdir(tests_dir) if name.startswith("_err.")
        )
        if failures:
            raise ConanException(
                "Upstream web-mode fixture tests failed: " + ", ".join(failures)
            )
        self.output.success("Upstream web-mode fixture tests passed: 31/31")

    @staticmethod
    def _elisp_string(value):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    def package(self):
        lisp_dir = os.path.join(
            self.package_folder,
            "share",
            "emacs",
            "site-lisp",
            f"web-mode-{self.version}",
        )
        copy(self, "web-mode.el", self.source_folder, lisp_dir)
        copy(self, "web-mode.elc", self.source_folder, lisp_dir)
        copy(
            self,
            "README.md",
            self.source_folder,
            os.path.join(self.package_folder, "share", "doc", "web-mode"),
        )
        copy(
            self,
            "LICENSE",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        lisp_dir = os.path.join(
            self.package_folder,
            "share",
            "emacs",
            "site-lisp",
            f"web-mode-{self.version}",
        )
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
        self.buildenv_info.define_path("WEB_MODE_LISPDIR", lisp_dir)
        self.runenv_info.define_path("WEB_MODE_LISPDIR", lisp_dir)
        self.buildenv_info.prepend_path("EMACSLOADPATH", lisp_dir)
        self.runenv_info.prepend_path("EMACSLOADPATH", lisp_dir)
