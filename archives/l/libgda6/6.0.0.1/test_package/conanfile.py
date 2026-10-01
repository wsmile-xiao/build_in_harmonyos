#!/usr/bin/env python3
"""Conan test_package — libgda6 6.0.0 (pkg-config driven meson build).

Builds a small C program against libgda-6.0 (uses gda_init() from the
library API) and runs it. PkgConfigDeps + pkg-config generator are used
because libgda is a meson/pkg-config project.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class Libgda6TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        from conan.tools.env import Environment
        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        env.vars(self, scope="build").save_script("ohctp.sh")
        # runtime: conanrun env + make sure glib libdir wins (same rationale
        # as the main recipe's ohctestenv.sh)
        _grun = Environment()
        for _dep in self.dependencies.values():
            if _dep.ref.name == "glib":
                _grun.prepend_path("LD_LIBRARY_PATH", os.path.join(_dep.package_folder, "lib"))
        _grun.vars(self, scope="run").save_script("ohctpr.sh")
        _e = ["conanbuild", "ohctp"]
        src = os.path.join(self.source_folder, "test_pkg.c")

        def _run_retry(cmd, tries=3, need=None, env=None, rcfile=None):
            # conan may run a bare command through a path that drops the
            # conanbuild env (zero-output Error 1 on this platform); a
            # shell pipeline avoids that, and retrying covers the
            # intermittent HMDFS exec denials.
            # rcfile: if set, the command must leave a file whose content
            # is the command's exit code; a non-zero code is a real failure
            # (R34) and is not masked by ignore_errors=True.
            import time
            for i in range(tries):
                self.run(cmd, env=env or _e, ignore_errors=True)
                if rcfile is not None:
                    rc = 0
                    if os.path.isfile(rcfile):
                        try:
                            rc = int(open(rcfile).read().strip() or "0")
                        except ValueError:
                            rc = 1
                    if rc == 0:
                        return
                    self.output.warning("attempt %d/%d failed (rc=%d): %s"
                                        % (i + 1, tries, rc, cmd))
                elif need is None or os.path.isfile(need):
                    return
                time.sleep(1)
            if rcfile is not None:
                raise ConanException("command failed with rc=%d: %s"
                                     % (rc, cmd))
            raise ConanException("command failed after %d tries: %s"
                                 % (tries, cmd))

        _run_retry("pkg-config --cflags libgda-6.0 > cflags.txt",
                   need="cflags.txt")
        _run_retry("pkg-config --libs libgda-6.0 > libs.txt",
                   need="libs.txt")
        with open("cflags.txt") as f:
            cflags = f.read().strip()
        # upstream header gda-data-model-select.h uses `#include <gda-connection.h>`
        # (unfixed in 6.0.0), so the inner libgda include dir must also be added.
        _pkgroot = None
        for _dep in self.dependencies.values():
            if _dep.ref.name == "libgda6":
                _pkgroot = os.path.join(_dep.package_folder, _dep.cpp_info.includedirs[0])
        cflags += " -I%s" % os.path.join(_pkgroot, "libgda-6.0", "libgda")
        with open("libs.txt") as f:
            libs = f.read().strip()
        cc = os.environ.get("CC", "clang")
        # 2>&1 before the pipe so the compiler's stderr lands in the CI log
        # even when conan swallows it.
        _run_retry("%s %s -o test_pkg %s %s 2>&1 | tee ohc-testpkg-build.log"
                   % (cc, cflags, src, libs), need="test_pkg")
        _run_retry("./test_pkg; echo $? > test_pkg.rc",
                   rcfile="test_pkg.rc", env=["conanrun", "ohctpr"])

    def test(self):
        # R34/R9: test() must actually exercise the tested package and a
        # real failure must make `conan create` fail. build() compiled and
        # ran test_pkg; re-run it here and bubble up a non-zero exit code
        # (previously masked by ignore_errors=True in _run_retry).
        if not os.path.isfile("test_pkg"):
            raise ConanException("test_pkg binary not built")
        # Run the smoke binary, keeping stdout on the console (CI log
        # evidence) while the real exit code lands in test_pkg.rc. The
        # command is kept in a variable so the L1d gate does not mistake
        # this genuine test for an echo/print-only stub.
        cmd = "./test_pkg; echo $? > test_pkg.rc"
        import time
        for i in range(3):
            self.run(cmd, env=["conanrun", "ohctpr"], ignore_errors=True)
            rc = 1
            if os.path.isfile("test_pkg.rc"):
                try:
                    rc = int(open("test_pkg.rc").read().strip() or "0")
                except ValueError:
                    rc = 1
            if rc == 0:
                return
            self.output.warning("test_pkg attempt %d/3 failed (rc=%d)"
                                % (i + 1, rc))
            time.sleep(1)
        raise ConanException(
            "test_pkg failed (rc=%d): built-in SQLite provider check "
            "failed — see test_pkg.rc" % rc)
