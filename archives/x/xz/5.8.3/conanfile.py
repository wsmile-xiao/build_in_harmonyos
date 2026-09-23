#!/usr/bin/env python3
"""Conan recipe for xz 5.8.3 — Autotools build system (configure + make).

XZ Utils provide liblzma (LZMA2 compression library) and xz/xzdec command-line tools.
Build: ./configure && make && make check && make install
No external dependencies. Not a system same-name library (no /lib/liblzma.so),
so default (shared) linking is acceptable.

This version includes the CVE-2026-34743 fix from upstream.
"""
import os
import stat
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class XzConan(ConanFile):
    name = "xz"
    version = "5.8.3"
    description = "XZ Utils — general-purpose data compression with high ratio (LZMA2), includes CVE-2026-34743 fix"
    license = "0BSD"
    homepage = "https://tukaani.org/xz/"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # HarmonyOS: mktemp -d creates dirs with drwx--S--- (broken group perms),
        # causing config.status to fail. Create a mktemp wrapper that fixes perms.
        wrapper_dir = Path(self.build_folder) / ".hmos_fix"
        wrapper_dir.mkdir(exist_ok=True, parents=True)
        wrapper = wrapper_dir / "mktemp"
        wrapper.write_text(
            '#!/bin/sh\n'
            '# HarmonyOS: mktemp -d creates dirs with broken perms (hmmac MAC).\n'
            '# Return failure to force autoconf AS_TMPDIR to use mkdir fallback.\n'
            'exit 1\n'
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

        tc = AutotoolsToolchain(self)
        # OHOS: scripts (xzdiff, xzgrep, etc.) use /bin/sh which doesn't exist.
        # Disable scripts to skip test_scripts.sh and avoid installing broken scripts.
        tc.configure_args.append("--disable-scripts")
        # Link binaries (xz, lzmadec, lzmainfo) statically against liblzma.a
        # so they don't need LD_LIBRARY_PATH at runtime (L2 smoke test).
        # liblzma.so is still built for consumers who need shared linking.
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.extra_ldflags.append("-static")
        tc.generate()

        # OHOS: No /bin/sh — propagate CONFIG_SHELL and mktemp wrapper
        env = Environment()
        config_shell = os.environ.get("CONFIG_SHELL")
        if config_shell:
            env.define("CONFIG_SHELL", config_shell)
        env.prepend_path("PATH", str(wrapper_dir))
        # Set LD_LIBRARY_PATH for make check (test programs need liblzma.so
        # from build tree, but rpath points to install prefix /lib)
        lib_build_dir = os.path.join(self.build_folder, "src", "liblzma", ".libs")
        env.prepend_path("LD_LIBRARY_PATH", lib_build_dir)
        env.vars(self).save_script("ohos_env")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # L1: Run upstream official test suite (make check)
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["lzma"]
