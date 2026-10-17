#!/usr/bin/env python3
"""test_package for pd-log — loads every packaged Pd external natively.

The test compiles a small C program against the target toolchain and then runs
it on the target: it dlopen()s each packaged *.pd_linux exactly the way Pure
Data does and resolves the externals' "<name>_setup" entry point, after
checking each file is an ELF64 object for the expected machine.  Because the
externals import every Pd symbol from the hosting process, the program
defines the Pd API they need and is linked with -rdynamic so the loader can
bind those imports — the same contract the real pd binary honours.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException

# ELF e_machine values, see <elf.h>.
ELF_MACHINE = {"armv8": "183", "aarch64": "183", "x86_64": "62"}


class PdLogTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Pure Data is what actually loads these externals; requiring it here
        # also proves the dependency resolves for consumers of pd-log.
        self.requires("puredata/0.54.1")

    def _c_compiler(self):
        conf_cc = self.conf.get("tools.build:compiler_executables", default={})
        cc = conf_cc.get("c", "") if isinstance(conf_cc, dict) else ""
        if not cc or not os.path.isfile(cc) or not os.access(cc, os.X_OK):
            cc = (shutil.which("aarch64-unknown-linux-ohos-clang")
                  or shutil.which("clang") or shutil.which("gcc"))
        if not cc:
            raise ConanException("no usable C compiler found for pd-log tests")
        return cc

    def build(self):
        cc = self._c_compiler()
        # OHOS uses musl, where dlopen() lives in libc; glibc still needs -ldl.
        ldflags = "" if str(self.settings.os) == "OHOS" else " -ldl"
        # -rdynamic publishes the Pd host stubs defined in pdlog_dlopen_test.c
        # through the process-global symbol table, the same way the pd binary
        # exports its API.  OHOS musl binds every relocation of a dlopen()ed
        # object eagerly, so without these exports a load of a perfectly
        # correct external fails with "Error relocating ...: gensym: symbol
        # not found" (CI build #73602).
        self.run(
            f'{cc} pdlog_dlopen_test.c -rdynamic -o pdlog_dlopen_test{ldflags}',
            cwd=self.source_folder)

    def test(self):
        shell = os.environ.get("CONFIG_SHELL", "bash")
        pkg = self.dependencies[self.tested_reference_str].package_folder
        machine = ELF_MACHINE.get(str(self.settings.arch), "")
        self.run(
            f'CONAN_PD_LOG_FOLDER="{pkg}" PDLOG_EXPECT_MACHINE="{machine}" '
            f'{shell} test.sh',
            cwd=self.source_folder,
        )
