#!/usr/bin/env python3
"""Conan recipe for apg (Automated Password Generator) 2.2.3.

apg is a command-line tool for generating random passwords.
Build system: Makefile (no configure script).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, save, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


# getpass() compatibility for HarmonyOS (musl libc lacks getpass())
GETPASS_COMPAT_C = """\
/*
 * getpass_compat.c - getpass() compatibility for HarmonyOS
 *
 * HarmonyOS musl libc does not provide getpass().
 * This implementation uses fgets + termios for secure password input.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <termios.h>

char *getpass(const char *prompt)
{
    static char buf[256];
    struct termios old_t, new_t;
    int tc_ok = 0;

    if (prompt != NULL) {
        fputs(prompt, stderr);
        fflush(stderr);
    }

    if (tcgetattr(STDIN_FILENO, &old_t) == 0) {
        new_t = old_t;
        new_t.c_lflag &= ~(ECHO);
        tcsetattr(STDIN_FILENO, TCSAFLUSH, &new_t);
        tc_ok = 1;
    }

    if (fgets(buf, sizeof(buf), stdin) == NULL) {
        if (tc_ok)
            tcsetattr(STDIN_FILENO, TCSANOW, &old_t);
        fputc('\\n', stderr);
        return NULL;
    }

    /* Remove trailing newline */
    size_t len = strlen(buf);
    if (len > 0 && buf[len - 1] == '\\n')
        buf[len - 1] = '\\0';

    if (tc_ok)
        tcsetattr(STDIN_FILENO, TCSANOW, &old_t);
    fputc('\\n', stderr);

    return buf;
}
"""


class ApgConan(ConanFile):
    name = "apg"
    version = "2.2.3"
    description = "Automated Password Generator - tool for generating random passwords"
    license = "BSD-style"
    homepage = "https://github.com/wilx/apg"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

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

        # Write getpass_compat.c into source tree (HarmonyOS lacks getpass())
        save(self, os.path.join(self.source_folder, "getpass_compat.c"), GETPASS_COMPAT_C)

        # R33: Get compiler from Conan conf, not shell env vars
        compiler_executables = self.conf.get("tools.build:compiler_executables", default={})
        if isinstance(compiler_executables, dict):
            cc = compiler_executables.get("c", "clang")
        else:
            cc = "clang"

        # R9: Use make -j1
        # Build standalone target (apg + apgbfm, no daemon)
        # Run from source folder since basic_layout sets build_folder separately
        self.run(f"make CC={cc} standalone -j1", cwd=self.source_folder)

    def package(self):
        # Copy binaries to bin/
        copy(self, "apg", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "apgbfm", self.source_folder, os.path.join(self.package_folder, "bin"))
        # Copy man pages
        copy(self, "*.1", os.path.join(self.source_folder, "doc", "man"),
             os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
