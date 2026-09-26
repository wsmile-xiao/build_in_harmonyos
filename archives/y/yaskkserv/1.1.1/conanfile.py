#!/usr/bin/env python3
"""Conan recipe for yaskkserv 1.1.1 on Linux and HarmonyOS."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class YaskkservConan(ConanFile):
    name = "yaskkserv"
    version = "1.1.1"
    description = "Yet Another SKK server: fast Japanese kana-kanji conversion dictionary server"
    license = "GPL-2.0-or-later"
    homepage = "http://umiushi.org/~wac/yaskkserv/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    _commands = (
        "yaskkserv_simple",
        "yaskkserv_normal",
        "yaskkserv_hairy",
        "yaskkserv_make_dictionary",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _find_tool(self, name, fallbacks):
        found = shutil.which(name)
        if found:
            return found
        for candidate in fallbacks:
            if os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration(
            f"{name} is required to build yaskkserv on OHOS"
        )

    def build(self):
        apply_conandata_patches(self)
        perl = self._find_tool("perl", ["/data/service/hnp/bin/perl"])
        prefix = shlex.quote(self.package_folder)
        # The perl configure probes compilers through File::Temp with a
        # /tmp template: OHOS /tmp is read-only, so point TMPDIR at the
        # writable build folder.
        tmpdir = shlex.quote(self.build_folder)
        self.run(
            f"TMPDIR={tmpdir} {shlex.quote(perl)} ./configure "
            f"--compiler=clang++ --prefix={prefix}",
            cwd=self.source_folder,
            env="conanbuild",
        )
        self.run("make", cwd=self.source_folder, env="conanbuild")

        # The upstream Tcl-free test surface is empty; the packaged commands
        # are exercised after signature, matching the valkey family flow.
        is_ohos = str(self.settings.os) == "OHOS"
        if is_ohos:
            self._sign_ohos_binaries(
                os.path.join(
                    self.source_folder, "var", "bsd_cygwin_linux_gcc", "release"
                )
            )

    def _sign_ohos_binaries(self, releasedir):
        signer = self._find_tool(
            "binary-sign-tool",
            [
                "/data/service/hnp/bin/binary-sign-tool",
                "/storage/Users/currentUser/usr/local/bin/binary-sign-tool",
            ],
        )
        objcopy = self._find_tool(
            "llvm-objcopy",
            [
                "/data/service/hnp/bin/llvm-objcopy",
                "/storage/Users/currentUser/usr/local/bin/llvm-objcopy",
            ],
        )
        commands = set(self._commands)
        for name in sorted(commands):
            binary = os.path.join(releasedir, name, name)
            if not os.path.isfile(binary):
                raise ConanInvalidConfiguration(
                    f"expected build output missing: {binary}"
                )
            signed = binary + ".signed"
            self.run(
                f"{shlex.quote(objcopy)} --remove-section .codesign "
                f"{shlex.quote(binary)}",
                quiet=True,
            )
            self.run(
                f"{shlex.quote(signer)} sign -inFile {shlex.quote(binary)} "
                f"-outFile {shlex.quote(signed)} -selfSign 1",
                quiet=True,
            )
            os.replace(signed, binary)
            os.chmod(binary, 0o755)

    def package(self):
        if str(self.settings.os) == "OHOS":
            releasedir = os.path.join(
                self.source_folder, "var", "bsd_cygwin_linux_gcc", "release"
            )
            package_bin = os.path.join(self.package_folder, "bin")
            for binary in self._commands:
                copy(self, binary, src=os.path.join(releasedir, binary),
                     dst=package_bin)
        else:
            self.run(
                "make install",
                cwd=self.source_folder,
                env="conanbuild",
            )
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
