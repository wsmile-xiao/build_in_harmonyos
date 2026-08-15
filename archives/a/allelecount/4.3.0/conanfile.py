#!/usr/bin/env python3
"""Conan recipe for allelecount — NGS allele counting tool (C, htslib-based).

Builds c/bin/alleleCounter via the upstream c/Makefile, linking the
static libhts.a from the htslib conan package.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AllelecountConan(ConanFile):
    name = "allelecount"
    version = "4.3.0"
    description = "NGS copy number support tool: counts allele coverage from BAM/CRAM"
    license = "AGPL-3.0-or-later"
    homepage = "https://github.com/cancerit/alleleCount"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("htslib/1.24-r0")
        # 上游 LIBS=-lhts -lpthread -lz -lbz2 -llzma -lm -ldl;bz2/lzma 静态库来自制品仓
        self.requires("bzip2/1.0.8")
        self.requires("xz/5.6.2")
        # htslib 的 libhts.a(bgzf/cram)依赖 libdeflate 符号,需一并链接
        self.requires("libdeflate/1.25")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # 上游 c/Makefile: 硬编码 CC=gcc(本机无 gcc),HTSLOC 指向 htslib 包,
        # 产物 ./bin/alleleCounter。用 subprocess 执行 make:
        #  - 命令行传 CC=clang 覆盖 Makefile 的 gcc
        #  - prefix=<htslib pkg> 使 JOIN_INCLUDES=-I<prefix>/include 提供头、
        #    CAT_LFLAGS=-L<prefix>/lib 提供静态库路径
        #  - HTSLIB=<pkg>/lib 使 make_htslib_tmp 的 ln -fs 软链 libhts.a 成功
        #  - 只构建 ./bin/alleleCounter(跳过 all 里的 test/runtests.sh,
        #    避免额外测试依赖;removal 目标也跳过)
        import subprocess
        _env = dict(os.environ)
        _tool_paths = ["/data/service/hnp/bin", "/storage/Users/currentUser/usr/local/bin"]
        _env["PATH"] = ":".join(_tool_paths) + ":" + _env.get("PATH", "")
        # CI worker 沙箱 loader 对 lld 的 $ORIGIN RUNPATH 解析失败, 导致
        # lld 启动时加载 libxml2.so.16 失败 (Error loading shared library
        # libxml2.so.16: needed by .../llvm/bin/lld)。显式把 SDK llvm/lib
        # (含正确版本 libxml2.so.16) 加入 LD_LIBRARY_PATH 供 lld 加载。
        _clang_real = os.path.realpath("/data/service/hnp/bin/clang")
        _llvm_lib = os.path.join(os.path.dirname(os.path.dirname(_clang_real)), "lib")
        if os.path.isdir(_llvm_lib):
            _env["LD_LIBRARY_PATH"] = _llvm_lib + ":" + _env.get("LD_LIBRARY_PATH", "")
        hts = self.dependencies["htslib"]
        _hts_pkg = hts.package_folder
        _cc = "clang" if self.settings.compiler == "clang" else "gcc"
        _version = self.version
        _sdk_dir = os.path.join(self.source_folder, "c")
        # bzip2/xz/libdeflate 静态库路径(上游 LIBS=-lbz2 -llzma,htslib 依赖 libdeflate)
        _extra_lib = []
        for _dep in ("bzip2", "xz", "libdeflate"):
            if _dep in self.dependencies:
                _extra_lib.extend(self.dependencies[_dep].cpp_info.libdirs)
        _lflags = "-L{}".format(" -L".join(_extra_lib)) if _extra_lib else ""
        _cmd = ["make", "-j4",
                "CC={} -O3 -DALLELECOUNTER_VERSION='\"{}\"'".format(_cc, _version),
                "prefix={}".format(_hts_pkg),
                "HTSLIB={}/lib".format(_hts_pkg),
                "LFLAGS=-L./htslib_tmp {}".format(_lflags),
                "LIBS=-lhts -lpthread -lz -lbz2 -llzma -lm -ldl -ldeflate",
                "make_bin", "./bin/alleleCounter"]
        _r = subprocess.run(_cmd, cwd=_sdk_dir, env=_env, capture_output=False)
        if _r.returncode != 0:
            raise ConanException("make failed with exit code {}".format(_r.returncode))

    def package(self):
        import shutil
        _bin = os.path.join(self.source_folder, "c", "bin", "alleleCounter")
        if os.path.exists(_bin):
            _dst = os.path.join(self.package_folder, "bin")
            os.makedirs(_dst, exist_ok=True)
            shutil.copy2(_bin, os.path.join(_dst, "alleleCounter"))

    def package_info(self):
        self.output.info("allelecount packaged: bin/alleleCounter")
