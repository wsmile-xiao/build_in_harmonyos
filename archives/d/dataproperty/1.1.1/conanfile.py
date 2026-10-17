import os
import shutil

from conan import ConanFile
from conan.tools.files import get


class DatapropertyConan(ConanFile):
    name = "dataproperty"
    version = "1.1.1"
    package_type = "application"
    license = "MIT"
    homepage = "https://github.com/thombashi/dataproperty"
    description = ("dataproperty — Python data property library (pure Python)")
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"
    # dataproperty 依赖 typepy（import dataproperty 需 typepy——已合入 2.0.0）
    requires = "typepy/2.0.0"
    # 纯 Python 库——无编译——安装 dataproperty/ 到 site-packages

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        pass

    def package(self):
        src = os.path.join(self.source_folder, "dataproperty")
        dest = os.path.join(self.package_folder, "lib", "python3")
        if os.path.isdir(src):
            os.makedirs(dest, exist_ok=True)
            shutil.copytree(src, os.path.join(dest, "dataproperty"),
                            dirs_exist_ok=True)

    def package_info(self):
        self.cpp_info.libs = []
