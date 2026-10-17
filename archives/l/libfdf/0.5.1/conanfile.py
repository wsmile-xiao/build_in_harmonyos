#!/usr/bin/env python3
"""Conan recipe for libfdf 0.5.1 on HarmonyOS PC.

Upstream provides a CMake build and exactly three CTest entries.  The recipe
uses the repository's flang-ohos tool package for Fortran and the OHOS SDK
clang resource/sysroot directories so that flang can also act as the link
driver.  The upstream CTest suite is executed from build().
"""

import glob
import os
import subprocess

_OBJCOPY = "/data/service/hnp/bin/llvm-objcopy"
_SIGNTOOL = "/data/service/hnp/bin/binary-sign-tool"

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LibfdfConan(ConanFile):
    name = "libfdf"
    version = "0.5.1"
    description = "Library implementing the Flexible Data Format (FDF)"
    license = "BSD-3-Clause"
    homepage = "https://gitlab.com/siesta-project/libraries/libfdf"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "libfdf is built natively on HarmonyOS PC "
                "(os=OHOS, arch=armv8)"
            )

    def build_requirements(self):
        # .mod files are compiler-private; keep the exact toolchain in the
        # package identity so consumers cannot mix incompatible module files.
        self.tool_requires("flang-ohos/20.1.0", package_id_mode="full_mode")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _sdk_native(self):
        """Locate the complete OHOS SDK native root used by the recipe/tests."""
        configured = self.conf.get(
            "user.libfdf:sdk_native", default=None, check_type=str
        )
        candidates = [configured] if configured else glob.glob(
            "/data/service/hnp/ohos-sdk.org/*/ohos/native"
        )
        valid = []
        for candidate in candidates:
            candidate = os.path.realpath(candidate)
            required = (
                os.path.join(candidate, "sysroot"),
                os.path.join(candidate, "llvm", "lib"),
                os.path.join(candidate, "llvm", "lib", "aarch64-linux-ohos"),
            )
            clang = os.path.join(candidate, "llvm", "bin", "clang")
            if (
                all(os.path.isdir(path) for path in required)
                and os.path.isfile(clang)
                and os.access(clang, os.X_OK)
            ):
                valid.append(candidate)
        valid = sorted(set(valid))
        if len(valid) != 1:
            raise ConanInvalidConfiguration(
                "exactly one complete OHOS SDK native root is required; set "
                "user.libfdf:sdk_native to select it explicitly"
            )
        return valid[0]

    def _fortran_toolchain(self):
        """Return flang, compile flags, link flags and runtime library dirs."""
        flang_package = self.dependencies.build["flang-ohos"].package_folder
        flang = os.path.join(flang_package, "bin", "flang")
        flang_lib = os.path.join(flang_package, "lib")
        if not os.path.isfile(flang) or not os.path.isdir(flang_lib):
            raise ConanInvalidConfiguration("flang-ohos tool package is incomplete")

        sdk_native = self._sdk_native()
        sdk_clang = os.path.join(sdk_native, "llvm", "bin", "clang")
        runtime_dirs = (os.path.join(sdk_native, "llvm", "lib"), flang_lib)

        probe_env = os.environ.copy()
        probe_env["LD_LIBRARY_PATH"] = os.pathsep.join(runtime_dirs)
        try:
            resource_dir = subprocess.run(
                [sdk_clang, "-print-resource-dir"],
                check=True,
                env=probe_env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError) as error:
            raise ConanInvalidConfiguration(
                "unable to query the OHOS SDK clang resource directory"
            ) from error

        resource_dir = os.path.realpath(resource_dir)
        if (
            not os.path.isdir(resource_dir)
            or os.path.commonpath((sdk_native, resource_dir)) != sdk_native
        ):
            raise ConanInvalidConfiguration(
                "SDK clang returned a resource directory outside the SDK root"
            )

        compile_flags = " ".join(
            [
                "--target=aarch64-unknown-linux-ohos",
                "--sysroot={}".format(os.path.join(sdk_native, "sysroot")),
                "-resource-dir={}".format(resource_dir),
            ]
        )
        link_flags = " ".join(
            [
                "-L{}".format(
                    os.path.join(sdk_native, "llvm", "lib", "aarch64-linux-ohos")
                ),
                "-L{}".format(flang_lib),
            ]
        )
        return (
            flang.replace("\\", "/"),
            compile_flags.replace("\\", "/"),
            link_flags.replace("\\", "/"),
            runtime_dirs,
        )

    def generate(self):
        flang, fortran_flags, link_flags, _runtime_dirs = self._fortran_toolchain()
        toolchain = CMakeToolchain(self)

        if self.settings.os == "OHOS":
            toolchain.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            toolchain.blocks["generic_system"].values[
                "cmake_system_processor"
            ] = "aarch64"

        toolchain.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        toolchain.variables["BUILD_SHARED_LIBS"] = "OFF"
        toolchain.variables["libfdf_SHARED_LIBS"] = "OFF"
        toolchain.variables["CMAKE_Fortran_COMPILER"] = flang
        toolchain.variables["CMAKE_Fortran_FLAGS"] = fortran_flags
        toolchain.variables["CMAKE_EXE_LINKER_FLAGS"] = link_flags
        toolchain.variables["CMAKE_SHARED_LINKER_FLAGS"] = link_flags
        # flang-ohos is a frontend/runtime package without CRT files.  Compiler
        # identification can use static-library try-compiles; actual test links
        # use flang with the SDK flags above.
        toolchain.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        toolchain.generate()

    def _apply_runtime_env(self):
        _flang, _flags, _link_flags, runtime_dirs = self._fortran_toolchain()
        previous = os.environ.get("LD_LIBRARY_PATH")
        paths = list(runtime_dirs)
        if previous:
            paths.append(previous)
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(dict.fromkeys(paths))
        return previous

    def _sign_elf(self, path):
        if not os.path.isfile(path) or os.path.islink(path) or not os.path.isfile(_SIGNTOOL):
            return
        try:
            with open(path, "rb") as handle:
                header = handle.read(18)
        except OSError:
            return
        if header[:4] != b"\x7fELF" or len(header) < 18:
            return
        if int.from_bytes(header[16:18], "little") not in (2, 3):
            return
        self.run(f'{_OBJCOPY} --remove-section .codesign "{path}" 2>/dev/null || true')
        self.run(f'{_SIGNTOOL} sign -inFile "{path}" -outFile "{path}" -selfSign 1')
        os.chmod(path, 0o755)

    def _sign_build_tree(self):
        for root, _dirs, files in os.walk(self.build_folder):
            for name in files:
                self._sign_elf(os.path.join(root, name))


    def build(self):
        apply_conandata_patches(self)
        previous_ld_path = self._apply_runtime_env()
        try:
            cmake = CMake(self)
            cmake.configure()
            cmake.build()
            self._sign_build_tree()
            # Runs the three upstream CTest entries:
            # fdf-sample-test, fdf-units-test and fdf-ambiguous-units-test.
            cmake.test()
        finally:
            if previous_ld_path is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = previous_ld_path

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
        self.cpp_info.libs = ["fdf"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.system_libs = ["m"]

        includedirs = ["include"]
        include_root = os.path.join(self.package_folder, "include")
        for root, _dirs, files in os.walk(include_root):
            if any(name.endswith(".mod") for name in files):
                relative = os.path.relpath(root, self.package_folder).replace(
                    "\\", "/"
                )
                if relative not in includedirs:
                    includedirs.append(relative)
        self.cpp_info.includedirs = includedirs

        self.cpp_info.set_property("cmake_file_name", "libfdf")
        self.cpp_info.set_property("cmake_target_name", "libfdf::libfdf")
        self.cpp_info.set_property("pkg_config_name", "libfdf")
