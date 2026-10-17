#!/usr/bin/env python3
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class UidWrapperConan(ConanFile):
    name = "uid-wrapper"
    version = "1.2.5"
    description = "A wrapper for privilege separation of uid/gid operations in testing environments"
    license = "GPL-3.0-or-later"
    homepage = "https://cwrap.org/uid_wrapper.html"
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
                "uid-wrapper requires POSIX uid/gid libc calls and LD_PRELOAD support"
            )
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "uid-wrapper builds a shared LD_PRELOAD interposition library only"
            )

    def build_requirements(self):
        if self.options.with_upstream_tests:
            self.test_requires("cmocka/2.0.2")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        if self.options.with_upstream_tests:
            deps = CMakeDeps(self)
            deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["UNIT_TESTING"] = bool(self.options.with_upstream_tests)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
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
                self.run(
                    "ctest --output-on-failure --verbose -j4",
                    cwd=self.build_folder,
                )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
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
            os.path.join(self.build_folder, "**", "*.so*"),
            recursive=True,
        )
        candidates.extend(
            glob.glob(
                os.path.join(self.build_folder, "**", "test_*"),
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
            raise ConanException(
                "OHOS signing tools unavailable: %s" % ", ".join(missing)
            )
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
        wrapper_path = os.path.join(libdir, "libuid_wrapper.so")

        self.cpp_info.set_property("cmake_file_name", "uid_wrapper")
        self.cpp_info.set_property("cmake_target_name", "uid_wrapper::uid_wrapper")
        self.cpp_info.set_property("pkg_config_name", "uid_wrapper")
        self.cpp_info.libs = ["uid_wrapper"]

        self.runenv_info.define_path("UID_WRAPPER_LIB", wrapper_path)
        self.buildenv_info.define_path("UID_WRAPPER_LIB", wrapper_path)
        self.runenv_info.append_path("LD_LIBRARY_PATH", libdir)
