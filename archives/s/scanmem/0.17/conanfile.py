#!/usr/bin/env python3
"""Conan recipe — scanmem 0.17 (Autotools process-memory scanner).

scanmem is an interactive debugging utility that locates and modifies
variables inside a running process. C codebase, GNU Autotools build; it ships
both an executable (`scanmem`) and a shared library (`libscanmem.so`), so this
recipe is package_type="application" (R38: commands.json at package level).

Source provenance
-----------------
The v0.17 GitHub *release asset* does not exist (HTTP 404, verified), and the
GitHub tag archive ships no generated `configure` — only `configure.ac`,
`Makefile.am` and `autogen.sh`. So the build is a genuine bootstrap:
`autoreconf -fi` is mandatory.

OHOS adaptation (all steps verified against the 0.17 tag archive)
-----------------------------------------------------------------
  * E007 platform triplet: the autoreconf-generated `config.guess` /
    `config.sub` predate HarmonyOS, so `configure` aborts in stage 1. The
    reference `scripts/patch-autotools-ohos.pl` is reproduced in
    `_patch_autotools_ohos()` (self-contained: `conan create` runs in a clean
    tree with no access to the framework's scripts/).
    Documented deviation from the reference script: it patches the config.sub
    triplet + OS list but SKIPS the kernel-list hunk whenever the OS hunk
    fires, so `--host=aarch64-linux-ohos` still dies with
    "Kernel `linux' not known to work with OS `ohos'". This recipe therefore
    also adds `linux-ohos*` to the kernel-OS validation list. Same deviation
    lftp/4.9.3 documented; both errors reproduced here before patching.
    No --build/--host override (R1: native build; E007 forbids the bypass).
    The patch runs AFTER `autoreconf -fi`, because autoreconf reinstalls
    config.guess/config.sub and would otherwise undo it.
  * readline is a hard configure requirement (AC_CHECK_LIB exits 1 without
    it) -> `readline/8.3` (W0-published, OHOS binary present in the registry).
    It is a *static* library whose terminfo consumers (`tputs`/`tgetent`/
    `tgetstr`/`tgoto`/`tgetnum` plus the `PC`/`BC`/`UP` capability variables)
    live in ncurses. readline's own package_info does not forward ncurses, so
    scanmem's own `AC_CHECK_LIB([termcap],[tgetent])` probe fails silently and
    nothing links terminfo. Conan still propagates the transitive
    `ncurses/6.6` requirement into the aggregated LIBS, in the correct
    "consumer first, provider last" order, which is what makes the link work.
  * Patches (patches/, both registered in conandata.yml):
      0001 drops `IT_PROG_INTLTOOL` and the `po/Makefile.in` AC_CONFIG_FILES
           entry. intltool needs perl XML::Parser, absent on the OHOS worker,
           and without it config.status hard-errors on the missing
           `po/Makefile.in.in`. Nothing is lost: scanmem 0.17 never calls
           `_()`/gettext (audited: no libintl.h, no gettext symbol anywhere in
           the tree) and `po/` is a SUBDIRS entry only `if ENABLE_GUI`, which
           additionally requires Python 2.7.
      0002 adds `#include <sys/types.h>` where the BSD `uint` alias is used.
           scanroutines.c/targetmem.h/test/memfake.c relied on glibc pulling
           `uint` in transitively; the musl-style OHOS headers do not, giving
           "use of undeclared identifier 'uint'". `uint` is a plain
           `unsigned int` alias, so the fix is the missing include, not a type
           change.
  * chmod +x on the autoreconf-generated helper scripts: HMDFS extraction does
    not preserve the executable bit (E490).
  * Pinning, not clearing, CONFIG_SHELL when driving configure: the profile
    injects /data/service/hnp/bin/bash as CONFIG_SHELL and that shell's
    getcwd() fails on the HMDFS conan build cache (gtypist/2.10.1 §12.38①), so
    both CONFIG_SHELL and SHELL are set to a shell that was probed to exist
    (see _good_shell). CONFIG_SHELL must be *set*, never unset: with it empty
    autoconf falls back to a hardcoded /bin/bash to run ./config.sub, which is
    absent on the OHOS worker, and the resulting "configure: error: cannot run
    /bin/bash ./config.sub" is indistinguishable from a corrupted config.sub.
  * E011 umask: both `configure` and the `config.status` it emits hard-code
    `umask 077 && mktemp -d "./confXXXXXX"`, and HMDFS maps the new directory to
    a different owner UID, so the running process cannot create
    `./confXXXXXX/subs1.awk` inside it ("./config.status[1001]: can't create
    ./confLGAKDj/subs1.awk: Permission denied" / "config.status: error: could
    not setup config files machinery"). A leading `umask 022` on the command
    line cannot help -- each script resets the umask internally. The 077 is
    rewritten to 022 in `configure` before it runs; see _relax_autoconf_umask
    for why that also covers the generated config.status.
  * make -j1 (E074: HMDFS jobserver fifo EPERM under parallel make).
  * Upstream tests: test/Makefile.am declares TESTS = sm_test.sh, a single
    automake entry that drives 10 `test_sm` cases against test/memfake. The
    build() runs `make check` when the host can run the target binaries and
    reports the outcome through HMBS_UPSTREAM_TEST_RESULT, parsing
    test/test-suite.log (deterministic single source). Non-passing tests are
    recorded honestly with source-grounded gaps instead of vetoing the
    package (leatherman/1.12.1 + lftp/4.9.3 precedent, TEST_QUALITY_SPEC 3.3).
"""
import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, rm)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


