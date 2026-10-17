#!/usr/bin/env python3
"""Conan recipe for aircrack-ng 1.7 — WiFi security auditing tools suite."""
import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import (Autotools, AutotoolsDeps,
                             AutotoolsToolchain, PkgConfigDeps)
from conan.tools.layout import basic_layout


class AircrackngConan(ConanFile):
    name = "aircrack-ng"
    version = "1.7"
    description = "WiFi security auditing tools suite"
    license = "GPL-2.0"
    homepage = "https://aircrack-ng.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")

    def build_requirements(self):
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--with-libnl=no")
        tc.extra_cflags.append("-Wno-deprecated-declarations")
        tc.generate()
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

    def _patch_config_for_ohos(self):
        """Patch config.guess and config.sub to recognize HarmonyOS (R15/E007)."""
        src = self.source_folder
        candidates = [src, os.path.join(src, "build-aux")]
        cg_path = cs_path = None
        for d in candidates:
            cg = os.path.join(d, "config.guess")
            cs = os.path.join(d, "config.sub")
            if os.path.exists(cg) and os.path.exists(cs):
                cg_path, cs_path = cg, cs
                break
        if not cg_path:
            return

        # Try skill's perl script if OHC_SKILL_ROOT is set
        skill_root = os.environ.get("OHC_SKILL_ROOT", "")
        if skill_root:
            script = os.path.join(skill_root, "scripts", "patch-autotools-ohos.pl")
            if os.path.exists(script):
                self.run(f'perl "{script}" "{cg_path}" "{cs_path}"')
                return

        # Manual Python fallback
        self._patch_config_guess(cg_path)
        self._patch_config_sub(cs_path)

    def _patch_config_guess(self, cg_path):
        with open(cg_path, "r") as f:
            content = f.read()
        changed = False

        if "__OHOS__" not in content:
            old = "#if defined(__ANDROID__)\n    LIBC=android"
            new = ("#if defined(__ANDROID__)\n    LIBC=android"
                   "\n#elif defined(__OHOS__)\n    LIBC=ohos")
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

    def _patch_config_sub(self, cs_path):
        with open(cs_path, "r") as f:
            content = f.read()
        changed = False

        if "ohos-linux" not in content:
            pattern = (r'(android-linux\)\s*\n\s*basic_machine=\$field1-unknown'
                       r'\s*\n\s*basic_os=linux-android\s*\n\s*;;\s*\n)')
            replacement = (r'\1\tohos-linux)\n'
                           r'\tbasic_machine=$field1-unknown\n'
                           r'\tbasic_os=linux-ohos\n\t;;\n')
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                content = new_content
                changed = True

        if "ohos*" not in content:
            content = content.replace("gnu* | android*", "gnu* | android* | ohos*", 1)
            changed = True

        if "linux-ohos" not in content:
            content, count = re.subn(r'(linux-uclibc[\*/-]?\s*\))',
                                     r'\1| linux-ohos*)', content)
            if count > 0:
                changed = True

        if changed:
            with open(cs_path, "w") as f:
                f.write(content)

    def build(self):
        apply_conandata_patches(self)

        # Dynamically locate pkg.m4 for aclocal (R33: no hardcoded paths)
        pkg_config = shutil.which("pkg-config")
        if pkg_config:
            real_path = os.path.realpath(pkg_config)
            prefix = os.path.dirname(os.path.dirname(real_path))
            aclocal_dir = os.path.join(prefix, "share", "aclocal")
            if os.path.isfile(os.path.join(aclocal_dir, "pkg.m4")):
                existing = os.environ.get("ACLOCAL_PATH", "")
                os.environ["ACLOCAL_PATH"] = (
                    f"{aclocal_dir}:{existing}" if existing else aclocal_dir
                )

        # Regenerate autotools files (tarball ships configure.ac only)
        self.run("autoreconf -fiv", cwd=self.source_folder)

        # Patch config.guess/config.sub for HarmonyOS (E007)
        self._patch_config_for_ohos()

        # Fix HMDFS umask 077 issue: autoconf's config.status template
        # uses "./confXXXXXX" with umask 077 for temp files, which fails
        # on HMDFS. Redirect to ${TMPDIR:-/tmp} and remove umask.
        # This is in autoconf's internal template, not configurable.ac.
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            with open(configure_path, "r") as f:
                content = f.read()
            content = content.replace(
                'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
                'tmp=`(mktemp -d "${TMPDIR:-/tmp}/confXXXXXX") 2>/dev/null`'
            )
            content = content.replace(
                'tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")',
                'tmp="${TMPDIR:-/tmp}/conf$$-$RANDOM"\n  mkdir "$tmp"'
            )
            with open(configure_path, "w") as f:
                f.write(content)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libs = ["aircrack", "aircrack-ce-wpa", "aircrack-ce-wep",
                              "aircrack-osdep", "accrypto", "cowpatty",
                              "ptw", "radiotap"]
