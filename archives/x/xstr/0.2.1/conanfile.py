#!/usr/bin/env python3
"""Conan recipe — xstr 0.2.1 (OCaml library, Gerd Stolpmann / camlcity.org)

xstr is a small pure-OCaml library providing string searching, replacement,
splitting and matching (thread-safe subset of the OCaml Str module).

Build: plain Makefile (no autotools/cmake/dune). It compiles three modules
(xstr_split, xstr_search, xstr_match) into a bytecode archive (xstr.cma,
`make all`) and a native archive (xstr.cmxa + libxstr.a, `make opt`).

Key OHOS adaptations (following the ocaml-syntax-shims precedent in this repo):
  - The OCaml toolchain (ocamlc/ocamlopt/ocamldep/ocamlrun) comes from the
    `ocaml` Conan dependency package (R33: no bare shell env vars).
  - `make install` uses ocamlfind, which is not packaged; instead we install
    the build products manually into lib/xstr (README documents this manual
    copy as a supported alternative to findlib).
  - The Makefile `include depend` triggers `ocamldep` generation on first run,
    which requires the ocaml bin dir on PATH.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy


def _apply_source_fixes(source_folder):
    """就地修复上游源码在 OCaml>=4.06（不可变 string）下的编译错误。

    这类错误是把可变 bytes 缓冲与不可变 string 混用导致类型不匹配：
    - xstr_search.ml 的 rev_concat：`String.create`(bytes) 缓冲返回，但 .mli
      声明 string，需 `Bytes.to_string t`。
    - xstr_match.ml 的 set_as_string：`String.make`(string) 后 `s.[i]<-`
      原地写（要求 bytes），需 `Bytes.make` + `Bytes.to_string s`。
    - xstr_match.ml 的 replace_matched_substrings：`String.create`(bytes) 的
      `target` 返回给 .mli 声明的 `(string*int)`，需 `Bytes.to_string target`。

    全部用 Python 就地字符串替换实现，不依赖外部 `patch` 二进制
    （真机 busybox/toybox patch 报 "patch stream is incomplete!" 无法解析
    统一 diff）——这是本配方采用 Python 就地编辑的原因。
    """
    # --- xstr_search.ml: rev_concat 返回 t -> Bytes.to_string t ---
    ml_path = os.path.join(source_folder, "xstr_search.ml")
    with open(ml_path, "r", encoding="utf-8") as f:
        src = f.read()
    marker = "  fill_in len sl;\n  t\n;;"
    if "Bytes.to_string t" not in src:
        if marker not in src:
            raise RuntimeError(
                "xstr_search.ml: 未找到 rev_concat 返回块（%r）" % marker)
        src = src.replace(marker, "  fill_in len sl;\n  Bytes.to_string t\n;;")
        with open(ml_path, "w", encoding="utf-8") as f:
            f.write(src)

    # --- xstr_match.ml ---
    mm_path = os.path.join(source_folder, "xstr_match.ml")
    with open(mm_path, "r", encoding="utf-8") as f:
        src = f.read()

    # 1) set_as_string: String.make(string) 允许 s.[i]<- 原地写需 bytes。
    #    改为 Bytes.make(bytes)，返回时 Bytes.to_string s。
    ss_marker = "let set_as_string set =\n  let s = String.make 32 ' ' in"
    ss_done = "let set_as_string set =\n  let s = Bytes.make 32 ' ' in"
    if ss_marker in src:
        src = src.replace(ss_marker, ss_done)
        # 返回 s -> Bytes.to_string s（该函数结尾为 "  done;\n  s\n;;"）
        src = src.replace(
            "  done;\n  s\n;;",
            "  done;\n  Bytes.to_string s\n;;")

    # 2) replace_matched_substrings: String.create(bytes) 的 target 返回给
    #    .mli 声明的 (string*int)，需 Bytes.to_string target。
    rm_marker = "  form_replacement_ltor target transformer length;\n  target, !n_repl"
    rm_done = "  form_replacement_ltor target transformer length;\n  Bytes.to_string target, !n_repl"
    if rm_marker in src and "Bytes.to_string target" not in src:
        src = src.replace(rm_marker, rm_done)

    with open(mm_path, "w", encoding="utf-8") as f:
        f.write(src)


class XstrConan(ConanFile):
    name = "xstr"
    version = "0.2.1"
    description = "Functions for string searching/matching/splitting in pure OCaml"
    license = "MIT"
    homepage = "https://projects.camlcity.org/projects/xstr.html"
    url = "https://projects.camlcity.org/projects/xstr.html"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    # Conan requires a 'shared' option for package_type='library'.
    # xstr 是纯 OCaml 库，仅产出静态/字节码归档（xstr.cma/xstr.cmxa/.a），
    # 无共享库概念；声明该选项以满足 Conan 校验，恒为 False（不构建动态库）。
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        # 源码补丁通过 Python 在 build() 内就地修改实现（见 build()），
        # 不依赖外部 `patch` 二进制，故无需 export_conandata_patches。
        pass

    def requirements(self):
        # OCaml 编译器（ocamlc/ocamlopt/ocamldep）由该包提供（R33）
        self.requires("ocaml/4.14.1.1.4")

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # 纯 Makefile 构建，无 CMake/Autotools 工具链
        pass

    def build(self):
        # 上游多个 OCaml>=4.06 不可变 string 引起的类型不匹配就地修复
        # （见 _apply_source_fixes）。用 Python 就地编辑而非 apply_conandata_patches：
        # 真机 busybox/toybox patch 报 "patch stream is incomplete!" 无法解析统一 diff。
        _apply_source_fixes(self.source_folder)

        # 从 ocaml 依赖包取得编译器 bin 目录与标准库目录，注入构建环境。
        # R33：不裸用 shell 变量，路径全部从 Conan 依赖包解析。
        # ocaml 包把 stdlib 装在 lib/ocaml/（含 pervasives.cmi/stdlib.cma 等）。
        # ocamlc 默认按编译期嵌入的 --prefix 找 stdlib，换缓存目录后会失效
        # （报 `Error: Unbound module Stdlib`）；显式设 OCAMLLIB 指向真实 stdlib 根治。
        ocaml_pkg = self.dependencies["ocaml"]
        ocaml_bin = os.path.join(ocaml_pkg.package_folder, "bin")
        ocaml_lib = os.path.join(ocaml_pkg.package_folder, "lib", "ocaml")
        env_vars = ('PATH="{ocaml_bin}:$PATH" '
                    'OCAMLLIB="{ocaml_lib}"').format(
            ocaml_bin=ocaml_bin, ocaml_lib=ocaml_lib)
        # `make all` 生成字节码归档 xstr.cma
        self.run('{env} make all'.format(env=env_vars), env="conanrun")
        # `make opt` 生成本机归档 xstr.cmxa + libxstr.a
        self.run('{env} make opt'.format(env=env_vars), env="conanrun")

    def package(self):
        # 手动安装（不依赖 ocamlfind）：把编译产物拷到 lib/xstr/
        # 编译产物位于 build_folder；.mli 等源文件在 build==source 布局下亦同处
        artifacts = [
            "xstr_split.mli", "xstr_search.mli", "xstr_match.mli",
            "xstr_split.cmi", "xstr_search.cmi", "xstr_match.cmi",
            "xstr_split.cmo", "xstr_search.cmo", "xstr_match.cmo",
            "xstr_split.cmx", "xstr_search.cmx", "xstr_match.cmx",
            "xstr.cma", "xstr.cmxa", "libxstr.a", "xstr.a", "META",
            "LICENSE", "README",
        ]
        dstdir = os.path.join(self.package_folder, "lib", "xstr")
        for base in (self.build_folder, self.source_folder):
            for name in artifacts:
                path = os.path.join(base, name)
                if os.path.exists(path):
                    copy(self, name, src=base, dst=dstdir)

    def package_info(self):
        # OCaml 接口文件（.cmi）与归档（.cma/.cmxa）同目录，下游 `-I` 用
        self.cpp_info.includedirs = ["lib/xstr"]
        self.cpp_info.libdirs = ["lib/xstr"]
        # OCaml 库通过 xstr.cma / xstr.cmxa 按文件名链接，非常规 -l 库
        self.cpp_info.libs = []
