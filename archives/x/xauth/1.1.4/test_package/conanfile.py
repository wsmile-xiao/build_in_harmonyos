#!/usr/bin/env python3
"""Conan test_package — xauth 1.1.4

L1 test: xauth 是命令行工具（无可链接库），test_xauth.sh 真实执行**已安装的**
`bin/xauth`，覆盖版本输出 + 授权文件的写-读-删全链路（R34：二进制即被测 API）。

运行时寻库（同 xeyes/1.3.1）：libX11.so.6 的 DT_NEEDED 是 libxcb.so.1 与
libXau.so.6，libxcb.so.1 又需要 libXdmcp.so.6。主配方把 libxcb/libxdmcp 声明为
run 依赖（conanrun 环境注入 LD_LIBRARY_PATH），本 conanfile 再按 HMBS
[stale_runtime_library] 的诊断从依赖包取这几个 .so 的**绝对路径**经
LD_PRELOAD 注入测试脚本，双保险。

脚本以 HMBS 注入的 SHELL/CONFIG_SHELL（POSIX sh）执行，不硬编码
/data/service/hnp/bin/bash（HMBS [shell_getcwd]）。
"""
import os
import shutil

from conan import ConanFile


class XauthTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _find_so(self, dep, soname_prefix):
        """在依赖包里找 SONAME 前缀对应的 .so 文件。

        conan 缓存中的库是 .so -> .so.1 -> .so.1.x.y 符号链接链，HMFS 对
        symlink 物化不可靠（E050），优先取实体文件；loader 按 SONAME 登记，
        效果等价。
        """
        hits = []
        for root, _dirs, files in os.walk(dep.package_folder):
            for name in sorted(files):
                if name.startswith(soname_prefix):
                    hits.append(os.path.join(root, name))
        if not hits:
            return None
        for path in hits:
            if not os.path.islink(path):
                return path
        return hits[0]

    def _runtime_preload(self):
        """按依赖序拼接 LD_PRELOAD：libXau → libXdmcp → libxcb → libX11 → libXext。"""
        found = []
        for name, prefix in (
            ("libxau", "libXau.so.6"),
            ("libxdmcp", "libXdmcp.so.6"),
            ("libxcb", "libxcb.so.1"),
            ("libx11", "libX11.so.6"),
            ("libxext", "libXext.so.6"),
        ):
            try:
                dep = self.dependencies[name]
            except KeyError:
                continue
            so = self._find_so(dep, prefix)
            if so:
                found.append(so)
        return ":".join(found)

    def test(self):
        dep = self.dependencies["xauth"]
        binary = os.path.join(dep.package_folder, "bin", "xauth")
        scratch = os.path.join(self.build_folder, "xauth-scratch")
        os.makedirs(scratch, exist_ok=True)

        shell = (
            os.environ.get("SHELL")
            or os.environ.get("CONFIG_SHELL")
            or shutil.which("sh")
            or "/bin/sh"
        )
        script = os.path.join(self.source_folder, "test_xauth.sh")
        preload = self._runtime_preload()
        if preload:
            self.output.info("runtime LD_PRELOAD=%s" % preload)
        self.run(f'"{shell}" "{script}" "{binary}" "{preload}" "{scratch}"',
                 env="conanrun")
        # HMBS_TEST_PACKAGE_RESULT 由 test_xauth.sh 在真实断言结束后打印。
        # 上游套件统计由脚本内联的 make check 结果给出（main recipe build()
        # 实跑 TESTS = test_xauth，5 个 *.script 场景全过）。
