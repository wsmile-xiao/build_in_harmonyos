#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LeelaZeroConan(ConanFile):
    name = "leela-zero"
    version = "0.17"
    description = "Go engine based on the AlphaGo Zero approach"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/leela-zero/leela-zero"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("boost/1.90.0.1.1")
        self.requires("zlib/1.3.1.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("leela-zero is only supported on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("leela-zero supports OHOS armv8 only")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        sources = self.conan_data["sources"]
        get(self, **sources["main"], filename="leela-zero-0.17.tar.gz", strip_root=True)
        get(
            self,
            **sources["eigen"],
            filename="eigen-3.4.0.tar.gz",
            destination=os.path.join(self.source_folder, "src", "Eigen"),
            strip_root=True,
        )
        get(
            self,
            **sources["googletest"],
            filename="googletest-1.15.2.tar.gz",
            destination=os.path.join(self.source_folder, "gtest"),
            strip_root=True,
        )
        boost_overlay = os.path.join(self.source_folder, "_boost_compat", "include")
        format_source = os.path.join(self.source_folder, "_boost_format")
        get(
            self,
            **sources["boost_format"],
            filename="boost-format-1.90.0.tar.gz",
            destination=format_source,
            strip_root=True,
        )
        copy(
            self,
            "*",
            src=os.path.join(format_source, "include", "boost"),
            dst=os.path.join(boost_overlay, "boost"),
        )
        spirit_source = os.path.join(self.source_folder, "_boost_spirit")
        get(
            self,
            **sources["boost_spirit"],
            filename="boost-spirit-1.90.0.tar.gz",
            destination=spirit_source,
            strip_root=True,
        )
        copy(
            self,
            "*",
            src=os.path.join(spirit_source, "include", "boost", "spirit"),
            dst=os.path.join(boost_overlay, "boost", "spirit"),
        )
        apply_conandata_patches(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["USE_CPU_ONLY"] = True
        tc.variables["BUILD_TESTING"] = True
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.variables["BOOST_COMPAT_INCLUDE_DIR"] = os.path.join(
            self.source_folder, "_boost_compat", "include"
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        test_executable = os.path.join(self.build_folder, "tests")
        # OHOS ships a read-only /tmp, but gtest captures streams to
        # /tmp/gtest_captured_stream.XXXXXX. Redirect TMPDIR to a
        # writable scratch dir under the build folder for the test run.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        prev_tmpdir = os.environ.get("TMPDIR")
        os.environ["TMPDIR"] = tmpdir
        try:
            self.run(test_executable, env="conanrun", cwd=os.path.join(self.build_folder, ".."))
        finally:
            if prev_tmpdir is None:
                os.environ.pop("TMPDIR", None)
            else:
                os.environ["TMPDIR"] = prev_tmpdir

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
