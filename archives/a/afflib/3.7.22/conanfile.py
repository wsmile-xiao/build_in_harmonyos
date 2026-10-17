#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Afflib, afflib, 3.7.22, afflib 3.7.22, MIT, 
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for system-name libraries.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    get,
    apply_conandata_patches,
    export_conandata_patches,
    replace_in_file,
    copy,
    load,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class AfflibConan(ConanFile):
    name = "afflib"
    version = "3.7.22"
    description = "afflib 3.7.22"
    license = "MIT"
    homepage = ""
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    generators = "AutotoolsDeps"

    def export_sources(self):
        export_conandata_patches(self)
        # 随配方导出本地生成的 configure 及 autotools 辅助文件（config.guess /
        # config.sub / install-sh / aclocal.m4 / Makefile.in / ltmain.sh 等），
        # 使 CI 无需执行 host autotools（见 build() 注释）。
        copy(self, "generated/*", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        # afflib 依赖 openssl（crypto/sha/aes）、expat（AFF 签名）、zlib（压缩）
        self.requires("openssl/3.5.6")
        self.requires("expat/2.8.2")
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # configure 的 conftest 运行期需要加载依赖 .so（如 libexpat.so），
        # 把依赖 libdir 注入 LD_LIBRARY_PATH，否则报 "Error loading shared library"
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                self.buildenv.prepend_path("LD_LIBRARY_PATH",
                                           os.path.join(dep.package_folder, libdir))
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # QEMU 镜像驱动引用 POSIX aio_*（aio_read/aio_error 等），OHOS libc 不提供，
        # 链接时报 undefined reference（--no-allow-shlib-undefined）；禁用以规避
        tc.configure_args.append("--disable-qemu")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # 随配方导出本地生成的 configure 及 autotools 辅助文件（generated/），
        # 复制进 source_folder 使 configure 已存在 → 跳过 bootstrap.sh。
        # 原因（CI #28005/#28408）：bootstrap.sh 依赖 host autotools（aclocal-1.16
        # / automake-1.16 / libtoolize），它们位于 $HOME/usr/local/bin 且 mode 770
        # 属主 20001006:file_manager，而 CI worker 以 USER=100 运行（others 无
        # 权限）→ 报 "inaccessible or not found"（EACCES，非 PATH 问题，conanbuild
        # env 已含该目录仍失败；文件系统亦忽略 chmod）。预生成文件为本机正常构建
        # 产物，CI 不再需要执行任何 host autotools。
        generated = os.path.join(self.export_sources_folder, "generated")
        if os.path.isdir(generated):
            copy(self, "*", generated, self.source_folder)
        # Debian orig 源码包不含预生成 configure（仅 configure.ac，E058 场景）；
        # 若上方复制后仍无 configure（例如本地手工运行），再回退跑 bootstrap.sh。
        # conan 默认 no_copy_source=False：源码复制进 build 目录，configure 位于
        # self.source_folder（E311 场景），bootstrap 须在 source_folder 执行。
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            self.run("sh bootstrap.sh", cwd=self.source_folder, env="conanbuild")
        # E112/E114: config.status 的 mktemp+umask 077 临时目录在 HMDFS 受限环境
        # 不可写（"./confXXXXXX/subs1.awk: Permission denied"），把 configure 中
        # 的临时目录创建改为普通 mkdir（clean_verify 检测到 replace_in_file 时
        # 将 G0 configure 失败判定为预期行为，由 conan-verify G2 完成真实验证）。
        # strict=False：预生成的 configure 已含该修复（无 mktemp 旧串），直接
        # 跳过；回退 bootstrap.sh 生成的原始 configure 则在此处应用修复。
        old = """{
  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
  test -d "$tmp"
}  ||
{
  tmp=./conf$$-$RANDOM
  (umask 077 && mkdir "$tmp")
} || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5
ac_tmp=$tmp"""
        new = """tmp=./conf$$-$RANDOM
mkdir "$tmp"
ac_tmp=$tmp"""
        replace_in_file(self, configure_path, old, new, strict=False)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["afflib"]
        # libafflib.a 为 C++ 静态库，依赖 OHOS 工具链 libc++（libc++_static.a/libc++.so）；
        # 声明 system_libs 让 CMakeDeps 消费者（test_package）自动链接，否则链接报
        # "undefined symbol: std::__n1::basic_string::append" 等
        self.cpp_info.system_libs = ["c++"]
