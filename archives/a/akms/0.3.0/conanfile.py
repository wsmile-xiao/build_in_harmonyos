#!/usr/bin/env python3
"""Conan 2.x recipe — akms 0.3.0 (Alpine Kernel Module Support)

akms (DKMS for Alpine Linux) is a pure POSIX sh tool that builds
out-of-tree kernel modules per installed kernel. No C sources are
compiled: the source ships shell scripts (akms, akms-build, akms-runas,
akms.kernel-hook) plus akms.conf. The upstream Makefile's man-page target
needs asciidoctor (absent on OHOS), so the recipe installs the scripts
directly and skips man generation. build() validates the scripts with
`sh -n`. The tool's kernel-module functionality is Linux-specific, but
the scripts install and run (--version/--help) on OHOS as a packaged
tool.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AkmsConan(ConanFile):
    name = "akms"
    version = "0.3.0"
    description = "Alpine Kernel Module Support — build out-of-tree kernel modules (DKMS for Alpine)"
    license = "MIT"
    homepage = "https://github.com/jirutka/akms"
    url = "https://github.com/jirutka/akms"

    # Pure shell-script tool (no compiled binary in the usual sense, but it
    # ships an executable `akms` script) — package as an application.
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"akms supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure shell tool: validate the scripts parse (no C compilation).
        # The upstream Makefile `build` target generates man pages via
        # asciidoctor, which is not available on OHOS — skipped.
        for script in ("akms", "akms-build", "akms-runas", "akms.kernel-hook"):
            self.run(f"sh -n {self.source_folder}/{script}", env="conanbuild")

    def package(self):
        # Install the shell scripts directly (the upstream Makefile uses
        # coreutils `install` + sed path baking; a plain copy is simpler and
        # avoids tool dependencies on OHOS).
        src = self.source_folder
        pkg = self.package_folder
        for rel, dest in (
            ("akms", "bin"),
            ("akms-build", "libexec/akms"),
            ("akms-runas", "libexec/akms"),
            ("akms.kernel-hook", "share/kernel-hooks.d"),
            ("akms.conf", "etc"),
        ):
            copy(self, os.path.basename(rel), os.path.join(src, os.path.dirname(rel)) or src,
                 os.path.join(pkg, dest))
        # Make the main script executable.
        os.chmod(os.path.join(pkg, "bin", "akms"), 0o755)
        copy(self, "LICENSE", src, os.path.join(pkg, "licenses"))
        copy(self, "README.adoc", src, os.path.join(pkg, "res"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
