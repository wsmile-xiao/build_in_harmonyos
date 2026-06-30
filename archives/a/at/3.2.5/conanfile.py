#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace At, at, 3.2.5, at 3.2.5, MIT,
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class AtConan(ConanFile):
    name = "at"
    version = "3.2.5"
    description = "at 3.2.5"
    license = "MIT"
    homepage = ""
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        # at doesn't support out-of-source builds; use in-source layout
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # at requires jobdir and atspool to be specified
        tc.configure_args.append("--with-jobdir=/var/spool/atjobs")
        tc.configure_args.append("--with-atspool=/var/spool/atspool")
        tc.generate()
        # HMDFS doesn't support mkfifo (needed by make jobserver), force -j1
        # Also set SENDMAIL path (atd.c requires it at compile time)
        # Create no-op chown/chgrp wrappers (not available on HarmonyOS)
        bin_dir = os.path.join(self.build_folder, "_ohos_bin")
        os.makedirs(bin_dir, exist_ok=True)
        for cmd in ["chown", "chgrp"]:
            script_path = os.path.join(bin_dir, cmd)
            with open(script_path, "w") as f:
                f.write("#!/bin/sh\nexit 0\n")
            os.chmod(script_path, 0o755)
        env = Environment()
        env.define("MAKEFLAGS", "-j1")
        env.define("SENDMAIL", "/usr/sbin/sendmail")
        env.append_path("PATH", bin_dir)
        envvars = env.vars(self)
        envvars.save_script("env_overrides")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])

    def package_info(self):
        # at is a binary-only package (no shared/static library)
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
