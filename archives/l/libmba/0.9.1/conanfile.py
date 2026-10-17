#!/usr/bin/env python3
"""Conan recipe — libmba 0.9.1 (Makefile project).

libmba uses a plain Makefile; its mktool.c build driver hardcodes the
'gcc' command name (PATH lookup), so the build synthesizes a 'gcc' ->
configured-compiler symlink in a build-local bin dir and prepends it to
PATH. Headers live under src/mba/ and are installed to include/mba/.

Platform note: the svsem(3m)/svcond(3m) modules depend on SysV semaphore
syscalls (semget/semop). On OHOS these syscalls are intercepted by the
seccomp filter (SIGSYS), so those modules cannot be exercised at runtime;
the library itself builds and links normally, and all other modules
(linkedlist, hashmap, csv, cfg, pool, varray, stack, path, suba, text,
diff, time, bitset, daemon, allocator, msgno, eval, hexdump, shellout)
are unaffected. See notes.md and the upstream test report.

This adaptation follows the ohos-aarch64 toolchain: compiler and ar come
from Conan conf (R33), never from shell env vars.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, rmdir
from conan.tools.layout import basic_layout


class LibmbaConan(ConanFile):
    name = "libmba"
    version = "0.9.1"
    description = "A library of generic C modules (linkedlist, hashmap, pool, varray, csv, cfg, path, text, diff, ...)"
    license = "MIT/X Consortium"
    homepage = "https://www.ioplex.com/~miallen/libmba/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        ar = comp_execs.get("ar") or "llvm-ar"
        ranlib = comp_execs.get("ranlib") or "llvm-ranlib"

        # mktool.c constructs compile/link commands that hardcode "gcc" and
        # resolves it through PATH. Put a 'gcc' -> configured compiler
        # symlink in a build-local bin dir so the driver finds the OHOS
        # toolchain compiler. R33: compiler comes from Conan conf.
        bindir = os.path.join(self.build_folder, "bin")
        rmdir(self, bindir)
        os.makedirs(bindir, exist_ok=True)
        for name, target in (("gcc", cc), ("cc", cc)):
            link = os.path.join(bindir, name)
            if os.path.lexists(link):
                os.remove(link)
            os.symlink(target, link)

        env = Environment()
        env.append_path("PATH", bindir)

        # R9: build with -j1. 'all' builds mktool, libmba.a (ar) and
        # libmba.so (shared) — the package needs the static archive; the
        # Makefile has no configure step.
        with env.vars(self).apply():
            self.run(f"make CC={cc} AR={ar} RANLIB={ranlib} -j1", cwd=self.source_folder)

    def package(self):
        # Headers are under src/mba/ and must land in include/mba/
        copy(self, "*.h", os.path.join(self.source_folder, "src", "mba"),
             os.path.join(self.package_folder, "include", "mba"))
        # Static archive (always produced by the Makefile)
        copy(self, "*.a", self.source_folder, os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            # Shared library plus its versioned symlinks
            copy(self, "libmba.so*", self.source_folder, os.path.join(self.package_folder, "lib"))
            copy(self, "libmba.so", self.source_folder, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # LIBNAME in the Makefile is "mba" -> libmba.a / -lmba
        self.cpp_info.libs = ["mba"]