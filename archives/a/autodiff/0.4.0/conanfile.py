#!/usr/bin/env python3
"""Conan recipe — autodiff 0.4.0 (CMake header-only / INTERFACE library).

Reference: archives/r/range-v3/0.12.0/ (header-only CMake pattern).

Downstream expects:
  find_package(autodiff REQUIRED)
  target_link_libraries(... PRIVATE autodiff::autodiff)
"""
import os
import shutil
import subprocess
import tarfile
import tempfile
from multiprocessing import cpu_count

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.files import apply_conandata_patches, export_conandata_patches, copy, download
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AutodiffConan(ConanFile):
    name = "autodiff"
    version = "0.4.0"
    description = "automatic differentiation made easier for C++"
    license = "MIT"
    homepage = "https://github.com/autodiff/autodiff"
    url = "https://github.com/autodiff/autodiff"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    # For header-only, shared/static is not relevant
    # but we keep the default Conan behavior

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Use local tarball if available (OHOS device CI), otherwise download.
        # codeload.github.com URL pattern confuses Conan's get() format detection,
        # so we download and extract manually.
        tarball_path = os.environ.get("AUTODIFF_TARBALL_PATH", "")
        url = self.conan_data["sources"]["url"]
        sha256 = self.conan_data["sources"]["sha256"]

        if tarball_path and os.path.exists(tarball_path):
            local_tarball = tarball_path
        else:
            local_tarball = os.path.join(
                tempfile.gettempdir(), "autodiff-src.tar.gz"
            )
            download(self, url, local_tarball, sha256=sha256)

        tmp = tempfile.mkdtemp()
        with tarfile.open(local_tarball, "r:gz") as tar:
            tar.extractall(tmp)

        # strip_root: move contents of single top-level dir to source_folder
        members = sorted(os.listdir(tmp))
        if len(members) == 1 and os.path.isdir(os.path.join(tmp, members[0])):
            top_dir = os.path.join(tmp, members[0])
            for item in os.listdir(top_dir):
                shutil.move(
                    os.path.join(top_dir, item),
                    os.path.join(self.source_folder, item),
                )
        else:
            for item in members:
                shutil.move(
                    os.path.join(tmp, item),
                    os.path.join(self.source_folder, item),
                )
        shutil.rmtree(tmp, ignore_errors=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS: CMake may not recognize OHOS as a known system name
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            arch_map = {"armv8": "aarch64", "x86_64": "x86_64"}
            cmake_arch = arch_map.get(str(self.settings.arch), str(self.settings.arch))
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = cmake_arch
        # Upstream requires CMake >= 3.0, but the device CMake has dropped
        # compatibility with < 3.5. Tell CMake to accept the older minimum.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Main build: header-only, just configure for install
        cmake = CMake(self)
        cmake.configure()

        # Build upstream tests in an isolated temporary directory
        test_build_dir = tempfile.mkdtemp(prefix="autodiff-tests-")
        try:
            toolchain = os.path.join(
                self.generators_folder, "conan_toolchain.cmake"
            ).replace("\\", "/")
            cmake_cmd = [
                "cmake", self.source_folder,
                "-DCMAKE_TOOLCHAIN_FILE=" + toolchain,
                "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            ]
            # OHOS-specific flags
            if self.settings.os in ("Linux", "OHOS"):
                cmake_cmd.append("-DCMAKE_SYSTEM_NAME=Linux")
            if self.settings.os == "OHOS":
                arch_map = {"armv8": "aarch64", "x86_64": "x86_64"}
                cmake_arch = arch_map.get(str(self.settings.arch), str(self.settings.arch))
                cmake_cmd += [
                    f"-DCMAKE_SYSTEM_PROCESSOR={cmake_arch}",
                ]
                # When cross-compiling with qemu available, tell cmake how to
                # run target binaries during ctest.
                if cross_building(self):
                    qemu = shutil.which("qemu-aarch64")
                    if qemu:
                        cmake_cmd.append(
                            "-DCMAKE_CROSSCOMPILING_EMULATOR=" + qemu
                        )

            subprocess.check_call(cmake_cmd, cwd=test_build_dir)
            nproc = os.environ.get("CONAN_CPU_COUNT", str(cpu_count()))
            subprocess.check_call(
                ["cmake", "--build", ".", "--target", "tests", "-j", nproc],
                cwd=test_build_dir,
            )

            # Run upstream test binary (Catch2 vendored, not CTest)
            tests_binary = os.path.join(test_build_dir, "test", "tests")
            if os.path.isfile(tests_binary) and os.access(tests_binary, os.X_OK):
                if cross_building(self):
                    qemu = shutil.which("qemu-aarch64")
                    if not qemu:
                        self.output.warning(
                            "qemu-aarch64 not found; skipping upstream test execution"
                        )
                    else:
                        subprocess.check_call(
                            [qemu, tests_binary], cwd=test_build_dir
                        )
                else:
                    subprocess.check_call([tests_binary], cwd=test_build_dir)
            else:
                self.output.warning(
                    "Upstream test binary not found; skipping upstream tests"
                )
        finally:
            shutil.rmtree(test_build_dir, ignore_errors=True)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Header-only: no link libraries
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]

        self.cpp_info.set_property("cmake_file_name", "autodiff")
        self.cpp_info.set_property("cmake_target_name", "autodiff::autodiff")
        self.cpp_info.set_property("pkg_config_name", "autodiff")
