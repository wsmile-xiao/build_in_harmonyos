#!/usr/bin/env python3
"""Conan test_package for sisc-scheme 1.16.6."""
import os
import shutil
import subprocess

from conan import ConanFile


class SiscSchemeTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if os.name == "nt":
            bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash")
        else:
            bash = shutil.which("bash") or os.environ.get("CONFIG_SHELL")
        bash = bash or "/storage/Users/currentUser/usr/local/bin/bash"
        bash_arg = bash
        pkg = self.dependencies["sisc-scheme"].package_folder
        sisc = os.path.join(pkg, "bin", "sisc")
        if not os.path.exists(sisc):
            raise Exception(f"sisc wrapper not found at {sisc}")
        script = os.path.join(self.source_folder, "test.sh")
        if os.name == "nt":
            cygpath = shutil.which("cygpath")
            if not cygpath and bash:
                candidate = os.path.join(os.path.dirname(bash), "cygpath.exe")
                if os.path.exists(candidate):
                    cygpath = candidate
            if cygpath:
                script = subprocess.check_output([cygpath, "-u", script], text=True).strip()
                sisc = subprocess.check_output([cygpath, "-u", sisc], text=True).strip()
                bash_arg = subprocess.check_output([cygpath, "-u", bash], text=True).strip()
        self.run(f'"{bash}" "{script}" "{sisc}" "{bash_arg}"')
