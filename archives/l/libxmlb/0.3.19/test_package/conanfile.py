#!/usr/bin/env python3
"""Conan test_package for libxmlb 0.3.19.

Consumer-level validation through the pkg-config interface (the way fwupd
consumes libxmlb): builds a small program with dependency('xmlb'), compiles
an inline XML document into a binary silo, runs an XPath query, exports the
silo back to XML and checks the version metadata.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.meson import Meson, MesonToolchain


class LibxmlbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # xmlb.pc Requires gio-2.0; make glib's components resolvable in the
        # consumer graph as well.
        self.requires("glib/2.88.3")

    def layout(self):
        self.folders.build = "builddir"
        self.folders.generators = "builddir/generators"

    def generate(self):
        # Same CI-worker quirk as the main recipe: AR/AS/... exported as
        # llvm-* bare names break meson's tool probing. Resolve a real
        # archiver from PATH and pin it.
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        archiver = (
            shutil.which("llvm-ar")
            or shutil.which("ar")
            or shutil.which("gar")
        )
        if archiver is None:
            raise ConanInvalidConfiguration(
                "No archive tool (llvm-ar/ar/gar) found in PATH"
            )
        tc = MesonToolchain(self)
        tc.ar = archiver
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def test(self):
        if not can_run(self):
            self.output.info("NOT_RUN LIBXMLB_CONSUMER reason=cross_building")
            return
        # 1) Library consumer path: pkg-config('xmlb') linked test program.
        exe = os.path.join(self.build_folder, "test_libxmlb")
        self.run(f'"{exe}"', env="conanrun")
        # 2) CLI path: xb-tool from the installed package, driven through the
        #    conanrun environment (LD_LIBRARY_PATH resolves the shared libs —
        #    the CI L2 smoke runs it bare and skips, which is expected for a
        #    dynamically linked conan CLI). Compile then query a real file so
        #    the tool's code path is exercised end to end with archived output.
        pkg = self.dependencies["libxmlb"].package_folder
        xb_tool = os.path.join(pkg, "bin", "xb-tool")
        src_xml = os.path.join(self.build_folder, "xb-tool-check.xml")
        blob = os.path.join(self.build_folder, "xb-tool-check.xmlb")
        with open(src_xml, "w", encoding="utf-8") as handle:
            handle.write(
                '<?xml version="1.0"?>\n'
                '<components origin="conan">'
                '<component type="desktop">'
                "<id>xb.tool.check</id>"
                "<name>XB Tool Check</name>"
                "</component>"
                "</components>\n"
            )
        self.run(f'"{xb_tool}" compile "{blob}" "{src_xml}"', env="conanrun")
        self.run(f'"{xb_tool}" query "{blob}" "components/component/id"',
                 env="conanrun")
