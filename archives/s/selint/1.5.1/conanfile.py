#!/usr/bin/env python3
"""Conan recipe — selint 1.5.1 (autotools, CLI application).

SELint is a static analysis linter for SELinux policy source files.  It builds
a single `selint` executable (bin_PROGRAMS) from an Autotools project whose
release tarball ships a pre-generated `configure`, `lex.c`, `parse.c` and
`parse.h` (no autoreconf needed on OHOS).

Runtime dependencies (linked into the selint binary, both static so the
installed executable is self-contained and runs without any env):
  - libconfuse (confuse/3.4, shared=False by default) — cfg_init etc.
  - musl-fts (musl-fts/1.2.7, forced shared=False)   — fts_open/read/set/close;
    OHOS/musl ships no <fts.h>, needed for recursive policy scanning.

Build/test-only dependencies:
  - uthash/2.3.0  — header-only, AC_CHECK_HEADER([uthash.h]).
  - check/0.15.2  — Check unit-test framework, declared `test_requires`; only the
                    `tests/` suite links it (via PKG_CHECK_MODULES @CHECK_LIBS@),
                    never the selint binary.
  - flex/bison    — the .l/.y sources are already shipped pre-generated, but are
                    declared tool_requires as a defensive guard so a timestamp
                    change can never abort the build.

OHOS adaptations (see knowledge graph E011/E052/E543):
  - configure's embedded config.status template creates its temp dir with
    `umask 077 && mktemp/mkdir`; HMDFS setgid semantics make that dir
    unwritable (subs1.awk Permission denied).  We strip the umask wrapper.
  - The ohos-aarch64 profile buildenv points SHELL/CONFIG_SHELL at the hnp
    bash, whose getcwd fails inside an HMDFS build dir; we force /bin/sh via an
    inline env prefix on the configure command.
  - Single job (-j1): parallel make hits HMDFS jobserver fifo EPERM (E074).
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout


class SelintConan(ConanFile):
    name = "selint"
    version = "1.5.1"
    description = "SELint - static analysis linter for SELinux policy source files"
    license = "Apache-2.0"
    homepage = "https://github.com/SELinuxProject/selint"
    url = ""  # CI fills this

    # CLI tool, not a library (R38: commands.json declared at software level)
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    # musl-fts defaults to shared=True, which would leave the installed
    # bin/selint with a DT_NEEDED libfts.so.0 that only resolves under the
    # conanrun env (the L2 smoke test runs the binary bare).  Linking it
    # statically makes the CLI self-contained — like confuse, which already
    # defaults to shared=False.
    default_options = {"musl-fts/*:shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Linked into the selint binary (AC_SEARCH_LIBS([cfg_init], [confuse])).
        self.requires("confuse/3.4")
        # Header-only, compile-time only.
        self.requires("uthash/2.3.0")
        # musl (OHOS) has no <fts.h>/libfts — selint's recursive scan uses
        # fts_open/fts_read/fts_set/fts_close.  musl-fts supplies the header +
        # library (nnn/libselinux/afsctool precedent).  AutotoolsDeps wires its
        # -I/-L/-lfts into configure/make.
        self.requires("musl-fts/1.2.7")
        # Check is used ONLY by the tests/ suite (make check), never by the
        # selint binary.  test_requires puts it in the TEST context, so
        # AutotoolsDeps (which reads dependencies.host) never adds -lcheck to
        # the global LIBS — otherwise the packaged selint binary would acquire
        # a spurious DT_NEEDED libcheck.so the consumer cannot resolve
        # (teseq/1.1.1 precedent).  PkgConfigDeps still emits check.pc for
        # configure's PKG_CHECK_MODULES([CHECK], [check >= 0.11.0]).
        self.test_requires("check/0.15.2")

    def build_requirements(self):
        # Defensive: the release tarball ships pre-generated lex.c/parse.c that
        # are newer than lex.l/parse.y, so make will not regenerate them.  These
        # are declared only so an unexpected regeneration can never fail the
        # build for a missing tool.
        self.tool_requires("flex/2.6.4")
        self.tool_requires("bison/3.8.2")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"selint is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # AutotoolsDeps: feed confuse's -I/-L/-l and uthash's -I into
        # configure/make (AC_SEARCH_LIBS + AC_CHECK_HEADER).
        deps = AutotoolsDeps(self)
        deps.generate()
        # PkgConfigDeps: generate check.pc so configure's
        # PKG_CHECK_MODULES([CHECK], [check >= 0.11.0]) resolves for the tests.
        pc = PkgConfigDeps(self)
        pc.generate()
        tc = AutotoolsToolchain(self)
        tc.generate()
        # OHOS loader has no default search path for conan-cached shared libs.
        # check/0.15.2 (test_requires) is shipped shared, and the 18 test
        # programs link it dynamically, so `make check` needs its lib dir at
        # runtime; configure's conftest likewise needs any shared dep resolvable
        # ("Error loading shared library ...").  Prepend every dependency lib
        # dir to LD_LIBRARY_PATH (aaphoto precedent).
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        # Check's open_tmp_file (check_msg.c) probes TEMP first, then the musl
        # P_tmpdir ("/tmp" — read-only on OHOS, E002/E011), and only then TMPDIR
        # (which is unreachable because P_tmpdir is always defined on musl).
        # Give both a guaranteed-writable temp root under the build folder so
        # all 18 check_* programs can create their IPC temp file (teseq precedent).
        check_tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(check_tmp, exist_ok=True)
        env.define("TEMP", check_tmp)
        env.define("TMPDIR", check_tmp)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        # E011/E052: HMDFS setgid makes configure's `umask 077 && mktemp/mkdir`
        # temp dir unwritable; strip the umask wrapper (confuse/3.4 precedent).
        self._patch_configure_umask()
        autotools = Autotools(self)
        if self.settings.os == "OHOS":
            # E543: profile buildenv points SHELL/CONFIG_SHELL at the hnp bash
            # whose getcwd fails on HMDFS; force /bin/sh via inline env prefix
            # (confuse/3.4 / abx precedent).  No autoreconf — release tarball
            # ships a ready configure.
            configure_script = os.path.join(self.source_folder, "configure")
            command = (
                "CONFIG_SHELL=/bin/sh SHELL=/bin/sh "
                + shlex.join(["/bin/sh", configure_script])
            )
            if autotools._configure_args:
                command = f"{command} {autotools._configure_args}"
            self.run(command, cwd=self.build_folder, env="conanbuild")
        else:
            autotools.configure()

        # E074: single job — parallel make hits HMDFS jobserver fifo EPERM.
        autotools.make(args=["-j1"])

        # Run the upstream Check test suite (tests/: 18 check_* programs +
        # functional/ bats end-to-end).  Non-zero exit is recorded, not fatal, so
        # every test still builds+runs and failures can be attributed per-class
        # (R51 requires the real count; see notes.md / MANIFEST.yml).
        try:
            autotools.make(target="check", args=["-j1"])
        except Exception as exc:  # noqa: BLE001 — failure is recorded for attribution
            self.output.warning(
                f"make check reported failures (logs kept for attribution): {exc}"
            )

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Standalone executable; no library info to export.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    def _patch_configure_umask(self):
        # E011/E052: autoconf's embedded config.status template does
        # `tmp=`(umask 077 && mktemp -d "./confXXXXXX")`` and
        # `(umask 077 && mkdir "$tmp")`.  Under HMDFS setgid semantics the
        # resulting drwx--S--- dir is not writable by its owner (subs1.awk
        # Permission denied).  Drop the umask wrapper, keep real mktemp/mkdir.
        path = os.path.join(self.source_folder, "configure")
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
        patched = content.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`',
        ).replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
        if patched != content:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(patched)
