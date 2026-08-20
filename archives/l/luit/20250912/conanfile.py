#!/usr/bin/env python3
"""Conan recipe — luit 20250912 (Autotools)"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class LuitConan(ConanFile):
    name = "luit"
    version = "20250912"
    description = "Filter run between arbitrary application and UTF-8 terminal emulator"
    license = "MIT-like"
    homepage = "https://invisible-mirror.net/archives/luit/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        # E002: /tmp is read-only on HMDFS, redirect TMPDIR
        tmpdir = os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("TMPDIR", tmpdir)
        envvars = env.vars(self)
        envvars.save_script("env_tmpdir")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # HMDFS umask 077 incompatibility: config.status creates directories
        # with umask 077, but HMDFS doesn't allow writing to those directories.
        # Fix: change umask 077 to 022 in config.status, then re-run it.
        config_status = os.path.join(self.build_folder, "config.status")
        if os.path.exists(config_status):
            with open(config_status, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            with open(config_status, "w") as f:
                f.write(content)
            self.run("sh ./config.status", env="conanbuild")
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
