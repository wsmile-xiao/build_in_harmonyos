#!/usr/bin/env python3
"""Conan recipe for bwm-ng 0.6.3 — Autotools CLI.

bwm-ng (Bandwidth Monitor Next Generation) is a small live bandwidth monitor
for Linux / BSD. Upstream ships Autotools sources (configure.in + Makefile.am)
but no test suite: no `tests/` directory and no TESTS= in Makefile.am, so
automake's default `make check` is a no-op.

OHOS adaptations:
    - GitHub archive has no pre-generated configure; build() runs autoreconf.
      CI has autoconf but not automake/libtoolize — pull them via tool_requires
      (E178, same pattern as enet/torsocks). No hardcoded host paths.
    - E007: after autoreconf, patch config.guess/config.sub so HarmonyOS is
      detected as aarch64-unknown-linux-ohos. Do not pass --build/--host (R15).
    - E114: generated configure uses `umask 077 && mktemp -d`; on HMDFS that
      yields an unwritable temp dir. Relax umask 077 → 022 before configure.
    - Disable curses/ncurses; use --with-proc-netdev; static-link (R26).
"""
import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get,
    apply_conandata_patches,
    export_conandata_patches,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BwmNgConan(ConanFile):
    name = "bwm-ng"
    version = "0.6.3"
    description = (
        "bwm-ng (Bandwidth Monitor Next Generation) — small live console "
        "bandwidth monitor for Linux/BSD."
    )
    license = "GPL-2.0-only"
    homepage = "https://www.gropp.org/?id=projects&sub=bwm-ng"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        pass

    def build_requirements(self):
        # Archive ships configure.in only. Worker has autoconf, not automake.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)
        # In-source autotools: configure is generated next to configure.in.
        self.folders.build = "."

    def source(self):
        src = dict(self.conan_data["sources"])
        src.setdefault("filename", "bwm-ng-0.6.3.tar.gz")
        get(self, **src, strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R15/E007: never pass --build/--host; patched config.guess detects OHOS.
        tc.configure_args = [
            a for a in tc.configure_args
            if not str(a).startswith("--build=") and not str(a).startswith("--host=")
        ]
        # R26: static CLI binary, no runtime NEEDED libs.
        tc.extra_ldflags.append("-static")
        tc.configure_args.append("--without-curses")
        tc.configure_args.append("--without-ncurses")
        tc.configure_args.append("--with-proc-netdev")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Modern autoreconf (>=2.70) looks for configure.ac, not configure.in.
        cfgin = Path(self.source_folder) / "configure.in"
        cfgac = Path(self.source_folder) / "configure.ac"
        if cfgin.exists() and not cfgac.exists():
            cfgac.write_text(cfgin.read_text())

        self.run("autoreconf -v -i -f", cwd=self.source_folder)
        self._apply_e007()

        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            # E114: HMDFS + umask 077 → unwritable config.status temp dir.
            replace_in_file(self, configure_path, "umask 077", "umask 022", strict=False)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # Upstream has no TESTS=; automake emits a no-op check that exits 0.
        autotools.make(target="check")

    def _config_script_pairs(self):
        root = self.source_folder
        return [
            (os.path.join(root, "config.guess"), os.path.join(root, "config.sub")),
            (
                os.path.join(root, "build-aux", "config.guess"),
                os.path.join(root, "build-aux", "config.sub"),
            ),
        ]

    def _apply_e007(self):
        """Patch generated config.guess/config.sub for HarmonyOS (E007/R15)."""
        pairs = [
            (cg, cs) for cg, cs in self._config_script_pairs()
            if os.path.isfile(cg) and os.path.isfile(cs)
        ]
        if not pairs:
            self.output.warning("E007: config.guess/config.sub not found after autoreconf")
            return

        repo = os.environ.get("CI_REPO_ROOT", "")
        script = os.path.join(repo, "scripts", "patch-autotools-ohos.pl") if repo else ""
        for cg, cs in pairs:
            if script and os.path.isfile(script):
                self.run(f'perl "{script}" "{cg}" "{cs}"', cwd=self.source_folder)
            else:
                self.output.info("E007: patch-autotools-ohos.pl not found, Python fallback")
                self._patch_config_guess_python(cg)
                self._patch_config_sub_python(cs)

    def _patch_config_guess_python(self, cg_path):
        with open(cg_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        changed = False
        if "__OHOS__" not in content:
            old = "#if defined(__ANDROID__)\n    LIBC=android"
            new = (
                "#if defined(__ANDROID__)\n    LIBC=android\n"
                "#elif defined(__OHOS__)\n    LIBC=ohos"
            )
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
            with open(cg_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.output.info("E007: patched config.guess for HarmonyOS")

    def _patch_config_sub_python(self, cs_path):
        import re

        with open(cs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        changed = False
        if "ohos-linux" not in content:
            pattern = (
                r'(android-linux\)\s*\n\s*basic_machine=\$field1-unknown\s*\n'
                r'\s*basic_os=linux-android\s*\n\s*;;\s*\n)'
            )
            replacement = (
                r'\1\tohos-linux)\n\tbasic_machine=$field1-unknown\n'
                r'\tbasic_os=linux-ohos\n\t;;\n'
            )
            content, count = re.subn(pattern, replacement, content)
            if count > 0:
                changed = True
        if "ohos*" not in content:
            new_content = content.replace("gnu* | android*", "gnu* | android* | ohos*", 1)
            if new_content != content:
                content = new_content
                changed = True
        if "linux-ohos" not in content:
            content, count = re.subn(r'(linux-uclibc[\*/-]?\s*\))', r'\1| linux-ohos*)', content)
            if count > 0:
                changed = True
        if changed:
            with open(cs_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.output.info("E007: patched config.sub for HarmonyOS")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        import glob

        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            for pattern in ("*.la", "*.dylib"):
                for f in glob.glob(os.path.join(lib_dir, pattern)):
                    os.remove(f)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
