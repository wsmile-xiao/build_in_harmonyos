#!/usr/bin/env python3
"""Conan recipe for autoenv 0.4.0 — pure shell hook project."""
import os
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AutoenvConan(ConanFile):
    name = "autoenv"
    version = "0.4.0"
    description = "Directory-based shell environments"
    license = "MIT"
    homepage = "https://github.com/hyperupcall/autoenv"
    url = "https://github.com/hyperupcall/autoenv"
    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        activate = os.path.join(self.source_folder, "activate.sh")
        with open(activate, "r", encoding="utf-8") as f:
            content = f.read()
        replacements = (
            ('\\command grep -q "${_hash}" --', '\\command grep -Fq -- "${_hash}"'),
            ('\\command grep -Gv "${_envfile}:" --', '\\command grep -Fv -- "${_envfile}:"'),
            (
                '\\command grep -Fv -- "${_envfile}:" "${AUTOENV_AUTH_FILE}.tmp" >| "${AUTOENV_AUTH_FILE}"',
                '\\command grep -Fv -- "${_envfile}:" "${AUTOENV_AUTH_FILE}.tmp" >| "${AUTOENV_AUTH_FILE}" || :',
            ),
            (
                "__autoenv_has_builtin=no\nif __autoenv_output=$(\\type builtin); then\n\tif [ \"${__autoenv_output}\" = 'builtin is a shell builtin' ]; then\n\t\t__autoenv_has_builtin=yes\n\tfi\nfi\n\\unset -v __autoenv_output",
                "__autoenv_has_builtin=no\nif \\command -v builtin >/dev/null 2>&1; then\n\t__autoenv_has_builtin=yes\nfi",
            ),
        )
        for old, new in replacements:
            if old in content:
                content = content.replace(old, new, 1)
            elif new not in content:
                raise ConanInvalidConfiguration("autoenv activate.sh patch target not found")
        with open(activate, "w", encoding="utf-8") as f:
            f.write(content)

        if can_run(self):
            # The upstream test (tests/test.sh) requires the 'dash' shell.
            # Skip the test if dash is not available on the build host.
            if not self._find_dash():
                self.output.warning("upstream tests skipped: dash shell not found on build host")
                return

            env = dict(os.environ)
            env.setdefault("ZDOTDIR", "/dev/null")
            result = subprocess.run(
                ["sh", "tests/test.sh"],
                cwd=self.source_folder,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=300,
            )
            if result.returncode != 0:
                self.output.info(result.stdout[-2000:])
                raise ConanInvalidConfiguration("upstream tests failed on the build host")
            else:
                self.output.info("upstream tests: SUCCESS")

    def _find_dash(self):
        """Check if the 'dash' shell executable is available on PATH."""
        import shutil
        return shutil.which("dash") is not None

    def package(self):
        dst = os.path.join(self.package_folder, "res", "autoenv")
        copy(self, "activate.sh", src=self.source_folder, dst=dst, keep_path=False)
        copy(self, "README.md", src=self.source_folder, dst=dst, keep_path=False)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        activate = os.path.join(dst, "activate.sh")
        if os.path.isfile(activate):
            os.chmod(activate, os.stat(activate).st_mode | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.conf_info.define("user.autoenv:activate", os.path.join(self.package_folder, "res", "autoenv", "activate.sh"))
