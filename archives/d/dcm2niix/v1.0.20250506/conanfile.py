#!/usr/bin/env python3
"""Conan recipe for dcm2niix — DICOM to NIfTI converter (CMake SuperBuild project).

dcm2niix converts DICOM medical images to NIfTI format. It is a command-line
tool built with CMake SuperBuild (ExternalProject_Add builds the console
subproject from the local console/ directory, no download).

Build: CMake SuperBuild → ExternalProject_Add(console) → dcm2niix binary
Deps:  None external (uses built-in Miniz as zlib implementation)
Patch: 0001-console-CMakeLists.txt.patch — fix macOS-only -dead_strip → --gc-sections on ELF

See: https://github.com/rordenlab/dcm2niix
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Dcm2NiixConan(ConanFile):
    name = "dcm2niix"
    version = "v1.0.20250506"
    description = "DICOM to NIfTI format converter for medical images"
    license = "BSD-3-Clause"
    homepage = "https://github.com/rordenlab/dcm2niix"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external Conan deps: dcm2niix uses built-in Miniz as zlib,
        # and has no TurboJPEG/Jasper/OpenJPEG/JPEGLS by default.
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # USE_STATIC_RUNTIME=OFF: Clang on HarmonyOS has issues statically
        # linking libstdc++; use dynamic runtime instead.
        tc.variables["USE_STATIC_RUNTIME"] = "OFF"
        # Keep all optional image codec dependencies OFF (use built-in Miniz).
        tc.variables["USE_TURBOJPEG"] = "OFF"
        tc.variables["USE_JASPER"] = "OFF"
        tc.variables["USE_OPENJPEG"] = "OFF"
        tc.variables["USE_JPEGLS"] = "OFF"
        tc.variables["BUILD_DCM2NIIXFSLIB"] = "OFF"
        tc.variables["BATCH_VERSION"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # R38/E082: HarmonyOS requires ELF signing before a binary can execute.
        # Without this the test_package cannot run the dcm2niix binary.
        # R32: guard with in ("Linux", "OHOS") — signing only needed on OHOS,
        # but package() runs in the host context so we sign for OHOS targets.
        bin_path = os.path.join(self.package_folder, "bin", "dcm2niix")
        if os.path.exists(bin_path) and self.settings.os in ("Linux", "OHOS"):
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            is_ohos = self.settings.os == "OHOS"
            if os.path.exists(sign_tool):
                tmp_signed = bin_path + ".signed"
                # Step 1: Remove old .codesign section (may not exist on fresh build)
                r_obj = subprocess.run(
                    [objcopy, "--remove-section", ".codesign", bin_path],
                    capture_output=True, timeout=10)
                if r_obj.returncode != 0 and is_ohos:
                    self.output.warning(f"objcopy returned {r_obj.returncode} for dcm2niix")
                # Step 2: Sign with binary-sign-tool
                r = subprocess.run(
                    [sign_tool, "sign", "-inFile", bin_path, "-outFile", tmp_signed,
                     "-selfSign", "1"],
                    capture_output=True, timeout=30)
                if r.returncode == 0 and os.path.exists(tmp_signed):
                    os.replace(tmp_signed, bin_path)
                    os.chmod(bin_path, 0o755)
                else:
                    msg = f"ELF signing failed for dcm2niix (rc={r.returncode})"
                    if is_ohos:
                        raise RuntimeError(msg)
                    self.output.warning(msg)
            elif is_ohos:
                self.output.warning(
                    "ELF signing tool not found at /data/service/hnp/bin/binary-sign-tool; "
                    "the resulting binary will NOT be executable on HarmonyOS."
                )

    def package_info(self):
        # Tool-only package: ships an executable, no libraries to link against.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
