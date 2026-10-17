#!/usr/bin/env python3
"""Conan recipe for compat 31.0.0.2."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (
    copy,
    get,
    replace_in_file,
)
from conan.tools.layout import basic_layout


class CompatConan(ConanFile):
    name = "compat"
    version = "31.0.0.2"
    description = "Emacs Lisp compatibility library"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/emacs-compat/compat"
    url = "https://github.com/emacs-compat/compat"
    package_type = "unknown"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def package_id(self):
        self.info.clear()

    def requirements(self):
        self.requires("emacs/29.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        tmpdir = os.path.normpath(
            os.path.abspath(os.path.join(self.build_folder, "compat-check-tmp"))
        )
        os.makedirs(tmpdir, exist_ok=True)

        test_source = os.path.join(self.build_folder, f"compat-{self.version}")
        if os.path.isdir(test_source):
            shutil.rmtree(test_source)
        os.makedirs(test_source, exist_ok=True)
        for filename in os.listdir(self.source_folder):
            source_file = os.path.join(self.source_folder, filename)
            if not os.path.isfile(source_file):
                continue
            if (
                filename == "Makefile"
                or filename in ("COPYING", "README.md", "compat.texi")
                or (filename.startswith("compat") and filename.endswith(".el"))
            ):
                shutil.copy2(source_file, os.path.join(test_source, filename))

        self._patch_ohos_test_source(test_source)

        makefile = os.path.join(test_source, "Makefile")
        replace_in_file(
            self,
            makefile,
            "sort > /tmp/compat-defs",
            'sort > "$(TMPDIR)/compat-defs"',
            strict=False,
        )
        replace_in_file(
            self,
            makefile,
            "sort | uniq > /tmp/compat-links",
            'sort | uniq > "$(TMPDIR)/compat-links"',
            strict=False,
        )
        replace_in_file(
            self,
            makefile,
            "diff /tmp/compat-defs /tmp/compat-links",
            'diff "$(TMPDIR)/compat-defs" "$(TMPDIR)/compat-links"',
            strict=False,
        )
        with open(makefile, encoding="utf-8") as file:
            makefile_text = file.read()
        if "/tmp/compat-defs" in makefile_text or "/tmp/compat-links" in makefile_text:
            raise ValueError("compat make check still writes under /tmp")

        env = Environment()
        env.define("CI", "true")
        env.define("COMPAT_OHOS_SKIP_TRAMP_TMP", "1")
        env.define("TMPDIR", tmpdir)
        env.prepend_path("PATH", "/usr/bin")
        env.prepend_path("PATH", "/bin")
        env.vars(self).save_script("compat_test_env")

        make = self.conf.get("tools.gnu:make_program", default="make")
        make = shlex.quote(make)
        build_env = ["conanbuild", "conanrun", "compat_test_env"]
        self.run(f"{make} clean", cwd=test_source, env=build_env)
        self.run(f"{make} compile", cwd=test_source, env=build_env)
        self.run(f"{make} test", cwd=test_source, env=build_env)
        self.run(f"{make} check", cwd=test_source, env=build_env)

    def _patch_ohos_test_source(self, test_source):
        if self.settings.os != "OHOS":
            return

        tests = os.path.join(test_source, "compat-tests.el")
        skip = (
            '    (when (getenv "COMPAT_OHOS_SKIP_TRAMP_TMP")\n'
            '      (ert-skip\n'
            '       "OHOS runner cannot access /tmp through the mock TRAMP remote"))\n'
        )
        replace_in_file(
            self,
            tests,
            '    ;; Tramp test (mock protocol)\n'
            '    (let* ((default-directory "/mock::/")',
            '    ;; Tramp test (mock protocol)\n'
            + skip
            + '    (let* ((default-directory "/mock::/")',
        )
        replace_in_file(
            self,
            tests,
            '  ;; Tramp test (mock protocol)\n'
            '  (let ((default-directory "/mock::/"))',
            '  ;; Tramp test (mock protocol)\n'
            + skip.replace("    ", "  ", 1)
            + '  (let ((default-directory "/mock::/"))',
        )

    def package(self):
        lisp_dir = os.path.join(
            self.package_folder,
            "share",
            "emacs",
            "site-lisp",
            f"compat-{self.version}",
        )
        for pattern in (
            "compat.el",
            "compat-[0-9][0-9].el",
            "compat-macs.el",
            "compat-pkg.el",
        ):
            copy(self, pattern, self.source_folder, lisp_dir, keep_path=False)

        share_dir = os.path.join(self.package_folder, "share", "compat")
        copy(self, "README.md", self.source_folder, share_dir, keep_path=False)
        copy(self, "compat.texi", self.source_folder, share_dir, keep_path=False)
        copy(
            self,
            "COPYING",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        lisp_dir = os.path.join(
            self.package_folder,
            "share",
            "emacs",
            "site-lisp",
            f"compat-{self.version}",
        )

        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

        self.buildenv_info.define_path("COMPAT_LISPDIR", lisp_dir)
        self.runenv_info.define_path("COMPAT_LISPDIR", lisp_dir)
        self.buildenv_info.prepend_path("EMACSLOADPATH", lisp_dir)
        self.runenv_info.prepend_path("EMACSLOADPATH", lisp_dir)
