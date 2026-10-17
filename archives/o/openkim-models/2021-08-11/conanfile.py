#!/usr/bin/env python3
"""Conan recipe for openkim-models 2021-08-11 (pure data package).

openkim-models is the OpenKIM models collection consumed by KIM-API:
34 model-driver source trees (C++ drivers, compiled by kim-api's
collection management on the upstream side), 445 portable-model
parameter sets and 96 simulator-model definitions — 4228 files in
total. This package ships the collection as-is (data + driver sources,
no compilation): kim-api itself is not yet adapted to OHOS, so drivers
cannot be built here; downstream consumers (future kim-api adaptation
or parameter consumers) get the complete collection via the
KIM_MODELS_DIR runenv variable. Debian distributes the same layout
(openkim-models 1:2021.08.11 installs model-drivers/,
portable-models/, simulator-models/ under /usr/share/openkim-models/).

Follows the lebiniou-data/inform6-library pure-data pattern: build() is
an inventory drift check, package() copies the collection tree to
share/openkim-models/, package_id is cleared.

License: CDDL-1.0.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get


class OpenkimModelsConan(ConanFile):
    name = "openkim-models"
    version = "2021-08-11"
    description = ("OpenKIM models collection (34 model drivers + 445 "
                   "portable models + 96 simulator models, 4228 files), "
                   "data package for KIM-API consumers")
    license = "CDDL-1.0"
    homepage = "https://openkim.org"
    url = ""  # CI fills this
    package_type = "unknown"

    # 纯数据/资源包：无编译、无链接，但保留 settings 以满足 CI L0 门禁的
    # 显式 settings 声明要求（与 kicad-demos/lebiniou-data 先例同款）。
    settings = "os", "compiler", "build_type", "arch"

    # 上游发行归档的逐目录文件数（构建期防漂移校验，实测计数；
    # 根目录另有 CMakeLists.txt + LICENSE 两个标记文件）。
    _expected_files = {
        "model-drivers": 415,
        "portable-models": 3108,
        "simulator-models": 703,
    }
    _root_markers = ("CMakeLists.txt", "LICENSE")

    _install_dirs = ("model-drivers", "portable-models", "simulator-models")
    _resource_dir = os.path.join("share", "openkim-models")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        # 配方自足：数据全部经 conandata sources（get）下载，
        # 除 conanfile.py/conandata.yml 外无本地文件需要随配方导出。
        pass

    def build(self):
        apply_conandata_patches(self)  # patches=[] 时为空操作，预留补丁入口
        # 纯数据包无编译步骤。构建期校验上游文件清单，防止下载内容或目录
        # 结构静默漂移（lebiniou-data 先例范式）。只数 3 个安装目录与根
        # 标记文件，conan 在构建目录生成的 *.sh 环境脚本不参与计数。
        for sub, expected in self._expected_files.items():
            path = os.path.join(self.source_folder, sub)
            total = sum(1 for _, _, files in os.walk(path) for f in files)
            if total != expected:
                raise ConanInvalidConfiguration(
                    f"openkim-models 2021-08-11 inventory drift: {sub} has "
                    f"{total} files, expected {expected}"
                )
        for marker in self._root_markers:
            if not os.path.isfile(os.path.join(self.source_folder, marker)):
                raise ConanInvalidConfiguration(
                    f"openkim-models 2021-08-11 inventory drift: missing "
                    f"root file {marker}"
                )

    def package(self):
        # 安装布局与 Debian 一致：/usr/share/openkim-models/ 下放三个
        # 集合目录（含各条目自带 CMakeLists.txt/kimspec.edn——它们是
        # 集合内容的一部分，kim-api-collections-management 需要读取），
        # 根目录的 CMakeLists.txt 与 LICENSE 一并安装。
        for sub in self._install_dirs:
            copy(self, "*", src=os.path.join(self.source_folder, sub),
                 dst=os.path.join(self.package_folder, self._resource_dir,
                                  sub))
        copy(self, "CMakeLists.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, self._resource_dir))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, self._resource_dir))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.resdirs = [self._resource_dir]
        self.cpp_info.libs = []
        self.runenv_info.define_path(
            "KIM_MODELS_DIR",
            os.path.join(self.package_folder, self._resource_dir))

    def package_id(self):
        self.info.clear()
