#!/usr/bin/env python3
# 权限: 本配方在 OHOS PC 平台适配使用
"""
Conan recipe — b64.c 0.1.0 (plain C library, jwerle/b64.c).

Base64 encode/decode library, pure libc, no external dependencies.
Upstream ships a plain Makefile (builds the test harness only) and a
CMakeLists.txt (shared lib, no install rules), so the recipe compiles the
three library sources directly into a static library (R26).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout
from conan.errors import ConanInvalidConfiguration

required_conan_version = ">=2.0"


class B64CConan(ConanFile):
    name = "b64.c"
    version = "0.1.0"
    package_type = "library"

    description = "Base64 encode/decode library (jwerle/b64.c)"
    homepage = "https://github.com/jwerle/b64.c"
    license = "MIT"
    url = "https://github.com/jwerle/b64.c"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        # R26: 库仅以静态形式交付（上游无共享库安装规则）
        if self.options.shared:
            raise ConanInvalidConfiguration("b64.c is static-only")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: 编译器取自 Conan 配置（tools.build:compiler_executables），
        # 不依赖未定义的 shell 环境变量。
        cc_conf = self.conf.get("tools.build:compiler_executables", default={})
        cc = (cc_conf or {}).get("c", "clang")
        pic = "-fPIC" if self.options.fPIC else ""
        self.run(f"{cc} -std=c99 -Wall -O2 {pic} -c encode.c decode.c buffer.c",
                 cwd=self.source_folder)
        self.run("ar rcs libb64c.a encode.o decode.o buffer.o",
                 cwd=self.source_folder)

    def package(self):
        copy(self, "b64.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libb64c.a", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["b64c"]
