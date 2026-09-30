#!/usr/bin/env python3
"""Conan test_package — wmname 0.1 消费者测试。

R34: 真实执行打包产物。设备与 CI worker 均无 X server，故断言上游 wmname.c
的确定性分支，并用链接后 ELF 内的 property 名字面量覆盖 atom 断言（共 12 条）：
  - argc > 2            → "usage: wmname [name] [-v]" + exit 1
  - argc == 2 && -v     → "wmname-0.1, © 2008 Anselm R Garbe" + exit 1
  - XOpenDisplay(0)==NULL → "wmname: cannot open display" + exit 1
  - ELF 内 _NET_WM_NAME / _NET_SUPPORTING_WM_CHECK / UTF8_STRING 字面量
    （2026-09-30 返修：改用 strings|grep 主检 + grep -a 备检的双探测器，
     不再依赖某个 grep 实现对二进制文件的匹配语义；详见 test_wmname.sh 注释）
  - ELF 内出现 libX11 的 DT_NEEDED SONAME（真链 X11）
  - ELF 头为 ELF64 / 小端 / AArch64（od 直读 e_machine）
退出码必须恰为 1（126/127 说明签名失效或依赖库未解析，会当场判失败）。
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class WmnameTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        pkg_bin = None
        for dep in self.dependencies.host.values():
            if dep.ref.name == "wmname":
                bindirs = dep.cpp_info.bindirs or ["bin"]
                bindir = bindirs[0]
                if not os.path.isabs(bindir):
                    bindir = os.path.join(dep.package_folder, bindir)
                pkg_bin = os.path.join(bindir, "wmname")
        if not pkg_bin or not os.path.isfile(pkg_bin):
            raise Exception("wmname binary not found in package bindirs")

        script = os.path.join(self.source_folder, "test_wmname.sh")
        if not os.path.isfile(script):
            raise Exception("test_wmname.sh missing in test_package")
        os.chmod(script, 0o755)

        # OHOS 的默认 sh 不保证能 exec ELF，统一用 bash 承载被测二进制执行
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.isfile(bash):
            bash = "bash"
        work = self.build_folder
        # L0c: 测试逻辑落在 test_wmname.sh（测试源文件），此处实质调用
        self.run(f'{bash} "{script}" "{pkg_bin}" "{work}"', env="conanrun")
        self.output.info("wmname consumer test PASSED "
                         "(signed ELF runs; usage/-v/no-display paths + property literals verified)")
