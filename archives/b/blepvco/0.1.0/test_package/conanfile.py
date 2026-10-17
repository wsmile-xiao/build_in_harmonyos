#!/usr/bin/env python3
"""Consumer test for blepvco: compile a dlopen host against ladspa.h and
exercise every LADSPA descriptor exported by the packaged blepvco.so."""
import json
import os
import shutil

from conan import ConanFile
from conan.tools.env import VirtualRunEnv


class BlepvcoTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 测试宿主 #include <ladspa.h>（被测包的传递依赖，显式声明为直接
        # 依赖以保证 self.dependencies 可解析）
        self.requires("ladspa-sdk/1.17")

    def generate(self):
        # conanrunenv：默认环境 + 依赖 runenv（ladspa-sdk 的 LADSPA_PATH/PATH）
        VirtualRunEnv(self).generate()

    def _host_cc(self):
        ce = self.conf.get("tools.build:compiler_executables", default=None)
        cc = None
        if ce:
            try:
                data = json.loads(ce) if isinstance(ce, str) else ce
                cc = data.get("c")
            except (ValueError, AttributeError):
                cc = None
        if cc and os.path.isfile(cc) and os.access(cc, os.X_OK):
            return cc
        return shutil.which("clang") or "/data/service/hnp/bin/clang"

    def test(self):
        pkg = self.dependencies["blepvco"].package_folder
        so = os.path.join(pkg, "lib", "ladspa", "blepvco.so")
        if not os.path.isfile(so):
            raise Exception("blepvco.so missing: " + so)
        sdk_inc = os.path.join(
            self.dependencies["ladspa-sdk"].package_folder, "include")
        host_src = os.path.join(self.source_folder, "src", "test_ladspa_host.c")
        build_dir = self.build_folder or self.source_folder
        host_bin = os.path.join(build_dir, "test_ladspa_host")
        # 编译 dlopen 宿主（R33：编译器取自 profile conf，非 shell 环境变量）
        self.run('"{cc}" -I"{inc}" "{src}" -o "{out}" -ldl'.format(
            cc=self._host_cc(), inc=sdk_inc, src=host_src, out=host_bin),
            env="conanbuild")
        # 运行：期望恰好 3 个描述符（Sync-Saw/Rect/Tri-VCO）全部可实例化并 run
        self.run('"{host}" "{so}"'.format(host=host_bin, so=so), env="conanrun")
        self.output.info("blepvco test_package PASS (3 descriptors exercised)")
