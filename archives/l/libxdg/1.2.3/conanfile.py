#!/usr/bin/env python3
"""Conan recipe for libxdg 1.2.3 (autotools, HarmonyOS PC / aarch64).

Upstream: https://github.com/devnev/libxdg-basedir (tag `libxdg-basedir-1.2.3`)
The freedesktop.org XDG Base Directory Specification library (C, MIT).

Build notes (E007/E011/E074/E114):
  - the tarball ships no generated `configure`/`Makefile.in`, so build()
    bootstraps with `autoreconf -fi` (automake + libtool tool_requires);
  - config.guess/config.sub do not know HarmonyOS (`uname -s` = "HarmonyOS"):
    build() injects the `*-unknown-linux-ohos` triplet (E007);
  - E114: HMDFS setgid directories + `umask 077 && mktemp -d` in the
    generated configure produce a temp dir that is not writable even by its
    owner (config.status then dies on Permission denied); every `umask 077`
    becomes `umask 022` (a52dec/adcli/univalue pattern);
  - E074: the SELinux policy on the OHOS worker denies the make jobserver
    FIFO, so all make invocations use -j1;
  - patches/0001 fixes an upstream VPATH bug in the automake query tests
    (see the patch header) so that `make check` runs out-of-tree -- which is
    exactly how Conan builds every package.

The recipe is self-contained (it does not read scripts/ from the CI
checkout) so that conanfile.py + conandata.yml + patches/ alone reproduce
the CI result.
"""
import glob as _glob
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _drop_umask_077(path):
    """E114/E011: HMDFS forces setgid on directories, so `umask 077 &&
    mktemp -d` yields a drwx--S--- temp dir that even its owner cannot
    write.  Relax every umask 077 in the generated configure (the
    a52dec/adcli/univalue method)."""
    with open(path, "r", encoding="utf-8", newline="") as fh:
        data = fh.read()
    data = data.replace("umask 077", "umask 022")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(data)


def _patch_ohos_triplet(conanfile, src_dir):
    """E007: teach config.guess/config.sub the aarch64-linux-ohos triplet.

    Inline equivalent of scripts/patch-autotools-ohos.pl (staying
    self-contained on purpose).  Four edits, matching the two file
    variants this project's autotools vintage actually ships:

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
    cg_path = os.path.join(src_dir, "config.guess")
    cs_path = os.path.join(src_dir, "config.sub")
    changed = 0

    # ---------------- config.guess ----------------
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
            conanfile.output.warning("config.guess: __GLIBC__ anchor not found")
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
            conanfile.output.warning("config.guess: NetBSD anchor not found")
    else:
        conanfile.output.info("config.guess: HarmonyOS already present")

    with open(cg_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(gc)

    # ---------------- config.sub ----------------
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
            conanfile.output.warning("config.sub: android-linux anchor not found")
    else:
        conanfile.output.info("config.sub: ohos-linux already present")

    if not re.search(r"gnu\*\s*\|\s*android\*\s*\|\s*ohos\*", sc):
        new_sc, n = re.subn(r"(gnu\*\s*\|\s*android\*)", r"\1 | ohos*", sc, count=1)
        if n:
            sc = new_sc
            changed += 1
            conanfile.output.info("config.sub: ohos* added to OS list")
        else:
            conanfile.output.warning("config.sub: gnu*|android* anchor not found")
    else:
        conanfile.output.info("config.sub: ohos* already in OS list")

    if "linux-ohos" not in sc:
        new_sc, n = re.subn(
            r"(linux-uclibc\*[/-]?\s*)\)", r"\1| linux-ohos*)", sc, count=1)
        if n:
            sc = new_sc
            changed += 1
            conanfile.output.info("config.sub: linux-ohos added to kernel list")
        else:
            conanfile.output.warning("config.sub: linux-uclibc anchor not found")
    else:
        conanfile.output.info("config.sub: linux-ohos already in kernel list")

    with open(cs_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(sc)

    # rewriting a file keeps its mode, but be explicit: configure runs both
    # helpers as `$SHELL $ac_aux_dir/config.sub` and a lost exec bit turns
    # into "cannot run .../config.sub"
    for helper in (cg_path, cs_path):
        os.chmod(helper, 0o755)

    conanfile.output.info("OHOS triplet patch applied ({} change(s))".format(changed))


def _automake_count(text, label):
    """Parse `# LABEL: N` from an automake parallel-tests test-suite.log."""
    for line in text.splitlines():
        if line.startswith("# " + label + ":"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                return 0
    return 0


class LibxdgConan(ConanFile):
    name = "libxdg"
    version = "1.2.3"
    description = ("libxdg-basedir: implementation of the XDG Base Directory "
                   "Specification (freedesktop.org)")
    license = "MIT"
    homepage = "https://github.com/devnev/libxdg-basedir"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libxdg is supported only on Linux/OHOS, not "
                + str(self.settings.os))

    def build_requirements(self):
        # the tarball ships no configure/Makefile.in; autoreconf needs both
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        # conandata.yml 的 sources 是版本键控的（sources["1.2.3"]），
        # 直接展开会把 "1.2.3" 当成 get() 的关键字参数：
        #   TypeError: get() got an unexpected keyword argument '1.2.3'
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _prepare_build_env(self):
        """OHOS keeps /tmp read-only and the worker storage is HMDFS, so
        autom4te/libtoolize/configure must be handed a writable TMPDIR (the
        generated configure's own `mktemp -d ./confXXXXXX` is cwd-relative,
        but autoreconf's autom4te is not).  Same approach as
        accel-config/4.1.9.  The build directory always exists by now."""
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.chmod(tmpdir, 0o755)
        os.environ["TMPDIR"] = tmpdir

    def generate(self):
        self._prepare_build_env()
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        tc.generate()

    def build(self):
        self._prepare_build_env()
        apply_conandata_patches(self)
        # 1) bootstrap: upstream ships configure.ac only
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # 2) E007: OHOS triplet for the generated config.guess/config.sub
        _patch_ohos_triplet(self, self.source_folder)
        # 3) E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(os.path.join(self.source_folder, "configure"))

        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make trips the HMDFS jobserver FIFO
        autotools.make(args=["-j1"])
        # L1: real upstream regression suite.  automake parallel-tests:
        #     TESTS = testdump + 30 query*.N harness scripts = 31 cases
        autotools.make(target="check", args=["-j1"])
        self._emit_upstream_test_result()

    def _emit_upstream_test_result(self):
        """Emit the hmbs upstream-test marker from automake's own
        test-suite.log so the numbers come from the framework, not from the
        recipe's estimate."""
        suite_logs = []
        for root, _dirs, files in os.walk(self.build_folder):
            if "test-suite.log" in files:
                suite_logs.append(os.path.join(root, "test-suite.log"))
        if not suite_logs:
            raise ConanException(
                "make check produced no test-suite.log under " + self.build_folder)
        with open(suite_logs[0], "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        skipped = _automake_count(content, "SKIP")
        failed = (_automake_count(content, "FAIL")
                  + _automake_count(content, "XPASS")
                  + _automake_count(content, "ERROR"))
        result = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "automake-parallel-tests",
            "command": "make check",
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
        autotools.install()
        # remove libtool *.la wrappers (they embed absolute build paths)
        for _la in _glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["xdg-basedir"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
