#!/usr/bin/env python3
"""Conan test_package — xgamma 1.0.8

xgamma 是 X11 gamma 调节命令行工具（无对外可链接库），test_xgamma.sh 真实执行
被测二进制的 9 条命令行路径（R34 实质执行被测包）：版本号（-version /
--version）、usage（-help）、非法选项、**gamma 取值域校验（-gamma 0.05 越下界 /
-gamma 99.0 越上界）**、-gamma 与 -rgamma 互斥、-gamma 缺参数、以及裸执行的**只读
查询路径**。前 8 条在 xgamma.c 中均早于第 202 行 XOpenDisplay 返回，故无 X server
也能真跑；第 9 条走源码第 245-249 行 "Not changing gamma, all done" 分支——
**只 XF86VidModeGetGamma 读、永不调用 XF86VidModeSetGamma**，仅在本机无可达 X
server 时执行（断言上游 "unable to open display" + 非 0 退出），有 display 则记
skipped。全部 9 条对真机显示状态零副作用（安全红线，详见 test_xgamma.sh 头部）。

运行期寻库：xgamma 链接 conan 依赖 libXxf86vm/libX11，其 DT_NEEDED 闭包
（libXxf86vm.so.1 → libXext.so.6 + libX11.so.6；libX11.so.6 → libxcb.so.1 +
libXau.so.6；libxcb.so.1 → libXau.so.6 + libXdmcp.so.6）需在加载期解析。
conanrun 环境把各依赖包 libdir 注入 LD_LIBRARY_PATH；按 HMBS
[stale_runtime_library] 诊断，loader 可能忽略 LD_LIBRARY_PATH，故从依赖包取实体
.so 绝对路径经 LD_PRELOAD 注入测试命令（依赖序拼接）。脚本以 HMBS 注入的
SHELL=/bin/sh 执行（HMBS [shell_getcwd]，POSIX sh 兼容，同 xev/xeyes 已过门禁模式）。
"""
import os
import shutil

from conan import ConanFile


class XgammaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _find_so(self, dep, soname_prefix):
        """在依赖包里找 SONAME 前缀对应的实体 .so（HMFS symlink 物化不可靠，
        E050：优先非符号链接实体文件，loader 按其 SONAME 登记效果等价）。"""
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
        """按依赖序拼 LD_PRELOAD：libXau → libXdmcp → libxcb → libX11 →
        libXext → libXxf86vm。"""
        found = []
        for name, prefix in (("libxau", "libXau.so.6"),
                             ("libxdmcp", "libXdmcp.so.6"),
                             ("libxcb", "libxcb.so.1"),
                             ("libx11", "libX11.so.6"),
                             ("libxext", "libXext.so.6"),
                             ("libxxf86vm", "libXxf86vm.so.1")):
            try:
                dep = self.dependencies[name]
            except KeyError:
                continue
            so = self._find_so(dep, prefix)
            if so:
                found.append(so)
        return ":".join(found)

    def test(self):
        dep = self.dependencies["xgamma"]
        xgamma_bin = os.path.join(dep.package_folder, "bin", "xgamma")

        shell = (os.environ.get("SHELL") or os.environ.get("CONFIG_SHELL")
                 or shutil.which("bash") or "/bin/sh")
        script = os.path.join(self.source_folder, "test_xgamma.sh")
        preload = self._runtime_preload()
        if preload:
            self.output.info("runtime LD_PRELOAD=%s" % preload)
        cmd = f'"{shell}" "{script}" "{xgamma_bin}" "{preload}"'
        self.run(cmd, env="conanrun")
        # HMBS_TEST_PACKAGE_RESULT 由 test_xgamma.sh 在真实断言结束后打印。
        # 上游套件审计（详见 test_package/MANIFEST.yml）：xgamma 1.0.8 发布包
        # 无自动化测试——Makefile.am 仅 bin_PROGRAMS + SUBDIRS = man，无
        # TESTS/check_PROGRAMS；Makefile.in 的 check/check-am 只是 automake
        # 样板规则（第 824-825 行），无任何用例；meson.build 无 test()；
        # 源码树无 tests/；xgamma.c 无 assert()。
        print('HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",'
              '"framework":"none",'
              '"command":"make -n check (automake boilerplate only, no TESTS)",'
              '"discovered":0,"executed":0,"passed":0,"failed":0,'
              '"skipped":0,'
              '"reason":"xgamma 1.0.8 上游无测试套件：Makefile.am 无 TESTS/check_PROGRAMS、meson.build 无 test()、源码树无 tests/ 目录、xgamma.c 无 assert()"}')
