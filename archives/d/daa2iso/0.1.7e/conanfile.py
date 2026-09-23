#!/usr/bin/env python3
"""Conan recipe for daa2iso 0.1.7e — Direct Access Archive (.daa) → ISO 转换工具。

上游是 Luigi Auriemma 的独立小工具（3 个 C 文件，无 configure），
自带 src/Makefile 但只做三件事：编译 LzmaDec.c / tinflate.c / daa2iso.c 再链接。
本配方直接驱动 OHOS clang 完成同样的三步，避免依赖 make 与 Makefile 里的
`-s`（strip）细节，保证在 aarch64-linux-ohos 上可复现。

OHOS 适配要点：
- 纯 C + 标准库（stdio/stdlib/string），无外部依赖；
- 源码取自 Debian pool 的 orig.tar.gz（上游个人站点在 CI worker 上不可达）；
- LzmaDec.c / tinflate.c 是 7-Zip LZMA 与 zlib 解压器的内嵌副本，用 -fcommon
  兼容老式 C 的重复 tentative definition；
- 3 个 TU 一起链接，产物 bin/daa2iso。
"""
import json
import os

from conan import ConanFile
from conan.tools.files import copy, get


class Daa2IsoConan(ConanFile):
    name = "daa2iso"
    version = "0.1.7e"
    description = "Convert Direct Access Archive (.daa) images to ISO"
    license = "GPL-2.0-or-later"
    homepage = "http://aluigi.altervista.org/mytoolz.htm"
    topics = ("daa", "iso", "archive", "converter", "cli")
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        """解析 C 编译器：conf > CC 环境变量 > 裸 clang（R33：不在 self.run 里做 shell 展开）。"""
        compilers = self.conf.get("tools.build:compiler_executables")
        if isinstance(compilers, str):
            try:
                compilers = json.loads(compilers)
            except ValueError:
                compilers = None
        if isinstance(compilers, dict) and compilers.get("c"):
            return compilers["c"]
        return os.environ.get("CC", "clang")

    def build(self):
        cc = self._cc()
        cflags = os.environ.get("CFLAGS", "") + " -O2 -Wall -fcommon"
        src = os.path.join(self.source_folder, "src")
        for obj, cf in (("LzmaDec.o", "LzmaDec.c"), ("tinflate.o", "tinflate.c")):
            self.run(f'cd {src} && {cc} {cflags} -c {cf} -o {obj}')
        self.run(f'cd {src} && {cc} {cflags} daa2iso.c LzmaDec.o tinflate.o -o daa2iso')

    def package(self):
        copy(self, "daa2iso", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "daa2iso.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "daa2iso"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "daa2iso"))
        exe = os.path.join(self.package_folder, "bin", "daa2iso")
        if os.path.isfile(exe):
            os.chmod(exe, 0o755)
