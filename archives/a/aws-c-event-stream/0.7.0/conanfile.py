#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Conan recipe for aws-c-event-stream 0.7.0.

aws-c-event-stream provides AWS event-stream protocol encoding/decoding
for binary message framing and CRC validation. Used by S3 Select,
Kinesis, DynamoDB Streams and other AWS services.

Build system: CMake (C99 library).

Note: We use CMAKE_PREFIX_PATH instead of CMakeDeps because the aws-c-common
cmake config creates the AWS::aws-c-common target and adds CMake modules
(AwsCFlags, AwsCheckHeaders, etc.) to CMAKE_MODULE_PATH. CMakeDeps replaces
these with different target names (aws-c-common::aws-c-common) and doesn't
add the module path, causing build failures.
"""
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AwsCEventStreamConan(ConanFile):
    name = "aws-c-event-stream"
    version = "0.7.0"
    description = "AWS event-stream protocol encoding/decoding library for binary message framing and CRC validation"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-event-stream"
    url = "https://github.com/awslabs/aws-c-event-stream"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("aws-c-common/0.14.3")
        self.requires("aws-c-io/0.27.5")
        self.requires("aws-checksums/0.2.10")
        # aws-c-cal and aws-lc are transitive deps of aws-c-io, but
        # aws-c-io's cmake config (aws-c-io-config.cmake) calls
        # find_dependency(aws-c-cal), and aws-c-cal's config calls
        # find_dependency(crypto) which needs aws-lc. Since the AWS CRT
        # recipes don't declare cpp_info.requires, we must list them
        # explicitly so conan makes their package folders available.
        self.requires("aws-c-cal/0.9.15")
        self.requires("aws-lc/5.4.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Run the upstream test suite (21 unit + 24 net cases registered via
        # AwsTestHarness add_test_case/add_net_test_case in tests/CMakeLists.txt).
        tc.variables["BUILD_TESTING"] = True
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.generate()

    def _ensure_conan2_symlink(self):
        # Some prebuilt dependency binaries (e.g. aws-c-cal/0.9.15 from the
        # registry) carry absolute DT_NEEDED paths pointing at the publishing
        # machine's ~/.conan2. On workers where CONAN_HOME is ~/.cache/conan2
        # those paths do not resolve and every test binary fails to load.
        # Create ~/.conan2 -> actual conan home so the paths resolve (same
        # workaround the test_package test() applies at runtime).
        default_conan2 = os.path.expanduser("~/.conan2")
        if os.path.exists(default_conan2):
            return
        actual_home = os.environ.get("CONAN_HOME", "")
        if not actual_home or not os.path.isdir(actual_home):
            cache_conan2 = os.path.expanduser("~/.cache/conan2")
            if os.path.isdir(cache_conan2):
                actual_home = cache_conan2
        if actual_home and os.path.isdir(actual_home):
            try:
                os.symlink(actual_home, default_conan2)
            except OSError:
                pass  # may lack permission; ctest will show load errors

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)

        # Use CMAKE_PREFIX_PATH to point to dependency package folders so that
        # find_package(aws-c-common) uses the original config file which:
        # 1. Creates the AWS::aws-c-common target (not aws-c-common::aws-c-common)
        # 2. Adds CMake modules (AwsCFlags, AwsCheckHeaders, etc.) to CMAKE_MODULE_PATH
        # aws-c-io's config calls find_dependency(aws-c-cal), which in turn
        # calls find_dependency(crypto) needing aws-lc's package folder.
        prefix_paths = []
        for dep_name in ["aws-c-common", "aws-c-io", "aws-checksums",
                         "aws-c-cal", "aws-lc"]:
            try:
                dep = self.dependencies[dep_name]
                if dep.package_folder:
                    prefix_paths.append(dep.package_folder)
            except KeyError:
                pass  # transitive dep not directly required
        cmake.configure(variables={
            "CMAKE_PREFIX_PATH": ";".join(prefix_paths)
        })
        cmake.build()

        # Run the upstream ctest suite. The test driver links the just-built
        # library through a relative DT_NEEDED (../libaws-c-event-stream.so)
        # and the OHOS dynamic linker resolves relative NEEDED against the
        # process cwd, so ctest must run from the tests build directory.
        tests_dir = os.path.join(self.build_folder, "tests")
        if os.path.isdir(tests_dir):
            self._ensure_conan2_symlink()
            ctest_log = os.path.join(self.build_folder, "ctest_output.log")
            # ctest exits non-zero when tests fail; swallow the exception and
            # surface the per-test details from the redirected log instead.
            try:
                self.run(
                    f'cd "{tests_dir}" && ctest --output-on-failure > "{ctest_log}" 2>&1',
                    env="conanbuild")
            except ConanException:
                self.output.warning(
                    "ctest exited non-zero — failing cases in ctest_output.log below")
            with open(ctest_log, "r", encoding="utf-8", errors="replace") as fh:
                out = fh.read()
            # Head of the log holds the first failure's diagnostics (dynamic
            # loader errors); tail holds the per-test result table.
            self.output.info("ctest output head:\n" + out[:3000])
            self.output.info("ctest output tail:\n" + out[-3000:])
            # ctest summary lines: "100% tests passed, 0 tests failed out of 45"
            mt = re.search(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)", out)
            if not mt:
                raise ConanException(
                    "could not parse ctest summary; full output tail:\n"
                    + out[-2000:])
            pct, failed, total = int(mt.group(1)), int(mt.group(2)), int(mt.group(3))
            if failed or pct != 100:
                failed_lines = [
                    l for l in out.splitlines()
                    if re.search(r"\*\*\*Failed|\*\*\*Timeout|Failed ", l)]
                raise ConanException(
                    f"upstream test suite failed: {failed}/{total} cases failed\n"
                    + "\n".join(failed_lines[:40]))
            marker = {
                "status": "passed",
                "framework": "ctest",
                "command": "cd build/tests && ctest --output-on-failure (AwsTestHarness driver)",
                "discovered": total,
                "executed": total,
                "passed": total - failed,
                "failed": failed,
                "skipped": 0,
            }
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
            print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False), flush=True)
            with open(os.path.join(self.build_folder, "upstream_test_result.json"),
                      "w", encoding="utf-8") as f:
                json.dump(marker, f)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Persist the upstream test evidence in the package (res/) so the
        # test_package stage can re-emit it (HMBS marker chain).
        res_json = os.path.join(self.build_folder, "upstream_test_result.json")
        if os.path.isfile(res_json):
            copy(self, "upstream_test_result.json",
                 self.build_folder, os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.libs = ["aws-c-event-stream"]
        # R32: settings.os judgment must use "in" for OHOS compatibility
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
