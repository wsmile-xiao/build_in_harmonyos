#!/usr/bin/env python3
"""Conan test_package for libscrypt 1.22 — Conan L1 official test.

Compiles test.c against the Conan-built libscrypt (CMakeDeps +
CMakeToolchain) and runs it on the target via self.run(). The test calls
the real libscrypt_scrypt() API with tiny parameters (N=2, r=1, p=1, 32B
out) and checks a byte-exact known-answer vector, so it genuinely links
and exercises the packaged library — no host stub, no empty shell.

OHOS linker-runtime note:
  test_package is an independent Conan build flow: it does NOT inherit the
  LD_LIBRARY_PATH that the main conanfile sets in its build(). The OHOS
  clang driver spawns `lld` for linking. lld is a dynamically linked ELF
  whose NEEDED list includes libxml2.so.16, resolved via its RUNPATH
  ($ORIGIN/../lib → the SDK llvm/lib). On CI workers the ambient
  LD_LIBRARY_PATH (e.g. ~/usr/local/lib) can shadow that dir with an
  ABI-mismatched libxml2.so.16, so lld fails to start during
  CMakeTestCCompiler try_compile with "Error loading shared library
  libxml2.so.16 ... xmlFreeDoc: symbol not found" and configure aborts.
  This is the same runtime fix the main conanfile applies in build();
  test_package must set up the SDK LLVM runtime path itself around
  cmake.configure() / cmake.build(). No new Conan dependency is added
  (libxml2 is the SDK's own runtime, not a libscrypt build input).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibscryptTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    # ── Toolchain resolution (R33: from Conan conf, not host shell) ──────
    def _cc(self):
        # Profile config may carry a stale toolchain path (e.g.
        # /data/service/hnp/bin/clang that does not exist on this host).
        # Verify the configured binary actually exists; otherwise fall
        # back to `clang` resolved from the Conan buildenv PATH, which on
        # OHOS is the real clang wrapper that auto-signs the ELF.
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = comp_execs.get("c", "clang")
        if os.path.isabs(cc):
            return cc if os.path.exists(cc) else "clang"
        return cc if shutil.which(cc) else "clang"

    # ── OHOS SDK linker runtime path (lld/libxml2.so.16) ──────────────
    def _sdk_llvm_libdir(self):
        """Resolve the active OHOS SDK llvm/lib containing libxml2.so.16.

        Derives the dir from the real clang path (tools.build:compiler_executables
        → resolved by _cc()), never hardcoding a user name, an SDK version,
        or an absolute path. On non-OHOS hosts returns "".
        """
        if str(self.settings.os) != "OHOS":
            return ""
        cc = self._cc()
        # _cc() may return a bare name ("clang") when the profile path is
        # stale. os.path.realpath on a bare name resolves against CWD, not
        # PATH — so resolve it to an absolute path via shutil.which first,
        # then take the physical realpath (dereferencing any symlink).
        cc_resolved = shutil.which(cc) or cc
        cc_real = os.path.realpath(cc_resolved)
        llvm_lib = os.path.join(os.path.dirname(os.path.dirname(cc_real)), "lib")
        # Only trust the dir if it actually carries libxml2.so.16 — guards
        # against stale profile paths or a bare `clang` on PATH whose parent
        # is not the SDK.
        if os.path.isfile(os.path.join(llvm_lib, "libxml2.so.16")):
            return llvm_lib
        return ""

    def _build_environment(self):
        """Conan Environment that prepends the SDK llvm/lib to LD_LIBRARY_PATH.

        Applied around cmake.configure() / cmake.build() so clang → lld
        inherit it. No new Conan dependency is added (libxml2 is the SDK's
        own runtime, not a libscrypt build input).
        """
        env = Environment()
        sdk_lib = self._sdk_llvm_libdir()
        if sdk_lib:
            self.output.info(
                f"Prepending OHOS SDK linker runtime path for lld: {sdk_lib}"
            )
            env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
        return env

    def generate(self):
        # The shared profile may carry a stale tools.build:compiler_executables
        # path (e.g. /data/service/hnp/bin/clang) that does not exist on this
        # host. CMakeToolchain would bake that dead path into CMAKE_C_COMPILER
        # and break configure. Resolve a real C compiler (validated by _cc())
        # and pin it explicitly so the generated toolchain file always points
        # at a usable compiler.
        env = CMakeToolchain(self)
        env.variables["CMAKE_C_COMPILER"] = self._cc()
        env.generate()

    def build(self):
        cmake = CMake(self)
        # cmake.configure() runs CMakeTestCCompiler try_compile, which links
        # via clang → lld. lld needs the SDK's libxml2.so.16 at runtime, so
        # the SDK LLVM lib dir must be on LD_LIBRARY_PATH during configure
        # AND build — both spawn the linker. On non-OHOS hosts this is a
        # no-op (empty Environment).
        with self._build_environment().vars(self).apply():
            cmake.configure()
            cmake.build()

    def test(self):
        # Run the compiled test binary directly against the Conan-built
        # libscrypt. can_run() guards cross-compile cases where the target
        # binary cannot execute on the build host.
        if can_run(self):
            exe = os.path.join(self.cpp.build.bindirs[0], "test_libscrypt")
            self.run(exe, env="conanrun")
