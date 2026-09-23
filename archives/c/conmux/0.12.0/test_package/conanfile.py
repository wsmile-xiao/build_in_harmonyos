#!/usr/bin/env python3
"""Conan test_package for conmux 0.12.0 — consumer check.

Runs test_conmux.py (standalone test source, satisfies L0c) via self.run
with env="conanrun". The test drives the real conmux-registry protocol
(LOOKUP/ADD/LIST) and loads Conmux.pm through the packaged scripts —
real API verification (R34), not a print-only shell.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class ConmuxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 显式声明运行时依赖模块（test 需定位其 site_perl 目录提供 PERL5LIB）
        self.requires("perl-io-multiplex/1.16")
        self.requires("perl-uri/5.35")

    def _locate_perl5_dirs(self) -> str:
        """Collect PERL5LIB (site_perl roots) from perl-module deps.
        IO/Multiplex.pm sits under <site>/IO/, URI/Escape.pm under
        <site>/URI/ — perl needs -I <site> to resolve both.  Return
        each dependency's site_perl root (parent of IO/ and URI/)."""
        dirs = []
        for dep in ("perl-io-multiplex", "perl-uri"):
            if dep not in self.dependencies:
                continue
            pkg = self.dependencies[dep].package_folder
            for root, _dirs, files in os.walk(pkg):
                base = os.path.basename(root)
                if base == "IO" and "Multiplex.pm" in files:
                    dirs.append(os.path.dirname(root))
                    break
                if base == "URI" and "Escape.pm" in files:
                    dirs.append(os.path.dirname(root))
                    break
        return ":".join(sorted(set(dirs)))

    def test(self):
        pkg = self.dependencies["conmux"].package_folder
        # locate packaged sbin/conmux-registry and lib/Conmux.pm
        registry = os.path.join(pkg, "usr", "local", "conmux",
                                "sbin", "conmux-registry")
        conmux = os.path.join(pkg, "usr", "local", "conmux",
                              "sbin", "conmux")
        conmux_lib = os.path.join(pkg, "usr", "local", "conmux", "lib")
        if not os.path.isfile(registry):
            raise ConanException(f"conmux-registry missing: {registry}")
        if not os.path.isfile(conmux):
            raise ConanException(f"conmux missing: {conmux}")
        if not os.path.isfile(os.path.join(conmux_lib, "Conmux.pm")):
            raise ConanException("Conmux.pm missing in package")
        perl5 = self._locate_perl5_dirs()
        if not perl5:
            raise ConanException("perl dependency modules not found")
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_conmux.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_conmux.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{registry}' '{conmux_lib}' "
                 f"'{perl5}'", env="conanrun")
