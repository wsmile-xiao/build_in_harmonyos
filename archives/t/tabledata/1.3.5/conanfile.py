import os
import shutil

from conan import ConanFile
from conan.tools.files import get


class TabledataConan(ConanFile):
    name = "tabledata"
    version = "1.3.5"
    package_type = "application"
    license = "MIT"
    homepage = "https://github.com/thombashi/tabledata"
    description = ("tabledata — Python library to represent tabular data "
                   "(pure Python)")
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"
    # tabledata 运行时依赖 DataProperty>=1.0.2,<2 + typepy>=1.2.0,<3
    # （loguru 是 optional extra "logging"，非必需——test_logger 用
    # NullLogger 不依赖 loguru）——dataproperty/1.1.1 与 typepy/2.0.0
    # 均已合入 main
    requires = "dataproperty/1.1.1", "typepy/2.0.0"
    # 纯 Python 库——无编译——安装 tabledata/ 到 site-packages

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        pass

    def package(self):
        src = os.path.join(self.source_folder, "tabledata")
        dest = os.path.join(self.package_folder, "lib", "python3")
        if os.path.isdir(src):
            os.makedirs(dest, exist_ok=True)
            shutil.copytree(src, os.path.join(dest, "tabledata"),
                            dirs_exist_ok=True)

    def package_info(self):
        self.cpp_info.libs = []
