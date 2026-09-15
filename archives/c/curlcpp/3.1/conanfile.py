#!/usr/bin/env python3
"""Conan recipe — curlcpp 3.1 (CMake).

curlcpp is an object-oriented C++ wrapper for libcurl (C++11). It builds a
libcurlcpp library with CMake and links the Conan-provided libcurl.
"""

import json
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get, rmdir


class CurlcppConan(ConanFile):
    name = "curlcpp"
    version = "3.1"
    description = "An object oriented C++ wrapper for CURL (libcurl)"
    license = "MIT"
    homepage = "https://github.com/JosephP91/curlcpp"
    url = "https://github.com/JosephP91/curlcpp"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        copy(self, "patches/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "curlcpp supports Linux and OHOS targets, got {}".format(self.settings.os)
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("curl/8.15.0.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["CURLCPP_USE_PKGCONFIG"] = False
        # Upstream test/ holds network-dependent example programs with no
        # ctest registration (see test_package/MANIFEST.yml audit), so the
        # upstream example tree is not built here.
        tc.cache_variables["BUILD_TEST"] = False
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
            self.options.shared or self.options.get_safe("fPIC", True)
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream audit evidence: curlcpp 3.1 registers no automated test
        # suite (no enable_testing()/add_test(); test/ holds only
        # network-dependent example programs). Emitted every build.
        upstream = {
            "status": "no_tests",
            "framework": "ctest",
            "command": "ctest --output-on-failure",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "curlcpp 3.1 上游无可接入的自动化测试套件：顶层 CMakeLists.txt "
                "从未调用 enable_testing()/add_test()/add_custom_target(check)；"
                "test/ 目录仅定义 7 个需外网访问的示例程序目标"
                "（cookie/custom_request/easy/easy_info/header/recv_header/multi），"
                "无断言、无测试框架注册，无法通过 ctest 发现或执行"
                "（详见 test_package/MANIFEST.yml 审计）"
            ),
        }
        marker = "HMBS_UPSTREAM_TEST_RESULT={}".format(
            json.dumps(upstream, ensure_ascii=False)
        )
        print(marker, flush=True)
        self.output.info(marker)

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["curlcpp"]
        # 公开头文件直接 #include <curl/curl.h>，必须透传 libcurl 的头文件与链接。
        self.cpp_info.requires = ["curl::curl"]
        self.cpp_info.set_property("cmake_file_name", "curlcpp")
        self.cpp_info.set_property("cmake_target_name", "curlcpp::curlcpp")
        self.cpp_info.set_property("pkg_config_name", "curlcpp")
