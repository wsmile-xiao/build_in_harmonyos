#!/usr/bin/env python3
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class PamWrapperConan(ConanFile):
    name = "pam-wrapper"
    version = "1.1.8"
    description = "A tool to test PAM applications and PAM modules"
    license = "GPL-3.0-or-later"
    homepage = "https://cwrap.org/pam_wrapper.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True],
        "with_upstream_tests": [True, False],
    }
    default_options = {
        "shared": True,
        "with_upstream_tests": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pam-wrapper requires POSIX PAM headers/libraries and LD_PRELOAD support"
            )
        if not self.options.shared:
            raise ConanInvalidConfiguration("pam-wrapper builds shared interposition libraries only")

    def requirements(self):
        self.requires("linux-pam/1.7.2")

    def build_requirements(self):
        if self.options.with_upstream_tests:
            self.test_requires(self.conan_data["requirements"]["cmocka"])

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        linux_pam = self.dependencies["linux-pam"]
        pam_include = linux_pam.cpp_info.includedirs[0]
        pam_libdir = linux_pam.cpp_info.libdirs[0]
        pam_library = os.path.join(pam_libdir, "libpam.so")
        pam_misc_library = os.path.join(pam_libdir, "libpam_misc.so")

        tc = CMakeToolchain(self)
        tc.variables["UNIT_TESTING"] = bool(self.options.with_upstream_tests)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.cache_variables["PAM_INCLUDE_DIR"] = pam_include
        tc.cache_variables["PAM_INCLUDE_DIRS"] = pam_include
        tc.cache_variables["PAM_LIBRARY"] = pam_library
        tc.cache_variables["PAM_MISC_LIBRARY"] = pam_misc_library
        tc.cache_variables["CMAKE_REQUIRED_INCLUDES"] = pam_include
        tc.cache_variables["PAM_LIBRARIES"] = pam_library
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_Python"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.with_upstream_tests:
            if str(self.settings.os) == "OHOS":
                self._sign_upstream_test_artifacts()
            test_runtime_dir = os.path.join(self.build_folder, "upstream-test-runtime")
            os.makedirs(test_runtime_dir, exist_ok=True)
            test_env = Environment()
            test_env.define("TMPDIR", test_runtime_dir)
            with test_env.vars(self).apply():
                self.run("ctest -N", cwd=self.build_folder)
                self.run("ctest --output-on-failure --verbose -j1", cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        if str(self.settings.os) == "OHOS":
            self._sign_shared_objects()


    def _sign_shared_objects(self):
        self._sign_elf_files(
            glob.glob(
                os.path.join(self.package_folder, "lib", "**", "*.so*"),
                recursive=True,
            )
        )

    def _sign_upstream_test_artifacts(self):
        candidates = glob.glob(
            os.path.join(self.build_folder, "**", "*.so*"), recursive=True
        )
        candidates.extend(
            glob.glob(
                os.path.join(self.build_folder, "**", "test_pam_wrapper"),
                recursive=True,
            )
        )
        self._sign_elf_files(candidates)

    def _sign_elf_files(self, candidates):
        paths = sorted(
            {
                path
                for path in candidates
                if os.path.isfile(path)
                and not os.path.islink(path)
                and self._is_elf(path)
            }
        )
        if not paths:
            return

        objcopy = self._find_ohos_tool("OHOS_LLVM_OBJCOPY", "llvm-objcopy")
        signer = self._find_ohos_tool("OHOS_BINARY_SIGN_TOOL", "binary-sign-tool")
        missing = [
            name
            for name, path in (("llvm-objcopy", objcopy), ("binary-sign-tool", signer))
            if not path
        ]
        if missing:
            raise ConanException("OHOS signing tools unavailable: %s" % ", ".join(missing))
        for path in paths:
            strip_result = self.run(
                f'{objcopy} --remove-section .codesign "{path}"',
                ignore_errors=True,
            )
            if strip_result != 0:
                raise ConanException(
                    "llvm-objcopy could not remove .codesign from %s" % path
                )
            sign_result = self.run(
                f'{signer} sign -inFile "{path}" -outFile "{path}" -selfSign 1',
                ignore_errors=True,
            )
            if sign_result != 0:
                raise ConanException("binary-sign-tool failed for %s" % path)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as stream:
                return stream.read(4) == b"\x7fELF"
        except OSError:
            return False

    @staticmethod
    def _find_ohos_tool(env_name, command):
        configured = os.environ.get(env_name)
        if configured:
            found = shutil.which(configured)
            if found:
                return found
            if os.path.isfile(configured):
                return configured
        tool_dir = os.environ.get("SIGN_TOOL_PATH")
        if tool_dir:
            candidate = os.path.join(tool_dir, command)
            if os.path.isfile(candidate):
                return candidate
        return shutil.which(command)

    def package_info(self):
        libdir = os.path.join(self.package_folder, "lib")
        wrapper_path = os.path.join(libdir, "libpam_wrapper.so")

        self.cpp_info.set_property("cmake_file_name", "pam_wrapper")
        self.cpp_info.set_property("cmake_target_name", "pam_wrapper::pam_wrapper")
        self.cpp_info.set_property("pkg_config_name", "pam_wrapper")
        self.cpp_info.libs = ["pamtest"]
        self.cpp_info.requires = ["linux-pam::pam"]

        self.runenv_info.define_path("PAM_WRAPPER_LIB", wrapper_path)
        self.buildenv_info.define_path("PAM_WRAPPER_LIB", wrapper_path)
        self.runenv_info.append_path("LD_LIBRARY_PATH", libdir)
