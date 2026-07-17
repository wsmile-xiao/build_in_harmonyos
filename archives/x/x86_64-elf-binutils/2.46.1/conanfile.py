#!/usr/bin/env python3
"""Conan recipe — x86_64-elf-binutils 2.46.1 (Autotools, cross-toolchain).

GNU binutils configured as a cross-development toolchain that targets the
x86_64-elf (bare-metal) ABI. The assembler, linker and binary utilities
(x86_64-elf-as, x86_64-elf-ld, x86_64-elf-objdump, x86_64-elf-ar, ...) are
built to run on the HarmonyOS PC (aarch64) host and operate on x86_64 ELF
objects; they do not execute x86_64 code on the host.

R32: settings.os supports both Linux and OHOS.
R33: compiler and flags come from AutotoolsToolchain (ohos-aarch64 profile);
     no bare shell env vars (CC/CFLAGS/...) are used in build().
R38: produces executables -> commands.json declared, cpp_info.bindirs set.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class X8664ElfBinutilsConan(ConanFile):
    name = "x86_64-elf-binutils"
    version = "2.46.1"
    description = "GNU binutils cross-toolchain targeting x86_64-elf (bare-metal)"
    license = "GPL-3.0"
    homepage = "https://www.gnu.org/software/binutils/"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)

        # Build a cross-toolchain: the tools run on the build host (HarmonyOS
        # PC aarch64) and target the x86_64-elf bare-metal ABI. binutils
        # auto-prefixes every tool with "x86_64-elf-" when target != host.
        tc.configure_args.append("--target=x86_64-elf")

        # Build only static libraries (libbfd/libopcodes/...) so no .so is
        # shipped, keeping the toolchain self-contained and free of any
        # system-library collision (R26 spirit).
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")

        # gprofng relies on the Linux-specific SIGEV_THREAD_ID, which is not
        # available on HarmonyOS -> must be disabled.
        tc.configure_args.append("--disable-gprofng")

        # gdb/gdbserver/sim pull in heavy host dependencies (ncurses/python/...)
        # that are unnecessary for an assemble/link cross toolchain.
        tc.configure_args.append("--disable-gdb")
        tc.configure_args.append("--disable-gdbserver")
        tc.configure_args.append("--disable-sim")

        # No NLS/gettext, and do not let clang warnings fail the build.
        tc.configure_args.append("--disable-nls")
        tc.configure_args.append("--disable-werror")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # The build-host clang passes linker-only options such as `-fuse-ld=lld`
        # on every invocation, including the configure preprocessor probes
        # (`$CC -E`). There the option is unused and clang prints a "argument
        # unused" warning on stderr; autoconf's legacy preprocess-mode header
        # check treats any stderr as failure and wrongly leaves
        # HAVE_LIMITS_H / HAVE_FCNTL_H / HAVE_SPAWN_H / ... unset. That breaks
        # libiberty (LONG_MIN in fibheap.c, O_* in pex-unix.c, posix_spawn ...).
        # Suppressing that single diagnostic gives the probes clean stderr so
        # the headers are detected correctly. Harmless when no such flag exists.
        os.environ["CPPFLAGS"] = (
            (os.environ.get("CPPFLAGS", "") + " -Wno-unused-command-line-argument").strip()
        )

        # musl ships mallinfo/mallinfo2 as linkable compatibility stubs but
        # does not define `struct mallinfo` / `struct mallinfo2` in <malloc.h>.
        # autoconf's link-only AC_CHECK_FUNCS therefore wrongly sets
        # HAVE_MALLINFO(_2) and ld's ldmain.c fails to compile on the incomplete
        # type. The functions are unusable on musl; ld just skips the optional
        # malloc statistics, so report them as absent.
        os.environ["ac_cv_func_mallinfo"] = "no"
        os.environ["ac_cv_func_mallinfo2"] = "no"

        autotools = Autotools(self)
        autotools.configure()
        # binutils is large; serial builds risk the CI timeout, so use modest
        # parallelism (capped to avoid memory pressure).
        jobs = min(os.cpu_count() or 2, 8)
        autotools.make(args=[f"-j{jobs}"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Cross-toolchain: the deliverables are the x86_64-elf-* executables
        # installed under bin/.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
