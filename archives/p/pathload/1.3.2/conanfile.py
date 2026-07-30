#!/usr/bin/env python3
"""Conan recipe for pathload 1.3.2.

pathload is a command-line tool for end-to-end available-bandwidth
measurement. The upstream release uses an old autoconf/make build.
"""

import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import chdir, copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PathloadConan(ConanFile):
    name = "pathload"
    version = "1.3.2"
    description = "End-to-end available bandwidth estimation tool"
    license = "GPL-2.0-or-later"
    homepage = "https://www.cc.gatech.edu/~dovrolis/bw-est/pathload.html"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._replace_source_text(
            "configure",
            [("main(){return(0);}", "int main(void){return(0);}")],
        )
        self._replace_source_text(
            "makefile.in",
            [
                ("all:${TARGETS} clean", "all:${TARGETS}"),
                (
                    "\t $(CC) $(SOBJS) -o pathload_snd $(LIBS) $(LDFLAGS) $(CFLAGS)",
                    "\t $(CC) $(CFLAGS) $(LDFLAGS) $(SOBJS) -o pathload_snd $(LIBS)",
                ),
                (
                    "\t $(CC) $(ROBJS) -o pathload_rcv $(LIBS) $(LDFLAGS) $(CFLAGS)",
                    "\t $(CC) $(CFLAGS) $(LDFLAGS) $(ROBJS) -o pathload_rcv $(LIBS)",
                ),
            ],
        )
        self._replace_source_text(
            "pathload_rcv.c",
            [("int main(l_int32 argc, char *argv[])", "int main(int argc, char *argv[])")],
        )
        self._replace_source_text(
            "pathload_rcv.h",
            [
                ("EXTERN void sig_alrm();", "EXTERN void sig_alrm(int unused);"),
                ("EXTERN void sig_sigusr1() ;", "EXTERN void sig_sigusr1(int unused) ;"),
            ],
        )
        self._replace_source_text(
            "pathload_rcv_func.c",
            [
                (
                    "void sig_sigusr1()\n{\n  return;",
                    "void sig_sigusr1(int unused)\n{\n  (void)unused;\n  return;",
                ),
                (
                    "void sig_alrm()\n{\n  terminate_gracefully(exp_start_time);",
                    "void sig_alrm(int unused)\n{\n  (void)unused;\n  terminate_gracefully(exp_start_time);",
                ),
            ],
        )

    def _replace_source_text(self, relative_path, replacements):
        file_path = os.path.join(self.source_folder, relative_path)
        with open(file_path, "r", encoding="latin-1", newline="") as source_file:
            content = source_file.read()

        for old, new in replacements:
            if old not in content:
                raise ConanException(f"expected text not found in {relative_path!r}: {old!r}")
            content = content.replace(old, new, 1)

        with open(file_path, "w", encoding="latin-1", newline="") as source_file:
            source_file.write(content)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        with chdir(self, self.source_folder):
            configure_args = []
            if str(self.settings.os) == "OHOS":
                host_triplet = "x86_64-unknown-linux-gnu"
                if str(self.settings.arch) == "armv8":
                    host_triplet = "arm-unknown-linux-gnu"
                configure_args = [f"--build={host_triplet}", f"--host={host_triplet}"]
            autotools.configure(args=configure_args)
            autotools.make(args=["-j1"])

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "CHANGELOG", self.source_folder, os.path.join(self.package_folder, "share", "doc", "pathload"), keep_path=False)
        copy(self, "CHANGES", self.source_folder, os.path.join(self.package_folder, "share", "doc", "pathload"), keep_path=False)
        copy(self, "README", self.source_folder, os.path.join(self.package_folder, "share", "doc", "pathload"), keep_path=False)
        copy(self, "pathload_rcv", self.source_folder, os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "pathload_snd", self.source_folder, os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
