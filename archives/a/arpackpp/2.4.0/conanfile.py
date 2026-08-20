#!/usr/bin/env python3
"""Conan recipe for arpackpp 2.4.0 — C++ interface to ARPACK.

Header-only INTERFACE library. CMake build system installs headers.
Depends on arpack-ng (ARPACK), openblas (BLAS), lapack (LAPACK).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
import os


class ArpackppConan(ConanFile):
    name = "arpackpp"
    version = "2.4.0"
    description = "ARPACK++: C++ interface to ARPACK"
    license = "BSD-3-Clause"
    homepage = "https://github.com/m-reuter/arpackpp"
    url = "https://github.com/m-reuter/arpackpp"
    topics = ("eigenvalue", "arpack", "linear-algebra", "scientific-computing")

    package_type = "header-library"

    # R32: settings.os 判断必须用 in ("Linux", "OHOS")
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("arpack-ng/3.9.1")
        self.requires("openblas/0.3.34")
        self.requires("lapack/3.12.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Check for local pre-downloaded tarball first (GitHub blocked on OHOS)
        import shutil, hashlib, tarfile
        local_tarball = os.path.join(
            os.environ.get("TMPDIR", os.path.expanduser("~/tmp")),
            "builds", f"{self.name}-{self.version}.tar.gz")
        if os.path.exists(local_tarball):
            expected_sha = self.conan_data["sources"].get("sha256", "")
            actual_sha = hashlib.sha256(
                open(local_tarball, "rb").read()).hexdigest()
            if expected_sha and actual_sha != expected_sha:
                raise RuntimeError(
                    f"SHA256 mismatch: {actual_sha} != {expected_sha}")
            src_folder = self.source_folder
            with tarfile.open(local_tarball, "r:gz") as tf:
                tf.extractall(src_folder, filter="data")
            children = [c for c in os.listdir(src_folder)
                        if not c.startswith(".")]
            if len(children) == 1 and os.path.isdir(
                    os.path.join(src_folder, children[0])):
                subdir = os.path.join(src_folder, children[0])
                for item in os.listdir(subdir):
                    shutil.move(
                        os.path.join(subdir, item),
                        os.path.join(src_folder, item))
                os.rmdir(subdir)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E225: Prevent CMakeUserPresets.json from being written to source
        tc.user_presets_path = False
        # CMake doesn't recognize HarmonyOS; use Linux for cross-compat
        if self.settings.os in ("Linux", "OHOS"):
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["ENABLE_TESTS"] = False
        tc.variables["ENABLE_FORTRAN"] = False
        tc.variables["ENABLE_SUPERLU"] = False
        tc.variables["ENABLE_UMFPACK"] = False
        tc.variables["ENABLE_CHOLMOD"] = False
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        import subprocess
        build_dir = self.build_folder
        generators_dir = os.path.join(build_dir, "generators")
        toolchain = os.path.join(generators_dir, "conan_toolchain.cmake")
        # Clear env vars that interfere with cmake try-compile on OHOS
        for var in ["CC", "CXX", "CFLAGS", "CXXFLAGS", "LDFLAGS", "CPPFLAGS",
                     "CMAKE_PREFIX_PATH", "MAKEFLAGS", "MFLAGS"]:
            os.environ.pop(var, None)
        os.environ.setdefault("TMPDIR", os.path.expanduser("~/tmp"))
        # Use subprocess directly (conan self.run() breaks cmake try-compile)
        r = subprocess.run(
            ["cmake", "-G", "Unix Makefiles",
             f"-DCMAKE_TOOLCHAIN_FILE={toolchain}",
             f"-DCMAKE_INSTALL_PREFIX={self.package_folder}",
             "-DCMAKE_POLICY_DEFAULT_CMP0091=NEW",
             "-DCMAKE_BUILD_TYPE=Release",
             self.source_folder],
            cwd=build_dir, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            print("CMAKE STDERR:", r.stderr[-3000:])
            raise RuntimeError(f"cmake configure failed ({r.returncode})")
        r = subprocess.run(
            ["cmake", "--build", ".", "-j1"],
            cwd=build_dir, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            print("BUILD STDERR:", r.stderr[-3000:])
            raise RuntimeError(f"cmake build failed ({r.returncode})")

    def package(self):
        import subprocess
        r = subprocess.run(
            ["cmake", "--install", "."],
            cwd=self.build_folder, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            print("INSTALL STDERR:", r.stderr[-3000:])
            raise RuntimeError(f"cmake install failed ({r.returncode})")

    def package_info(self):
        self.cpp_info.libs = []
        # Header-only library: headers installed to include/arpackpp/
        self.cpp_info.includedirs = ["include/arpackpp"]
