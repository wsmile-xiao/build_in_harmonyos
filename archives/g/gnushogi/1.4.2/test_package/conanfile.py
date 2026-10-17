#!/usr/bin/env python3
"""test_package — 以使用者身份运行 gnushogi 引擎并断言行为.

两条真实行为断言：
1) `gnushogi --version` 退出码 0 且输出版本串；
2) stdin 喂入 "quit" 后引擎打印 "GNU Shogi" 横幅并干净退出（rc=0）。

HMDFS 上 chmod 不生效（E046），conan 打包后二进制 exec 位丢失；先把
签名后的引擎拷到可正常 chmod 的 tmpfs 再执行。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class GnushogiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # R33：不裸用 shell 环境变量；经 Conan conf 获取 C 编译器
            cc_map = self.conf.get("tools.build:compiler_executables",
                                   default={}, check_type=dict)
            cc = cc_map.get("c") or str(self.settings.compiler)
            src = os.path.join(self.source_folder, "consumer.c")
            bin_path = os.path.join(self.build_folder, "consumer")
            self.run(f"{cc} -o {bin_path} {src}", env="conanbuild")
            pkg = self.dependencies["gnushogi"]
            engine_pkg = os.path.join(pkg.package_folder, "bin", "gnushogi")
            # E046/E077：包内 exec 位不可靠，拷到 tmpfs 恢复执行位；
            # HMDFS/ Fuse 按进程映射属主，覆盖旧文件会 EACCES，用唯一名
            scratch = "/data/storage/el2/base/.gnushogi-consumer"
            os.makedirs(scratch, exist_ok=True)
            engine = os.path.join(scratch, f"gnushogi-{os.getpid()}")
            shutil.copyfile(engine_pkg, engine)
            os.chmod(engine, 0o755)
            self.run(f"GNUSHOGI_BIN=\"{engine}\" \"{bin_path}\"", env="conanrun")
