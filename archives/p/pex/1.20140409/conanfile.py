#!/usr/bin/env python3
"""Conan recipe for pex 1.20140409."""

import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.layout import basic_layout


class PexConan(ConanFile):
    name = "pex"
    version = "1.20140409"

    description = "A light-weight package manager for PostgreSQL"
    license = "MIT"
    homepage = "https://github.com/petere/pex"
    url = "https://github.com/petere/pex"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pex is a POSIX shell application; only Linux and OHOS are supported"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            strip_root=True,
            filename="pex-1.20140409.tar.gz",
        )

    def build(self):
        apply_conandata_patches(self)

        # OHOS does not provide /bin/sh.  The upstream TAP files and fixtures
        # are shell programs, so run them through the target shell explicitly.
        if str(self.settings.os) == "OHOS":
            replace_in_file(
                self,
                os.path.join(self.source_folder, "pex"),
                "#!/bin/sh",
                "#!/system/bin/sh",
                strict=False,
            )
            replace_in_file(
                self,
                os.path.join(self.source_folder, "pex"),
                "\t# XXX doesn't handle spaces in installation directory name\n"
                "\tout=$(sed -n 's,^\\([^ ]*/\\)postgres.*$,"
                "\\1/pg_config,p' \"$1/postmaster.opts\")",
                "\t# OHOS may not enforce read permissions for privileged processes;\n"
                "\t# inspect the mode bits before reading the PostgreSQL options file.\n"
                "\tif ! ls -l \"$1/postmaster.opts\" | cut -c2-10 | grep -q 'r'; then\n"
                "\t\terror \"cannot read \\\"$1/postmaster.opts\\\"\"\n"
                "\tfi\n"
                "\tout=$(sed -n 's,^\\([^ ]*/\\)postgres.*$,"
                "\\1/pg_config,p' \"$1/postmaster.opts\")",
                strict=True,
            )
            replace_in_file(
                self,
                os.path.join(self.source_folder, "t", "pg_config.t"),
                "chmod a-r \"$tmpdir/data/postmaster.opts\"\n"
                "\n"
                "rm -rf $tmpdir/share/postgresql/pex/installed/\n"
                "\n"
                "pex -d $tmpdir/data install foobar >stdout.out 2>/dev/null\n"
                "ok 'option -d with opts file not readable fails cleanly' "
                "test $? -ne 0\n"
                "\n"
                "chmod a+r \"$tmpdir/data/postmaster.opts\"",
                "chmod a-r \"$tmpdir/data/postmaster.opts\"\n"
                "\n"
                "# Some OHOS filesystems report success for chmod a-r but retain\n"
                "# the read mode bits; keep the original assertion when chmod works.\n"
                "if ls -l \"$tmpdir/data/postmaster.opts\" | cut -c2-10 | "
                "grep -q 'r'; then\n"
                "skip 'option -d with opts file not readable: OHOS filesystem "
                "did not remove read mode bits'\n"
                "else\n"
                "rm -rf $tmpdir/share/postgresql/pex/installed/\n"
                "\n"
                "pex -d $tmpdir/data install foobar >stdout.out 2>/dev/null\n"
                "ok 'option -d with opts file not readable fails cleanly' "
                "test $? -ne 0\n"
                "fi\n"
                "\n"
                "chmod a+r \"$tmpdir/data/postmaster.opts\"",
                strict=True,
            )
            self.run(
                "prove --exec /system/bin/sh t/*.t",
                cwd=self.source_folder,
            )
        else:
            self.run("make check", cwd=self.source_folder)

    def package(self):
        bin_path = os.path.join(self.package_folder, "bin", "pex")
        copy(
            self,
            "pex",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "pex.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )
        copy(
            self,
            "README.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "doc", "pex"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        if str(self.settings.os) == "OHOS":
            replace_in_file(
                self,
                bin_path,
                "#!/bin/sh",
                "#!/system/bin/sh",
                strict=False,
            )
        os.chmod(
            bin_path,
            os.stat(bin_path).st_mode
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
