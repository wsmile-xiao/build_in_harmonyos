#!/usr/bin/env python3
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class SocketWrapperTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
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
            compatible_sdk = self.conf.get(
                "user.socket-wrapper:ohos_compatible_sdk_version",
                default=None,
            )
            if compatible_sdk:
                toolchain.cache_variables[
                    "OHOS_COMPATIBLE_SDK_VERSION"
                ] = str(compatible_sdk)
        toolchain.generate()

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["socket-wrapper"]
        libdir = dep.cpp_info.libdirs[0] if dep.cpp_info.libdirs else "lib"
        if not os.path.isabs(libdir):
            libdir = os.path.join(dep.package_folder, libdir)

        wrapper = os.path.join(libdir, "libsocket_wrapper.so")
        if not os.path.isfile(wrapper):
            raise ConanException(
                "packaged LD_PRELOAD library is missing: %s" % wrapper
            )

        exe = os.path.join(self.cpp.build.bindirs[0], "test_socket_wrapper")
        runtime_dir = self._short_runtime_dir()
        os.makedirs(runtime_dir, exist_ok=False)

        env = {
            "LD_PRELOAD": wrapper,
            "LD_LIBRARY_PATH": libdir,
            "SOCKET_WRAPPER_DIR": runtime_dir,
            "SOCKET_WRAPPER_IFACE": "2",
        }
        prefix = " ".join(
            "{}={}".format(key, shlex.quote(value))
            for key, value in env.items()
        )
        try:
            self.run(
                "{} {}".format(prefix, shlex.quote(exe)),
                env="conanrun",
            )
        finally:
            shutil.rmtree(runtime_dir, ignore_errors=True)

    @staticmethod
    def _short_runtime_dir():
        candidates = [
            "/data/storage/el2/base/temp",
            "/data/local/tmp",
            "/tmp",
        ]
        inherited = os.environ.get("TMPDIR")
        if inherited:
            candidates.append(inherited)

        suffix = "swrap-tp-%s" % os.getpid()
        for candidate in candidates:
            if (
                os.path.isdir(candidate)
                and os.access(candidate, os.W_OK)
                and len(os.path.join(candidate, suffix)) <= 90
            ):
                return os.path.join(candidate, suffix)

        raise ConanException(
            "no short writable directory is available for SOCKET_WRAPPER_DIR"
        )
