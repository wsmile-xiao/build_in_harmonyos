#!/usr/bin/env python3
"""Conan recipe — libubox 20260222 (OpenWrt C 库 + jshn CLI)."""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class LibuboxConan(ConanFile):
    name = "libubox"
    version = "20260222"
    description = "OpenWrt C utility library (blob/blobmsg, uloop, ustream, runqueue, kvlist, md5, base64, json_script) with jshn JSON shell tool"
    license = "ISC"
    homepage = "https://github.com/openwrt/libubox"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("json-c/0.18")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 上游 PKG_SEARCH_MODULE(JSONC json-c REQUIRED) -> 需要 json-c.pc
        PkgConfigDeps(self).generate()
        # json-c 头文件装在 include/json-c/ 子目录，但 PkgConfigDeps 生成的
        # json-c.pc 的 Cflags 是 -I${includedir} -> 修补为 -I${includedir}/json-c
        pc = os.path.join(self.generators_folder, "json-c.pc")
        if os.path.exists(pc):
            with open(pc, "r", encoding="utf-8") as f:
                data = f.read()
            fixed = data.replace('-I"${includedir}"', '-I"${includedir}/json-c"')
            if fixed != data:
                with open(pc, "w", encoding="utf-8") as f:
                    f.write(fixed)
        tc = CMakeToolchain(self)
        # E092: OHOS 无 CMake 平台模块 -> 映射 Linux
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch))
        tc.variables["BUILD_LUA"] = "OFF"       # OHOS 无 lua（否则 SEND_ERROR）
        tc.variables["BUILD_EXAMPLES"] = "OFF"  # 示例不安装
        # 跳过 install 期 RPATH 改写：CMake 的 RPATH_CHANGE 会重写链接了
        # json-c 的 .so，改写产物 musl loader 无法加载（E074/E046 平台问题）
        tc.cache_variables["CMAKE_SKIP_INSTALL_RPATH"] = "TRUE"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # CMakeToolchain 不注入 PKG_CONFIG_PATH -> 手动加入 PkgConfigDeps 生成目录
        prev = os.environ.get("PKG_CONFIG_PATH", "")
        os.environ["PKG_CONFIG_PATH"] = f"{self.generators_folder}:{prev}".rstrip(":")
        try:
            cmake = CMake(self)
            cmake.configure()
            cmake.build()
        finally:
            if prev:
                os.environ["PKG_CONFIG_PATH"] = prev
            else:
                os.environ.pop("PKG_CONFIG_PATH", None)

    def package(self):
        CMake(self).install()
        # OHOS musl loader 兼容修复：CMake install 期 RPATH_CHANGE 会重写
        # 链接了 json-c 的 .so（libblobmsg_json.so/libjson_script.so），
        # 改写产物 musl loader 无法加载（即使 LD_LIBRARY_PATH 指向也失败，
        # 平台问题，见 notes.md）。用构建产物覆盖安装产物。
        build_dir = os.path.join(self.build_folder, str(self.settings.build_type))
        if not os.path.isdir(build_dir):
            build_dir = self.build_folder
        for name in ("libubox.so", "libblobmsg_json.so", "libjson_script.so", "jshn"):
            hits = glob.glob(os.path.join(build_dir, "**", name), recursive=True)
            if not hits:
                continue
            src = hits[0]
            # 目标目录：.so -> package/lib，可执行 -> package/bin
            sub = "bin" if name == "jshn" else "lib"
            dst = os.path.join(self.package_folder, sub, name)
            if os.path.exists(dst):
                shutil.copy2(src, dst)

    def package_info(self):
        self.cpp_info.libs = ["ubox", "blobmsg_json", "json_script"]
        self.cpp_info.bindirs = ["bin"]          # jshn -> R38 触发 commands.json
