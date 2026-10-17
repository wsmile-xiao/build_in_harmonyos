#!/usr/bin/env python3
"""Consumer test package for vttest — CLI-level regression on the OHOS target.

vttest publishes no headers or libraries, so the consumer view is "run the
installed binary and observe documented behaviour":

1. the packaged executable exists and is executable;
2. ``vttest -V`` prints the exact upstream version banner and exits 0;
3. an unknown option is rejected with the documented usage text and a
   non-zero exit status (negative control);
4. the manpage shipped by ``make install`` is present;
5. a PTY-driven smoke test (pty_smoke.py) starts vttest on a real
   pseudo-terminal, selects the main-menu "Exit" item and requires a clean
   exit — the only way to exercise vttest's actual terminal-facing code path.
"""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class VttestTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross build: vttest consumer tests require the OHOS target; "
                "run them on the HarmonyOS PC device."
            )
            return

        dep = self.dependencies[self.tested_reference_str]
        bindir = dep.cpp_info.bindirs[0]
        vttest = os.path.join(bindir, "vttest")
        manpage = os.path.join(dep.package_folder, "share", "man", "man1",
                               "vttest.1")

        self.output.info(f"Running vttest consumer assertions against {vttest}")

        # 1. packaged executable present
        self.run(f'test -x "{vttest}"', env="conanrun")

        # 2. exact upstream version banner reported by -V
        self.run(
            f'"{vttest}" -V | grep -Fx "VT100 test program, version 2.7 (20251205)"',
            env="conanrun")

        # 3. -V terminates successfully
        self.run(f'"{vttest}" -V > /dev/null', env="conanrun")

        # 4. unknown option: documented usage text (negative control)
        self.run(f'"{vttest}" -Z 2>&1 | grep -F "Usage: vttest"', env="conanrun")

        # 5. unknown option: non-zero exit status (negative control)
        self.run(f'! "{vttest}" -Z > /dev/null 2>&1', env="conanrun")

        # 6. manpage installed by make install
        self.run(f'test -s "{manpage}"', env="conanrun")

        # 7. PTY smoke test: banner + main menu + clean exit on a real tty
        helper = os.path.join(self.recipe_folder, "pty_smoke.py")
        self.run(f'"{sys.executable}" "{helper}" "{vttest}"', env="conanrun")
