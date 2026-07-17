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

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        # 编译 LuaJIT
        luajit_dir = os.path.join(self.source_folder, "deps", "luajit")
        self.run(f"cd {luajit_dir} && make -j$(nproc)")
        # 编译 luv
        cmake = CMake(self)
        cmake.configure(variables={
            "BUILD_MODULE": "OFF",
            "LUV_USE_SYSTEM_LIBUV": "ON",
            "WITH_SHARED_LIBUV": "ON",
            "LUAJIT_INCLUDE_DIR": os.path.join(luajit_dir, "src"),
            "LUAJIT_LIBRARIES": os.path.join(luajit_dir, "src", "libluajit.a")
        })
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["luv"]
