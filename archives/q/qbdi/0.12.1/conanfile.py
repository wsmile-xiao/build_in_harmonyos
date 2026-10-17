#!/usr/bin/env python3
"""Conan recipe for QBDI 0.12.1 (QuarkslaB Dynamic binary Instrumentation)
on HarmonyOS PC.

Path C evidence (source / build / test configuration):
  * ``README.rst`` states it plainly: "A local version of llvm is statically
    built within QBDI because QBDI uses **private APIs not exported by regular
    LLVM installations** and because our code is only compatible with a specific
    version of those APIs."  ``cmake/llvm/QBDI_llvm.cmake`` pins
    ``QBDI_LLVM_VERSION 19.1.5`` and pulls the LLVM *source* through
    FetchContent, merging it into ``libQBDI.a`` via ``merge_archives.cmake``.
    It also drives LLVM TableGen (``QBDI_llvm_tblgen.cmake``) - a build-time
    code generator that must execute on the host.
  * The engine emits and patches AArch64 code at run time into executable
    memory, rewrites instructions it does not understand, and maintains the
    instruction cache.

Portability findings on HarmonyOS PC (all reproduced on the device):
  1. ``config.guess`` in ``llvm-19.1.5.src.tar.xz`` predates HarmonyOS and exits
     non-zero; LLVM's ``config-ix.cmake`` calls ``get_host_triple()``
     unconditionally (``LLVM_HOST_TRIPLE`` is an *output*), so configure aborts.
  2. LLVM starts a separate ``NATIVE`` TableGen sub-build which re-autodetects
     the host as HarmonyOS; CMake ships no ``Platform/HarmonyOS`` module so
     ``UNIX`` is unset and ``HandleLLVMOptions.cmake`` aborts with
     "Unable to determine platform".
  3. ``cmake/merge_archives.cmake`` rejects ``CMAKE_SYSTEM_NAME=HarmonyOS``;
     ``-DCMAKE_SYSTEM_NAME=Linux`` is the correct knob because the HarmonyOS PC
     ABI here *is* Linux (musl, ``aarch64-unknown-linux-ohos``).
  4. ``config.guess`` also needs a writable non-HMDFS ``TMPDIR`` (E011 class).

(1) and (2) are fixed by installing two idempotent fix-up scripts into the
source tree and hooking them into QBDI's LLVM FetchContent step before it
configures LLVM.  The hook is applied by direct text edit in ``build()`` rather
than by the ``patch`` tool, so the recipe has no external patching dependency.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get

FIXUPS = ("ohos_config_guess_fix.py", "ohos_llvm_platform_fix.py")

# Anchor + hook inserted into cmake/llvm/QBDI_llvm.cmake right after the LLVM
# FetchContent_Populate() call, i.e. after the tree is extracted and before it
# is configured.
_HOOK_ANCHOR = (
    '  SUBBUILD_DIR "${FETCHCONTENT_BASE_DIR}/llvm-subbuild"\n'
    '  QUIET)\n'
)
_HOOK = '''
# --- OHOS portability hooks (added by the build_in_harmonyos recipe) --------
# LLVM's bundled config.guess does not know HarmonyOS and LLVM config-ix.cmake
# calls get_host_triple() unconditionally, so configure aborts; and LLVM's
# NATIVE TableGen sub-build trips over "Unable to determine platform" because
# CMake has no Platform/HarmonyOS module.  Both fix-ups are idempotent.
execute_process(
  COMMAND python3 "${CMAKE_CURRENT_LIST_DIR}/ohos_config_guess_fix.py"
          "${FETCHCONTENT_BASE_DIR}/qbdi_llvm/llvm/cmake/config.guess")
execute_process(
  COMMAND python3 "${CMAKE_CURRENT_LIST_DIR}/ohos_llvm_platform_fix.py"
          "${FETCHCONTENT_BASE_DIR}/qbdi_llvm/llvm")
'''


class QBDIConan(ConanFile):
    name = "qbdi"
    version = "0.12.1"
    description = (
        "QBDI: QuarkslaB Dynamic binary Instrumentation - LLVM-based DBI "
        "framework with an embedded AArch64 JIT and a private statically "
        "linked LLVM 19.1.5"
    )
    license = "Apache-2.0"
    homepage = "https://github.com/QBDI/QBDI"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"

    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def validate(self):
        # R32: OHOS must be accepted alongside Linux, never "== Linux".
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"QBDI supports Linux and OHOS only, got {self.settings.os}"
            )
        if str(self.settings.arch) not in ("armv8", "aarch64", "ARM64"):
            raise ConanInvalidConfiguration(
                f"this recipe is configured for AArch64, got {self.settings.arch}"
            )

    def export_sources(self):
        copy(self, "ohos_*_fix.py",
             src=os.path.join(self.recipe_folder, "fixups"),
             dst=self.export_sources_folder)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True, verify=True)

    def _conf_tool(self, key, default):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get(key, default)

    def _install_ohos_fixups(self):
        """Install the fix-up scripts and hook them into QBDI_llvm.cmake."""
        llvm_dir = os.path.join(self.source_folder, "cmake", "llvm")
        for f in FIXUPS:
            copy(self, f, src=self.export_sources_folder, dst=llvm_dir,
                 keep_path=False)
            if not os.path.isfile(os.path.join(llvm_dir, f)):
                raise ConanInvalidConfiguration(
                    "OHOS fix-up script missing after export: {}".format(f)
                )

        cmk = os.path.join(llvm_dir, "QBDI_llvm.cmake")
        with open(cmk, encoding="utf-8") as fh:
            text = fh.read()
        if "ohos_config_guess_fix" in text:
            self.output.info("OHOS fix-up hooks already present")
            return
        if _HOOK_ANCHOR not in text:
            raise ConanInvalidConfiguration(
                "cannot hook OHOS fix-ups: anchor not found in {}".format(cmk)
            )
        with open(cmk, "w", encoding="utf-8") as fh:
            fh.write(text.replace(_HOOK_ANCHOR, _HOOK_ANCHOR + _HOOK, 1))
        self.output.info("OHOS fix-up hooks installed into QBDI_llvm.cmake")

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        # HarmonyOS is autodetected by CMake, but QBDI's merge_archives.cmake and
        # the LLVM build both key off CMAKE_SYSTEM_NAME; the ABI here is Linux.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["QBDI_PLATFORM"] = "linux"
        tc.variables["QBDI_ARCH"] = "AARCH64"
        tc.variables["QBDI_TEST"] = "ON"
        # Components needing extra host tooling / that would widen the package:
        tc.variables["QBDI_TOOLS_FRIDAQBDI"] = "OFF"
        tc.variables["QBDI_TOOLS_PYQBDI"] = "OFF"
        tc.variables["QBDI_INCLUDE_DOCS"] = "OFF"
        tc.variables["QBDI_CCACHE"] = "OFF"
        tc.generate()

    def build(self):
        self._install_ohos_fixups()
        cmake = CMake(self)
        cmake.configure()
        # R9: serial build.  QBDI statically links its own LLVM 19.1.5, which is
        # the bulk of the work; -j1 is deliberate.
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        inc = os.path.join(self.package_folder, "include")

        # The public headers come from TWO places, and both are needed:
        #
        #   1. <source>/include - the hand-written headers.  "*.h" + "*.hpp"
        #      rather than "*.h*", because the latter also matches the
        #      configure_file() templates QBDI/Config.h.in and
        #      QBDI/Version.h.in, whose generated counterparts are added next.
        #   2. the CMake build tree - configure_file() writes QBDI/Version.h
        #      and the architecture-selected QBDI/Options.h and QBDI/State.h
        #      into <build>/include, and QBDI/Config.h into
        #      <build>/include-{static,shared}.  None of these exist in the
        #      source tree, so a recipe that only copies (1) ships a package
        #      that cannot compile: QBDI/Platform.h includes QBDI/Config.h.
        src_inc = os.path.join(self.source_folder, "include")
        copy(self, "*.h", src=src_inc, dst=inc, keep_path=True)
        copy(self, "*.hpp", src=src_inc, dst=inc, keep_path=True)
        copy(self, "*.h", src=os.path.join(self.build_folder, "include"),
             dst=inc, keep_path=True)
        cfg_dir = "include-shared" if self.options.shared else "include-static"
        copy(self, "*.h", src=os.path.join(self.build_folder, cfg_dir),
             dst=inc, keep_path=True)

        # Fail loudly rather than shipping a header set that cannot compile.
        required = ["QBDI.h",
                    os.path.join("QBDI", "Config.h"),
                    os.path.join("QBDI", "Version.h"),
                    os.path.join("QBDI", "State.h"),
                    os.path.join("QBDI", "Options.h"),
                    os.path.join("QBDI", "Memory.hpp")]
        missing = [h for h in required
                   if not os.path.isfile(os.path.join(inc, h))]
        if missing:
            raise ConanInvalidConfiguration(
                "packaged headers are incomplete, missing: {} (source include "
                "dir read from {})".format(missing, src_inc)
            )

        libdir = os.path.join(self.package_folder, "lib")
        copy(self, "libQBDI.a", src=self.build_folder, dst=libdir, keep_path=False)
        copy(self, "libqbdi-llvm.a", src=self.build_folder, dst=libdir,
             keep_path=False)
        if self.options.shared:
            copy(self, "libQBDI.so*", src=self.build_folder, dst=libdir,
                 keep_path=False)
        produced = os.listdir(libdir) if os.path.isdir(libdir) else []
        if not any(n.startswith("libQBDI") for n in produced):
            raise ConanInvalidConfiguration(
                "no libQBDI was produced; contents of libdir: {}".format(produced)
            )

    def package_info(self):
        self.cpp_info.libs = ["QBDI"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
