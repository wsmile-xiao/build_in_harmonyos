#!/usr/bin/env python3
"""Conan recipe — hivex 1.3.24 (Autotools).

hivex is a self-contained C library for reading and writing Windows Registry
"hive" binary files (upstream libguestfs/hivex, licence LGPL-2.1-only — the
upstream LICENSE states "LGPL v2.1, but not later versions").  It backs
libguestfs / virt-v2v registry access; the two upstream command line tools
hivexsh and hivexml are built from the same tree.

Build facts (audited from the hivex-1.3.24 tarball, 741279 bytes,
sha256 a52fa45cecc9a78adb2d28605d68261e4f1fd4514a778a5473013d2ccc8a193c):
  * Autotools project.  The tarball ships the pre-generated `configure`
    plus a bundled gnulib, so no autoreconf is run and no autoconf/automake
    version constraint leaks into the build.
  * Hard configure requirements: an ISO C compiler and the Perl programs
    `pod2man`/`pod2text` (AC_CHECK_PROG + AC_MSG_ERROR — they render the
    installed hivex.3 man page).  Both are provided by the worker image in
    /data/service/hnp/bin, which the ohos-aarch64 profile puts on PATH.
  * The library itself links nothing external: libhivex.la is built from
    gnulib + lib/*.c only.  readline (hivexsh line editing) and libxml2
    (hivexml) are optional and detected at configure time.
  * Upstream test suite: `make check` compiles and runs exactly ONE C test
    registered in lib/Makefile.am (`check_PROGRAMS = test-just-header`,
    `TESTS = test-just-header`).  It is a real functional test:
    lib/test-just-header.c hivex_open()s the bundled images/minimal registry
    image and fails if the handle is NULL.  The Perl/Python/Ruby/OCaml test
    suites live in the language-binding subdirs, which are disabled here.

OHOS notes (native build, host = build = OHOS/aarch64, profile ohos-aarch64):
  * E007: GNU config.guess/config.sub know nothing about HarmonyOS.  Because
    this is a *native* build the profile passes no --host, so configure falls
    back to running build-aux/config.guess, which answers "unable to guess
    system type" and aborts configure with "cannot guess build type; you must
    specify one".  Faking it with --build/--host is forbidden (it would make
    autoconf believe it is cross compiling, skipping every AC_RUN_IFELSE and
    silently producing a wrong config.h), so the repository's
    scripts/patch-autotools-ohos.pl patch is applied instead: it adds the
    HarmonyOS branch to config.guess and accepts the linux-ohos triplet in
    config.sub, yielding the standard aarch64-unknown-linux-ohos.
  * Language bindings disabled (--disable-ocaml/--disable-perl/
    --disable-python/--disable-ruby).  OCaml is not installed on the worker
    (and is only needed for git checkouts anyway); the remaining bindings
    would drag a second language runtime into a pure C library port.
  * --disable-nls neutralises AM_GNU_GETTEXT([external]), so no msgfmt or
    xgettext is required and the library falls back to gnulib's bundled
    gettext stub instead of linking libintl.
  * --without-readline: readline is consumed by the hivexsh CLI only.  This
    recipe packages the library, so the dependency is dropped rather than
    propagated to consumers.
  * libxml2 is deliberately not provided, so PKG_CHECK_MODULES(libxml-2.0)
    takes its "not found" branch, the `xml` subdirectory (hivexml) is left
    out via the HAVE_LIBXML2 conditional and the package stays
    dependency-free.
  * Library-only package: the upstream tools are built (the share/
    subdirectory has no configure switch — it is gated on open_memstream,
    which musl provides) but are removed in package().  R38/PF8 tie any
    bin/ payload to a software-level commands.json plus a tool package
    type, which is out of scope for a library port; consumers that need
    hivexsh/hivexml build them from the same upstream tarball.
  * R26: static is the default (--enable-static --disable-shared) so the
    recipe can never overwrite the worker's system /lib.
  * Shared builds are rejected in validate(): upstream derives
    VERSION_SCRIPT_FLAGS by probing `/usr/bin/ld --help`, which does not
    exist on OHOS, so configure falls back to the Solaris form
    "-Wl,-M -Wl," that lld cannot parse.  That flag only reaches the
    libhivex.so link line, which is why the default static build is clean
    while shared=True would fail at link time.
"""
import os
import re
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    rm,
    rmdir,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# E490: the HarmonyOS PC adaptation paths behind the worker's build folder do
