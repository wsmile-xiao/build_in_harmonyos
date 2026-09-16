#!/usr/bin/env python3
"""Conan recipe for makedepend 1.0.10 — X.Org Makefile dependency generator.

makedepend parses C/C++ sources and appends ``# DO NOT DELETE`` dependency
blocks to an existing Makefile.  It is the tool that mk-configure (bmake
based) looks for when mkdep/nbmkdep are unavailable, so the package is
published as an application (bin/makedepend).

The release tarball ships a pre-generated ``configure``; no autotools
regeneration is performed, therefore autoconf/automake/libtool are not
build requirements.  ``util-macros`` is kept as a tool requirement because
``configure`` queries ``xorg-macros`` through pkg-config (XORG_MANPAGE_SECTIONS
macros_datadir/INSTALL_CMD).
"""

import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MakedependConan(ConanFile):
    name = "makedepend"
    version = "1.0.10"
    description = "Create dependencies in makefiles (X.Org makedepend)"
    license = "MIT-open-group AND HPND-sell-variant"
    homepage = "https://gitlab.freedesktop.org/xorg/util/makedepend"
    url = ""

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("OHOS", "Linux"):
            raise ConanInvalidConfiguration(
                f"makedepend supports OHOS and Linux, not {self.settings.os}"
            )
        if str(self.settings.arch) not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration(
                f"makedepend/{self.version} is validated on aarch64 only"
            )

    def build_requirements(self):
        # configure probes xorg-macros via pkg-config; a missing .pc only warns,
        # but every X.Org autotools recipe in this repository provides it.
        self.tool_requires("util-macros/1.20.1")

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        tc = AutotoolsToolchain(self)
        # patches/0001 teaches config.guess about HarmonyOS; the triplets are
        # passed explicitly so configure never has to guess the build type.
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-ohos",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream suite is two shell tests driven by 'make check' (no extra cost).
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        binary = os.path.join(self.package_folder, "bin", "makedepend")
        if os.path.exists(binary):
            self._sign_binary(binary)

    def _sign_binary(self, path):
        """OHOS: sign the packaged executable so device policy accepts it."""
        os.chmod(path, 0o755)
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if str(self.settings.os) != "OHOS" or not (
            os.path.exists(sign_tool) and os.path.exists(objcopy)
        ):
            return
        tmp_signed = path + ".signed"
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [sign_tool, "sign", "-inFile", path, "-outFile", tmp_signed, "-selfSign", "1"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        os.replace(tmp_signed, path)
        os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
