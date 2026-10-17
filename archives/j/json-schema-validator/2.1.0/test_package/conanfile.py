#!/usr/bin/env python3
"""Conan test_package for json-schema-validator 2.1.0."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class JsonSchemaValidatorTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 上游公共头 json-schema.hpp 会 #include <nlohmann/json.hpp>，消费端必须显式
        # require 并 find_package nlohmann_json 才能拿到其 include 目录（同仓库 cairomm
        # 等带依赖库的 test_package 模式）；仅依赖 tested_reference 时 CMakeDeps 生成的
        # config 其 FIND_DEPENDENCY_NAMES 为空，不传递该 header-only 依赖的 include 路径。
        self.requires("nlohmann_json/3.12.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} -c './test_json_schema_validator'", cwd=self.cpp.build.bindirs[0])
