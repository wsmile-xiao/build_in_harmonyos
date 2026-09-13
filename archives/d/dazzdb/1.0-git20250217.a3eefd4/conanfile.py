#!/usr/bin/env python3
"""Conan recipe for dazzdb — the Dazzler database library (C, raw makefile).

DAZZ_DB stores PacBio/ONT read data in a compressed "database" (one visible
FOO.db stub plus hidden .FOO.idx/.FOO.bps/.FOO.qvs/.FOO.arw files) and ships 21
command line tools that build, query, partition, annotate and export it.
Upstream is plain C with a hand written Makefile and, notably, **no test
target**, so every executed case in test_package is an adaptation side case.

OHOS adaptation:
- the upstream Makefile hardcodes `gcc` in all 21 recipes and the OHOS
  toolchain only provides clang, so 0001 makes the Makefile honour
  CC/CPPFLAGS/CFLAGS/LDFLAGS/LDLIBS;
- the OHOS libc exports `index` but not the BSD legacy `rindex`, which the
  sources call in three files (0002 replaces it with POSIX strrchr);
- ONElib.c hardcodes `/tmp` for its schema scratch files while `/tmp` is a
  read only mount on OHOS, so every ONElib based tool died with EROFS
  (0003 probes a writable scratch directory at run time);
- three additional upstream defects are fixed in 0004-0006 (see patches/).
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

#  The Makefile's ALL list: 21 command line tools, all installed into bin/.
TOOLS = ("Catrack", "DAM2fasta", "DB2ONE", "DB2arrow", "DB2fasta", "DB2quiva",
         "DBcp", "DBdust", "DBmv", "DBrm", "DBshow", "DBsplit", "DBstats",
         "DBtrim", "DBwipe", "arrow2DB", "fasta2DAM", "fasta2DB", "quiva2DB",
         "rangen", "simulator")

#  Upstream CFLAGS, restated here so the build does not depend on the ambient
#  shell environment (the Makefile keeps them as its own ?= default as well).
UPSTREAM_CFLAGS = "-O3 -Wall -Wextra -Wno-unused-result -fno-strict-aliasing"


class DazzdbConan(ConanFile):
    name = "dazzdb"
    version = "1.0-git20250217.a3eefd4"
    description = ("Dazzler database library: compressed read store for the "
                   "Dazzler assembler with 21 command line tools")
    license = "BSD-3-Clause"
    homepage = "https://github.com/thegenemyers/DAZZ_DB"
    url = "https://github.com/thegenemyers/DAZZ_DB"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        #  The upstream Makefile links -lz for arrow2DB/DB2arrow.  This version's
        #  sources neither include <zlib.h> nor call any zlib entry point, so the
        #  dependency is link time only: it makes -lz resolve to the package's
        #  static libz.a instead of the OHOS sysroot stub libz.so, which keeps a
        #  needless DT_NEEDED entry out of the produced binaries.
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = Environment()
        cc = self.conf.get("tools.build:compiler_executables", default={}).get("c")
        env.define("CC", cc or "clang")
        env.define("CFLAGS", UPSTREAM_CFLAGS)

        zlib = self.dependencies["zlib"]
        env.append("CPPFLAGS", "-I%s" % zlib.cpp_info.includedirs[0])
        env.append("LDFLAGS", "-L%s" % zlib.cpp_info.libdirs[0])

        env.vars(self).save_script("conanbuild_dazzdb")

    def build(self):
        apply_conandata_patches(self)
        #  The upstream Makefile builds each tool straight into the source
        #  tree, so the build has to run in the source folder.
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
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
