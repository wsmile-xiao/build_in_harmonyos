#!/usr/bin/env python3
"""Conan recipe - dhcpd-pools 3.2."""
import os
import shlex
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DhcpdPoolsConan(ConanFile):
    name = "dhcpd-pools"
    version = "3.2"
    description = "ISC dhcpd lease pool usage analyzer"
    license = "BSD-2-Clause"
    homepage = "http://dhcpd-pools.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(
            self,
            **self.conan_data["uthash"],
            destination=os.path.join(self.source_folder, "build_deps", "uthash"),
            strip_root=True,
        )

    def _uthash_include_dir(self):
        return os.path.join(self.source_folder, "build_deps", "uthash", "src")

    def _configure_args(self):
        args = [
            "--prefix=/",
            "--bindir=${prefix}/bin",
            "--sbindir=${prefix}/bin",
            "--libdir=${prefix}/lib",
            "--includedir=${prefix}/include",
            "--oldincludedir=${prefix}/include",
            f"--with-uthash={self._uthash_include_dir()}",
            "--disable-doxygen",
        ]
        if self.settings.os == "OHOS":
            args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        return args

    def _ensure_executable_scripts(self):
        roots = {self.source_folder, self.build_folder}
        for root in roots:
            for relpath in ("configure", "tests/test.sh"):
                path = os.path.join(root, relpath)
                if os.path.exists(path):
                    mode = os.stat(path).st_mode
                    os.chmod(path, mode | stat.S_IXUSR)

            tests_dir = os.path.join(root, "tests")
            if os.path.isdir(tests_dir):
                for name in os.listdir(tests_dir):
                    path = os.path.join(tests_dir, name)
                    if os.path.isfile(path):
                        mode = os.stat(path).st_mode
                        os.chmod(path, mode | stat.S_IXUSR)

    def _patch_ohos_configure_tmpdir(self):
        if self.settings.os != "OHOS":
            return
        configure = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure, "(umask 077 && mktemp -d", "(umask 022 && mktemp -d")
        replace_in_file(self, configure, "(umask 077 && mkdir \"$tmp\")", "(umask 022 && mkdir \"$tmp\")")

    def _patch_ohos_sources(self):
        if self.settings.os != "OHOS":
            return
        main_source = os.path.join(self.source_folder, "src", "dhcpd-pools.c")
        replace_in_file(
            self,
            main_source,
            "char *value;\n\n\twhile (*arg != '\\0') {\n\t\tswitch (getsubopt(&arg, tokens, &value)) {",
            "char *value;\n\n\twhile (*arg != '\\0') {\n\t\tchar *unknown = arg;\n\t\tswitch (getsubopt(&arg, tokens, &value)) {",
        )
        replace_in_file(
            self,
            main_source,
            "error(EXIT_FAILURE, 0, \"unknown --skip specifier: %s\", value);",
            "error(EXIT_FAILURE, 0, \"unknown --skip specifier: %s\", value ? value : unknown);",
        )
        errors_test = os.path.join(self.source_folder, "tests", "errors")
        replace_in_file(self, errors_test, "sed 's/: ..\\/..\\/tests/: .\\/tests/'", "sed 's|: /.*tests|: ./tests|'")

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_args())
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._ensure_executable_scripts()
        self._patch_ohos_sources()
        self._patch_ohos_configure_tmpdir()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.chmod(tmpdir, 0o755)
        autotools = Autotools(self)
        configure = os.path.join(self.source_folder, "configure")
        args = " ".join(shlex.quote(arg) for arg in [configure] + self._configure_args())
        self.run(
            f"TMPDIR={shlex.quote(tmpdir)} TMPPREFIX={shlex.quote(os.path.join(tmpdir, 'zsh'))} sh {args}",
            env="conanbuild",
            cwd=self.build_folder,
        )
        autotools.make(args=["-j1"])
        autotools.make(target="check", args=["-j1", "LOG_COMPILER=sh"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
