#!/usr/bin/env python3
"""Conan recipe — nanomsg 1.2 (CMake), HarmonyOS PC 适配."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class NanomsgConan(ConanFile):
    name = "nanomsg"
    version = "1.2"
    description = "nanomsg 高性能消息队列库（零代理通信原语：pair/bus/pipeline/pubsub/reqrep/survey + inproc/ipc/tcp/ws 传输）"
    license = "MIT"
    homepage = "https://nanomsg.org/"
    url = "https://github.com/nanomsg/nanomsg"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 文档构建需要 asciidoctor（CI 环境无），关闭
        tc.variables["NN_ENABLE_DOC"] = "OFF"
        # 上游测试在 conan create 之外的独立源码构建中真跑（本地 ctest 43 项，见 notes.md）；
        # test_package 里另行做消费者级验证
        tc.variables["NN_TESTS"] = "OFF"
        tc.variables["NN_TOOLS"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["nanomsg"]
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.set_property("cmake_file_name", "nanomsg")
        self.cpp_info.set_property("cmake_target_name", "nanomsg::nanomsg")
        self.cpp_info.set_property("pkg_config_name", "nanomsg")
