#!/usr/bin/env python3
"""Conan recipe for cpdb-libs 2.0-b5 using Autotools."""

import os
import shlex
import shutil
import sys
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
    rm,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class CpdbLibsConan(ConanFile):
    name = "cpdb-libs"
    version = "2.0-b5"
    description = "OpenPrinting Common Print Dialog Backends libraries"
    license = "MIT"
    homepage = "https://github.com/OpenPrinting/cpdb-libs"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.88.3", transitive_headers=True, transitive_libs=True)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "cpdb-libs supports Linux and HarmonyOS-compatible POSIX targets"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "The HarmonyOS package is validated for AArch64"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()

        glib_package = self.dependencies["glib"].package_folder
        gio_unix_pc = os.path.join(
            glib_package, "lib", "pkgconfig", "gio-unix-2.0.pc"
        )
        if not os.path.isfile(gio_unix_pc):
            raise ConanInvalidConfiguration(
                "glib/2.88.3 does not provide gio-unix-2.0.pc"
            )
        gio_unix_metadata = load(self, gio_unix_pc)
        if "prefix=/\n" not in gio_unix_metadata:
            raise ConanInvalidConfiguration(
                "glib/2.88.3 gio-unix-2.0.pc has an unexpected prefix"
            )
        gio_unix_metadata = gio_unix_metadata.replace(
            "prefix=/\n", "prefix={}\n".format(glib_package), 1
        )
        save(
            self,
            os.path.join(self.generators_folder, "gio-unix-2.0.pc"),
            gio_unix_metadata,
        )

        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.append("--disable-nls")
        if self.settings.os == "OHOS":
            toolchain.configure_args.extend(
                [
                    "--build=aarch64-unknown-linux-gnu",
                    "--host=aarch64-unknown-linux-gnu",
                ]
            )
        if self.options.shared:
            toolchain.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            toolchain.configure_args.extend(["--disable-shared", "--enable-static"])

        environment = toolchain.environment()
        environment.prepend_path("PATH", os.path.join(glib_package, "bin"))
        environment.define("ac_cv_func_malloc_0_nonnull", "yes")
        if self.settings.os == "OHOS":
            environment.define("CPDB_CONFIG_TMP_UMASK", "022")

            # The SDK copy of gdbus-codegen has a fixed /usr/bin/python3
            # shebang, but HarmonyOS provides the interpreter elsewhere. Do
            # not rely on PATH ordering: the profile prepends the SDK bin after
            # this environment is generated. Invoke the GLib package script
            # with the interpreter already running Conan, and discard the
            # target-library search path because this generator is pure Python.
            gdbus_codegen = os.path.join(glib_package, "bin", "gdbus-codegen")
            if not os.path.isfile(gdbus_codegen):
                raise ConanInvalidConfiguration(
                    "glib/2.88.3 does not provide gdbus-codegen"
                )
            python = os.path.realpath(sys.executable)
            if not python or not os.path.isfile(python):
                raise ConanInvalidConfiguration(
                    "A runnable Python 3 interpreter is required by gdbus-codegen"
                )
            environment.define(
                "GDBUS_CODEGEN",
                "LD_LIBRARY_PATH= {} {}".format(
                    shlex.quote(python),
                    shlex.quote(gdbus_codegen),
                ),
            )

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("c") or ""
        tool_directory = os.path.dirname(compiler)
        for variable, executable in (
            ("AR", "llvm-ar"),
            ("RANLIB", "llvm-ranlib"),
            ("NM", "llvm-nm"),
            ("STRIP", "llvm-strip"),
        ):
            tool = compilers.get(variable.lower()) or os.path.join(
                tool_directory, executable
            )
            if tool_directory and os.path.isfile(tool):
                environment.define(variable, tool)

        for dependency in self.dependencies.host.values():
            if not dependency.package_folder:
                continue
            for libdir in dependency.cpp_info.libdirs:
                path = libdir if os.path.isabs(libdir) else os.path.join(
                    dependency.package_folder, libdir
                )
                if os.path.isdir(path):
                    environment.prepend_path("LD_LIBRARY_PATH", path)
        toolchain.generate(environment)

    def build(self):
        apply_conandata_patches(self)
        generated_timestamp = time.time() + 1
        for relative_path in (
            "aclocal.m4",
            "configure",
            "Makefile.in",
            os.path.join("cpdb", "Makefile.in"),
            os.path.join("tools", "Makefile.in"),
        ):
            path = os.path.join(self.source_folder, relative_path)
            os.utime(path, (generated_timestamp, generated_timestamp))
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # Automake otherwise executes tools/run-tests.sh through its
        # /bin/bash shebang. HarmonyOS exposes bash through the build profile,
        # so pass that resolved shell as the test log compiler explicitly.
        test_shell = shutil.which("bash") or shutil.which("sh")
        if not test_shell:
            raise ConanInvalidConfiguration("A POSIX shell is required for tests")
        autotools.make(target="check", args=["LOG_COMPILER={}".format(test_shell)])

    def package(self):
        Autotools(self).install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "cpdb")
        self.cpp_info.set_property("cmake_target_name", "cpdb::cpdb-libs")
        self.cpp_info.bindirs = ["bin"]

        core = self.cpp_info.components["cpdb"]
        core.libs = ["cpdb"]
        core.requires = ["glib::glib", "glib::gobject", "glib::gio"]
        core.set_property("cmake_target_name", "cpdb::cpdb")
        core.set_property("pkg_config_name", "cpdb")

        frontend = self.cpp_info.components["frontend"]
        frontend.libs = ["cpdb-frontend"]
        frontend.requires = ["cpdb", "glib::glib", "glib::gobject", "glib::gio"]
        frontend.system_libs = ["pthread", "m", "crypt"]
        frontend.set_property("cmake_target_name", "cpdb::frontend")
        frontend.set_property("pkg_config_name", "cpdb-frontend")

        self.cpp_info.requires = ["cpdb", "frontend"]
