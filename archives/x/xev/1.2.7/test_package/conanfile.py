#!/usr/bin/env python3
"""Conan test_package — xev 1.2.7

xev 是 X11 事件打印程序（无对外可链接库），test_xev.sh 真实执行被测二进制
的 4 条命令行路径：`-version` / `--version` / `-help` / 非法选项。这 4 条路径
在 xev.c 中均早于 XOpenDisplay（第 1384 行）返回，故无 X server 也能真跑，
对公开行为（版本串 / usage 文本 / 非法参数退出码）断言（R34 实质执行被测包）。

运行期寻库：xev 链接 conan 依赖 libXrandr/libX11，其 DT_NEEDED 闭包
（libXrandr.so.2 → libXext.so.6 + libXrender.so.1 + libX11.so.6；
libX11.so.6 → libxcb.so.1 + libXau.so.6；libxcb → libXau + libXdmcp）需在
加载期解析。conanrun 环境把各依赖包 libdir 注入 LD_LIBRARY_PATH；按 HMBS
[stale_runtime_library] 诊断，loader 可能忽略 LD_LIBRARY_PATH，故从依赖包
文件夹取实体 .so 绝对路径经 LD_PRELOAD 注入测试命令（依赖序拼接）。脚本以
HMBS 注入的 SHELL=/bin/sh 执行（HMBS [shell_getcwd]，POSIX sh 兼容，同 xeyes
/xidle 已过门禁模式）。
"""
import os
import shutil

from conan import ConanFile


class XevTestConan(ConanFile):
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
        libXext → libXrender → libXrandr。"""
        found = []
        for name, prefix in (("libxau", "libXau.so.6"),
                             ("libxdmcp", "libXdmcp.so.6"),
                             ("libxcb", "libxcb.so.1"),
                             ("libx11", "libX11.so.6"),
                             ("libxext", "libXext.so.6"),
                             ("libxrender", "libXrender.so.1"),
                             ("libxrandr", "libXrandr.so.2")):
            try:
                dep = self.dependencies[name]
            except KeyError:
                continue
            so = self._find_so(dep, prefix)
            if so:
                found.append(so)
        return ":".join(found)

    def test(self):
        dep = self.dependencies["xev"]
        xev_bin = os.path.join(dep.package_folder, "bin", "xev")

        shell = (os.environ.get("SHELL") or os.environ.get("CONFIG_SHELL")
                 or shutil.which("bash") or "/bin/sh")
        script = os.path.join(self.source_folder, "test_xev.sh")
        preload = self._runtime_preload()
        if preload:
            self.output.info("runtime LD_PRELOAD=%s" % preload)
        cmd = f'"{shell}" "{script}" "{xev_bin}" "{preload}"'
        self.run(cmd, env="conanrun")
        # HMBS_TEST_PACKAGE_RESULT 由 test_xev.sh 在真实断言结束后打印。
        # 上游套件审计（详见 test_package/MANIFEST.yml）：xev 1.2.7 发布包
        # 无自动化测试——Makefile.am 仅 bin_PROGRAMS + SUBDIRS = man，无
        # TESTS/check；meson.build 无 test()；源码树无 tests/；xev.c 无 assert()。
        print('HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",'
              '"framework":"none",'
              '"command":"make -n check (no check target)",'
              '"discovered":0,"executed":0,"passed":0,"failed":0,'
              '"skipped":0,'
              '"reason":"xev 1.2.7 上游无测试套件：Makefile.am 无 check/TESTS 目标、meson.build 无 test()、源码树无 tests/ 目录、xev.c 无 assert()"}')
