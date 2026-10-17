#!/usr/bin/env python3
"""Conan recipe for gd 2.3.3 — Autotools (configure + make + libtool).

GD Graphics Library (libgd). Required deps: zlib (static) + libpng (shared).
Optional deps (freetype/libjpeg-turbo/webp/heif/avif/tiff/fontconfig/xpm)
are disabled — not needed for core PNG/GIF/BMP functionality.
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class GdConan(ConanFile):
    name = "gd"
    version = "2.3.3"
    description = "Open-source image processing library supporting PNG, JPEG, GIF, WebP and more"
    license = "MIT-like"
    homepage = "https://libgd.github.io/"
    url = "https://github.com/libgd/libgd"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        self.requires("libpng/1.6.58")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--prefix=/")
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        # 可选依赖全部禁用（不影响核心 PNG/GIF 功能）
        tc.configure_args.extend(["--without-freetype", "--without-jpeg"])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E011: HMDFS UID 映射导致 umask 077 创建的 0700 临时目录对进程不可写，
        # configure/config.status 的 mktemp -d "./confXXXXXX" 失败 → 改为 umask 022。
        for _cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))

        autotools = Autotools(self)
        # gd 的 configure 用 PKG_CHECK_MODULES 探测 zlib/libpng，
        # 需把 PkgConfigDeps 生成的 .pc 目录加入 PKG_CONFIG_PATH。
        prev_pkg_config_path = os.environ.get("PKG_CONFIG_PATH", "")
        os.environ["PKG_CONFIG_PATH"] = (
            f"{self.generators_folder}:{prev_pkg_config_path}"
        ).rstrip(":")
        # libpng 为共享库：configure 的 conftest 运行期需能加载 libpng16.so.16，
        # 把依赖库目录注入 LD_LIBRARY_PATH，否则报 "cannot run C compiled programs"。
        prev_ld_library_path = os.environ.get("LD_LIBRARY_PATH", "")
        dep_lib_dirs = []
        for _dep in self.dependencies.values():
            for _d in _dep.cpp_info.libdirs:
                dep_lib_dirs.append(os.path.join(_dep.package_folder, _d))
        os.environ["LD_LIBRARY_PATH"] = (
            ":".join(dep_lib_dirs + [prev_ld_library_path]).rstrip(":")
            if dep_lib_dirs
            else prev_ld_library_path
        )
        try:
            autotools.configure()
        finally:
            if prev_pkg_config_path:
                os.environ["PKG_CONFIG_PATH"] = prev_pkg_config_path
            else:
                os.environ.pop("PKG_CONFIG_PATH", None)
            if prev_ld_library_path:
                os.environ["LD_LIBRARY_PATH"] = prev_ld_library_path
            else:
                os.environ.pop("LD_LIBRARY_PATH", None)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["gd"]
        self.cpp_info.bindirs = ["bin"]  # gd 安装 11 个 CLI 工具到 bin/（R38）
        self.cpp_info.set_property("pkg_config_name", "gdlib")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