# Audited from test/Makefile.am + test/sm_test.sh in the 0.17 tag archive:
#   TESTS = sm_test.sh                      (1 automake entry)
#   sm_test.sh issues 10 `test_sm` commands (upstream's real case count)
_UPSTREAM_AUTOMAKE_ENTRIES = 1
_UPSTREAM_TEST_CASES = 10

# Upper bound for `make check`. The 10 upstream scans of a 4 MiB target finish
# in well under a minute on a healthy host, so this is slack rather than a
# target: its job is to convert a would-be 4-hour CI step timeout (14400 s,
# which yields no verdict at all) into a fast, diagnosable exit 124/137.
# See _run_upstream_tests.
_UPSTREAM_TEST_TIMEOUT = 900

# Autotools helper scripts generated by autoreconf -fi. HMDFS does not keep
# the executable bit through extraction, and configure execs these directly.
_AUTORECONF_HELPERS = (
    "configure",
    "config.guess",
    "config.sub",
    "install-sh",
    "missing",
    "depcomp",
    "compile",
    "config.rpath",
    "test-driver",
    "py-compile",
)


class ScanmemConan(ConanFile):
    name = "scanmem"
    version = "0.17"
    description = "Locate and modify variables in a running process's memory"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/scanmem/scanmem"
    url = "https://github.com/scanmem/scanmem"
    topics = ("debugging", "memory", "process", "ptrace", "reverse-engineering")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # L0q: keep conanfile.py + patches/ in the exported recipe.
    exports_sources = "conanfile.py", "conandata.yml", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # The tag archive has no generated `configure`, so autoreconf must run.
        # The OHOS worker ships autoconf but not automake/aclocal, so without
        # this `autoreconf -fi` dies with "Can't exec \"aclocal\""; and without
        # libtool.m4 on ACLOCAL_PATH, LT_INIT aborts (htscodecs/1.6.5
        # precedent). NB: do NOT tool_requires autoconf — its conan package
        # drags in its own perl, whose XS modules shadow the system perl and
        # break the system autoreconf.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4.1")

    def requirements(self):
        # W0-verified published against the project artifact registry
        # (recipe-only download of readline/8.3 succeeded): configure hard-fails
        # with "libreadline could not be found" without it. ncurses/6.6 arrives
        # transitively and supplies the terminfo symbols the static
        # libreadline.a needs.
        self.requires("readline/8.3")

    def validate(self):
        # R32: the platform check must accept Linux and OHOS alike.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "scanmem is only supported on Linux/OHOS, not %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # No --host/--build override: host and build profiles are identical, so
        # configure self-detects and runs its AC_RUN_IFELSE probes for real
        # (R1/E007 forbid forcing the cross path -- it would make
        # AC_CHECK_FILE(/proc/self/maps) hard-error "cannot check for file
        # existence when cross compiling").
        # --disable-rpath keeps conan-cache paths out of the shipped binaries.
        # scanmem has no --with-readline=DIR knob, so readline/ncurses reach
        # configure purely through the AutotoolsDeps CPPFLAGS/LDFLAGS/LIBS.
        tc.configure_args.append("--disable-rpath")
        tc.generate()

        # libscanmem.so is a real shared object, so conftest programs and the
        # built binary need the dependency libdirs on the loader path
        # (lbreakouthd/1.2.3 precedent).
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_deps_env")

    # ------------------------------------------------------------------
    # E007: teach the autotools triplet guesser about HarmonyOS.
    # ------------------------------------------------------------------
    def _patch_autotools_ohos(self):
        cg_path = os.path.join(self.source_folder, "config.guess")
        cs_path = os.path.join(self.source_folder, "config.sub")
        if not (os.path.isfile(cg_path) and os.path.isfile(cs_path)):
            self.output.warning("scanmem: config.guess/config.sub missing, skipping E007")
            return

        def read(path):
            with open(path, "r", encoding="utf-8", errors="surrogateescape") as fh:
                return fh.read()

        def write(path, text):
            with open(path, "w", encoding="utf-8", errors="surrogateescape",
                      newline="\n") as fh:
                fh.write(text)

        # 1. config.guess: recognise uname -s = HarmonyOS.
        cg = read(cg_path)
        if "HarmonyOS" not in cg:
            block = (
                "    *:HarmonyOS:*:*)\n"
                '\tcase "$UNAME_MACHINE" in\n'
                "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                "\t    i?86)         MACHINE=i686 ;;\n"
                '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                "\tesac\n"
                "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                "\t;;\n\n"
            )
            new_cg, n = re.subn(r"(^[ \t]+\*\:NetBSD\:\*\:\*\)[ \t]*\n)",
                                block + r"\1", cg, count=1, flags=re.M)
            if n:
                cg = new_cg
                self.output.info("scanmem: E007 config.guess HarmonyOS branch added")
        else:
            self.output.info("scanmem: E007 config.guess already knows HarmonyOS")

        # 2. config.sub: triplet + OS list + kernel/OS validation list.
        cs = read(cs_path)
        if "ohos-linux)" not in cs:
            # Clone the whole android-linux arm and substitute. Rebuilding it
            # from separately captured groups is unsafe: a trailing "[ \t]*" in
            # the pattern silently swallows the next line's indentation and
            # emits a stray ";;" that turns config.sub into a shell syntax
            # error ("Syntax error: newline unexpected") -- exactly the failure
            # mode when a recipe patches config.sub without executing it.
            m = re.search(
                r"^[ \t]*android-linux\)[ \t]*\n"
                r"[ \t]*basic_machine=\$field1-unknown[ \t]*\n"
                r"[ \t]*basic_os=linux-android[ \t]*\n"
                r"[ \t]*;;[ \t]*\n",
                cs, re.M)
            if m:
                cs = (cs[:m.end()]
                      + m.group(0).replace("android-linux)", "ohos-linux)", 1)
                                .replace("basic_os=linux-android",
                                         "basic_os=linux-ohos", 1)
                      + cs[m.end():])
                self.output.info("scanmem: E007 config.sub ohos-linux triplet added")
            else:
                self.output.warning("scanmem: android-linux arm not found in config.sub")
        if not re.search(r"android\*\s*\|\s*ohos\*", cs):
            cs, n = re.subn(r"(gnu\*\s*\|\s*android\*)", r"\1 | ohos*", cs, count=1)
            if n:
                self.output.info("scanmem: E007 config.sub OS list extended")
        if not re.search(r"linux-uclibc\*\s*\|\s*linux-ohos\*", cs):
            # The framework's perl script guards this hunk on a global
            # `/linux-ohos/` search, which the triplet hunk above has already
            # satisfied (it writes `basic_os=linux-ohos`), so its kernel hunk
            # is dead code whenever the triplet hunk fires. Guard on the kernel
            # list itself instead. Same deviation lftp/4.9.3 documented; the
            # "Kernel `linux' not known to work with OS `ohos'" failure was
            # reproduced here before patching.
            cs, n = re.subn(r"(linux-uclibc\*[/-]?[ \t]*)\)", r"\1| linux-ohos*)",
                            cs, count=1)
            if n:
                self.output.info("scanmem: E007 config.sub kernel-OS list extended")

        write(cg_path, cg)
        write(cs_path, cs)
        self._verify_config_sub(cs_path)

    def _shell(self):
        """Resolve a usable POSIX shell on this executor, or None.

        Do not assume `sh` exists. The OHOS build worker's PATH is
        /data/app/bin:/system/bin:/system/sbin:/vendor/bin:… plus the profile's
        /data/service/hnp/bin, and none of those is guaranteed to provide `sh`
        -- CI #64654 died with
            FileNotFoundError: [Errno 2] No such file or directory: 'sh'
        from a bare subprocess.run(["sh", ...]) here. Probe, never assume.
        """
        candidates = (
            os.environ.get("CONFIG_SHELL"),
            shutil.which("sh"),
            shutil.which("bash"),
            "/data/service/hnp/bin/bash",   # CI profile's [buildenv] shell
            "/system/bin/sh",               # OHOS standard
            "/bin/sh",
        )
        for cand in candidates:
            if not cand:
                continue
            try:
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
            except OSError:
                continue
        return None

    def _verify_config_sub(self, cs_path):
        """Fail loudly if the patched config.sub is not valid shell.

        A malformed config.sub otherwise surfaces much later as the opaque
        "configure: error: cannot run <shell> ./config.sub", which reads like
        a missing shell rather than a bad patch. Skipped (not failed) when the
        executor has no usable shell at all -- the configure step that follows
        still catches a broken config.sub, just with a worse message.
        """
        sh = self._shell()
        if sh is None:
            self.output.warning(
                "scanmem: no usable shell found; skipping `sh -n config.sub` "
                "self-check (configure will validate it implicitly)")
            return
        proc = subprocess.run([sh, "-n", cs_path], capture_output=True)
        if proc.returncode != 0:
            raise ConanException(
                "scanmem: patched config.sub is not valid shell (%s -n): %s"
                % (sh, proc.stderr.decode("utf-8", "replace").strip() or "unknown")
            )
        self.output.info("scanmem: patched config.sub passes `%s -n`" % sh)

    def _chmod_helpers(self):
        for rel in _AUTORECONF_HELPERS:
            path = os.path.join(self.source_folder, rel)
            if not os.path.isfile(path):
                continue
            try:
                os.chmod(path, 0o755)
            except OSError:
                # HMBS_CAP_CHMOD=0: HMDFS may ignore chmod; the OHOS-native
                # path never reaches here because the files are already +x.
                self.output.warning("scanmem: chmod 0755 failed on %s" % rel)

    def _writable_tmpdir(self):
        """Reuse the HMBS-injected TMPDIR/TMP/TEMP; never /tmp (read-only)."""
        for var in ("TMPDIR", "TMP", "TEMP"):
            cand = os.environ.get(var, "")
            if cand and cand != "/tmp" and os.path.isdir(cand):
                return cand
        tmpd = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpd, exist_ok=True)
        return tmpd

    def _good_shell(self):
        """Healthy shell for native OHOS builds, else None (E232 forbid_1).

        Branch key is settings_build.os: settings.os is the target and would
        misroute cross-build executors. Returns None off OHOS so every other
        executor keeps the stock Autotools path.
        """
        if self.settings_build.os != "OHOS":
            return None
        for cand in ("/system/bin/sh", "/bin/sh"):
            if os.path.exists(cand):
                return cand
        return self._shell()

    def _configure_and_make(self, target=None):
        """Run configure (and optionally a make target) in-source.

        In-source in two independent senses, both required:
          * cwd is self.source_folder, because scanmem ships no generated
            `configure` and the tree that autoreconf bootstraps is the tree
            that must be configured (basic_layout keeps src/ and build/ apart,
            and AutotoolsToolchain's config.status bookkeeping expects its own
            layout);
          * a single tree, because test/Makefile.am's check target reaches the
            CLI as ../scanmem.
        """
        sh = self._good_shell()
        tmpdir = self._writable_tmpdir()
        tmp_export = ('export TMPDIR="%s"; export TMP="%s"; export TEMP="%s"; '
                      % (tmpdir, tmpdir, tmpdir))
        autotools = Autotools(self)
        args = autotools._configure_args
        if isinstance(args, (list, tuple)):
            args = " ".join(shlex.quote(a) for a in args)
        configure = os.path.join(self.source_folder, "configure").replace("\\", "/")
        # E011: relax autoconf's umask BEFORE configure runs, because configure
        # generates and immediately executes config.status, and both carry their
        # own `umask 077`.
        self._relax_autoconf_umask(configure)
        if sh is None:
            self.run('umask 022; %s"configure" %s' % (tmp_export, args),
                     cwd=self.source_folder, env="conanbuild")
        else:
            # The profile injects CONFIG_SHELL=/data/service/hnp/bin/bash and
            # that shell's getcwd() fails on the HMDFS conan build cache
            # (gtypist/2.10.1 §12.38①), so pin both CONFIG_SHELL and SHELL to
            # the healthy system shell. CONFIG_SHELL must be *set*, not unset:
            # autoconf falls back to a hardcoded /bin/bash to run config.sub
            # when it is empty ("configure: error: cannot run /bin/bash
            # ./config.sub"), which is absent on the OHOS worker.
            self.run('umask 022; %senv CONFIG_SHELL="%s" SHELL="%s" "%s" %s'
                     % (tmp_export, sh, sh, configure, args),
                     cwd=self.source_folder, env="conanbuild")
        # config.status gets its own baked-in `umask 077` copy, and it is the
        # one that actually failed on the worker ("./config.status[1001]: can't
        # create ./confXXXXXX/subs1.awk: Permission denied"). Fix it, then re-run
        # it if the Makefiles were not produced.
        status_path = os.path.join(self.source_folder, "config.status")
        if self._relax_autoconf_umask(status_path):
            if not os.path.isfile(os.path.join(self.source_folder, "Makefile")):
                self.output.warning("scanmem: Makefile missing after configure; "
                                    "re-running config.status once")
                self.run('%sCONFIG_SHELL="%s" ./config.status'
                         % (tmp_export, sh or self._shell() or "/bin/sh"),
                         cwd=self.source_folder, env="conanbuild")
        make_cmd = "umask 022; %sCONFIG_SHELL=\"%s\" make -j1 %s" % (
            tmp_export, sh or "/bin/sh", target or "")
        self.run(make_cmd, cwd=self.source_folder, env="conanbuild")

    def build(self):
        apply_conandata_patches(self)
        # Bootstrap: the tag archive ships no `configure`. automake/aclocal/
        # libtoolize come from tool_requires (CI has autoconf but not them).
        self.run("umask 022; autoreconf -fi", cwd=self.source_folder,
                 env="conanbuild")
        # E007 after autoreconf -- autoreconf reinstalls config.guess/sub and
        # would silently undo the patch otherwise.
        self._patch_autotools_ohos()
        self._chmod_helpers()
        self._configure_and_make()
        self._run_upstream_tests()

    def _relax_autoconf_umask(self, *paths):
        """E011: rewrite autoconf's `umask 077` to `umask 022` in-place.

        HMDFS maps the directory owner to a different UID than the running
        process, so the 0700 temp dir that config.status creates via
        `mktemp -d "./confXXXXXX"` is not writable by that process:

            ./config.status[1001]: can't create ./confLGAKDj/subs1.awk: Permission denied
            config.status: error: could not setup config files machinery

        Editing the generated configure/config.status is the framework's
        documented E011 remedy (146 recipes already do this). Leading `umask 022`
        on the command line is not enough: configure and config.status each set
        their own umask internally, overriding the inherited value.
        """
        changed = []
        for path in paths:
            if not path or not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="surrogateescape") as fh:
                    content = fh.read()
            except OSError:
                continue
            if "umask 077" not in content:
                continue
            try:
                with open(path, "w", encoding="utf-8", errors="surrogateescape",
                          newline="\n") as fh:
                    fh.write(content.replace("umask 077", "umask 022"))
            except OSError:
                continue
            changed.append(os.path.basename(path))
        if changed:
            self.output.info("scanmem: E011 relaxed umask 077->022 in %s"
                             % ", ".join(changed))
        return changed

    # ------------------------------------------------------------------
    # Upstream test suite: make check -> test/sm_test.sh (10 test_sm cases)
    # ------------------------------------------------------------------
    def _have_timeout(self):
        """True when a `timeout` binary is usable here.

        The CI worker provides it (build_and_test.sh itself wraps conan create
        in `timeout --signal=KILL`), so this is normally True; the guard keeps
        the recipe working on hosts that lack it instead of hard-failing. Probe
        PATH plus the OHOS-standard absolute locations, never assume.
        """
        for cand in (shutil.which("timeout"), "/system/bin/timeout",
                     "/bin/timeout", "/usr/bin/timeout",
                     "/data/service/hnp/bin/timeout"):
            if not cand:
                continue
            try:
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return True
            except OSError:
                continue
        return False

    def _timeout_bin(self):
        for cand in (shutil.which("timeout"), "/system/bin/timeout",
                     "/bin/timeout", "/usr/bin/timeout",
                     "/data/service/hnp/bin/timeout"):
            if not cand:
                continue
            try:
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
            except OSError:
                continue
        return None

    def _find_suite_log(self):
        hits = []
        for root in (self.build_folder, self.source_folder):
            if not root:
                continue
            for dirpath, _dirs, files in os.walk(root):
                if "test-suite.log" in files and os.path.basename(dirpath) == "test":
                    hits.append(os.path.join(dirpath, "test-suite.log"))
        return str(max(hits, key=os.path.getmtime)) if hits else None

    def _run_upstream_tests(self):
        """Run `make check` and emit HMBS_UPSTREAM_TEST_RESULT.

        Deterministic source: test/test-suite.log written by the automake
        parallel harness (TOTAL/PASS/FAIL/SKIP/... summary plus per-test
        PASS:/FAIL: lines). No stdout scraping.

        A failing upstream suite does NOT veto the package (leatherman/1.12.1
        and lftp/4.9.3 precedent): the marker keeps status=failed so the
        outcome stays honest, every non-passing test gets a source-grounded
        gap entry, and packaging continues so test_package still runs.

        The run is time-bounded. test/sm_test.sh issues 10 `test_sm` scans of a
        live 4 MiB target with no per-test timeout, so on a host that cannot
        read another process's /proc/<pid>/mem a scan can block indefinitely
        instead of failing. Unbounded, that burns the whole CI step budget
        (14400 s) and yields no verdict at all; bounded, it fails in minutes
        with a diagnosable exit 124. Same bounding idea as lftp/4.9.3's
        per-test `timeout` wrapper.
        """
        timed_out = False
        # Use the resolved absolute path: `timeout` may live outside PATH on
        # the OHOS worker, in which case a bare `timeout ...` would fail with
        # "No such file or directory" and the bound would silently not apply.
        timeout_bin = self._timeout_bin()
        if timeout_bin:
            # Generous: the 10 scans of a 4 MiB target take well under a
            # minute on a healthy host, so 900 s is slack, not a target.
            check = '"%s" --signal=KILL %d make check' % (
                timeout_bin, _UPSTREAM_TEST_TIMEOUT)
        else:
            self.output.warning("scanmem: no `timeout` binary found; "
                                "make check runs unbounded")
            check = None
        try:
            sh = self._good_shell()
            tmpdir = self._writable_tmpdir()
            tmp_export = ('export TMPDIR="%s"; export TMP="%s"; export TEMP="%s"; '
                          % (tmpdir, tmpdir, tmpdir))
            if check:
                self.run('umask 022; %sCONFIG_SHELL="%s" %s'
                         % (tmp_export, sh or self._shell() or "/bin/sh", check),
                         cwd=self.source_folder, env="conanbuild")
            else:
                self._configure_and_make(target="check")
            interrupted = False
        except Exception as exc:
            msg = str(exc)
            timed_out = ("Exited with code: 137" in msg
                         or "Error 137" in msg
                         or "Killed" in msg
                         or "timed out" in msg.lower())
            self.output.warning("scanmem: make check interrupted: %s" % exc)
            interrupted = True
        if timed_out:
            self.output.error(
                "scanmem: make check exceeded %d s and was killed; the upstream "
                "scans most likely cannot read /proc/<pid>/mem of another "
                "process on this host. Recorded as an environment gap, not a "
                "build failure." % _UPSTREAM_TEST_TIMEOUT)

        log = self._find_suite_log()
        if log is None:
            marker = {
                "status": "failed",
                "framework": "automake",
                "command": "make check",
                "discovered": _UPSTREAM_TEST_CASES,
                "autotools_entries": _UPSTREAM_AUTOMAKE_ENTRIES,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "test/test-suite.log not found under %s"
                          % ", ".join(str(r) for r in (self.build_folder,
                                                      self.source_folder) if r),
                "gaps": [{
                    "count": _UPSTREAM_TEST_CASES,
                    "category": "environment",
                    "detail": "make check exceeded %d s and was killed before the "
                              "automake summary; the upstream scans most likely "
                              "cannot read /proc/<pid>/mem of another process on "
                              "this host" % _UPSTREAM_TEST_TIMEOUT,
                    "evidence": "test/test-suite.log",
                }],
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
            self.output.warning("scanmem: upstream tests produced no log; recorded "
                                "honestly, continuing to package")
            return

        text = Path(log).read_text(encoding="utf-8", errors="replace")
        counts = {}
        for key in ("TOTAL", "PASS", "FAIL", "SKIP", "XFAIL", "XPASS", "ERROR"):
            m = re.search(r"^# %s:\s*(\d+)\s*$" % key, text, re.MULTILINE)
            counts[key] = int(m.group(1)) if m else 0

        passed = counts["PASS"]
        skipped = counts["SKIP"] + counts["XFAIL"]
        failed = counts["FAIL"] + counts["XPASS"] + counts["ERROR"]
        entry_ok = (counts["TOTAL"] > 0 and failed == 0 and not interrupted)
        # sm_test.sh runs under `set -ev` and issues its 10 test_sm calls
        # sequentially, so it aborts at the *first* failing scan. That makes the
        # single automake entry all-or-nothing: a green entry means all
        # _UPSTREAM_TEST_CASES ran and passed, and a red entry means the run
        # stopped at the first failure. Deriving the per-case counts from
        # automake's TOTAL alone would wrongly report 9 cases as "never ran"
        # even on a fully green run.
        if entry_ok:
            executed = passed = _UPSTREAM_TEST_CASES
            unrun = 0
        else:
            executed = passed
            unrun = max(0, _UPSTREAM_TEST_CASES - executed - skipped)

        status = "passed" if entry_ok else "failed"
        marker = {
            "status": status,
            "framework": "automake",
            "command": "make check",
            "discovered": _UPSTREAM_TEST_CASES,
            "autotools_entries": _UPSTREAM_AUTOMAKE_ENTRIES,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "automake_total": counts["TOTAL"],
            "automake_pass": passed if not entry_ok else counts["PASS"],
        }
        if status != "passed":
            gaps = []
            if failed:
                gaps.append({
                    "count": failed,
                    "category": "test_failure",
                    "detail": "test/sm_test.sh exited non-zero: scanmem could not "
                              "complete the scans against test/memfake on this host "
                              "(the script is `set -e`, so it stops at the first "
                              "failing test_sm case)",
                    "evidence": log,
                })
            if unrun:
                gaps.append({
                    "count": unrun,
                    "category": "environment",
                    "detail": "%d of the %d upstream test_sm cases never ran; the "
                              "single automake entry (sm_test.sh) aborts at the "
                              "first failing scan" % (unrun, _UPSTREAM_TEST_CASES),
                    "evidence": log,
                })
            if gaps:
                marker["gaps"] = gaps
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
        if status != "passed":
            self.output.warning(
                "scanmem: upstream tests not fully green (executed=%d passed=%d "
                "failed=%d skipped=%d); recorded honestly, continuing to package"
                % (executed, passed, failed, skipped))

    def package(self):
        # Explicit in-source `make install` (same context as build()) rather
        # than Autotools.install(), which would run in the basic_layout
        # build/ folder where nothing was configured.
        sh = self._good_shell()
        tmpdir = self._writable_tmpdir()
        tmp_export = ('export TMPDIR="%s"; export TMP="%s"; export TEMP="%s"; '
                      % (tmpdir, tmpdir, tmpdir))
        prefix = self.package_folder.replace("\\", "/")
        self.run('umask 022; %sCONFIG_SHELL="%s" make install DESTDIR="%s"'
                 % (tmp_export, sh or "/bin/sh", prefix),
                 cwd=self.source_folder, env="conanbuild")
        # libtool bookkeeping files are build-time only.
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            rm(self, "*.la", libdir)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Ships an executable *and* a shared library plus public headers, so
        # bindirs/libdirs/includedirs all matter to consumers: VirtualRunEnv
        # puts bin/ on PATH and lib/ on LD_LIBRARY_PATH, which the
        # test_package needs to load libscanmem.so.1.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
