#!/usr/bin/env python3
"""Conan recipe for ogg 1.1.1 — Ogg multimedia container library (2004 line).

This is the old `ogg` package-name line (xiph/ogg tag v1.1.1, pre-autotools
modernisation). It is fully independent from the newer `libogg` package line
under archives/l/libogg/ (1.3.5-1.3.6.1, CMake): same upstream project,
different package name, different version line, both may coexist in the
registry.

Upstream facts (from the v1.1.1 tag tarball):
  - 2004-era autotools: `configure.in` (not configure.ac), no pre-generated
    `configure`, no bundled config.guess/config.sub, AM_PROG_LIBTOOL /
    AM_CONFIG_HEADER (obsolete spellings).
  - Pure C, zero third-party dependencies (only libc).
  - Library libogg + two self-test programs (test_bitwise / test_framing)
    wired into `make check` by src/Makefile.am.

OHOS adaptations (all same as the gate-passing bwm-ng 0.6.3 recipe):
  - E178: the worker has autoconf but no automake/aclocal/libtoolize —
    pull automake/1.18 + libtool/2.5.4 via tool_requires.
  - autoreconf >= 2.70 only reads configure.ac — copy configure.in to
    configure.ac before bootstrapping (bwm-ng precedent).
  - autoreconf -fi installs modern (2024) config.guess/config.sub from the
    conan automake/libtool packages, so the official perl patcher works
    (new-style scripts with GUESS=; no need for the E564 old-style anchors).
  - E007/R15: patch config.guess/config.sub for HarmonyOS; never pass
    --build/--host.
  - E114: relax `umask 077` to `umask 022` in the generated configure so
    config.status temp dirs stay writable on HMDFS.
  - E074: parallel make hits the HMDFS jobserver fifo EPERM — use -j1.
  - Upstream `make check` runs test_bitwise (16 assertions) and test_framing
    (14 assertions); both executed during conan create.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OggConan(ConanFile):
    name = "ogg"
    version = "1.1.1"
    description = "Ogg multimedia container library (xiph/ogg v1.1.1, old package line)"
    license = "BSD-3-Clause"
    homepage = "https://xiph.org/ogg/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # 2004-era libtool (1.5.x) only knows gcc-style dependency tracking;
        # the modern libtool installed by autoreconf handles clang fine.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ogg 1.1.1 is only supported on Linux/OHOS, not "
                + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload.github.com tar.gz links download without a filename
        # extension hint, so conan's get() sniffs the bytes and misdetects
        # the gzip stream as a zip — pass an explicit .tar.gz filename
        # (bwm-ng 0.6.3 precedent, same codeload URL form).
        src = dict(self.conan_data["sources"])
        src.setdefault("filename", "ogg-1.1.1.tar.gz")
        get(self, **src, strip_root=True)

    def build_requirements(self):
        # The 2004 tarball ships no pre-generated configure (and no
        # config.guess/config.sub): bootstrap with autoreconf -fi. The OHOS
        # worker has the autoconf suite but lacks automake/aclocal/libtoolize
        # (E178), same as bwm-ng 0.6.3 / afuse 0.5.0 / aribb24 1.0.4.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # R15/E007: never pass --build/--host; the patched config.guess
        # detects HarmonyOS as aarch64-unknown-linux-ohos natively.
        tc.configure_args = [
            a for a in tc.configure_args
            if not str(a).startswith("--build=") and not str(a).startswith("--host=")
        ]
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder

        # Modern autoreconf (>= 2.70) only reads configure.ac — the 2004
        # tarball only ships configure.in (bwm-ng 0.6.3 precedent).
        cfg_in = os.path.join(src, "configure.in")
        cfg_ac = os.path.join(src, "configure.ac")
        if os.path.isfile(cfg_in) and not os.path.isfile(cfg_ac):
            with open(cfg_in, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            with open(cfg_ac, "w", encoding="utf-8") as f:
                f.write(text)

        # Bootstrap: generates configure + installs modern (2024)
        # config.guess/config.sub/ltmain.sh from the tool_requires packages.
        self.run("autoreconf -fi", cwd=src)

        # E007: patch the freshly installed config.guess/config.sub so
        # HarmonyOS (uname -s = HarmonyOS, HongMeng kernel) is detected as
        # aarch64-unknown-linux-ohos. The scripts installed by autoreconf are
        # new-style (GUESS= variable), so the official perl patcher applies
        # cleanly; the python fallback covers machines without the repo
        # checkout (CI passes CI_REPO_ROOT, see bwm-ng 0.6.3).
        self._patch_config_scripts()

        # E114: HMDFS + `umask 077 && mktemp -d` yields an unwritable
        # drwx--S--- temp dir — relax to 022 before configure runs.
        configure_path = os.path.join(src, "configure")
        if os.path.isfile(configure_path):
            replace_in_file(self, configure_path, "umask 077", "umask 022",
                            strict=False)

        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make hits the HMDFS jobserver fifo EPERM.
        autotools.make(args=["-j1"])
        # Upstream test suite: src/Makefile.am wires `check:` to run
        # ./test_bitwise and ./test_framing (16 + 14 assertions).
        autotools.make(target="check", args=["-j1"])

    def _config_script_pairs(self):
        root = self.source_folder
        return [
            (os.path.join(root, "config.guess"), os.path.join(root, "config.sub")),
            (os.path.join(root, "build-aux", "config.guess"),
             os.path.join(root, "build-aux", "config.sub")),
        ]

    def _patch_config_scripts(self):
        """E007: HarmonyOS detection for config.guess/config.sub."""
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
        # Conan 2 copy() has no delete= argument; remove libtool *.la wrappers
        # (same cleanup as aribb24/a52dec recipes).
        import glob
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)

    def package_info(self):
        self.cpp_info.libs = ["ogg"]
        self.cpp_info.set_property("cmake_file_name", "Ogg")
        self.cpp_info.set_property("cmake_target_name", "Ogg::ogg")
        self.cpp_info.set_property("pkg_config_name", "ogg")
