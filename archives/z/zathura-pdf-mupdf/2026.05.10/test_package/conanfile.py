#!/usr/bin/env python3
"""Test package for zathura-pdf-mupdf — dlopen the plugin and verify ABI."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["zathura-pdf-mupdf"].cpp_info
        if not dep.libdirs:
            raise ConanInvalidConfiguration("No library directories found for zathura-pdf-mupdf dependency")
        so = os.path.join(dep.libdirs[0], "libpdf-mupdf.so")
        if not os.path.isfile(so):
            raise ConanInvalidConfiguration("libpdf-mupdf.so not found at %s" % so)
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = ce.get("c", "clang")
        if self.settings.os in ("Linux", "OHOS"):
            self._linker_libxml2_workaround(cc)
        # -rdynamic exports the zathura_* host API stubs so the plugin's
        # relocations bind when dlopen'd (the test plays the host role)
        self.run(f'{cc} test.c -o test_probe -rdynamic -DTARGET_SO=\\"{so}\\" -ldl')

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only verify compile+link")
            return
        self.run("./test_probe", env="conanrun")

    @staticmethod
    def _linker_libxml2_workaround(cc):
        """Same workaround as the main recipe: the OHOS SDK lld needs
        libxml2.so.16 from the SDK's own lib dir on the loader path."""
        cc_dir = os.path.dirname(os.path.realpath(cc))
        for cand in (os.path.join(cc_dir, "..", "lib"), os.path.join(cc_dir, "lib")):
            libdir = os.path.normpath(cand)
            if os.path.isfile(os.path.join(libdir, "libxml2.so.16")):
                old = os.environ.get("LD_LIBRARY_PATH", "")
                if libdir not in old.split(":"):
                    os.environ["LD_LIBRARY_PATH"] = libdir + (":" + old if old else "")
                return
