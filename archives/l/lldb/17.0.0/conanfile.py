#!/usr/bin/env python3
"""Conan recipe - LLDB 17.0.0 (LLVM monorepo, CMake/Ninja)."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LldbConan(ConanFile):
    name = "lldb"
    version = "17.0.0"
    description = "LLVM project debugger (LLDB)"
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://lldb.llvm.org/"
    url = "https://github.com/llvm/llvm-project"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "lldb/17.0.0 supports only OpenHarmony PC aarch64"
            )
        check_min_cppstd(self, 17)

    no_copy_source = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        ccache_program = shutil.which("ccache")
        if ccache_program:
            tc.variables["CMAKE_C_COMPILER_LAUNCHER"] = ccache_program
            tc.variables["CMAKE_CXX_COMPILER_LAUNCHER"] = ccache_program
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["LLVM_BUILD_LLVM_DYLIB"] = False
        tc.variables["LLVM_LINK_LLVM_DYLIB"] = False
        # LLDB's expression evaluator and command layer link against Clang
        # libraries, so the monorepo build must enable both clang and lldb
        # (LLDBConfig.cmake requires clang resource headers/artifacts).
        tc.variables["LLVM_ENABLE_PROJECTS"] = "clang;lldb"
        tc.variables["LLVM_ENABLE_RUNTIMES"] = ""
        tc.variables["LLVM_TARGETS_TO_BUILD"] = "AArch64"
        tc.variables["LLVM_DEFAULT_TARGET_TRIPLE"] = "aarch64-linux-ohos"
        tc.variables["LLVM_INCLUDE_TESTS"] = True
        tc.variables["LLVM_BUILD_TESTS"] = False
        # Cap concurrent link jobs (memory-heavy phase of the test-tool
        # build). Unbounded links exhaust the constrained CI worker RAM.
        tc.variables["LLVM_PARALLEL_LINK_JOBS"] = "2"
        tc.variables["LLVM_INCLUDE_EXAMPLES"] = False
        tc.variables["LLVM_INCLUDE_BENCHMARKS"] = False
        tc.variables["LLVM_INCLUDE_DOCS"] = False
        tc.variables["LLVM_ENABLE_BINDINGS"] = False
        tc.variables["LLVM_ENABLE_TERMINFO"] = False
        tc.variables["LLVM_ENABLE_ZLIB"] = False
        tc.variables["LLVM_ENABLE_ZSTD"] = False
        tc.variables["LLVM_ENABLE_LIBXML2"] = False
        tc.variables["LLVM_ENABLE_LIBEDIT"] = False
        tc.variables["LLVM_ENABLE_CURL"] = False
        # r04: Python bindings enable the upstream API dotest suite. r11:
        # enable conditionally — only when an ABI-usable Python3 dev
        # environment and a runnable native SWIG are actually available on
        # the build host (probe executables + dev headers/lib, no executor
        # absolute paths hard-coded). On hosts without them, fall back to
        # LLDB_ENABLE_PYTHON/SWIG=False so the core lldb still configures.
        python_ok = False
        python3_exe = shutil.which("python3")
        if python3_exe and os.access(python3_exe, os.X_OK):
            python_include = os.path.join(
                os.path.dirname(os.path.dirname(python3_exe)),
                "include", "python3.12")
            python_lib_dir = os.path.join(
                os.path.dirname(os.path.dirname(python3_exe)), "lib")
            python_lib = os.path.join(python_lib_dir, "libpython3.12.so")
            python_ok = (
                os.path.isdir(python_include)
                and os.path.isfile(os.path.join(python_include, "Python.h"))
                and os.path.isfile(python_lib)
            )
        swig_exe = shutil.which("swig")
        swig_ok = swig_exe is not None and os.access(swig_exe, os.X_OK)
        if python_ok and swig_ok:
            tc.variables["LLDB_ENABLE_PYTHON"] = True
            tc.variables["LLDB_ENABLE_SWIG"] = True
            tc.variables["SWIG_EXECUTABLE"] = swig_exe
            tc.variables["Python3_EXECUTABLE"] = python3_exe
            tc.variables["Python3_INCLUDE_DIR"] = python_include
            tc.variables["Python3_LIBRARY"] = python_lib
        else:
            # Fall back to no Python/SWIG so CI hosts without the dev env
            # can still build the core LLDB driver/server.
            tc.variables["LLDB_ENABLE_PYTHON"] = False
            tc.variables["LLDB_ENABLE_SWIG"] = False
        tc.variables["LLDB_ENABLE_LUA"] = False
        tc.variables["LLDB_INCLUDE_TESTS"] = True
        tc.generate()

    def build(self):
        temporary_directory = os.path.join(
            os.path.expanduser("~"),
            "tmp",
            "lldb-build-tmp",
        )
        os.makedirs(temporary_directory, mode=0o770, exist_ok=True)
        build_environment = Environment()
        build_environment.define("TMPDIR", temporary_directory)
        build_environment.define("TMP", temporary_directory)
        build_environment.define("TEMP", temporary_directory)
        build_environment.define("LIT_PRESERVES_TMP", "1")
        if shutil.which("ccache"):
            ccache_directory = os.path.join(
                os.path.expanduser("~"), ".ccache", "lldb-17.0.0-aarch64"
            )
            ccache_temporary_directory = os.path.join(
                temporary_directory, "ccache-tmp"
            )
            os.makedirs(ccache_directory, mode=0o770, exist_ok=True)
            os.makedirs(ccache_temporary_directory, mode=0o770, exist_ok=True)
            ccache_base_directory = os.path.commonpath(
                [self.source_folder, self.build_folder]
            )
            build_environment.define("CCACHE_DIR", ccache_directory)
            build_environment.define("CCACHE_TEMPDIR", ccache_temporary_directory)
            build_environment.define("CCACHE_BASEDIR", ccache_base_directory)
            build_environment.define("CCACHE_NOHASHDIR", "true")
            build_environment.define("CCACHE_COMPILERCHECK", "content")
        with build_environment.vars(self).apply():
            cmake = CMake(self)
            cmake.configure(
                build_script_folder=os.path.join(self.source_folder, "llvm")
            )
            # Keep full compile parallelism (tools.build:jobs on the CI
            # worker); link concurrency is capped via LLVM_PARALLEL_LINK_JOBS
            # in generate() to avoid OOM.
            cmake.build(target="lldb")

    def package(self):
        # cmake_layout places the CMake outputs under build/Release (single
        # config), i.e. self.build_folder = <base>/build/Release.
        build_root = self.build_folder
        package_bin = os.path.join(self.package_folder, "bin")
        package_lib = os.path.join(self.package_folder, "lib")
        package_include = os.path.join(self.package_folder, "include")
        for binary in ("lldb", "lldb-argdumper", "lldb-server", "lldb-repro"):
            copy(
                self,
                pattern=binary,
                dst=package_bin,
                src=os.path.join(build_root, "bin"),
            )
        copy(
            self,
            pattern="liblldb.so",
            dst=package_lib,
            src=os.path.join(build_root, "lib"),
        )
        copy(
            self,
            pattern="liblldb.a",
            dst=package_lib,
            src=os.path.join(build_root, "lib"),
        )
        # Public LLDB API headers live in the monorepo source tree
        # (lldb/include/lldb/API/...). Generated configuration headers
        # (Config.h, Version.inc) are produced under
        # <build>/tools/lldb/include/lldb/Host.
        source_include = os.path.join(self.source_folder, "lldb", "include")
        generated_include = os.path.join(
            build_root, "tools", "lldb", "include"
        )
        for include_root in (source_include, generated_include):
            if os.path.isdir(include_root):
                copy(
                    self,
                    pattern="lldb/**",
                    dst=package_include,
                    src=include_root,
                )

    def package_info(self):
        self.cpp_info.libs = ["lldb"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        # bin/lldb 与 liblldb.so 通过相对 NEEDED 链接，消费者运行（含
        # test_package 的 conanrun 环境）必须能解析包内 lib 目录。
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        self.conf_info.define("user.lldb:bin_path",
                              os.path.join(self.package_folder, "bin"))
