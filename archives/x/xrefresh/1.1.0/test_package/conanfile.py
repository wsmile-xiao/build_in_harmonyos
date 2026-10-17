#!/usr/bin/env python3
"""Conan test_package — xrefresh 1.1.0

L1 消费者测试：**真实执行被测包里的 xrefresh 二进制**（R34/PF3：不打印字符串、
不空壳）。上游 0 自动化测试用例（实测证据见 MANIFEST.yml 的 upstream_test_audit），
所以断言全部由本包自造，且**声明数 6 ≤ 本机实测数 6**。

为什么这 6 条不需要 X server（都取自 xrefresh.c 里 XOpenDisplay 之前的代码路径，
第 207-259 行）：
  1 -version        → puts(PACKAGE_STRING) + exit(EXIT_SUCCESS)          实测 rc=0
  2 -help           → Syntax(EXIT_SUCCESS) 打印 usage                    实测 rc=0
  3 -v 缩写         → isabbreviation() 的缩写分支                        实测 rc=0
  4 未知参数        → unknown_arg() → Syntax(EXIT_FAILURE)               实测 rc=1
  5 -delay 缺参     → missing_arg() → Syntax(EXIT_FAILURE)               实测 rc=1
  6 无 DISPLAY      → XOpenDisplay 返回 NULL 后干净报错 exit(1)          实测 rc=1
第 6 条是真正的动态链接/运行期断言：它必须解析 libX11.so.6 的 XOpenDisplay 与
XDisplayName 才能打印出 "unable to open display" —— 链接不上就在 loader 阶段
死掉（本机实测过缺 libXdmcp 时是 `Error relocating ... XdmcpWrap: symbol not
found`，rc=127）。同时它证明无头环境下本工具**不挂住**：不可达 DISPLAY=:99 实测
rc=1 且在 20s timeout 之前返回（超时会是 124，超时不当作通过）。

运行期寻库（同族 xeyes 同款处置）：已发布的 libxcb.so.1 的 RUNPATH 写死了构建机
/storage/.../.conan2/p/... 绝对路径，换 CONAN_HOME 即失效，所以
  a) 主配方把 libxcb/libxau/libxdmcp 声明为 run=True 依赖，VirtualRunEnv 会把它们
     的 libdir 注入 LD_LIBRARY_PATH；
  b) 再从依赖包目录取 .so 绝对路径经 LD_PRELOAD 兜底（HMBS [stale_runtime_library]
     口径：loader 可能忽略 LD_LIBRARY_PATH）。
脚本是 POSIX sh 且不用 set -e/-u/pipefail（HMBS [shell_getcwd] + toybox ash 不接受），
执行用 HMBS 注入的 SHELL/CONFIG_SHELL。
"""
import os
import shutil

from conan import ConanFile


class XrefreshTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 运行期闭包显式声明，便于下面取 .so 绝对路径做 LD_PRELOAD 兜底
        # （版本与主配方一致，同一图内不产生冲突）
        self.requires("libx11/6.4.0")
        self.requires("libxcb/1.16")
        self.requires("libxau/1.0.11")
        self.requires("libxdmcp/1.1.5")

    def _find_so(self, dep, soname_prefix):
        """在依赖包目录里找 SONAME 前缀对应的库文件。

        conan 缓存里可能是 libX11.so -> libX11.so.6 -> libX11.so.6.4.0 的符号链接
        链，HMDFS 对 symlink 物化不可靠（E050），故优先返回实体文件。
        """
        hits = []
        for root, _dirs, files in os.walk(dep.package_folder):
            for f in sorted(files):
                if f.startswith(soname_prefix):
                    hits.append(os.path.join(root, f))
        if not hits:
            return None
        for p in hits:
            if not os.path.islink(p):
                return p
        return hits[0]

    def _runtime_preload(self):
        """按依赖序拼 LD_PRELOAD：libXau → libXdmcp → libxcb → libX11。"""
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
        pkg = self.dependencies["xrefresh"]
        xrefresh_bin = os.path.join(pkg.package_folder, "bin", "xrefresh")
        if not os.path.isfile(xrefresh_bin):
            raise RuntimeError(f"packaged binary missing: {xrefresh_bin}")

        shell = (os.environ.get("SHELL") or os.environ.get("CONFIG_SHELL")
                 or shutil.which("sh") or "/bin/sh")
        script = os.path.join(self.source_folder, "test_xrefresh.sh")
        preload = self._runtime_preload()
        self.output.info("test runner shell=%s" % shell)
        self.output.info("runtime LD_PRELOAD=%s" % (preload or "<none>"))
        cmd = f'"{shell}" "{script}" "{xrefresh_bin}" "{preload}"'
        self.run(cmd, env="conanrun")
        # 上游套件审计结论（详见 test_package/MANIFEST.yml upstream_test_audit）：
        # xrefresh 1.1.0 无任何自动化测试——Makefile.am 仅 bin_PROGRAMS +
        # SUBDIRS = man，无 TESTS/check_PROGRAMS/check-local；man/Makefile.am 同；
        # configure 成功后 make -n check 只展开 check-recursive 骨架，
        # 真跑 make check rc=0 且 "Nothing to be done for 'check'"。
        print('HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",'
              '"framework":"none",'
              '"command":"make -n check / make check (both register 0 cases)",'
              '"discovered":0,"executed":0,"passed":0,"failed":0,'
              '"skipped":0,'
              '"reason":"xrefresh 1.1.0 上游无测试套件：Makefile.am/man/Makefile.am '
              '无 TESTS/check_PROGRAMS/check-local；make check 实测 0 用例"}')
