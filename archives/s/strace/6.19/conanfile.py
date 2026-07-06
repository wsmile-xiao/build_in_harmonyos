#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Strace, strace, 6.19, System call tracer for monitoring process-kernel interaction, LGPL-2.1, https://strace.io/
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for terminal tools.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class StraceConan(ConanFile):
    name = "strace"
    version = "6.19"
    description = "System call tracer for monitoring process-kernel interaction"
    license = "LGPL-2.1"
    homepage = "https://strace.io/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # strace is a standalone binary tool, not a system same-name library
        # --disable-mpers: disable multi-architecture personality support (not available on OHOS)
        # --disable-dependency-tracking: avoid OOM during depfiles bootstrap on memory-constrained systems
        tc.configure_args.append("--disable-mpers")
        tc.configure_args.append("--disable-dependency-tracking")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix CONFIG_SHELL from profile that may point to non-existent path
        bash_path = shutil.which("bash") or "/bin/sh"
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            with open(configure_path, "r") as f:
                content = f.read()
            # Insert CONFIG_SHELL fallback after shebang line
            if content.startswith("#!"):
                shebang = content.split("\n", 1)[0]
                rest = content.split("\n", 1)[1] if "\n" in content else ""
                fallback = (
                    f'{shebang}\n'
                    f'# Override invalid paths from Conan profile\n'
                    f'if [ ! -x "$CONFIG_SHELL" ] 2>/dev/null; then\n'
                    f'  CONFIG_SHELL={bash_path}\n'
                    f'  export CONFIG_SHELL\n'
                    f'fi\n'
                    f'if [ ! -x "$SHELL" ] 2>/dev/null; then\n'
                    f'  SHELL={bash_path}\n'
                    f'  export SHELL\n'
                    f'fi\n'
                    f'if [ -n "$CC" ] && [ ! -x "$CC" ] 2>/dev/null; then\n'
                    f'  CC=clang\n'
                    f'  export CC\n'
                    f'fi\n'
                    f'if [ -n "$CXX" ] && [ ! -x "$CXX" ] 2>/dev/null; then\n'
                    f'  CXX=clang++\n'
                    f'  export CXX\n'
                    f'fi\n'
                )
                content = fallback + rest
                with open(configure_path, "w") as f:
                    f.write(content)
        os.environ["CONFIG_SHELL"] = bash_path
        os.environ["SHELL"] = bash_path
        # Fix umask 077 issue on HMDFS (E002-related): directories created
        # with umask 077 get setgid bit which prevents file creation
        for fn in ["configure", "config.status"]:
            p = os.path.join(self.source_folder, fn)
            if os.path.exists(p):
                with open(p, "r") as f:
                    content = f.read()
                content = content.replace("umask 077", "umask 022")
                with open(p, "w") as f:
                    f.write(content)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # strace is a standalone binary tool, no libraries to export
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
