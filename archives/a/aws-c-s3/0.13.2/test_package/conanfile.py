#!/usr/bin/env python3
"""Conan test_package — aws-c-s3 0.13.2 (CMake).

L1 test: verifies aws-c-s3 library loads and S3 API can be called.

Note: aws-c-http (a transitive dependency) references aws_tls_handler_protocol
which is not compiled in aws-c-io (built with BYO_CRYPTO=ON). The test_package
provides a stub.c that defines this symbol, and uses --export-dynamic +
--allow-shlib-undefined to make it available for dynamic linking.

Runtime environment: aws-c-s3 is the deepest in the dependency chain (L5).
Pre-built .so files from Conan remote have NEEDED entries with full absolute
paths (e.g. /home/user/.conan2/p/.../libfoo.so) instead of sonames. On CI
workers where Conan cache is at ~/.cache/conan2/ (not ~/.conan2/), the dynamic
linker loads from the embedded path, fails, and exits (127).

We can't use patchelf to modify .so (breaks files on HMDFS, chmod can't
restore exec permissions due to SELinux). Instead, create symlinks at the
expected paths so the dynamic linker finds the actual files.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AwsCs3TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        import subprocess
        import shutil

        # Pre-built .so files from Conan remote have NEEDED entries with
        # full absolute paths (e.g. /home/user/.conan2/p/.../libfoo.so)
        # instead of sonames. On CI workers where Conan cache is at
        # ~/.cache/conan2/ (not ~/.conan2/), the dynamic linker loads
        # from the embedded path, fails, and exits (127).
        #
        # We can't use patchelf to modify .so (breaks files on HMDFS, chmod
        # can't restore exec permissions due to SELinux). Instead, create
        # symlinks at the expected paths so the dynamic linker finds the
        # actual files.
        patchelf = shutil.which("patchelf") or "/data/service/hnp/bin/patchelf"
        test_binary = os.path.join(self.cpp.build.bindir, "test_aws_c_s3")

        # Collect all dependency lib dirs and build soname -> path map
        lib_paths = []
        soname_map = {}
        for dep in self.dependencies.host.values():
            if not dep.package_folder:
                continue
            lib_dir = os.path.join(dep.package_folder, "lib")
            if lib_dir not in lib_paths:
                lib_paths.append(lib_dir)
            if os.path.isdir(lib_dir):
                for f in os.listdir(lib_dir):
                    if f.endswith(".so"):
                        soname_map[f] = os.path.join(lib_dir, f)

        # For each .so, check NEEDED entries for absolute paths that
        # don't exist. Create symlinks at those paths pointing to the
        # actual file (found by soname in our lib dirs).
        conan_home = os.path.expanduser("~/.conan2")
        cache_home = os.path.expanduser("~/.cache/conan2")
        for dep in self.dependencies.host.values():
            if not dep.package_folder:
                continue
            lib_dir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(lib_dir):
                continue
            for f in os.listdir(lib_dir):
                if not f.endswith(".so"):
                    continue
                so_path = os.path.join(lib_dir, f)
                r = subprocess.run(
                    [patchelf, "--print-needed", so_path],
                    capture_output=True, text=True
                )
                for line in r.stdout.splitlines():
                    line = line.strip()
                    if "/" not in line or os.path.exists(line):
                        continue
                    soname = os.path.basename(line)
                    actual = soname_map.get(soname)
                    if not actual:
                        # Try replacing ~/.conan2 with ~/.cache/conan2
                        if line.startswith(conan_home):
                            actual = cache_home + line[len(conan_home):]
                            if not os.path.exists(actual):
                                actual = None
                    if actual and os.path.exists(actual):
                        try:
                            os.makedirs(os.path.dirname(line), exist_ok=True)
                            if not os.path.exists(line):
                                os.symlink(actual, line)
                        except OSError:
                            pass

        ld_path = ":".join(lib_paths)
        self.run(f"LD_LIBRARY_PATH={ld_path} {test_binary}")
