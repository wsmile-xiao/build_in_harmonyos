from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class ClnConan(ConanFile):
    name = "cln"
    version = "1.3.7"
    description = "CLN - Class Library for Numbers (arbitrary precision arithmetic)"
    license = "GPL-2.0-or-later"
    url = "https://www.ginac.de/CLN/"
    homepage = "https://www.ginac.de/CLN/"
    topics = ("math", "arbitrary-precision", "numbers")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gmp/6.3.0.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        exe = self.conf.get("tools.build:compiler_executables") or {}
        cc = exe.get("c", "clang")
        cxx = exe.get("cpp", "clang++")
        gmp_cppinfo = self.dependencies["gmp"].cpp_info
        gmp_prefix = gmp_cppinfo.includedirs[0].rsplit(os.sep, 1)[0]
        fpic = "-fPIC" if (not self.options.shared and self.options.fPIC) else ""
        # 三元组：2022 年 config.guess 不识 HarmonyOS（E007/E160 同源）
        # CONFIG_SHELL=/bin/sh：profile 注入的 OHOS bash 在 HMDFS getcwd 失败
        # 原地构建：conan 缓存 build-release 子目录在 HMDFS 上 getcwd 风暴
        self.run(
            f'cd "{src}" && umask 000 && mkdir -p "$HOME/tmp" 2>/dev/null; '
            f'CONFIG_SHELL=/bin/sh TMPDIR=$HOME/tmp '
            f'CC={cc} CXX={cxx} CFLAGS="-O2 {fpic}" CXXFLAGS="-O2 {fpic}" '
            f"./configure --prefix={self.package_folder} "
            f"--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu "
            f"--with-gmp={gmp_prefix} "
            # 遵循设备准入 conf（AGENTS §8：jobs=2 限制并发内存峰值）
            f"&& make -j{self.conf.get('tools.build:jobs', default=2)}"
        )

    def package(self):
        src = self.source_folder
        copy(self, "*.so*", os.path.join(src, "src", ".libs"),
             os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.a", os.path.join(src, "src", ".libs"),
             os.path.join(self.package_folder, "lib"), keep_path=False)
        # keep_path 保留 include/cln/ 前缀，dst 用包根避免 include/include 嵌套
        copy(self, "include/cln/*.h", src,
             self.package_folder, keep_path=True)
        copy(self, "COPYING", src, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "cln")
        self.cpp_info.set_property("pkg_config_name", "cln")
        self.cpp_info.libs = ["cln"]
        self.cpp_info.requires = ["gmp::gmp"]
