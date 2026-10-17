#!/usr/bin/env python3
"""Conan recipe for trio 1.16 — portable printf/sprintf/scanf replacement library.

Build system: autotools (the release tarball ships a pre-generated configure).

HarmonyOS PC adaptation:
  - HMDFS 下 configure 以 umask 077 创建临时目录，config.status 读取其中的
    subs1.awk 时报 Permission denied；补丁把 umask 改为 022。
  - 构建目录可能 noexec：config.status 用 `awk -f script` 执行替换程序时 awk
    无法 mmap 脚本，补丁改为经 stdin 传入程序。
  - 显式给出 --build triplet，避免 config.guess 在 noexec 目录编译探测程序失败。
  - OHOS 工具链没有裸 ar/ranlib，通过环境变量指向 llvm-ar/llvm-ranlib。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class TrioConan(ConanFile):
    name = "trio"
    version = "1.16"
    description = "Portable, extensible printf/sprintf/scanf replacement library"
    license = "MIT"
    homepage = "https://sourceforge.net/projects/ctrio/"
    url = "https://sourceforge.net/projects/ctrio/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()

        # OHOS 工具链的 PATH 里只有 llvm-ar/llvm-ranlib，没有裸 ar/ranlib。
        env = Environment()
        for var, names in (
            ("AR", ("llvm-ar", "ar")),
            ("RANLIB", ("llvm-ranlib", "ranlib")),
        ):
            found = next((n for n in names if shutil.which(n)), None)
            if found:
                env.define(var, found)
        env.vars(self).save_script("ohos_env")

    def build(self):
        apply_conandata_patches(self)
        configure = os.path.join(self.source_folder, "configure")
        makefile_in = os.path.join(self.source_folder, "Makefile.in")

        # HMDFS：兜底替换 configure 中所有 umask 077（补丁已覆盖创建临时目录
        # 的两处，这里再兜一层，防止其它 umask 077 出现在 config.status 路径上）。
        if str(self.settings.os) == "OHOS":
            self._replace_if_present(configure, "umask 077", "umask 022")

        # Makefile 硬编码 AR=ar；改成 ?= 以便环境变量 AR 生效。
        self._replace_if_present(makefile_in, "AR\t= ar", "AR\t?= ar")

        # 默认静态包：只构建/安装静态库，避免 libtrio.so 干扰消费者。
        if not self.options.shared:
            self._replace_if_present(
                makefile_in,
                "all: $(TARGETLIB) $(TARGETSHLIB) $(TARGET)",
                "all: $(TARGETLIB) $(TARGET)",
            )
            self._replace_if_present(
                makefile_in,
                "install:\t$(TARGETLIB) $(TARGETSHLIB)",
                "install:\t$(TARGETLIB)",
            )
            self._replace_if_present(
                makefile_in,
                "$(INSTALL_DATA) $(TARGETLIB) $(TARGETSHLIB) $(libdir)/",
                "$(INSTALL_DATA) $(TARGETLIB) $(libdir)/",
            )

        previous_umask = os.umask(0o022)
        try:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()
        finally:
            os.umask(previous_umask)

    def _replace_if_present(self, file_path, old, new):
        """replace_in_file 在找不到模式时会抛 ConanException；先确认存在再替换。"""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        if old in content:
            replace_in_file(self, file_path, old, new)

    def package(self):
        # trio 的 Makefile install 规则不识别 DESTDIR（直接 mkdir -p $(libdir)），
        # 无法用 make install 打包，改为手动拷贝产物。
        # 产物（libtrio.a/Makefile）位于 build_folder（basic_layout 的 build-release），
        # 头文件在 source_folder（src/）。
        if self.options.shared:
            copy(self, "libtrio.so*", self.build_folder, os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libtrio.a", self.build_folder, os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "README", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["trio"]
        self.cpp_info.includedirs = ["include"]
        # 静态库使用 floorl/log10l/powl 等数学函数，需要链接 libm（OHOS 的 libc 内置数学库，无需额外 -lm）。
        if str(self.settings.os) not in ("OHOS", "Windows"):
            self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "trio")
        self.cpp_info.set_property("cmake_target_name", "trio::trio")