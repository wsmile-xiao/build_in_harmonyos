#!/usr/bin/env python3
"""Conan recipe for unuran 1.12.0 (autotools, HarmonyOS PC / aarch64).

Upstream: https://statmath.wu.ac.at/unuran/ — the Universal Non-Uniform
RANdom number generator library (C, GPL-2.0-or-later).  It is the sampling
back end used by ROOT, and ships 58 self-checking regression programs that
compare every implemented method against reference sequences.

Build notes (E007/E011/E074/E114):
  - the tarball ships a pre-generated `configure` plus every `Makefile.in`,
    so no `autoreconf` bootstrap is needed (unlike libxdg);
  - `config.guess` lives in `autoconf/` (`AC_CONFIG_AUX_DIR([autoconf])`),
    not in the source root — the E007 triplet patch has to look for it;
    its `config.sub` already knows the `ohos` OS and the `linux-ohos*`
    kernel, so only the config.guess half of the patch applies here;
  - E114: HMDFS forces setgid on directories, so the generated configure's
    `umask 077 && mktemp -d ./confXXXXXX` produces a temp dir that is not
    writable even by its owner; every `umask 077` becomes `umask 022`;
  - E074: the SELinux policy on the OHOS worker denies the make jobserver
    FIFO, so every make invocation uses -j1;
  - the top-level `make` also descends into `doc/`, which needs `makeinfo`
    from the texinfo package.  Nothing in this package consumes the
    documentation, and the CI worker's clean PATH has no makeinfo, so the
    build is driven per sub-directory (`make -C scripts`, `make -C src`,
    `make -C tests check`) instead of a bare top-level `make`.  `make -C`
    is used rather than a command-line `SUBDIRS=...` override because the
    latter travels through MAKEFLAGS into every sub-make and clobbers the
    nested `SUBDIRS` variables of `src/` and `tests/`.

The recipe is self-contained (it does not read scripts/ from the CI
checkout) so that conanfile.py + conandata.yml alone reproduce the CI
result.
"""
import glob as _glob
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# Top-level SUBDIRS = . scripts src examples experiments tests doc.
# `scripts` runs first because it owns the rule that generates
# src/utils/unur_fp_const_source.h (a no-op guard when the tarball already
# ships that file, which it does).  `examples`, `experiments` and `doc`
# produce nothing that is packaged or tested.
BUILD_SUBDIRS = ("scripts", "src")
CHECK_SUBDIR = "tests"
INSTALL_SUBDIR = "src"

_AUX_DIRS = (".", "autoconf", "config", "build-aux", "scripts")


def _patch_configure_hmdfs(path):
    """Two HMDFS workarounds for the shipped configure.

    E114/E011: HMDFS forces setgid on directories, so `umask 077 &&
    mktemp -d` yields a drwx--S--- temp dir that even its owner cannot
    write.  Relax every umask 077 (the a52dec/adcli/univalue/libxdg
    method).

    [shell_getcwd]: HMDFS makes everything above the conan build tree
    unreachable to getcwd(), so configure's own `ac_pwd=`pwd`` bottom
    dies with "working directory cannot be determined" before a single
    compiler line runs.  Fall back to $PWD, which build() exports; the
    `cd "$ac_pwd" && ls -di .` check just below goes through plain path
    lookup, which HMDFS still serves (adms 2.3.7 / nspr 4.37 /
    aribb24 1.0.4 precedents).
    """
    with open(path, "r", encoding="utf-8", newline="") as fh:
        data = fh.read()
    data = data.replace("umask 077", "umask 022")
    data = data.replace(
        "ac_pwd=`pwd` && test -n \"$ac_pwd\" &&",
        "ac_pwd=`pwd` 2>/dev/null || ac_pwd=\"$PWD\"\ntest -n \"$ac_pwd\" &&",
        1,
    )
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(data)


def _find_helper(src_dir, leaf):
    """Locate an autoconf helper that may sit in an AC_CONFIG_AUX_DIR.

    unuran uses `AC_CONFIG_AUX_DIR(autoconf)`, so config.guess/config.sub
    are at `autoconf/config.guess`, not at the source root; a recipe that
    only looks at the root silently applies nothing.
    """
    for rel in _AUX_DIRS:
        candidate = os.path.join(src_dir, rel, leaf) if rel != "." \
            else os.path.join(src_dir, leaf)
        if os.path.isfile(candidate):
            return candidate
    return None


