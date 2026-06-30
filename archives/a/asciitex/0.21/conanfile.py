"""Conan recipe — asciitex 0.21 (Autotools).

Generate ASCII-art representations of mathematical equations.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class AsciitexConan(ConanFile):
    name = "asciitex"
    version = "0.21"
    description = "Generate ASCII-art representations of mathematical equations"
    license = "GPL-2.0-only"
    homepage = "https://asciitex.sourceforge.net/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        # Disable GTK GUI (not available on HarmonyOS)
        tc.configure_args.append("--disable-gtk")
        tc.generate()
        # R26: BUILD_SHARED_LIBS=OFF
        env = Environment()
        env.define("BUILD_SHARED_LIBS", "OFF")
        envvars = env.vars(self, scope="build")
        envvars.save_script("asciitex_build_env")

    def build(self):
        apply_conandata_patches(self)
        # Fix umask 077 -> 022 in configure script (HMDFS permission issue)
        configure_script = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_script):
            with open(configure_script, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            with open(configure_script, "w") as f:
                f.write(content)
            self.output.info("Patched configure: umask 077 -> 022")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Terminal tool: no libraries to link, only executables
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
