#!/usr/bin/env python3
"""Conan recipe — libbacktrace 20240505 (autotools, C library).

Adapted for HarmonyOS PC (aarch64, OHOS). Key adaptation points:
- config.guess/config.sub taught to recognize aarch64-unknown-linux-ohos
- configure's private tmp dirs use umask 077 which HMDFS rejects -> umask 022 (E129)
- test binaries: compile flags -fno-optimize-sibling-calls -fno-omit-frame-pointer
  keep the stack frames that upstream btest asserts on (clang drops noclone frames)
- objcopy-derived test binaries lose the .codesign signature required by OHOS;
  Makefile rules re-sign them with binary-sign-tool self-signing

Upstream check suite (make check, 33 tests) runs inside build().
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibbacktraceConan(ConanFile):
    name = "libbacktrace"
    version = "20240505"
    description = "C library producing symbolic backtraces for ELF/Mach-O/XCOFF/PE-COFF programs"
    license = "BSD-3-Clause"
    homepage = "https://github.com/ianlancetaylor/libbacktrace"
    url = "https://github.com/ianlancetaylor/libbacktrace"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ztest/ztest_alloc link -lz (compress in -lz detected by upstream configure)
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: system-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Keep upstream test stack frames: clang ignores __attribute__((noclone)),
        # so sibling-call and frame-pointer optimization break btest/edtest line asserts
        tc.extra_cflags = ["-fno-optimize-sibling-calls", "-fno-omit-frame-pointer"]
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E490: HMDFS copies may drop the exec bit on autotools helper scripts
        for script in ("configure", "config.guess", "config.sub",
                       "install-sh", "missing", "test-driver",
                       "install-debuginfo-for-buildid.sh"):
            self.run(f"test -f {script} && chmod +x {script} || true")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream official test suite: 33 tests (full execution)
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["backtrace"]
