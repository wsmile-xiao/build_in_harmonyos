#!/usr/bin/env python3
"""Conan recipe — zeromq 4.3.5 (cmake)

ZeroMQ (libzmq) is a high-performance asynchronous messaging library
for building distributed or concurrent applications.
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ZeromqConan(ConanFile):
    name = "zeromq"
    version = "4.3.5"
    description = "ZeroMQ — high-performance asynchronous messaging library"
    license = "MPL-2.0"
    homepage = "https://zeromq.org"
    url = "https://github.com/zeromq/libzmq"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_drafts": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "enable_drafts": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_STATIC"] = "OFF" if self.options.shared else "ON"
        tc.variables["ENABLE_DRAFTS"] = "ON" if self.options.enable_drafts else "OFF"
        tc.variables["ENABLE_CURVE"] = "OFF"
        tc.variables["WITH_LIBSODIUM"] = "OFF"
        tc.variables["WITH_OPENPGM"] = "OFF"
        tc.variables["WITH_NORM"] = "OFF"
        tc.variables["WITH_VMCI"] = "OFF"
        tc.variables["ZMQ_BUILD_TESTS"] = "OFF"
        tc.variables["ENABLE_WS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if self.settings.os in ("Linux", "OHOS"):
            self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ZeroMQ")
        self.cpp_info.set_property("cmake_target_name", "libzmq")
        self.cpp_info.set_property("cmake_target_aliases", ["libzmq-static"])
        if self.options.shared:
            self.cpp_info.libs = ["zmq"]
        else:
            self.cpp_info.libs = ["zmq"]  # static: libzmq.a → lib name is "zmq"
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "rt"]
