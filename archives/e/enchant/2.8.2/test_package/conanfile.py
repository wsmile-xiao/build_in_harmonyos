#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import load


class EnchantTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        package = self.dependencies["enchant"].package_folder
        required = [
            "include/enchant-2/enchant.h",
            "lib/pkgconfig/enchant-2.pc",
            "bin/enchant-2",
            "bin/enchant-lsmod-2",
            "licenses/COPYING.LIB",
        ]
        missing = [x for x in required if not os.path.exists(os.path.join(package, x))]
        if missing:
            raise ConanException(f"PACKAGE_VALIDATION missing={missing}")
        la_files = [
            os.path.join(root, name)
            for root, _, names in os.walk(package)
            for name in names
            if name.endswith(".la")
        ]
        if la_files:
            raise ConanException(f"PACKAGE_VALIDATION unexpected_libtool_archives={la_files}")
        pc = load(self, os.path.join(package, "lib", "pkgconfig", "enchant-2.pc"))
        if package not in pc or "-lenchant-2" not in pc:
            raise ConanException("PACKAGE_VALIDATION invalid enchant-2.pc")
        self.output.info("PACKAGE_VALIDATION_RESULT checks=7 passed=7 failed=0 status=PASS")
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_enchant"), env="conanrun")
        self.output.info("CONSUMER_ENCHANT_TESTS_RESULT assertions=7 passed=7 failed=0 status=PASS")
        self.run(f'"{os.path.join(package, "bin", "enchant-2")}" -v', env="conanrun")
        self.run(f'"{os.path.join(package, "bin", "enchant-lsmod-2")}" -version', env="conanrun")
        self.output.info("COMMAND_SMOKE_RESULT commands=2 passed=2 failed=0 status=PASS")
