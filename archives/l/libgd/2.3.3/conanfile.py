#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class LibgdConan(ConanFile):
    name = "libgd"
    version = "2.3.3"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    # library 类型必须声明 shared 选项（conan 2 校验——cattle/sherlock.lv2 先例）
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    # 导出 patches/（apply_conandata_patches 需要——multitail 教训）
    exports_sources = "patches/*"
    # 依赖：libgd 核心图像格式（PNG 需 libpng + zlib——registry 已合入）
    requires = "zlib/1.3.1", "libpng/1.6.39"

    def layout(self):
        basic_layout(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        machine = self._machine(self.settings.arch)
        triplet = f"{machine}-unknown-linux-gnu"
        # --disable-shared --enable-static：静态链接（drill/cattle 先例）；
        # --without-*：禁用 OHOS 无的格式（jpeg/freetype/webp/avif/heif/tiff）
        tc.configure_args.extend(
            ["--disable-shared", "--enable-static", "--without-jpeg",
             "--without-freetype", "--without-webp", "--without-avif",
             "--without-heif", "--without-tiff",
             f"--build={triplet}", f"--host={triplet}"])
        # configure 的依赖检查（-l 链接测试）需要 -L 依赖包路径（alpine 教训：
        # Terminfo not found——extra_ldflags/extra_cflags 指向 zlib/libpng）
        for dep in ("zlib", "libpng"):
            d = self.dependencies[dep]
            tc.extra_ldflags.append(f"-L{os.path.join(d.package_folder, 'lib')}")
            tc.extra_cflags.append(f"-I{os.path.join(d.package_folder, 'include')}")
        tc.generate()
        # 依赖包的 pkg-config 路径（configure 的 pkg-config 检测）
        env = Environment()
        for dep in ("zlib", "libpng"):
            env.append_path("PKG_CONFIG_PATH", os.path.join(
                self.dependencies[dep].package_folder, "lib", "pkgconfig"))
        env.vars(self).save_script("conanbuild_pkgconfig")

    def source(self):
        # 显式 get(strip_root=True)——conan 2 的自动下载不 strip_root——
        # 源码在 libgd-2.3.3/ 子目录（patch 应用找不到 configure——CI #26789）
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        # -j1：OHOS 沙箱不支持 mkfifo（jobserver），并行编译失败（opensp 先例）
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "*.h", dst=os.path.join(self.package_folder, "include"),
             src=os.path.join(self.source_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["gd"]
        self.cpp_info.includedirs = ["include"]

    def _machine(self, arch):
        return {"armv8": "aarch64"}.get(str(arch), str(arch))
