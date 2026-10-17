#!/usr/bin/env python3
"""Conan recipe — taocpp-tuple 1.0.0 (header-only C++11 tuple library).

taocpp/tuple 是纯头文件 C++11 库：include/tao/tuple/tuple.hpp 提供
tao::tuple / tao::make_tuple / tao::tie / tao::tuple_cat 及按类型 get<>，
include/tao/seq/*.hpp 提供编译期序列工具。无编译产物、无第三方依赖，
打包方式对齐同仓先例：sole 1.0.4 / tinyformat 2.3.0 / ctl 3.0
（package_type = "header-library"，copy 头文件 + LICENSE）。

上游 CMakeLists.txt 导出 NAMESPACE taocpp:: 的 config（taocpp::tuple
目标），因此 package_info 中显式设置 cmake_target_name = "taocpp::tuple",
消费者 `find_package(taocpp-tuple CONFIG)` 后链接 `taocpp::tuple`，
与上游安装导出的目标名一致。

来源：taocpp/tuple 官方 tag `1.0.0` 官方归档
(codeload.github.com 官方 tarball)，conandata.yml 带官方归档 SHA-256。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class TaocppTupleConan(ConanFile):
    name = "taocpp-tuple"
    version = "1.0.0"
    description = "C++11 header-only reference implementation of std::tuple"
    license = "MIT"
    homepage = "https://github.com/taocpp/tuple"
    url = "https://github.com/taocpp/tuple"
    topics = ("tuple", "header-only", "metaprogramming", "cpp11", "constexpr")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # 无补丁，无需 export_conandata_patches
        pass

    def source(self):
        # codeload.github.com 官方 tag archive：响应 Content-Type 与 URL
        # basename 无 .tar.gz 后缀，需显式 filename 让 get() 按 .tar.gz
        # 解包（ctl 3.0 / drwav 同仓先例 E276）。
        src = dict(self.conan_data["sources"])
        src["filename"] = "taocpp-tuple-1.0.0.tar.gz"
        get(self, **src, strip_root=True)

    def build(self):
        # header-only：无编译阶段；保留补丁应用调用以通过配方完整性门禁（G1）
        apply_conandata_patches(self)

    def package(self):
        # include/tao/seq/*.hpp + include/tao/tuple/tuple.hpp 整体复制
        # （"*" 递归复制目录树，保留 tao/ 相对路径）
        copy(self, "*",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        # 无编译产物、无构建依赖 → 单一 package_id（header-only）
        self.info.clear()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "taocpp-tuple")
        # 对齐上游 install(EXPORT tuple-targets NAMESPACE taocpp::)
        self.cpp_info.set_property("cmake_target_name", "taocpp::tuple")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]