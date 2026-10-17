#!/usr/bin/env python3
"""Conan recipe — NumCpp 2.16.1 (header-only C++17 NumPy work-alike).

NumCpp is a header-only library: the package contains no compiled artifact,
only the 544 public headers under include/ and the upstream MIT LICENSE.

Dependencies
------------
NumCpp's public headers reference Boost behind the `NUMCPP_NO_USE_BOOST`
guard which upstream keeps DISABLED by default.  With default settings the
headers pull Boost.Math special functions, Boost.DateTime (posix_time),
Boost.Random distributions, Boost.Polynomial helpers and the Boost.Log
backend for the Logging module.  Turning the guard on would silently remove
whole modules (Special/DateTime/Logging/Polynomial/...), so the package keeps
the upstream default and requires Boost *headers* transitively.

ohpcd's published boost flavor used here (boost/1.84.0) ships the complete
Boost header tree plus the compiled static filesystem/regex/program_options/
iostreams archives.  Everything NumCpp needs at consumer compile time is
header-only, so no compiled Boost component has to be force-linked.

Upstream tests
--------------
The v2.16.1 upstream unit-test suite is Python/pytest based
(test/pytest/test_*.py: 748 test-function definitions in 25 files, 747
collectable because test_random.py defines test_seed twice) driving a compiled
pybind11 extension (test/pytest/src -> NumCppPy shared module).  Running it
needs a Python interpreter + the NumPy scientific stack (numpy/scipy/astropy/
matplotlib/mpmath/pymap3d/vectormath; upstream environment.yml pins numpy=2.2)
+ building the vendored-pybind11 binding with OHOS clang.  That stack is NOT
bundled in the pure C++ conan/CI pipeline, so conan create keeps running only
the runnable C++ subset (`test/multiple`, layer-1) and the consumer API checks
in test_package/ (layer 2).  The full pytest suite has nevertheless been
executed and recorded on an OHOS PC with the scientific venv (2026-09-04,
numpy 2.2.6): 732 passed / 12 upstream-skipped / 3 platform-difference
failures; evidence and reproduction script under reports/
(pytest-full-20260904-numpy2.2.6.log, run_upstream_pytest.sh,
pytest-failures-analysis.md).  The two gtest Logger TUs
(test/gtest/test_Logger.cpp, test_BinaryLogger.cpp) were also compiled and run
locally (5/5 gtest pass) using GTest 1.17 from the ohpcd registry plus a
locally built Boost.Log 1.84 (the published ohpcd boost flavour ships no
libboost_log / libboost_log_setup); evidence in
reports/gtest-LoggerTests-20260904.log.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import (apply_conandata_patches,
                               export_conandata_patches, get)


class NumCppConan(ConanFile):
    name = "numcpp"
    version = "2.16.1"
    description = ("NumCpp — a templatized header-only C++ implementation of "
                   "the Python NumPy library")
    license = "MIT"
    homepage = "https://github.com/dpilger26/NumCpp"
    url = "https://github.com/dpilger26/NumCpp"
    topics = ("numpy", "ndarray", "header-only", "linear-algebra", "math")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        # No patches in this revision; export_conandata_patches is a no-op here
        # but keeps the recipe future-proof if a later adaptation revision adds
        # a patches/ entry to conandata.yml.
        export_conandata_patches(self)

    def requirements(self):
        # Public headers include Boost headers unless the consumer defines
        # NUMCPP_NO_USE_BOOST.  Keep upstream default (Boost enabled) and make
        # the Boost headers available to every consumer of this package.
        self.requires("boost/1.84.0", transitive_headers=True)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # No patches apply in this revision (conandata.yml has none).
        apply_conandata_patches(self)
        self._run_upstream_cpp_subset()

    def _run_upstream_cpp_subset(self):
        """Compile & run the runnable upstream C++ subset.

        test/multiple is the only C++-runnable upstream test target that does
        not need GTest or a compiled Boost.Log: it includes the full
        NumCpp.hpp umbrella from two translation units (a NumCpp-internal
        link-boundary check) and prints random NdArrays.  Failing to compile
        or run it fails conan create (layer-1 semantics).
        """
        import json
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")

        flags = ["-std=c++17"]
        if self.settings.get_safe("compiler.libcxx") == "libc++":
            flags.append("-stdlib=libc++")
        # Boost 1.84.0 ohpcd flavor exposes this define on the boost_headers
        # component (musl lacks pthread_setcancelstate); mirror it for the
        # direct clang++ invocation used by the upstream-test compile.
        flags.append("-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE")

        numcpp_inc = os.path.join(self.source_folder, "include")
        boost_inc = os.path.join(self.dependencies["boost"].package_folder,
                                 "include")
        test_dir = os.path.join(self.source_folder, "test", "multiple")
        exe = os.path.join(self.build_folder, "numcpp_upstream_multiple")

        cmd = (f"{cxx} {' '.join(flags)} -I{numcpp_inc} -I{boost_inc} "
               f"{test_dir}/main.cpp {test_dir}/function.cpp -o {exe}")
        self.output.info(f"[numcpp] compiling upstream test/multiple: {cmd}")
        self.run(cmd)

        discovered = 1
        executed = 0
        passed = 0
        status = "compile_only"
        if can_run(self):
            self.output.info("[numcpp] running upstream test/multiple")
            self.run(f"'{exe}'", cwd=self.build_folder)
            executed = 1
            passed = 1
            status = "passed"
        else:
            self.output.info(
                "[numcpp] cannot run OHOS binaries here; upstream "
                "test/multiple verified at compile level only")

        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": status,
            "framework": "upstream-test-multiple-cpp",
            "command": os.path.basename(exe),
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": 0,
            "skipped": discovered - executed,
        }))

    def package(self):
        shutil.copytree(os.path.join(self.source_folder, "include"),
                        os.path.join(self.package_folder, "include"))
        os.makedirs(os.path.join(self.package_folder, "licenses"),
                    exist_ok=True)
        shutil.copy2(os.path.join(self.source_folder, "LICENSE"),
                     os.path.join(self.package_folder, "licenses", "LICENSE"))

    def package_info(self):
        # Upstream CMake exports the package/target as NumCpp::NumCpp; expose
        # the same names through CMakeDeps so consumers can find_package(NumCpp)
        # and link NumCpp::NumCpp exactly as documented upstream.
        self.cpp_info.set_property("cmake_file_name", "NumCpp")
        self.cpp_info.set_property("cmake_target_name", "NumCpp::NumCpp")
        self.cpp_info.set_property("pkg_config_name", "NumCpp")

        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

        # Consumers compile NumCpp headers which `#include <boost/...>`, so
        # propagate the Boost headers component of the required boost package.
        self.cpp_info.requires = ["boost::boost_headers"]

    def package_id(self):
        # Header-only: every settings combination yields identical content.
        self.info.clear()
