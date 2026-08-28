from conan import ConanFile
from conan.tools.files import get


class BaseDevelConan(ConanFile):
    name = "base-devel"
    # '1' 无效（conan 'Invalid package version' 实测）——用 '1.0'
    version = "1.0"
    package_type = "application"
    license = "GPL-2.0"
    homepage = "https://archlinux.org/groups/x86_64/base-devel/"
    description = ("base-devel — meta-package of base dev tools (gcc/make/"
                   "autoconf/automake/patch — dependency aggregation)")
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"
    # 元包——无编译——聚合已发布的开发工具（gcc/autoconf/automake 已发布
    # ohpcd——make/patch 未发布不 requires——只聚合已发布的）
    requires = "gcc/9.5.0", "autoconf/2.72", "automake/1.18"

    def source(self):
        # 元包无实际源码——不下载（get() 的 Arch download URL 失败实测）
        pass

    def build(self):
        pass

    def package(self):
        # 元包——不安装实际文件（仅 requires 聚合）
        pass

    def package_info(self):
        self.cpp_info.libs = []
