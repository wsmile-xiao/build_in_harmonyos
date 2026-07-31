#!/usr/bin/env python3
"""Conan recipe for opusfile 0.12."""

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


class OpusfileConan(ConanFile):
    name = "opusfile"
    version = "0.12"
    description = "High-level API for decoding and seeking Ogg Opus streams"
    license = "BSD-3-Clause"
    homepage = "https://opus-codec.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    win_bash = True

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("libogg/1.3.5")
        self.requires("opus/1.5.2.1")
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        pkgconfig = PkgConfigDeps(self)
        pkgconfig.set_property("libogg", "pkg_config_name", "ogg")
        pkgconfig.generate()
        VirtualBuildEnv(self).generate()

        toolchain = AutotoolsToolchain(self)
        opus_include = os.path.join(
            self.dependencies["opus"].package_folder,
            "include",
            "opus",
        )
        toolchain.extra_cflags.append(f"-I{unix_path(self, opus_include)}")
        environment = toolchain.environment()
        if str(self.settings_build.os) == "OHOS":
            environment.define_path("SHELL", "/system/bin/sh")
            environment.define_path("CONFIG_SHELL", "/system/bin/sh")
            environment.define("MKDIR_P", "/system/bin/mkdir -p")
        toolchain.generate(env=environment)

    def _make_args(self):
        args = []
        if str(self.settings_build.os) == "Windows":
            args.append("-j1")
        if str(self.settings.os) == "OHOS" and self.options.shared:
            flags = "-avoid-version -no-undefined"
            args.extend(
                [
                f'libopusfile_la_LDFLAGS="{flags}"',
                f'libopusurl_la_LDFLAGS="{flags}"',
                ]
            )
        return args

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
        signed = path + ".opusfile-signed"
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
        if str(self.settings_build.os) == "OHOS":
            configure = os.path.join(self.source_folder, "configure")
            shell = "/system/bin/sh"
            if not os.path.isfile(shell):
                raise ConanException(f"Required OHOS shell is missing: {shell}")
            environment = Environment()
            environment.define_path("SHELL", shell)
            environment.define_path("CONFIG_SHELL", shell)
            with environment.vars(self).apply():
                self.run(f'"{shell}" "{configure}" {autotools._configure_args}')
                autotools.make(args=self._make_args())
        else:
            autotools.configure()
            autotools.make(args=self._make_args())
        suffix = ".so" if self.options.shared else ".a"
        stage = os.path.join(self.build_folder, "package-libs")
        os.makedirs(stage, exist_ok=True)
        for name in (f"libopusfile{suffix}", f"libopusurl{suffix}"):
            matches = []
            for root, _, files in os.walk(self.build_folder):
                if name in files and os.path.abspath(root) != os.path.abspath(stage):
                    matches.append(os.path.join(root, name))
            if len(matches) != 1:
                raise ConanException(f"Expected one built {name}, got {matches}")
            shutil.copy2(matches[0], os.path.join(stage, name))

    def package(self):
        suffix = ".so" if self.options.shared else ".a"
        libraries = []
        for name in (f"libopusfile{suffix}", f"libopusurl{suffix}"):
            libraries.extend(
                copy(
                    self,
                    name,
                    src=os.path.join(self.build_folder, "package-libs"),
                    dst=os.path.join(self.package_folder, "lib"),
                )
            )
        headers = copy(
            self,
            "opusfile.h",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include", "opus"),
        )
        pkgconfigs = []
        for name in ("opusfile.pc", "opusurl.pc"):
            pkgconfigs.extend(
                copy(
                    self,
                    name,
                    src=self.build_folder,
                    dst=os.path.join(self.package_folder, "lib", "pkgconfig"),
                )
            )
        licenses = copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        counts = tuple(map(len, (libraries, headers, pkgconfigs, licenses)))
        if counts != (2, 1, 2, 1):
            raise ConanException(
                "Incomplete package copy: expected 2 libraries, 1 header, "
                f"2 pkg-config files, and 1 license; got {counts}"
            )

        libdir = os.path.join(self.package_folder, "lib")
        rm(self, "*.la", libdir)
        expected = (
            os.path.join(libdir, f"libopusfile{suffix}"),
            os.path.join(libdir, f"libopusurl{suffix}"),
            os.path.join(self.package_folder, "include", "opus", "opusfile.h"),
            os.path.join(libdir, "pkgconfig", "opusfile.pc"),
            os.path.join(libdir, "pkgconfig", "opusurl.pc"),
            os.path.join(self.package_folder, "licenses", "COPYING"),
        )
        missing = [path for path in expected if not os.path.isfile(path) or os.path.getsize(path) == 0]
        if missing:
            raise ConanException(f"Package output is missing or empty: {missing}")
        if any(name.endswith(".la") for name in os.listdir(libdir)):
            raise ConanException("Libtool archive cleanup failed")
        if str(self.settings.os) == "OHOS" and self.options.shared and can_run(self):
            for name in ("libopusfile.so", "libopusurl.so"):
                path = os.path.join(self.package_folder, "lib", name)
                if not os.path.isfile(path) or os.path.islink(path):
                    raise ConanException(f"Expected one real unversioned shared object: {path}")
                self._sign_ohos_elf(path)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "OpusFile")

        core = self.cpp_info.components["opusfile"]
        core.libs = ["opusfile"]
        core.requires = ["libogg::libogg", "opus::opus"]
        core.set_property("cmake_target_name", "OpusFile::opusfile")
        core.set_property("pkg_config_name", "opusfile")

        url = self.cpp_info.components["opusurl"]
        url.libs = ["opusurl"]
        url.requires = ["opusfile", "openssl::openssl"]
        url.set_property("cmake_target_name", "OpusFile::opusurl")
        url.set_property("pkg_config_name", "opusurl")
