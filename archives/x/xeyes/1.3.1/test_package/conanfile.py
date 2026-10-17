#!/usr/bin/env python3
"""Conan test_package — xeyes 1.3.1

L1 test: xeyes 是 X11 演示程序（无库可链接），test_xeyes.sh 真实执行被测包
二进制 xeyes -version / -help（两路径均在 XtAppInitialize 之前退出，无需
X server 即可验证版本输出与退出码，R34 实质依赖被测包）。

真机演进（第 4 轮根因确认）：bash 5.3.0 能正常执行 ELF，127 的真正原因是
xeyes 链接的预编译栈 libX11.so.6（/usr/local/lib）运行时 DT_NEEDED 需要
libxcb.so.1/libXau.so.6，而真机栈只有 .a 无 .so（xterm/410 笔记同款记录；
xterm test 只验二进制存在未运行故未暴露）。修复：
  1. 主配方 requirements() 增加 libxcb/1.16 + libxau/1.0.11（run=True，
     ohpcd 已发布 OHOS armv8 binary，libxcb 传递依赖 libxdmcp/1.1.5），
     test_package 的 conanrun 环境自动把其 libdir 注入 LD_LIBRARY_PATH；
  2. 按 HMBS [stale_runtime_library] 诊断，loader 可能忽略 LD_LIBRARY_PATH，
     从依赖包文件夹取 libxcb.so.1/libXau.so.6/libXdmcp.so.6 绝对路径，
     经 LD_PRELOAD 注入测试命令（依赖序 libXau → libXdmcp → libxcb）；
  3. 按 HMBS [shell_getcwd] 诊断，用注入的 SHELL/CONFIG_SHELL（/bin/sh）
     执行脚本，不硬编码 /data/service/hnp/bin/bash；脚本为 POSIX sh 兼容
     （xidle 已过门禁同款：toybox ash 拒绝 set -eu，脚本不用 set/pipefail）。
"""
import os
import shutil

from conan import ConanFile


class XeyesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _find_so(self, dep, soname_prefix):
        """在依赖包里找 SONAME 前缀对应的 .so 文件。

        libxcb 的 package_info 用 components（根 cpp_info.libdirs 可能为空），
        因此直接递归扫描整个 package_folder。conan 缓存中的库可能是
        .so -> .so.1 -> .so.1.x.y 符号链接链，HMFS 对 symlink 物化不可靠
        （E050），LD_PRELOAD 优先指向实体文件（如 libxcb.so.1.4）——loader
        按其 SONAME（libxcb.so.1）登记，效果等价；仅当全是 symlink 时才退回
        符号链接路径。
        """
        hits = []
        for root, _dirs, files in os.walk(dep.package_folder):
            for f in sorted(files):
                if f.startswith(soname_prefix):
                    hits.append(os.path.join(root, f))
        if not hits:
            return None
        # 优先非符号链接的实体文件（HMFS symlink 物化不可靠，E050）
        for p in hits:
            if not os.path.islink(p):
                return p
        return hits[0]

    def _runtime_preload(self):
        """xeyes 运行时共享库补齐（conan 依赖 libx11/libxext + 传递依赖）。

        主配方 libX11/libXext 来自 conan 依赖（libx11/6.4.0 + libxext/6.4.0，
        CI #28097 起不再依赖预编译栈——worker 栈可能完全没有 libX11）。
        libX11.so.6 运行时需要 libxcb.so.1 + libXau.so.6（libxcb 自身又链接
        libXau.so.6 / libXdmcp.so.6），libXext.so.6 链接 libX11.so.6。
        依赖序拼接 LD_PRELOAD：libXau → libXdmcp → libxcb → libX11 → libXext。
        """
        found = []
        for name, prefix in (("libxau", "libXau.so.6"),
                             ("libxdmcp", "libXdmcp.so.6"),
                             ("libxcb", "libxcb.so.1"),
                             ("libx11", "libX11.so.6"),
                             ("libxext", "libXext.so.6")):
            try:
                dep = self.dependencies[name]
            except KeyError:
                continue
            so = self._find_so(dep, prefix)
            if so:
                found.append(so)
        return ":".join(found)

    def test(self):
        dep = self.dependencies["xeyes"]
        xeyes_bin = os.path.join(dep.package_folder, "bin", "xeyes")

        # HMBS [shell_getcwd]：HNP bash 在 HMFS 工作目录 getcwd 不可用；
        # 使用 HMBS 注入的 SHELL/CONFIG_SHELL（/bin/sh），不硬编码
        # /data/service/hnp/bin/bash。脚本为 POSIX sh（xidle 同款）。
        shell = (os.environ.get("SHELL") or os.environ.get("CONFIG_SHELL")
                 or shutil.which("bash") or "/bin/sh")
        script = os.path.join(self.source_folder, "test_xeyes.sh")
        # HMBS [stale_runtime_library]：loader 可能忽略 LD_LIBRARY_PATH，
        # 对测试命令用 LD_PRELOAD 指向依赖包中的本次构建共享库（绝对路径）。
        preload = self._runtime_preload()
        if preload:
            self.output.info("runtime LD_PRELOAD=%s" % preload)
        cmd = f'"{shell}" "{script}" "{xeyes_bin}" "{preload}"'
        self.run(cmd, env="conanrun")
        # HMBS_TEST_PACKAGE_RESULT 由 test_xeyes.sh 在真实断言结束后打印
        # （discovered/passedCount 来自脚本内部计数，见脚本尾部）。
        # 上游套件审计结论（详见 test_package/MANIFEST.yml upstream_test_audit）：
        # xeyes 1.3.1 发布包无自动化测试——Makefile.am 仅 bin_PROGRAMS +
        # SUBDIRS = man，无 TESTS/check_PROGRAMS/check-local；meson.build
        # 无 test()；源码树无 tests/ 目录。
        print('HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",'
              '"framework":"none",'
              '"command":"make -n check (no check target)",'
              '"discovered":0,"executed":0,"passed":0,"failed":0,'
              '"skipped":0,'
              '"reason":"xeyes 1.3.1 上游无测试套件：Makefile.am 无 check/TESTS 目标、meson.build 无 test()、源码树无 tests/ 目录"}')
