#!/usr/bin/env python3
"""Conan recipe — autodir 0.99.9 (automount directory mapping daemon)

autodir 提供 autodir 命令（C/autotools——libtool 构建——automount
目录映射工具——依赖 libltdl（OHOS 有）+ Linux 内核头 auto_fs4.h）。
路径 A 基础适配。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AutodirConan(ConanFile):
    name = "autodir"
    version = "0.99.9"
    description = "autodir — automount directory mapping (autofs-based tool)"
    license = "GPL-2.0-or-later"
    homepage = "https://packages.debian.org/source/sid/autodir"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # 导出 stub libltdl 源（stub-ltdl.c/ltdl.h——OHOS 无 ltdl.h +
    # libltdl 库——stub 注入——build() 用 self.recipe_folder/stubs）
    exports_sources = "stubs/*"

    def requirements(self):
        # libcap 提供 cap_* API（autodir configure 用 AC_CHECK_LIB(cap,
        # cap_set_proc) 检测——OHOS 无 libcap——conan 依赖 libcap/2.69）
        self.requires("libcap/2.69")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        src_dir = self.source_folder
        # conan 的 exports_sources 在 source() 时复制到源码目录——
        # stub 随源码到 source_folder/stubs（非 recipe_folder）
        stub_dir = os.path.join(self.source_folder, "stubs")
        # 编译 stub libltdl（OHOS 无 ltdl.h + libltdl 库——stub 自带
        # ltdl.h 声明 + 空实现：模块加载不可用，autodir 主功能（目录
        # 映射）正常——同 mydumper/itstool stub 先例，MANIFEST 如实申报）
        self.run(
            f"mkdir -p {src_dir}/stubltdl && "
            f"/data/service/hnp/bin/clang -c {stub_dir}/stub-ltdl.c "
            f"-I{stub_dir} -o {src_dir}/stubltdl/stub-ltdl.o && "
            f"/data/service/hnp/bin/clang -c {stub_dir}/stub-pthread.c "
            f"-I{stub_dir} -o {src_dir}/stubltdl/stub-pthread.o && "
            f"ar rcs {src_dir}/stubltdl/libltdl.a "
            f"{src_dir}/stubltdl/stub-ltdl.o && "
            # stub pthread（pthread_cancel/pthread_setcanceltype——
            # OHOS libpthread.a 无——空实现——同 libltdl stub 先例）
            f"ar rcs {src_dir}/stubltdl/libpthread_stub.a "
            f"{src_dir}/stubltdl/stub-pthread.o",
            env="conanbuild",
        )
        # configure + make（CC=clang——OHOS 无 gcc；--build=arm-linux-gnu
        # 显式指定（config.sub 不识别 aarch64——OHOS uname -s=HarmonyOS
        # 无法猜测 build type，同 brightnessctl uname 处理先例）；
        # CPPFLAGS 注入 stub ltdl.h（autodir 源码 include <ltdl.h>——
        # OHOS 无——stub 头）+ LDFLAGS 注入 stub libltdl.a
        # （configure 的 lt_dlinit 检测通过）
        self.run(
            f"umask 000 && cd {src_dir} && "
            f"./configure CC=/data/service/hnp/bin/clang "
            f"--build=arm-linux-gnu "
            f"CPPFLAGS='-I{stub_dir} "
            f"-I{self.dependencies['libcap'].package_folder}/include' "
            f"LDFLAGS='-L{src_dir}/stubltdl -lltdl "
            f"-L{self.dependencies['libcap'].package_folder}/lib -lcap' "
            # LIBS 注入 -lpthread（make 链接用 LIBS——LDFLAGS 的
            # -lpthread 未传到链接命令；OHOS 有 libpthread.a——
            # pthread_setcanceltype 在静态库）
            f"LIBS='-L{src_dir}/stubltdl -lpthread_stub -lpthread'",
            env="conanbuild",
        )
        self.run(
            f"umask 000 && cd {src_dir} && "
            # -include limits.h（PATH_MAX 未声明——同 bridge-utils 先例）+
            # -fcommon（mod_dir 等全局变量在多个 .c 重复定义——C 旧代码
            # common 符号——现代 clang 默认 -fno-common 报 duplicate
            # symbol——-fcommon 允许合并）
            f"make CFLAGS='-include limits.h -fcommon' -j1",
            env="conanbuild",
        )

    def package(self):
        src_dir = self.source_folder
        # DESTDIR install（autodir 到 sbin/）
        self.run(
            f"umask 000 && cd {src_dir} && "
            f"make install DESTDIR={self.package_folder}",
            env="conanbuild",
        )
        copy(self, "COPYING", src=src_dir,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["usr/local/sbin"]
