#!/usr/bin/env python3
"""Conan recipe for lci 1.1, a lambda calculus interpreter.

lci is a single C executable built by CMake. It vendors two git submodules:
dparser (C, builds the host-side make_dparser grammar generator that emits
grammar.g.d_parser.c at build time) and replxx (C++ readline replacement used
only in the interactive REPL). The upstream CMakeLists runs make_dparser as
part of the build, which works in the OHOS-native (self-hosted aarch64)
environment because the generator is compiled by the same native toolchain
and executed on the same machine (E359 host-variables mapping not needed —
there is no cross build gap here).

OHOS adaptation points:
- CMake >= 4 rejects the subprojects' cmake_minimum_required(<3.5); the fix
  goes through cache_variables CMAKE_POLICY_VERSION_MINIMUM=3.5 (E187, and
  draft DRAFT-E321 documents why cache_variables must be used instead of
  tc.variables).
- src/run.c only compiles the termios branch on musl after patch 0001
  guards the TCGETA/TCSETA redefines (musl already defines them and has no
  TIOCGETA/TIOCSETA).
- Terminal tool: BUILD_SHARED_LIBS=OFF (R26) — replxx is linked statically
  into the lci executable.
- The packaged bin/lci is signed (self-sign) and its .codesign section is
  verified, per E486/E489: the same toolchain runs build-tree executables
  (make_dparser, ctest), so signing happens before first execution.
- Upstream tests run via CTest inside build(): build, queens, fixed_point
  (valgrind is conditionally registered upstream and absent on OHOS).
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get


class LciConan(ConanFile):
    name = "lci"
    version = "1.1"
    description = "An interactive interpreter for pure lambda calculus"
    license = "GPL-2.0-only"
    homepage = "https://github.com/chatziko/lci"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # patches/ is exported; conandata.yml is exported automatically.
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(
                f"lci supports Linux/OHOS native builds, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The release archive lacks the git submodules; fetch the exact
        # commits pinned by the v1.1 tag into the expected directories.
        get(self, **self.conan_data["dparser"], strip_root=True,
            destination=os.path.join(self.source_folder, "dparser"))
        get(self, **self.conan_data["replxx"], strip_root=True,
            destination=os.path.join(self.source_folder, "replxx"))

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: terminal tools are linked statically.
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # E187/DRAFT-E321: CMake 4 rejects cmake_minimum_required(<3.5) in
        # dparser (3.0). Must be a cache variable: it has to take effect
        # before any project() call, and tc.variables only lands inside
        # the toolchain file, which the subprojects load too late.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        if can_run(self):
            # On OHOS every first-executed build-tree ELF needs a valid
            # signature (E486/E489). Sign the test closure before CTest.
            if self.settings.os == "OHOS":
                self._sign_ohos_elf(self._lci_executable())
            # Upstream registers CMAKE_CTEST_ARGUMENTS --output-on-failure
            # in its CMakeLists.txt, so cmake.test() inherits it.
            cmake.test()

    def _lci_executable(self):
        # With cmake_layout, build_folder already includes the build_type
        # subdirectory (build/Release); the executable sits at its root.
        exe = os.path.join(self.build_folder, "lci")
        if not os.path.isfile(exe):
            raise ConanException(f"Missing built executable: {exe}")
        return exe

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            self._sign_ohos_elf(os.path.join(self.package_folder, "bin", "lci"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH",
                                      os.path.join(self.package_folder, "bin"))

    def _sign_ohos_elf(self, path):
        # E486/E489: OHOS requires .codesign on executed ELFs. abx 0.1 and
        # aercbook 0.1.6 established the binary-sign-tool + readelf pattern.
        import shutil
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = (
            shutil.which("llvm-readelf")
            or shutil.which("llvm-readobj")
            or shutil.which("readelf")
            or "/data/service/hnp/bin/readelf"
        )
        if not os.path.isfile(path):
            raise ConanException(f"Missing built executable: {path}")
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("Required OHOS signing tools are missing")
        output = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", output],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("Signed executable has invalid .codesign count")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)
