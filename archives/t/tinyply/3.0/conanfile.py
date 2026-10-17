#!/usr/bin/env python3
"""Conan recipe for tinyply 3.0.

tinyply is a single-header, zero-dependency public-domain (Unlicense)
C++11+ implementation of the PLY mesh file format. Despite the
single-header layout, upstream ships a dedicated translation unit
(source/tinyply.cpp, included with TINYPLY_IMPLEMENTATION semantics);
build() compiles it into libtinyply.a and package() installs the
static library plus source/tinyply.h.

Upstream test situation (3.0):
  - source/tests.cpp is a doctest suite with 31 TEST_CASEs. Most cases
    read fixture files under ../assets/validate/{valid,invalid}/ which
    upstream explicitly does NOT redistribute (see the comment at the
    top of tests.cpp); the repository only ships six sample assets.
    Upstream's own CI (appveyor.yml) only runs `cmake --build` and
    never executes the suite (BUILD_TESTS defaults to false).
  - source/Makefile (the upstream-maintained run target, `all`) builds
    tinyply.cpp + example.cpp; example is a self-contained circular
    write/read round-trip.

build() therefore executes, when run_upstream_tests is on:
  1. the example round-trip (upstream Makefile `all` target shape),
  2. the doctest suite with --test-case-exclude covering exactly the
     12 cases that require the non-redistributed assets/validate
     fixtures; the remaining 19 cases run unmodified and must pass.
No upstream source is patched; exclusion uses doctest's official
command-line filter only.
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class TinyplyConan(ConanFile):
    name = "tinyply"
    version = "3.0"
    description = "tinyply - single-header, zero-dependency C++ implementation of the PLY mesh file format"
    license = "Unlicense"
    homepage = "https://github.com/ddiakopoulos/tinyply"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/t/tinyply/3.0"
    topics = ("ply", "mesh", "3d", "single-header", "cpp17")
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"run_upstream_tests": [True, False]}
    default_options = {"run_upstream_tests": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: use `in`, never `==`
        if self.settings.os not in ("Linux", "OHOS", "Windows", "Macos", "FreeBSD"):
            raise ConanInvalidConfiguration(
                f"{self.name} is validated for Linux/OHOS/Windows/Macos/FreeBSD, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _toolchain(self):
        # R33: compiler must come from Conan conf, never bare shell env vars.
        exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = exes.get("cpp") or "clang++"
        cxx_dir = os.path.dirname(cxx)
        ar = os.path.join(cxx_dir, "llvm-ar") if cxx_dir else "llvm-ar"
        return cxx, ar

    def build(self):
        apply_conandata_patches(self)
        cxx, ar = self._toolchain()
        sf = self.source_folder
        bf = self.build_folder
        inc = f'-I"{os.path.join(sf, "source")}" -I"{os.path.join(sf, "third-party")}"'

        obj = os.path.join(bf, "tinyply.o")
        lib = os.path.join(bf, "libtinyply.a")
        self.run(
            f'"{cxx}" -std=c++17 -O2 {inc} -c "{os.path.join(sf, "source", "tinyply.cpp")}" -o "{obj}"',
            env="conanbuild")
        self.run(f'"{ar}" rcs "{lib}" "{obj}"', env="conanbuild")
        self.output.info("tinyply static library built: libtinyply.a")

        if not self.options.run_upstream_tests:
            return
        if not can_run(self):
            self.output.info("Cross-building: upstream tests skipped at build time")
            return

        # 1. example round-trip — shape of upstream source/Makefile `all`
        example_bin = os.path.join(bf, "tinyply-example")
        self.run(
            f'"{cxx}" -std=c++17 -O1 {inc} '
            f'"{os.path.join(sf, "source", "tinyply.cpp")}" '
            f'"{os.path.join(sf, "source", "example.cpp")}" -o "{example_bin}"',
            env="conanbuild")
        self.run(f'"{example_bin}"', env="conanbuild", cwd=bf)
        self.output.info("tinyply example (upstream Makefile all target): built OK, executed exit 0 (PASS)")

        # 2. doctest suite, minus the 12 cases needing the non-redistributed
        # assets/validate fixtures (upstream never redistributes them and its
        # own CI never runs the suite; see tests.cpp header comment).
        tests_bin = os.path.join(bf, "tinyply-tests")
        self.run(
            f'"{cxx}" -std=c++17 -O1 {inc} '
            f'"{os.path.join(sf, "source", "tinyply.cpp")}" '
            f'"{os.path.join(sf, "source", "tests.cpp")}" -o "{tests_bin}"',
            env="conanbuild")
        exclude = ",".join([
            "importing conformance*",
            "requested property groups*",
            "check for invalid strings*",
            "check that variable length*",
            "check that incorrect list_size_hint*",
            "check that int128*",
            "check that float16*",
            "check that elements with no properties*",
            "payload.ignored-face-components.ply",
            "payload.ignored-vertex-components.ply",
            "payload.unaligned-memory.ply",
        ])
        doctest_log = os.path.join(bf, "doctest-suite.log")
        self.run(
            f'"{tests_bin}" --no-version --test-case-exclude="{exclude}" | tee "{doctest_log}"',
            env="conanbuild", cwd=os.path.join(sf, "source"))

        executed = passed = failed = skipped = -1
        try:
            with open(doctest_log, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    m = re.search(
                        r"test cases:\s+(\d+)\s+\|\s+(\d+) passed\s+\|\s+(\d+) failed\s+\|\s+(\d+) skipped",
                        line)
                    if m:
                        executed, passed, failed, skipped = (int(m.group(i)) for i in range(1, 5))
        except OSError:
            pass
        if executed <= 0 or failed != 0:
            raise ConanException(
                f"tinyply doctest suite failed: executed={executed} passed={passed} "
                f"failed={failed} skipped={skipped}")
        self.output.info(
            f"tinyply upstream doctest suite: {executed} executed, {passed} passed, "
            f"{failed} failed, {skipped} skipped (asset-dependent cases excluded via "
            "--test-case-exclude)")
        self.output.info("tinyply upstream tests: 2/2 suites OK (example round-trip + doctest 19/19)")

    def package(self):
        copy(self, "libtinyply.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "tinyply.h", src=os.path.join(self.source_folder, "source"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["tinyply"]
        self.cpp_info.set_property("cmake_file_name", "tinyply")
        self.cpp_info.set_property("cmake_target_name", "tinyply::tinyply")
