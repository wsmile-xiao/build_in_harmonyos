#!/usr/bin/env python3
"""Conan recipe for canl-c 3.0.0 — EMI custom top-level Makefile + libtool build.

上游构建系统是 EGEE/EMI 风格的自定义 Makefile（无 autotools/cmake），
libtool 直接承担 compile/link/install；perl 在 make 内生成 canl_err*.c/h，
bison 生成 *_parse.c。构建产物：libcanl_c（libtool versioning → .so.4）
与 4 个示例工具（emi-canl-server/client/proxy-init/delegation）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, save, rm, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CanlCConan(ConanFile):
    name = "canl-c"
    version = "3.0.0"
    description = "Common Authentication Library (caNl) C binding: TLS connections and X.509 proxy certificate management"
    license = "Apache-2.0"
    homepage = "https://github.com/CESNET/canl-c"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 公开头文件 canl.h 包含 <gssapi.h>（krb5 头文件用途，库源码仅使用 gss 类型）
        self.requires("openssl/3.0.16")
        self.requires("c-ares/1.34.6")
        self.requires("krb5/1.22.1")

    def build_requirements(self):
        # Makefile 在构建期调用 libtool 二进制、perl（错误码头生成）、bison（语法分析器）
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("bison/3.8.2")
        self.tool_requires("perl/5.42.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_c(self):
        # Conan 2.29 直接点分子键访问 self.conf 会抛 ConanException，先取 dict 再索引
        comp_exec = self.conf.get("tools.build:compiler_executables")
        if comp_exec:
            return comp_exec.get("c", "clang")
        return "clang"

    def _optimization_flag(self):
        return {
            "Debug": "-O0 -g",
            "RelWithDebInfo": "-O2 -g",
            "MinSizeRel": "-Os",
        }.get(str(self.settings.build_type), "-O2")

    def _build_flags(self):
        deps = self.dependencies
        krb5_inc = deps["krb5"].cpp_info.includedirs[0]
        ossl_inc = deps["openssl"].cpp_info.includedirs[0]
        cares_inc = deps["c-ares"].cpp_info.includedirs[0]
        ossl_lib = deps["openssl"].cpp_info.libdirs[0]
        cares_lib = deps["c-ares"].cpp_info.libdirs[0]
        return krb5_inc, ossl_inc, cares_inc, ossl_lib, cares_lib

    # libtool --mode=install 只接受「单个词」的安装程序；
    # OHOS 设备无 GNU install，CI worker 可能有。此 wrapper 依序回退：
    # 系统 install → busybox install → 纯 sh 最小实现（-m 模式 + cp）。
    _INSTALL_WRAPPER = """#!/bin/sh
# single-word install wrapper for libtool --mode=install
if command -v install >/dev/null 2>&1; then
    exec install "$@"
fi
if command -v busybox >/dev/null 2>&1; then
    exec busybox install "$@"
fi
mode=
while getopts "m:dC" o 2>/dev/null; do
    case "$o" in
        m) mode=$OPTARG ;;
    esac
done
shift $((OPTIND - 1))
src="$1"
dst="$2"
cp "$src" "$dst" || exit 1
[ -n "$mode" ] && chmod "$mode" "$dst"
exit 0
"""

    def build(self):
        apply_conandata_patches(self)
        krb5_inc, ossl_inc, cares_inc, ossl_lib, cares_lib = self._build_flags()

        install_sh = os.path.join(self.build_folder, "canl-c-install-wrapper.sh")
        save(self, install_sh, self._INSTALL_WRAPPER)
        os.chmod(install_sh, 0o755)

        # Makefile 的 CFLAGS 是 "CFLAGS:=... ${CFLAGS}" 形式：环境变量值被追加；
        # 若放命令行会整体覆盖掉 Makefile 自带的 -Isrc/proxy 等必需 include。
        bison_pkg = self.dependencies.build["bison"]
        bison_data = os.path.join(str(bison_pkg.package_folder), "share", "bison")
        cmd = (
            f'export BISON_PKGDATADIR="{bison_data}" && '
            f'export CFLAGS="{self._optimization_flag()} -I{krb5_inc}" && '
            f'export LDFLAGS="-L{cares_lib} -L{ossl_lib}" && '
            f'make -j1 CC="{self._compiler_c()}" '
            f'LIBCARES_CFLAGS="-I{cares_inc}" LIBSSL_CFLAGS="-I{ossl_inc}" '
            f'LIBCARES_LIBS="-lcares" LIBSSL_LIBS="-lssl -lcrypto" '
            f'all'
        )
        self.run(cmd, cwd=self.source_folder, env="conanbuild")

    def package(self):
        krb5_inc, ossl_inc, cares_inc, ossl_lib, cares_lib = self._build_flags()
        install_sh = os.path.join(self.build_folder, "canl-c-install-wrapper.sh")
        bison_pkg = self.dependencies.build["bison"]
        bison_data = os.path.join(str(bison_pkg.package_folder), "share", "bison")
        cmd = (
            f'export BISON_PKGDATADIR="{bison_data}" && '
            f'export CFLAGS="{self._optimization_flag()} -I{krb5_inc}" && '
            f'export LDFLAGS="-L{cares_lib} -L{ossl_lib}" && '
            f'make -j1 CC="{self._compiler_c()}" '
            f'LIBCARES_CFLAGS="-I{cares_inc}" LIBSSL_CFLAGS="-I{ossl_inc}" '
            f'LIBCARES_LIBS="-lcares" LIBSSL_LIBS="-lssl -lcrypto" '
            f'INSTALL="libtool --mode=install {install_sh}" '
            f'install DESTDIR="{self.package_folder}" prefix=/'
        )
        self.run(cmd, cwd=self.source_folder, env="conanbuild")

        # .la 文件内固化构建机路径，跨机消费会引发 libtool archive 误用（见知识库 E236/E522）
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            # shared 包交付动态库 + 可执行工具；静态归档一并移除避免双交付
            rm(self, "*.a", os.path.join(self.package_folder, "lib"))
        else:
            # static 包只交付静态归档；工具链接动态库，静态包不含 bin
            rm(self, "*.so*", os.path.join(self.package_folder, "lib"))
            rm(self, "*", os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        # canl.h → <gssapi.h>；canl_ssl.h → <openssl/ssl.h>；消费者需要传递头文件路径
        self.cpp_info.libs = ["canl_c"]
        self.cpp_info.requires = ["openssl::openssl", "c-ares::c-ares", "krb5::krb5"]
        self.cpp_info.set_property("cmake_file_name", "canl-c")
        self.cpp_info.set_property("cmake_target_name", "canl-c::canl-c")
        self.cpp_info.set_property("pkg_config_name", "libcanl_c")
