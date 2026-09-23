#!/usr/bin/env python3
"""Conan test_package — myman 2009-10-30

L1 test: myman 是 X11/文本模式游戏（无库可链接），test_myman.sh 真实执行
被测包二进制 myman -k / -L / -h——三条路径均在显示后端初始化（XCurses
Xinitscr/PDCurses initscr）之前退出：-k 输出内置 MYMANKEYS 字符串
（utils.c:155/218，"Keyboard Map"）后 exit(0)，-L 输出 MYMANLEGALNOTICE，
-h 打印 usage（myman.c 7324 行）。无需 X server 即可验证，R34 实质依赖
被测包（Homebrew formula 同款 -k 测试路径）。

运行期共享库：主配方把内建 vendored X11 库（libICE/libSM/libXt/libXmu 的
.so.6、libXpm.so.4、libXaw.so.7）与 myman 同放 bin/（rpath $ORIGIN），
conanrun 环境把 <pkg>/bin 注入 LD_LIBRARY_PATH；libX11/libXext 来自 conan
依赖（libx11/6.4.0 + libxext/6.4.0），其运行期 DT_NEEDED 需要
libxcb.so.1/libXau.so.6（libxcb 又链接 libXau/libXdmcp）。HMBS
[stale_runtime_library]：loader 可能忽略 LD_LIBRARY_PATH，对测试命令用
LD_PRELOAD 指向依赖包中的 .so 绝对路径（依赖序 libXau → libXdmcp →
libxcb → libX11 → libXext，xeyes 同款）。
"""
import os
import shutil

from conan import ConanFile


class MymanTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _find_so(self, dep, soname_prefix):
        """在依赖包里找 SONAME 前缀对应的 .so 文件（递归扫描整个
        package_folder：libxcb 的 package_info 用 components，根 cpp_info
        libdirs 可能为空）。优先非符号链接的实体文件（HMFS symlink 物化
        不可靠 E050），loader 按 SONAME 登记，效果等价。"""
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
        """myman 运行时共享库补齐（conan 依赖 libx11/libxext + 传递依赖）。"""
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
        dep = self.dependencies["myman"]
        myman_bin = os.path.join(dep.package_folder, "bin", "myman")

        # HMBS [shell_getcwd]：使用注入的 SHELL/CONFIG_SHELL（/bin/sh），
        # 不硬编码 bash；脚本为 POSIX sh（xidle/xeyes 同款）。
        shell = (os.environ.get("SHELL") or os.environ.get("CONFIG_SHELL")
                 or shutil.which("bash") or "/bin/sh")
        script = os.path.join(self.source_folder, "test_myman.sh")
        preload = self._runtime_preload()
        if preload:
            self.output.info("runtime LD_PRELOAD=%s" % preload)
        cmd = f'"{shell}" "{script}" "{myman_bin}" "{preload}"'
        self.run(cmd, env="conanrun")
        # HMBS_TEST_PACKAGE_RESULT 由 test_myman.sh 在真实断言结束后打印。
        # 上游套件审计结论（详见 test_package/MANIFEST.yml upstream_test_audit）：
        # myman 2009-10-30 发布包无自动化测试——根 Makefile 无 test/check 目标、
        # 官方简化构建 simple.mk 无 check、源码树无 tests/ 目录。
        print('HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",'
              '"framework":"none",'
              '"command":"make check (no check target; Makefile/simple.mk 均无 check)",'
              '"discovered":0,"executed":0,"passed":0,"failed":0,'
              '"skipped":0,'
              '"reason":"myman 2009-10-30 上游无测试套件：根 Makefile 与 simple.mk 均无 test/check 目标、源码树无 tests/ 目录"}')
