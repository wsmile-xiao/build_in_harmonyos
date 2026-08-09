#!/usr/bin/env python3
"""Conan recipe - LLD 20.1.8 (CMake)."""

import os
import shutil
import tarfile

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


class LldConan(ConanFile):
    name = "lld"
    version = "20.1.8"
    description = "LLVM project high-performance linker"
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://lld.llvm.org/"
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
                "lld/20.1.8 supports only OpenHarmony PC aarch64"
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
        tc.variables["LLVM_ENABLE_PROJECTS"] = "lld"
        tc.variables["LLVM_ENABLE_RUNTIMES"] = ""
        tc.variables["LLVM_INCLUDE_TESTS"] = True
        tc.variables["LLVM_BUILD_TESTS"] = False
        # Cap concurrent link jobs (the memory-heavy phase of the check-lld
        # test-tool build: llvm-objdump/opt/llc/dsymutil/...). Unbounded links
        # on the constrained CI worker OOM-kill conan create silently right
        # after the lit suite passes; compile parallelism is untouched.
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
        if str(self.settings.os) == "OHOS":
            tc.variables["LLVM_TARGETS_TO_BUILD"] = "AArch64"
            tc.variables["LLVM_DEFAULT_TARGET_TRIPLE"] = "aarch64-linux-ohos"
        tc.generate()

    def build(self):
        known_ohos_xfails = (
            "COFF/lto-cache-errors.ll",
            "COFF/thinlto-emit-imports.ll",
            "ELF/lto/resolution-err.ll",
            "ELF/lto/thinlto-cant-write-index.ll",
            "ELF/lto/thinlto-emit-imports.ll",
            "MachO/invalid/invalid-lto-object-path.ll",
            "MachO/lto-object-path.ll",
            "MachO/thinlto-emit-imports.ll",
        )
        temporary_directory = os.path.join(
            os.path.expanduser("~"),
            "tmp",
            "lld-build-tmp",
        )
        os.makedirs(temporary_directory, mode=0o770, exist_ok=True)
        build_environment = Environment()
        build_environment.define("TMPDIR", temporary_directory)
        build_environment.define("LIT_PRESERVES_TMP", "1")
        build_environment.define("LIT_XFAIL", ";".join(known_ohos_xfails))
        if shutil.which("ccache"):
            ccache_directory = os.path.join(
                os.path.expanduser("~"), ".ccache", "lld-20.1.8-aarch64"
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
            # Keep full compile parallelism (tools.build:jobs, 20 on the CI
            # worker): capping it to -j8 made the full 1821+1357 object build
            # exceed the 2700s CI timeout (conan create TIMED OUT after the
            # main lld target linked). Link concurrency is capped separately
            # via LLVM_PARALLEL_LINK_JOBS=2 in generate() to avoid OOM.
            cmake.build(target="lld")
            cmake.build(target="check-lld")

        reproduction_archive = os.path.join(
            self.build_folder,
            "tools",
            "lld",
            "test",
            "ELF",
            "Output",
            "reproduce-error.s.tmp.dir",
            "repro.tar",
        )
        if not os.path.isfile(reproduction_archive):
            raise ConanException("check-lld did not create the reproduction archive")
        try:
            with tarfile.open(reproduction_archive) as archive:
                response = archive.extractfile("repro/response.txt")
                if response is None or not response.read():
                    raise ConanException(
                        "LLD reproduction archive contains an empty response.txt"
                    )
        except (KeyError, OSError, tarfile.TarError) as error:
            raise ConanException(
                f"Unable to validate LLD reproduction archive "
                f"{reproduction_archive}: {error}"
            ) from error

    def package(self):
        source = os.path.join(self.build_folder, "bin")
        destination = os.path.join(self.package_folder, "bin")
        copy(
            self,
            "LICENSE.TXT",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        os.makedirs(destination, exist_ok=True)
        for command in ("lld", "ld.lld", "lld-link", "ld64.lld", "wasm-ld"):
            shutil.copy2(
                os.path.join(source, "lld"),
                os.path.join(destination, command),
            )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        binary_directory = os.path.join(self.package_folder, "bin")
        self.buildenv_info.prepend_path("PATH", binary_directory)
        self.runenv_info.prepend_path("PATH", binary_directory)
