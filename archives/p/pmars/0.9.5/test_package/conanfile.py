#!/usr/bin/env python3
"""Conan test_package — pmars 0.9.5 consumer-side verification.

R34/PF3: the test really executes the packaged binary (absolute path inside the
package just produced, never a $PATH lookup) and asserts on its behaviour:

  0. packaged binary is absolute and executable
  1. `-Q 1000` exits 95            -> PMARSVER of the 0.9.5 release
  2. banner text contains v0.9.5   -> second, independent version witness
  3. `-Q 1002` exits 184           -> 0.9.5 *plus* the curses display variant
  4. `-Q 1003` exits 4             -> 32-bit core addresses (no SMALLMEM)
  5. six shipped warriors assemble -> the six upstream `;assert` directives hold
  6. a real fight runs through ncurses -> proves the ncurses requirement is
     declared run=True (its recipe publishes TERMINFO/TERMINFO_DIRS through
     runenv_info; without that env the binary exits 1 with
     "ncurses: cannot initialize terminal type")
  7. a deliberately false `;assert` is rejected -> negative control

The assertions themselves live in test_pmars.sh so the runner summary
("SUMMARY: n/n passed") is greppable in the log.
"""
import os

from conan import ConanFile


class PmarsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        this_folder = os.path.dirname(os.path.abspath(__file__))
        script = os.path.join(this_folder, "test_pmars.sh")
        pkg_folder = self.dependencies["pmars"].package_folder
        pmars_bin = os.path.join(pkg_folder, "bin", "pmars")
        res_folder = os.path.join(pkg_folder, "res")

        # env="conanrun" is what delivers ncurses' TERMINFO/TERMINFO_DIRS to
        # the packaged binary; see notes.md.
        self.run(
            'sh "{script}" "{pmars}" "{res}"'.format(
                script=script, pmars=pmars_bin, res=res_folder
            ),
            env="conanrun",
        )
