#!/usr/bin/env python3
"""Conan recipe — ndisc6 1.0.8 (Autotools)

IPv6 diagnostic tools (ndisc6, rdisc6, rltraceroute6, tcpspray, rdnssd).
Homepage: https://github.com/nomis/ndisc6
License: GPL-2.0-or-later
"""
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Ndisc6Conan(ConanFile):
    name = "ndisc6"
    version = "1.0.8"
    description = "IPv6 diagnostic tools: ndisc6, rdisc6, rltraceroute6, tcpspray, rdnssd"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/nomis/ndisc6"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

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
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._patch_config_for_ohos()

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1", "ACLOCAL=true", "AUTOCONF=true", "AUTOMAKE=true"])

    def _patch_config_for_ohos(self):
        """Patch config.guess and config.sub to recognize HarmonyOS/OHOS (R15).
        Patches 0001/0002 already apply these changes; this is a fallback
        in case the source version changes and patches don't apply cleanly.
        """
        candidates = [
            self.source_folder,
            os.path.join(self.source_folder, "admin"),
            os.path.join(self.source_folder, "build-aux"),
        ]
        cg_path = cs_path = None
        for d in candidates:
            cg = os.path.join(d, "config.guess")
            cs = os.path.join(d, "config.sub")
            if os.path.exists(cg) and os.path.exists(cs):
                cg_path = cg
                cs_path = cs
                break

        if not cg_path or not cs_path:
            self.output.info("config.guess/config.sub not found, skipping OHOS patch")
            return

        # Check if patches already applied
        with open(cg_path, "r") as f:
            cg_content = f.read()
        if "__OHOS__" in cg_content or "HarmonyOS" in cg_content:
            self.output.info("config.guess already patched for OHOS")
            return

        skill_root = os.environ.get("OHC_SKILL_ROOT", "")
        if skill_root:
            script = os.path.join(skill_root, "scripts", "patch-autotools-ohos.pl")
            if os.path.exists(script):
                self.output.info(f"Patching config.guess/config.sub with {script}")
                subprocess.run(["perl", script, cg_path, cs_path], check=True)
                with open(cs_path, "r") as f:
                    content = f.read()
                if "linux-ohos*" not in content:
                    content = content.replace(
                        "| linux-uclibc* )",
                        "| linux-uclibc* | linux-ohos* )",
                    )
                    with open(cs_path, "w") as f:
                        f.write(content)
                return

        self._manual_patch_config_guess(cg_path)
        self._manual_patch_config_sub(cs_path)

    def _manual_patch_config_guess(self, cg_path):
        with open(cg_path, "r") as f:
            content = f.read()

        changed = False

        if "__OHOS__" not in content:
            old = "#if defined(__ANDROID__)\n    LIBC=android"
            new = "#if defined(__ANDROID__)\n    LIBC=android\n#elif defined(__OHOS__)\n    LIBC=ohos"
            if old in content:
                content = content.replace(old, new, 1)
                changed = True

        if "HarmonyOS" not in content:
            block = (
                '    *:HarmonyOS:*:*)\n'
                '\tcase "$UNAME_MACHINE" in\n'
                '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
                '\t    armv7*|armv8*) MACHINE=arm ;;\n'
                '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
                '\t    i?86)          MACHINE=i686 ;;\n'
                '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                '\tesac\n'
                '\tGUESS=${MACHINE}-unknown-linux-ohos\n'
                '\t;;\n\n'
                '    *:NetBSD:*:*)'
            )
            if "    *:NetBSD:*:*)" in content:
                content = content.replace("    *:NetBSD:*:*)", block, 1)
                changed = True

        if changed:
            with open(cg_path, "w") as f:
                f.write(content)

    def _manual_patch_config_sub(self, cs_path):
        with open(cs_path, "r") as f:
            content = f.read()

        changed = False

        if "ohos-linux" not in content:
            pattern = r'(android-linux\)\s*\n\s*basic_machine=\$field1-unknown\s*\n\s*basic_os=linux-android\s*\n\s*;;\s*\n)'
            replacement = r'\1\tohos-linux)\n\tbasic_machine=$field1-unknown\n\tbasic_os=linux-ohos\n\t;;\n'
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                content = new_content
                changed = True

        if "ohos*" not in content:
            content = content.replace("gnu* | android*", "gnu* | android* | ohos*", 1)
            changed = True

        if "linux-ohos*" not in content:
            content = content.replace(
                "| linux-uclibc* )",
                "| linux-uclibc* | linux-ohos* )",
            )
            changed = True

        if changed:
            with open(cs_path, "w") as f:
                f.write(content)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
