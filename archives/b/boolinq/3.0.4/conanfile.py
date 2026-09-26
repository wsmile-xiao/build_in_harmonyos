#!/usr/bin/env python3
"""Conan recipe for boolinq 3.0.4 — LINQ-style iterator library, header-only.

The library itself is a single header (include/boolinq/boolinq.h); the package
ships headers only.  The upstream GoogleTest suite under test/ is compiled and
executed inside build() against the Conan-provided gtest (the upstream CMake
tree needs a patch because it add_subdirectory()s git submodule directories
that are empty inside release tarballs).
"""

import json
import os
import re
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

_TEST_BINARIES = ("boolinq-test", "boolinq-test14")


class BoolinqConan(ConanFile):
    name = "boolinq"
    version = "3.0.4"
    description = "LINQ-like lazy iterators for C++ (single header)"
    license = "MIT"
    homepage = "https://github.com/k06a/boolinq"
    url = "https://github.com/k06a/boolinq"
    topics = ("linq", "iterators", "ranges", "header-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("boolinq is supported only on Linux/OHOS")

    def build_requirements(self):
        self.test_requires("gtest/1.17.0")

    def layout(self):
        cmake_layout(self)

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        gtest = self.dependencies["gtest"]
        tc.cache_variables["GTest_DIR"] = os.path.join(
            gtest.package_folder, "lib", "cmake", "GTest"
        ).replace("\\", "/")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        if can_run(self):
            self._run_upstream_tests()
        else:
            self.output.info(
                "Cross-building: upstream boolinq tests were built but not executed"
            )

    def _run_upstream_tests(self):
        """Run both upstream GoogleTest binaries and report honest counts.

        Fails the build (non-zero self.run) if any binary fails; counts are
        parsed from the real GoogleTest summary lines, never invented.
        """
        binaries = {}
        for path in sorted(Path(self.build_folder).rglob("*")):
            if path.is_file() and path.name in _TEST_BINARIES:
                binaries.setdefault(path.name, str(path))
        missing = [name for name in _TEST_BINARIES if name not in binaries]
        if missing:
            raise ConanException(
                "upstream test binary(s) not produced by the build: " + ", ".join(missing)
            )

        executed = 0
        passed = 0
        per_binary = {}
        for name in _TEST_BINARIES:
            outfile = os.path.join(self.build_folder, name + ".gtest.txt")
            # Run, keep the full GoogleTest output both on disk (for counting)
            # and in the build log; propagate the real test exit code.
            self.run(
                f'"{binaries[name]}" > "{outfile}" 2>&1; rc=$?; cat "{outfile}"; exit $rc',
                env="conanbuild",
            )
            text = Path(outfile).read_text(encoding="utf-8", errors="replace")
            m_run = re.search(r"\[==========\] (\d+) tests? from .*? ran\.", text)
            m_pass = re.search(r"\[  PASSED  \] (\d+) tests?\.", text)
            if not m_run or not m_pass:
                raise ConanException(
                    f"cannot parse GoogleTest summary from {name} output"
                )
            run_n, pass_n = int(m_run.group(1)), int(m_pass.group(1))
            if run_n != pass_n:
                raise ConanException(
                    f"{name}: {run_n} tests ran but only {pass_n} passed"
                )
            per_binary[name] = run_n
            executed += run_n
            passed += pass_n

        # Count the upstream source declarations (candidate N, R51 step 1).
        declared = 0
        test_dir = Path(self.source_folder) / "test"
        for src in sorted(test_dir.glob("*.cpp")):
            declared += len(
                re.findall(r"(?m)^\s*TEST(?:_F|_P)?\s*\(", src.read_text(encoding="utf-8"))
            )

        result = {
            "status": "passed",
            "framework": "gtest",
            "source_declared_total": declared,
            "executed": executed,
            "passed": passed,
            "failed": executed - passed,
            "skipped": 0,
            "binaries": per_binary,
        }
        if executed != declared:
            result["note"] = (
                f"declared {declared} vs executed {executed}: difference must be "
                "attributed in the PR body"
            )
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))

    def package(self):
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "LICENSE*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "boolinq")
        self.cpp_info.set_property("cmake_target_name", "boolinq::boolinq")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
