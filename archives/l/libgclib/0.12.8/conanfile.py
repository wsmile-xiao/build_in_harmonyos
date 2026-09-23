#!/usr/bin/env python3
"""Conan recipe for libgclib (gclib) 0.12.8 (gpertea/gclib) on OpenHarmony PC.

gclib 是 GPertea 的通用 C++ 工具库（GStr/GArgs/GList/GHash/FASTA 解析/线程
封装/内存采样/密码子表），是 GFFread、StringTie 等基因组工具的共同底座。

**上游没有"库"这个产物**：仓库根只有一份手写 Makefile，
`all:` 只编出基准程序 `htest`，`OBJS := GBase.o GStr.o GArgs.o GResUsage.o`
是给下游把 .o 直接链进自己程序用的用法 —— 既没有 `install:` 规则，也没有
任何归档/链接目标。所以本包必须自己定义"库"的边界。

OHOS 适配要点：
- **上游 release tarball 编不全**：22 个 .cpp 里
  `GBam.cpp` 需要 htslib 的 `kstring.h`/`sam.h`/`bam.h`、
  `gdimg.cpp` 需要 libgd 的 `gd.h`、
  `gff.cpp` 需要 boost 的 `boost/crc.hpp` —— 三者都不随包发布。
  另有 `htest.cpp`/`mdtest.cpp`/`gtest.cpp` 三个带 `main()` 的演示程序。
  本包只编译剩下的 **16 个库翻译单元**。
- **发运集合 = 已编译 TU 的 include 闭包**：package() 只装这 16 个 TU 的
  quoted-include 闭包（24 个头文件），因此**每个被发运的头都在 build() 里
  真实编译过**，不存在"发运了却编不过"的头。被排除的 6 个头
  （GBam.h / gdimg.h / gff.h / GBitVec.h / GIntHash.hh / GIntervalTree.hh）
  连同理由写在 notes.md。
- **上游 Makefile 的编译期开关**：`BASEFLAGS` 带 `-D_REENTRANT`
  `-fno-exceptions` `-fno-rtti`（gclib 全库零 `throw`、零 `dynamic_cast`/
  `typeid`，这两个开关只影响异常表与 RTTI 元数据的生成）。`-Wall -Wextra`
  是诊断项，不影响产物，本包不施加。前三个（除 `_REENTRANT` 之外的两个
  开关）经 `cpp_info.cxxflags` 发布给消费者 —— 模板在两侧都实例化，开关
  必须一致。
- **一个必须打的补丁**：`GList.hh` 移动构造的声明（`:101`）没有 `noexcept`
  而定义（`:375`）有。上游永远按 `-std=c++11 -fno-exceptions` 编，clang 在
  该组合下跳过异常规格等价性检查；OHOS 消费者默认 `-std=c++17`，此时
  `noexcept` 已是函数类型的一部分，直接报
  `exception specification in declaration does not match previous declaration`。
  `patches/0001-glist-move-ctor-noexcept-declaration.patch` 把声明补成
  `noexcept`，与定义一致。
- **`ENABLE_COMPRESSION` 默认关闭**：`GCdbYank.h` 的 `<zlib.h>` 与整个
  `GCdbZFasta` 类都在 `#ifdef ENABLE_COMPRESSION` 里，上游 Makefile 未定义
  它 —— 所以本包**零第三方依赖**（打开该宏才会引入 zlib）。
- **上游 Makefile 无 install 规则**：package() 自己拷头文件与库文件。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get, patch
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class LibGclibConan(ConanFile):
    name = "libgclib"
    version = "0.12.8"
    description = "General purpose C++ utility library from the GFF utilities suite (GStr/GArgs/GList/FASTA parsing/threads)"
    license = "MIT"
    homepage = "https://github.com/gpertea/gclib"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("genomics", "fasta", "utility", "containers", "cpp11")

    package_type = "library"

    # patches/ 里的补丁经 export_sources 随配方导出，在 source() 里应用；
    # 见 patches/0001-glist-move-ctor-noexcept-declaration.patch 的头部说明。
    exports_sources = "patches/*"

    settings = "os", "arch", "compiler", "build_type"

    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    # 22 个上游 .cpp 减去 3 个不可编译的（GBam / gdimg / gff，各自缺一个
    # 未随包发布的外部头）再减去 3 个带 main() 的演示程序（htest 是基准
    # 程序、mdtest/gtest 是手工演示），得到 16 个库翻译单元。
    _LIB_TUS = (
        "GBase", "GStr", "GArgs", "GResUsage", "GThreads",
        "gcdb", "GCdbYank", "gsocket", "gstopwatch", "proc_mem",
        "codons", "gdna", "GAlnExtend", "GFastaIndex", "GFaSeqGet", "GapAssem",
    )

    # 上面 16 个 TU 的 quoted-include 闭包（去重后 24 个头文件）。
    # 注：`#include "config.h"`（GBase.h，受 HAVE_CONFIG_H 守卫）、
    # `"windows.h"`/`"psapi.h"`（proc_mem.cpp，受 _WIN32 守卫）在源码树里
    # 并不存在，不计入。
    _PUBLIC_HEADERS = (
        "GBase.h", "GStr.h", "GArgs.h", "GResUsage.h", "GThreads.h",
        "gcdb.h", "GCdbYank.h", "gsocket.h", "gstopwatch.h", "proc_mem.h",
        "codons.h", "gdna.h", "GAlnExtend.h", "GFastaIndex.h", "GFaSeqGet.h",
        "GapAssem.h", "GFastaFile.h",
        "GList.hh", "GVec.hh", "GHash.hh", "GHashMap.hh",
        "khashl.hh", "wyhash.h", "xxhash.h",
    )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # 上游只按 -std=c++11 编过，`GList.hh` 的移动构造声明/定义异常规格
        # 不一致（`:101` 无 noexcept、`:375` 有）；C++11 下 clang 放过、C++17
        # 下是硬错误，而 OHOS 消费者默认 c++17。补丁只改声明一侧，见
        # patches/0001-glist-move-ctor-noexcept-declaration.patch。
        patch(
            self,
            patch_file="patches/0001-glist-move-ctor-noexcept-declaration.patch",
            base_path=self.source_folder,
        )

    # -- build ---------------------------------------------------------------

    def build(self):
        src = self.source_folder
        bld = self.build_folder
        # 编译器一律取自 Conan conf（字典形式），不依赖 shell 变量；
        # OHOS profile 里给的是 /data/service/hnp/bin/clang++。
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compilers.get("cpp", "clang++")
        ar = compilers.get("ar", "llvm-ar")

        fpic = "-fPIC" if self.options.fPIC else ""
        # 上游 Makefile 的 BASEFLAGS（-std=c++11 -D_REENTRANT
        # -fno-exceptions -fno-rtti）加上固定的优化档。
        flags = "-std=c++11 -D_REENTRANT -fno-exceptions -fno-rtti -O2"

        objs = []
        for tu in self._LIB_TUS:
            obj = os.path.join(bld, tu + ".o")
            self.run(
                '"{}" {} {} -I"{}" -c "{}" -o "{}"'.format(
                    cxx, flags, fpic, src, os.path.join(src, tu + ".cpp"), obj
                ),
                cwd=bld,
            )
            objs.append('"{}"'.format(obj))

        if self.options.shared:
            self.run(
                '"{}" -shared -pthread -Wl,-soname,libgclib.so -o "{}" {}'.format(
                    cxx, os.path.join(bld, "libgclib.so"), " ".join(objs)
                ),
                cwd=bld,
            )
        else:
            self.run(
                '"{}" rcs "{}" {}'.format(
                    ar, os.path.join(bld, "libgclib.a"), " ".join(objs)
                ),
                cwd=bld,
            )

    # -- package -------------------------------------------------------------

    def package(self):
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

        libdir = os.path.join(self.package_folder, "lib")
        libname = "libgclib.so" if self.options.shared else "libgclib.a"
        copy(self, libname, src=self.build_folder, dst=libdir, keep_path=False)
        # copy() 匹配不到文件时是静默的 —— 显式点数，避免上游改名后
        # 悄悄发一个空包（"绿但空转"防护）。
        if not os.path.isfile(os.path.join(libdir, libname)):
            raise ConanException("build did not produce {}".format(libname))

        incdir = os.path.join(self.package_folder, "include")
        for header in self._PUBLIC_HEADERS:
            copy(self, header, src=self.source_folder, dst=incdir, keep_path=False)
        staged = len(os.listdir(incdir)) if os.path.isdir(incdir) else 0
        if staged != len(self._PUBLIC_HEADERS):
            raise ConanException(
                "header staging mismatch: expected {} files, staged {}".format(
                    len(self._PUBLIC_HEADERS), staged
                )
            )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libgclib")
        self.cpp_info.set_property("cmake_target_name", "libgclib::libgclib")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["gclib"]
        # -fno-exceptions / -fno-rtti 是**接口级**要求，不是本包自选的优化档：
        # 上游 Makefile 的 BASEFLAGS 就带这两个开关，16 个 TU 全部按它编；
        # 而 gclib 是模板密集库，`GList<OBJ>`/`GVec<OBJ>`/`GHash<...>` 这些
        # 模板**同时**在库的 16 个 TU 里和消费者的 TU 里实例化，两侧的
        # 异常表/RTTI 元数据生成必须一致，否则同一实体在不同 TU 里有两份
        # 语义不同的定义（ODR）。所以这两个开关必须随 cpp_info 发布，
        # 而不是靠消费者自己猜。
        #
        # （注：`GList.hh` 声明/定义异常规格不一致是**另一个**问题，已在
        # source() 用补丁修掉 —— `-fno-exceptions` 只能在 C++11 下豁免该
        # 诊断，C++17 下 noexcept 已是函数类型的一部分，豁免不了。）
        self.cpp_info.cxxflags = ["-fno-exceptions", "-fno-rtti"]
