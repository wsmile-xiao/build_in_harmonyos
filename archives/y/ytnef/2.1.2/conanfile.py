#!/usr/bin/env python3
"""Conan recipe — ytnef 2.1.2 (Yerase's TNEF Stream Reader) for HarmonyOS PC.

Builds `libytnef` (the TNEF / winmail.dat decoding library) plus the three
upstream command line tools `ytnef`, `ytnefprint` and `ytnefprocess`.

Upstream is an autotools project, but the release snapshot used here is a
git-archive (`codeload.github.com/.../v2.1.2`) which ships only
`configure.ac` / `Makefile.am` / `autogen.sh` / `travis-build.sh` — there is no
generated `configure`.  The recipe therefore bootstraps the build with
`autoreconf -fi`, pulling `automake` and `libtool` in as `tool_requires`
(the OHOS build hosts provide only the autoconf suite, no automake/libtoolize).

OHOS adaptations (details in notes.md):
  * E007 — GNU `config.guess` has no HarmonyOS branch, so it cannot derive the
    `aarch64-unknown-linux-ohos` triplet (`uname -s` reports "HarmonyOS").
    `config.guess` / `config.sub` are produced by `autoreconf`, hence they do
    not exist in the pristine tarball and cannot be expressed as a conandata
    patch — they are adjusted at build time instead.  The explicit
    `--build=`/`--host=` triplets are deliberately NOT used (E205/R1).
  * E074 — every `make` invocation runs with `-j1`: HMDFS forbids the make
    jobserver FIFO ("mkfifo ... Operation not permitted").
  * R51  — the upstream integration suite `test-data/test.sh` is executed on
    every build, so the CI re-runs the upstream assertions.
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (get, apply_conandata_patches, copy,
                               export_conandata_patches)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


# ── E007: HarmonyOS support for the autotools helper scripts ────────────────
#
# Injected in front of the NetBSD branch of the `uname` dispatch table, this
# block lets config.guess derive `aarch64-unknown-linux-ohos` straight from
# `uname` without invoking the compiler probe.  Skipping the probe matters on
# HarmonyOS: it creates its scratch directory with `mktemp -d` under
# `umask 077`, and HMDFS turns that 0700 directory into an unwritable
# `drwx--S---` one (same family of symptoms as E114).
_CONFIG_GUESS_HARMONYOS_BLOCK = (
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

_CONFIG_GUESS_NETBSD_ANCHOR = re.compile(r"(?m)^([ \t]+\*:NetBSD:\*:\*\)[ \t]*\n)")


def _inject_harmonyos_config_guess(path):
    """Teach the generated `config.guess` to recognise HarmonyOS (E007).

    Returns True when the file was modified.
    """
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if "linux-ohos" in text:
        return False
    patched, count = _CONFIG_GUESS_NETBSD_ANCHOR.subn(
        _CONFIG_GUESS_HARMONYOS_BLOCK + r"\1", text, count=1)
    if count == 0:
        raise ConanException(
            "E007: could not find the NetBSD branch in the generated "
            "config.guess; the HarmonyOS triplet cannot be derived. "
            "config.guess=%s" % path)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(patched)
    return True


def _ensure_ohos_config_sub(path):
    """Make sure the generated `config.sub` accepts the `linux-ohos` triplet.

    automake/1.18 already ships an OHOS aware config.sub; this only fills the
    gaps should a different toolchain version be resolved.  Returns True when
    the file was modified.
    """
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if "ohos" in text:
        return False

    changed = False
    # `ohos-linux` short form -> basic_os=linux-ohos
    text, n = re.subn(
        r"(?m)^([ \t]*android-linux\)[ \t]*\n"
        r"([ \t]*basic_machine=\$field1-unknown[ \t]*\n)"
        r"([ \t]*basic_os=linux-android[ \t]*\n)"
        r"([ \t]*;;[ \t]*\n))",
        r"\1\t\tohos-linux)\n\t\tbasic_machine=$field1-unknown\n"
        r"\t\tbasic_os=linux-ohos\n\t\t;;\n",
        text, count=1)
    changed = changed or bool(n)
    # `ohos*` in the OS type list
    text, n = re.subn(r"(gnu\*\s*\|\s*android\*)", r"\1 | ohos*", text, count=1)
    changed = changed or bool(n)
    # `linux-ohos*` in the kernel-OS validation list
    text, n = re.subn(r"(linux-uclibc\*[/-]?\s*)\)", r"\1| linux-ohos*)",
                      text, count=1)
    changed = changed or bool(n)

    if not changed:
        raise ConanException(
            "E007: config.sub neither knows about OHOS nor matches any known "
            "anchor, refusing to continue with an unrecognised triplet "
            "(config.sub=%s)" % path)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return True


# ── Conan recipe ────────────────────────────────────────────────────────────

class YtnefConan(ConanFile):
    name = "ytnef"
    version = "2.1.2"
    description = ("Yerase's TNEF Stream Reader: library plus command line "
                   "tools to decode MS-TNEF (winmail.dat) streams")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/Yeraze/ytnef"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # dependency free: libc + libtool only (configure.ac has no
        # AC_CHECK_LIB / PKG_CHECK_MODULES at all)
        pass

    def build_requirements(self):
        # The git-archive snapshot has no `configure`; bootstrap it with
        # autoreconf.  The OHOS build hosts ship autoconf/m4 but no
        # automake/aclocal/libtoolize, so those come from the registry.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        # R32: settings.os must be checked against ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ytnef is only supported on Linux/OHOS, not " + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.get_safe("fPIC"):
            tc.extra_cflags.append("-fPIC")
        # R26 is not triggered here: libytnef is not a system library name
        # (there is no /lib/libytnef.so on OHOS), so the linkage flavour stays
        # a plain consumer option instead of a forced static build.
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate()

    # ── build helpers ───────────────────────────────────────────────────

    def _bootstrap_configure(self):
        """Run `autoreconf -fi` in a stable, single-Perl environment.

        The Conan `automake` package ships `aclocal`/`automake` wrappers whose
        shebang points at the *system* perl, while libtool requires the Conan
        Perl data files, and Conan's own `autoreconf`/`autoconf` wrappers run
        whatever `$PERL` resolves to.  Conan's VirtualBuildEnv points
        `PERL`/`PERL5LIB` at its own (threaded, different ABI) Perl, which
        makes the two Perl flavours collide:

            Can't load Cwd.so for module Cwd: Permission denied
            ... Perl_my_cxt_init: symbol not found

        Pin one Perl (the system one) for the whole bootstrap and hand it the
        Conan automake data directory, which is where `Automake/Config.pm`
        lives.  `m4/` is required because configure.ac declares
        `AC_CONFIG_MACRO_DIR([m4])`.
        """
        self.run(
            'mkdir -p m4 && '
            '( if [ -n "${AUTOMAKE:-}" ]; then '
            '    _am_pkg=$(dirname "$(dirname "$AUTOMAKE")"); '
            '    for _d in "$_am_pkg"/share/automake-*; do '
            '      [ -d "$_d" ] && PERL5LIB="$_d"; '
            '    done; '
            '  fi; '
            '  unset PERL; '
            '  autoreconf -fi ) && '
            # E490: keep the freshly generated autotools helpers executable -
            # some HarmonyOS adaptation paths carry source content across
            # without the mode bits and `configure` then cannot be executed.
            'chmod +x configure config.guess config.sub install-sh missing '
            'compile depcomp 2>/dev/null || true',
            cwd=self.source_folder, env="conanbuild")

    def _harden_configure_tmpdir(self, configure_path):
        """E114: `umask 077 && mktemp -d` creates an unusable temp dir here.

        On HMDFS a directory created with mode 0700 ends up as `drwx--S---`,
        which not even its owner can write into, so the `config.status` helper
        generation step dies with

            ./config.status: line 819: ./confmAOPle/subs1.awk: Permission denied

        The scratch directory lives inside the private build tree anyway, so
        dropping the hardened umask is safe.  Same remediation as
        archives/a/abiword-plugin-*/3.0.8/conanfile.py and
        archives/a/abook/0.6.1/conanfile.py.

        The generated `configure` is patched (rather than `config.status`)
        because `config.status` is emitted from a template embedded in
        `configure`, so fixing the source covers both.  Returns True when the
        script was modified.
        """
        with open(configure_path, encoding="utf-8") as fh:
            text = fh.read()
        fixed = text.replace('(umask 077 && mktemp -d "./confXXXXXX")',
                             '(mktemp -d "./confXXXXXX")')
        fixed = fixed.replace('(umask 077 && mkdir "$tmp")', '(mkdir "$tmp")')
        if fixed == text:
            return False
        with open(configure_path, "w", encoding="utf-8") as fh:
            fh.write(fixed)
        return True

    def _apply_harmonyos_autotools_fix(self):
        """E007: complete the autotools helper scripts for HarmonyOS."""
        config_guess = os.path.join(self.source_folder, "config.guess")
        config_sub = os.path.join(self.source_folder, "config.sub")
        for script in (config_guess, config_sub):
            if not os.path.exists(script):
                raise ConanException(
                    "E007: %s missing after `autoreconf -fi`" % script)
        if _inject_harmonyos_config_guess(config_guess):
            self.output.info("E007: injected the HarmonyOS branch into config.guess")
        if _ensure_ohos_config_sub(config_sub):
            self.output.info("E007: completed the linux-ohos support in config.sub")
        # content based verification - `configure` below exercises them for real
        with open(config_guess, encoding="utf-8") as fh:
            if "linux-ohos" not in fh.read():
                raise ConanException(
                    "E007: config.guess still has no HarmonyOS triplet support")
        with open(config_sub, encoding="utf-8") as fh:
            if "ohos" not in fh.read():
                raise ConanException(
                    "E007: config.sub still has no OHOS triplet support")

    def _run_upstream_tests(self):
        """R51: run the upstream integration suite (test-data/test.sh).

        `test.sh` extracts every bundled fixture with the freshly built
        binaries, byte-compares the result against test-data/results/ and
        checks five specific ytnefprint fields plus one malformed-input
        robustness case.  It reaches the binaries through `../ytnef/ytnef`,
        so it has to run with both the built tree and the fixtures under a
        single directory - Conan builds out of source, hence the mirror below.
        """
        if os.path.realpath(self.build_folder) != os.path.realpath(self.source_folder):
            copy(self, "*", src=os.path.join(self.source_folder, "test-data"),
                 dst=os.path.join(self.build_folder, "test-data"))
        self.run('cd test-data && rm -rf data && bash ./test.sh',
                 cwd=self.build_folder, env="conanbuild")

    # ── conan entry points ──────────────────────────────────────────────

    def build(self):
        self._bootstrap_configure()
        self._apply_harmonyos_autotools_fix()
        if self._harden_configure_tmpdir(
                os.path.join(self.source_folder, "configure")):
            self.output.info("E114: dropped the hardened umask from configure")

        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make would need a jobserver FIFO, which HMDFS rejects
        autotools.make(args=["-j1"])
        # R51: upstream integration suite
        self._run_upstream_tests()

    def package(self):
        autotools = Autotools(self)
        # E074: keep -j1 here as well, otherwise make tries to open its
        # jobserver FIFO (forbidden on HMDFS) even for `make install`
        autotools.install(args=["-j1"])
        # Drop the libtool *.la wrappers: they embed absolute build paths and
        # are useless for consumers.
        libdir = os.path.join(self.package_folder, "lib")
        for name in os.listdir(libdir) if os.path.isdir(libdir) else []:
            if name.endswith(".la"):
                os.remove(os.path.join(libdir, name))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["ytnef"]
        self.cpp_info.includedirs = ["include"]
        # ytnef / ytnefprint / ytnefprocess are command line tools (R38)
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
