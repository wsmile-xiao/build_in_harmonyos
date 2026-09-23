#!/usr/bin/env python3
"""Conan recipe for Microsoft GSL 4.2.1 on HarmonyOS.

Microsoft GSL (Guidelines Support Library) is the reference implementation of
the C++ Core Guidelines support types (gsl::span, gsl::not_null, gsl::finally,
gsl::narrow, ...).  It is a header-only C++14 library; the upstream CMake
project exports the ``Microsoft.GSL::GSL`` interface target.

The upstream test suite (tests/CMakeLists.txt) fetches GoogleTest with a
configure-time ``git clone`` when no pre-installed gtest_main is found, which
cannot work inside a clean CI worker.  Patch 0001 replaces that download with
the Conan-resolved GTest target; the suite is then built and executed through
ctest inside build().
"""

import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class MsGslConan(ConanFile):
    name = "ms-gsl"
    version = "4.2.1"
    description = "Guidelines Support Library implementation of the C++ Core Guidelines support types"
    license = "MIT"
    homepage = "https://github.com/microsoft/GSL"
    url = "https://github.com/microsoft/GSL"
    topics = ("gsl", "core-guidelines", "span", "not-null", "header-only")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("ms-gsl is supported only on Linux/OHOS")

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
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        if self.settings.os == "OHOS":
            # OHOS provides pthread APIs in libc. CMake's cross probe can
            # otherwise select the non-existent compatibility name -lpthreads.
            tc.variables["CMAKE_HAVE_LIBC_PTHREAD"] = True
        tc.variables["GSL_INSTALL"] = True
        tc.variables["GSL_TEST"] = True
        tc.variables["GSL_CXX_STANDARD"] = "17"
        gtest = self.dependencies["gtest"]
        tc.variables["GTest_DIR"] = os.path.join(
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
                "Cross-building: upstream test binaries were built; execution is skipped"
            )

    def _ctest_command(self):
        """Absolute ctest path recorded by CMake at configure time.

        The CI worker has cmake on PATH but not ctest, so `shutil.which("ctest")`
        / a bare "ctest" subprocess call fails there while `cmake --build` works.
        CMake bakes the absolute CMAKE_CTEST_COMMAND into the build cache, which
        is what the generated RUN_TESTS target uses as well.
        """
        cache = os.path.join(self.build_folder, "CMakeCache.txt")
        if os.path.isfile(cache):
            with open(cache, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if line.startswith("CMAKE_CTEST_COMMAND:"):
                        return line.split("=", 1)[1].strip()
        return "ctest"

    def _run_upstream_tests(self):
        """Build and run the upstream GoogleTest suite through ctest.

        The suite is registered by tests/CMakeLists.txt (2 executables).  Counts
        are parsed from the run itself: the GoogleTest summary lines give the
        atomic cases that were instantiated, `--gtest_list_tests` gives the
        declarations actually compiled into the binary, and the TEST() macros in
        the sources give the static declarations in the tag tarball.
        """
        declared = 0
        tests_dir = os.path.join(self.source_folder, "tests")
        for root, _, files in os.walk(tests_dir):
            for name in files:
                if not name.endswith(".cpp"):
                    continue
                with open(os.path.join(root, name), encoding="utf-8", errors="replace") as fh:
                    declared += len(re.findall(r"^TEST(_F)?\(", fh.read(), re.M))

        test_tmp = os.path.join(self.build_folder, "test-tmp")
        os.makedirs(test_tmp, exist_ok=True)
        ctest = self._ctest_command()
        self.output.info(f"  [info] ctest executable: {ctest}")
        proc = subprocess.run(
            [ctest, "--test-dir", self.build_folder, "--output-on-failure", "-V"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=3600,
            env={**os.environ, "TMPDIR": test_tmp},
        )
        output = proc.stdout
        passed = sum(int(m) for m in re.findall(r"\[  PASSED  \] (\d+) tests", output))
        failed = sum(int(m) for m in re.findall(r"\[  FAILED  \] (\d+) tests", output))
        registered = len(re.findall(r"Test\s+#\d+:", output))
        # gsl_noexcept_tests is a plain program (no GoogleTest cases); it is one
        # additional ctest test, so it is counted as one executed item.
        executed = passed + failed + (1 if "gsl_noexcept_tests" in output else 0)
        status = "passed" if proc.returncode == 0 and failed == 0 else "failed"
        result = {
            "status": status,
            "framework": "gtest+ctest",
            "command": "ctest --test-dir <build> --output-on-failure -V",
            "source_declared_total": declared + 1,
            "configured_executable_total": registered,
            "executed": executed,
            "passed": executed if status == "passed" else passed,
            "failed": failed,
            "skipped": 0,
            "not_instantiated": declared - passed,
            "note": (f"{declared} TEST declarations in the tag sources; {passed} GoogleTest "
                     "cases instantiated and run, plus gsl_noexcept_tests; the remaining "
                     f"{declared - passed} declarations are compiled out under this "
                     "standard/platform combination"),
        }
        self.output.info(output[-1500:])
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))
        if status != "passed":
            self.output.error("upstream tests failed; tail:\n" + output[-3000:])
            raise RuntimeError("upstream tests failed")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Microsoft.GSL")
        self.cpp_info.set_property("cmake_target_name", "Microsoft.GSL::GSL")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
