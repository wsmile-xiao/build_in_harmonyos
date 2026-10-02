#!/usr/bin/env python3
"""Conan test_package — mlgmp 20021123 (OCaml GMP/MPFR binding)

消费者视角验证：用 ocamlopt（native）编译并运行一个调用 Gmp 模块的
OCaml 程序，验证 mlgmp 安装的 gmp.cmxa/gmp.cmi/libmlgmp.a 可被下游正常链接使用。
同时用 ocamlc + ocamlrun 验证字节码路径（dllmlgmp.so 可加载）。

OHOS 说明：字节码 -custom ELF 无法直接执行（EPERM），一律经 ocamlrun 运行。
"""
import os

from conan import ConanFile


class MlgmpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        mlgmp_pkg = self.dependencies["mlgmp"].package_folder
        ocaml_pkg = self.dependencies["ocaml"].package_folder
        ocaml_bin = os.path.join(ocaml_pkg, "bin")
        ocaml_lib = os.path.join(ocaml_pkg, "lib", "ocaml")
        gmpdir = os.path.join(mlgmp_pkg, "lib", "ocaml", "gmp")

        test_ml = os.path.join(self.source_folder, "test.ml")
        test_sh = os.path.join(self.source_folder, "test.sh")

        env = {
            "OCAMLLIB": ocaml_lib,
            "PATH": ocaml_bin + os.pathsep + os.environ.get("PATH", ""),
            "CAML_LD_LIBRARY_PATH": os.path.join(ocaml_lib, "stublibs"),
            "MLGMP_DIR": gmpdir,
        }
        self.run(
            f'/bin/sh "{test_sh}" "{test_ml}" '
            + " ".join(f'{k}="{v}"' for k, v in env.items()),
            env="conanrun",
        )
