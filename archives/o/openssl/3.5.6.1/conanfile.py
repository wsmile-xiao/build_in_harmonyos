#!/usr/bin/env python3
"""Conan recipe for the OpenSSL 3.5.6 OHOS adaptation revision."""

import os
from io import StringIO

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
    rmdir,
)
from conan.tools.layout import basic_layout


class OpensslConan(ConanFile):
    name = "openssl"
    version = "3.5.6.1"
    description = "TLS/SSL and cryptographic library"
    license = "Apache-2.0"
    homepage = "https://www.openssl.org/"
    url = "https://github.com/openssl/openssl"
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OpenSSL supports Linux and OHOS targets, got {self.settings.os}"
            )

    def validate(self):
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"OpenSSL supports OHOS armv8, got {self.settings.arch}"
            )

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    @staticmethod
    def _posix(path):
        return str(path).replace("\\", "/")

    @classmethod
    def _msys_path(cls, path):
        path = cls._posix(path)
        if len(path) > 2 and path[1] == ":":
            return f"/{path[0].lower()}{path[2:]}"
        return path

    def _tool(self, executables, key, default_name):
        configured = executables.get(key)
        if configured:
            return self._posix(configured)

        compiler = executables.get("c") or ""
        bindir = os.path.dirname(compiler)
        suffix = ".exe" if compiler.lower().endswith(".exe") else ""
        candidate = os.path.join(bindir, default_name + suffix) if bindir else ""
        if candidate and os.path.isfile(candidate):
            return self._posix(candidate)
        if str(self.settings_build.os) == "Windows":
            raise ConanInvalidConfiguration(
                f"Missing {default_name} beside the configured OHOS compiler"
            )
        return default_name

    def _tool_command(self, executables, key, default_name):
        tool = self._tool(executables, key, default_name)
        if str(self.settings_build.os) == "Windows":
            return f'"{tool}"'
        return tool

    def _perl(self):
        output = StringIO()
        self.run('perl -e "print join chr(10), @INC"', stdout=output)
        include_paths = [
            line.strip() for line in output.getvalue().splitlines()
            if line.strip()
        ]
        if not include_paths:
            raise ConanInvalidConfiguration(
                "OpenSSL could not resolve the Perl module search path"
            )
        if str(self.settings_build.os) != "Windows":
            output = StringIO()
            self.run("command -v perl", stdout=output)
            perl = output.getvalue().strip()
            if not perl:
                raise ConanInvalidConfiguration(
                    "OpenSSL requires Perl in the build environment"
                )
            include_args = [
                "-I" + self._posix(path).replace(" ", "\\ ")
                for path in include_paths
            ]
            perl_command = " ".join([self._posix(perl)] + include_args)
            return perl_command, perl_command

        output = StringIO()
        self.run("where.exe perl", stdout=output)
        perl = next(
            (line.strip() for line in output.getvalue().splitlines()
             if line.strip()),
            "",
        )
        if not perl:
            raise ConanInvalidConfiguration(
                "OpenSSL requires Perl in the Windows build environment"
            )

        configure_include_args = " ".join(
            f'-I"{path}"' for path in include_paths
        )
        configure_perl = " ".join(
            item for item in (
                f'"{self._posix(perl)}"', configure_include_args
            ) if item
        )
        make_include_args = " ".join(
            f"'-I{self._msys_path(path)}'" for path in include_paths
        )
        # Recursive OpenSSL rules run under /usr/bin/sh. A .cmd wrapper works
        # for Configure under cmd.exe but is not executable from that shell.
        make_perl = " ".join(
            item for item in ("perl", make_include_args) if item
        )
        return configure_perl, make_perl

    def _make(self):
        output = StringIO()
        if str(self.settings_build.os) == "Windows":
            self.run("where.exe make", stdout=output)
        else:
            self.run("command -v make", stdout=output)
        paths = [line.strip() for line in output.getvalue().splitlines()]
        make = next((path for path in paths if path), "")
        if not make:
            raise ConanInvalidConfiguration(
                "OpenSSL requires GNU Make in the build environment"
            )
        return self._posix(make), self._msys_path(make)

    def _prepare_ohos_sources(self):
        if self.settings.os != "OHOS":
            return

        makefile_template = os.path.join(
            self.source_folder, "Configurations", "unix-Makefile.tmpl"
        )
        replace_in_file(
            self,
            makefile_template,
            "my $max_per_call = 500;",
            "my $max_per_call = 100;",
        )

        build_info = os.path.join(self.source_folder, "crypto", "build.info")
        replace_in_file(
            self,
            build_info,
            'GENERATE[buildinf.h]=../util/mkbuildinf.pl "$(CC) '
            '$(LIB_CFLAGS) $(CPPFLAGS_Q)" "$(PLATFORM)"',
            'GENERATE[buildinf.h]=../util/mkbuildinf.pl "clang '
            '--target=aarch64-linux-ohos $(LIB_CFLAGS) $(CPPFLAGS_Q)" '
            '"$(PLATFORM)"',
        )

    def _build_environment(self):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        compiler = executables.get("c") or ""
        if not compiler:
            raise ConanInvalidConfiguration(
                "OpenSSL requires tools.build:compiler_executables['c']"
            )

        compiler_command = self._posix(compiler)
        if str(self.settings_build.os) == "Windows":
            llvm_root = os.path.dirname(os.path.dirname(compiler))
            sdk_native = os.path.dirname(llvm_root)
            sysroot = os.path.join(sdk_native, "sysroot")
            if not os.path.isdir(sysroot):
                raise ConanInvalidConfiguration(
                    "Windows-to-OHOS OpenSSL build requires native/sysroot "
                    "beside the configured SDK compiler"
                )
            compiler_command = (
                '"{}" --target=aarch64-linux-ohos '
                '--sysroot="{}" -D__MUSL__'.format(
                    self._posix(compiler), self._posix(sysroot)
                )
            )

        env = Environment()
        env.define("CC", compiler_command)
        env.define("AR", self._tool_command(executables, "ar", "llvm-ar"))
        env.define(
            "RANLIB",
            self._tool_command(executables, "ranlib", "llvm-ranlib"),
        )
        env.define("NM", self._tool_command(executables, "nm", "llvm-nm"))
        if str(self.settings_build.os) == "Windows":
            env.define(
                "MSYS2_ARG_CONV_EXCL",
                "--prefix=;--openssldir=;--libdir=;-DOPENSSLDIR=;"
                "-DENGINESDIR=;-DMODULESDIR=",
            )
        return env

    def build(self):
        self._prepare_ohos_sources()
        configure_perl, make_perl = self._perl()
        make, recursive_make = self._make()
        configure_args = [
            f"{configure_perl} ./Configure",
            "linux-aarch64",
            '--prefix="/"',
            '--openssldir="/ssl"',
            "--libdir=/lib",
            "--with-rand-seed=getrandom",
            "no-asm",
            "no-shared",
            "no-legacy",
            "no-module",
            "no-docs",
        ]
        if self.options.fPIC:
            configure_args.append("-fPIC")

        with self._build_environment().vars(self).apply():
            self.run(" ".join(configure_args), cwd=self.source_folder)
            self.run(
                f'"{make}" MAKE="{recursive_make}" PERL="{make_perl}" '
                "-j1 build_sw build_tests",
                cwd=self.source_folder,
            )
            if can_run(self):
                self.run(
                    f'"{make}" MAKE="{recursive_make}" PERL="{make_perl}" '
                    "test HARNESS_JOBS=1",
                    cwd=self.source_folder,
                )
            else:
                self.output.info(
                    "cross-building: upstream test programs compiled but cannot run"
                )

    def package(self):
        destdir = self._posix(self.package_folder)
        _, make_perl = self._perl()
        make, recursive_make = self._make()
        with self._build_environment().vars(self).apply():
            self.run(
                f'"{make}" MAKE="{recursive_make}" PERL="{make_perl}" '
                f'install_sw DESTDIR="{destdir}"',
                cwd=self.source_folder,
            )
        # Conan supplies consumer metadata. Removing upstream metadata avoids
        # target-root prefixes, and the module cleanup protects reused package
        # folders from stale provider DSOs produced by an earlier build.
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "ossl-modules"))
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        crypto = self.cpp_info.components["crypto"]
        crypto.libs = ["crypto"]
        crypto.system_libs = ["dl", "pthread"]
        crypto.set_property("cmake_target_name", "OpenSSL::Crypto")

        ssl = self.cpp_info.components["ssl"]
        ssl.libs = ["ssl"]
        ssl.requires = ["crypto"]
        ssl.set_property("cmake_target_name", "OpenSSL::SSL")

        self.cpp_info.set_property("cmake_file_name", "OpenSSL")
        self.cpp_info.set_property("pkg_config_name", "openssl")
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
