#!/usr/bin/env python3
"""Conan recipe for mdm 0.1.3 (cklin's Middleman Distributed Make).

Scope: the pure-libc core (mdm-run, mdm-master, mdm-slave).  mdm-top — the
ncurses monitor UI — is deliberately not built: it is the only program that
needs -lcurses, and the recipe carries no curses dependency (see notes.md for
the disclosure; delivering the coordination core is the package's substance).

Why build() drives the compiler itself instead of `make`:
  * the upstream link rule `mdm-% : programs/mdm-%.c $(LIB)` hands clang a
    .c file together with .o files plus -o — clang 15 refuses `-o` with
    multiple input files (gcc accepts it; the Makefile predates clang);
  * `override CC := ...` also prefixes `mdm-run` when it happens to be on
    PATH, which we must not depend on;
  * everything else the Makefile does (install with /usr/bin/install, sed
    rewriting, gzip man pages) is Debian packaging, replaced by package().

One UB-fix patch, zero dependencies: eight translation units compiled with an
explicit clang invocation and linked into the three binaries (R33: compiler
from Conan conf; R9: serial compile).
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy
from conan.tools.layout import basic_layout

# translation units -> binary membership (mdm-top intentionally excluded)
COMPILE = [
    "library/buffer.c", "library/comms.c", "library/socket.c",
    "library/hazard.c", "library/procfs.c",
    "programs/mdm-run.c", "programs/mdm-master.c", "programs/mdm-slave.c",
]
LINK = {
    "mdm-run": ["programs/mdm-run.o", "library/buffer.o",
                "library/comms.o", "library/socket.o"],
    "mdm-master": ["programs/mdm-master.o", "library/buffer.o",
                   "library/comms.o", "library/socket.o", "library/hazard.o"],
    "mdm-slave": ["programs/mdm-slave.o", "library/buffer.o",
                  "library/comms.o", "library/socket.o"],
}


class MdmConan(ConanFile):
    name = "mdm"
    version = "0.1.3"
    description = ("Middleman Distributed Make core (mdm-run/mdm-master/"
                   "mdm-slave); the ncurses monitor mdm-top is not built")
    license = "Apache-2.0"
    homepage = "https://github.com/cklin/mdm"
    url = "https://github.com/cklin/mdm"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # Single UB-fix patch: programs/mdm-run.c execvp(*argv, ++argv) is
        # unsequenced (UB); authoritative wording: conandata/notes.md.
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        return compilers.get("c") or "cc"

    def _run(self, argv, cwd):
        env = dict(os.environ)
        env.pop("CPATH", None)  # no deps; keep the env minimal and explicit
        proc = subprocess.run(argv, cwd=cwd, env=env,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)
        out = proc.stdout.decode(errors="replace")
        if out:
            self.output.info(out)
        if proc.returncode != 0:
            raise ConanException("%s failed with exit code %d"
                                 % (argv[0], proc.returncode))

    def build(self):
        # Applies the single UB-fix patch declared in conandata.yml:
        # 0001-mdm-run-fix-unsequenced-execvp.patch (programs/mdm-run.c).
        apply_conandata_patches(self)
        # R33: compiler from Conan conf; R9: serial.  CFLAGS mirror the
        # upstream override line (-Wall -D_GNU_SOURCE -Iinclude); the default
        # -O is left to the toolchain via CFLAGS from the profile when the
        # conf provides it, otherwise -O2 as a sane floor.
        cc = self._cc()
        cflags = ["-O2", "-Wall", "-D_GNU_SOURCE", "-Iinclude"]
        cwd = self.source_folder
        for src in COMPILE:
            obj = src[:-1] + "o"
            self._run([cc] + cflags + ["-c", "-o", obj, src], cwd)
        for binary, objs in LINK.items():
            self._run([cc, "-o", binary] + objs, cwd)
        for binary in LINK:
            exe = os.path.join(cwd, binary)
            if not os.path.isfile(exe):
                raise ConanException("build(): missing artifact %s" % exe)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        licdir = os.path.join(self.package_folder, "licenses")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(licdir, exist_ok=True)
        copy(self, "mdm-*", src=self.source_folder, dst=bindir,
             keep_path=False)
        copy(self, "LICENSE", src=self.source_folder, dst=licdir,
             keep_path=False)
        for binary in LINK:
            exe = os.path.join(bindir, binary)
            if not os.path.isfile(exe):
                raise ConanException("package(): missing artifact %s" % exe)
            os.chmod(exe, 0o755)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