# not always carry POSIX execute bits through extract/copy, while the generated
# Makefiles execute these helper scripts directly.  Only these well-known
# Autotools helpers get the bits restored.
_AUTOTOOLS_HELPERS = frozenset({
    "configure", "config.guess", "config.sub", "install-sh", "missing",
    "depcomp", "compile", "ltmain.sh", "ylwrap", "test-driver", "ar-lib",
})


class HivexConan(ConanFile):
    name = "hivex"
    version = "1.3.24"
    description = "Library for reading and writing Windows Registry hive files"
    license = "LGPL-2.1-only"
    homepage = "https://libguestfs.org/"
    url = "https://download.libguestfs.org/hivex/"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: system-name (here: dependency-free) library -> static default.
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.extend([
            # Language bindings (OCaml/perl/python/ruby) are out of scope.
            "--disable-ocaml",
            "--disable-perl",
            "--disable-python",
            "--disable-ruby",
            # AM_GNU_GETTEXT([external]): no msgfmt/xgettext, no libintl.
            "--disable-nls",
            # readline is only used by the hivexsh CLI, which is not shipped.
            "--without-readline",
        ])
        tc.generate()

    def validate(self):
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "hivex/1.3.24 on OHOS is packaged as a static library only: "
                "upstream's VERSION_SCRIPT_FLAGS probe needs /usr/bin/ld, so "
                "configure would feed lld the unsupported '-M' flag while "
                "linking libhivex.so"
            )

    # ------------------------------------------------------------------
    # E490 — Autotools helper scripts must stay executable
    # ------------------------------------------------------------------
    def _restore_autotools_helper_modes(self):
        """E490: give the Autotools helper scripts their execute bits back.

        configure/config.guess/config.sub/install-sh/missing are executed
        directly by the generated Makefiles, so a mode bit lost in
        extract/copy surfaces as ``/bin/sh: <b>/configure: Permission
        denied`` (Error 126) before any compilation happens.  Files that
        already carry an execute bit are left untouched, which makes this a
        no-op on workers whose filesystem preserves the modes.
        """
        exec_bits = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        for root in {self.source_folder, self.build_folder}:
            if not root or not os.path.isdir(root):
                continue
            for dirpath, _dirnames, filenames in os.walk(root):
                for name in filenames:
                    if name not in _AUTOTOOLS_HELPERS:
                        continue
                    path = os.path.join(dirpath, name)
                    mode = os.stat(path).st_mode
                    if not mode & exec_bits:
                        os.chmod(path, mode | exec_bits)

    # ------------------------------------------------------------------
    # E007 — teach config.guess/config.sub about HarmonyOS
    # ------------------------------------------------------------------
    def _config_script_paths(self):
        """Return the (config.guess, config.sub) pair shipped in the tarball."""
        for folder in (os.path.join(self.source_folder, "build-aux"),
                       self.source_folder):
            guess = os.path.join(folder, "config.guess")
            sub = os.path.join(folder, "config.sub")
            if os.path.isfile(guess) and os.path.isfile(sub):
                return guess, sub
        return None, None

    def _ohos_patch_script(self):
        """Locate the repository's HarmonyOS config.guess/config.sub patcher."""
        candidates = [
            os.environ.get("OHC_SKILL_ROOT", ""),
            os.environ.get("CI_REPO_ROOT", ""),
            # archives/<letter>/<name>/<version>/ -> repository root
            os.path.normpath(os.path.join(self.recipe_folder, *[".."] * 4)),
        ]
        for root in candidates:
            if not root:
                continue
            script = os.path.join(root, "scripts", "patch-autotools-ohos.pl")
            if os.path.isfile(script):
                return script
        return None

    def _patch_config_for_ohos(self):
        """E007: make the Autotools platform probe recognise HarmonyOS.

        A native OHOS build gets no --host from the toolchain, so configure
        runs build-aux/config.guess, which has no HarmonyOS branch and aborts
        with "cannot guess build type; you must specify one".  Forcing
        --build/--host around it is explicitly forbidden (autoconf would then
        treat the build as cross compiling and skip every AC_RUN_IFELSE,
        producing a wrong config.h), so both scripts are patched instead.
        """
        guess, sub = self._config_script_paths()
        if not guess:
            self.output.warning("E007: config.guess/config.sub not found")
            return
        script = self._ohos_patch_script()
        if script:
            self.run(f'perl "{script}" "{guess}" "{sub}"')
        else:
            self.output.info("E007: patch-autotools-ohos.pl unavailable — "
                             "applying the equivalent in-recipe patch")
        # Both transformers below are idempotent, so they also act as the
        # verification pass when the repository script ran: its "add
        # linux-ohos to the kernel-compatibility list" step is guarded by a
        # plain "linux-ohos" substring test that its own triplet step has
        # already satisfied, so that edit is silently skipped and config.sub
        # rejects the guessed triplet later on (E072).  Re-running the
        # transformers only fills in what is actually missing.
        self._patch_config_guess(guess)
        self._patch_config_sub(sub)

    def _patch_config_guess(self, guess_path):
        """config.guess fallback: emit aarch64-unknown-linux-ohos.

        hivex ships the 2022-05-25 config.guess, which resolves the system via
        a single `case "$UNAME_SYSTEM:..."` and therefore has no
        `__ANDROID__`/`LIBC=` block to extend — only the HarmonyOS case arm is
        added, before the NetBSD arm that the main switch already has.
        """
        with open(guess_path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        if "HarmonyOS" in content:
            self.output.info("E007: config.guess already knows HarmonyOS")
            return
        block = (
            '    *:HarmonyOS:*:*)\n'
            '\tcase "$UNAME_MACHINE" in\n'
            '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
            '\t    armv7*|armv8*) MACHINE=arm ;;\n'
            '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
            '\t    i?86)          MACHINE=i686 ;;\n'
            '\t    *)             MACHINE="$UNAME_MACHINE" ;;\n'
            '\tesac\n'
            '\tGUESS=${MACHINE}-unknown-linux-ohos\n'
            '\t;;\n\n'
        )
        anchor = "    *:NetBSD:*:*)\n"
        if anchor not in content:
            self.output.warning("E007: config.guess insertion point not found")
            return
        content = content.replace(anchor, block + anchor, 1)
        with open(guess_path, "w", encoding="utf-8") as fh:
            fh.write(content)
        self.output.info("E007: config.guess now reports HarmonyOS")

    def _patch_config_sub(self, sub_path):
        """config.sub fallback: accept the linux-ohos triplet."""
        with open(sub_path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        changed = False
        if "ohos-linux" not in content:
            pattern = (r'(android-linux\)\s*\n\s*basic_machine=\$field1-unknown\s*\n'
                       r'\s*basic_os=linux-android\s*\n\s*;;\s*\n)')
            replacement = (r'\1\tohos-linux)\n\tbasic_machine=$field1-unknown\n'
                           r'\tbasic_os=linux-ohos\n\t;;\n')
            content, count = re.subn(pattern, replacement, content)
            changed = changed or count > 0
        if "ohos*" not in content:
            patched = content.replace("gnu* | android*", "gnu* | android* | ohos*", 1)
            if patched != content:
                content = patched
                changed = True
        if "linux-ohos*" not in content:
            # The guard deliberately looks for "linux-ohos*" and not for plain
            # "linux-ohos": the triplet arm added above already contains the
            # literal text "basic_os=linux-ohos", so a plain-substring guard
            # would match here and silently skip this edit.  Without it
            # config.sub rejects the guessed triplet with "Kernel `linux' not
            # known to work with OS `ohos'" (E072) — the repository's
            # patch-autotools-ohos.pl has exactly that collision between its
            # 2.1 and 2.3 steps.
            # The trailing closing paren must stay *outside* the captured
            # group — capturing it would duplicate the brace that closes the
            # case arm, and that arm would then silently stop matching.
            content, count = re.subn(r'(linux-uclibc[\*/-]?\s*)\)',
                                     r'\1| linux-ohos*)', content)
            changed = changed or count > 0
        if not changed:
            self.output.warning("E007: config.sub patch did not match")
            return
        with open(sub_path, "w", encoding="utf-8") as fh:
            fh.write(content)
        self.output.info("E007: config.sub now accepts linux-ohos")

    # ------------------------------------------------------------------
    # E?? — autoconf config.status temp dir must live on an ordinary fs
    # ------------------------------------------------------------------
    def _patch_config_status_tmpdir(self):
        """Make autoconf's config.status temp dir writable on the CI HMDFS volume.

        autoconf creates its substitution temp dir via
        ``mktemp -d "./confXXXXXX"`` (or ``tmp=./conf$$-$RANDOM`` as fallback), both
        *relative* to the build directory; config.status then writes/executes
        ``subs1.awk`` there.

        On the CI worker the conan build folder lives on the user volume (HMDFS).
        A directory freshly created there — by ``mktemp`` (mode 0700) or ``mkdir``
        — is owned by the volume's mapped uid (20001006), **not** by the build
        process (uid 100), so writing ``subs1.awk`` fails with
        ``./config.status: line 844: ./confXXX/subs1.awk: Permission denied``
        ("could not setup config files machinery").  The same recipe builds fine
        on an ordinary filesystem (the local conan cache sits on one).

        Fix: replace the block with one that probes a list of candidate
        directories (``$TMPDIR`` first, then known ordinary CI filesystems
        ``/data/storage/el2/base/cache``, ``/data/cache``, ``/data/local/tmp``,
        ``/tmp``) and keeps the first where a *real* write probe succeeds; if none
        works it falls back to a 0777 dir created in the build folder, which on
        HMDFS is world-writable and therefore usable by uid 100.  This mirrors the
        validated approach in pitfalls-checklist.md #25.  Idempotent.
        """
        # The autoconf block that creates the substitution temp dir.
        old = (
            '{\n'
            '  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n'
            '  test -d "$tmp"\n'
            '}  ||\n'
            '{\n'
            '  tmp=./conf$$-$RANDOM\n'
            '  (umask 077 && mkdir "$tmp")\n'
            '} || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5\n'
            'ac_tmp=$tmp\n'
        )
        new = (
            '# Patched for OpenHarmonyPC/CI: HMDFS maps a fresh dir to a foreign\n'
            '# uid with mode 0700, so uid 100 cannot write into it.  Probe candidate\n'
            '# dirs and keep the first where a real write succeeds; fall back to a\n'
            '# 0777 dir in the build folder (world-writable on HMDFS).\n'
            '{\n'
            '  tmp=\n'
            '  for _hivex_tmp in "${TMPDIR:-/tmp}" /data/storage/el2/base/cache /data/cache /data/local/tmp /tmp; do\n'
            '    [ -d "$_hivex_tmp" ] || continue\n'
            '    t=`(umask 077 && mktemp -d "$_hivex_tmp/confXXXXXX") 2>/dev/null`\n'
            '    [ -d "$t" ] || continue\n'
            '    (echo probe > "$t/.writable") 2>/dev/null && { tmp=$t; break; }\n'
            '  done\n'
            '  test -n "$tmp"\n'
            '}  ||\n'
            '{\n'
            '  tmp=./conf$$-$RANDOM\n'
            '  (umask 000 && mkdir "$tmp") 2>/dev/null\n'
            '  (echo probe > "$tmp/.writable") 2>/dev/null || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5\n'
            '} || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5\n'
            'ac_tmp=$tmp\n'
        )
        for root in {self.source_folder, self.build_folder}:
            if not root or not os.path.isdir(root):
                continue
            configure = os.path.join(root, "configure")
            if not os.path.isfile(configure):
                continue
            content = open(configure, "r", encoding="utf-8",
                           errors="replace").read()
            if old not in content:
                continue
            content = content.replace(old, new)
            open(configure, "w", encoding="utf-8").write(content)
            self.output.info("E??: configure temp dir patched for HMDFS writability")

    def build(self):
        apply_conandata_patches(self)
        self._restore_autotools_helper_modes()
        self._patch_config_for_ohos()
        self._patch_config_status_tmpdir()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Layer 1 of the repository's test system: run the upstream suite.
        # lib/Makefile.am registers exactly one C test (test-just-header),
        # which hivex_open()s the bundled images/minimal registry image.
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Library-only package (see the class docstring): drop the CLI tools
        # and the libtool archives, which embed absolute build paths.
        rm(self, "hivex*", os.path.join(self.package_folder, "bin"))
        rmdir(self, os.path.join(self.package_folder, "bin"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)

    def package_info(self):
        # Installed as libhivex.a / libhivex.so -> -lhivex.
        self.cpp_info.libs = ["hivex"]
        self.cpp_info.set_property("pkg_config_name", "hivex")
        self.cpp_info.set_property("cmake_file_name", "hivex")
        self.cpp_info.set_property("cmake_target_name", "hivex::hivex")
