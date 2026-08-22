import os
import shutil

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class GnuPrologConan(ConanFile):
    name = "gnu-prolog"
    version = "1.5.0"
    package_type = "application"
    description = "GNU Prolog compiler and runtime"
    license = "GPL-2.0-or-later"
    homepage = "https://gprolog.org/"
    url = "https://gprolog.org/"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os != "OHOS":
            from conan.errors import ConanInvalidConfiguration
            raise ConanInvalidConfiguration("gnu-prolog recipe targets OHOS")
        if self.settings.arch != "armv8":
            from conan.errors import ConanInvalidConfiguration
            raise ConanInvalidConfiguration("gnu-prolog recipe targets OHOS armv8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        src = os.path.join(self.source_folder, "src")
        stage = os.path.join(self.build_folder, "stage")
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(stage, exist_ok=True)
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

        configure = os.path.join(src, "configure")
        with open(configure, encoding="utf-8") as handle:
            content = handle.read()
        content = content.replace("/tmp/version_no.tex", "./version_no.tex")
        content = content.replace("/tmp/copyright.tex", "./copyright.tex")
        content = content.replace("umask 077", "umask 000")
        content = content.replace(
            "diff /tmp/version_no.tex ../doc/version_no.tex",
            "diff -b ./version_no.tex ../doc/version_no.tex",
        )
        content = content.replace(
            "diff /tmp/copyright.tex ../doc/copyright.tex",
            "diff -b ./copyright.tex ../doc/copyright.tex",
        )
        with open(configure, "w", encoding="utf-8") as handle:
            handle.write(content)

        check_boot = os.path.join(src, "Pl2Wam", "check_boot")
        with open(check_boot, encoding="utf-8") as handle:
            content = handle.read()
        content = content.replace(
            "diff --ignore-space-change -I '^%' -I '^file_name[(]' $1 $2 || \\\n\t( echo \"difference encountered: $1 <> $2\"; exit 1 )",
            "t1=\"${TMPDIR:-.}/gprolog-diff-$$.a\"; t2=\"${TMPDIR:-.}/gprolog-diff-$$.b\"; "
            "sed -e '/^%/d' -e '/^file_name[(]/d' \"$1\" > \"$t1\" && "
            "sed -e '/^%/d' -e '/^file_name[(]/d' \"$2\" > \"$t2\" && "
            "diff -b \"$t1\" \"$t2\"; r=$?; rm -f \"$t1\" \"$t2\"; "
            "test $r -eq 0 || ( echo \"difference encountered: $1 <> $2\"; exit 1 )",
        )
        content = content.replace("/tmp/make.log", "make.log")
        with open(check_boot, "w", encoding="utf-8") as handle:
            handle.write(content)

        args = [
            f"--build=aarch64-unknown-linux-gnu",
            f"--with-install-dir={stage}",
            "--without-links-dir",
            "--without-doc-dir",
            "--without-html-dir",
            "--without-examples-dir",
            "--disable-linedit",
            "--disable-sockets",
        ]
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        assembler = compiler_executables.get("as") or shutil.which("as") or "as"
        command = f'AS="{assembler}" ./configure ' + " ".join(
            f'"{arg}"' for arg in args
        )
        self.run(command, cwd=src)
        self.run("make -j1", cwd=src)
        self.run("make check", cwd=src)
        self.run("make install", cwd=src)

    def package(self):
        copy(self, "*", os.path.join(self.build_folder, "stage"), self.package_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
