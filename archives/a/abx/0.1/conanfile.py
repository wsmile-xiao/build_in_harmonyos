#!/usr/bin/env python3
"""Conan recipe for abx 0.1, an audio ABX testing application."""

import glob
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class AbxConan(ConanFile):
    name = "abx"
    version = "0.1"
    description = "Software-based audio ABX testing application"
    license = "GPL-3.0-or-later"
    homepage = "https://phintsan.kapsi.fi/abx.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("gtk/3.24.38", transitive_headers=True, transitive_libs=True)
        self.requires("libsndfile/1.2.2")
        self.requires("portaudio/19.7.0")

    def build_requirements(self):
        # The GTK3/GLib patches update configure.ac, so autoreconf must rebuild
        # configure and Makefile.in. automake also exposes aclocal's macro path.
        self.tool_requires("automake/1.18")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"abx supports Linux/OHOS native builds, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # configure.ac discovers every host dependency through pkg-config.
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()

        toolchain = AutotoolsToolchain(self)
        environment = toolchain.environment()
        for directory in sorted(glob.glob("/data/service/hnp/*/*/share/aclocal")):
            environment.append_path("ACLOCAL_PATH", directory)

        # OHOS /tmp may be read-only. Keep autoreconf/configure temporary files
        # inside this isolated Conan build directory.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        environment.define_path("TMPPREFIX", os.path.join(tmpdir, "zsh"))
        toolchain.generate(env=environment)

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            if self.settings.os == "OHOS":
                self._bootstrap_autotools_for_ohos()
                self._make_config_status_tmp_writable(
                    os.path.join(self.source_folder, "configure")
                )
            else:
                self.run(
                    "autoreconf --force --install --verbose",
                    cwd=self.source_folder,
                    env="conanbuild",
                )

            autotools = Autotools(self)
            if self.settings.os == "OHOS":
                configure_script = os.path.join(self.source_folder, "configure")
                command = (
                    "CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh "
                    + shlex.join(["/system/bin/sh", configure_script])
                )
                if autotools._configure_args:
                    command = f"{command} {autotools._configure_args}"
                self.run(command, cwd=self.build_folder)
            else:
                autotools.configure()
            # A single job avoids make jobserver/FIFO failures on HMDFS.
            autotools.make(args=["-j1"])
            # Upstream 0.1 has no automated test suite or TESTS/check_PROGRAMS.

    def package(self):
        with self._build_environment().vars(self).apply():
            Autotools(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        if self.settings.os == "OHOS":
            self._sign_ohos_elf(os.path.join(self.package_folder, "bin", "abx"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

    def _build_environment(self):
        environment = Environment()
        if self.settings.os == "OHOS":
            sdk_llvm_libs = sorted(
                glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib")
            )
            if sdk_llvm_libs:
                # The SDK lld needs its ABI-matched libxml2 during compiler probes.
                environment.prepend_path("LD_LIBRARY_PATH", sdk_llvm_libs[-1])
        return environment

    @staticmethod
    def _make_config_status_tmp_writable(path):
        # Autoconf's embedded config.status template creates a 0700 temp
        # directory. HMDFS adds setgid semantics that make it unwritable.
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
        patched = content.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`',
        ).replace(
            '(umask 077 && mkdir "$tmp")',
            'mkdir "$tmp"',
        )
        if patched == content:
            raise ConanException(
                "Autoconf config.status temporary-directory template changed"
            )
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(patched)

    def _bootstrap_autotools_for_ohos(self):
        # automake/aclocal are Perl scripts in the Conan cache. HMDFS blocks
        # direct shebang execution, so invoke their real entry points through
        # the SDK Perl interpreter and pass the relocatable package paths.
        automake_root = self.dependencies.build["automake"].package_folder
        perl = shutil.which("perl") or "/data/service/hnp/bin/perl"
        automake_share = os.path.join(automake_root, "share", "automake-1.18")
        common = [perl, "-I", automake_share]

        aclocal = os.path.join(automake_root, "bin", ".aclocal-real")
        self.run(
            shlex.join(
                common
                + [
                    aclocal,
                    "--automake-acdir="
                    + os.path.join(automake_root, "share", "aclocal-1.18"),
                    "--system-acdir="
                    + os.path.join(automake_root, "share", "aclocal"),
                    "--force",
                ]
            ),
            cwd=self.source_folder,
            env="conanbuild",
        )
        self.run("autoconf --force", cwd=self.source_folder, env="conanbuild")
        self.run("autoheader --force", cwd=self.source_folder, env="conanbuild")

        automake = os.path.join(automake_root, "bin", ".automake-real")
        self.run(
            shlex.join(
                common
                + [
                    automake,
                    "--libdir=" + automake_share,
                    "--add-missing",
                    "--copy",
                    "--force-missing",
                ]
            ),
            cwd=self.source_folder,
            env="conanbuild",
        )

    @staticmethod
    def _sign_ohos_elf(path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(path):
            raise ConanException(f"Missing packaged executable: {path}")
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("Required OHOS signing tools are missing")
        output = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", output],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("Signed packaged executable has invalid .codesign count")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)
