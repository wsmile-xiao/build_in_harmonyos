#!/usr/bin/env python3
"""Conan recipe for unicorn 2.1.4 — C CPU emulator + Python bindings (setuptools/CMake).

HarmonyOS PC adaptation (Path B: OHOS platform support contributed upstream):
- builds the C emulator core via CMake (UNICORN_BUILD_TESTS=off)
- packages libunicorn + Python bindings into site-packages
- OHOS platform support added to configure/osdep.h (patches/0001, 0002)
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class UnicornConan(ConanFile):
    name = "unicorn"
    version = "2.1.4"
    description = "Unicorn CPU emulator framework (multi-architecture)"
    license = "GPL-2.0"
    homepage = "https://www.unicorn-engine.org/"
    url = "https://github.com/unicorn-engine/unicorn"

    package_type = "python-require"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Build the C emulator core via CMake (as setup.py build_libraries does)
        src_dir = os.path.join(self.source_folder, "src")
        build_dir = os.path.join(src_dir, "build-ohos")
        os.makedirs(build_dir, exist_ok=True)
        cc = self.settings.get_safe("compiler") and os.environ.get("CC", "clang")
        cmake_args = [
            "cmake", "-B", build_dir, "-S", src_dir,
            "-DCMAKE_BUILD_TYPE=Release",
            # -O2 makes huge TCG files (mips msa_helper.c, riscv softfloat.c)
            # take >290s each on OHOS clang → full-arch build times out.
            # -O1 keeps tests meaningful while compiling fast enough.
            "-DCMAKE_C_FLAGS=-O1",
            "-DUNICORN_BUILD_TESTS=off",
            "-DCMAKE_C_COMPILER=" + cc,
            # Build ALL upstream architectures so every upstream unit test
            # can run for its arch (UC_ERR_ARCH otherwise).
            "-DUNICORN_ARCH=x86;arm;aarch64;riscv;mips;sparc;m68k;ppc;s390x;tricore",
        ]
        subprocess.run(cmake_args, check=True, cwd=src_dir)
        subprocess.run(
            ["cmake", "--build", build_dir, "-j1"], check=True, cwd=src_dir)

    def package(self):
        # Copy C headers (public headers live under src/include/unicorn)
        hdr_dir = os.path.join(self.package_folder, "include", "unicorn")
        os.makedirs(hdr_dir, exist_ok=True)
        src_hdr = os.path.join(self.source_folder, "src", "include", "unicorn")
        for f in os.listdir(src_hdr):
            shutil.copy2(os.path.join(src_hdr, f), os.path.join(hdr_dir, f))
        # Copy built shared library into site-packages/unicorn/lib so the
        # Python bindings' __load_uc_lib() can find it (looks for
        # unicorn/lib/libunicorn.so.2, fallback libunicorn.so)
        site_uc = os.path.join(self.package_folder, "lib", "python3.12",
                               "site-packages", "unicorn")
        lib_dest = os.path.join(site_uc, "lib")
        os.makedirs(lib_dest, exist_ok=True)
        build_dir = os.path.join(self.source_folder, "src", "build-ohos")
        for root, _, files in os.walk(build_dir):
            for f in files:
                if f.startswith("libunicorn.so"):
                    dst = os.path.join(lib_dest, "libunicorn.so.2")
                    shutil.copy2(os.path.join(root, f), dst)
                    shutil.copy2(os.path.join(root, f),
                                 os.path.join(lib_dest, "libunicorn.so"))
        # Copy Python bindings into site-packages
        site = os.path.join(self.package_folder, "lib", "python3.12", "site-packages", "unicorn")
        os.makedirs(site, exist_ok=True)
        src_py = os.path.join(self.source_folder, "unicorn")
        for f in os.listdir(src_py):
            fpath = os.path.join(src_py, f)
            if os.path.isdir(fpath):
                shutil.copytree(fpath, os.path.join(site, f), dirs_exist_ok=True)
            else:
                shutil.copy2(fpath, os.path.join(site, f))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["unicorn"]