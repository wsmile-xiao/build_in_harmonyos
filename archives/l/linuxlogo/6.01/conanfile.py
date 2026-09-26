#!/usr/bin/env python3
"""linuxlogo 6.01 (Linux Logo by Vince Weaver) recipe for HarmonyOS PC.

Build system: hand written ./configure + raw Makefile (no autoconf).

Upstream configure contract (measured on the B build host, 2026-09-25):
  * configure parses ONLY "--prefix=PATH"; every other argv token falls
    through an uncased "case ${1%=*}" and is silently discarded, and CC /
    CFLAGS are re-derived unconditionally from its own compiler probe.
  * The probe is "which gcc"; when both gcc and cc are absent it only
    prints "C compiler not found!", leaves CC empty, and still exits 0.
    Makefile.default then bakes CC= (empty) and CFLAGS=-O2, so make dies
    with a confusing "make: O2: No such file or directory".
  Therefore this recipe drives the build through *make command line*
  variables (which GNU make also forwards to the libsysinfo sub-make via
  MAKEFLAGS) and never relies on environment CC/CFLAGS.

Both configure and make build in-tree: ./configure writes Makefile.default
next to the raw Makefile, so every command below passes an explicit cwd
(conanfile.run() otherwise inherits the process cwd, which is the *build*
folder under basic_layout, where ./configure does not exist).
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LinuxlogoConan(ConanFile):
    name = "linuxlogo"
    version = "6.01"
    description = ("Linux Logo - print a distribution logo plus CPU, memory "
                   "and uptime information to the terminal")
    license = "GPL-2.0-or-later"
    author = "Vince Weaver"
    homepage = "http://www.deater.net/weave/vmwprod/linux_logo/"
    url = "https://github.com/deater/linux_logo"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # conan 2.29 registers only the dict-typed conf; the per-language
        # "…:c" form is not a conf name and raises ConanException on read.
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict)
        cc = compilers.get("c") or "clang"
        ar = compilers.get("ar") or "llvm-ar"
        shell = os.environ.get("CONFIG_SHELL", "sh")
        src = self.source_folder

        # configure only accepts --prefix; it is still required because the
        # Makefile refuses to run without a generated Makefile.default.
        self.run("{0} ./configure --prefix={1}".format(shell, self.package_folder), cwd=src)

        # OS=Linux is needed twice: libsysinfo selects its backend with
        # "cd $(OS) && make", and uname -m reports "HarmonyOS", for which no
        # backend directory ships. It reads /proc, which HongMeng provides.
        # USE_I18N=0 / TRANSLATIONS= drop the gettext and po/ path, which
        # needs libintl.h (absent from the OHOS native sysroot).
        make_vars = ("CC={0} AR={1} OS=Linux USE_I18N=0 TRANSLATIONS=".format(cc, ar))
        self.run("make {0} -j1".format(make_vars), cwd=src)

        self._upstream_tests(cc, ar)

    def _upstream_tests(self, cc, ar):
        """Run every case the tarball ships under tests/ (tests/README:
        "some tests checking for buffer overruns in linux_logo").

        tests/Makefile is stale (CC=gcc, LIBSYSINFO=libsysinfo-0.2.2 while the
        tarball ships libsysinfo-0.3.0), so both are overridden on the command
        line; it only builds memory_print / memory_method, the two shell
        drivers test1/test2 need no build step.

        Exit statuses measured on the B build host (2026-09-25, same tree the
        recipe produces) and asserted below:
            test1         rc 0   (invokes ./linux_logo, hence the copy)
            test2         rc 1   (upstream prints "Error!  Not enough room in
                                  string!" - the guard firing IS the pass)
            memory_print  rc 0   (size pretty-print table, last row "1PB")
            memory_method rc 0   (per-backend dump, prints a MEMINFO block)
        All four run with cwd=tests/, because test2 references ../linux_logo.
        """
        tests = os.path.join(self.source_folder, "tests")
        copy(self, "linux_logo", self.source_folder, tests)
        self.run("make -C tests CC={0} AR={1} LIBSYSINFO=libsysinfo-0.3.0 -j1".format(cc, ar),
                 cwd=self.source_folder)

        cases = [
            ("test1", "sh test1", 0, None),
            ("test2", "sh test2", 1, "Not enough room in string"),
            ("memory_print", "./memory_print", 0, "1PB"),
            ("memory_method", "./memory_method", 0, "MEMINFO"),
        ]
        for name, cmd, want_rc, needle in cases:
            log = os.path.join(self.build_folder, "upstream-{0}.log".format(name))
            proc = subprocess.run("{0} > {1} 2>&1 < /dev/null".format(cmd, log),
                                  shell=True, cwd=tests)
            body = ""
            if os.path.isfile(log):
                with open(log, "rb") as handle:
                    body = handle.read().decode("utf-8", "replace")
            if proc.returncode != want_rc:
                raise RuntimeError("upstream tests/{0}: rc={1}, expected {2}; output tail: {3}"
                                   .format(name, proc.returncode, want_rc, body[-200:]))
            if needle is not None and needle not in body:
                raise RuntimeError("upstream tests/{0}: {1!r} missing from output; tail: {2}"
                                   .format(name, needle, body[-200:]))
            self.output.info("upstream tests/{0}: OK (rc={1}{2})".format(
                name, want_rc, ", marker matched" if needle else ""))

    def package(self):
        copy(self, "linux_logo", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "linux_logo.1*", self.source_folder,
             os.path.join(self.package_folder, "man", "man1"))
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        os.chmod(os.path.join(self.package_folder, "bin", "linux_logo"), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_find_mode", "none")
