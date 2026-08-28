import os
import shutil

from conan import ConanFile
from conan.tools.files import get


class S3transferConan(ConanFile):
    name = "s3transfer"
    version = "0.19.2"
    package_type = "application"
    license = "Apache-2.0"
    homepage = "https://github.com/boto/s3transfer"
    description = ("s3transfer — Amazon S3 transfer manager (pure Python)")
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"
    # s3transfer 依赖 botocore（已合入 1.43.78——等 botocore 后适配）
    requires = "botocore/1.43.78"
    # 纯 Python 库——无编译——安装 s3transfer/ 到 site-packages

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        pass

    def package(self):
        src = os.path.join(self.source_folder, "s3transfer")
        dest = os.path.join(self.package_folder, "lib", "python3")
        if os.path.isdir(src):
            os.makedirs(dest, exist_ok=True)
            shutil.copytree(src, os.path.join(dest, "s3transfer"),
                            dirs_exist_ok=True)

    def package_info(self):
        self.cpp_info.libs = []
