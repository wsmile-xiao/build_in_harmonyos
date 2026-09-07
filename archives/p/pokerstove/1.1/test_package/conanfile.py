#!/usr/bin/env python3
"""Conan test_package for pokerstove 1.1 (R34: substantive tests).

L1 consumer test, run by `conan create`:
  1. C++ consumer links peval+penum, calls Card/CardSet parsing,
     HoldemHandEvaluator and ShowdownEnumerator::calculateEquity,
     asserting the canonical AcAs vs Kh4d equity values
  2. Executes the packaged ps-eval CLI on a real equity query and
     verifies the printed equity (97.6768% / 2.32323%)
  3. Executes the packaged ps-colex CLI and verifies colex indices
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PokerstoveTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # pokerstove public headers #include <boost/...> (CardSet.h ->
        # boost/operators.hpp etc.), so the consumer declares boost
        # explicitly — CMakeDeps then generates boost's full config
        # (include dirs) for the consumer context.
        self.requires("boost/1.84.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # ── 1. C++ consumer test (links peval/penum, asserts real values) ──
        cmake = CMake(self)
        cmake.test()

        # ── 2. run the packaged CLI tools (R34: real binary execution) ──
        dep = self.dependencies["pokerstove"]
        bin_dir = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0])

        # ps-eval: AcAs vs Kh4d on 5c8s9h → 97.6768% / 2.32323% equity
        eval_out = os.path.join(self.build_folder, "ps-eval.out")
        self.run(
            f'"{os.path.join(bin_dir, "ps-eval")}" --game h AcAs Kh4d --board 5c8s9h'
            f' > "{eval_out}"',
            env="conanrun",
        )
        with open(eval_out, encoding="utf-8") as f:
            out = f.read()
        assert "The hand AcAs has" in out, f"ps-eval output missing AcAs line: {out!r}"
        assert "97.6768" in out, f"ps-eval AcAs equity mismatch (expected 97.6768%): {out!r}"
        assert "2.32323" in out, f"ps-eval Kh4d equity mismatch (expected 2.32323%): {out!r}"
        print("[PASS] ps-eval equity output verified: AcAs 97.6768% / Kh4d 2.32323%")

        # ps-colex: prints the canonical-suit colex table for all 169
        # starting-hand shapes; takes no positional args (any extra arg is
        # ignored, argc==1 prints help), so pass a placeholder.
        # canonical mapping: AcAs (pair AA) -> "AcAd: 312",
        #                    Kh4d (offsuit K4) -> "Kc4d: 116"
        colex_out = os.path.join(self.build_folder, "ps-colex.out")
        self.run(
            f'"{os.path.join(bin_dir, "ps-colex")}" all > "{colex_out}"',
            env="conanrun",
        )
        with open(colex_out, encoding="utf-8") as f:
            out = f.read()
        lines = [ln for ln in out.splitlines() if ln.strip()]
        assert len(lines) == 169, f"ps-colex expected 169 canonical hands, got {len(lines)}"
        assert "2c3c: 0" in out, f"ps-colex missing first colex entry (2c3c: 0): {out[:200]!r}"
        assert "AcAd: 312" in out, f"ps-colex AA pair colex mismatch (expected AcAd: 312): {out[-200:]!r}"
        assert "Kc4d: 116" in out, f"ps-colex K4 offsuit colex mismatch (expected Kc4d: 116)"
        print("[PASS] ps-colex canonical colex table verified: 169 hands, AcAd=312, Kc4d=116")
