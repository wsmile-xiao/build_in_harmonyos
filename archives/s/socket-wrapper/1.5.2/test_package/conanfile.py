#!/usr/bin/env python3
import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SocketWrapperTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        dep = self.dependencies["socket-wrapper"]
        libdir = dep.cpp_info.libdirs[0] if dep.cpp_info.libdirs else "lib"
        if not os.path.isabs(libdir):
            libdir = os.path.join(dep.package_folder, libdir)

        tc = CMakeToolchain(self)
        tc.variables["SOCKET_WRAPPER_TEST_LIBRARY"] = os.path.join(
            libdir, "libsocket_wrapper.so"
        ).replace("\\", "/")
        tc.generate()

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

        exe = os.path.join(self.cpp.build.bindirs[0], "test_socket_wrapper")
        runtime_dir = self._short_runtime_dir()
        os.makedirs(runtime_dir, exist_ok=True)

        env = {
            "LD_PRELOAD": os.path.join(libdir, "libsocket_wrapper.so"),
            "LD_LIBRARY_PATH": libdir,
            "SOCKET_WRAPPER_DIR": runtime_dir,
            "SOCKET_WRAPPER_IFACE": "2",
        }
        prefix = " ".join("{}={}".format(k, shlex.quote(v)) for k, v in env.items())
        self.run("{} {}".format(prefix, shlex.quote(exe)), env="conanrun")

    @staticmethod
    def _short_runtime_dir():
        """socket_wrapper stores AF_UNIX socket files inside
        SOCKET_WRAPPER_DIR and the kernel limits sun_path to ~108 bytes.
        Deep package/build folders easily exceed that, so prefer a short
        native temp filesystem when it exists."""
        candidates = ["/data/storage/el2/base/temp", "/tmp"]
        for candidate in candidates:
            if os.path.isdir(candidate) and os.access(candidate, os.W_OK):
                return os.path.join(
                    candidate, "swrap-tp-%s" % os.getpid()
                )
        return None
