#!/usr/bin/env python3
"""Conan recipe - utftex 1.31."""
import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UtftexConan(ConanFile):
    name = "utftex"
    version = "1.31"
    description = "Render TeX math expressions as UTF-8 terminal text"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/bartp5/libtexprintf"
    url = "https://github.com/bartp5/libtexprintf"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.extra_ldflags.append("-fuse-ld=/data/service/hnp/bin/ld")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._ensure_autotools_aux_files()
        configure = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure):
            self._relax_configure_umask(configure)
            os.chmod(configure, 0o755)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def _ensure_autotools_aux_files(self):
        required = ["install-sh", "compile", "config.guess", "config.sub", "ltmain.sh"]
        if all(os.path.exists(os.path.join(self.source_folder, name)) for name in required):
            return
        autogen = os.path.join(self.source_folder, "autogen.sh")
        if os.path.exists(autogen):
            os.chmod(autogen, 0o755)
            self.run("sh ./autogen.sh", cwd=self.source_folder, env="conanbuild")
        else:
            self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")

    def _relax_configure_umask(self, configure):
        with open(configure, "r", encoding="utf-8", errors="ignore") as source:
            content = source.read()
        content = content.replace("umask 077", "umask 022")
        with open(configure, "w", encoding="utf-8") as source:
            source.write(content)

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
