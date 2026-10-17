#!/usr/bin/env python3
"""Conan 2 recipe for WAILI 19990723 on OpenHarmony PC.

WAILI is a 1999 C++ wavelet/image-processing library.  Upstream has no
formal test runner: test/Makefile builds six demonstration programs, which
are the available integration checks.  This recipe builds the static
libwaili library and all six programs with the profile's clang++ and runs
the viable programs from the consumer package.  Histogram's plotting path
needs gnuplot, and Rangecheck has an upstream 64-bit PixType precondition
that cannot be met by the project's s16 PixType; both limitations are
reported explicitly by test_package instead of being counted as passes.
"""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


_OBJCOPY = "/data/service/hnp/bin/llvm-objcopy"
_SIGNTOOL = "/data/service/hnp/bin/binary-sign-tool"



_PROGRAMS = ("Demo", "Example", "Histogram", "Proof", "Rangecheck", "Test")


class WailiConan(ConanFile):
    name = "waili"
    version = "19990723"
    description = "Wavelet image-processing library and demonstration programs"
    license = "GPL-2.0-or-later"
    homepage = "https://deb.debian.org/debian/pool/main/w/waili/"
    url = "https://deb.debian.org/debian/pool/main/w/waili/"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"waili supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cxx(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compilers.get("cpp") or compilers.get("cxx")
        if not cxx:
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables must define the cpp compiler"
            )
        if os.path.isabs(cxx):
            if not os.path.isfile(cxx):
                raise ConanInvalidConfiguration(f"configured C++ compiler is missing: {cxx}")
        elif shutil.which(cxx) is None:
            raise ConanInvalidConfiguration(f"configured C++ compiler is not on PATH: {cxx}")
        return cxx

    def _tool(self, cxx, names, fallback):
        compiler_dir = os.path.dirname(os.path.abspath(cxx))
        for name in names:
            candidate = os.path.join(compiler_dir, name)
            if os.path.isfile(candidate):
                return candidate
            found = shutil.which(name)
            if found:
                return found
        return fallback

    def _shell(self):
        candidates = [
            "/data/service/hnp/bin/bash",
            shutil.which("bash"),
            "/system/bin/sh",
            shutil.which("sh"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration("no POSIX shell is available to run config/Configure")

    def build(self):
        apply_conandata_patches(self)
        cxx = self._cxx()
        ar = self._tool(cxx, ("llvm-ar", "ar"), "llvm-ar")
        ranlib = self._tool(cxx, ("llvm-ranlib", "ranlib"), "llvm-ranlib")
        make = shutil.which("make") or "make"
        shell = self._shell()

        config_dir = os.path.join(self.source_folder, "config")
        self.run(f'"{shell}" ./Configure', cwd=config_dir, env="conanbuild")

        cxxflags = [
            "-Wall",
            f"-I{self.source_folder}/include",
            "-O3",
            "-fomit-frame-pointer",
            "-std=c++17",
        ]
        ldflags = [
            f"-L{self.source_folder}/lib",
            "-lwaili",
            "-lm",
        ]
        if str(self.settings.compiler.libcxx) == "libc++":
            cxxflags.append("-stdlib=libc++")
            ldflags.append("-stdlib=libc++")

        common = [
            f"CXX={shlex.quote(cxx)}",
            f"AR={shlex.quote(ar)}",
            f"RANLIB={shlex.quote(ranlib)}",
            f"CFLAGS={shlex.quote(' '.join(cxxflags))}",
        ]
        self.run(
            " ".join(
                [shlex.quote(make), "-C", shlex.quote(os.path.join(self.source_folder, "lib")), "-j1"]
                + common
            ),
            env="conanbuild",
        )
        self.run(
            " ".join(
                [shlex.quote(make), "-C", shlex.quote(os.path.join(self.source_folder, "test")), "-j1"]
                + common
                + [f"LFLAGS={shlex.quote(' '.join(ldflags))}"]
            ),
            env="conanbuild",
        )

        missing = [
            name
            for name in _PROGRAMS
            if not os.path.isfile(os.path.join(self.source_folder, "test", name))
        ]
        if missing:
            raise ConanException("waili build did not produce: " + ", ".join(missing))

    def package(self):
        test_dir = os.path.join(self.source_folder, "test")
        bin_dir = os.path.join(self.package_folder, "bin")
        for program in _PROGRAMS:
            copy(self, program, src=test_dir, dst=bin_dir)
        for program in _PROGRAMS:
            path = os.path.join(bin_dir, program)
            if not os.path.isfile(path):
                raise ConanException(f"missing built program: {program}")
            if os.path.isfile(_SIGNTOOL):
                self.run(
                    f'{_OBJCOPY} --remove-section .codesign "{path}" 2>/dev/null || true',
                    env="conanbuild",
                )
                self.run(
                    f'{_SIGNTOOL} sign -inFile "{path}" -outFile "{path}" -selfSign 1',
                    env="conanbuild",
                )
            os.chmod(path, 0o755)

        copy(
            self,
            "libwaili.a",
            src=os.path.join(self.source_folder, "lib"),
            dst=os.path.join(self.package_folder, "lib"),
        )
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "include", "waili"),
            dst=os.path.join(self.package_folder, "include", "waili"),
        )
        copy(
            self,
            "README.GPL",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["waili"]
        self.cpp_info.system_libs = ["m"]
