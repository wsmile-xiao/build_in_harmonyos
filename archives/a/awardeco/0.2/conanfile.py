#!/usr/bin/env python3
"""Conan recipe for awardeco 0.2 on HarmonyOS PC.

awardeco is an Award BIOS decompiler (decodes/decompresses Award BIOS
flash firmware files). Pure C (~21KB), zero external deps, built with
its own Makefile (src/): gcc awardeco.c awardfnc.o kernel.o
-fpack-struct.

Note: the Makefile targets are one-step (awardeco / awardfnc / kernel
do not chain), so build the .o targets first, then the binary.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get


class AwardecoConan(ConanFile):
    name = "awardeco"
    version = "0.2"
    package_type = "application"
    license = "GPL-2.0"
    homepage = "https://salsa.debian.org/debian/awardeco"
    url = "https://salsa.debian.org/debian/awardeco"
    description = "Award BIOS decompiler (decode BIOS flash firmware)"
    settings = "os", "arch", "compiler", "build_type"

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True)
        # main 签名标准化（byte→int/char**——clang 强制 main 参数类型，
        # 2002 年老代码 K&R 签名）。直接 python 替换（apply_conandata_patches
        # 在 conan 2.29 从 source 目录找 patch 有路径问题，用内联替换最稳）
        cfile = os.path.join(self.source_folder, "src", "awardeco.c")
        src = open(cfile).read()
        src = src.replace(
            "int main(byte argc, byte *argv[])",
            "int main(int argc, char *argv[])",
        )
        open(cfile, "w").write(src)

    def build(self):
        # Makefile recipe 硬编码 gcc（非 $(CC)，make CC= 无效——
        # 实测 'make: gcc: No such file or directory' Error 127）。
        # 方案：创建 gcc→clang 包装目录 + PATH 前缀。
        # 分步 target 不自动串联——先编 .o 再编二进制。
        import shutil
        bindir = "/data/storage/el2/base/cache/awardeco-bin"
        shutil.rmtree(bindir, ignore_errors=True)
        os.makedirs(bindir, exist_ok=True)
        # gcc 包装脚本（非符号链接）：clang -std=gnu89——awardeco 是
        # 2002 年老代码（K&R main 签名），clang 默认标准报 'first
        # parameter of main must be of type int'；Makefile recipe 硬编码
        # gcc 且无 CFLAGS 变量，只能从包装层加 -std=gnu89
        wrapper = (
            "#!/bin/sh\n"
            "exec /data/service/hnp/bin/clang -std=gnu89 \"$@\"\n"
        )
        for name in ("gcc", "cc"):
            wpath = os.path.join(bindir, name)
            with open(wpath, "w") as f:
                f.write(wrapper)
            os.chmod(wpath, 0o755)
        src = os.path.join(self.source_folder, "src")
        self.run(f"env PATH={bindir}:$PATH make awardfnc kernel", cwd=src)
        self.run(f"env PATH={bindir}:$PATH make awardeco", cwd=src)

    def package(self):
        copy(self, "awardeco",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc"))

    def package_info(self):
        self.conf_info.define("user.awardeco:exe", os.path.join(
            self.package_folder, "bin", "awardeco"))
