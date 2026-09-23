#!/usr/bin/env python3
"""Conan test_package — aws-c-event-stream 0.7.0 (CMake).

L1 test: verifies aws-c-event-stream library loads and API can be called.
Emits HMBS machine-evidence markers (HMBS_TEST_PACKAGE_RESULT /
HMBS_UPSTREAM_TEST_RESULT) at the end of test() for the CI PR reporter.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout

# Consumer smoke checks executed by test.c:
#   1. allocator NULL check + library init
#   2. aws_event_stream_message_init roundtrip
#   3. message total_length >= prelude(12)+trailer(4)
#   4. message buffer non-NULL after init
TEST_PACKAGE_CHECKS = 4


class AwsCEventStreamTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # aws-c-cal's pre-built .so has DT_NEEDED with absolute paths from
        # the build machine's ~/.conan2. On CI workers where CONAN_HOME !=
        # ~/.conan2 (e.g. ~/.cache/conan2), create a symlink so the
        # absolute paths resolve.
        default_conan2 = os.path.expanduser("~/.conan2")
        if not os.path.exists(default_conan2):
            actual_home = os.environ.get("CONAN_HOME", "")
            if not actual_home or not os.path.isdir(actual_home):
                cache_conan2 = os.path.expanduser("~/.cache/conan2")
                if os.path.isdir(cache_conan2):
                    actual_home = cache_conan2
            if actual_home and os.path.isdir(actual_home):
                try:
                    os.symlink(actual_home, default_conan2)
                except OSError:
                    pass  # may lack permission

        test_binary = os.path.join(self.cpp.build.bindir, "test_aws_c_event_stream")
        self.run(test_binary, env="conanrun")

        # HMBS machine-evidence markers for the CI PR reporter
        tp_marker = {
            "executed": True,
            "passed": True,
            "command": "test_aws_c_event_stream (consumer smoke: init/message roundtrip/length/buffer)",
            "discovered": TEST_PACKAGE_CHECKS,
            "passedCount": TEST_PACKAGE_CHECKS,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker, ensure_ascii=False))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker, ensure_ascii=False), flush=True)

        # Re-emit the upstream test result persisted by the main recipe
        # (res/upstream_test_result.json — written by build() after the
        # upstream ctest suite passed).
        upstream_json = os.path.join(
            self.dependencies["aws-c-event-stream"].package_folder,
            "res", "upstream_test_result.json")
        if not os.path.isfile(upstream_json):
            raise ConanException(
                f"upstream_test_result.json missing from package res/: {upstream_json}")
        with open(upstream_json, "r", encoding="utf-8") as fh:
            ut_marker = json.load(fh)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(ut_marker, ensure_ascii=False))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(ut_marker, ensure_ascii=False), flush=True)
