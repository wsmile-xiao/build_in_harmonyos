#!/usr/bin/env python3
"""Conan recipe — multimail 0.52 (Makefile CLI tool).

MultiMail 0.52 (wmcbrine/MultiMail tag 0.52) is an offline mail packet
reader (Blue Wave/QWK/OMEN/SOUP/OPX) with a curses-based interface.
Build system: plain GNU Makefile (no configure/CMake), in-source build
of the `mm` binary plus the mm.1 man page.

Upstream ships no test suite: no tests/ directory, no check/test target
in the Makefile, so build() does not run `make check`
(upstream_test_in_build: false, audited — see test_package/MANIFEST.yml).
HMBS_UPSTREAM_TEST_RESULT status=no_tests is emitted by
test_package/test_multimail.sh every run (re-emitted by
test_package/conanfile.py on cache-hit runs).

OHOS adaptations:
    - DEBUG=Y so the Makefile skips its `strip mm` post step (no strip
      dependency on the device).
    - CURS_DIR/LIBS overridden to the ncurses/6.6 package (upstream
      defaults CURS_DIR=. and LIBS=-lcurses, unusable on OHOS).
    - CXX resolved from Conan conf tools.build:compiler_executables
      (R33), passed explicitly on the make command line.
    - Upstream `make install` is NOT used (install -s needs strip, and
      its hardlink `ln` is unreliable on HMDFS); package() copies bin/mm
      and mm.1 manually.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class MultimailConan(ConanFile):
    name = "multimail"
    version = "0.52"
    description = (
        "MultiMail — offline mail packet reader "
        "(Blue Wave/QWK/OMEN/SOUP/OPX, curses interface)."
    )
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/wmcbrine/MultiMail"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("ncurses/6.6")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "%s is only supported on Linux/OHOS, not %s"
                % (self.name, self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # True-machine guard (bwm/0.6.3 precedent): the repo profile pins
        # SHELL/CONFIG_SHELL to HNP bash, which may be inaccessible on the
        # HMBS host; HMBS injects SHELL=/bin/sh. Save a build-scope env
        # script so every make invocation sees a usable shell plus a
        # writable TMPDIR instead of read-only /tmp.
        shell = self._usable_shell()
        tmpdir = self._usable_tmpdir(makedirs=True)
        env = Environment()
        env.define("SHELL", shell)
        env.define("CONFIG_SHELL", shell)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        env.vars(self, scope="build").save_script("multimail_hmos_fix")
        self.output.info(
            "multimail_hmos_fix: SHELL/CONFIG_SHELL=%s TMPDIR=%s"
            % (shell, tmpdir)
        )

    def build(self):
        shell = self._usable_shell()
        tmpdir = self._usable_tmpdir(makedirs=True)
        for var, val in (("SHELL", shell), ("CONFIG_SHELL", shell),
                         ("TMPDIR", tmpdir), ("TMP", tmpdir),
                         ("TEMP", tmpdir)):
            os.environ[var] = val
        cxx = self._resolve_cxx()
        self.output.info(
            "multimail build shell=%s tmpdir=%s CXX=%s" % (shell, tmpdir, cxx)
        )
        ncurses = self.dependencies["ncurses"]
        inc = os.path.join(ncurses.package_folder, "include")
        libdirs = list(ncurses.cpp_info.libdirs or ["lib"])
        lib = os.path.join(ncurses.package_folder, libdirs[0])
        self.output.info("multimail ncurses inc=%s lib=%s" % (inc, lib))
        prefix = (
            'export SHELL="%s" && export CONFIG_SHELL="%s" && '
            'export TMPDIR="%s" && export TMP="%s" && export TEMP="%s" && '
            % (shell, shell, tmpdir, tmpdir, tmpdir)
        )
        # DEBUG=Y:OPTS=-g -Wall -pedantic with no `strip mm` post step.
        # -j1: OHOS sandbox jobserver (mkfifo) restriction.
        # CURS_DIR/LIBS: point upstream at the ncurses/6.6 package instead
        # of its defaults (CURS_DIR=. / LIBS=-lcurses).
        cmd = (
            prefix + 'make -j1 DEBUG=Y CXX="%s" CURS_DIR="%s" '
            'LIBS="-L%s -lncursesw"' % (cxx, inc, lib)
        )
        self.run(cmd, cwd=self.source_folder, env="conanbuild")
        # Upstream has no test suite (audited: no tests/ dir, no
        # check/test target in the Makefile — see test_package/
        # MANIFEST.yml upstream_test_audit). build() therefore does NOT
        # invoke make check (upstream_test_in_build: false); the
        # HMBS_UPSTREAM_TEST_RESULT status=no_tests evidence is produced
        # by test_package/test_multimail.sh in the test phase
        # (re-emitted by test_package/conanfile.py on cache-hit runs).

    def _resolve_cxx(self):
        """Return a CXX binary that exists on this host (R33).

        Prefer Conan conf tools.build:compiler_executables:cpp when the
        file exists (CI workers unchanged); otherwise resolve via PATH
        plus known true-machine SDK dirs. Pure isfile probing, no X_OK
        probing per R49.
        """
        def _ok(p):
            try:
                return bool(p) and os.path.isfile(p)
            except Exception:
                return False

        try:
            conf_cxx = (
                self.conf.get("tools.build:compiler_executables:cpp",
                              check_type=str) or ""
            ).split()[0]
        except Exception:
            conf_cxx = ""
        if _ok(conf_cxx):
            return conf_cxx
        for name in ("clang++", "c++", "g++"):
            found = shutil.which(name)
            if _ok(found):
                return found
        for d in (
            "/storage/Users/currentUser/usr/local/bin",
            os.path.join(os.path.expanduser("~"), ".harmonybrew", "bin"),
            "/data/service/hnp/bin",
            "/opt/llvm/bin",
            "/usr/local/bin",
            "/usr/bin",
        ):
            for name in ("clang++", "c++", "g++"):
                cand = os.path.join(d, name)
                if _ok(cand):
                    return cand
        return conf_cxx or "clang++"

    def _usable_shell(self):
        # HMBS capability shell=/bin/sh; never return the HNP bash path
        # even if isfile() is true for it (bwm/0.6.3 precedent).
        if os.path.isfile("/bin/sh"):
            return "/bin/sh"
        sh_which = shutil.which("sh") or ""
        if sh_which and os.path.isfile(sh_which):
            return sh_which
        return "/bin/sh"

    def _usable_tmpdir(self, makedirs=False):
        # Priority: HMBS task-local TMPDIR/TMP/TEMP (injected writable);
        # never fall back to /tmp (read-only on the true device).
        for var in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR", "HMBS_INSTALL"):
            cand = os.environ.get(var, "")
            if cand and os.path.isdir(cand):
                return cand
        tmpd = os.path.join(self.build_folder, "tmp")
        if makedirs:
            os.makedirs(tmpd, exist_ok=True)
        return tmpd

    def package(self):
        # Same stale-shell reason as build(): run everything with inline
        # good-shell exports instead of relying on profile env.
        src_bin = os.path.join(self.source_folder, "mm")
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        copy(self, "mm", src=self.source_folder, dst=bin_dir)
        try:
            if os.path.isfile(src_bin):
                self.output.info("multimail package: mm built OK")
            else:
                self.output.warning("multimail package: mm missing after build")
        except Exception as e:
            self.output.warning("multimail package probe failed: %s" % e)
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(man_dir, exist_ok=True)
        copy(self, "mm.1", src=self.source_folder, dst=man_dir)
        for pattern in ("*.la", "*.dylib"):
            import glob

            for f in glob.glob(
                os.path.join(self.package_folder, "lib", pattern)
            ):
                os.remove(f)
        for b in (os.path.join(bin_dir, "mm"),):
            try:
                if os.path.isfile(b):
                    os.chmod(b, 0o755)
            except OSError:
                pass
        try:
            self.run('ls -l "%s" 2>&1 || true' % bin_dir)
        except Exception:
            pass

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
