#!/usr/bin/env python3
"""Conan recipe for aspell-compat 0.60.8.2.

aspell-compat is the Alpine Linux subpackage of GNU Aspell that ships the
ispell / unix spell compatibility shell scripts. It contains no compiled
code — only two POSIX shell scripts (`ispell`, `spell`) that wrap the
`aspell` CLI. The source is the upstream aspell tarball itself.

Build: no configure/make — the two scripts are copied from scripts/ to bin/.
Runtime dependency: aspell (provides the `aspell` binary the scripts exec).

R34: test_package actually executes the ispell/spell scripts against a real
     word list, proving they wrap the aspell CLI correctly.
R38: produces executables (ispell, spell) → commands.json at software level.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get, export_conandata_patches


class AspellCompatConan(ConanFile):
    name = "aspell-compat"
    version = "0.60.8.2"
    package_type = "application"

    description = (
        "aspell compatibility scripts for ispell and unix spell "
        "(POSIX shell wrappers around the aspell CLI)"
    )
    license = "LGPL-2.1-or-later"
    homepage = "http://aspell.net"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("spell", "ispell", "aspell", "compat")

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The scripts exec the `aspell` binary at runtime.
        self.requires("aspell/0.60.8")

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # aspell-compat is a scripts-only package: no compilation.
        # Verify the two wrapper scripts exist and are valid POSIX shell.
        scripts_dir = os.path.join(self.source_folder, "scripts")
        for script in ("spell", "ispell"):
            path = os.path.join(scripts_dir, script)
            if not os.path.isfile(path):
                raise Exception(f"missing compat script: {path}")
            self.run(f"sh -n '{path}'")

    def package(self):
        scripts_dir = os.path.join(self.source_folder, "scripts")
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "spell", scripts_dir, bin_dir)
        copy(self, "ispell", scripts_dir, bin_dir)
        os.chmod(os.path.join(bin_dir, "spell"), 0o755)
        os.chmod(os.path.join(bin_dir, "ispell"), 0o755)

    def package_info(self):
        # Scripts live in bin/; no libraries.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
