#!/usr/bin/env python3
"""Conan recipe for ZArith 1.14 — OCaml big integer arithmetic library.

ZArith uses a custom configure script (not standard autotools).
Build: ./configure -installdir <dir> && make -j1 && make install
Dependencies: OCaml (system-installed), GMP (system-installed)
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ZarithConan(ConanFile):
    name = "zarith"
    version = "1.14"
    description = "Arithmetic and rational arithmetic library for OCaml"
    license = "LGPL-2.0-or-later"
    homepage = "https://github.com/ocaml/Zarith"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # OCaml 4.14.1.1 已在制品仓（PR #3767 合入），zarith 构建需要 ocaml 编译器
        self.tool_requires("ocaml/4.14.1.1.4")
        # GMP 6.3.0 已在制品仓，zarith 需要 gmp.h（configure 检测 GMP/MPIR）
        self.requires("gmp/6.3.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        import re
        apply_conandata_patches(self)
        # GMP 6.3.0 来自 conan 依赖（制品仓），注入其 include/lib 路径
        gmp_dep = self.dependencies["gmp"]
        gmp_inc = os.path.join(gmp_dep.package_folder, "include")
        gmp_lib = os.path.join(gmp_dep.package_folder, "lib")
        os.environ["CFLAGS"] = os.environ.get("CFLAGS", "") + f" -I{gmp_inc}"
        os.environ["LDFLAGS"] = os.environ.get("LDFLAGS", "") + f" -L{gmp_lib}"
        # OCaml 4.14.1.1 来自 tool_requires（制品仓），但其配方未声明 bindirs，
        # conanbuild 环境不会自动注入 bin——此处显式注入 ocaml bin 到 PATH
        # 注意：ocaml 是 build 依赖（tool_requires），需用 dependencies.build 访问
        ocaml_dep = self.dependencies.build["ocaml"]
        ocaml_bin = os.path.join(ocaml_dep.package_folder, "bin")
        os.environ["PATH"] = ocaml_bin + os.pathsep + os.environ.get("PATH", "")
        # 修复：configure 编译检查（ocamlc.opt 编译测试程序）不带 -I stdlib——
        # ocamlc.opt 用默认 stdlib 路径，制品仓包默认路径找不到 Stdlib（Unbound module Stdlib）。
        # 设置 OCAMLLIB 指向制品仓包的 stdlib，让 ocamlc.opt 找到 Stdlib 编译通过。
        ocaml_stdlib = os.path.join(ocaml_dep.package_folder, "lib", "ocaml")
        if os.path.isdir(ocaml_stdlib):
            os.environ["OCAMLLIB"] = ocaml_stdlib
            self.output.info(f"OCAMLLIB 指向制品仓 stdlib: {ocaml_stdlib}")
        # 制品仓 ocaml 包（CI release 构建）的 ocamlc 可能为字节码版且
        # ocamlrun/命令文件存在但无效（bin 文件存在却不可执行），checkcc 编译失败。
        # configure 硬编码 ocamlc='ocamlc'（不读 OCAMLC 环境变量），
        # 故用 PATH 前缀目录覆盖：将 ocamlc.opt 复制为 ocamlc 置于 PATH 最前，
        # 使 configure 的 PATH 查找命中原生 ocamlc.opt（可执行、不依赖 ocamlrun）。
        ocamlc_opt = os.path.join(ocaml_bin, "ocamlc.opt")
        if os.path.isfile(ocamlc_opt):
            override_dir = os.path.join(self.build_folder, "bin_override")
            os.makedirs(override_dir, exist_ok=True)
            override_ocamlc = os.path.join(override_dir, "ocamlc")
            if not os.path.exists(override_ocamlc):
                import shutil
                shutil.copy2(ocamlc_opt, override_ocamlc)
            os.environ["PATH"] = override_dir + os.pathsep + os.environ.get("PATH", "")
            # configure 用 env="conanbuild" 运行（其 PATH 覆盖 os.environ），
            # 用 Environment 将 override_dir 注入 conanbuild 脚本，使 configure 的 ocamlc 命中 override
            env = Environment()
            env.prepend_path("PATH", override_dir)
            env.vars(self).save_script("conanbuild_path_override")
            self.output.info("PATH 前缀覆盖 ocamlc=ocamlc.opt（原生可执行，规避字节码 ocamlc 无效）")
        else:
            self.output.warning("ocamlc.opt 不存在，checkcc 将使用默认 ocamlc（可能受字节码运行时依赖影响）")
        # ZArith uses a custom configure script (not standard autotools)
        # The configure script takes -installdir, not --prefix
        # configure 硬编码 ocamlc='ocamlc'（PATH 查找），而 env=conanbuild 的 PATH
        # 未含 override_dir——直接修改 configure 的 ocamlc 变量为 ocamlc.opt 绝对路径，
        # 使 checkcc 用原生 ocamlc.opt（不依赖字节码 ocamlc/ocamlrun）
        if os.path.isfile(ocamlc_opt):
            cfg = os.path.join(self.source_folder, 'configure')
            if os.path.isfile(cfg):
                with open(cfg) as f:
                    txt = f.read()
                txt = txt.replace("ocamlc='ocamlc'", f"ocamlc='{ocamlc_opt}'")
                with open(cfg, 'w') as f:
                    f.write(txt)
                self.output.info(f'configure ocamlc 变量已指向 ocamlc.opt: {ocamlc_opt}')
        # 修复：configure 编译检查带 -fPIC/-O2（OCaml ocamlc 不认识这些 C 选项——
        # checkcc 报 unknown option 失败）。补丁 configure 去掉 -fPIC/-O2，让 checkcc 编译检查通过
        if os.path.isfile(cfg):
            with open(cfg) as f:
                txt = f.read()
            import re as _re
            txt = _re.sub(r"\s*-fPIC\s*", " ", txt)   # 去 -fPIC（任意位置）
            txt = _re.sub(r"\s*-O2\s*", " ", txt)    # 去 -O2（任意位置）
            txt = _re.sub(r"\s*-O\b(?!\w)", " ", txt)  # 去单独的 -O（ocamlc 不支持）
            with open(cfg, 'w') as f:
                f.write(txt)
            self.output.info("configure 编译检查已适配（去 -fPIC/-O2——ocamlc 不支持这些 C 选项）")
        # 修复：make 的 ocamlmklib 调用 ocamlc（字节码版——OHOS 上不可执行——inaccessible or not found）。
        # 设置 OCAMLC 指向原生 ocamlc.opt（有效）——ocamlmklib 用 OCAMLC 编译链接。
        if os.path.isfile(ocamlc_opt):
            os.environ["OCAMLC"] = ocamlc_opt
        install_dir = os.path.join(self.package_folder, "lib", "ocaml")
        self.run(f"./configure -installdir {install_dir}", cwd=self.source_folder, env="conanbuild")
        # configure 会覆盖/生成 project.mak/Makefile——补丁必须在 configure 之后、make 之前：
        # ocamlmklib 从 PATH 找 ocamlc（build 环境的字节码 ocamlc 无效）——
        # 补丁 Makefile+project.mak 的所有 ocamlmklib 行/OCAMLMKLIB 定义加 -ocamlc ocamlc.opt
        if os.path.isfile(ocamlc_opt):
            for mk in ('project.mak', 'Makefile'):
                mkp = os.path.join(self.source_folder, mk)
                if os.path.isfile(mkp):
                    with open(mkp) as f:
                        mtxt = f.read()
                    if '-ocamlopt' not in mtxt:
                        # ocamlmklib 用原生 ocamlc.opt 与 ocamlopt.opt（字节码 ocamlc/ocamlopt 在 OHOS 上不可执行）
                        ocamlopt_opt = os.path.join(ocaml_bin, 'ocamlopt.opt')
                        if not os.path.isfile(ocamlopt_opt):
                            ocamlopt_opt = ocamlc_opt  # 无 ocamlopt.opt 时退化用 ocamlc.opt
                        # 无条件补丁（含已带 -ocamlc 的）——确保 -ocamlc + -ocamlopt 都在
                        mtxt = mtxt.replace('ocamlmklib', f'ocamlmklib -ocamlc {ocamlc_opt} -ocamlopt {ocamlopt_opt}')
                        with open(mkp, 'w') as f:
                            f.write(mtxt)
                        self.output.info(f"{mk} 已补丁 ocamlmklib -ocamlc: {ocamlc_opt}")
        self.run(f"make -j1 OCAMLC={ocamlc_opt} OCAML_OCAMLC={ocamlc_opt}", cwd=self.source_folder, env="conanbuild")

    def package(self):
        # make install uses INSTALLDIR from configure
        self.run("make install", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["zarith"]
        self.cpp_info.libdirs = ["lib/ocaml/zarith"]
        self.cpp_info.includedirs = ["lib/ocaml/zarith"]
