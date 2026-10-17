#!/usr/bin/env python3
"""test_package for roll 2.7.0 — exercises the packaged CLI binary (R34).

test_roll.sh really runs the installed `roll` on deterministic `--test`
expressions and asserts on its measured behaviour: version banner, usage text,
single die, keep-highest/lowest operators, percentile and Fudge dice, the five
arithmetic operators, zero-sided dice, series sums, repetition groups, the
verbose roll trace, the random (non --test) code path, the positive-only mode,
and six negative cases (impossible filter, division by zero, integer overflow,
too many kept dice, missing expression, unknown symbol).  It fails when the
binary is missing or broken (CI L1e sabotages bin/ to prove this dependency).
"""
import os

from conan import ConanFile


class RollTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        self.run("{0} test_roll.sh".format(shell), env="conanrun")
