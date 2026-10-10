#!/usr/bin/env python3
"""Conan test_package — libclapper 0.10.0

L1 test: verify the packaged libclapper-0.0 can be found, linked and that
the real playback-library API works on the device: library init, version
helpers and ClapperMarker object construction/introspection (no GStreamer
plugin needed, so it is deterministic on a headless OHOS device).
"""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibclapperTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The clapper public headers include GLib/GObject and GStreamer headers;
        # declare them explicitly so CMakeDeps generates their config files and
        # the chain resolves (same pattern as gstreamer / gst-plugins-base
        # test_packages).
        self.requires("glib2/2.88.0")
        self.requires("gstreamer/1.28.3")
        self.requires("gst-plugins-base/1.28.3")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_clapper")
        rc = self.run(bin_path, env="conanrun")
        # One test_package executable = one test case; it runs 10 internal
        # assertions (init/version/object). passedCount is the deterministic
        # binary exit code (0 => all assertions passed).
        passed = 1 if rc == 0 else 0
        print('HMBS_TEST_PACKAGE_RESULT=' + json.dumps({
            "executed": True,
            "passed": rc == 0,
            "command": bin_path,
            "discovered": 1,
            "passedCount": passed,
        }))
        # 上游库无自动化测试（详见 test_package/MANIFEST.yml upstream_test_audit
        # 与 conanfile.py build() 中的 _audit_upstream_tests 真机 grep）：
        # clapper 0.10.0 唯一测试在 src/bin/clapper-app/data（appstream/
        # gsettings/desktop 校验），属于 app 组件，本配方不构建（clapper-app
        # =disabled）；核心 clapper 库的 meson 不注册任何 test()。
        audit_cmd = (
            "grep -rn '^ *test(' <src>/src --include='meson.build'; "
            "find <src>/src -type d \\( -name tests -o -name test \\); "
            "find <src>/src/lib/clapper -name '*test*'"
        )
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "no_tests",
            "framework": "none",
            "command": audit_cmd,
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "clapper 0.10.0 source tree ships no automated tests for the "
                "libclapper playback library: the only test() entries are "
                "appstream/gsettings/desktop validation inside src/bin/"
                "clapper-app/data (clapper-app component, not built by this "
                "recipe); no tests/ directory and no *_test sources exist "
                "under src/lib/clapper"
            ),
        }))
