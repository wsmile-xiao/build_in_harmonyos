#!/usr/bin/env python3
"""Conan recipe — riscv64-elf-gdb 17.2 (Autotools, cross-debugger).

GNU GDB configured as a cross-debugger that targets the riscv64-elf
(bare-metal) ABI. The debugger (riscv64-elf-gdb) runs on the HarmonyOS PC
(aarch64) host and operates on riscv64 ELF target objects; it does not
execute riscv64 code on the host.

The build uses the top-level GDB build tree (bfd/opcodes/libiberty/
libctf/libsframe/libbacktrace/gdb/gnulib/...) with --target=riscv64-elf.

R32: settings.os supports both Linux and OHOS.
R33: compiler and flags come from AutotoolsToolchain (ohos-aarch64 profile);
     no bare shell env vars (CC/CFLAGS/...) are used in build().
R37: first adaptation, version "17.2" (no suffix).
R38: produces executables -> commands.json declared, cpp_info.bindirs set.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Riscv64ElfGdbConan(ConanFile):
    name = "riscv64-elf-gdb"
    version = "17.2"
    description = "GNU GDB cross-debugger targeting riscv64-elf (bare-metal)"
    license = "GPL-3.0"
    homepage = "https://www.gnu.org/software/gdb/"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Top-level configure requires gmp+mpfr when gdb/ is present.
        self.requires("gmp/6.3.0")
        self.requires("mpfr/4.2.2")
        # GDB interactive command line.
        self.requires("readline/8.3")
        # GDB XML remote protocol support.
        self.requires("expat/2.8.2")
        # Debug section compression.
        self.requires("zlib/1.3.2")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _stage_dependency_archives(self):
        """E236 scoped-la-free-static-archive-directory.

        Pre-built gmp/6.3.0 and mpfr/4.2.2 packages carry .la files whose
        libdir/dependency_libs paths are non-relocatable (libdir='//lib').
        Libtool gives visible .la files precedence and follows those stale
        paths, failing the final link with:
            cannot find the library '//lib/libgmp.la'

        Per E236, do NOT rewrite the Conan package cache (forbid_1: breaks
        immutability and affects unrelated builds sharing the revision).
        Instead copy only the required static archives into a build-private
        directory that contains NO .la metadata, and pass that directory
        through --with-gmp-lib/--with-mpfr-lib as -L<dir> -lname. Libtool
        then links the raw .a files and never sees the stale .la metadata.
        """
        staged = os.path.join(self.build_folder, ".dep-archives")
        os.makedirs(staged, exist_ok=True)
        for dep_name in ("gmp", "mpfr"):
            dep = self.dependencies[dep_name]
            for libdir in dep.cpp_info.libdirs:
                if not libdir or not os.path.isdir(libdir):
                    continue
                for a_path in glob.glob(os.path.join(libdir, "*.a")):
                    dst = os.path.join(staged, os.path.basename(a_path))
                    if not os.path.exists(dst):
                        shutil.copy2(a_path, dst)
        return staged

    def generate(self):
        tc = AutotoolsToolchain(self)

        # Cross-debugger: runs on OHOS aarch64 host, targets riscv64-elf.
        tc.configure_args.append("--target=riscv64-elf")

        # Explicit build triplet avoids config.guess probing issues (E007).
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")

        # GMP and MPFR from conan dependencies (flint precedent pattern).
        # Lib dirs point at a build-private archive dir WITHOUT .la files
        # (E236 scoped-la-free-static-archive-directory): libtool links the
        # raw .a and cannot follow stale //lib .la paths.
        gmp_info = self.dependencies["gmp"].cpp_info
        mpfr_info = self.dependencies["mpfr"].cpp_info
        staged_lib = self._stage_dependency_archives()
        tc.configure_args.append(
            "--with-gmp-include={}".format(gmp_info.includedirs[0])
        )
        tc.configure_args.append(
            "--with-gmp-lib={}".format(staged_lib)
        )
        tc.configure_args.append(
            "--with-mpfr-include={}".format(mpfr_info.includedirs[0])
        )
        tc.configure_args.append(
            "--with-mpfr-lib={}".format(staged_lib)
        )

        # Use system readline from conan dependency.
        tc.configure_args.append("--with-system-readline")

        # Use system expat from conan dependency.
        tc.configure_args.append("--with-expat")

        # Disable components unnecessary for a cross-debugger.
        tc.configure_args.append("--disable-gdbserver")
        tc.configure_args.append("--disable-sim")
        tc.configure_args.append("--disable-tui")

        # No NLS, no Python scripting (simplifies build, avoids 3.12 compat risk).
        tc.configure_args.append("--without-python")
        tc.configure_args.append("--disable-nls")
        tc.configure_args.append("--disable-werror")

        # Pass dependency include/lib dirs via CPPFLAGS/LDFLAGS so that
        # nested subdirectory configures (gdb/, bfd/, etc.) can find
        # readline, ncurses, expat headers and libraries.
        readline_info = self.dependencies["readline"].cpp_info
        ncurses_info = self.dependencies["ncurses"].cpp_info
        expat_info = self.dependencies["expat"].cpp_info
        zlib_info = self.dependencies["zlib"].cpp_info

        include_dirs = [
            readline_info.includedirs[0],
            ncurses_info.includedirs[0],
            expat_info.includedirs[0],
            zlib_info.includedirs[0],
            gmp_info.includedirs[0],
            mpfr_info.includedirs[0],
        ]
        # gmp/mpfr link dirs use the staged .a dir (no .la), not the Conan
        # cache libdirs, so libtool never follows stale .la metadata.
        lib_dirs = [
            readline_info.libdirs[0],
            ncurses_info.libdirs[0],
            expat_info.libdirs[0],
            zlib_info.libdirs[0],
            staged_lib,
            staged_lib,
        ]

        cppflags = " ".join("-I{}".format(d) for d in include_dirs)
        ldflags = " ".join("-L{}".format(d) for d in lib_dirs)

        tc.extra_cflags.append(cppflags)
        tc.extra_cxxflags.append(cppflags)
        tc.extra_ldflags.append(ldflags)

        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # HMDFS E011: 19 configure scripts contain "umask 077" which creates
        # directories with restrictive permissions on HMDFS. Replace with
        # "umask 022" via glob (flint precedent). Must be done after any
        # autoreconf that would regenerate configure.
        for cfg_path in glob.glob(
            os.path.join(self.source_folder, "**", "configure"),
            recursive=True,
        ):
            try:
                with open(cfg_path, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(cfg_path, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))

        # Same CPPFLAGS fix as x86_64-elf-binutils: host clang passes
        # -fuse-ld=lld on every invocation including $CC -E probes,
        # causing "argument unused" warnings on stderr that autoconf's
        # legacy preprocess-mode header check treats as failure.
        os.environ["CPPFLAGS"] = (
            (os.environ.get("CPPFLAGS", "")
             + " -Wno-unused-command-line-argument").strip()
        )

        # Same mallinfo fix as x86_64-elf-binutils: musl provides
        # mallinfo/mallinfo2 as linkable stubs but does not define the
        # struct, causing autoconf link probes to wrongly set HAVE_MALLINFO.
        os.environ["ac_cv_func_mallinfo"] = "no"
        os.environ["ac_cv_func_mallinfo2"] = "no"

        autotools = Autotools(self)
        autotools.configure()
        # GDB is large; use modest parallelism (capped to avoid memory pressure).
        jobs = min(os.cpu_count() or 2, 8)
        autotools.make(args=[f"-j{jobs}"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # E236: remove any unintended .la metadata generated into the package.
        for la in glob.glob(os.path.join(self.package_folder, "**", "*.la"),
                            recursive=True):
            try:
                os.remove(la)
            except OSError:
                pass

    def package_info(self):
        # Cross-debugger: the deliverable is the riscv64-elf-gdb executable
        # installed under bin/.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
