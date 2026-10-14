#!/usr/bin/env python3
"""Kamailio db_postgres 模块（db_postgres.so）Conan 配方 — HarmonyOS PC / aarch64。

打包口径（参照 archives/k/kamailio-unixodbc/6.0.6 同族先例）：
  - 取官方 kamailio 6.0.6 源码包全量源码，仅编译打包 db_postgres 模块
  - 不依赖 kamailio 本体包（模块 .so 由 kamailio 运行时 loadmodule 加载）

上游子包口径：Alpine `kamailio-postgres` 子包（pkg/kamailio/alpine/APKBUILD:255
  `_mod_list_postgres="db_postgres"`，postgres() 调 `_db_driver Postgres postgres postgres pgsql`）
  成员即 db_postgres 一个模块；本包交付该模块（外加许可证），与同族 kamailio-* 包一致。

构建体系：kamailio 6.0.6 自带经典 Makefile 体系（src/Makefile + Makefile.defs）
  make cfg     include_modules=db_postgres   → 生成 src/config.mak（探测 aarch64-…-linux-ohos）
  make modules modules=modules/db_postgres   → 产出 src/modules/db_postgres/db_postgres.so

模块 Makefile 的 libpq 探测（src/modules/db_postgres/Makefile）：
  1) `pkg-config --exists libpq` 命中则用其 --cflags/--libs；
  2) 否则 `PGCFG=$(shell which pg_config)` 命中则用 pg_config --includedir/--libdir；
  3) 否则回退 LOCALBASE/SYSBASE 推导（-I$(LOCALBASE)/include -L$(LOCALBASE)/lib -lpq）。
  构建机若存在系统 pkg-config 的 libpq 或 pg_config，会被自动探测注入宿主路径，故显式传
  `LIBPQ_BUILDER=` 与 `PGCFG=`（make 命令行变量优先级高于 Makefile 内部赋值）钉死回退分支，
  并以 LOCALBASE 指向 conan 的 libpq 包目录；同时用 CPATH/LIBRARY_PATH 兜住头/库搜索。
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class KamailioPostgresConan(ConanFile):
    name = "kamailio-postgres"
    version = "6.0.6"
    description = ("Kamailio db_postgres module: SQL database connector using the "
                   "PostgreSQL client library (libpq)")
    license = "GPL-2.0-or-later"
    homepage = "https://www.kamailio.org"
    url = "https://github.com/kamailio/kamailio"

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"{self.ref} supports Linux/OHOS only")

    def requirements(self):
        # db_postgres 只使用 libpq 客户端库（模块 Makefile 探测 libpq / pg_config）
        self.requires("libpq/18.6.1")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        libpq = self.dependencies["libpq"].package_folder
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"

        # R33：编译器与头/库搜索路径全部显式注入，不使用未定义的 shell 变量
        env = Environment()
        env.define("CC", cc)
        env.define("CPATH", f"{libpq}/include")
        env.define("LIBRARY_PATH", f"{libpq}/lib")

        # E525/E074：OHOS SELinux 禁止用户进程创建 FIFO，GNU make jobserver 靠 FIFO
        # 传递令牌 → 固定 -j1（与同族 kamailio-* 配方一致）
        make_vars = f"LOCALBASE={libpq} LIBPQ_BUILDER= PGCFG="
        with env.vars(self).apply():
            self.run(f"make cfg include_modules=db_postgres {make_vars}", cwd=self.source_folder)
            self.run(f"make modules modules=modules/db_postgres -j1 {make_vars}",
                     cwd=self.source_folder)

        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """层 1 上游官方测试真实执行（R51 三步法）。

        清点结论（完整台账见 notes.md 第四节）：官方源码包内 `test/`、`tests/` 目录共
        4 个、文件共 17 个，其中唯一自包含、无需运行中 kamailio 实例的上游测试是
        `utils/kamctl/dbtextdb/dbtextdb_test.py`（上游自带 unittest 入口，3 个用例，
        仅依赖 Python 标准库）。其余 14 个文件分属 janssonrpcc / rtpproxy / tm 模块或为
        纯数据，逐项不可执行原因见 notes.md。db_postgres 模块自身源码目录内无测试源、
        无 check/ctest 目标注册。
        """
        test_dir = os.path.join(self.source_folder, "utils", "kamctl", "dbtextdb")
        self.output.info("upstream_test_command: python3 dbtextdb_test.py -v "
                         "(kamailio-6.0.6/utils/kamctl/dbtextdb, 3 unittest cases)")
        self.run(f'"{sys.executable}" dbtextdb_test.py -v', cwd=test_dir)

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        module_dir = os.path.join(self.source_folder, "src", "modules", "db_postgres")
        copy(self, "db_postgres.so", src=module_dir,
             dst=os.path.join(self.package_folder, "lib", "kamailio", "modules"))

    def package_info(self):
        # 模块由 kamailio 运行时 loadmodule 加载，不作为链接库供消费者使用
        self.cpp_info.libdirs = ["lib/kamailio/modules"]
        self.cpp_info.libs = []
        self.cpp_info.set_property("kamailio_modules_dir", "lib/kamailio/modules")
