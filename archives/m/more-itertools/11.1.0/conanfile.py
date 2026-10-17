import os
import shutil

from conan import ConanFile
from conan.tools.files import download


class MoreItertoolsConan(ConanFile):
    name = "more-itertools"
    version = "11.1.0"
    package_type = "application"
    license = "MIT"
    homepage = "https://more-itertools.readthedocs.io/"
    description = ("more-itertools — more routines for operating on iterables "
                   "(pure Python, no compile)")
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"
    # 纯 Python 库——依赖 typing-extensions（已发布 ohpcd）
    requires = "typing-extensions/4.16.0"

    def source(self):
        download(self, self.conan_data["sources"]["url"],
                 "more_itertools-11.1.0.tar.gz",
                 sha256=self.conan_data["sources"]["sha256"])
        self.run("tar -xzf more_itertools-11.1.0.tar.gz --no-same-owner || true")
        self.run("cp -a more_itertools-11.1.0/. . && rm -rf more_itertools-11.1.0")

    def build(self):
        pass

    def package(self):
        # 纯 Python——安装 more_itertools 包到 python site-packages
        src = os.path.join(self.source_folder, "more_itertools")
        if os.path.isdir(src):
            shutil.copytree(src,
                            os.path.join(self.package_folder, "lib", "python3",
                                         "site-packages", "more_itertools"),
                            dirs_exist_ok=True)

    def package_info(self):
        self.cpp_info.libs = []
