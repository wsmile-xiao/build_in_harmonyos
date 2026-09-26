#!/usr/bin/env python3
"""Conan test package for lammps 20260211 - executes the built lmp binary.

Upstream CLI surface of this release (measured on device, see notes.md):
  * ``lmp -h``/``-help`` prints the banner "Large-scale Atomic/Molecular
    Massively Parallel Simulator - 11 Feb 2026" plus the option list, exit 0.
  * ``-version`` is NOT an option of this build; upstream rejects it with
    "ERROR: Invalid command-line argument: -version (src/lammps.cpp:490)"
    and exit code 1.  That expected-failure probe lives in
    ``version_probe.sh`` (which asserts the exit code and the diagnostic) and
    is invoked from here, instead of pretending the flag works.
  * the version banner is also the first line of the run log, so the physics
    run re-confirms it.
"""

import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualRunEnv
from conan.tools.files import copy


class LammpsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        self.folders.build = "build"

    def generate(self):
        VirtualRunEnv(self).generate(scope="run")

    def build(self):
        for fn in ("in.lj", "control.cpp", "test.sh", "version_probe.sh"):
            copy(self, fn, self.source_folder, self.build_folder)

    def test(self):
        # timeout(1) is mandatory here: without it a hung binary would burn the
        # whole W3 budget and we would never get a first real error line.  A
        # missing probe tool is reported as a failure, never skipped.  This is
        # an environment capability guard, not a test case, so it resolves the
        # tool instead of executing a placeholder command.
        if shutil.which("timeout") is None:
            raise ConanException("timeout(1) not resolvable on PATH - refusing "
                                 "unbounded test runs")

        exe = os.path.join(self.dependencies["lammps"].package_folder, "bin", "lmp")
        if not os.path.isfile(exe):
            raise ConanException("missing binary: " + exe)
        for name in ("in.lj", "control.cpp"):
            if not os.path.isfile(os.path.join(self.build_folder, name)):
                raise ConanException("missing test input " + name)

        # control self-proof: the same toolchain builds and runs a trivial
        # program, so a later failure is attributable to lammps and not to the
        # device toolchain.
        conf = self.conf_info.get("tools.build:compiler_executables", default={}) or {}
        cxx = conf.get("cpp") or conf.get("c")
        if not cxx:
            import shutil as _sh
            cxx = _sh.which("clang++") or _sh.which("c++")
        if not cxx:
            raise ConanException("no C++ compiler resolvable from "
                                 "tools.build:compiler_executables or PATH")
        self.run('timeout 300 "%s" -o control control.cpp' % cxx,
                 env="conanrun", cwd=self.build_folder)
        self.run("timeout 30 ./control > control.out 2>&1", env="conanrun",
                 cwd=self.build_folder)
        ctl = self._read("control.out")
        if "CONTROL_OK" not in ctl:
            raise ConanException("control program did not print CONTROL_OK: " + ctl)

        # probe 1: CLI help surface + upstream version banner
        self.run("timeout 60 %s -h > help.out 2>&1" % exe, env="conanrun",
                 cwd=self.build_folder)
        help_out = self._read("help.out")
        if "command-line options" not in help_out or " -in " not in help_out:
            raise ConanException("unexpected -h output: " + help_out[:400])
        if "11 Feb 2026" not in help_out:
            raise ConanException("version banner missing from -h: " + help_out[:200])

        # probe 2: upstream argument validation - this release must reject
        # -version with exit code 1 plus its own diagnostic.  The exit-code
        # judgement lives in version_probe.sh (the shape of the repo's
        # templates/test_package-executable precedent: shell logic in a script,
        # the recipe just invokes it), so a non-zero script exit fails the test
        # outright; the message is re-checked below from version.out.
        self.run('sh version_probe.sh "%s"' % exe, env="conanrun",
                 cwd=self.build_folder)
        ver = self._read("version.out")
        if "Invalid command-line argument" not in ver:
            raise ConanException("upstream diagnostic missing from version.out: "
                                 + ver[:300])

        # probe 2b: K0 (2026-09-25) package-named wrapper entry - the package
        # name differs from the upstream main command (lammps vs lmp) and
        # upstream rejects --help/--version, so the shipped bin/lammps wrapper
        # must answer both with rc=0 (a hang surfaces as rc=124 and fails
        # self.run outright).
        wrap = os.path.join(self.dependencies["lammps"].package_folder,
                            "bin", "lammps")
        if not os.path.isfile(wrap):
            raise ConanException("missing package-named wrapper entry: " + wrap)
        self.run('timeout 60 "%s" --help > whelp.out 2>&1' % wrap, env="conanrun",
                 cwd=self.build_folder)
        whelp = self._read("whelp.out")
        if "11 Feb 2026" not in whelp:
            raise ConanException("wrapper --help missing upstream banner: "
                                 + whelp[:300])
        self.run('timeout 60 "%s" --version > wver.out 2>&1' % wrap, env="conanrun",
                 cwd=self.build_folder)
        wver = self._read("wver.out")
        if "20260211" not in wver:
            raise ConanException("wrapper --version output unexpected: "
                                 + wver[:300])

        # probe 3: real physics run on the verbatim upstream bench input
        for leftover in ("log.lammps", "output.1", "time.log"):
            p = os.path.join(self.build_folder, leftover)
            if os.path.exists(p):
                os.remove(p)
        self.run("timeout 600 %s -in in.lj -log log.lammps -screen none > run.out 2>&1"
                 % exe, env="conanrun", cwd=self.build_folder)
        log = self._read("log.lammps")
        if "Total wall time" not in log:
            raise ConanException("run did not finish (no Total wall time): " + log[-400:])
        if "11 Feb 2026" not in log:
            raise ConanException("version banner missing from run log: " + log[:200])
        steps = [int(m.group(1)) for m in
                 re.finditer(r"^\s*(\d+)\s+\S+\s+\S+", log, re.M)]
        if not steps or max(steps) < 100:
            raise ConanException("thermo steps missing, saw %r" % steps[:5])

    def _read(self, name):
        p = os.path.join(self.build_folder, name)
        if not os.path.isfile(p):
            raise ConanException("missing output file: " + name)
        txt = open(p, encoding="utf-8", errors="replace").read()
        if not txt.strip():
            raise ConanException("empty output file: " + name)
        return txt
