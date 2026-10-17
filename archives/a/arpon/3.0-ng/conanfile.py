#!/usr/bin/env python3
"""Conan recipe — ArpON (ARP handler inspection) using CMake.

ArpON is a host-based ARP handler inspection tool providing SARPI,
DARPI and HARPI anti-ARP-spoofing techniques.

Build system: CMake (custom Find*.cmake modules).
Dependencies: libnet/1.2, libpcap/1.10.6, libdnet/1.12.
Product: arpon executable (command-line tool).
"""
import os
import hashlib
import tarfile

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ArponConan(ConanFile):
    name = "arpon"
    version = "3.0-ng"
    description = "ArpON - ARP handler inspection (SARPI/DARPI/HARPI anti-ARP-spoofing)"
    license = "BSD-2-Clause"
    homepage = "https://sourceforge.net/projects/arpon/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libnet/1.2")
        self.requires("libpcap/1.10.6")
        self.requires("libdnet/1.12")

    def validate(self):
        from conan.errors import ConanInvalidConfiguration
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "arpon is only supported on Linux/OHOS, not " + str(self.settings.os)
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        from conan.tools.files import get
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Let CMake auto-detect the system (HarmonyOS).
        # Setting CMAKE_SYSTEM_NAME=Linux causes compiler detection issues
        # in the conan build env on HarmonyOS.
        include_paths = set()
        lib_paths = set()
        for dep_name in ("libnet", "libpcap", "libdnet"):
            dep = self.dependencies.get(dep_name)
            if dep:
                for d in dep.cpp_info.includedirs:
                    include_paths.add(str(d))
                for d in dep.cpp_info.libdirs:
                    lib_paths.add(str(d))
        # Add OHOS SDK sysroot paths for system headers (pthread.h, etc.)
        import subprocess
        import shutil
        try:
            # On HarmonyOS, subprocess with short name fails (posix_spawn bug),
            # so resolve the full path from profile conf or shutil.which.
            cc = "clang"
            compilers = self.conf.get("tools.build:compiler_executables", default={})
            if isinstance(compilers, dict) and compilers.get("c"):
                cc = compilers["c"]
            elif isinstance(compilers, str):
                import json
                parsed = json.loads(compilers)
                if isinstance(parsed, dict) and parsed.get("c"):
                    cc = parsed["c"]
            if cc == "clang":
                resolved = shutil.which("clang")
                if resolved:
                    cc = resolved
            crt_path = subprocess.check_output(
                [cc, "-print-file-name=crt1.o"], stderr=subprocess.DEVNULL
            ).decode().strip()
            if crt_path:
                idx = crt_path.find("/usr/lib/")
                if idx > 0:
                    sysroot = crt_path[:idx]
                    inc = os.path.join(sysroot, "usr", "include")
                    inc_arch = os.path.join(sysroot, "usr", "include", "aarch64-linux-ohos")
                    lib_arch = os.path.join(sysroot, "usr", "lib", "aarch64-linux-ohos")
                    for p in (inc, inc_arch):
                        if os.path.isdir(p):
                            include_paths.add(p)
                    if os.path.isdir(lib_arch):
                        lib_paths.add(lib_arch)
        except Exception:
            pass
        if include_paths:
            tc.variables["CMAKE_INCLUDE_PATH"] = ";".join(sorted(include_paths))
        if lib_paths:
            tc.variables["CMAKE_LIBRARY_PATH"] = ";".join(sorted(lib_paths))
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HarmonyOS: getcwd() fails in conan cache directories.
        # Must os.chdir() to a valid dir before spawning subprocess.
        import subprocess
        bash = "/data/service/hnp/bin/bash"
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        conanbuild_sh = os.path.join(self.generators_folder, "conanbuild.sh")

        # Change to build folder first
        os.chdir(self.build_folder)

        configure_cmd = (
            f'. "{conanbuild_sh}" && '
            f'cmake -G "Unix Makefiles" '
            f'-DCMAKE_TOOLCHAIN_FILE="{toolchain}" '
            f'-DCMAKE_POLICY_DEFAULT_CMP0091=NEW '
            f'-DCMAKE_BUILD_TYPE=Release '
            f'-DCMAKE_INSTALL_PREFIX="{self.package_folder}" '
            f'"{self.source_folder}"'
        )
        ret = subprocess.call([bash, "-c", configure_cmd])
        if ret != 0:
            raise Exception(f"cmake configure failed (exit {ret})")
        build_cmd = (
            f'. "{conanbuild_sh}" && '
            f'cmake --build . -- -j1'
        )
        ret = subprocess.call([bash, "-c", build_cmd])
        if ret != 0:
            raise Exception(f"cmake build failed (exit {ret})")

    def package(self):
        import subprocess
        bash = "/data/service/hnp/bin/bash"
        conanbuild_sh = os.path.join(self.generators_folder, "conanbuild.sh")
        os.chdir(self.build_folder)
        install_cmd = (
            f'. "{conanbuild_sh}" && '
            f'cmake --install . --prefix "{self.package_folder}"'
        )
        ret = subprocess.call([bash, "-c", install_cmd])
        if ret != 0:
            raise Exception(f"cmake install failed (exit {ret})")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["sbin", "bin"]
