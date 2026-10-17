#!/usr/bin/env python3
"""Conan recipe for ctpv 1.1, a terminal file previewer."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class CtpvConan(ConanFile):
    name = "ctpv"
    version = "1.1"
    description = "File previewer for a terminal"
    license = "MIT"
    homepage = "https://github.com/NikitaIvanovV/ctpv"
    url = "https://github.com/NikitaIvanovV/ctpv"
    topics = ("terminal", "file-preview", "file-manager")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("libmagic/5.48")
        self.requires("openssl/3.5.6.1")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ctpv supports Linux and OHOS POSIX environments"
            )

    def layout(self):
        basic_layout(self, src_folder=".")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True, verify=True)

    def build(self):
        apply_conandata_patches(self)

        target_cc = self._target_compiler()
        host_cc = self._host_compiler()
        cflags = self._compile_flags()
        ldflags = self._link_flags()

        self.run(
            "make -j1 CC={} HOSTCC={} CFLAGS={} LDFLAGS={}".format(
                shlex.quote(target_cc),
                shlex.quote(host_cc),
                shlex.quote(" ".join(cflags)),
                shlex.quote(" ".join(ldflags)),
            ),
            cwd=self.source_folder,
            env="conanbuild",
        )
        self.run(
            "make -j1 CC={} HOSTCC={} CFLAGS={} LDFLAGS={} quit/ctpvquit".format(
                shlex.quote(target_cc),
                shlex.quote(host_cc),
                shlex.quote(" ".join(cflags)),
                shlex.quote(" ".join(ldflags)),
            ),
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        license_dir = os.path.join(self.package_folder, "licenses")
        magic_dir = os.path.join(self.package_folder, "share", "misc")

        copy(self, "ctpv", src=self.source_folder, dst=bin_dir, keep_path=False)
        copy(
            self,
            "ctpvquit",
            src=os.path.join(self.source_folder, "quit"),
            dst=bin_dir,
            keep_path=False,
        )
        copy(self, "ctpvclear", src=self.source_folder, dst=bin_dir, keep_path=False)
        copy(
            self,
            "ctpv.1",
            src=os.path.join(self.source_folder, "doc"),
            dst=man_dir,
            keep_path=False,
        )
        copy(self, "LICENSE", src=self.source_folder, dst=license_dir, keep_path=False)

        magic_db = os.path.join(
            self.dependencies["libmagic"].package_folder,
            "share",
            "misc",
            "magic.mgc",
        )
        if not os.path.isfile(magic_db):
            raise ConanInvalidConfiguration(
                "libmagic package does not contain share/misc/magic.mgc"
            )
        copy(self, "magic.mgc", src=os.path.dirname(magic_db), dst=magic_dir)

        for command in ("ctpv", "ctpvquit", "ctpvclear"):
            os.chmod(os.path.join(bin_dir, command), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.define(
            "MAGIC", os.path.join(self.package_folder, "share", "misc", "magic.mgc")
        )

    def _target_compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("c")
        if compiler:
            return compiler
        return shutil.which("clang") or shutil.which("cc") or "cc"

    def _host_compiler(self):
        configured = os.environ.get("CC_FOR_BUILD")
        if configured:
            return configured
        if cross_building(self):
            raise ConanInvalidConfiguration(
                "CC_FOR_BUILD is required when cross-building ctpv's embed helper"
            )
        return shutil.which("cc") or shutil.which("clang") or "cc"

    def _compile_flags(self):
        flags = [
            "-fPIE",
            "-fstack-protector-strong",
            "-D_FORTIFY_SOURCE=2",
            "-Wall",
            "-Wextra",
        ]
        if str(self.settings.build_type) == "Debug":
            flags.extend(["-O0", "-g"])
        else:
            flags.append("-O2")

        for dependency in ("libmagic", "openssl"):
            for include_dir in self.dependencies[dependency].cpp_info.includedirs:
                flags.append("-I{}".format(include_dir))
        return flags

    def _link_flags(self):
        flags = ["-static-pie", "-Wl,-z,relro,-z,now"]
        for dependency in ("libmagic", "openssl"):
            for library_dir in self.dependencies[dependency].cpp_info.libdirs:
                flags.append("-L{}".format(library_dir))
        return flags
