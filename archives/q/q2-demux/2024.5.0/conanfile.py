#!/usr/bin/env python3
"""Conan recipe for q2-demux 2024.5.0 — pure-Python QIIME 2 plugin.

q2-demux is a pure-Python QIIME 2 plugin. It does NOT require the full
QIIME 2 runtime (qiime2 / q2-types / q2templates / pandas / numpy /
scikit-bio) to be *packaged*: this recipe archives the pure-Python source
tree into the package's site-packages, so the build is self-contained and
succeeds even when those ecosystem packages are not yet available in
build_in_harmonyos. Consumer-side runtime imports still need the QIIME 2
stack, but that is out of scope for archiving (R36: deps are layered on
later, after they are published to the artifact repo).

The test_package verifies two things (both R34-compliant, i.e. they really
depend on the archived artifact):
  * an archive-integrity / consumer test (鸿蒙-specific) that the package is
    correctly laid out under lib/pythonX.Y/site-packages, exposes a non-empty
    ``__version__``, is pure-Python (no arch-specific ELF -> OHOS-consumable),
    and is reachable via PYTHONPATH;
  * the upstream ``q2_demux.tests.test_ecc`` Golay-code unit suite (13 cases,
    unittest.TestCase) which depends ONLY on numpy, executed by stubbing the
    package namespace so the QIIME-2-only ``__init__`` is not triggered.
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import get, copy


class Q2DemuxConan(ConanFile):
    name = "q2-demux"
    version = "2024.5.0"
    description = "QIIME 2 plugin for demultiplexing sequence reads."
    license = "BSD-3-Clause"
    homepage = "https://github.com/qiime2/q2-demux"
    url = "https://github.com/qiime2/q2-demux"

    # Pure-Python package: only os/arch are relevant (R32: use in ("Linux", "OHOS"))
    settings = "os", "arch"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Pure-python QIIME 2 plugin: no compilation step required.
        pass

    def package(self):
        # Archive the pure-python package tree under a standard site-packages
        # layout (lib/pythonX.Y/site-packages) so the test_package -- and the
        # CI L1e destructive check, which sabotages lib/ -- can locate it.
        py_ver = "python{}.{}".format(sys.version_info.major, sys.version_info.minor)
        src_pkg = os.path.join(self.source_folder, "q2_demux")
        dst = os.path.join(self.package_folder, "lib", py_ver, "site-packages", "q2_demux")
        copy(self, "*", src_pkg, dst)

    def package_info(self):
        py_ver = "python{}.{}".format(sys.version_info.major, sys.version_info.minor)
        site_packages = os.path.join("lib", py_ver, "site-packages")
        # Pure-Python: no shared/static libs; expose site-packages to consumers.
        self.cpp_info.libdirs = [site_packages]
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        lib_path = os.path.join(self.package_folder, site_packages)
        self.runenv_info.define("PYTHONPATH", lib_path)
