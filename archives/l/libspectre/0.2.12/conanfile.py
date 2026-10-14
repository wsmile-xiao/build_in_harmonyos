"""libspectre 0.2.12 的 Conan 配方。"""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibspectreConan(ConanFile):
    name = "libspectre"
    version = "0.2.12"
    description = "用于处理和渲染 PostScript 文档的库"
    license = "GPL-2.0-or-later"
    homepage = "https://libspectre.freedesktop.org/"
    url = ""

    package_type = "library"
    exports_sources = "patches/*"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def requirements(self):
        self.requires("ghostscript/10.07.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        # CI 的预下载辅助脚本通过 conandata.yml 扫描 URL；
        # 直接用 Conan get() 下载，走 Conan 自身的 Python 下载实现。
        get(
            self,
            url="https://libspectre.freedesktop.org/releases/libspectre-0.2.12.tar.gz",
            sha256="55a7517cd3572bd2565df0cf450944a04d5273b279ebb369a895391957f0f960",
            strip_root=True,
        )
        # 必须在复制到构建目录之前打上，否则 build() 里跑的是未改的 configure。
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        else:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        # 避免老版 config.guess 在 HarmonyOS /bin/sh 下解析构建类型失败。
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        # configure 的 AC_CHECK_LIB(gs, ...) 会单独探测并设置 libgs；
        # 不要把 -lgs 注入最初的通用编译器可执行文件探测。
        tc.configure_args.append("--disable-test")
        tc.generate()
        AutotoolsDeps(self).generate()

    def build(self):
        # AutotoolsDeps 把 -lgs 放进全部链接测试，Conan 却只把依赖库目录放进 runenv。
        # configure 会运行这个链接了 libgs 的小程序来判断能否执行编译结果；
        # 构建环境没有该库目录时，加载 soname 失败，被误判成交叉编译错误。
        gs_lib = os.path.join(self.dependencies["ghostscript"].package_folder, "lib")
        previous = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = gs_lib if not previous else f"{gs_lib}:{previous}"
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # 发行包没有登记自动化用例，仍执行官方 check 目标确认该版本的实际状态。
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["spectre"]
        self.cpp_info.requires = ["ghostscript::ghostscript"]
        self.cpp_info.set_property("cmake_file_name", "libspectre")
        self.cpp_info.set_property("cmake_target_name", "libspectre::libspectre")
