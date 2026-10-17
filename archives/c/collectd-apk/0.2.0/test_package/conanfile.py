#!/usr/bin/env python3
"""collectd-apk test_package — 消费者用例：模拟 collectd 上层加载 apk 插件.

collectd-apk 是 collectd 插件（产物 lib/collectd/apk.so），无对外库 API。
消费者验证模拟 collectd 插件加载器：
  1. apk.so 产物存在（lib/collectd/apk.so）
  2. dlopen 可加载、dlsym 取 collectd 插件必需符号（module_register）
  3. 加载后 dlclose 正常
"""
import os
from conan import ConanFile
from conan.tools.build import can_run


class CollectdApkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            import os
            cc_map = self.conf.get("tools.build:compiler_executables",
                                   default={}) or {}
            cc = cc_map.get("c") or os.environ.get("CC", "clang")
            pkg = self.dependencies["collectd-apk"]

            src = os.path.join(self.source_folder, "src", "test_plugin.c")
            out = os.path.join(self.build_folder, "test_plugin")
            apk_so = os.path.join(pkg.package_folder, "lib", "collectd", "apk.so")

            # 断言 1：产物存在
            self.run(f"test -f {apk_so}")
            # 断言 2/3：dlopen 加载 + dlsym module_register
            # apk.so 的 DT_NEEDED 含 libapk.so.2.14.0，需把 apk-tools 包
            # lib 目录注入 LD_LIBRARY_PATH 才能 dlopen 成功
            apk_lib = os.path.join(
                self.dependencies["apk-tools"].package_folder, "lib")
            # -rdynamic：test_plugin 扮演 collectd 主进程，导出 plugin_log 等
            # 回调 stub 供 apk.so dlopen 时解析
            self.run(
                f"{cc} -o {out} {src} -DAPK_SO_PATH='\"{apk_so}\"' "
                f"-rdynamic -ldl",
                env="conanbuild")
            self.run(
                f"LD_LIBRARY_PATH={apk_lib}:$LD_LIBRARY_PATH {out}",
                env="conanrun")
