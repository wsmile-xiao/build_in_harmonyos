#!/usr/bin/env python3
"""Conan test_package — mypaint-brushes 2.0.2.

L1 official test: substantive consumer verification (R34) of the packaged
pure brush-data package (no C/C++ API, no binaries):

  1. packaged layout: share/mypaint-data/2.0/brushes/ exists with all
     7 upstream brush groups (Dieterle, classic, deevad, experimental,
     kaerhon_v1, ramon, tanda) plus order.conf
  2. content integrity: every order.conf entry resolves to a real .myb
     file on disk (order<->disk cross-check, 196/196) and a sample .myb
     has the gzip magic header (MyPaint 2.x brush files are gzipped JSON)
  3. pkgconfig: share/pkgconfig/mypaint-brushes-2.0.pc is installed and
     declares the brushesdir pointing into the package
  4. purity: no lib/ or bin/ artifacts (data-only package, R38)
"""
import os

from conan import ConanFile


class MypaintbrushesTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["mypaint-brushes"]
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test_mypaint_brushes.sh")
        self.run(f'"{bash}" "{script}" "{pkg.package_folder}"', env="conanrun")
