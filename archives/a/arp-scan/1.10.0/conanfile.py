#!/usr/bin/env python3
"""Conan recipe for arp-scan 1.10.0 — ARP-based network discovery tool.

arp-scan sends ARP requests to discover and fingerprint hosts on the local
network. It uses libpcap for packet capture and supports IEEE OUI lookup.

Build system: Autotools (configure + make)
Dependencies: libpcap >= 1.10.6 (from ohpcd conan repo)

OHOS adaptations (handled in build()):
  - config.guess/config.sub: patch for HarmonyOS recognition (E007)
  - configure: remove umask 077 from temp-dir creation (E114: HMDFS setgid)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class ArpScanConan(ConanFile):
    name = "arp-scan"
    version = "1.10.0"
    description = "ARP scanner — discover and fingerprint hosts on local network via ARP requests"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/royhills/arp-scan"
    url = ""  # CI fills this

    # CLI tool, not a library (R38: commands.json declared at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpcap/1.10.6")

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"arp-scan is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsDeps: feed -I/-L/-l from libpcap into configure/make
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _patch_config_guess(self, cg_path):
        """Patch config.guess for HarmonyOS support (E007).

        The release tarball ships config.guess v2022 (GUESS= format)
        which does not recognize HarmonyOS.
        """
        with open(cg_path, "r") as f:
            cg = f.read()
        changed = False

        # 1. Add __OHOS__ LIBC detection after __dietlibc__
        if "__OHOS__" not in cg:
            cg = cg.replace(
                "#elif defined(__dietlibc__)\n\tLIBC=dietlibc\n",
                "#elif defined(__dietlibc__)\n\tLIBC=dietlibc\n#elif defined(__OHOS__)\n\tLIBC=ohos\n",
            )
            changed = True

        # 2. Add HarmonyOS case block before NetBSD (GUESS= format)
        if "HarmonyOS" not in cg:
            block = (
                '    *:HarmonyOS:*:*)\n'
                '\tcase "$UNAME_MACHINE" in\n'
                '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
                '\t    armv7*|armv8*) MACHINE=arm ;;\n'
                '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
                '\t    i?86)         MACHINE=i686 ;;\n'
                '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                '\tesac\n'
                '\tGUESS=${MACHINE}-unknown-linux-ohos\n'
                '\t;;\n\n'
            )
            cg = cg.replace("    *:NetBSD:*:*)", block + "    *:NetBSD:*:*)")
            changed = True

        if changed:
            with open(cg_path, "w") as f:
                f.write(cg)

    def _patch_config_sub(self, cs_path):
        """Patch config.sub for HarmonyOS support (E007).

        The release tarball ships config.sub v2022 which does not
        recognize 'ohos' as an OS.
        """
        with open(cs_path, "r") as f:
            cs = f.read()
        changed = False

        # 1. Add linux-ohos* to OS validation list (line ~1775)
        # Pattern: "| linux-uclibc* )" → "| linux-uclibc* | linux-ohos* )"
        if "linux-ohos" not in cs:
            cs = cs.replace(
                " | linux-uclibc* )",
                " | linux-uclibc* | linux-ohos* )",
            )
            changed = True

        # 2. Add ohos-linux to android-linux case (line ~152)
        if "ohos-linux" not in cs:
            cs = cs.replace(
                "android-linux)",
                "android-linux | ohos-linux)",
            )
            changed = True

        # 3. Add -ohos* to negative libc pattern list
        # Pattern: "-uclibc* )" → "-uclibc* | -ohos* )"
        if "-ohos* )" not in cs:
            cs = cs.replace(
                "-uclibc* )",
                "-uclibc* | -ohos* )",
            )
            changed = True

        # 4. Add ohos* to libc-only pattern list
        # Pattern: "uclibc*)" → "uclibc* | ohos*)"
        if "| ohos*)" not in cs:
            cs = cs.replace(
                "uclibc*)",
                "uclibc* | ohos*)",
            )
            changed = True

        if changed:
            with open(cs_path, "w") as f:
                f.write(cs)

    def build(self):
        apply_conandata_patches(self)

        # Patch config.guess/config.sub for HarmonyOS (E007)
        build_aux = os.path.join(self.source_folder, "build-aux")
        cg_path = os.path.join(build_aux, "config.guess")
        cs_path = os.path.join(build_aux, "config.sub")
        if os.path.exists(cg_path):
            self._patch_config_guess(cg_path)
        if os.path.exists(cs_path):
            self._patch_config_sub(cs_path)

        # Fix umask 077 in configure is handled by patch (0001-configure-umask-fix.patch)
        # via apply_conandata_patches() above — no runtime modification of generated files (R6)

        # Run configure and make (R9: -j1 to avoid HMDFS jobserver fifo EPERM)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # CLI tool, no library info
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
