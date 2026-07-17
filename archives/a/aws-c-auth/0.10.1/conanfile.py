import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


def _export_local_aws_recipes(conanfile, refs):
    repo_root = os.path.abspath(os.path.join(conanfile.recipe_folder, "..", "..", "..", ".."))
    for ref in refs:
        name, version = ref.split("/", 1)
        dep_dir = os.path.join(repo_root, "archives", "a", name, version)
        if not os.path.isfile(os.path.join(dep_dir, "conanfile.py")):
            conanfile.output.warning(f"local dependency recipe not found: {ref}")
            continue
        conanfile.output.info(f"Exporting local dependency recipe: {ref}")
        conan_cmd = [shutil.which("conan")] if shutil.which("conan") else [sys.executable, "-m", "conan"]
        subprocess.run(conan_cmd + ["export", dep_dir], check=True)


class AwsCAuthConan(ConanFile):
    name = "aws-c-auth"
    version = "0.10.1"
    description = "C99 library implementation of AWS client-side authentication"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-auth"
    url = "https://github.com/awslabs/aws-c-auth"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        _export_local_aws_recipes(self, [
            "aws-c-common/0.12.6",
            "aws-c-cal/0.9.13",
            "aws-c-compression/0.3.2",
            "aws-c-io/0.26.3",
            "aws-c-http/0.10.14",
            "aws-c-sdkutils/0.2.4",
        ])
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def requirements(self):
        self.requires("aws-c-common/0.12.6")
        self.requires("aws-c-cal/0.9.13")
        self.requires("aws-c-http/0.10.14")
        self.requires("aws-c-io/0.26.3")
        self.requires("aws-c-sdkutils/0.2.4")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.get_safe("fPIC", True))
        common_root = self.dependencies["aws-c-common"].package_folder
        tc.variables["CMAKE_MODULE_PATH"] = ";".join([
            os.path.join(common_root, "lib", "cmake"),
            os.path.join(common_root, "lib", "cmake", "aws-c-common"),
        ])
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
        self.cpp_info.libs = ["aws-c-auth"]
