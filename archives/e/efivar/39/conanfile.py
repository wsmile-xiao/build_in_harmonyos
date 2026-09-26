#!/usr/bin/env python3
"""Conan recipe for efivar 39 — EFI variable manipulation library.

efivar provides libraries (libefivar, libefiboot, libefisec) and tools
(efivar, efisecdb) for manipulating UEFI variables on Linux/OHOS.

Build system: plain Makefile (no configure, no CMake).
The musl libc on HarmonyOS lacks qsort_r(), secure_getenv(), and
program_invocation_short_name — these are provided by musl_shim.c/h
patches.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class EfivarConan(ConanFile):
    name = "efivar"
    version = "39"
    description = "Library and tools for the manipulation of EFI variables"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/rhboot/efivar"
    url = "https://github.com/rhboot/efivar"
    package_type = "library"

    settings = ("os", "compiler", "build_type", "arch")
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    exports_sources = "*"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "efivar is supported only on Linux/OHOS"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _compiler(self):
        # R33: Get compiler from Conan conf, never from shell env vars.
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return comp_execs.get("c") or "clang"

    def build(self):
        cc = self._compiler()

        # efivar uses a plain Makefile (no configure step).
        # CC/CCLD/HOSTCC/HOSTCCLD must all point to the same clang for
        # cross-compilation to work on OHOS.
        # ERRORS="" disables -Werror (musl/clang produces new warnings).
        # WARNINGS="-Wall" keeps useful warnings without failing the build.
        # ENABLE_DOCS=0 avoids needing asciidoc/xmllint.

        # The Makefile has a circular dependency: makeguids binary generates
        # efivar-guids.h, but makeguids.c includes efivar.h which includes
        # efivar-guids.h. Make detects this and drops the dependency, leaving
        # makeguids unbuilt. We must manually compile and link makeguids first.
        src_dir = os.path.join(self.source_folder, "src")
        common_flags = (
            f"-fPIC -O2 -std=gnu11 -funsigned-char -fvisibility=hidden "
            f"-DLIBEFIVAR_VERSION=39 -D_GNU_SOURCE -D_FILE_OFFSET_BITS=64 "
            f"-I{os.path.join(src_dir, 'include')} "
            f"-include {os.path.join(src_dir, 'musl_shim.h')} "
            f"-DEFIVAR_BUILD_ENVIRONMENT"
        )

        # Step 1: Compile makeguids objects and musl_shim.o
        self.run(f"{cc} {common_flags} -c -o {os.path.join(src_dir, 'makeguids.o')} {os.path.join(src_dir, 'makeguids.c')}", cwd=self.source_folder)
        self.run(f"cp {os.path.join(src_dir, 'util.c')} {os.path.join(src_dir, 'util-makeguids.c')}", cwd=self.source_folder)
        self.run(f"{cc} {common_flags} -c -o {os.path.join(src_dir, 'util-makeguids.o')} {os.path.join(src_dir, 'util-makeguids.c')}", cwd=self.source_folder)
        self.run(f"{cc} {common_flags} -c -o {os.path.join(src_dir, 'musl_shim.o')} {os.path.join(src_dir, 'musl_shim.c')}", cwd=self.source_folder)

        # Step 2: Link makeguids binary
        self.run(
            f"{cc} -L. -Wl,-z,now -Wl,-z,relro "
            f"-o {os.path.join(src_dir, 'makeguids')} "
            f"{os.path.join(src_dir, 'makeguids.o')} "
            f"{os.path.join(src_dir, 'util-makeguids.o')} "
            f"{os.path.join(src_dir, 'musl_shim.o')} -ldl",
            cwd=src_dir,
        )

        # Step 3: Run full make (makeguids already built, so circular dep is resolved)
        self.run(
            f"make CC={cc} CCLD={cc} HOSTCC={cc} HOSTCCLD={cc} "
            f'ERRORS="" WARNINGS="-Wall" ENABLE_DOCS=0 -j1',
            cwd=self.source_folder,
        )

        # Step 4: Run upstream tests (tests/Makefile, 14 registered TESTS).
        # 3 tests (test.dmpstore.export / test.efivar.export / test.grubenv.var)
        # require grub2-editenv which is absent on OHOS; 11 tests exercise the
        # efivar/efisecdb CLI against checked-in goal files and the thread-test
        # against a local scratch efivarfs emulation. Run the runnable subset
        # non-blocking and record results.
        if can_run(self):
            self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream tests that do not need grub2-editenv.

        tests/Makefile derives binary paths from $(TOPDIR), which the
        top-level Makefile exports but a bare `make -C tests` does not —
        pass it explicitly. The efivar/efisecdb binaries are OHOS ELF
        executables; run them through the bash wrapper so the shell layer
        can load them (mksh cannot exec them directly).
        """
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        runnable = [
            "test.bootorder.var",
            "test.conin.var",
            "test.efivar.threading",
            "test.parse.db",
            "test.esl.annotation",
            "test.esl.sha256.unsorted",
            "test.esl.sha256.ascending",
            "test.esl.sha256.removal.descending",
            "test.esl.sha256.addition.unsorted",
            "test.esl.cert.addition",
            "test.esl.cert.removal",
        ]
        passed = 0
        failed = []
        for t in runnable:
            ret = self.run(
                f'make -C tests TOPDIR="{self.source_folder}" '
                f'SHELL="{bash}" {t}',
                cwd=self.source_folder,
                env="conanbuild",
                ignore_errors=True,
            )
            if ret == 0:
                passed += 1
            else:
                failed.append(t)
        self.output.info(
            f"efivar upstream tests: {passed}/{len(runnable)} passed"
            + (f" (failed: {', '.join(failed)})" if failed else "")
        )

    def package(self):
        # R33: re-derive compiler for the install step (install depends on all).
        cc = self._compiler()

        # Install with DESTDIR to redirect into package_folder.
        # PREFIX=/ with explicit LIBDIR/INCLUDEDIR/BINDIR overrides so that
        # files land at lib/, include/, bin/ relative to package root.
        self.run(
            f"make install "
            f"CC={cc} CCLD={cc} HOSTCC={cc} HOSTCCLD={cc} "
            f'ERRORS="" WARNINGS="-Wall" '
            f"DESTDIR={self.package_folder} "
            f"PREFIX=/ LIBDIR=/lib INCLUDEDIR=/include BINDIR=/bin "
            f"ENABLE_DOCS=0",
            cwd=self.source_folder,
        )

        # Copy license
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["efivar", "efiboot", "efisec"]
        self.cpp_info.includedirs = ["include", "include/efivar"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "efivar")
        self.cpp_info.set_property("cmake_target_name", "efivar::efivar")
        self.cpp_info.set_property("pkg_config_name", "efivar")
