#!/usr/bin/env python3
"""Consumer test for the rtklib package.

Three independent checks, none of which can be satisfied by a stub package:

1. ``test_consumer.c`` is configured by CMake through
   ``find_package(rtklib CONFIG REQUIRED)`` (CMakeDeps generated config), so it
   compiles against the **installed** ``include/rtklib.h`` and links the
   **installed** ``lib/libRTK.a``; the resulting binary is executed and its
   19 numeric RTKLIB API assertions decide pass/fail.
2. Every delivered tool is executed in a **bare** environment
   (``env -u LD_LIBRARY_PATH``): the environment Conan injects for ``conanrun``
   otherwise hides a broken/absolute RUNPATH, which only shows up as
   ``rc=127`` in a bare shell.  ``rc==127`` fails the test.
3. An end-to-end data path that uses the package's own runtime behaviour:
   ``pos2kml`` converts the recorded RTKLIB solution file ``smoke.pos`` into
   KML and the KML content (placemark count and the first coordinate) is
   checked.

No display/Qt dependency and no GNSS receiver hardware is involved.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import load


TOOLS = ("convbin", "rnx2rtkp", "pos2kml", "str2str", "rtkrcv")


class RtklibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        ref = self.tested_reference_str
        # 包目录从依赖对象取：CMakeDeps 生成的是 INTERFACE IMPORTED target，
        # 没有 IMPORTED_LOCATION_RELEASE，按它取会恒失败。
        pkg = self.dependencies[ref].package_folder
        bindir = os.path.join(pkg, "bin")

        # ① 库消费者：CMake + find_package(rtklib) 真编真跑
        consumer = os.path.join(self.build_folder, "rtklib_consumer")
        if not os.path.isfile(consumer):
            raise ConanException("CMake consumer binary was not produced: %s" % consumer)
        self.run('env -u LD_LIBRARY_PATH "%s"' % consumer)

        # ② 裸环境 CLI smoke（LD_LIBRARY_PATH 摘掉）：rc==127 表示装载失败
        probe = "; ".join(
            'env -u LD_LIBRARY_PATH "{exe}" -h </dev/null >/dev/null 2>&1; '
            'rc=$?; if [ "$rc" -eq 127 ]; then echo "bare-environment load failed: {name}"; '
            "exit 1; fi".format(exe=os.path.join(bindir, tool), name=tool)
            for tool in TOOLS
        )
        self.run(probe)

        # ③ 端到端数据通路：recorded solution file → KML
        pos_in = os.path.join(self.source_folder, "smoke.pos")
        kml_out = os.path.join(self.build_folder, "smoke.kml")
        self.run(
            'env -u LD_LIBRARY_PATH "{exe}" "{pos}" -o "{kml}"'.format(
                exe=os.path.join(bindir, "pos2kml"), pos=pos_in, kml=kml_out
            )
        )
        kml = load(self, kml_out)
        if "<Placemark>" not in kml:
            raise ConanException("pos2kml: the produced KML contains no Placemark")
        if "139.613829262,35.160867778,0.000" not in kml:
            raise ConanException("pos2kml: the KML is missing the first solution coordinate")
        if kml.count("<Placemark>") != 11:
            raise ConanException(
                "pos2kml: expected 11 Placemark entries, got %d" % kml.count("<Placemark>")
            )
