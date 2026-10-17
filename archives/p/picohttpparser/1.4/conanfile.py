#!/usr/bin/env python3
"""Conan recipe for picohttpparser 1.4 — single translation unit, no build system.

Upstream ships no build system for the library itself: its Makefile only carries
the test target (test-bin + prove). The library is therefore compiled directly,
taking compiler and archiver from the Conan conf instead of relying on bare
shell variables (R33).

The upstream suite (R51) is executed inside build(): test-bin is compiled the
same way upstream's Makefile does it (-Wall -fsanitize=address,undefined) from
picohttpparser.c + picotest/picotest.c + test.c, and then run. picotest is the
framework pinned by upstream's .gitmodules; GitHub source tarballs do not carry
submodule contents, so it is fetched as a second source by source().

picohttpparser has no system counterpart (there is no /lib/libpicohttpparser.so),
so the R26 system-same-name static rule does not apply. `shared` defaults to
False, matching the packaging of picohttpparser/1.2, but a proper versioned
shared object (real file + .so.1 + .so symlinks) is built as well when the
option is enabled.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# OHOS: /system/bin/sh (mksh) may fail to exec an ELF file directly; wrap in bash.
_SHELL_FALLBACK = "/data/service/hnp/bin/bash"

# SONAME major: picohttpparser is a source-level library without an ABI policy,
# the major number of the packaged version is used to follow ELF conventions.
_SO_MAJOR = 1


class PicohttpparserConan(ConanFile):
    name = "picohttpparser"
    version = "1.4"
    description = "Tiny HTTP request/response parser written in C, with zero dependencies."
    license = "MIT"
    homepage = "https://github.com/h2o/picohttpparser"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["picohttpparser"], strip_root=True)
        # test.c includes "picotest/picotest.h" and upstream's Makefile compiles
        # picotest/picotest.c alongside it, so picotest must land in
        # <source_folder>/picotest.
        get(self, **self.conan_data["sources"]["picotest"], strip_root=True,
            destination="picotest")

    def generate(self):
        pass

    def _tool(self, name, default):
        # R33: tool paths come from the Conan conf, never from the shell environment.
        conf = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        return conf.get(name, default)

    def _shell(self):
        return os.environ.get("CONFIG_SHELL", _SHELL_FALLBACK)

    # ---- library artefact names -------------------------------------------------
    @property
    def _so_real_name(self):
        return f"libpicohttpparser.so.{self.version}"

    @property
    def _so_soname(self):
        return f"libpicohttpparser.so.{_SO_MAJOR}"

    def build(self):
        apply_conandata_patches(self)
        cc = self._tool("c", "clang")
        ar = self._tool("ar", "llvm-ar")
        opt = "-O0 -g" if self.settings.build_type == "Debug" else "-O2"
        pic = "-fPIC" if (self.options.get_safe("fPIC", True) or self.options.shared) else ""

        src = os.path.join(self.source_folder, "picohttpparser.c")
        obj = os.path.join(self.build_folder, "picohttpparser.o")

        compile_cmd = " ".join(p for p in [cc, opt, pic, "-c", f'"{src}"', "-o", f'"{obj}"'] if p)
        self.run(compile_cmd, env="conanbuild")

        if self.options.shared:
            so = os.path.join(self.build_folder, self._so_real_name)
            link_cmd = " ".join(p for p in [
                cc, opt, pic, "-shared", f"-Wl,-soname,{self._so_soname}",
                f'"{obj}"', "-o", f'"{so}"',
            ] if p)
            self.run(link_cmd, env="conanbuild")
        else:
            lib = os.path.join(self.build_folder, "libpicohttpparser.a")
            self.run(f'{ar} rcs "{lib}" "{obj}"', env="conanbuild")

        self._run_upstream_tests(cc)

    def _run_upstream_tests(self, cc):
        """Build and run the upstream suite (upstream `make test`).

        Upstream runs `prove -v ./test-bin`; the binary is itself the TAP
        producer and picotest's done_testing() returns the number of failed
        tests as the process exit code, so running it directly yields the same
        verdict without depending on the Perl harness being installed.
        """
        sf = self.source_folder
        test_bin = os.path.join(self.build_folder, "test-bin")
        self.run(
            f'{cc} -Wall -fsanitize=address,undefined '
            f'"{os.path.join(sf, "picohttpparser.c")}" '
            f'"{os.path.join(sf, "picotest", "picotest.c")}" '
            f'"{os.path.join(sf, "test.c")}" '
            f'-I"{sf}" -o "{test_bin}"',
            env="conanbuild",
        )
        # `bash -c '<binary>'` execs the ELF; passing the binary as bash's
        # argument would make bash interpret it as a shell script instead.
        # TEST_ENV from upstream's Makefile is preserved so UBSan behaves the
        # same way here (halt_on_error makes a UB report fail the build).
        ubsan = 'UBSAN_OPTIONS="print_stacktrace=1:halt_on_error=1"'
        self.run(f"{self._shell()} -c '{ubsan} \"{test_bin}\"'", env="conanbuild")

    def package(self):
        copy(self, "picohttpparser.h",
             dst=os.path.join(self.package_folder, "include"), src=self.source_folder)
        libdir = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            copy(self, self._so_real_name, dst=libdir, src=self.build_folder)
            # R5: remove before re-creating, and never use `ln -sf`.
            for link in (self._so_soname, "libpicohttpparser.so"):
                path = os.path.join(libdir, link)
                if os.path.islink(path) or os.path.exists(path):
                    os.remove(path)
                os.symlink(self._so_real_name, path)
        else:
            copy(self, "libpicohttpparser.a", dst=libdir, src=self.build_folder)

    def package_info(self):
        self.cpp_info.libs = ["picohttpparser"]
