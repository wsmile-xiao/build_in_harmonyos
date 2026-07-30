import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class LuaProctitleTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # CMakeDeps only guarantees config files for direct test requirements.
        # The module's Lua dependency must therefore be declared here too.
        self.requires("lua/5.4.8")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        module_dir = os.path.join(
            self.dependencies["lua-proctitle"].package_folder,
            "lib", "lua", "5.4",
        )
        cmake.configure(variables={"PROCTITLE_MODULE_DIR": module_dir})
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("Cross-building: compile and link test passed")
            return
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_lua_proctitle")
        self.run(f'"{test_bin}"', env="conanrun")
