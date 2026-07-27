#!/usr/bin/env python3
"""Conan recipe for libgcrypt 1.12.2."""

import configparser
import os
import shlex
import subprocess

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibgcryptConan(ConanFile):
    name = "libgcrypt"
    version = "1.12.2"
    description = "General-purpose cryptographic library from the GnuPG project"
    license = "LGPL-2.1-or-later AND GPL-2.0-or-later"
    homepage = "https://gnupg.org/software/libgcrypt/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {
        "shared": True,
        "fPIC": True,
        "libgpg-error/*:shared": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires(
            "libgpg-error/1.55",
            transitive_headers=True,
            transitive_libs=True,
        )

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            source_map = "{}=.".format(self.source_folder)
            tc.extra_cflags.extend(
                [
                    "-ffile-prefix-map={}".format(source_map),
                    "-fdebug-prefix-map={}".format(source_map),
                    "-fmacro-prefix-map={}".format(source_map),
                ]
            )
        tc.configure_args.extend(
            [
                "--disable-asm",
                "--disable-doc",
                "--disable-silent-rules",
                "--with-libgpg-error-prefix={}".format(
                    self.dependencies["libgpg-error"].package_folder
                ),
            ]
        )
        tc.generate()

    def _dependency_environment(self):
        dep = self.dependencies["libgpg-error"]
        env = Environment()
        if self.settings.os == "OHOS":
            shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            gpgrt_config = os.path.join(dep.package_folder, "bin", "gpgrt-config")
            env.define("ac_cv_path_GPGRT_CONFIG", "no")
            env.define(
                "GPG_ERROR_CONFIG",
                "{} {} gpg-error".format(shell, gpgrt_config),
            )
        env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
        env.prepend_path(
            "PKG_CONFIG_PATH", os.path.join(dep.package_folder, "lib", "pkgconfig")
        )
        env.append("CPPFLAGS", "-I{}".format(dep.cpp_info.includedirs[0]))
        env.append("LDFLAGS", "-L{}".format(dep.cpp_info.libdirs[0]))
        return env

    def _make_args(self):
        if self.settings.os == "OHOS":
            return ["SHELL=/system/bin/sh"]
        return []

    def _configure(self, autotools):
        if self.settings.os != "OHOS":
            autotools.configure()
            return

        config = configparser.RawConfigParser()
        config.read(os.path.join(self.generators_folder, "conanbuild.conf"))
        configure_args = config.get("toolchain", "configure_args")
        configure = os.path.join(self.source_folder, "configure")
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        pwd_env = Environment()
        pwd_env.define("PWD", self.build_folder)
        with pwd_env.vars(self).apply():
            self.run(
                "{} {} {}".format(
                    shlex.quote(shell), shlex.quote(configure), configure_args
                ),
                env="conanbuild",
            )

    def build(self):
        apply_conandata_patches(self)
        self._prepare_shipped_configure()
        autotools = Autotools(self)
        with self._dependency_environment().vars(self).apply():
            self._configure(autotools)
            if self.settings.os == "OHOS":
                replace_in_file(
                    self,
                    os.path.join(self.build_folder, "libtool"),
                    'hardcode_libdir_flag_spec="\\$wl-rpath \\$wl\\$libdir"',
                    'hardcode_libdir_flag_spec=""',
                )

            # Jitterentropy must be compiled without optimization. Building
            # these objects first mirrors the official Homebrew formula while
            # preserving the entropy source for the full build.
            self.run(
                "make -C random CFLAGS=-O0 {} rndjent.o rndjent.lo".format(
                    " ".join(self._make_args())
                ),
                env="conanbuild",
            )
            autotools.make(args=self._make_args())
            check_args = ["check"] + self._make_args()
            if self.settings.os == "OHOS":
                wrapper = os.path.join(
                    self.source_folder, "tests", "ohos-test-wrapper.sh"
                )
                dep_libdir = self.dependencies["libgpg-error"].cpp_info.libdirs[0]
                test_environment = (
                    "LD_LIBRARY_PATH={}:{} GCRYPT_IN_REGRESSION_TEST=1 "
                    "/system/bin/sh {}".format(
                        shlex.quote(os.path.join(self.build_folder, "src", ".libs")),
                        shlex.quote(dep_libdir),
                        shlex.quote(wrapper),
                    )
                )
                check_args.append(
                    "TESTS_ENVIRONMENT={}".format(shlex.quote(test_environment))
                )
            autotools.make(args=check_args)

    def _prepare_shipped_configure(self):
        configure = os.path.join(self.source_folder, "configure")
        # The release tarball ships configure and CI does not regenerate it.
        # Keep configure.ac authoritative, then mirror only the exact generated
        # values required by the published dependency and HMDFS.
        replace_in_file(
            self,
            configure,
            "NEED_GPG_ERROR_VERSION=1.56",
            "NEED_GPG_ERROR_VERSION=1.55",
        )
        if self.settings.os == "OHOS":
            replace_in_file(
                self,
                configure,
                'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
                'tmp=`(umask 022 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
            )
            replace_in_file(
                self,
                configure,
                '(umask 077 && mkdir "$tmp")',
                '(umask 022 && mkdir "$tmp")',
            )

    def package(self):
        with self._dependency_environment().vars(self).apply():
            Autotools(self).install(args=self._make_args())
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        if self.settings.os == "OHOS":
            self._postprocess_ohos_elfs()

    def _postprocess_ohos_elfs(self):
        tools = {
            "patchelf": "/data/service/hnp/bin/patchelf",
            "objcopy": "/data/service/hnp/bin/llvm-objcopy",
            "signer": "/data/service/hnp/bin/binary-sign-tool",
        }
        for name, path in tools.items():
            if not os.path.isfile(path):
                raise RuntimeError("Required OHOS {} tool is missing: {}".format(name, path))

        for root, _, files in os.walk(self.package_folder):
            for filename in files:
                path = os.path.join(root, filename)
                with open(path, "rb") as stream:
                    if stream.read(4) != b"\x7fELF":
                        continue
                subprocess.run(
                    [tools["patchelf"], "--remove-rpath", path], check=True
                )
                subprocess.run(
                    [tools["objcopy"], "--remove-section", ".codesign", path],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                subprocess.run(
                    [
                        tools["signer"],
                        "sign",
                        "-inFile",
                        path,
                        "-outFile",
                        path,
                        "-selfSign",
                        "1",
                    ],
                    check=True,
                )

    def package_info(self):
        self.cpp_info.libs = ["gcrypt"]
        self.cpp_info.requires = ["libgpg-error::libgpg-error"]
        self.cpp_info.set_property("cmake_file_name", "libgcrypt")
        self.cpp_info.set_property("cmake_target_name", "libgcrypt::libgcrypt")
        self.cpp_info.set_property("pkg_config_name", "libgcrypt")
