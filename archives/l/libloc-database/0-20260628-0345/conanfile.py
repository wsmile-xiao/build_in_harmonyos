#!/usr/bin/env python3
"""Conan recipe — libloc-database 0-20260628-0345 (pure data package).

IPFire Location Database：IP 地理位置查询库 libloc 使用的编译后数据库
（location.db，48,930,795 字节，格式版本 1）。

适配要点：
  * 纯数据包：无构建系统、无编译产物、无上游自动化测试
    （Debian 打包 Architecture: all，仅有 debhelper-compat 打包依赖）。
  * 源码取值：上游发布物 location-2026-06-28-03:45.db.xz 托管在
    location.ipfire.org（CI Worker 不可达），故改用 Debian 官方源码包
    （orig.tar.xz，内含同一份 location.db）的权威镜像源；无论取自哪个
    源，打包前都用固定的 size+SHA256 校验产物身份（见 DB_* 常量）。
  * 该源码包是 tar.xz 归档（内含 <top>/location.db），package() 用
    tarfile 流式提取该成员，不落中间文件、不整包解压。
  * 安装路径与 Debian 官方二进制包一致：
    share/libloc-location/location.db（libloc 库的数据库查找目录）。
"""
import hashlib
import os
import shutil
import tarfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, download,
                               export_conandata_patches)
from conan.tools.layout import basic_layout

# 解压后 location.db 的权威属性（与上游发布物一一对应，用于打包期校验）
DB_SIZE_BYTES = 48930795
DB_SHA256 = "819748dd33a18aecbbce624bc10b0b685cb292e95377bb2b434665b5afc69ffd"


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class LiblocDatabaseConan(ConanFile):
    name = "libloc-database"
    version = "0-20260628-0345"
    description = ("IPFire Location Database — compiled location.db "
                   "consumed by the libloc IP geolocation library")
    license = "CC-BY-NC-SA-4.0"
    homepage = "https://location.ipfire.org/databases/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 纯数据包：Conan 无 data 类型，既非 library 也非 application
    # → 取 unknown（Conan 2.x 合法取值；仓库同类数据包/资源包先例一致）
    package_type = "unknown"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        sources = self.conan_data["sources"]
        # url 为权威镜像列表；download() 逐个尝试并校验归档的 sha256
        download(self, url=sources["url"], sha256=sources["sha256"],
                 filename=sources["filename"])

    def build(self):
        # 纯数据包：无编译步骤，仅应用补丁（当前无补丁）
        apply_conandata_patches(self)

    def package(self):
        archive = os.path.join(self.source_folder,
                               self.conan_data["sources"]["filename"])
        dst_dir = os.path.join(self.package_folder, "share", "libloc-location")
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, "location.db")

        # 从 tar.xz 中流式提取 <top>/location.db
        with tarfile.open(archive, "r:xz") as tf:
            member = next((m for m in tf.getmembers()
                           if m.isfile()
                           and os.path.basename(m.name) == "location.db"), None)
            if member is None:
                raise ConanException(f"location.db not found inside {archive}")
            src = tf.extractfile(member)
            with open(dst, "wb") as f_out:
                shutil.copyfileobj(src, f_out)

        size = os.path.getsize(dst)
        digest = _sha256(dst)
        if size != DB_SIZE_BYTES or digest != DB_SHA256:
            raise ConanException(
                "location.db integrity check failed: "
                f"size={size} (expected {DB_SIZE_BYTES}), "
                f"sha256={digest} (expected {DB_SHA256})")
        self.output.info(f"location.db installed: {size} bytes, sha256={digest}")

    def package_id(self):
        # 纯数据包：与平台/编译器无关，所有配置共享同一个 package_id
        self.info.clear()

    def package_info(self):
        # 纯数据包：无 include/lib/bin 产物，三个目录显式置空（不伪装成库或工具）
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
        # 数据实际安装位置（与 Debian 官方包一致）：share/libloc-location/location.db
        self.cpp_info.resdirs = ["share/libloc-location"]
