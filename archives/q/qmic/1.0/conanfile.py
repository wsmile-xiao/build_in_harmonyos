#!/usr/bin/env python3
"""Conan recipe for qmic 1.0 — QMI IDL compiler (Qualcomm MSM Interface).

qmic is a small, dependency-free C compiler that turns a `.qmi` IDL description
into C source/header pairs. It reads the IDL from stdin, takes `-a` (accessor
backend) or `-k` (kernel backend), and writes `qmi_<package>.c` /
`qmi_<package>.h` into the current directory.

Upstream (linux-msm/qmic, BSD-3-Clause) is a hand-written Makefile project with
no configure script and no install target beyond `install -D` of the single
binary.  The whole tool is four translation units plus two headers; `qmic.c`
already declares `extern const char *__progname;` for its usage message.

Adaptation notes (HarmonyOS PC, aarch64):
    * Build system untouched: the Makefile is `CC`-overridable and only uses
      default variables, so build() injects CC/CFLAGS/LDFLAGS on the make
      command line (R33: compiler path comes from the Conan conf
      `tools.build:compiler_executables`, never a bare shell variable).
    * One portability patch (parser.c): yyerror() prefixes parse errors with
      `program_invocation_short_name`, a glibc-only extension that OHOS musl
      does not declare (compile error: undeclared identifier).  The patch uses
      `__progname` instead — exported by glibc, musl and OHOS libc alike, and
      already the symbol upstream qmic.c uses for the same purpose.  No
      platform conditional is introduced, so non-OHOS builds are unaffected
      (verified by building the same patch set with glibc gcc).
    * Upstream Makefile `install` needs install(1) and bakes PREFIX into the
      destination path; package() copies the binary directly instead.
    * The `tests/*.qmi` inputs are driven from test_package (see MANIFEST.yml).
Artifacts: bin/qmic (software-level commands.json declares the CLI, R38).
License: BSD-3-Clause.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class QmicConan(ConanFile):
    name = "qmic"
    version = "1.0"
    description = "QMI IDL compiler — generates C accessor/kernel sources from .qmi IDL"
    license = "BSD-3-Clause"
    homepage = "https://github.com/linux-msm/qmic"
    url = ""  # CI fills this
    topics = ("qmi", "idl", "compiler", "codegen", "qualcomm", "cli")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # Plain hand-written Makefile project: build in the source folder.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        # R9: -j1.  Command-line assignments beat the Makefile's defaults, so
        # the OHOS SDK clang is used and no shell variable is consulted (R33).
        self.run('make -j1 CC="{0}" CFLAGS="-pipe -O2 -Wall"'.format(cc))

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        licdir = os.path.join(self.package_folder, "licenses")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(licdir, exist_ok=True)
        # Direct copy: upstream `make install` needs install(1) and hardcodes
        # PREFIX into the destination path.
        copy(self, "qmic", src=self.source_folder, dst=bindir, keep_path=False)
        copy(self, "LICENSE", src=self.source_folder, dst=licdir, keep_path=False)
        binary = os.path.join(bindir, "qmic")
        if not os.path.isfile(binary):
            raise ConanException("package(): missing build artifact %s" % binary)
        os.chmod(binary, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
