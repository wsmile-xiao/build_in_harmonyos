import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, load, replace_in_file


def _replace_if_needed(conanfile, path, old, new):
    content = load(conanfile, path)
    if new in content:
        return
    replace_in_file(conanfile, path, old, new)


def _clone_git_source(repo_url, expected_revision, destination):
    tmpdir = tempfile.mkdtemp(prefix="aws-c-common-git-")
    clone_dir = os.path.join(tmpdir, "src")
    try:
        os.makedirs(destination, exist_ok=True)
        subprocess.check_call(["git", "clone", "--filter=blob:none", "--no-checkout", repo_url, clone_dir])
        subprocess.check_call(["git", "-C", clone_dir, "checkout", "--detach", expected_revision])
        actual_revision = subprocess.check_output(
            ["git", "-C", clone_dir, "rev-parse", "HEAD"], text=True
        ).strip()
        if actual_revision != expected_revision:
            raise RuntimeError(
                f"unexpected git revision: {actual_revision} != {expected_revision}"
            )
        shutil.rmtree(os.path.join(clone_dir, ".git"), ignore_errors=True)
        for entry in os.listdir(clone_dir):
            src = os.path.join(clone_dir, entry)
            dst = os.path.join(destination, entry)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


class AwsCCommonConan(ConanFile):
    name = "aws-c-common"
    version = "0.12.6"
    description = "AWS SDK for C core primitives and platform abstraction"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-common"
    url = "https://github.com/awslabs/aws-c-common"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        try:
            get(self, **self.conan_data["sources"], strip_root=True)
        except Exception as exc:
            self.output.warning(
                f"aws-c-common source tarball download failed, falling back to git clone: {exc}"
            )
            _clone_git_source(
                "https://gitcode.com/gh_mirrors/aw/aws-c-common.git",
                "95515a8b1ff40d5bb14f965ca4cbbe99ad1843df",
                self.source_folder,
            )
        cmake_lists = os.path.join(self.source_folder, "CMakeLists.txt")
        _replace_if_needed(
            self,
            cmake_lists,
            'project(aws-c-common LANGUAGES C VERSION 0.1.0)',
            '''project(aws-c-common LANGUAGES C VERSION 0.1.0)
find_package(Threads REQUIRED)
if(NOT TARGET Threads::Threads)
    add_library(Threads::Threads INTERFACE IMPORTED)
endif()''',
        )
        _replace_if_needed(
            self,
            cmake_lists,
            'elseif (${CMAKE_SYSTEM_NAME} STREQUAL "Linux")',
            'elseif (${CMAKE_SYSTEM_NAME} STREQUAL "Linux" OR ${CMAKE_SYSTEM_NAME} STREQUAL "HarmonyOS" OR ${CMAKE_SYSTEM_NAME} STREQUAL "OHOS")',
        )
        _replace_if_needed(
            self,
            cmake_lists,
            'if (UNIX AND NOT APPLE AND NOT ${CMAKE_SYSTEM_NAME} MATCHES FreeBSD|OpenBSD)',
            'if ((UNIX OR ${CMAKE_SYSTEM_NAME} STREQUAL "HarmonyOS" OR ${CMAKE_SYSTEM_NAME} STREQUAL "OHOS") AND NOT APPLE AND NOT ${CMAKE_SYSTEM_NAME} MATCHES FreeBSD|OpenBSD)',
        )

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.get_safe("fPIC", True))
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
        self.cpp_info.libs = ['aws-c-common']
        self.cpp_info.builddirs = ["lib/cmake", "lib/cmake/aws-c-common", "lib/cmake/aws-c-common/modules"]
        self.cpp_info.set_property("cmake_file_name", "aws-c-common")
        self.cpp_info.set_property("cmake_target_name", "AWS::aws-c-common")
