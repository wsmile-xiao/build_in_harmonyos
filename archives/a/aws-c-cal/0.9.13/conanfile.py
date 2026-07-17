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


class AwsCCalConan(ConanFile):
    name = "aws-c-cal"
    version = "0.9.13"
    description = "AWS SDK for C cryptographic abstraction layer"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-cal"
    url = "https://github.com/awslabs/aws-c-cal"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        _export_local_aws_recipes(self, ["aws-c-common/0.12.6"])
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def requirements(self):
        self.requires("aws-c-common/0.12.6")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        config_template = os.path.join(self.source_folder, "cmake", "aws-c-cal-config.cmake")
        _replace_if_needed(
            self,
            config_template,
            '''if (NOT @BYO_CRYPTO@ AND (@AWS_USE_LIBCRYPTO_TO_SUPPORT_ED25519_EVERYWHERE@ OR (NOT WIN32 AND NOT APPLE)))
    if (@USE_OPENSSL@ AND NOT ANDROID)
        # aws-c-cal has been built with a dependency on OpenSSL::Crypto,
        # therefore consumers of this library have a dependency on OpenSSL and must have it found
        find_dependency(OpenSSL REQUIRED)
        find_dependency(Threads REQUIRED)
    else()
        list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/modules")
        find_dependency(crypto)
    endif()
endif()

''',
            '',
        )

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
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

    def package_info(self):
        self.cpp_info.libs = ['aws-c-cal']
        self.cpp_info.requires = ["aws-c-common::aws-c-common"]
        self.cpp_info.set_property("cmake_file_name", "aws-c-cal")
        self.cpp_info.set_property("cmake_target_name", "AWS::aws-c-cal")
