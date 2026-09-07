#!/usr/bin/env python3
import glob
import os
import shutil
import uuid

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class SocketWrapperConan(ConanFile):
    name = "socket-wrapper"
    version = "1.4.1"
    description = (
        "A library passing all BSD sockets API calls through a Unix socket"
    )
    license = "BSD-3-Clause"
    homepage = "https://gitlab.com/cwrap/socket_wrapper"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
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
                "socket-wrapper requires POSIX socket APIs and LD_PRELOAD"
            )
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "socket-wrapper builds shared interposition libraries only"
            )

    def build_requirements(self):
        if self.options.with_upstream_tests:
            self.test_requires(self.conan_data["requirements"]["cmocka"])

    def source(self):
        get(
            self,
            **self.conan_data["sources"][self.version],
            strip_root=True,
        )

    def generate(self):
        if self.options.with_upstream_tests:
            CMakeDeps(self).generate()

        toolchain = CMakeToolchain(self)
        toolchain.variables["UNIT_TESTING"] = bool(
            self.options.with_upstream_tests
        )
        toolchain.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        if str(self.settings.os) == "OHOS":
            processors = {
                "armv8": "aarch64",
                "x86_64": "x86_64",
            }
            ohos_arches = {
                "armv8": "arm64-v8a",
                "x86_64": "x86_64",
            }
            arch = str(self.settings.arch)
            toolchain.cache_variables["CMAKE_SYSTEM_NAME"] = "OHOS"
            toolchain.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                processors.get(arch, arch)
            )
            toolchain.cache_variables["OHOS_ARCH"] = ohos_arches.get(
                arch, arch
            )
            toolchain.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = (
                "STATIC_LIBRARY"
            )
            compatible_sdk = self.conf.get(
                "user.socket-wrapper:ohos_compatible_sdk_version",
                default=None,
            )
            if compatible_sdk:
                toolchain.cache_variables[
                    "OHOS_COMPATIBLE_SDK_VERSION"
                ] = str(compatible_sdk)

            musl_available = {
                "HAVE_STRNCPY",
                "HAVE_VSNPRINTF",
                "HAVE_SNPRINTF",
                "HAVE_SIGNALFD",
                "HAVE_EVENTFD",
                "HAVE_TIMERFD_CREATE",
                "HAVE_ACCEPT4",
                "HAVE_RECVMMSG",
                "HAVE_RECVMMSG_UNSIGNED_FLAGS",
                "HAVE_SENDMMSG",
                "HAVE_SENDMMSG_UNSIGNED_FLAGS",
                "HAVE_SYSCALL",
                "HAVE_DLOPEN",
                "HAVE_GETADDRINFO",
            }
            musl_unavailable = {
                "HAVE_BINDRESVPORT",
                "HAVE_GETPROGNAME",
                "HAVE_GETEXECNAME",
                "HAVE_PLEDGE",
                "HAVE_FCNTL64",
                "HAVE_OPEN64",
                "HAVE_OPENAT64",
                "HAVE_FOPEN64",
                "HAVE_LIBNSL",
                "HAVE_LIBSOCKET",
                "HAVE__SOCKET",
                "HAVE__CLOSE",
                "HAVE___CLOSE_NOCANCEL",
                "HAVE_PROGRAM_INVOCATION_SHORT_NAME",
            }
            for variable in musl_available:
                toolchain.cache_variables[variable] = True
            for variable in musl_unavailable:
                toolchain.cache_variables[variable] = False
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        if self.options.with_upstream_tests and can_run(self):
            if str(self.settings.os) == "OHOS":
                self._sign_upstream_test_artifacts()
            runtime_dir = self._upstream_test_runtime_dir()
            os.makedirs(runtime_dir, exist_ok=True)
            test_env = Environment()
            test_env.define("TMPDIR", runtime_dir)
            test_env.append_path(
                "LD_LIBRARY_PATH",
                os.path.join(self.build_folder, "tests"),
            )
            with test_env.vars(self).apply():
                self.run("ctest -N", cwd=self.build_folder)
                self.run(
                    "ctest --output-on-failure --verbose -j1",
                    cwd=self.build_folder,
                )

    def package(self):
        CMake(self).install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        if str(self.settings.os) == "OHOS":
            self._sign_shared_objects()

    def package_info(self):
        libdir = os.path.join(self.package_folder, "lib")
        wrapper = os.path.join(libdir, "libsocket_wrapper.so")

        self.cpp_info.set_property("cmake_file_name", "socket_wrapper")
        self.cpp_info.set_property(
            "cmake_target_name", "socket_wrapper::socket_wrapper"
        )
        self.cpp_info.set_property("pkg_config_name", "socket_wrapper")
        self.cpp_info.libs = ["socket_wrapper_noop"]

        self.runenv_info.define_path("SOCKET_WRAPPER_LIB", wrapper)
        self.buildenv_info.define_path("SOCKET_WRAPPER_LIB", wrapper)
        self.runenv_info.append_path("LD_LIBRARY_PATH", libdir)

    def _upstream_test_runtime_dir(self):
        candidates = [
            "/data/storage/el2/base/temp",
            "/data/local/tmp",
            "/tmp",
        ]
        inherited = os.environ.get("TMPDIR")
        if inherited:
            candidates.append(inherited)
        candidates.append(os.path.join(self.build_folder, "t"))

        for candidate in candidates:
            if candidate and len(candidate) + len("/w_XXXXXX") <= 90:
                unique = os.path.join(
                    candidate, "swrap-" + uuid.uuid4().hex[:8]
                )
                try:
                    os.makedirs(unique, exist_ok=False)
                    return unique
                except OSError:
                    continue

        raise ConanException(
            "no short writable directory is available for upstream tests"
        )

    def _sign_shared_objects(self):
        self._sign_elf_files(
            glob.glob(
                os.path.join(self.package_folder, "lib", "**", "*.so*"),
                recursive=True,
            )
        )

    def _sign_upstream_test_artifacts(self):
        self._sign_elf_files(
            glob.glob(
                os.path.join(self.build_folder, "**", "*"),
                recursive=True,
            )
        )

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

        objcopy = self._find_ohos_tool(
            "OHOS_LLVM_OBJCOPY", "llvm-objcopy"
        )
        signer = self._find_ohos_tool(
            "OHOS_BINARY_SIGN_TOOL", "binary-sign-tool"
        )
        missing = [
            name
            for name, path in (
                ("llvm-objcopy", objcopy),
                ("binary-sign-tool", signer),
            )
            if not path
        ]
        if missing:
            raise ConanException(
                "OHOS signing tools unavailable: %s" % ", ".join(missing)
            )

        for path in paths:
            strip_result = self.run(
                '"{}" --remove-section .codesign "{}"'.format(
                    objcopy, path
                ),
                ignore_errors=True,
            )
            if strip_result != 0:
                raise ConanException(
                    "llvm-objcopy could not remove .codesign from %s" % path
                )
            sign_result = self.run(
                '"{}" sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
                    signer, path, path
                ),
                ignore_errors=True,
            )
            if sign_result != 0:
                raise ConanException(
                    "binary-sign-tool failed for %s" % path
                )

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
