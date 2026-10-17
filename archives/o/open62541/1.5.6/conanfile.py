#!/usr/bin/env python3
"""Conan recipe for open62541 - OPC UA (IEC 62541) open source implementation in C99.

open62541 is licensed under the Mozilla Public License v2.0 (MPLv2).
Homepage: https://open62541.org
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class Open62541Conan(ConanFile):
    name = "open62541"
    version = "1.5.6"
    description = "Open source implementation of OPC UA (OPC Unified Architecture / IEC 62541) written in the C language"
    license = "MPL-2.0"
    homepage = "https://open62541.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {"shared": False}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "open62541 is currently adapted for Linux and OHOS"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _resolve_real_compiler(self, wrapper_path):
        """Read the OHOS clang wrapper script to find the real binary path.

        The wrapper at /data/service/hnp/bin/clang is a #!/bin/sh script:
            exec -a /path/to/clang /path/to/clang-15 "$@"
        /bin/sh on OHOS doesn't support `exec -a`, causing silent failures.
        Return the real binary path, or None if not found.
        """
        try:
            real_path = os.path.realpath(wrapper_path)
            if not os.path.isfile(real_path):
                return None
            with open(real_path, "r") as f:
                content = f.read()
            # Match: exec -a ... /path/to/clang-15 "$@"
            m = re.search(r'exec\s+-a\s+\S+\s+(\S+clang-?\d*)\s+"?\$@"?', content)
            if m:
                binary = m.group(1)
                if os.path.exists(binary):
                    return binary
            # Fallback: look for clang-NN in the same directory
            d = os.path.dirname(real_path)
            for name in sorted(os.listdir(d) if os.path.isdir(d) else []):
                if re.match(r'clang(-\d+)?$', name) and name != os.path.basename(real_path):
                    candidate = os.path.join(d, name)
                    if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                        return candidate
        except Exception:
            pass
        return None

    def generate(self):
        tc = CMakeToolchain(self)
        # Fix CMake platform detection: OHOS maps to CMAKE_SYSTEM_NAME=HarmonyOS
        # but CMake only has Platform/OHOS.cmake (not HarmonyOS.cmake).
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # Disable features requiring unavailable dependencies
        tc.variables["UA_ENABLE_DISCOVERY_MULTICAST_MDNSD"] = False
        tc.variables["UA_FORCE_WERROR"] = False
        tc.variables["UA_ENABLE_DEBUG_SANITIZER"] = False
        tc.variables["UA_BUILD_UNIT_TESTS"] = False
        tc.variables["UA_BUILD_EXAMPLES"] = False
        tc.variables["UA_ENABLE_AMALGAMATION"] = False
        if self.settings.os == "OHOS":
            # The OHOS sysroot does not provide the Linux raw-socket headers
            # required by open62541's POSIX Ethernet event source.
            tc.variables["UA_ENABLE_POSIX_ETHERNET"] = False
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # Fix CMake object extension (.obj vs .o on OHOS host)
        tc.cache_variables["CMAKE_C_OUTPUT_EXTENSION"] = "o"
        # Skip compiler try-compile (OHOS host not recognized by CMake)
        tc.cache_variables["CMAKE_C_COMPILER_FORCED"] = "ON"
        tc.generate()

        # Patch toolchain to use real clang binary instead of wrapper script.
        # The /data/service/hnp/bin/clang wrapper uses `exec -a` which
        # /bin/sh (used by make for recipes) doesn't support on OHOS.
        if self.settings.os == "OHOS":
            gen_dir = os.path.join(self.build_folder, "generators")
            toolchain_file = os.path.join(gen_dir, "conan_toolchain.cmake")
            if not os.path.exists(toolchain_file):
                return
            replacements = {}
            for wrap_name, wrap_path in [
                ("C", "/data/service/hnp/bin/clang"),
                ("CXX", "/data/service/hnp/bin/clang++"),
            ]:
                real = self._resolve_real_compiler(wrap_path)
                if real:
                    replacements[wrap_path] = real
            if replacements and os.path.exists(toolchain_file):
                with open(toolchain_file, "r") as f:
                    content = f.read()
                for wrap_name, wrap_path in [
                    ("C", "/data/service/hnp/bin/clang"),
                    ("CXX", "/data/service/hnp/bin/clang++"),
                ]:
                    real = replacements.get(wrap_path)
                    if real:
                        var = f"CMAKE_{wrap_name}_COMPILER"
                        content = content.replace(
                            f'set({var} "{wrap_path}")',
                            f'set({var} "{real}")'
                        )
                with open(toolchain_file, "w") as f:
                    f.write(content)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["open62541"]
        if not self.options.shared:
            self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.set_property("cmake_file_name", "open62541")
        self.cpp_info.set_property("cmake_target_name", "open62541::open62541")
