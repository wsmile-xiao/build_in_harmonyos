#!/usr/bin/env python3
"""Conan recipe for Nagios Plugins 2.5 on HarmonyOS."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import load_toolchain_args
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NagiosPluginsConan(ConanFile):
    name = "nagios-plugins"
    version = "2.5"
    description = "Official monitoring plugins for Nagios"
    license = "GPL-3.0-or-later"
    homepage = "https://nagios-plugins.org/"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "nagios-plugins 2.5 is adapted for Linux and OHOS"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("openssl/3.5.6")

    def generate(self):
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()

        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            [
                "--prefix=/",
                "--libexecdir=/bin",
                "--enable-extra-opts",
                "--enable-perl-modules=no",
                "--with-openssl={}".format(
                    self.dependencies["openssl"].package_folder
                ),
                "--with-gnutls=no",
                "--with-pgsql=no",
                "--without-dbi",
                "--without-radius",
                "--without-ldap",
                "--with-mysql=no",
            ]
        )
        if str(self.settings.os) == "OHOS":
            toolchain.configure_args.extend(
                [
                    "--build=aarch64-unknown-linux-gnu",
                    "--host=aarch64-unknown-linux-gnu",
                    "--with-ps-command=/bin/ps -o stat,uid,pid,ppid,vsz,rss,pcpu,comm,args",
                    "--with-ps-format=%%s %%d %%d %%d %%d %%d %%f %%s %%n",
                    "--with-ps-cols=9",
                    "--with-ps-varlist=procstat,&procuid,&procpid,&procppid,&procvsz,&procrss,&procpcpu,procprog,&pos",
                ]
            )
            toolchain.extra_cflags.extend(
                [
                    "-include",
                    "utmp.h",
                    "-Dpthread_cancel=pthread_self",
                    "-Dsetutxent=setutent",
                    "-Dgetutxent=getutent",
                    "-Dendutxent=endutent",
                    "-Drindex=strrchr",
                ]
            )
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        self._prepare_temp_directory()
        self._prepare_configure_temp_permissions()
        self._configure_with_shell()
        self._prepare_plugin_alias_rules()

        self.run("make -j1", cwd=self.build_folder, env="conanbuild")
        self._run_targeted_upstream_test()

    def package(self):
        Autotools(self).install(args=["-j1"])

        # The upstream root-only plugins are installed without setuid bits for
        # package managers; a device-side installer may apply policy later.
        destination = shlex.quote(self.package_folder)
        self.run(
            "make -j1 install-packager DESTDIR={}".format(destination),
            cwd=self.build_folder,
            env="conanbuild",
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

        bin_dir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.prepend_path("PATH", bin_dir)
        self.runenv_info.prepend_path("PATH", bin_dir)

    def _prepare_temp_directory(self):
        temp_dir = os.path.join(self.build_folder, "_tmp")
        os.makedirs(temp_dir, exist_ok=True)
        for variable in ("TMPDIR", "TMP", "TEMP"):
            os.environ[variable] = temp_dir

    def _prepare_configure_temp_permissions(self):
        configure = os.path.join(self.source_folder, "configure")
        with open(configure, "r", encoding="utf-8") as stream:
            content = stream.read()

        adjusted = content.replace("umask 077 && mktemp -d", "umask 000 && mktemp -d")
        adjusted = adjusted.replace("umask 077 && mkdir", "umask 000 && mkdir")
        if adjusted == content:
            raise RuntimeError("configure temporary-directory setup was not found")

        with open(configure, "w", encoding="utf-8") as stream:
            stream.write(adjusted)

    def _configure_with_shell(self):
        shell = self._config_shell()
        configure_args = load_toolchain_args(self.generators_folder).get(
            "configure_args", ""
        )
        configure = os.path.join(self.source_folder, "configure")
        command = " ".join(
            part
            for part in (
                "CONFIG_SHELL={}".format(shlex.quote(shell)),
                "SHELL={}".format(shlex.quote(shell)),
                shlex.quote(shell),
                shlex.quote(configure),
                configure_args,
            )
            if part
        )
        self.run(command, cwd=self.build_folder, env="conanbuild")

    def _prepare_plugin_alias_rules(self):
        makefile = os.path.join(self.build_folder, "plugins", "Makefile")
        with open(makefile, "r", encoding="utf-8") as stream:
            content = stream.read()

        replacements = {
            "ln -s check_tcp $@": "cp -p check_tcp $@",
            "ln -s check_tcp $$i": "cp -p check_tcp $$i",
            "ln -s check_ldap check_ldaps": "cp -p check_ldap check_ldaps",
        }
        adjusted = content
        for source, target in replacements.items():
            adjusted = adjusted.replace(source, target)

        if adjusted == content:
            raise RuntimeError("plugin alias rules were not found in plugins/Makefile")

        with open(makefile, "w", encoding="utf-8") as stream:
            stream.write(adjusted)

    def _run_targeted_upstream_test(self):
        perl = shutil.which("perl")
        if not perl:
            self.output.warning(
                "Perl is unavailable; skipping upstream plugins/t/check_dummy.t"
            )
            return

        test_script = os.path.join(self.build_folder, "test.pl")
        test_file = os.path.join(
            self.source_folder, "plugins", "t", "check_dummy.t"
        )
        command = "{} -I {} -I {} {} {}".format(
            shlex.quote(perl),
            shlex.quote(self.build_folder),
            shlex.quote(self.source_folder),
            shlex.quote(test_script),
            shlex.quote(test_file),
        )
        self.run(
            command,
            cwd=os.path.join(self.build_folder, "plugins"),
            env="conanbuild",
        )

    @staticmethod
    def _config_shell():
        candidates = (
            os.environ.get("CONFIG_SHELL"),
            "/data/service/hnp/bin/bash",
            shutil.which("bash"),
            shutil.which("sh"),
            "/system/bin/sh",
            "/bin/sh",
        )
        for candidate in candidates:
            if not candidate:
                continue
            if os.path.isabs(candidate):
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    return candidate
            elif shutil.which(candidate):
                return candidate
        return "sh"