def _patch_ohos_triplet(conanfile, src_dir):
    """E007: teach config.guess/config.sub the aarch64-linux-ohos triple.

    Inline equivalent of scripts/patch-autotools-ohos.pl (staying
    self-contained on purpose).  Each of the four edits is applied only if
    its guard is missing, so a helper that already knows HarmonyOS is left
    alone: unuran 1.12.0's config.sub already matches `ohos*` and
    `linux-ohos*` (its autotools vintage is newer than the one libxdg
    ships), so in practice only the two config.guess edits land.

      config.guess
        1. `#elif defined(__GLIBC__) / LIBC=gnu` -> add a
           `#elif defined(__OHOS__) / LIBC=ohos` arm, so a worker that
           reports `uname -s` = Linux still resolves the OHOS libc
           instead of falling through to the `LIBC=gnu` fallback;
        2. a `*:HarmonyOS:*:*)` case, because the OHOS `uname -s` is
           literally "HarmonyOS" and no stock config.guess matches it
           (configure then dies with "cannot guess build type").

      config.sub
        3. `ohos-linux)` basic machine entry next to `android-linux)`;
        4. `ohos*` in the OS list and `linux-ohos*` in the kernel-OS
           validation list, so `--host=aarch64-linux-ohos` is accepted.
    """
    cg_path = _find_helper(src_dir, "config.guess")
    cs_path = _find_helper(src_dir, "config.sub")
    changed = 0

    if cg_path is None:
        conanfile.output.warning("config.guess not found under " + src_dir)
    else:
        conanfile.output.info("config.guess: " + cg_path)
        with open(cg_path, "r", encoding="utf-8", newline="") as fh:
            gc = fh.read()

        if "LIBC=ohos" not in gc:
            new_gc, n = re.subn(
                r"(#elif defined\(__GLIBC__\)\s*\n\s*LIBC=gnu)",
                r"#elif defined(__OHOS__)\n\tLIBC=ohos\n\1",
                gc, count=1)
            if n:
                gc = new_gc
                changed += 1
                conanfile.output.info("config.guess: __OHOS__ LIBC arm added")
            else:
                conanfile.output.warning(
                    "config.guess: __GLIBC__ anchor not found")
        else:
            conanfile.output.info("config.guess: LIBC=ohos already present")

        if "HarmonyOS" not in gc:
            block = (
                "    *:HarmonyOS:*:*)\n"
                "\tcase \"$UNAME_MACHINE\" in\n"
                "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                "\t    i?86)         MACHINE=i686 ;;\n"
                "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
                "\tesac\n"
                "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                "\t;;\n\n")
            new_gc, n = re.subn(
                r"(^[ \t]+\*:NetBSD:\*:\*\)[ \t]*\n)", block + r"\1",
                gc, count=1, flags=re.M)
            if n:
                gc = new_gc
                changed += 1
                conanfile.output.info("config.guess: HarmonyOS case added")
            else:
                conanfile.output.warning(
                    "config.guess: NetBSD anchor not found")
        else:
            conanfile.output.info("config.guess: HarmonyOS already present")

        with open(cg_path, "w", encoding="utf-8", newline="") as fh:
            fh.write(gc)

    if cs_path is None:
        conanfile.output.info("config.sub not found — no config.sub edits")
    else:
        conanfile.output.info("config.sub: " + cs_path)
        with open(cs_path, "r", encoding="utf-8", newline="") as fh:
            sc = fh.read()

        if "ohos-linux" not in sc:
            new_sc, n = re.subn(
                r"(\s*android-linux\)\s*\n"
                r"((?:\s*)basic_machine=\$field1-unknown\s*\n)"
                r"((?:\s*)basic_os=linux-android\s*\n)"
                r"(\s*;;\s*\n))",
                r"\1"
                r"\tohos-linux)\n"
                r"\2"
                r"\3"
                r"\4",
                sc, count=1)
            if n:
                sc = new_sc
                changed += 1
                conanfile.output.info("config.sub: ohos-linux triplet added")
            else:
                conanfile.output.warning(
                    "config.sub: android-linux anchor not found")
        else:
            conanfile.output.info("config.sub: ohos-linux already present")

        if not re.search(r"gnu\*\s*\|\s*android\*\s*\|\s*ohos\*", sc):
            new_sc, n = re.subn(
                r"(gnu\*\s*\|\s*android\*)", r"\1 | ohos*", sc, count=1)
            if n:
                sc = new_sc
                changed += 1
                conanfile.output.info("config.sub: ohos* added to OS list")
            else:
                conanfile.output.warning(
                    "config.sub: gnu*|android* anchor not found")
        else:
            conanfile.output.info("config.sub: ohos* already in OS list")

        if "linux-ohos" not in sc:
            new_sc, n = re.subn(
                r"(linux-uclibc\*[/-]?\s*)\)", r"\1| linux-ohos*)", sc,
                count=1)
            if n:
                sc = new_sc
                changed += 1
                conanfile.output.info(
                    "config.sub: linux-ohos added to kernel list")
            else:
                conanfile.output.warning(
                    "config.sub: linux-uclibc anchor not found")
        else:
            conanfile.output.info("config.sub: linux-ohos already in kernel list")

        with open(cs_path, "w", encoding="utf-8", newline="") as fh:
            fh.write(sc)

    # rewriting a file keeps its mode, but be explicit: configure runs both
    # helpers as `$SHELL $ac_aux_dir/config.sub` and a lost exec bit turns
    # into "cannot run .../config.sub"
    for helper in (cg_path, cs_path):
        if helper:
            os.chmod(helper, 0o755)

    conanfile.output.info(
        "OHOS triplet patch applied ({} change(s))".format(changed))


