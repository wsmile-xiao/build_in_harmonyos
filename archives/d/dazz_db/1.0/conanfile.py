#!/usr/bin/env python3
"""Conan recipe for dazz_db — Dazzler database tools (C, raw makefile).

DAZZ_DB (official tag V1.0) stores PacBio/ONT read data in a compressed
"database" (one visible FOO.db stub plus hidden .FOO.idx/.FOO.bps/.FOO.qvs
files) and ships 13 command line tools that build, query, partition, annotate
and export it, plus 3 legacy DBupgrade migration utilities.  Upstream is plain
C with a hand written Makefile and, notably, **no test target**, so every
executed case in test_package is an adaptation side case.

OHOS adaptation:
- the upstream Makefile hardcodes `gcc` in all 16 recipes and the OHOS
  toolchain only provides clang, so 0001 makes the Makefile honour
  CC/CPPFLAGS/CFLAGS/LDFLAGS/LDLIBS;
- the OHOS libc exports `index` but not the BSD legacy `rindex`, which the
  sources call in DB.c and DBshow.c, so 0002 replaces it with POSIX strrchr
  (same root cause as knowledge E570).
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

#  The Makefile's ALL list: 13 command line tools, all installed into bin/.
#  The 3 DBupgrade.* / DUSTupgrade.* targets are one-off legacy DB format
#  migration utilities shipped in the source tree but not part of ALL,
#  matching upstream's default `make` product set.
TOOLS = ("Catrack", "DAM2fasta", "DB2fasta", "DB2quiva", "DBdust", "DBrm",
         "DBshow", "DBsplit", "DBstats", "fasta2DAM", "fasta2DB", "quiva2DB",
         "simulator")

#  Upstream CFLAGS, restated here so the build does not depend on the ambient
#  shell environment (the Makefile keeps them as its own ?= default as well).
UPSTREAM_CFLAGS = "-O3 -Wall -Wextra -fno-strict-aliasing"


class DazzDbConan(ConanFile):
    name = "dazz_db"
    version = "1.0"
    description = ("Dazzler database library: compressed read store for the "
                   "Dazzler assembler with 13 command line tools "
                   "(fasta2DB/DB2fasta/quiva2DB/DB2quiva/DBsplit/DBdust/"
                   "Catrack/DBshow/DBstats/DBrm/simulator/fasta2DAM/DAM2fasta)")
    license = "BSD-3-Clause"
    homepage = "https://github.com/thegenemyers/DAZZ_DB"
    url = "https://github.com/thegenemyers/DAZZ_DB"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        #  V1.0 的 Makefile 全部 16 条规则只链 -lm，不引用 zlib（无
        #  arrow2DB/DB2arrow，也没有任何 zlib API 调用），因此无第三方依赖。
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = Environment()
        cc = self.conf.get("tools.build:compiler_executables", default={}).get("c")
        env.define("CC", cc or "clang")
        env.define("CFLAGS", UPSTREAM_CFLAGS)
        env.vars(self).save_script("conanbuild_dazz_db")

    def build(self):
        apply_conandata_patches(self)
        #  The upstream Makefile builds each tool straight into the source
        #  tree, so the build has to run in the source folder.
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        #  V1.0 tag 无独立 LICENSE 文件：上游把所有许可文本写在 README
        #  顶部的 BSD 版权块里，复制 README 作为许可记录。
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        bindir = os.path.join(self.package_folder, "bin")
        for tool in TOOLS:
            copy(self, tool, src=self.source_folder, dst=bindir,
                 keep_path=False)
        missing = [t for t in TOOLS
                   if not os.path.isfile(os.path.join(bindir, t))]
        if missing:
            raise ConanException("build did not produce: %s" % ", ".join(missing))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []