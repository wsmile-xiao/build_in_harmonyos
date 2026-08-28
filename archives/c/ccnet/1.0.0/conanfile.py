import os
import shutil

from conan import ConanFile
from conan.tools.files import download


class CcnetConan(ConanFile):
    name = "ccnet"
    version = "1.0.0"
    package_type = "application"
    license = "MIT"
    homepage = "https://pypi.org/project/ccnet/"
    description = ("ccnet — a network-based single-cell RNA-seq data analysis "
                   "library (pure Python, no compile)")
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"
    # 纯 Python 库——无运行时依赖（PyPI requires_dist: None）

    def source(self):
        download(self, self.conan_data["sources"]["url"],
                 "ccnet-1.0.0.tar.gz",
                 sha256=self.conan_data["sources"]["sha256"])
        self.run("tar -xzf ccnet-1.0.0.tar.gz --no-same-owner || true")
        self.run("cp -a ccnet-1.0.0/. . && rm -rf ccnet-1.0.0")

    def build(self):
        pass

    def package(self):
        # 纯 Python——安装 ccnet 包到 python site-packages
        src = os.path.join(self.source_folder, "ccnet")
        if os.path.isdir(src):
            shutil.copytree(src,
                            os.path.join(self.package_folder, "lib", "python3",
                                         "site-packages", "ccnet"),
                            dirs_exist_ok=True)

    def package_info(self):
        self.cpp_info.libs = []