def _automake_count(text, label):
    """Parse `# LABEL: N` from an automake parallel-tests test-suite.log."""
    for line in text.splitlines():
        if line.startswith("# " + label + ":"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                return 0
    return 0


class UnuranConan(ConanFile):
    name = "unuran"
    version = "1.12.0"
    description = ("UNU.RAN: Universal Non-Uniform RANdom number generator "
                   "library (non-uniform variate generation)")
    license = "GPL-2.0-or-later"
    homepage = "https://statmath.wu.ac.at/unuran/"
    url = ""  # CI fills this
    topics = ("unuran", "random-number-generation", "statistics", "sampling",
              "monte-carlo", "root")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "unuran is supported only on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _prepare_build_env(self):
        """OHOS keeps /tmp read-only and the worker storage is HMDFS, so
        configure's own `mktemp -d ./confXXXXXX` bottom (and anything else
        that reaches for a system temp dir) must be handed a writable
        TMPDIR.  Same approach as libxdg/1.2.3 and accel-config/4.1.9.

        [shell_getcwd]: HMDFS also hides the build tree's parent chain
        from getcwd(), which leaves `pwd` empty for every shell libtool
        spawns while linking the relative .la sub-libraries of src/ and
        tests/ — `abs_ladir=`cd "$ladir" && pwd`` then yields the bare
        name "methods" and llvm-ar is asked to open the non-existent
        /methods/.libs/libmethods.a (adms 2.3.7 / nspr 4.37 /
        aribb24 1.0.4).  Pin the process cwd and export PWD so bash's pwd
        builtin resolves through the logical path instead of getcwd().
        Callers that make into a subdirectory re-point PWD with
        _enter_subdir() first.
        """
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.chmod(tmpdir, 0o755)
        os.environ["TMPDIR"] = tmpdir
        try:
            os.chdir(self.build_folder)
        except OSError:
            self.output.warning(
                "chdir(build_folder) failed; relying on the PWD fallback")
        os.environ["PWD"] = self.build_folder

    def _enter_subdir(self, subdir):
        """Move the process into a subdirectory and keep PWD in step with it.

        `make -C <subdir>` chdirs without rewriting PWD, so a shell started
        in the subdirectory would find a $PWD naming the *parent*, fail
        bash's same_file() check and drop it again — and `pwd` would be
        empty exactly where libtool needs it (`abs_ladir=`cd "$ladir" &&
        pwd`` then feeds a bogus path to llvm-ar).  Only a *real* chdir
        keeps PWD == `.`, which is what makes bash answer `pwd` from the
        logical path and never call getcwd() at all.  Setting PWD alone is
        not enough: the mismatch is exactly the condition bash reacts to.
        """
        path = os.path.join(self.build_folder, subdir)
        try:
            os.chdir(path)
        except OSError:
            self.output.warning(
                "chdir(%s) failed; relying on the PWD fallback" % path)
        os.environ["PWD"] = path
        return path

    def generate(self):
        # NOTE: deliberately *not* _prepare_build_env() here.  Conan calls
        # generate() inside `with chdir(generators_folder)` precisely
        # because AutotoolsToolchain.generate_args() writes conanbuild.conf
        # through save_toolchain_args(), which builds the path from a
        # *relative* filename and therefore lands in whatever the process
        # cwd happens to be.  chdir'ing to build_folder here would drop
        # conanbuild.conf one level up from build-release/conan/, and the
        # very next `Autotools(self)` would die with
        # "The file .../build-release/conan/conanbuild.conf does not
        # exist. Please, make sure that it was not generated in another
        # folder."  Toolchain generation needs no TMPDIR and no PWD: the
        # configure/make that do run from build(), which calls
        # _prepare_build_env() itself.
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        tc.generate()

    def build(self):
        self._prepare_build_env()
        # E007: OHOS triplet for the shipped config.guess/config.sub
        _patch_ohos_triplet(self, self.source_folder)
        # E114 + [shell_getcwd]: relax umask 077 / fall back to $PWD in the
        # shipped configure (HMDFS)
        _patch_configure_hmdfs(os.path.join(self.source_folder, "configure"))

        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make trips the HMDFS jobserver FIFO.
        # One `make` per subdirectory rather than a top-level `make`: the
        # top-level SUBDIRS list ends in `doc`, which needs makeinfo
        # (texinfo), and nothing here consumes the manual.  The subdirectory
        # is selected by chdir'ing into it (see _enter_subdir) instead of
        # `make -C`, so that PWD always names the real cwd.
        for subdir in BUILD_SUBDIRS:
            self._enter_subdir(subdir)
            autotools.make(args=["-j1"])
        # L1: the real upstream regression suite.
        # tests/Makefile.am: check_PROGRAMS 58 + TESTS = $(check_PROGRAMS)
        self._enter_subdir(CHECK_SUBDIR)
        autotools.make(target="check", args=["-j1"])
        self._emit_upstream_test_result()

    def _emit_upstream_test_result(self):
        """Emit the hmbs upstream-test marker from automake's own
        test-suite.log so the numbers come from the framework, not from the
        recipe's estimate.

        Note for anyone re-measuring by hand: re-running `make check` in a
        directory that already holds the per-test `.log` files reports a
        TOTAL below the real test count (those cases are skipped as "up to
        date").  Every measurement has to come from a clean build tree —
        which is what conan create always gives.  The real value here is
        58 with the default options (ENABLE_DEPRECATED=no and no external
        Mathematica), i.e. check_PROGRAMS minus nothing.
        """
        suite_logs = []
        for root, _dirs, files in os.walk(self.build_folder):
            if "test-suite.log" in files:
                suite_logs.append(os.path.join(root, "test-suite.log"))
        if not suite_logs:
            raise ConanException(
                "make check produced no test-suite.log under "
                + self.build_folder)
        with open(suite_logs[0], "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        skipped = _automake_count(content, "SKIP")
        failed = (_automake_count(content, "FAIL")
                  + _automake_count(content, "XPASS")
                  + _automake_count(content, "ERROR"))
        result = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "automake-parallel-tests",
            "command": "make -C tests check",
            "discovered": _automake_count(content, "TOTAL"),
            "executed": _automake_count(content, "TOTAL") - skipped,
            "passed": _automake_count(content, "PASS") + _automake_count(content, "XFAIL"),
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))
        if result["status"] != "passed":
            self.output.error(
                "upstream make check did not pass: "
                + json.dumps(result, ensure_ascii=False))

    def package(self):
        autotools = Autotools(self)
        # `make -C src install`: src/Makefile recurses into its own SUBDIRS
        # (utils/methods/distr/.../urng) which is what installs the extra
        # unuran_* public headers; the top-level install would descend into
        # doc/ again.
        autotools.install(args=["-C", INSTALL_SUBDIR, "-j1"])
        # remove libtool *.la wrappers (they embed absolute build paths)
        for _la in _glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["unuran"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # libunuran.a reaches for log/exp/pow/sqrt from its rejection and
        # inversion kernels; a static consumer has to carry -lm.
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "unuran")
        self.cpp_info.set_property("cmake_target_name", "unuran::unuran")
        self.cpp_info.set_property("pkg_config_name", "unuran")
