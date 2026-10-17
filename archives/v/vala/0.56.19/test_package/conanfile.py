#!/usr/bin/env python3
"""test_package — vala 0.56.19 实质调用 valac（R34）。

编译并运行一个真实 .vala 程序（hello.vala），同时验证 valac --version。
三个子步骤缺一不可，任何一步失败 conan create 即失败：
  1. valac --version                        → 可执行文件存在且可运行
  2. valac hello.vala -o hello（含链接）    → 编译器代码生成 + 链接真实可用
  3. ./hello 输出必须含 "Hello from vala"   → 生成的程序真实可运行（非空壳）
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.gnu import PkgConfigDeps


class ValaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # 与主配方一致：用 PkgConfigDeps 生成指向真实缓存路径的 .pc
        # （剔除 glib-2.0.pc 的 Requires.private: libpcre2-8 —— pcre2 已
        # 静态嵌入 glib .so，且其 binary 在图中为 Skipped 不落盘）
        PkgConfigDeps(self).generate()

    def _dep(self, name):
        try:
            return self.dependencies[name]
        except (KeyError, AttributeError):
            return None

    def _pkgconfig_dirs(self):
        dirs = [self.generators_folder]
        for name in ("vala", "glib"):
            dep = self._dep(name)
            if not dep or not dep.package_folder:
                continue
            pc = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pc):
                dirs.append(pc)
        return dirs

    def test(self):
        vala = self._dep("vala")
        if not vala:
            raise ConanException("vala dependency not found in graph")
        vapi_dir = os.path.join(vala.package_folder, "share", "vala-0.56", "vapi")
        if not os.path.isdir(vapi_dir):
            raise ConanException(f"vapi dir missing: {vapi_dir}")

        clang = shutil.which("clang") or "/data/service/hnp/bin/clang"
        if not os.path.exists(clang):
            clang = "cc"
        clang_dir = os.path.dirname(clang)

        # ohpcd glib .pc libdir=//lib 无效，valac 链接时显式补真实库目录
        lib_dirs = []
        for name in ("glib", "libffi", "pcre2"):
            dep = self._dep(name)
            if dep and dep.package_folder:
                lib_dirs.append(os.path.join(dep.package_folder, "lib"))
        link_flags = " ".join(f'-X -L"{d}"' for d in lib_dirs)

        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", os.pathsep.join(self._pkgconfig_dirs()))
        env.prepend_path("PATH", clang_dir)

        hello_src = os.path.join(self.source_folder, "hello.vala")
        hello_bin = os.path.join(self.build_folder, "hello")
        out_log = hello_bin + ".log"

        with env.vars(self).apply():
            # 1) 可执行文件冒烟
            self.run("valac --version", env="conanrun")

            # 2) valac 编译 + 链接（--cc 显式指定 C 编译器，--vapidir 指向包内 vapi）
            self.run(
                f'valac --vapidir="{vapi_dir}" --pkg=glib-2.0 --cc="{clang}" '
                f'{link_flags} "{hello_src}" -o "{hello_bin}"',
                env="conanrun",
            )
            if not os.path.exists(hello_bin):
                raise ConanException("valac did not produce hello binary")

            # 3) 运行生成的程序，校验真实输出（由 run_test.sh 判定）
            run_sh = os.path.join(self.source_folder, "run_test.sh")
            if not os.path.isfile(run_sh):
                raise ConanException(f"run_test.sh missing: {run_sh}")
            self.run(f'bash "{run_sh}" "{hello_bin}" "{out_log}"', env="conanrun")

        with open(out_log, "r", encoding="utf-8", errors="replace") as handle:
            output = handle.read().strip()
        if "Hello from vala 0.56.19" not in output:
            raise ConanException(f"hello output mismatch, got: {output!r}")
        self.output.info(f"valac smoke test OK: {output}")
