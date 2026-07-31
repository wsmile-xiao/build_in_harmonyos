#!/usr/bin/env python3
"""Conan test_package — file (libmagic) 5.48

L1 test: verify libmagic links and basic functionality.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FileTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Override profile's compiler paths that point to non-existent
        # /data/service/hnp/bin/clang. Use system clang from PATH instead.
        from conan.tools.env import Environment
        env = Environment()
        env.define_path("CC", "clang")
        env.define_path("CXX", "clang++")
        envvars = env.vars(self, scope="build")
        envvars.save_script("conanfixenv")

    def build(self):
        # Fix conanbuild.sh to override profile env vars
        conanbuild_sh = os.path.join(self.generators_folder, "conanbuild.sh")
        if os.path.exists(conanbuild_sh):
            with open(conanbuild_sh, "r") as f:
                content = f.read()
            fix = (
                '\n# Override non-existent profile paths\n'
                'export CC="clang"\n'
                'export CXX="clang++"\n'
            )
            if "Override non-existent" not in content:
                with open(conanbuild_sh, "w") as f:
                    f.write(content + fix)
        # Fix conan_toolchain.cmake: profile sets CMAKE_C_COMPILER to
        # /data/service/hnp/bin/clang which doesn't exist
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if os.path.exists(toolchain):
            with open(toolchain, "r") as f:
                tc_content = f.read()
            tc_content = tc_content.replace(
                "/data/service/hnp/bin/clang", "clang"
            ).replace(
                "/data/service/hnp/bin/clang++", "clang++"
            )
            with open(toolchain, "w") as f:
                f.write(tc_content)
        cmake = CMake(self)
        cmake.configure(variables={
            "CMAKE_C_COMPILER": "clang",
            "CMAKE_CXX_COMPILER": "clang++",
        })
        cmake.build()

    def test(self):
        # Run the compiled test binary directly.
        # L0d quality gate requires self.run() in test() method.
        self.run(os.path.join(self.build_folder, "test_package"), env="conanrun")
