import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, load, replace_in_file


def _replace_if_needed(conanfile, path, old, new):
    content = load(conanfile, path)
    if old not in content:
        return
    replace_in_file(conanfile, path, old, new)


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


class AwsCIoConan(ConanFile):
    name = "aws-c-io"
    version = "0.26.3"
    description = "AWS SDK for C asynchronous IO primitives"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-io"
    url = "https://github.com/awslabs/aws-c-io"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        _export_local_aws_recipes(self, ["aws-c-common/0.12.6", "aws-c-cal/0.9.13"])
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def requirements(self):
        self.requires("aws-c-common/0.12.6")
        self.requires("aws-c-cal/0.9.13")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        cmake_lists = os.path.join(self.source_folder, "CMakeLists.txt")
        _replace_if_needed(
            self,
            cmake_lists,
            'elseif (CMAKE_SYSTEM_NAME STREQUAL "Linux" OR CMAKE_SYSTEM_NAME STREQUAL "Android")',
            'elseif (CMAKE_SYSTEM_NAME STREQUAL "Linux" OR CMAKE_SYSTEM_NAME STREQUAL "Android" OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")',
        )

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.get_safe("fPIC", True))
        tc.variables["BYO_CRYPTO"] = "ON"
        common_root = self.dependencies["aws-c-common"].package_folder
        tc.variables["CMAKE_MODULE_PATH"] = ";".join([
            os.path.join(common_root, "lib", "cmake"),
            os.path.join(common_root, "lib", "cmake", "aws-c-common"),
            os.path.join(common_root, "lib", "cmake", "aws-c-common", "modules"),
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        config = os.path.join(self.package_folder, "lib", "cmake", "aws-c-io", "aws-c-io-config.cmake")
        if os.path.exists(config):
            s2n_dependency_block = '''if (UNIX AND NOT APPLE AND NOT BYO_CRYPTO)
    find_dependency(s2n)
endif()

'''
            if s2n_dependency_block not in load(self, config):
                self.output.warning("aws-c-io s2n dependency block already absent")
                return
            replace_in_file(
                self,
                config,
                s2n_dependency_block,
                '',
            )

    def package_info(self):
        self.cpp_info.libs = ['aws-c-io']
        self.cpp_info.requires = ["aws-c-common::aws-c-common", "aws-c-cal::aws-c-cal"]
        self.cpp_info.set_property("cmake_file_name", "aws-c-io")
        self.cpp_info.set_property("cmake_target_name", "AWS::aws-c-io")
