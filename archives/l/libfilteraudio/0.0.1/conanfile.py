#!/usr/bin/env python3
"""Conan recipe for libfilteraudio 0.0.1 (upstream hand-written Makefile).

libfilteraudio — lightweight audio filtering library extracted from WebRTC
code: echo cancellation (AEC), noise suppression (NS), automatic gain control
(AGC), voice activity detection (VAD) and the ZAM high/low-pass filters.
Upstream: https://github.com/irungentoo/filter_audio (tag v0.0.1).

Adaptation notes (HarmonyOS OHOS aarch64):
- Upstream builds with a plain Makefile (no configure/CMakeLists), so the
  recipe drives `make` directly. The compiler is taken from the Conan conf
  (R33), never from an inherited shell CC/CFLAGS.
- No source patch is required on aarch64: the SSE2 translation units
  (aec/aec_core_sse2.c, aec/aec_rdft_sse2.c) are wrapped in `#ifdef __SSE2__`
  and every `WebRtc_GetCPUInfo(kSSE2)` call site sits under
  `WEBRTC_ARCH_X86_FAMILY`, so the portable C path is compiled as-is.
- The upstream Makefile still carries `VERSION = 0.0.0` (the v0.0.1 tag does
  not bump it), which fixes the shared-library name and soname at
  libfilteraudio.so.0.0.0 / libfilteraudio.so.0. The recipe deliberately does
  not override VERSION: passing VERSION=0.0.1 would silently move the soname
  to libfilteraudio.so.1 and misdeclare the ABI.
- `make install` rewrites filteraudio.pc with `prefix=` set to the *build*
  directory. package() therefore regenerates the .pc with a relocatable
  `${pcfiledir}/../..` prefix (same idiom as abiword-plugin-*) and reports the
  upstream release version 0.0.1.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.layout import basic_layout


class LibfilteraudioConan(ConanFile):
    name = "libfilteraudio"
    version = "0.0.1"
    description = "Lightweight audio filtering library made from webrtc code (AEC/NS/AGC/VAD)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/irungentoo/filter_audio"
    url = "https://github.com/irungentoo/filter_audio"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # The Makefile sits at the root of the extracted sources, so the build
        # folder must stay on them: the default basic_layout build folder
        # (build-<build_type>/) has no Makefile ("No targets specified and no
        # makefile found"). Same pattern as abduco/0.6.
        basic_layout(self, build_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: the toolchain must come from the Conan conf; a bare ${CC} is
        # empty on the release worker, and the Makefile default (`cc`) does
        # not exist in the OHOS sysroot.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        # R9: never -j$(nproc); the upstream Makefile has no recursion anyway.
        self.run(f"make -j1 CC={cc}")

    def package(self):
        # Empty PREFIX installs under the Conan-standard layout
        # (<package>/include + <package>/lib) and keeps the upstream symlink
        # chain (libfilteraudio.so -> .so.0 -> .so.0.0.0) intact.
        self.run(
            "make install DESTDIR={} PREFIX= LIBDIR=lib INCLUDEDIR=include".format(
                self.package_folder
            )
        )
        # Upstream always builds both artifacts; keep only the one selected by
        # the `shared` option so the package does not mix ABIs.
        if self.options.shared:
            rm(self, "libfilteraudio.a", os.path.join(self.package_folder, "lib"))
        else:
            for so_name in (
                "libfilteraudio.so",
                "libfilteraudio.so.0",
                "libfilteraudio.so.0.0.0",
            ):
                rm(self, so_name, os.path.join(self.package_folder, "lib"))
        self._write_relocatable_pc()

    def _write_relocatable_pc(self):
        """Replace the build-directory-anchored .pc written by `make install`.

        The upstream rule substitutes prefix with `$(abspath $(PREFIX))`, i.e.
        the build directory, which is a dead path once the package is in the
        cache. Regenerate it relative to the .pc location (${pcfiledir}) and
        report the upstream release version (0.0.1) instead of the Makefile's
        internal ABI string (0.0.0).
        """
        pc_path = os.path.join(
            self.package_folder, "lib", "pkgconfig", "filteraudio.pc"
        )
        pc_text = (
            "prefix=${pcfiledir}/../..\n"
            "libdir=${prefix}/lib\n"
            "includedir=${prefix}/include\n"
            "\n"
            "Name: filteraudio\n"
            "Description: Lightweight audio filtering library made from webrtc code\n"
            f"Version: {self.version}\n"
            "Libs: -L${libdir} -lfilteraudio\n"
            "Cflags: -I${includedir}\n"
        )
        os.makedirs(os.path.dirname(pc_path), exist_ok=True)
        with open(pc_path, "w", encoding="utf-8") as handle:
            handle.write(pc_text)

    def package_info(self):
        self.cpp_info.libs = ["filteraudio"]
        # The upstream Makefile links -lm -lpthread; static consumers need both.
        self.cpp_info.system_libs = ["m", "pthread"]
