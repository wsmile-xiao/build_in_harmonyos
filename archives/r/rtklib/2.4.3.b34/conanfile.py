#!/usr/bin/env python3
"""Conan recipe — RTKLIB 2.4.3 b34 for OpenHarmony / HarmonyOS PC.

RTKLIB upstream is a **hand-written Makefile project**, not autotools/CMake:
there is no configure step and no top-level makefile.  Every console
application carries its own ``app/consapp/<app>/gcc/makefile`` which re-compiles
``src/*.c`` into private object files and hard-codes ``CC``/``CFLAGS``/
``LDLIBS`` (``LDLIBS`` even points at a Fortran ``iers.a`` that upstream does not
ship for Linux).  ``patches/0001-makefile.patch`` adds the missing top-level
makefile, which is then driven from :meth:`build` with every build variable
passed explicitly on the command line.

Delivered artefacts:

* ``lib/libRTK.a``   — static RTKLIB library, header ``include/rtklib.h``
* ``bin/convbin``    — raw receiver log → RINEX converter
* ``bin/rnx2rtkp``   — RINEX → RTK/PPP post-processing
* ``bin/pos2kml``    — solution file → Google Earth KML
* ``bin/str2str``    — stream server/client/relay
* ``bin/rtkrcv``     — real-time RTK server (console UI)

The Qt GUI applications (``app/qtapp``: rtknavi/rtkplot/srctblbrows/strsvr) and
the Win32 applications (``app/winapp``) are intentionally not built; they need
Qt/Win32 and are out of scope for a headless package.

No external library is required: without ``-DLAPACK``/``-DMKL`` RTKLIB uses its
own matrix routines, and every ``#include`` is a C library header.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class RtklibConan(ConanFile):
    name = "rtklib"
    version = "2.4.3.b34"
    description = (
        "RTKLIB GNSS 定位开源程序包：静态库 libRTK 与命令行工具 "
        "convbin/rnx2rtkp/pos2kml/str2str/rtkrcv（RTK/PPP 后处理与实时解算）"
    )
    license = "BSD-2-Clause"
    homepage = "https://www.rtklib.com/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("gnss", "gps", "rtk", "ppp", "rinex", "rtcm", "positioning")

    # 本包只交付静态库 libRTK.a 与静态链接的命令行工具，不产出共享库，
    # 因此声明 static-library（Conan 的抽象类型 "library" 要求同时声明 shared
    # 选项，而本包没有也不需要有这个选项：RTKLIB 上游就是把 src/*.c 静态链进
    # 每个可执行程序，产出共享库会引入 SONAME/RUNPATH 一类与本平台无关的风险）。
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    # 设备 hnp 工具链目录：profile 的 tools.build:compiler_executables 只给 c/cpp，
    # ar/ranlib 只能靠 which 或这里兜底（R33：不依赖未定义的 shell 环境变量）。
    _HNP_BIN = "/data/service/hnp/bin"

    # 设备 8 核且被多任务共享，而 `tools.build:jobs` 的 Conan **内置默认**是
    # os.cpu_count()（本机实测 20）；工具驱动的 `conan create` 没有 jobs 旋钮，
    # 不夹紧就会开 20 路编译器。这里夹到 2。
    _JOBS_MAX = 2

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # 传统 Makefile 工程是就地构建（源目录 == 构建目录），没有 out-of-tree 支持。
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} is not supported")

    # ── helpers ──────────────────────────────────────────────────────────────
    def _tool(self, key, name):
        """Toolchain path from the Conan conf, with a which()/hnp fallback."""
        exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return exes.get(key) or shutil.which(name) or os.path.join(self._HNP_BIN, name)

    def _jobs(self):
        try:
            requested = int(self.conf.get("tools.build:jobs", default=self._JOBS_MAX))
        except (TypeError, ValueError):
            requested = self._JOBS_MAX
        return max(1, min(requested, self._JOBS_MAX))

    def _cflags(self):
        flags = list(self.conf.get("tools.build:cflags", default=[], check_type=list))
        if not any(str(f).startswith("-O") for f in flags):
            flags.append("-O0" if str(self.settings.build_type) == "Debug" else "-O2")
        if str(self.settings.build_type) == "Debug" and "-g" not in flags:
            flags.append("-g")
        return " ".join(flags)

    # ── build ────────────────────────────────────────────────────────────────
    def build(self):
        apply_conandata_patches(self)

        cc = self._tool("c", "clang")
        ar = self._tool("ar", "llvm-ar")
        ranlib = self._tool("ranlib", "llvm-ranlib")

        # 上游 app/consapp/*/gcc/makefile 的 LDLIBS 指向 lib/iers/gcc/iers.a + -lgfortran
        # （只有定义 -DIERS_MODEL 时才需要，且上游 Linux 侧并不生成该 .a），故这里显式覆盖
        # LDLIBS 为默认构建真正需要的三个库。
        self.run(
            'make -j{jobs} CC="{cc}" AR="{ar}" RANLIB="{ranlib}" CFLAGS="{cflags}" '
            'LDLIBS="-lm -lrt -lpthread"'.format(
                jobs=self._jobs(), cc=cc, ar=ar, ranlib=ranlib, cflags=self._cflags()
            ),
            cwd=self.source_folder,
        )

    def package(self):
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        # 走补丁里新增的 install 规则（mkdir -p + cp -f，不 strip、不改写 RUNPATH，
        # 因此链接器写入的 .codesign 段保持不变）。
        self.run(
            'make install DESTDIR="{}" PREFIX=/'.format(self.package_folder),
            cwd=self.source_folder,
        )

    def package_info(self):
        self.cpp_info.libs = ["RTK"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            # 静态库不自带这些系统库；纯 C 的 RTKLIB 用到 libm，pthread/rt 来自
            # 上游命令行应用的链接行（str2str/rtkrcv 的 LDLIBS）。
            self.cpp_info.system_libs = ["m", "rt", "pthread"]
        self.cpp_info.set_property("cmake_file_name", "rtklib")
        self.cpp_info.set_property("cmake_target_name", "rtklib::rtklib")
