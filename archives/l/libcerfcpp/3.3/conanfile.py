#!/usr/bin/env python3
"""Conan recipe — libcerfcpp 3.3 (CMake)."""

import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibcerfcppConan(ConanFile):
    name = "libcerfcpp"
    version = "3.3"
    description = "Self-contained complex error function library (C++ interface)"
    license = "MIT"
    homepage = "https://jugit.fz-juelich.de/mlz/libcerf"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("cerf", "faddeeva", "voigt", "dawson", "complex-error-function")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        pass

    def validate(self):
        check_min_cppstd(self, 17)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # libcerfcpp is the C++ interface of the libcerf source tree:
        # build only the C++ library, skip the C library, CLI tools and
        # man pages so the package stays a pure library.
        tc.variables["CERF_C"] = False
        tc.variables["CERF_CPP"] = True
        tc.variables["LIB_MAN"] = False
        tc.variables["LIB_RUN"] = False
        tc.variables["BUILD_TESTING"] = True
        # Upstream declares cmake_minimum_required(VERSION 3.20); keep a
        # policy floor so newer CMake (>= 4) still configures.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def _find_ctest(self):
        hmbs_cmake = os.environ.get("HMBS_CMAKE", "")
        cand = os.path.join(os.path.dirname(hmbs_cmake), "ctest")
        if hmbs_cmake and os.path.isfile(cand):
            return cand
        ctest = shutil.which("ctest")
        if ctest:
            return ctest
        raise ConanException("ctest executable not found; cannot run upstream tests")

    def _locate_ctest_dir(self):
        ctest_dir = self.build_folder
        for cand_dir in (
            os.path.join(self.build_folder, "build", "Release"),
            os.path.join(self.build_folder, "build"),
        ):
            if os.path.isfile(os.path.join(cand_dir, "CTestTestfile.cmake")):
                return cand_dir
        hits = glob.glob(
            os.path.join(self.build_folder, "**", "CTestTestfile.cmake"),
            recursive=True,
        )
        if hits:
            return os.path.dirname(hits[0])
        return ctest_dir

    def _subprocess_env(self):
        tmp = None
        for key in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key, "")
            if val and os.path.isdir(val):
                tmp = val
                break
        if not tmp:
            tmp = os.path.join(self.build_folder, "hmbs-tmp")
            os.makedirs(tmp, exist_ok=True)
        env = dict(os.environ)
        env["TMPDIR"] = tmp
        env["TMP"] = tmp
        env["TEMP"] = tmp
        return env

    def _run_upstream_tests(self):
        """Run the upstream ctest suite and print the HMBS evidence marker.

        Numbers are parsed from the real ctest output
        ("N% tests passed, M tests failed out of K"). Raises on failure so a
        red suite can never be packaged silently.
        """
        ctest = self._find_ctest()
        ctest_dir = self._locate_ctest_dir()
        self.output.info("running upstream ctest in %s" % ctest_dir)
        proc = subprocess.run(
            [ctest, "--output-on-failure"],
            cwd=ctest_dir,
            capture_output=True,
            text=True,
            env=self._subprocess_env(),
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        for line in out.splitlines():
            self.output.info("ctest: " + line)
        discovered = executed = passed = failed = 0
        skipped = 0
        m = re.search(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)", out)
        if m:
            total = int(m.group(3))
            failed = int(m.group(2))
            discovered = total
            executed = total
            passed = total - failed
        else:
            self.output.warning("Could not parse ctest summary; marking suite as failed")
        status = "passed" if proc.returncode == 0 and m and failed == 0 else "failed"
        marker = {
            "status": status,
            "framework": "ctest",
            "command": "ctest --output-on-failure",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
        print(msg, flush=True)
        self.output.info(msg)
        try:
            with open(
                os.path.join(self.build_folder, "hmbs_upstream.json"),
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(marker, handle)
        except OSError as exc:
            self.output.warning("could not persist hmbs_upstream.json: %r" % (exc,))
        if status != "passed":
            raise ConanException("Upstream test suite failed: " + json.dumps(marker))

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def package(self):
        copy(self, "LICENSE*", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()
        try:
            src_json = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(src_json):
                res_dir = os.path.join(self.package_folder, "res")
                os.makedirs(res_dir, exist_ok=True)
                shutil.copy2(src_json, os.path.join(res_dir, "hmbs_upstream.json"))
        except OSError as exc:
            self.output.warning("could not stage hmbs_upstream.json: %r" % (exc,))

    def package_info(self):
        self.cpp_info.libs = ["cerfcpp"]
        self.cpp_info.set_property("cmake_file_name", "cerf")
        self.cpp_info.set_property("cmake_target_name", "cerf::cerfcpp")
        self.cpp_info.set_property("pkg_config_name", "libcerf")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("m")
