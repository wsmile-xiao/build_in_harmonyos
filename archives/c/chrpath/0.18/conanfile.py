#!/usr/bin/env python3
"""Conan recipe for chrpath 0.18."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ChrpathConan(ConanFile):
    name = "chrpath"
    version = "0.18"
    description = "Tool to edit the rpath in ELF binaries"
    license = "GPL-2.0-or-later"
    homepage = "https://codeberg.org/pere/chrpath"
    url = "https://deb.debian.org/debian/pool/main/c/chrpath/chrpath_0.18.orig.tar.gz"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"chrpath {self.version} supports Linux and OHOS only"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            toolchain.extra_ldflags.append("-fuse-ld=lld")
        toolchain.generate()

    def _compiler_executable(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return str(executables.get("c") or "cc")

    @staticmethod
    def _quote(value):
        if os.name == "nt":
            return str(value)
        return shlex.quote(str(value))

    def _ohos_target_args(self):
        if str(self.settings.os) != "OHOS":
            return []
        args = ["--target=aarch64-linux-ohos"]
        sysroot = self.conf.get("tools.build:sysroot", default=None)
        if sysroot:
            args.append("--sysroot=" + str(sysroot))
        return args

    def _ohos_cflags(self):
        if str(self.settings.os) != "OHOS":
            return []
        return [str(flag) for flag in self.conf.get("tools.build:cflags", default=[])]

    def _direct_build(self):
        """Build the small utility without generated Autotools files."""
        compiler = self._compiler_executable()
        compiler_arg = self._quote(compiler)
        target_args = self._ohos_target_args()
        cflags_extra = self._ohos_cflags()
        link_args = ""
        if str(self.settings.os) == "OHOS":
            link_args = "-fuse-ld=lld"

        source_dir = self.source_folder
        build_dir = self.build_folder
        test_dir = os.path.join(build_dir, "testsuite")
        os.makedirs(test_dir, exist_ok=True)

        with open(os.path.join(build_dir, "config.h"), "w", encoding="ascii", newline="\n") as handle:
            handle.write(
                '#define PACKAGE "chrpath"\n'
                '#define VERSION "0.18"\n'
                '#define HAVE_FCNTL_H 1\n'
                '#define HAVE_GETOPT_H 1\n'
                '#define HAVE_LINK_H 1\n'
                '#define HAVE_UNISTD_H 1\n'
                '#define SIZEOF_VOID_P 8\n'
                '#define bswap_16 __builtin_bswap16\n'
                '#define bswap_32 __builtin_bswap32\n'
                '#define bswap_64 __builtin_bswap64\n'
            )

        cflags = " ".join([
            "-DHAVE_CONFIG_H",
            "-O2",
            "-W",
            "-Wall",
            "-Wcast-align",
            "-Wcast-qual",
            "-Wcomments",
            "-Wmissing-declarations",
            "-Wmissing-prototypes",
            "-Wpointer-arith",
            "-Wreturn-type",
            "-Wstrict-prototypes",
            "-I" + self._quote(build_dir),
        ] + cflags_extra)
        target_arg_string = " ".join(self._quote(arg) for arg in target_args)
        objects = []
        for source in ("chrpath.c", "killrpath.c", "main.c", "elf.c"):
            src_arg = self._quote(os.path.join(source_dir, source))
            obj_path = os.path.join(build_dir, source[:-2] + ".o")
            obj_arg = self._quote(obj_path)
            self.run(
                f"{compiler_arg} {target_arg_string} {cflags} -c {src_arg} -o {obj_arg}",
                cwd=source_dir,
            )
            objects.append(obj_arg)

        binary = os.path.join(build_dir, "chrpath")
        self.run(
            f"{compiler_arg} {target_arg_string} {link_args} -o {self._quote(binary)} "
            f"{' '.join(objects)}",
            cwd=source_dir,
        )

        shutil.copy2(os.path.join(source_dir, "testsuite", "prog.c"), test_dir)
        shutil.copy2(os.path.join(source_dir, "testsuite", "runtest.sh"), test_dir)
        with open(os.path.join(test_dir, "Makefile"), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "CC = " + compiler + "\n"
                "CFLAGS = " + target_arg_string + "\n"
                "LDFLAGS = " + link_args + "\n"
                "RPATH = -Wl,-rpath,/usr/local/lib\n"
                "prog: prog.c\n"
                "\t$(CC) $(CFLAGS) $(LDFLAGS) $(RPATH) -o $@ $<\n"
                "check: prog\n"
                "\tsh runtest.sh\n"
            )

    def _run_upstream_tests(self, cwd):
        if can_run(self):
            self.run("make -j1 check", cwd=cwd)
        else:
            self.output.info("cross: upstream chrpath tests deferred to a runnable target")

    def build(self):
        apply_conandata_patches(self)

        # The release archive contains Autotools input but not generated
        # configure files.  The direct path also avoids worker-side Automake
        # availability becoming a false source failure on OHOS.
        autotools_available = all(
            shutil.which(tool) is not None
            for tool in ("autoconf", "automake", "aclocal")
        )
        if str(self.settings.os) == "OHOS" or not autotools_available:
            self._direct_build()
            self._run_upstream_tests(os.path.join(self.build_folder, "testsuite"))
            return

        self.run("autoreconf -fi", cwd=self.source_folder)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        self._run_upstream_tests(self.build_folder)

    def package(self):
        if os.path.isfile(os.path.join(self.source_folder, "config.status")):
            Autotools(self).install()
        else:
            copy(
                self,
                "chrpath",
                dst=os.path.join(self.package_folder, "bin"),
                src=self.build_folder,
            )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
