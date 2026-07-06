#!/usr/bin/env python3
"""Conan recipe — autocutsel 0.10.1 (Autotools).

autocutsel is an X11 clipboard synchronization tool that keeps
the PRIMARY and CLIPBOARD selections in sync.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AutocutselConan(ConanFile):
    name = "autocutsel"
    version = "0.10.1"
    description = "X11 clipboard synchronization tool (PRIMARY <-> CLIPBOARD)"
    license = "GPL-2.0"
    homepage = "https://github.com/sigmike/autocutsel"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # X11 system libraries are managed outside Conan (cmd-pkgs / system)
        # If Conan packages become available, use  channel (R27)
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported os: {self.settings.os}")
        tc = AutotoolsToolchain(self)
        # autocutsel is a binary tool, not a system same-name library.
        # X11 libs are system dependencies; static linking is not applicable (R26 scope: system same-name libs only).
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Set TMPDIR to a writable directory on OHOS (/tmp is read-only)
        home_dir = os.path.expanduser("~")
        tmpdir = os.path.join(home_dir, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

        # Set CPP for configure's RAWCPP detection (OHOS quirk)
        cc = os.environ.get("CC", "cc")
        os.environ["CPP"] = f"{cc} -E -"

        # Set X11 library paths (libs installed in ~/.usr/local)
        x11_prefix = os.path.join(home_dir, "usr", "local")
        x11_inc = os.path.join(x11_prefix, "include")
        x11_lib = os.path.join(x11_prefix, "lib")

        for key, val in [
            ("CPPFLAGS", f"-I{x11_inc}"),
            ("LDFLAGS", f"-L{x11_lib} -Wl,-rpath,{x11_lib}"),
            ("PKG_CONFIG_PATH", os.path.join(x11_lib, "pkgconfig")),
        ]:
            current = os.environ.get(key, "")
            if val not in current:
                os.environ[key] = f"{val} {current}".strip()

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # autocutsel is a binary tool, not a library — no cpp_info.libs
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

        # Set LD_LIBRARY_PATH for runtime (X11 libs in ~/.usr/local/lib)
        home_dir = os.path.expanduser("~")
        x11_lib = os.path.join(home_dir, "usr", "local", "lib")
        if os.path.isdir(x11_lib):
            self.runenv_info.append_path("LD_LIBRARY_PATH", x11_lib)
