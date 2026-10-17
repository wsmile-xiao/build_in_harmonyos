#!/usr/bin/env python3
"""Conan recipe — minini 1.5（源码内嵌型 C/C++ INI 库）

minIni 是一个**可移植、可裁剪的 INI 文件读写库**（"mini INI"）：核心只有
`dev/minIni.c` + `dev/minIni.h`，通过一个 "glue" 头文件把文件 I/O 映射到目标
平台（默认 stdio，另有 FatFs/EFSL/CCS/mdd 等嵌入式后端的 glue）。它同时提供
C 与 C++ 两套接口（`ini_gets/ini_getl/ini_getbool/ini_getf/ini_puts/ini_browse`
+ `INIReader` 类），常用于把配置读写嵌进宿主程序。

上游没有构建系统（设计上就是"把 .c 拖进你的工程"），因此本包：

1. **编译出静态库** `libminIni.a`（用 profile 的 `tools.build:compiler_executables`，
   R33）—— 便于直接链接；
2. 同时安装**公开头文件**（`minIni.h` + 各 glue 头）与**可内嵌的源码**
   `share/minini/minIni.c` —— 保留上游"内嵌到宿主工程"的原始用法；
3. 在 `build()` 里**跑上游自带的测试程序** `dev/test.c`（29 条 assert，需要
   `test.ini` / `testplain.ini` 夹具），CI 的原生构建会真跑。

License: Apache-2.0
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

GLUE_HEADERS = ("minGlue.h", "minGlue-stdio.h", "minGlue-FatFs.h", "minGlue-efsl.h",
                "minGlue-ffs.h", "minGlue-ccs.h", "minGlue-mdd.h", "wxMinIni.h")


class MininiConan(ConanFile):
    name = "minini"
    version = "1.5"
    description = ("minIni — portable, configurable INI file reader/writer for "
                   "C and C++ (single-source library with pluggable file I/O glue)")
    license = "Apache-2.0"
    homepage = "https://www.compuphase.com/minini.htm"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("ini", "configuration", "embedded", "cpp")

    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _compiler(self):
        conf = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        return conf.get("c", "cc")

    def _archiver(self):
        return shutil.which("llvm-ar") or shutil.which("ar") or "ar"

    def _fix_tchar_typo(self):
        """上游 1.5 的 `ini_putbool` 声明与实现误用了未定义类型 `TCHAR`
        （其余 API 都是 `mTCHAR`；`minIni.c` 里 `#define TCHAR char` 出现在
        `#include "minIni.h"` 之后，等于没定义）——ANSI/Linux/OHOS 构建整包编不过。
        这里按二进制方式就地改为 `mTCHAR`（保留上游 CRLF 行尾，不引入补丁文件）。"""
        old = b"ini_putbool(const TCHAR *Section, const TCHAR *Key, int Value, const TCHAR *Filename)"
        new = b"ini_putbool(const mTCHAR *Section, const mTCHAR *Key, int Value, const mTCHAR *Filename)"
        for name in ("minIni.h", "minIni.c"):
            path = os.path.join(self.source_folder, "dev", name)
            with open(path, "rb") as handle:
                data = handle.read()
            if old in data:
                with open(path, "wb") as handle:
                    handle.write(data.replace(old, new))

    def build(self):
        apply_conandata_patches(self)
        self._fix_tchar_typo()
        dev = os.path.join(self.source_folder, "dev")
        cc = self._compiler()
        # 静态库：-fPIC 以便被宿主（可能是 .so）链接
        self.run('%s -O2 -fPIC -I"%s" -c "%s/minIni.c" -o minIni.o'
                 % (cc, dev, dev))
        self.run('%s rcs libminIni.a minIni.o' % self._archiver())

        # 上游自带测试程序（dev/test.c，29 条 assert），需要 test.ini/testplain.ini
        # 夹具；assert 失败会 abort → 非零退出码，CI 的 L1c 能看到真实执行痕迹。
        work = os.path.join(self.build_folder, "upstream-test")
        if os.path.isdir(work):
            shutil.rmtree(work)
        shutil.copytree(dev, work)
        self.run('%s -O2 -I"%s" "%s/test.c" "%s/libminIni.a" -o "%s/test_minini"'
                 % (cc, dev, work, self.build_folder, work))
        self.run("./test_minini", cwd=work)

    def package(self):
        dev = os.path.join(self.source_folder, "dev")
        copy(self, "minIni.h", src=dev,
             dst=os.path.join(self.package_folder, "include"))
        for name in GLUE_HEADERS:
            if os.path.isfile(os.path.join(dev, name)):
                copy(self, name, src=dev, dst=os.path.join(self.package_folder, "include"))
        copy(self, "libminIni.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        # 保留上游"把源码内嵌进宿主工程"的用法
        copy(self, "minIni.c", src=dev,
             dst=os.path.join(self.package_folder, "share", "minini"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "NOTICE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["minIni"]
        self.cpp_info.includedirs = ["include"]
        # 内嵌源码位置（消费者可选择编译 share/minini/minIni.c 而不是链接静态库）
        self.cpp_info.resdirs = [os.path.join("share", "minini")]
