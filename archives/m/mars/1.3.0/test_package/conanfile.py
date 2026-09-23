#!/usr/bin/env python3
"""Conan test_package — mars 1.3.0 (comm + xlog core).

Upstream mars ships no runnable test target in its build system for a
headless platform: the CMake tree only assembles static libs for MSVC /
ANDROID / APPLE wrappers, and the only "tests" are Android/iOS demo apps
(samples/android, samples/ios) plus gtest-style .cc files (MessageQueue_test,
stn/test_cases/*) that are not registered by any build target upstream (no
add_test anywhere — verified on the v1.3.0 tag).

test_package therefore exercises the library the way every mars consumer
does (this is also exactly what WeChat's own wrapper does at startup):

- xlog pipeline: appender_open + xlogger_SetLevel + xinfo2/xwarn2/xdebug2
  (both printf-style and TSF type-safe format) + appender_flush_sync +
  appender_close; then appender_get_current_log_path is verified to resolve
  the real file and the file is verified non-empty on disk.
- comm primitives the whole library (incl. STN) is built on: AutoBuffer
  write/roundtrip, strutil::Tokenizer, gettickcount() monotonicity.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class MarsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.build_folder, "test_mars")
            # The test binary links libc++_shared.so; on the OHOS runtime the
            # loader finds it under /system/lib64 (the profile buildenv only
            # covers build-time steps, not this test run).
            cmd = 'LD_LIBRARY_PATH="/system/lib64:$${LD_LIBRARY_PATH:+:$$LD_LIBRARY_PATH}" "%s"' % bin_path
            self.run(cmd, env="conanrun")
