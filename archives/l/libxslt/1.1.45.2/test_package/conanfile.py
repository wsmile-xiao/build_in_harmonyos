#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.build import cross_building


class LibxsltToolTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cc = os.environ.get("CC")
        if not cc:
            compilers = self.conf.get(
                "tools.build:compiler_executables",
                default={},
                check_type=dict,
            )
            cc = compilers.get("c", "cc")
        cflags = " ".join(
            self.conf.get("tools.build:cflags", default=[], check_type=list)
        )
        ldflags = " ".join(
            self.conf.get("tools.build:exelinkflags", default=[], check_type=list)
        )
        includes = []
        libdirs = []
        libs = []
        tested = self.dependencies["libxslt"]
        deps = [tested]
        deps.extend(
            dep
            for _, dep in self.dependencies.items()
            if dep.package_folder != tested.package_folder
        )
        for dep in deps:
            includes.extend(
                '-I"{}"'.format(path) for path in dep.cpp_info.includedirs
            )
            libdirs.extend(
                '-L"{}"'.format(path) for path in dep.cpp_info.libdirs
            )
            libs.extend("-l{}".format(lib) for lib in dep.cpp_info.libs)
            libs.extend("-l{}".format(lib) for lib in dep.cpp_info.system_libs)
        source = os.path.join(self.source_folder, "test.c")
        self.run(
            '"{}" {} {} "{}" -o test_probe {} {} {}'.format(
                cc,
                cflags,
                " ".join(includes),
                source,
                " ".join(libdirs),
                " ".join(libs),
                ldflags,
            ),
        )

    def test(self):
        if not cross_building(self):
            exe = "test_probe.exe" if self.settings.os == "Windows" else "./test_probe"
            self.run(exe, env="conanrun")

        dep = self.dependencies["libxslt"]
        exe = "xsltproc.exe" if self.settings.os == "Windows" else "xsltproc"
        xsltproc = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0], exe)
        if cross_building(self):
            self.output.info("cross-building: xsltproc run test skipped")
            return
        xsl = os.path.join(self.source_folder, "test.xsl")
        xml = os.path.join(self.source_folder, "test.xml")
        self.run('"{}" "{}" "{}" > out.txt'.format(xsltproc, xsl, xml), env="conanrun")
        with open("out.txt", encoding="utf-8") as handle:
            output = handle.read()
        if "morpheus-xslt-ok" not in output:
            raise Exception("xsltproc transformation output mismatch")
