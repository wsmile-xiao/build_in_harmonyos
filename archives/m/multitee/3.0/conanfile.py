#!/usr/bin/env python3
"""Conan recipe for multitee 3.0 - send multiple inputs to multiple outputs.

multitee (Daniel J. Bernstein, 1991, public domain) copies every input file
descriptor to any number of output descriptors; `multitee 0-1,4,5 4>a 5>b`
behaves like `tee a b` with better blocking behaviour.  It is built on the
author's sigsched library (a select()-driven non-preemptive scheduler) and
produces a single executable, bin/multitee, linked only against libc.

Porting notes (details and evidence in notes.md):
  * the 1991 release ships no Makefile: patch 0001 adds minimal make rules
    that take the compiler and every flag from the environment written by
    the Conan AutotoolsToolchain (R33);
  * sigdfl.c/sigsched.c use the 4.2BSD sigvec()/sigblock()/sigsetmask() API,
    which musl libc (OHOS) does not provide: patches 0004/0005 port them to
    POSIX sigaction()/sigprocmask()/sigset_t;
  * patches 0002/0003 replace pre-ANSI implicit and K&R libc declarations
    with the standard headers (correct prototypes on LP64 aarch64).
No platform macro is introduced.  The bundled tee.c clone is not built
(Debian does not ship it either): a packaged `tee` would shadow the system
tee on PATH.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    chdir,
    copy,
    export_conandata_patches,
    get,
    load,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MultiteeConan(ConanFile):
    name = "multitee"
    version = "3.0"
    description = "Send multiple inputs to multiple outputs (multi-descriptor tee)"
    license = "Public-Domain"
    homepage = "https://salsa.debian.org/debian/multitee"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("tee", "file-descriptor", "pipe", "command-line")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # plain C program
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        # R32: POSIX signals + select(); Linux and OHOS only
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} needs a POSIX target (Linux/OHOS)")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        AutotoolsToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # patch 0001 puts the Makefile in the source tree; -j1 avoids the
        # HMDFS jobserver EPERM on the OHOS worker (E074)
        with chdir(self, self.source_folder):
            Autotools(self).make(target="multitee", args=["-j1"])

    def package(self):
        copy(self, "multitee", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "multitee.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        # upstream has no licence file: the public-domain dedication is the
        # header comment of multitee.c
        header = load(self, os.path.join(self.source_folder, "multitee.c"))
        save(self, os.path.join(self.package_folder, "licenses", "LICENSE"),
             header.split("*/", 1)[0] + "*/\n")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
