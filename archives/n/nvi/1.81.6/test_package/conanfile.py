#!/usr/bin/env python3
"""test_package for nvi — actually runs the vi binary in ex-script mode.

R34: the test must execute the shipped binary (not just print a string).
We drive vi in -e -s mode with an ex substitution command piped to stdin,
then verify the file content was written back. TERMINFO is set explicitly
to the ncurses package share/terminfo (nvi requires terminal capabilities;
VirtualRunEnv only aggregates direct-dependency runenv, so we inject it
from self.dependencies["ncurses"]).
"""
import os
import shlex

from conan import ConanFile


class NviTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # ncurses is a transitive dep of nvi; declare it directly so that
        # (a) we can read its package_folder for TERMINFO, and (b) VirtualRunEnv
        # aggregates its runenv into the conanrun environment.
        self.requires("ncurses/6.6")

    def test(self):
        pkg = self.dependencies["nvi"]
        vi = os.path.join(pkg.package_folder, "bin", "vi")
        if not os.path.isfile(vi):
            raise Exception(f"vi binary not found at {vi}")

        # TERMINFO must point at ncurses terminfo db (needed by nvi to load
        # terminal capabilities); VirtualRunEnv only carries direct-dep
        # runenv, so inject from the ncurses dependency package folder.
        env_extra = ""
        try:
            ncurses = self.dependencies["ncurses"]
            terminfo = os.path.join(ncurses.package_folder, "share", "terminfo")
            if os.path.isdir(terminfo):
                env_extra = (
                    f"TERMINFO={shlex.quote(terminfo)} "
                    f"TERMINFO_DIRS={shlex.quote(terminfo)} "
                )
        except Exception:
            pass

        bash = os.environ.get("CONFIG_SHELL", "bash")
        workdir = self.build_folder
        cmd = (
            f"{env_extra}VI_BIN={shlex.quote(vi)} "
            f"TEST_WORKDIR={shlex.quote(workdir)} "
            f"{bash} test.sh"
        )
        # env="conanrun" also activates ncurses packages runenv (LD_LIBRARY_PATH etc.)
        self.run(cmd, env="conanrun")