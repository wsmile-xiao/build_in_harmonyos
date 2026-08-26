#!/usr/bin/env python3
"""Conan recipe for libass 0.17.5 on OpenHarmony PC."""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain


class LibassConan(ConanFile):
    name = "libass"
    version = "0.17.5"
    description = "Portable subtitle renderer for the ASS/SSA format (used by mpv)"
    license = "ISC"
    homepage = "https://github.com/libass/libass"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("freetype/2.14.3")
        self.requires("fribidi/1.0.16")
        self.requires("harfbuzz/14.2.0")
        # 用 2.18.1.1 而非 2.18.3：本地验证 2.18.3 的 libfontconfig.so.1 无法加载
        # （Permission denied，同 cairo/cairomm 已合入配方注释记录的 2.18.1 二进制损坏先例，
        #  该例用 2.18.1.1 override 解决）；2.18.1.1 实测可加载
        self.requires("fontconfig/2.18.1.1")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libass only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        source_data = self.conan_data["sources"]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get(
                    self,
                    url=url,
                    sha256=source_data["sha256"],
                    strip_root=True,
                )
                return
            except ConanException as error:
                self.output.warning(f"Failed to download libass source from {url}: {error}")
        raise ConanInvalidConfiguration("Unable to download libass source from all mirrors")

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared"
        # OHOS 无 DirectWrite/CoreText；libunibreak 未发布 → 均裁剪
        tc.project_options["libunibreak"] = "disabled"
        tc.project_options["coretext"] = "disabled"
        tc.project_options["directwrite"] = "disabled"
        # libass 默认构建 static，mpv 链接需要 shared
        tc.generate()
        # PkgConfigDeps 为每个依赖生成 pkg-config 文件（conan 2.29 无 MesonDeps），
        # MesonToolchain 的 pkg_config_path 已指向 generators 目录，
        # 使 meson 的 dependency('freetype2') 等能找到 conan 依赖
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        # fribidi 包 cpp_info.includedirs=["include"] 但头文件在 include/fribidi/
        # 子目录（PkgConfigDeps 生成的 pc 只提供 include 根路径），meson 编译
        # `<fribidi.h>` 找不到；显式补充 fribidi 子目录到 CPATH
        build_env = Environment()
        fribidi = self.dependencies["fribidi"]
        build_env.append(
            "CPATH",
            os.path.join(fribidi.package_folder, "include", "fribidi"),
        )
        # meson 探测 ar 静态链接器失败（native 文件 [binaries] 仅含 c/cpp），
        # 显式设置 AR/RANLIB 环境变量（meson 优先读 AR 环境变量）
        build_env.define("AR", "/data/service/hnp/bin/llvm-ar")
        build_env.define("RANLIB", "/data/service/hnp/bin/llvm-ranlib")
        with build_env.vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()

    def package(self):
        src_dir = self.source_folder

        # Copy shared libraries
        lib_dir = os.path.join(self.build_folder, "libass")
        copy(self, "*.so*", src=lib_dir,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)

        # Copy public headers (ass.h includes ass_types.h, copy both)
        copy(self, "ass.h", src=os.path.join(src_dir, "libass"),
             dst=os.path.join(self.package_folder, "include", "ass"), keep_path=False)
        copy(self, "ass_types.h", src=os.path.join(src_dir, "libass"),
             dst=os.path.join(self.package_folder, "include", "ass"), keep_path=False)

        # Copy pkg-config file
        pc_dir = os.path.join(self.build_folder, "meson-private")
        copy(self, "libass.pc", src=pc_dir,
             dst=os.path.join(self.package_folder, "lib", "pkgconfig"), keep_path=False)

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]

        libass = self.cpp_info.components["ass"]
        libass.libs = ["ass"]
        libass.includedirs = ["include"]
        libass.requires = [
            "freetype::freetype",
            "fribidi::fribidi",
            "harfbuzz::harfbuzz",
            "fontconfig::fontconfig",
        ]
        libass.set_property("cmake_file_name", "libass")
        libass.set_property("cmake_target_name", "libass::ass")
        libass.set_property("pkg_config_name", "libass")
