#!/usr/bin/env python3
"""Conan recipe — kexec-tools 2.0.32 (autotools, userspace kexec/kdump tools).

HarmonyOS PC (aarch64-linux-ohos) adaptation:
- config.guess/config.sub: HarmonyOS triplet recognition (aarch64-unknown-linux-ohos)
- configure: umask 077 -> 022 (HMDFS: dirs created via `umask 077 && mktemp -d`
  get the setgid quirk that denies owner writes, breaking config.status)
- stale include/config.h removed from the dist tarball (upstream packaging
  leftover with HAVE_LIBZSTD defined that shadows the freshly generated one)
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class KexecToolsConan(ConanFile):
    name = "kexec-tools"
    version = "2.0.32"
    description = "kexec-tools: userspace tools for the Linux kernel kexec/kdump mechanism (kexec loader + vmcore-dmesg)"
    license = "GPL-2.0"
    homepage = "https://kernel.org/pub/linux/utils/kernel/kexec/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # zlib is auto-detected by configure on the build host; upstream keeps
        # it optional (--without-zlib). No conan-side requirement needed.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix CONFIG_SHELL from profile that may point to non-existent path
        bash_path = shutil.which("bash") or "/bin/sh"
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            replace_in_file(self, configure_path, "#!/bin/sh",
                            f'#!/bin/sh\nif [ ! -x "$CONFIG_SHELL" ] 2>/dev/null; then\n'
                            f'  CONFIG_SHELL={bash_path}\n  export CONFIG_SHELL\nfi\n'
                            f'if [ ! -x "$SHELL" ] 2>/dev/null; then\n'
                            f'  SHELL={bash_path}\n  export SHELL\nfi', strict=False)
        os.environ["CONFIG_SHELL"] = bash_path
        os.environ["SHELL"] = bash_path
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # kexec-tools ships command line tools only (kexec, vmcore-dmesg),
        # no public libraries
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
