#!/usr/bin/env python3
"""Conan recipe for ticker 1.16 - configurable text scroller.

Ticker scrolls a message across the top or bottom line of the screen, in a
manner similar to a stock ticker. Upstream is Joey Hess' ticker, maintained
since 2014 as a Debian native package by the Debian QA Group; 1.16 is the
Debian native tarball (format 3.0 (native)).

OHOS notes
----------
* Build system is a 2002-era handwritten `configure` (no config.guess,
  no AC_CANONICAL_HOST) plus a handwritten Makefile without VPATH, so the
  build runs **in-source**: `sh configure` (explicit `sh`, the HMDFS exec
  bit is unreliable) then `make -j1`. Compiler and slang -I/-L/-l flags all
  come from the Conan AutotoolsToolchain/AutotoolsDeps build env (R33); no
  bare ${CC}/${CFLAGS} anywhere.
* Hard dependency on S-Lang: configure errors out without `-lslang` and
  `slang.h`. Resolved via `requires("slang/2.3.3")`, which is already
  adapted in this repo (archives/s/slang/2.3.3).
* `-Werror=implicit-function-declaration` (tal/1.9 precedent): musl hides
  POSIX declarations under strict ANSI, and truncated 64-bit pointers only
  warn there while crashing at runtime.
* Upstream test is the single autopkgtest command
  `debian/tests/control -> Test-Command: ticker -h` (Restrictions:
  superficial). build() runs it against the just-built binary with
  LD_LIBRARY_PATH pointed at the conan slang lib, asserts the usage banner
  is really printed (a silent rc=0 would be indistinguishable from a real
  pass), and emits HMBS_UPSTREAM_TEST_RESULT with discovered=1 from that
  single deterministic source.
"""
import os
import platform
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class TickerConan(ConanFile):
    name = "ticker"
    version = "1.16"
    description = "Configurable text scroller: scrolls messages across the top or bottom line of the screen"
    license = "GPL-2.0-or-later"
    homepage = "https://joeyh.name/code/ticker/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("terminal", "scroller", "tui", "slang")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ticker is validated on Linux/OHOS only, not {self.settings.os}")

    def requirements(self):
        self.requires("slang/2.3.3")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            # Same belt-and-braces as slang/2.3.3 (E001): make sure the
            # clang driver targets OHOS even if the profile wrapper changes.
            tc.extra_cflags.append("--target=aarch64-unknown-linux-ohos")
            tc.extra_ldflags.append("--target=aarch64-unknown-linux-ohos")
        # tal/1.9 precedent: implicit declarations truncate pointers on
        # musl while only warning; fail the build instead.
        tc.extra_cflags.append("-Werror=implicit-function-declaration")
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()
        # Profile pins CONFIG_SHELL/SHELL to /data/service/hnp/bin/bash, which
        # is inaccessible on some preflight runners (configure[157] re-exec
        # fails with "inaccessible or not found"). HMBS guarantees /bin/sh,
        # so force both to /bin/sh here (c-client/2007f precedent).
        env = Environment()
        env.define("SHELL", "/bin/sh")
        env.define("CONFIG_SHELL", "/bin/sh")
        env.vars(self, scope="build").save_script("hmbs_shell")

    def _aarch64_cmd(self, *args):
        """Run an AArch64 executable natively, or through qemu-aarch64."""
        if platform.machine().lower() in ("aarch64", "arm64"):
            return shlex.join(args)
        qemu = shutil.which("qemu-aarch64")
        if qemu is None:
            raise ConanException("qemu-aarch64 is required to run AArch64 binaries here")
        return shlex.join((qemu,) + args)

    @staticmethod
    def _path_usable(path):
        """File exists and is executable; bare names go through PATH."""
        if not path:
            return False
        if os.path.sep not in path and "/" not in path:
            return shutil.which(path) is not None
        return os.path.isfile(path) and os.access(path, os.X_OK)

    def _resolve_compilers(self):
        """Resolve working C/C++ drivers with probe-then-fallback.

        The profile pins absolute drivers that are missing on some
        preflight runners (configure then fails with C compiler cannot
        create executables). Probe the configured path with --version;
        on failure fall back to same-directory siblings then PATH.
        Only CC/CXX are covered here; flags are left to the toolchain.
        """
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        conf_c = executables.get("c")
        conf_cpp = executables.get("cpp")

        def probed(path):
            if not self._path_usable(path):
                return None
            # Absolute paths can look fine on HMDFS yet be unusable, so
            # prove usability with --version before trusting them.
            if os.path.sep in path or "/" in path:
                try:
                    self.run(shlex.quote(path) + " --version",
                             quiet=True, env="conanbuild")
                except Exception:
                    return None
            return path

        cc = probed(conf_c)
        cxx = probed(conf_cpp)
        if cc is not None and cxx is not None:
            return cc, cxx

        def siblings(conf_path, names):
            out = []
            if conf_path and (os.path.sep in conf_path or "/" in conf_path):
                d = os.path.dirname(conf_path)
                for n in names:
                    out.append(os.path.join(d, n))
            for n in names:
                w = shutil.which(n)
                if w and w not in out:
                    out.append(w)
            return out

        if cc is None:
            for cand in siblings(conf_c, ("clang", "aarch64-unknown-linux-ohos-clang")):
                cc = probed(cand)
                if cc is not None:
                    break
        if cxx is None:
            for cand in siblings(conf_cpp, ("clang++", "aarch64-unknown-linux-ohos-clang++")):
                cxx = probed(cand)
                if cxx is not None:
                    break
        if cc is None or cxx is None:
            raise ConanInvalidConfiguration(
                "HMBS environment fault: no usable C/C++ compiler found "
                f"(conf c={conf_c!r} cpp={conf_cpp!r}; "
                f"resolved c={cc!r} cpp={cxx!r})")
        self.output.info(f"resolved compilers: CC={cc} CXX={cxx}")
        return cc, cxx

    def _patch_autoconf_tmpdir(self, src):
        """HMDFS unsafe_local_mktemp fix (tta 2.2 patch 0003 precedent)."""
        configure = os.path.join(src, "configure")
        try:
            with open(configure, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError as exc:
            self.output.warning("tmpdir patch skipped: %s" % exc)
            return
        orig = text
        if 'mktemp -d' in text:
            text = text.replace('mktemp -d', 'false --skip-mktemp')
            self.output.info("tmpdir patch: mktemp branch disabled")
        if 'umask 077' in text:
            text = text.replace('umask 077', 'umask 022')
            self.output.info("tmpdir patch: umask 077 -> 022")
        if text != orig:
            with open(configure, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            self.output.info("tmpdir patch applied to configure")
        else:
            self.output.warning("tmpdir patch: pattern not found in configure")

    # config.h.in template restored from the author's own repo
    # (git://git.joeyh.name/ticker, history to 1.10). The 1.16 Debian
    # native tarball ships configure.ac identical to the author's
    # configure.ac but drops config.h.in, so config.status dies with
    # "cannot find input file: `config.h.in'" after the tmpdir fix lets
    # it get that far. Content verified byte-identical in intent against
    # .hmbs/upstream-ticker/config.h.in (autoheader output for the same
    # AC_CHECK_HEADERS/AC_CHECK_FUNCS set).
    _CONFIG_H_IN = """/* config.h.in.  Generated automatically from configure.in by autoheader.  */

/* Define to empty if the keyword does not work.  */
#undef const

/* Define if you don't have vprintf but do have _doprnt.  */
#undef HAVE_DOPRNT

/* Define if you have the vprintf function.  */
#undef HAVE_VPRINTF

/* Define if you have the ANSI C header files.  */
#undef STDC_HEADERS

/* Define if you can safely include both <sys/time.h> and <time.h>.  */
#undef TIME_WITH_SYS_TIME

/* Define if you have the getopt_long function.  */
#undef HAVE_GETOPT_LONG

/* Define if you have the getopt function.  */
#undef HAVE_GETOPT

/* Define if you have the select function.  */
#undef HAVE_SELECT

/* Define if you have the <getopt.h> header file.  */
#undef HAVE_GETOPT_H

/* Define if you have the <limits.h> header file.  */
#undef HAVE_LIMITS_H

/* Define if you have the <slang.h> header file.  */
#undef HAVE_SLANG_H

/* Define if you have the <slang/slang.h> header file.  */
#undef HAVE_SLANG_SLANG_H

/* Define if you have the <sys/time.h> header file.  */
#undef HAVE_SYS_TIME_H

/* Define if you have the <unistd.h> header file.  */
#undef HAVE_UNISTD_H

/* Define if you have the slang library (-lslang).  */
#undef HAVE_LIBSLANG
"""

    def _ensure_config_h_in(self, src):
        """Restore the missing config.h.in template (Debian tarball omission)."""
        dst = os.path.join(src, "config.h.in")
        if os.path.isfile(dst):
            self.output.info("config.h.in already present, no restore needed")
            return
        with open(dst, "w", encoding="utf-8", newline="\n") as f:
            f.write(self._CONFIG_H_IN)
        self.output.info("restored missing config.h.in from author repo template")

    def _dump_configure_failure(self, src, cc, cxx):
        """Dump config.log tail plus compiler context for diagnostics."""
        for name in ("config.log",):
            log = os.path.join(src, name)
            if os.path.isfile(log):
                try:
                    with open(log, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.read().splitlines()
                    tail = "\n".join(lines[-60:])
                    self.output.error(f"{name} tail:\n{tail}")
                except Exception as exc:
                    self.output.error(f"cannot read {log}: {exc}")
            else:
                self.output.error(f"{name} not found under {src}")
        for probe in (cc, cxx):
            try:
                self.run(shlex.quote(probe) + " --version", env="conanbuild")
            except Exception as exc:
                self.output.error(f"compiler probe failed for {probe}: {exc}")

    def build(self):
        src = self.source_folder
        configure = os.path.join(src, "configure")
        # Belt-and-braces with generate()'s hmbs_shell script: make sure the
        # configure re-exec never sees the profile's missing bash path.
        os.environ["SHELL"] = "/bin/sh"
        os.environ["CONFIG_SHELL"] = "/bin/sh"
        # Profile-pinned absolute drivers can be missing on some runners;
        # resolve working drivers first and pass them explicitly so the
        # conanbuild CC from the toolchain cannot shadow them.
        cc, cxx = self._resolve_compilers()
        os.environ["CC"] = cc
        os.environ["CXX"] = cxx
        # The 1.16 Debian tarball omits config.h.in while configure still
        # instantiates CONFIG_HEADERS=config.h from it; without the file
        # config.status stops at "cannot find input file". Restore the
        # author's own template (configure.ac is identical) when missing.
        self._ensure_config_h_in(src)
        # 2002-era configure has no config.guess/CANONICAL_HOST and defaults
        # to cross_compiling=no; the OHOS clang produces a target binary the
        # build host cannot execute, so the "whether we are cross compiling"
        # run test fails with "cannot run C compiled programs". Passing only
        # --host (no --build) sets cross=maybe, which lets that failure fall
        # through to cross=yes instead of a hard error.
        host_arg = ""
        if self.settings.os == "OHOS":
            host_arg = " --host=aarch64-unknown-linux-ohos"
            # HMBS [unsafe_local_mktemp]: mktemp-made ./conf* dirs are not
            # writable on HMDFS and the stock mkdir fallback keeps umask 077,
            # so config.status dies at subs1.awk Permission denied. Patch the
            # generated configure to always use mkdir under umask 022
            # (tta/2.2 patch 0003 precedent; no PATH shim, chmod unsupported).
            self._patch_autoconf_tmpdir(src)
        try:
            self.run(f'umask 022 && CC={shlex.quote(cc)} CXX={shlex.quote(cxx)} '
                     f'CONFIG_SHELL="/bin/sh" SHELL="/bin/sh" '
                     f'sh "{configure}" --prefix="{self.package_folder}"{host_arg}',
                     cwd=src, env="conanbuild")
        except Exception:
            self._dump_configure_failure(src, cc, cxx)
            raise
        # E074/E525: no FIFO jobserver on HMDFS, keep make serial.
        # Pass the resolved driver explicitly; the Makefile bakes in the
        # configure-substituted driver, this is only belt-and-braces.
        self.run(f'make -j1 CC={shlex.quote(cc)}', cwd=src, env="conanbuild")
        self._run_upstream_tests(src)

    def _run_upstream_tests(self, src):
        """Run the single upstream autopkgtest command.

        debian/tests/control declares exactly one test::

            Test-Command: ticker -h
            Restrictions: superficial

        The tarball has no test/ or tests/ directory and the Makefile has no
        check/test target, so discovered is unconditionally 1. The only
        deterministic evidence sources are the process exit code and the
        captured help text, which must be non-empty and contain the usage
        banner (exit code 0 alone is not proof: several ticker code paths
        print usage and exit 0 without touching the terminal).
        """
        slang_lib = os.path.join(self.dependencies["slang"].package_folder, "lib")
        ticker_bin = os.path.join(src, "ticker")
        help_log = os.path.join(self.build_folder, "ticker-upstream-help.log")
        cmd = self._aarch64_cmd(ticker_bin, "-h")
        rc = self.run(f'LD_LIBRARY_PATH="{slang_lib}" {cmd} > "{help_log}" 2>&1',
                      env="conanbuild", ignore_errors=True)
        with open(help_log, "r", encoding="utf-8", errors="replace") as f:
            help_text = f.read()
        banner_ok = "Usage: ticker" in help_text
        executed = 1
        passed = 1 if (rc == 0 and banner_ok) else 0
        failed = executed - passed
        status = "passed" if failed == 0 else "failed"
        self.output.info(f"upstream `ticker -h`: rc={rc}, usage banner present={banner_ok}")
        print(f'HMBS_UPSTREAM_TEST_RESULT={{"status":"{status}",'
              f'"framework":"autopkgtest","command":"ticker -h",'
              f'"discovered":1,"executed":{executed},'
              f'"passed":{passed},"failed":{failed},"skipped":0}}')
        if failed:
            raise ConanException(
                "upstream test `ticker -h` failed "
                f"(rc={rc}, banner_ok={banner_ok}); see {help_log}")

    def package(self):
        copy(self, "ticker", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "ticker.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
