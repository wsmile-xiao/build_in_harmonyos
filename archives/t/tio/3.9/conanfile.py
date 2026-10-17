#!/usr/bin/env python3
"""Conan recipe for tio 3.9.

tio is a Meson-built serial device I/O command-line tool. The recipe keeps the
hardware-independent build surface small: man page and bash completion install
paths are disabled, while Lua scripting support remains enabled through the
published lua package because upstream requires it.
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class TioConan(ConanFile):
    name = "tio"
    version = "3.9"
    description = "Serial device I/O command-line tool"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/tio/tio"
    url = "https://github.com/tio/tio"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"tio supports Linux and OHOS, got {self.settings.os}"
            )

    def configure(self):
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        self.requires("glib/2.84.0.1")
        self.requires("lua/5.4.8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True, verify=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        toolchain = MesonToolchain(self)
        toolchain.project_options["install_man_pages"] = False
        toolchain.project_options["bashcompletiondir"] = "no"
        toolchain.generate()
        self._inject_meson_binaries()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        binary = os.path.join(self.package_folder, "bin", "tio")
        if os.path.isfile(binary):
            os.chmod(binary, 0o755)
        if self.settings.os == "OHOS":
            self._sign_binary(binary)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

    def _inject_meson_binaries(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = executables.get("ar")
        ranlib = executables.get("ranlib")
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        cc = executables.get("c") or ""
        bindir = os.path.dirname(cc) if os.path.sep in cc else ""
        if not ar and bindir:
            for name in ("llvm-ar", "ar"):
                candidate = os.path.join(bindir, name)
                if os.path.isfile(candidate):
                    ar = candidate
                    break
        if not ranlib and bindir:
            for name in ("llvm-ranlib", "ranlib"):
                candidate = os.path.join(bindir, name)
                if os.path.isfile(candidate):
                    ranlib = candidate
                    break
        if not pkg_config:
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")

        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            path = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            additions = []
            if ar and "\nar =" not in content:
                additions.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content:
                additions.append(f"ranlib = '{ranlib}'")
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                additions.append(f"pkg-config = '{pkg_config}'")
            if not additions:
                continue
            content = content.replace(
                "[binaries]\n",
                "[binaries]\n" + "\n".join(additions) + "\n",
                1,
            )
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)

    def _sign_binary(self, binary):
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration(f"tio binary was not installed: {binary}")
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        signer = executables.get("sign_tool", "/data/service/hnp/bin/binary-sign-tool")
        objcopy = executables.get("objcopy", "/data/service/hnp/bin/llvm-objcopy")
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration(f"HarmonyOS binary signing tool not found: {signer}")
        if not os.path.isfile(objcopy):
            raise ConanInvalidConfiguration(f"HarmonyOS objcopy tool not found: {objcopy}")
        subprocess.run([objcopy, "--remove-section", ".codesign", binary], check=True)
        signed = binary + ".signed"
        subprocess.run(
            [
                signer,
                "sign",
                "-inFile",
                binary,
                "-outFile",
                signed,
                "-selfSign",
                "1",
            ],
            check=True,
        )
        os.replace(signed, binary)
        os.chmod(binary, 0o755)
