#!/usr/bin/env python3
"""Conan recipe for enet 1.3.18 — Reliable UDP networking library (pure C, autotools).

enet is a relatively thin, simple and robust network communication layer on top
of UDP. It provides features like connection management, reliable sequenced
packet delivery, channels, bandwidth/throttling management, and latency simulation.

Upstream: https://github.com/lsalzman/enet  (MIT license)

OHOS adaptation:
  - The GitHub archive ships only configure.ac (no pre-generated configure),
    so `autoreconf --install` runs in build() to generate configure +
    config.guess/sub.  automake/1.18 (tool_requires) ships unpatched
    config.guess/config.sub (2024-07-27, no HarmonyOS case), so build()
    applies E007 via scripts/patch-autotools-ohos.pl after autoreconf.
  - E178: the CI Worker has the autoconf 2.72 suite under /data/service/hnp/bin
    but no automake/aclocal/libtoolize on PATH.  Rather than patching around
    the broken partial automake on PATH, build_requirements() pulls in complete
    automake/1.18 + libtool/2.5.4 via the build profile (same pattern as afuse,
    aircrack-ng, adcli, air-quality-sensor — R33-safe, no hardcoded paths).
  - HMDFS umask 077 fix (E011/E129): configure's config.status creates temp
    directories with `umask 077` which yields drwx--S--- (not writable by owner
    under HMDFS UID mapping).  We sed umask 077→022 in the generated configure
    before running it.  This is a build-step fix (generated file, not source).
"""
import glob as _glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class EnetConan(ConanFile):
    name = "enet"
    version = "1.3.18"
    description = ("Reliable UDP networking library (thin layer over UDP with channels, "
                   "reliability, ordering, bandwidth throttling)")
    license = "MIT"
    homepage = "https://github.com/lsalzman/enet"
    url = "https://github.com/lsalzman/enet"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        pass  # enet has no external dependencies (pure C, POSIX sockets only)

    def build_requirements(self):
        # E178: the GitHub archive ships configure.ac only (no pre-generated
        # configure), so build() runs `autoreconf --install` to bootstrap it.
        # The CI Worker has the autoconf 2.72 suite under /data/service/hnp/bin
        # but no automake/aclocal/libtoolize on PATH, so pull in complete
        # automake + libtool via the build profile (afuse / aircrack-ng /
        # adcli / air-quality-sensor pattern — R33-safe, no hardcoded paths).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # GitHub archive has no pre-generated configure; bootstrap it.
        # automake/1.18 (tool_requires) ships unpatched config.guess/config.sub
        # (2024-07-27, no HarmonyOS case) — patched post-autoreconf below (E007).
        self.run("autoreconf --install --verbose", cwd=self.source_folder)

        # E007: patch generated config.guess/config.sub for HarmonyOS recognition.
        # automake/1.18 ships the 2024-07-27 versions which don't know OHOS.
        # CI runs from a Conan cache copy where self.recipe_folder does NOT point
        # back to the repo tree, so locate the patch script via CI_REPO_ROOT
        # (set by ci/conan/build_and_test.sh) instead of relative path traversal.
        _cg = os.path.join(self.source_folder, "config.guess")
        _cs = os.path.join(self.source_folder, "config.sub")
        _repo = os.environ.get("CI_REPO_ROOT", "")
        _patch_script = os.path.join(_repo, "scripts", "patch-autotools-ohos.pl") if _repo else ""
        if _patch_script and os.path.isfile(_patch_script) and os.path.isfile(_cg):
            self.run(f'perl "{_patch_script}" "{_cg}" "{_cs}"', cwd=self.source_folder)
        elif os.path.isfile(_cg) and os.path.isfile(_cs):
            # Fallback: in-process Python patch (addrwatch pattern) when the perl
            # script is unavailable (local builds without CI_REPO_ROOT).
            self.output.info("E007: patch-autotools-ohos.pl not found, applying Python fallback")
            self._patch_config_guess_python(_cg)
            self._patch_config_sub_python(_cs)

        # E011/E129: HMDFS umask 077 makes config.status temp dirs unwritable.
        # Fix in the generated configure (build-step, not a source patch).
        configure_path = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure_path, "umask 077", "umask 022")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def _patch_config_guess_python(self, cg_path):
        """In-process fallback: add HarmonyOS recognition to config.guess (E007)."""
        with open(cg_path, "r") as f:
            content = f.read()
        changed = False
        # 1. Add __OHOS__ LIBC detection after __ANDROID__
        if "__OHOS__" not in content:
            old = "#if defined(__ANDROID__)\n    LIBC=android"
            new = ("#if defined(__ANDROID__)\n    LIBC=android\n"
                   "#elif defined(__OHOS__)\n    LIBC=ohos")
            if old in content:
                content = content.replace(old, new, 1)
                changed = True
            else:
                self.output.warn("  [warn] Could not find __ANDROID__/LIBC=android in config.guess")
        # 2. Add HarmonyOS case block before NetBSD
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
            else:
                self.output.warn("  [warn] Could not find NetBSD insertion point in config.guess")
        if changed:
            with open(cg_path, "w") as f:
                f.write(content)
            self.output.info("  [ok] Python fallback patched config.guess for OHOS")

    def _patch_config_sub_python(self, cs_path):
        """In-process fallback: add ohos triplet to config.sub (E007)."""
        import re
        with open(cs_path, "r") as f:
            content = f.read()
        changed = False
        # 1. Add ohos-linux triplet after android-linux
        if "ohos-linux" not in content:
            pattern = r'(android-linux\)\s*\n\s*basic_machine=\$field1-unknown\s*\n\s*basic_os=linux-android\s*\n\s*;;\s*\n)'
            replacement = r'\1\tohos-linux)\n\tbasic_machine=$field1-unknown\n\tbasic_os=linux-ohos\n\t;;\n'
            content, count = re.subn(pattern, replacement, content)
            if count > 0:
                changed = True
            else:
                self.output.warn("  [warn] Could not find android-linux in config.sub")
        # 2. Add ohos* to OS type list
        if "ohos*" not in content:
            content = content.replace("gnu* | android*", "gnu* | android* | ohos*", 1)
            changed = True
        # 3. Add linux-ohos to kernel-OS validation list
        if "linux-ohos" not in content:
            content, count = re.subn(r'(linux-uclibc[\*/-]?\s*\))', r'\1| linux-ohos*)', content)
            if count > 0:
                changed = True
            else:
                self.output.warn("  [warn] Could not find linux-uclibc pattern in config.sub")
        if changed:
            with open(cs_path, "w") as f:
                f.write(content)
            self.output.info("  [ok] Python fallback patched config.sub for OHOS")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Remove libtool .la wrappers (Conan manages linkage)
        for _la in _glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        self.cpp_info.libs = ["enet"]
