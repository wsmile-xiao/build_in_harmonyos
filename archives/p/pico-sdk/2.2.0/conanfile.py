#!/usr/bin/env python3
"""Conan recipe for Raspberry Pi pico-sdk 2.2.0.

The SDK source tree targets RP-series microcontrollers.  The host-side pioasm
tool is built natively and the SDK files are packaged under share/pico-sdk.
"""
import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
    save,
)


class PicoSdkConan(ConanFile):
    name = "pico-sdk"
    version = "2.2.0"
    description = "Raspberry Pi Pico SDK source tree and pioasm host tool"
    license = "BSD-3-Clause"
    homepage = "https://github.com/raspberrypi/pico-sdk"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["PIOASM_VERSION_STRING"] = self.version
        tc.cache_variables["PIOASM_GENERATE_PARSER"] = False
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_CXX_FLAGS"] = "-stdlib=libc++"
            tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = "-lc++ -lpthread"
        tc.generate()

    def _sdk_llvm_libdir(self):
        if str(self.settings.os) != "OHOS":
            return ""

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp") or compilers.get("c")
        candidates = []
        if cxx:
            compiler = os.path.realpath(cxx)
            try:
                resource_dir = subprocess.check_output(
                    [cxx, "-print-resource-dir"],
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()
                candidates.append(os.path.dirname(os.path.dirname(resource_dir)))
            except (OSError, subprocess.CalledProcessError):
                pass
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
            )

        for candidate in dict.fromkeys(candidates):
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                return candidate
        return ""

    def _usable_sdk_llvm_libdir(self):
        if str(self.settings.os) != "OHOS":
            return ""

        cached = getattr(self, "_checked_sdk_llvm_libdir", None)
        if cached is not None:
            return cached

        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            lld = os.path.join(os.path.dirname(sdk_llvm_lib), "bin", "lld")
            probe_env = os.environ.copy()
            old_ld_path = probe_env.get("LD_LIBRARY_PATH", "")
            probe_env["LD_LIBRARY_PATH"] = os.pathsep.join(
                part for part in (sdk_llvm_lib, old_ld_path) if part
            )
            try:
                probe = subprocess.run(
                    [lld, "-flavor", "gnu", "--version"],
                    env=probe_env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError) as error:
                raise ConanException(
                    f"Cannot execute the active OHOS SDK linker {lld}: {error}"
                ) from error
            if probe is not None and probe.returncode == 0:
                self._checked_sdk_llvm_libdir = sdk_llvm_lib
                return sdk_llvm_lib
            raise ConanException(
                f"The active OHOS SDK linker failed its GNU-flavor probe: {lld}; "
                f"stderr={probe.stderr.strip()!r}"
            )

        raise ConanException(
            "Cannot locate the active OHOS SDK llvm/lib containing "
            "libxml2.so.16"
        )

    def _build_environment(self):
        environment = Environment()
        sdk_llvm_lib = self._usable_sdk_llvm_libdir()
        if sdk_llvm_lib:
            self.output.info(
                f"Prepending OHOS SDK linker runtime path: {sdk_llvm_lib}"
            )
            environment.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        return environment

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._build_environment().vars(self).apply():
            cmake.configure(build_script_folder=os.path.join(self.source_folder, "tools", "pioasm"))
            cmake.build(build_tool_args=["-j1"])

        pioasm = self._pioasm_path()
        smoke_pio = os.path.join(self.build_folder, "conan_smoke.pio")
        smoke_header = os.path.join(self.build_folder, "conan_smoke.pio.h")
        save(
            self,
            smoke_pio,
            ".program conan_smoke\n"
            ".wrap_target\n"
            "    pull block\n"
            "    out pins, 1\n"
            ".wrap\n",
        )
        self._run_tool([pioasm, "--version"])
        self._run_tool([pioasm, "-o", "c-sdk", "-v", "0", smoke_pio, smoke_header])
        generated = load(self, smoke_header)
        if "conan_smoke_program" not in generated:
            raise ConanException("pioasm smoke test did not generate the expected C SDK header")

    def package(self):
        cmake = CMake(self)
        cmake.install()

        copy(
            self,
            "LICENSE.TXT",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        sdk_dst = os.path.join(self.package_folder, "share", "pico-sdk")
        for filename in (
            ".gitmodules",
            "BUILD.bazel",
            "CMakeLists.txt",
            "CONTRIBUTING.md",
            "LICENSE.TXT",
            "MODULE.bazel",
            "README.md",
            "REPO.bazel",
            "WORKSPACE",
            "pico_sdk_init.cmake",
            "pico_sdk_version.cmake",
        ):
            copy(self, filename, src=self.source_folder, dst=sdk_dst, keep_path=False)

        for dirname in ("bazel", "cmake", "docs", "external", "src", "test", "tools"):
            copy(
                self,
                "*",
                src=os.path.join(self.source_folder, dirname),
                dst=os.path.join(sdk_dst, dirname),
            )

        # Debian's orig tarball keeps submodule directories empty. Preserve the
        # directory layout so downstream diagnostics match upstream paths.
        for dirname in ("btstack", "cyw43-driver", "lwip", "mbedtls", "tinyusb"):
            os.makedirs(os.path.join(sdk_dst, "lib", dirname), exist_ok=True)

    def package_info(self):
        sdk_path = os.path.join(self.package_folder, "share", "pico-sdk")
        bindir = os.path.join(self.package_folder, "bin")

        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.builddirs = [
            os.path.join("lib", "cmake", "pioasm"),
            os.path.join("share", "pico-sdk"),
        ]

        self.buildenv_info.prepend_path("PATH", bindir)
        self.buildenv_info.define_path("PICO_SDK_PATH", sdk_path)
        self.runenv_info.prepend_path("PATH", bindir)
        self.runenv_info.define_path("PICO_SDK_PATH", sdk_path)

    def _pioasm_path(self):
        exe = "pioasm.exe" if str(self.settings.os) == "Windows" else "pioasm"
        candidates = [
            os.path.join(self.build_folder, exe),
            os.path.join(self.build_folder, str(self.settings.build_type), exe),
            os.path.join(self.build_folder, "bin", exe),
            os.path.join(self.build_folder, "bin", str(self.settings.build_type), exe),
        ]
        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate
        raise ConanException("Cannot locate built pioasm executable")

    def _quote(self, value):
        if str(self.settings.os) == "Windows":
            return f'"{value}"'
        return shlex.quote(value)

    def _run_tool(self, args):
        command = " ".join(self._quote(arg) for arg in args)
        if str(self.settings.os) == "OHOS":
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f"{self._quote(bash)} -lc {self._quote(command)}")
        else:
            self.run(command)
