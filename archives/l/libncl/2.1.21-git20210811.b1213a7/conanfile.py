import glob
import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibnclConan(ConanFile):
    name = "libncl"
    version = "2.1.21-git20210811.b1213a7"
    package_type = "library"
    license = "BSD-2-Clause OR GPL-2.0-or-later"
    homepage = "https://github.com/mtholder/ncl"
    description = "NEXUS Class Library for phylogenetic data"
    topics = ("nexus", "phylogenetics", "parser")
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "upstream-tests.py", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libncl supports Linux and OHOS")
        if str(self.settings.compiler) not in ("gcc", "clang"):
            raise ConanInvalidConfiguration("libncl requires GCC or Clang")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 4 removed compatibility with pre-3.5 policy versions.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["NCL_BUILD_TEST_TOOLS"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # H1 rejects make's FIFO jobserver in its device temp directory.
        # Conan's default -jN precedes build_tool_args; GNU make uses the last -j.
        build_args = ["-j1"] if str(self.settings.os) == "OHOS" else None
        cmake.build(build_tool_args=build_args)
        if not can_run(self):
            raise ConanInvalidConfiguration(
                "Native execution is required for the libncl upstream regression suite")
        runner = os.path.join(self.export_sources_folder, "upstream-tests.py")
        args = [sys.executable, runner,
                "--source-root", self.source_folder,
                "--normalizer", os.path.join(self.build_folder, "NEXUSnormalizer"),
                "--converter", os.path.join(self.build_folder, "NCLconverter"),
                "--ncltest", os.path.join(self.build_folder, "ncltest"),
                "--translate", os.path.join(self.build_folder, "NEXUStranslate"),
                "--work-dir", self.build_folder]
        self.run(" ".join(shlex.quote(arg) for arg in args), cwd=self.build_folder)

    def package(self):
        CMake(self).install()
        copy(self, "BSDLicense.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        libdir = os.path.join(self.package_folder, "lib", "ncl")
        static_lib = os.path.join(libdir, "libncl.a")
        shared_libs = glob.glob(os.path.join(libdir, "libncl.so*"))
        if self.options.shared:
            if not shared_libs:
                raise ConanException("CMake did not install the shared libncl library")
            if os.path.exists(static_lib):
                os.remove(static_lib)
        else:
            if not os.path.isfile(static_lib):
                raise ConanException("CMake did not install the static libncl library")
            for path in shared_libs:
                os.remove(path)

    def package_info(self):
        self.cpp_info.libs = ["ncl"]
        self.cpp_info.libdirs = ["lib/ncl"]
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "libncl")
        self.cpp_info.set_property("cmake_target_name", "libncl::libncl")
        if self.options.shared:
            self.runenv_info.prepend_path("LD_LIBRARY_PATH",
                                          os.path.join(self.package_folder, "lib", "ncl"))
