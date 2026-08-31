import os
import shutil

from conan import ConanFile
from conan.tools.files import get


class ListMoreutilsPerlConan(ConanFile):
    name = "liblist-moreutils-perl"
    version = "0.430"
    package_type = "application"
    license = "Artistic-1.0-Perl"
    homepage = "https://metacpan.org/pod/List::MoreUtils"
    description = ("List::MoreUtils — list utilities (pure Perl, no compile)")
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"
    # List::MoreUtils 依赖 Exporter::Tiny（use Exporter::Tiny qw()——实测
    # 'Can't locate Exporter/Tiny.pm'）——requires
    requires = "libexporter-tiny-perl/1.002002"
    # 纯 Perl 模块——无编译依赖——安装 lib/ 的 .pm 到 perl site-lib

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        pass

    def package(self):
        lib = os.path.join(self.source_folder, "lib")
        dest = os.path.join(self.package_folder, "lib", "perl5")
        if os.path.isdir(lib):
            shutil.copytree(lib, dest, dirs_exist_ok=True)

    def package_info(self):
        self.cpp_info.libs = []
