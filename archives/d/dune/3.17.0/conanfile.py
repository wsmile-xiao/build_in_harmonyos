#!/usr/bin/env python3
"""Conan recipe — Dune 3.17.0 (OCaml build system)

Dune uses its own bootstrap mechanism:
  1. ocaml boot/bootstrap.ml  → builds _boot/dune.exe
  2. make release             → builds @install with --profile dune-bootstrap

Patches:
  - boot/duneboot.ml: prefer bytecode over .opt native binaries (OHOS security)
  - src/dune_rules/which.ml: don't prefer .opt variants in compiler detection
  - vendor/spawn/src/spawn_stubs.c: guard pthread_setcancelstate for OHOS
  - dune-project: add (version 3.17.0)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class DuneConan(ConanFile):
    name = "dune"
    version = "3.17.0"
    description = "Fast, portable, and opinionated build system for OCaml"
    license = "MIT"
    homepage = "https://github.com/ocaml/dune"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # OCaml 4.14.1.1 已在制品仓（PR #3767 合入），dune 自举需要 ocaml 编译器
        self.tool_requires("ocaml/4.14.1.1.2")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R8 合规：功能探测 pthread_setcancelstate（替代平台宏 __OHOS__）。
        # vendor/spawn 的 spawn_stubs.c 用 HAVE_PTHREAD_SETCANCELSTATE 宏守卫，
        # 编译小测试程序检测该函数是否可用（OHOS 未实现则不定义宏）。
        probe = os.path.join(self.source_folder, "_spawn_probe.c")
        with open(probe, "w") as f:
            f.write("#include <pthread.h>\nint main(void){int s;pthread_setcancelstate(PTHREAD_CANCEL_DISABLE,&s);return 0;}\n")
        probe_obj = os.path.join(self.source_folder, "_spawn_probe.o")
        cc = "clang"
        # -Werror=implicit-function-declaration：OHOS 上 pthread_setcancelstate 未声明，
        # 隐式声明会使编译失败（正确判定 NOT available），而非仅 warning 误判可用
        probe_cmd = f"{cc} -Werror=implicit-function-declaration -c {probe} -o {probe_obj}"
        self.run(probe_cmd, cwd=self.source_folder, env="conanbuild", ignore_errors=True)
        have_pthread = os.path.isfile(probe_obj)
        os.remove(probe) if os.path.isfile(probe) else None
        os.remove(probe_obj) if os.path.isfile(probe_obj) else None
        if have_pthread:
            self.output.info("pthread_setcancelstate available - enabling HAVE_PTHREAD_SETCANCELSTATE")
            os.environ["CFLAGS"] = os.environ.get("CFLAGS", "") + " -DHAVE_PTHREAD_SETCANCELSTATE"
        else:
            self.output.info("pthread_setcancelstate NOT available (OHOS) - feature macro disabled")
        # OCaml 来自 tool_requires（制品仓），声明了 bindirs/env_info.PATH，
        # conanbuild 环境应自动注入 bin。显式注入作为保险（某些 Conan 版本可能不自动注入）。
        ocaml_dep = self.dependencies.build["ocaml"]
        ocaml_bin = os.path.join(ocaml_dep.package_folder, "bin")
        ocaml_lib = os.path.join(ocaml_dep.package_folder, "lib", "ocaml")
        os.environ["PATH"] = ocaml_bin + os.pathsep + os.environ.get("PATH", "")
        self.output.info(f"ocaml bin 注入 PATH: {ocaml_bin}")
        # 制品仓 ocaml 包的原生二进制（ocamlc.opt/ocaml.opt）在编译时硬编码了
        # 标准库路径（--prefix），与 CI 运行器的 conan 缓存路径不同。
        # 设置 OCAMLLIB 让 ocamlc/ocamlrun 能找到 stdlib.cma 等标准库。
        os.environ["OCAMLLIB"] = ocaml_lib
        self.output.info(f"OCAMLLIB={ocaml_lib}")
        # Step 1: Bootstrap - build _boot/dune.exe
        # 制品仓 ocaml 包中的 ocaml 可能是原生 ELF 二进制（ocaml.opt 副本），
        # 在 OHOS CI 上可能因动态链接器（PT_INTERP）不兼容而无法执行。
        # os.path.isfile() 无法检测此情况——文件存在但 exec() 返回 ENOENT。
        # 必须实际试运行验证可执行性。
        try:
            self.run("ocaml -version", cwd=self.source_folder, env="conanbuild")
            ocaml_works = True
        except Exception:
            ocaml_works = False
            self.output.info("ocaml toplevel 不可执行（OHOS ELF PT_INTERP 不兼容）")
        if ocaml_works:
            self.run("ocaml boot/bootstrap.ml", cwd=self.source_folder, env="conanbuild")
        else:
            # ocaml toplevel 不可用，改用 ocamlc 编译 bootstrap.ml + ocamlrun 运行
            # 注意：ocamlc 也可能是原生二进制（ocamlc.opt 副本），同样可能不可执行
            try:
                self.run("ocamlc -version", cwd=self.source_folder, env="conanbuild")
                ocamlc_works = True
            except Exception:
                ocamlc_works = False
                self.output.info("ocamlc 原生二进制也不可执行，尝试 ocamlrun 运行字节码 ocamlc")
            if ocamlc_works:
                self.run("ocamlc -o boot/bootstrap.exe boot/bootstrap.ml", cwd=self.source_folder, env="conanbuild")
            else:
                # 最后手段：用 ocamlrun（原生 C 二进制，兼容性最好）直接运行字节码 ocamlc
                ocamlc_bytecode = os.path.join(ocaml_lib, "ocamlc")
                if not os.path.isfile(ocamlc_bytecode):
                    raise RuntimeError(
                        f"无可用的 OCaml 编译器：ocaml/ocamlc 原生二进制不可执行，"
                        f"字节码 ocamlc 也不存在于 {ocamlc_bytecode}")
                self.output.info(f"使用 ocamlrun + 字节码 ocamlc: {ocamlc_bytecode}")
                self.run(f'ocamlrun "{ocamlc_bytecode}" -o boot/bootstrap.exe boot/bootstrap.ml',
                         cwd=self.source_folder, env="conanbuild")
            self.run("ocamlrun boot/bootstrap.exe", cwd=self.source_folder, env="conanbuild")
            # 删除 fallback 编译产生的 boot/bootstrap.exe 残留，
            # 否则 dune 构建规则与源树中同名文件冲突（Multiple rules generated）
            bootstrap_exe = os.path.join(self.source_folder, "boot", "bootstrap.exe")
            if os.path.isfile(bootstrap_exe):
                os.remove(bootstrap_exe)
        # Step 2: Release build
        self.run("make release", cwd=self.source_folder, env="conanbuild")

    def package(self):
        # Copy the built binary and install artifacts
        copy(self, "dune.exe",
             src=os.path.join(self.source_folder, "_build", "default", "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        # Copy install tree (doc, lib, man, share)
        copy(self, "*",
             src=os.path.join(self.source_folder, "_build", "install", "default"),
             dst=self.package_folder, keep_path=True, excludes=["bin/*"])
        # Ensure bin/dune is the actual binary (not a symlink)
        bin_dune = os.path.join(self.package_folder, "bin", "dune")
        bin_dune_exe = os.path.join(self.package_folder, "bin", "dune.exe")
        if os.path.islink(bin_dune):
            os.unlink(bin_dune)
        if os.path.exists(bin_dune_exe):
            os.rename(bin_dune_exe, bin_dune)

    def package_info(self):
        self.cpp_info.libs = []
        # Dune is a build tool, expose it via bindirs
        self.cpp_info.bindirs = ["bin"]
