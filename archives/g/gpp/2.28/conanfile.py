#!/usr/bin/env python3
"""Conan recipe — gpp 2.28 (Autotools)

General-purpose preprocessor with customizable syntax.
Supports C/C++, TeX, HTML, Prolog and user-defined modes.

Build system: autotools (configure + make).
No external dependencies (only libc).
License: GPL-3.0-or-later
"""
import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class GppConan(ConanFile):
    name = "gpp"
    version = "2.28"
    description = "General-purpose preprocessor with customizable syntax"
    license = "GPL-3.0-or-later"
    homepage = "https://logological.org/gpp"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OS {self.settings.os} not supported, requires Linux or OHOS"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        is_ohos = str(self.settings.os) == "OHOS"

        if is_ohos:
            # HMDFS: mktemp -d creates dirs with drwx--S--- (broken group perms),
            # causing config.status to fail writing subs*.awk. Create a mktemp
            # wrapper that returns failure to force autoconf AS_TMPDIR mkdir fallback.
            import stat as stat_mod
            wrapper_dir = Path(self.build_folder) / ".ohos_fix"
            wrapper_dir.mkdir(exist_ok=True)
            wrapper = wrapper_dir / "mktemp"
            wrapper.write_text(
                '#!/bin/sh\n'
                '# HarmonyOS: mktemp -d creates dirs with broken perms.\n'
                '# Return failure to force autoconf AS_TMPDIR mkdir fallback.\n'
                'exit 1\n'
            )
            wrapper.chmod(wrapper.stat().st_mode | stat_mod.S_IEXEC)

        tc = AutotoolsToolchain(self)
        tc.generate()

        if is_ohos:
            # Prepend mktemp wrapper to PATH
            env = Environment()
            env.prepend_path("PATH", str(wrapper_dir))
            env.vars(self).save_script("ohos_env")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        # Sign ELF binary (HarmonyOS requires ELF signature for execution)
        bin_path = os.path.join(self.package_folder, "bin", "gpp")
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.exists(sign_tool) and os.path.exists(bin_path):
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", bin_path],
                capture_output=True, timeout=10,
            )
            tmp = bin_path + ".signed.tmp"
            for _attempt in range(3):
                r = subprocess.run(
                    [sign_tool, "sign", "-inFile", bin_path,
                     "-outFile", tmp, "-selfSign", "1"],
                    capture_output=True, timeout=30,
                )
                if r.returncode == 0 and os.path.exists(tmp):
                    shutil.move(tmp, bin_path)
                    break
                import time; time.sleep(1)
            else:
                if os.path.exists(tmp):
                    os.remove(tmp)
                raise ConanException(
                    f"ELF signing failed after 3 attempts for {bin_path}. "
                    f"Binary will not be executable on HarmonyOS."
                )
            os.chmod(bin_path, 0o755)

    def package_info(self):
        # gpp is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
