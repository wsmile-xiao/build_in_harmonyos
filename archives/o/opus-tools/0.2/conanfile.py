#!/usr/bin/env python3
"""Conan recipe for opus-tools 0.2."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout
from conan.tools.microsoft import unix_path


class OpusToolsConan(ConanFile):
    name = "opus-tools"
    version = "0.2"
    description = "Command-line tools for encoding, decoding, and inspecting Opus audio files"
    license = "BSD-3-Clause"
    homepage = "https://opus-codec.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("opus/1.5.2.1")
        self.requires("libogg/1.3.5")
        self.requires("opusfile/0.12")
        self.requires("libopusenc/0.2.1")
        self.requires("flac/1.4.3")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        for f in ["aclocal.m4", "Makefile.in", "configure", "config.h.in", "stamp-h1"]:
            path = os.path.join(self.source_folder, f)
            if os.path.exists(path):
                os.utime(path, None)

    def generate(self):
        pkgconfig = PkgConfigDeps(self)
        pkgconfig.set_property("opus", "pkg_config_name", "opus")
        pkgconfig.set_property("libogg", "pkg_config_name", "ogg")
        pkgconfig.set_property("opusfile", "pkg_config_name", "opusfile")
        pkgconfig.set_property("opusurl", "pkg_config_name", "opusurl")
        pkgconfig.set_property("libopusenc", "pkg_config_name", "libopusenc")
        pkgconfig.set_property("flac", "pkg_config_name", "flac")
        pkgconfig.set_property("flac++", "pkg_config_name", "flac++")
        pkgconfig.generate()
        VirtualBuildEnv(self).generate()

        for dep_name in ("opus", "libogg", "opusfile", "libopusenc", "flac"):
            dep = self.dependencies[dep_name]
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir):
                rm(self, "*.la", libdir)

        toolchain = AutotoolsToolchain(self)
        for dep_name in ("opus", "opusfile", "libopusenc"):
            dep = self.dependencies[dep_name]
            include_path = os.path.join(dep.package_folder, "include", "opus")
            toolchain.extra_cflags.append(f"-I{unix_path(self, include_path)}")
        environment = toolchain.environment()
        if str(self.settings_build.os) == "OHOS":
            environment.define_path("SHELL", "/system/bin/sh")
            environment.define_path("CONFIG_SHELL", "/system/bin/sh")
            environment.define("MKDIR_P", "/system/bin/mkdir -p")
        toolchain.generate(env=environment)

    @staticmethod
    def _ohos_tool(name):
        path = shutil.which(name) or os.path.join("/data/service/hnp/bin", name)
        if not os.path.isfile(path):
            raise ConanException(f"Required OHOS tool is missing: {name}")
        return path

    def _sign_ohos_elf(self, path):
        readelf = self._ohos_tool("llvm-readelf")
        objcopy = self._ohos_tool("llvm-objcopy")
        signer = self._ohos_tool("binary-sign-tool")
        sections = subprocess.run(
            [readelf, "-SW", path],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        codesign_count = sections.count(".codesign")
        if codesign_count == 1:
            self.output.info(f"Preserving existing .codesign section: {path}")
            return
        if codesign_count != 0:
            raise ConanException(f"ELF has invalid .codesign count: {path}")
        clean = path + ".codesign-clean"
        signed = path + ".opus-tools-signed"
        for generated in (clean, signed):
            if os.path.exists(generated):
                os.remove(generated)
        try:
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", path, clean],
                check=True,
                timeout=30,
            )
            subprocess.run(
                [signer, "sign", "-inFile", clean, "-outFile", signed, "-selfSign", "1"],
                check=True,
                timeout=60,
            )
            sections = subprocess.run(
                [readelf, "-SW", signed],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            ).stdout
            if sections.count(".codesign") != 1:
                raise ConanException(f"Signed ELF has invalid .codesign count: {path}")
            os.chmod(signed, (os.stat(path).st_mode & 0o777) | 0o055)
            os.replace(signed, path)
        finally:
            for generated in (clean, signed):
                if os.path.exists(generated):
                    os.remove(generated)

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        autotools.install()

    def package(self):
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        if str(self.settings.os) == "OHOS" and can_run(self):
            for name in ("opusenc", "opusdec", "opusinfo"):
                path = os.path.join(self.package_folder, "bin", name)
                if os.path.isfile(path):
                    self._sign_ohos_elf(path)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
