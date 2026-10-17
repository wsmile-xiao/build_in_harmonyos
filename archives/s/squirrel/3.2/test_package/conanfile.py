#!/usr/bin/env python3
"""Consumer test for the public Squirrel VM API."""

import os
import shlex
import glob

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class SquirrelTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        # The Windows build executor has stable Ninja support; MinGW Makefiles
        # mis-handle backslashes in Conan's cross-compile try-compile rules.
        toolchain = CMakeToolchain(self, generator="Ninja")
        sysroot = self.conf.get("tools.build:sysroot", default=None)
        if not sysroot:
            sysroot = os.environ.get("OHOS_NATIVE_SYSROOT", "").strip() or None
        if sysroot:
            toolchain.variables["CMAKE_SYSROOT"] = str(sysroot).replace("\\", "/")
        configured = self.conf.get("tools.build:compiler_executables", default={}) or {}
        configured_c = str(configured.get("c", ""))
        configured_cxx = str(configured.get("cpp", ""))
        llvm_root = os.environ.get("OHOS_NATIVE_LLVM", "").strip()
        if llvm_root and configured_c and not os.path.isfile(configured_c):
            target = os.environ.get("OHOS_TARGET_TRIPLE", "aarch64-linux-ohos").strip()
            toolchain.variables["CMAKE_C_COMPILER_TARGET"] = target
            toolchain.variables["CMAKE_CXX_COMPILER_TARGET"] = target
        toolchain.generate()
        if llvm_root and configured_c and not os.path.isfile(configured_c):
            normalized_llvm_root = llvm_root.replace("\\", "/")
            toolchain_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
            with open(toolchain_file, encoding="utf-8") as handle:
                content = handle.read()
            content = content.replace(configured_cxx, f"{normalized_llvm_root}/clang++.exe")
            content = content.replace(configured_c, f"{normalized_llvm_root}/clang.exe")
            with open(toolchain_file, "w", encoding="utf-8") as handle:
                handle.write(content)
        if sysroot:
            toolchain_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
            with open(toolchain_file, encoding="utf-8") as handle:
                lines = handle.readlines()
            normalized = str(sysroot).replace("\\", "/")
            with open(toolchain_file, "w", encoding="utf-8") as handle:
                for line in lines:
                    if line.startswith("set(CMAKE_SYSROOT "):
                        handle.write(f'set(CMAKE_SYSROOT "{normalized}")\n')
                    else:
                        handle.write(line)

    def build(self):
        self._configure_ohos_linker_runtime()
        cmake = CMake(self)
        toolchain_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        configure_args = [
            cmake._cmake_program,
            "-G",
            cmake._generator,
            f"-DCMAKE_TOOLCHAIN_FILE={toolchain_file}",
            f"-DCMAKE_INSTALL_PREFIX={self.package_folder}",
        ]
        configure_args.extend(
            f"-D{key}={value}" for key, value in cmake._cache_variables.items()
        )
        configure_args.append(self.source_folder)
        self.run(configure_args, env=None, shell=False)
        build_args = [cmake._cmake_program, "--build", self.build_folder]
        jobs = self.conf.get("tools.build:jobs", default=None)
        if jobs:
            build_args.extend(["--parallel", str(jobs)])
        self.run(build_args, env=None, shell=False)

    def _configure_ohos_linker_runtime(self):
        if os.name == "nt" or str(self.settings.os) != "OHOS":
            return

        configured = self.conf.get("tools.build:compiler_executables", default={}) or {}
        compiler = configured.get("cpp") or configured.get("c")
        candidates = []
        llvm_root = os.environ.get("OHOS_NATIVE_LLVM", "").strip()
        if llvm_root:
            candidates.append(os.path.join(llvm_root, "lib"))
            candidates.append(os.path.join(llvm_root, "..", "lib"))
        if compiler:
            compiler_dir = os.path.dirname(str(compiler))
            candidates.append(os.path.join(compiler_dir, "..", "lib"))
            sdk_parent = os.path.normpath(os.path.join(compiler_dir, ".."))
            for pattern in (
                os.path.join(sdk_parent, "ohos-sdk.org", "*", "ohos", "native", "llvm", "lib"),
                os.path.join(sdk_parent, "ohos-sdk", "*", "ohos", "native", "llvm", "lib"),
            ):
                candidates.extend(sorted(glob.glob(pattern)))

        for candidate in candidates:
            candidate = os.path.normpath(candidate)
            if not os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                continue
            existing = [item for item in os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep) if item]
            if candidate not in existing:
                os.environ["LD_LIBRARY_PATH"] = os.pathsep.join([candidate, *existing])
            self.output.info("Using OHOS linker host runtime: %s" % candidate)
            return

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built Squirrel consumer cannot run on this host")
            return
        self.run(shlex.join([os.path.join(self.cpp.build.bindirs[0], "squirrel_consumer")]), env="conanrun")
