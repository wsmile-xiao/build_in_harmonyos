#!/usr/bin/env python3
"""Conan test_package for libcss 0.9.2.

Consumer verification: parse an inline CSS stylesheet (including a media
query and an @import declaration), run the select engine over a single
<p> element through a minimal node-query handler (the documented NetSurf
consumer pattern), and assert the computed style:

  1. css_stylesheet_create succeeds
  2. css_stylesheet_append_data + css_stylesheet_data_done parse the
     stylesheet (body/p/.cls/#id/p:hover rules + @media screen + @import)
  3. css_select_ctx append/count (1 author sheet mounted)
  4. css_select_style over <p>: computed color == 0xffff0000 (#ff0000)
  5. p's background-color stays transparent (body rule does not apply
     to p — cascade specificity correct)
  6. teardown path is clean (no crash/leak on destroy)

The upstream test suite itself (test/ 8 binaries, 55 data files,
2759 registered cases) runs inside the recipe build() — see the
HMBS_UPSTREAM_TEST_RESULT evidence in the conan build log.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibcssTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # test.c 直接 #include <libwapcaplet/libwapcaplet.h>（node 查询
        # handler 用 lwc_string），消费者图需显式声明传递依赖
        self.requires("libwapcaplet/0.4.3")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("cannot run on this host, skipping execution")
            return
        if self.settings.os not in ("Linux", "OHOS"):
            return
        bin_path = os.path.join(self.cpp.build.bindirs[0], "libcss_consumer_test")
        # R-CI L0d / R34: test() must actually run the packaged library
        self.run(bin_path, env="conanrun")
        self.output.info("libcss consumer test passed")
