import os
from conan import ConanFile
from conan.tools.files import get
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.layout import basic_layout

class LuvConan(ConanFile):
    name = "luv"
    version = "1.52.1.0"
    description = "Bare libuv bindings for lua"
    homepage = "https://github.com/luvit/luv"
    license = "Apache-2.0"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("libuv/1.52.1")
        self.requires("lua/5.4.7")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(variables={
            "BUILD_MODULE": "OFF",
            "LUV_USE_SYSTEM_LIBUV": "ON",
            "WITH_SHARED_LIBUV": "ON",
            "LUA_BUILD_TYPE": "System"
        })
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["luv"]
