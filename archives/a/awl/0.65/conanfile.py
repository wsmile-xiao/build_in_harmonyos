import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class AwlConan(ConanFile):
    name = "awl"
    version = "0.65"
    package_type = "library"
    license = "LGPL-3.0"
    homepage = "https://gitlab.com/davical-project/awl"
    description = ("Andrew's Web Libraries (AWL) — PHP libraries for "
                   "DAViCal: vCalendar/vComponent/vProperty, AuthPlugin, "
                   "AwlDatabase (PgQuery), XMLElement etc. Pure PHP.")
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    # 运行时依赖 PHP 本体（同 php84-pecl-memcache 先例——已发布 ohpcd）
    requires = "php/8.5.8"

    def source(self):
        get(self, **self.conan_data["sources"]["awl"], strip_root=True)

    def build(self):
        # 纯 PHP 库零编译——copytree 源码到 staging（**源外**目录——
        # build 内 staging 在 source 下会递归复制自己——同 netaddr/
        # confspirator python-require 模式教训）——AWLUtilities.php 已
        # 由 sdist 预生成（版本号 0.65 已注入），无需 make
        staging = "/data/storage/el2/base/cache/awl-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.in", "Makefile", "VERSION", "README*", "AUTHORS",
                "COPYING", "ChangeLog", "TODO", "docs", "tests",
                "scripts", "dba", ".gitlab-ci.yml", ".git"))

    def package(self):
        staging = "/data/storage/el2/base/cache/awl-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        # PHP 库打包到 include/awl/（消费者 include_path 加入
        # <pkg>/include——同 php 包 include/php 结构惯例）
        pkg_inc = os.path.join(self.package_folder, "include", "awl")
        os.makedirs(pkg_inc, exist_ok=True)
        inc = os.path.join(staging, "inc")
        if not os.path.isdir(inc):
            raise ConanException(f"inc/ missing in staging: {inc}")
        for f in os.listdir(inc):
            if f.endswith(".php"):
                shutil.copy2(os.path.join(inc, f),
                             os.path.join(pkg_inc, f))

    def package_info(self):
        # 消费者 php include_path 需含 <pkg>/include（awl 库文件位置）
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = []
