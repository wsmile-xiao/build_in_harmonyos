#!/usr/bin/env python3
"""Conan recipe for leg 0.1.18 (peg/leg parser generators, Ian Piumarta).

上游是裸 Makefile 项目（无 configure / autotools / CMake），一个源码树产出
两个可执行文件：

  * `peg` — 从 PEG 文法生成递归下降解析器（Ford 风格）
  * `leg` — 同一引擎的 lex/yacc 替代风格前端

本配方以 `leg` 作为包名（与 Homebrew 的 "also known as: leg"、Alpine 的
`provides leg` 一致），但源码就是上游唯一的 `peg-0.1.18.tar.gz`；包内
`bin/peg` 与 `bin/leg` 两个命令都会安装。没有库、没有公共头文件，
package_type 为 application。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LegConan(ConanFile):
    name = "leg"
    version = "0.1.18"
    license = "MIT"
    homepage = "https://www.piumarta.com/software/peg/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    description = "Recursive-descent parser generators for C (peg/leg)"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()

    def _cc(self):
        comp_execs = self.conf.get("tools.build:compiler_executables",
                                   default={}, check_type=dict)
        return comp_execs.get("c", "clang")

    def build(self):
        apply_conandata_patches(self)
        cc = self._cc()
        # -j1: OHOS 下 make 无法创建 jobserver fifo（Operation not permitted），
        # GNU make 只在非并行模式下容忍该失败。
        self.run(f"make CC={cc} -j1", cwd=self.source_folder, env="conanbuild")

        # 上游 check = 自举一致性：用刚构建出来的 peg/leg 重新生成
        # src/peg.peg-c 与 src/leg.c，再与发行包内预生成的文件逐字节 diff。
        # 0.1.18 实测两者完全一致（本机 gcc 与 OHOS aarch64 clang 均通过），
        # 因此作为断言执行；这与 peg/0.1.19 不同（0.1.19 的预生成文件与源码
        # 不自洽，那里只能降级为如实记录）。
        self.run(f"make CC={cc} check", cwd=self.source_folder, env="conanbuild")

        # 上游 test = examples/ 下 11 个端到端用例：生成 C 源码 → 编译 →
        # 喂输入 → 与 .ref 参考输出 diff。生成器本身与生成的解析器都会被
        # 执行，所以在 conan create（目标机 aarch64 OHOS）里跑的是真机执行。
        self.run(f"make CC={cc} test", cwd=self.source_folder, env="conanbuild")

    def package(self):
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        for executable in ("peg", "leg"):
            source = os.path.join(self.source_folder, executable)
            if not os.path.isfile(source):
                raise FileNotFoundError(f"Missing build output: {source}")
            shutil.copy2(source, os.path.join(bin_dir, executable))
        # 上游只发行 peg.1 一份 man（leg 与其共用同一手册页）。
        copy(self, "peg.1", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "man", "man1"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        bin_dir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.prepend_path("PATH", bin_dir)
        self.runenv_info.prepend_path("PATH", bin_dir)
