#!/usr/bin/env python3
"""Conan recipe — mlgmp 20021123

mlgmp 是 GNU MP (GMP) / MPFR 的 Objective Caml (OCaml) 绑定库。
上游为纯 Makefile 项目（无 configure），构建产物为 OCaml 库
(gmp.cma / gmp.cmxa / gmp.a / gmp.cmi / gmp.mli) 与 C 存根库
(libmlgmp.a 静态 / dllmlgmp.so 共享，供字节码运行时查找 C 原语)。

OHOS/aarch64 适配要点:
  - 依赖 conan 预编译包 ocaml/4.14.4、gmp/6.3.0、mpfr/4.2.2.1
  - ocaml 预编译包 ocamlc -where 指向陈旧构建路径，需设 OCAMLLIB 指向实际 lib/ocaml
  - 字节码 -custom ELF 无法在 OHOS 直接执行 (EPERM)，测试/运行一律走 ocamlrun + dllmlgmp.so
  - Makefile 需生成 depend（上游 tarball 缺失），补丁见 patches/（refresh-patch --auto 生成）
"""
import os
import shlex

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class MlgmpConan(ConanFile):
    name = "mlgmp"
    version = "20021123"
    description = "Objective Caml interface to GNU MP (GMP) and MPFR (mlgmp 20021123)"
    license = "LGPL-2.1"
    homepage = "https://packages.debian.org/sid/ocaml/libgmp-ocaml"
    url = "https://salsa.debian.org/ocaml-team/mlgmp"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # mlgmp 是 OCaml 绑定，编译/测试依赖 OCaml 工具链与 GMP/MPFR
        self.requires("ocaml/4.14.4")
        self.requires("gmp/6.3.0")
        self.requires("mpfr/4.2.2.1")

    def layout(self):
        # 纯 Makefile 就地构建（.o/.cmx/.cma 生成在源码目录），
        # 与 ocaml 配方一致: source 与 build 同目录
        self.folders.build = "."
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        pass  # 纯 Makefile 构建，无 autotools/CMake toolchain

    def build(self):
        # 依赖包路径（R33：不依赖未定义 shell 环境变量，从 self.dependencies 取）
        ocaml_pkg = self.dependencies["ocaml"].package_folder
        gmp_pkg = self.dependencies["gmp"].package_folder
        mpfr_pkg = self.dependencies["mpfr"].package_folder

        # 编译器/归档器从 Conan conf 获取（R33，release worker 上 ${CC} 为空）
        conf_tools = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = conf_tools.get("c", "clang")
        ar = conf_tools.get("ar", "ar")
        ranlib = conf_tools.get("ranlib", "ranlib")

        ocaml_bin = os.path.join(ocaml_pkg, "bin")
        ocaml_lib = os.path.join(ocaml_pkg, "lib", "ocaml")
        env = {
            "OCAMLLIB": ocaml_lib,
            "PATH": ocaml_bin + os.pathsep + os.environ.get("PATH", ""),
            "CAML_LD_LIBRARY_PATH": os.path.join(ocaml_lib, "stublibs"),
            "GMP_PREFIX": gmp_pkg,
            "MPFR_PREFIX": mpfr_pkg,
            "CC": cc,
            "AR": ar,
            "RANLIB": ranlib,
        }
        env_str = " ".join(f"{k}={shlex.quote(v)}" for k, v in env.items())

        # 上游 tarball 缺 depend，Makefile `include depend` 需要先由 ocamldep 生成
        self.run(f"{env_str} ocamldep *.ml *.mli > depend", env="conanbuild")

        # R9: 用 -j1
        self.run(f"{env_str} make -j1", env="conanbuild")

        # 上游测试（make tests 即 make check）：
        # 原生 test_suite.opt 直接运行；字节码 test_suite 经 ocamlrun 运行
        self.run(f"{env_str} make tests", env="conanbuild")

    def package(self):
        # 产物镜像 OCaml 库目录约定: lib/ocaml/gmp/（对应 OCAML_LIBDIR/gmp）
        gmpdir = os.path.join(self.package_folder, "lib", "ocaml", "gmp")
        copy(self, "gmp.cma", self.build_folder, gmpdir)
        copy(self, "gmp.cmxa", self.build_folder, gmpdir)
        copy(self, "gmp.a", self.build_folder, gmpdir)
        copy(self, "gmp.cmi", self.build_folder, gmpdir)
        copy(self, "gmp.mli", self.build_folder, gmpdir)
        copy(self, "libmlgmp.a", self.build_folder, gmpdir)
        copy(self, "dllmlgmp.so", self.build_folder, gmpdir)

    def package_info(self):
        # OCaml 库目录（gmp.cmi/gmp.cma/gmp.cmxa/gmp.mli/libmlgmp.a/dllmlgmp.so）
        self.cpp_info.libdirs = ["lib/ocaml/gmp"]
        self.cpp_info.includedirs = ["lib/ocaml/gmp"]
        # C 存根静态库
        self.cpp_info.libs = ["mlgmp"]
        # OCaml 字节码运行时查找 dllmlgmp.so
        self.cpp_info.system_libs = []
        # 供下游 OCaml 编译使用（-I <pkg>/lib/ocaml/gmp）
        self.cpp_info.set_property("pkg_config_name", "mlgmp")
