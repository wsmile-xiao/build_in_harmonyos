#!/usr/bin/env python3
"""Conan recipe for Cling 1.3 (CMake with its matching LLVM 20 tree)."""

import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class ClingConan(ConanFile):
    name = "cling"
    version = "1.3"
    description = "Interactive C++ interpreter built on LLVM and Clang"
    license = "(LGPL-2.1-only OR NCSA) AND Apache-2.0 WITH LLVM-exception"
    homepage = "https://root.cern/cling/"
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self, src_folder=".")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(
            self,
            **self.conan_data["llvm"],
            strip_root=True,
            destination=os.path.join(self.source_folder, "llvm-project"),
        )

    def generate(self):
        # Buildbot's OHOS filesystem rejects GNU make's FIFO jobserver.
        generator = "Ninja" if self.settings.os == "OHOS" else None
        tc = CMakeToolchain(self, generator=generator)
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"
        tc.variables["CMAKE_SKIP_RPATH"] = "ON"

        # Match the source pairing and core build used by the upstream formula.
        tc.variables["CLING_CXX_PATH"] = "clang++"
        tc.variables["CLANG_TOOL_C_ARCMT_TEST_BUILD"] = "OFF"
        tc.variables["CLANG_TOOL_C_INDEX_TEST_BUILD"] = "OFF"
        tc.variables["CLANG_TOOL_LIBCLANG_BUILD"] = "OFF"
        tc.variables["LLVM_BUILD_TOOLS"] = "OFF"
        tc.variables["LLVM_ENABLE_PROJECTS"] = "clang"
        tc.variables["LLVM_EXTERNAL_PROJECTS"] = "cling"
        tc.variables["LLVM_EXTERNAL_CLING_SOURCE_DIR"] = self.source_folder
        tc.variables["LLVM_INCLUDE_BENCHMARKS"] = "OFF"
        tc.variables["LLVM_INCLUDE_DOCS"] = "OFF"
        tc.variables["LLVM_INCLUDE_EXAMPLES"] = "OFF"
        tc.variables["LLVM_INCLUDE_TESTS"] = "OFF"
        tc.variables["LLVM_PARALLEL_LINK_JOBS"] = "1"
        tc.variables["LLVM_TARGETS_TO_BUILD"] = "host;NVPTX"
        tc.variables["CLING_INCLUDE_DOCS"] = "OFF"
        tc.variables["CLING_INCLUDE_TESTS"] = "OFF"

        # Conan maps OHOS to HarmonyOS, which has no built-in CMake platform
        # module. Restore the UNIX semantics used by the official OHOS SDK.
        if self.settings.os == "OHOS":
            tc.variables["UNIX"] = True

        # Optional host libraries are disabled until matching Conan packages and
        # LLVM CMake targets are available. Core Cling/JIT does not require them.
        tc.variables["LLVM_ENABLE_LIBEDIT"] = "OFF"
        tc.variables["LLVM_ENABLE_LIBXML2"] = "OFF"
        tc.variables["LLVM_ENABLE_ZLIB"] = "OFF"
        tc.variables["LLVM_ENABLE_ZSTD"] = "OFF"
        tc.variables["LLVM_ENABLE_CURL"] = "OFF"
        tc.variables["LLVM_ENABLE_HTTPLIB"] = "OFF"
        tc.variables["LLVM_ENABLE_FFI"] = "OFF"
        tc.variables["LLVM_ENABLE_LIBPFM"] = "OFF"
        tc.variables["LLVM_ENABLE_Z3_SOLVER"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(
            build_script_folder=os.path.join(self.source_folder, "llvm-project", "llvm")
        )
        self.conf.define("tools.build:jobs", min(build_jobs(self), 20))
        cmake.build(
            target=[
                "cling",
                "libcling",
                "cling-headers",
                "clang-headers",
                "llvm-headers",
                "clang-resource-headers",
            ]
        )

    def package(self):
        cmake = CMake(self)
        for component in (
            "cling",
            "libcling",
            "cling-headers",
            "clang-headers",
            "llvm-headers",
            "clang-resource-headers",
        ):
            cmake.install(component=component)
        self._sign_package_elfs()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "cling")
        self.cpp_info.set_property("cmake_target_name", "cling::cling")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["cling"]

    def _sign_package_elfs(self):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        tools_available = os.path.isfile(objcopy) and os.path.isfile(signer)
        if not tools_available:
            if self.settings.os == "OHOS":
                raise ConanInvalidConfiguration(
                    "OHOS ELF signing tools are required before test_package execution"
                )
            self.output.warning("OHOS ELF signing tools not found; skipping on Linux")
            return

        signed = 0
        for path in self._package_elfs():
            cleaned = path + ".codesign.tmp"
            output = path + ".signed.tmp"
            for temporary in (cleaned, output):
                if os.path.exists(temporary):
                    os.remove(temporary)

            try:
                objcopy_result = subprocess.run(
                    [objcopy, "--remove-section", ".codesign", path, cleaned],
                    check=False,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=120,
                )
            except subprocess.TimeoutExpired as error:
                if os.path.exists(cleaned):
                    os.remove(cleaned)
                raise ConanInvalidConfiguration(
                    f"ELF codesign cleanup timed out for "
                    f"{os.path.relpath(path, self.package_folder)}"
                ) from error
            if objcopy_result.returncode != 0 or not os.path.isfile(cleaned):
                if os.path.exists(cleaned):
                    os.remove(cleaned)
                detail = (objcopy_result.stderr or objcopy_result.stdout).strip()
                raise ConanInvalidConfiguration(
                    f"ELF codesign cleanup failed for "
                    f"{os.path.relpath(path, self.package_folder)}: "
                    f"rc={objcopy_result.returncode}, detail={detail[-300:]!r}"
                )
            os.replace(cleaned, path)

            try:
                result = subprocess.run(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        path,
                        "-outFile",
                        output,
                        "-selfSign",
                        "1",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=120,
                )
            except subprocess.TimeoutExpired as error:
                if os.path.exists(output):
                    os.remove(output)
                raise ConanInvalidConfiguration(
                    f"ELF signing timed out for "
                    f"{os.path.relpath(path, self.package_folder)}"
                ) from error
            if result.returncode != 0 or not os.path.isfile(output):
                if os.path.exists(output):
                    os.remove(output)
                detail = (result.stderr or result.stdout).strip()
                raise ConanInvalidConfiguration(
                    f"ELF signing failed for {os.path.relpath(path, self.package_folder)}: "
                    f"rc={result.returncode}, detail={detail[-300:]!r}"
                )
            os.replace(output, path)
            os.chmod(path, os.stat(path).st_mode | 0o111)
            signed += 1
        self.output.info(f"Signed {signed} packaged ELF files")

    def _package_elfs(self):
        for top in ("bin", "lib"):
            root = os.path.join(self.package_folder, top)
            if not os.path.isdir(root):
                continue
            for directory, _, filenames in os.walk(root):
                for filename in sorted(filenames):
                    if top == "lib" and ".so" not in filename:
                        continue
                    path = os.path.join(directory, filename)
                    if os.path.islink(path):
                        continue
                    try:
                        with open(path, "rb") as stream:
                            if stream.read(4) == b"\x7fELF":
                                yield path
                    except OSError as error:
                        self.output.warning(f"Cannot inspect {path}: {error}")
