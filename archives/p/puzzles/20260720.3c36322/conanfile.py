#!/usr/bin/env python3
"""Conan recipe for puzzles (Simon Tatham's Portable Puzzle Collection)
20260720.3c36322 on HarmonyOS PC (aarch64).

Build system: CMake.  The upstream tree is a collection of small
one-player puzzle games plus standalone solver/test helper programs;
on HarmonyOS PC (which ships no GTK+ toolkit) the OHOS platform branch
added by the shipped patches builds every puzzle against the headless
command-line front end (ohos.c), producing one CLI binary per game.

Source: the official upstream git repository, pinned to the exact
commit 3c3632259d298ab62aafa8a5858823569ab1af46 (the 20260720 build
tag; upstream does not retain old release tarballs).  The recipe
clones from git and verifies the resolved HEAD against the pinned
commit (same pattern as ncmpcpp/0.10.1 in this repository).

Adaptation notes:
- cmake/setup.cmake gains a HarmonyOS/OHOS branch (patch 0001) which
  includes cmake/platforms/ohos.cmake.
- ohos.cmake (patch 0002) defines the OHOS platform: no GUI programs,
  CLI + individual puzzles built, puzzle binaries installed into
  bin/ with the same layout as the unix platform.
- ohos.c (patch 0003) is the headless command-line front end for
  HarmonyOS: --version/--list-presets/--generate/--test-solve/
  --time-generation/--save, with /dev/urandom based get_random_seed.
- test_package runs the full 50-scenario suite (10 upstream auxiliary
  unit tests + 34 in-game --test-solve + fuzzpuzz smoke + 5 OHOS
  front-end scenarios); the auxiliary helper binaries and fuzzpuzz
  are packaged into bin/ so the suite runs straight from PATH.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
)
from conan.tools.scm import Git


class PuzzlesConan(ConanFile):
    name = "puzzles"
    version = "20260720.3c36322"
    description = ("Simon Tatham's Portable Puzzle Collection - a collection "
                   "of small one-player puzzle games (37 playable games)")
    license = "MIT"
    homepage = "https://www.chiark.greenend.org.uk/~sgtatham/puzzles/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        # Conan copies export_sources into the source folder before source()
        # runs, so git clone cannot target "." directly.  Clone into a child
        # directory and merge the upstream tree up into the source folder.
        clone_folder = os.path.join(self.source_folder, "_upstream")
        git = Git(self, clone_folder)
        # git.tartarus.org is intermittently unreachable from CI workers
        # (worker network whitelist / transient SSL hangs): fail fast with
        # http low-speed + connect guards instead of hanging 3600s.
        git.clone(
            url=source["git"],
            target=".",
            args=[
                "--config", "http.lowSpeedLimit=1000",
                "--config", "http.lowSpeedTime=60",
                "--config", "http.connectTimeout=30",
            ],
        )
        git.checkout(commit=source["commit"])

        actual_commit = git.get_commit()
        if actual_commit != source["commit"]:
            raise ConanInvalidConfiguration(
                f"puzzles upstream HEAD resolved to {actual_commit}, "
                f"expected {source['commit']}"
            )

        for entry in os.listdir(clone_folder):
            if entry != ".git":
                shutil.move(os.path.join(clone_folder, entry), self.source_folder)
        shutil.rmtree(clone_folder)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream CMake does not install the auxiliary test/helper programs
        # (cliprogram targets).  Ship them in bin/ too so that test_package
        # can drive the full upstream auxiliary unit-test suite plus the
        # fuzzpuzz smoke test straight from PATH.
        # The auxiliary programs are built into auxiliary/ (subdir), while
        # fuzzpuzz is a top-level Release target; with cmake_layout the CMake
        # output dir IS self.build_folder (i.e. .../b/build/Release), so the
        # binaries live directly under it.  Use explicit shutil.copy2
        # (absolute src) so packaging is deterministic and does not depend on
        # conan copy() glob semantics.
        aux_src = os.path.join(self.build_folder, "auxiliary")
        for tool in (
            "combi-test", "divvy-test", "findloop-test", "hatgen", "hat-test",
            "latin-test", "matching", "obfusc", "penrose-legacy-test",
            "penrose-test", "sort-test", "spectre-gen", "spectre-test",
            "tree234-test",
        ):
            src = os.path.join(aux_src, tool)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(self.package_folder, "bin"))
        fuzzpuzz_src = os.path.join(self.build_folder, "fuzzpuzz")
        if os.path.isfile(fuzzpuzz_src):
            shutil.copy2(
                fuzzpuzz_src, os.path.join(self.package_folder, "bin"))
        copy(
            self,
            "LICENCE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
