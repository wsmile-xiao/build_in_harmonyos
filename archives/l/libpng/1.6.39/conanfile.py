#!/usr/bin/env python3
import os
from conan import ConanFile
# 必须用 conan.tools.gnu（非 conan.tools.autotools）——CI conan 环境无
# conan.tools.autotools 模块（libgd #19569 教训）
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class LibpngConan(ConanFile):
    name = "libpng"
    version = "1.6.39"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    # library 类型必须声明 shared 选项（conan 2 校验——cattle/sherlock.lv2 先例）
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    # 依赖：zlib（libpng 的压缩库——registry 已合入 zlib/1.3.1）
    requires = "zlib/1.3.1"
    exports_sources = "patches/*"

    def layout(self):
        basic_layout(self)

    def source(self):
        # 剥离顶层目录（sourceforge tarball 解压带 libpng-1.6.39/ 顶层——
        # configure 在子目录——strip_root 到 source_folder 顶层——
        # abduco/progress 教训）
        # 取当前版本的 url/sha256（conandata 的 sources 带版本键——
        # self.conan_data["sources"] 是 {"1.6.39": {...}}——直接解包
        # 会把版本键当关键字参数【CI #22760 实测 TypeError】——
        # 需 [self.version] 取当前版本条目）
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        machine = self._machine(self.settings.arch)
        triplet = f"{machine}-unknown-linux-gnu"
        # --disable-shared --enable-static：静态链接（drill/cattle 先例）；
        # --build/--host 三元组（config.guess 无法识别 HarmonyOS）
        tc.configure_args.extend(
            ["--disable-shared", "--enable-static",
             f"--build={triplet}", f"--host={triplet}"])
        # zlib 依赖：configure 检查 zlibVersion in -lz（AC_CHECK_LIB）——
        # extra_ldflags -L zlib 包 lib（链接测试）+ 编译 -I zlib include
        zlib = self.dependencies["zlib"]
        tc.extra_ldflags.append(f"-L{os.path.join(zlib.package_folder, 'lib')}")
        tc.extra_cflags.append(f"-I{os.path.join(zlib.package_folder, 'include')}")
        tc.generate()

    def build(self):
        # OHOS 沙箱 umask 077 创建的 0700 目录不可写（config.status 等
        # autotools 临时目录 Permission denied——fizmo #21434 教训），
        # 构建前改 umask 022
        old = os.umask(0o022)
        try:
            autotools = Autotools(self)
            autotools.configure()
            # -j1：OHOS 沙箱不支持 mkfifo（jobserver），并行编译失败（opensp 先例）
            autotools.make(args=["-j1"])
        finally:
            os.umask(old)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["png"]
        self.cpp_info.includedirs = ["include"]

    def _machine(self, arch):
        return {"armv8": "aarch64"}.get(str(arch), str(arch))
