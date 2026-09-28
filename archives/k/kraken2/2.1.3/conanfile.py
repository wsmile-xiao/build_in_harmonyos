#!/usr/bin/env python3
"""Conan recipe for kraken2 2.1.3 — taxonomic sequence classification system.

kraken2 使用自研 Makefile 构建（src/Makefile，非 autotools/cmake）：
CXX 命令行覆盖为 OHOS clang++；KRAKEN2_SKIP_FOPENMP 置空关闭 OpenMP
（OHOS 无 OpenMP 运行时，上游 src/omp_hack.cc 提供单线程兜底实现）。
仅 k2mask 工具链接 zlib（gzstream.h 的 gz* API），通过 CPATH/LIBRARY_PATH
注入 conan zlib 依赖的 include/lib 路径。产物为 6 个命令行工具
（无 install 规则，package() 手动拷贝到 bin/）。
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get
from conan.tools.layout import basic_layout


class Kraken2Conan(ConanFile):
    name = "kraken2"
    version = "2.1.3"
    description = "Kraken 2 taxonomic sequence classification system"
    license = "MIT"
    homepage = "https://github.com/DerrickWood/kraken2"
    url = "https://github.com/DerrickWood/kraken2"
    topics = ("bioinformatics", "taxonomy", "classification")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # k2mask 使用 gzstream.h（zlib gz* API）读写 gzip 序列/输出
        self.requires(
            "zlib/1.3.1",
            transitive_headers=True,
            transitive_libs=True,
        )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        cxx = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("cpp", "clang++")
        zlib = self.dependencies["zlib"].package_folder
        env = dict(os.environ)
        env["PATH"] = "/data/service/hnp/bin:/system/bin:/usr/bin:/bin"
        # gzstream.h 需要 zlib.h；k2mask 链接 -lz 需要 libz 路径
        env["CPATH"] = os.path.join(zlib, "include")
        env["LIBRARY_PATH"] = os.path.join(zlib, "lib")
        nproc = os.cpu_count() or 4

        cmd = (
            f"make -C src -j{nproc} "
            f"CXX={cxx} KRAKEN2_SKIP_FOPENMP= "
        )
        r = subprocess.run(cmd, shell=True, cwd=self.source_folder, env=env,
                           capture_output=True, text=True, timeout=900)
        print(r.stdout[-3000:])
        if r.returncode != 0:
            print(r.stderr[-3000:])
            raise ConanException(f"kraken2 make failed: rc={r.returncode}")

    def package(self):
        src = os.path.join(self.source_folder, "src")
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        for prog in ("estimate_capacity", "build_db", "classify",
                     "dump_table", "lookup_accession_numbers", "k2mask"):
            shutil.copy(os.path.join(src, prog), bin_dir)

    def package_info(self):
        self.output.info("kraken2 tools installed: estimate_capacity, "
                         "build_db, classify, dump_table, "
                         "lookup_accession_numbers, k2mask")
