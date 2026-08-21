#!/usr/bin/env python3
"""Conan recipe for bacula-pgsql 15.0.3 on HarmonyOS PC.

Bacula is an open-source backup suite. bacula-pgsql packages the
PostgreSQL catalog backend (libbaccats-postgresql.so) — built from the
Bacula source tree (src/cats/) with the postgresql driver enabled.

OHOS notes:
- Only the catalog backend is built (no Director/Storage/File daemons,
  no client tools) — configure with the postgresql driver and disable
  the rest to keep the build small and avoid system deps.
- Dependencies: libpq/18.1 (PostgreSQL client lib, published on ohpcd)
  + openssl (Bacula common dep) + zlib.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.build import stdcpp_library


class BaculaPgsqlConan(ConanFile):
    name = "bacula-pgsql"
    version = "15.0.3"
    package_type = "library"
    license = "AGPL-3.0"
    homepage = "https://www.bacula.org"
    url = "https://www.bacula.org"
    description = ("Bacula backup suite — PostgreSQL catalog backend "
                   "(libbaccats-postgresql)")
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    # pg_config_manual.h/pg_config.h（从 PG 18.1 提取，libpq 包未打包）——
    # 需随配方导出到 recipe 缓存（否则 recipe_folder 找不到）
    exports = "pg_include/*"

    def requirements(self):
        self.requires("libpq/18.1")
        self.requires("openssl/3.5.6")

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True)

    def generate(self):
        # 无 CMakeDeps——bacula 用 autotools，直接传 include/lib 路径
        pass

    def build(self):
        libpq = self.dependencies["libpq"]
        openssl = self.dependencies["openssl"]
        # E011 根治（DRAFT-swftools-autotools-hmdfs-2168）：config.status
        # 在**当前目录**生成并直接执行 ./confXXXX/subs1.awk（不走 TMPDIR，
        # 实测 umask/TMPDIR 均无效）——conan 源码目录在 HMDFS，执行位被剥
        # → Permission denied。方案：源码复制到非 HMDFS 目录（本地
        # /data/storage/el2/base/cache 非 HMDFS 可执行）再 configure。
        import shutil
        work = "/data/storage/el2/base/cache/bacula-src"
        shutil.rmtree(work, ignore_errors=True)
        shutil.copytree(self.source_folder, work, symlinks=True)
        # PG 头补齐：libpq 包未打包 pg_config_manual.h/pg_config.h（bacula
        # postgresql.c 需要 NAMEDATALEN/PG_VERSION_NUM）——从 PG 18.1 源码
        # 提取放在配方 pg_include/，复制到构建目录并加 -I
        shutil.copytree(os.path.join(self.recipe_folder, "pg_include"),
                        os.path.join(work, "pg_include"))
        self.run(
            f"env CPPFLAGS=\"-I{work}/pg_include "
            f"-I{libpq.package_folder}/include "
            f"-I{openssl.package_folder}/include\" "
            f"LDFLAGS=\"-L{libpq.package_folder}/lib "
            f"-L{openssl.package_folder}/lib\" "
            f"./configure --build=aarch64-unknown-linux-gnu "
            f"--prefix={self.package_folder} "
            f"--with-postgresql={libpq.package_folder} "
            "--disable-xml --disable-mysql "
            "--disable-sqlite3 --disable-static --without-readline",
            cwd=work,
        )
        # build the catalog backend only (src/cats)
        self.run("make -C src/cats", cwd=work)

    def package(self):
        # 产物在非 HMDFS 构建目录（work）——build() 把源码复制到
        # /data/storage/el2/base/cache/bacula-src 构建（E011 方案）
        work = "/data/storage/el2/base/cache/bacula-src"
        copy(self, "libbaccats*.so*",
             src=os.path.join(work, "src", "cats", ".libs"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", src=os.path.join(work, "src", "cats"),
             dst=os.path.join(self.package_folder, "include", "bacula"))

    def package_info(self):
        self.cpp_info.libs = ["baccats"]
        self.cpp_info.includedirs = ["include"]
