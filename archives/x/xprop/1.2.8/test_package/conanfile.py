#!/usr/bin/env python3
"""Conan test_package — xprop 1.2.8

L1 test: xprop 是 X11 命令行工具（无库可链接），test_xprop.sh 真实执行被测
二进制。★实测口径：xprop 非 Xt 程序，main 在解析任何参数（含 -version/-root）
前先经 dsimple.c Open_Display 连接 X server——dsimple.c L106 XOpenDisplay
失败后 fprintf "unable to open display" 并 exit(1)。本平台无 X server，
两项断言（-version 与 -root）均走上游确定性 no-X 错误路径：真实执行被测
包（动态链接/签名/进入 main/上游错误处理全链路，R34 实质依赖被测包），
不冒充功能级真机验证（not_covered 见 MANIFEST.yml）。

运行期（xeyes 1.3.1 同款）：conan libx11 的 libX11.so.6 运行时 DT_NEEDED
需要 libxcb.so.1/libXau.so.6（libxcb 又链 libXau/libXdmcp）；主配方已以
libxcb/1.16 + libxau/1.0.11（run=True）声明，本测试从依赖包取 .so 绝对
路径按依赖序（libXau → libXdmcp → libxcb → libX11）经 LD_PRELOAD 注入
（HMBS [stale_runtime_library]：loader 可能忽略 LD_LIBRARY_PATH），并以
HMBS 注入的 SHELL（/bin/sh）执行脚本（HMBS [shell_getcwd]，POSIX sh 兼容，
xidle/xeyes 已过门禁同款：toybox ash 拒绝 set -eu，脚本不用 set/pipefail）。
"""
import os
import shutil

from conan import ConanFile


class XpropTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _find_so(self, dep, soname_prefix):
        """在依赖包里找 SONAME 前缀对应的 .so 文件（xeyes 同款）。

        conan 缓存中的库可能是 libX11.so.6 → libX11.so 实体文件名，
        递归扫描整个 package_folder 取首个前缀匹配者。
        """
        target = None
        for root, _dirs, files in os.walk(dep.package_folder):
            for f in files:
                if f.startswith(soname_prefix) and ".so" in f:
                    target = os.path.join(root, f)
                    break
            if target:
                break
        return target

    def _runtime_preload(self):
        """xprop 运行时共享库补齐（依赖序 libXau → libXdmcp → libxcb → libX11）。"""
        found = []
        for name, prefix in (("libxau", "libXau.so.6"),
                             ("libxdmcp", "libXdmcp.so.6"),
                             ("libxcb", "libxcb.so.1"),
                             ("libx11", "libX11.so.6")):
            try:
                dep = self.dependencies[name]
            except KeyError:
                continue
            so = self._find_so(dep, prefix)
            if so:
                found.append(so)
        return ":".join(found)

    def test(self):
        dep = self.dependencies["xprop"]
        xprop_bin = os.path.join(dep.package_folder, "bin", "xprop")

        # HMBS [shell_getcwd]：使用 HMBS 注入的 SHELL/CONFIG_SHELL（/bin/sh）
        shell = (os.environ.get("SHELL") or os.environ.get("CONFIG_SHELL")
                 or shutil.which("bash") or "/bin/sh")
        script = os.path.join(self.source_folder, "test_xprop.sh")
        preload = self._runtime_preload()
        if preload:
            self.output.info("runtime LD_PRELOAD=%s" % preload)
        cmd = f'"{shell}" "{script}" "{xprop_bin}" "{preload}"'
        self.run(cmd, env="conanrun")
        # HMBS_UPSTREAM_TEST_RESULT：上游套件审计结论（详见
        # test_package/MANIFEST.yml upstream_test_audit）：xprop 1.2.8
        # 发布包无自动化测试——Makefile.am 仅 bin_PROGRAMS + man SUBDIRS，
        # 无 TESTS/check_PROGRAMS/check-local；无 meson.build；源码树无
        # tests/ 目录。
        print('HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",'
              '"framework":"none",'
              '"command":"make -n check (no check target)",'
              '"discovered":0,"executed":0,"passed":0,"failed":0,'
              '"skipped":0,'
              '"reason":"xprop 1.2.8 上游无测试套件：Makefile.am 无 check/TESTS 目标、无 meson.build、源码树无 tests/ 目录"}')
