#!/usr/bin/env python3
"""Conan recipe for libesedb — Autotools projects (configure + make).

Patches: E007 (config.guess/config.sub HarmonyOS) + E011 (umask fix)
R26: Terminal tools statically linked.
"""
import os
import subprocess
import tempfile

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibesedbConan(ConanFile):
    name = "libesedb"
    version = "20240420"
    description = "Library to access the Extensible Storage Engine (ESE) Database File (EDB) format"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/libyal/libesedb"
    url = ""

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
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        # E053: Provide libintl for bindtextdomain (gettext)
        tc.extra_ldflags.append("-L/data/service/hnp/gettext.org/gettext_0.26/lib")
        tc.extra_ldflags.append("-lintl")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder

        # E007: Patch config.guess for HarmonyOS
        cg = os.path.join(src, "config.guess")
        if os.path.exists(cg) and "HarmonyOS" not in open(cg).read():
            with open(cg, "r") as f:
                content = f.read()
            insertion = (
                '    *:HarmonyOS:*:*)\n'
                '\tcase "$UNAME_MACHINE" in\n'
                '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
                '\t    armv7*|armv8*) MACHINE=arm ;;\n'
                '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
                '\t    i?86)         MACHINE=i686 ;;\n'
                '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                '\tesac\n'
                '\tGUESS=${MACHINE}-unknown-linux-ohos\n'
                '\t;;\n'
                '\n'
            )
            marker = "    *:NetBSD:*:*)"
            content = content.replace(marker, insertion + marker, 1)
            with open(cg, "w") as f:
                f.write(content)
            self.output.info("Patched config.guess for HarmonyOS")

        # E007: Patch config.sub for ohos
        cs = os.path.join(src, "config.sub")
        if os.path.exists(cs) and "ohos" not in open(cs).read():
            with open(cs, "r") as f:
                content = f.read()
            # Add ohos-linux case
            old_block = '\t\t\t\tbasic_machine=$field1-unknown\n\t\t\t\tbasic_os=linux-android\n\t\t\t\t;;'
            new_block = (
                '\t\t\t\tbasic_machine=$field1-unknown\n'
                '\t\t\t\tbasic_os=linux-android\n'
                '\t\t\t\t;;\n'
                '\tohos-linux)\n'
                '\t\t\t\tbasic_machine=$field1-unknown\n'
                '\t\t\t\tbasic_os=linux-ohos\n'
                '\t\t\t\t;;'
            )
            content = content.replace(old_block, new_block, 1)
            # Add ohos* to recognized OS patterns
            content = content.replace(
                'gnu* | android* | bsd*',
                'gnu* | android* | ohos* | bsd*',
                1
            )
            # Add linux-ohos* to case list
            content = content.replace(
                '\tos2-emx)\n\t\t;;',
                '\tos2-emx)\n\t\t;;\n\tlinux-ohos*)\n\t\t;;',
                1
            )
            with open(cs, "w") as f:
                f.write(content)
            self.output.info("Patched config.sub for HarmonyOS")

        # E011: Fix umask 077 -> 022 in configure (and generated config.status)
        cf = os.path.join(src, "configure")
        if os.path.exists(cf):
            with open(cf, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            with open(cf, "w") as f:
                f.write(content)
            self.output.info("Patched configure umask 077->022")

        autotools = Autotools(self)
        autotools.configure()

        # E011: Also fix config.status after configure generates it
        cs_status = os.path.join(src, "config.status")
        if os.path.exists(cs_status):
            with open(cs_status, "r") as f:
                content = f.read()
            if "umask 077" in content:
                content = content.replace("umask 077", "umask 022")
                with open(cs_status, "w") as f:
                    f.write(content)
                self.output.info("Patched config.status umask 077->022")
                # Re-run config.status
                subprocess.run(
                    ["/data/service/hnp/bin/bash", "./config.status"],
                    cwd=src,
                    check=True
                )
                self.output.info("Re-ran config.status")

        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["esedb"]
