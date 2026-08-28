import os
import shutil

from conan import ConanFile
from conan.tools.files import get


class TryTinyPerlConan(ConanFile):
    name = "libtry-tiny-perl"
    version = "0.30"
    package_type = "application"
    license = "MIT"
    homepage = "https://metacpan.org/pod/Try::Tiny"
    description = ("Try::Tiny — minimal try/catch (pure Perl, no compile)")
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"
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
