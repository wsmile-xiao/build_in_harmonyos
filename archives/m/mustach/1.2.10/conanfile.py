#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe — mustach 1.2.10（C 版 mustache 模板引擎，核心零强制外部依赖）.

上游 gitlab.com/jobol/mustach（作者 José Bollo），双构建系统（Makefile 为主，
meson 为辅）。本配方走 meson（仓库先例 c-list/3.1.0、account-utils/1.4.0）。

形态选择：
- libs=single：core（mustach.c + mustach-wrap.c）与已启用 JSON 后端 wrapper
  合并为单一 libmustach，消费者一次链接（上游 Makefile 的 libs=single 语义）。
- JSON 后端 cjson / json-c / jansson 为可选依赖（上游 auto 探测语义的显式化），
  制品仓均已实查在架（cjson/1.7.19、json-c/0.18、jansson/2.15.1.1）。
- with_tool=True 额外交付 mustach CLI 渲染工具（静态包含所选后端）。

注意：上游 meson.build 的 project version 尚为 1.2.8（上游未随 1.2.10 递增，
tag 内 Makefile 的 MAJOR/MINOR/REVIS 才是权威版本），本配方以包版本 1.2.10 为准。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class MustachConan(ConanFile):
    name = "mustach"
    version = "1.2.10"
    description = "mustach - C implementation of the mustache template engine (core plus optional cjson/json-c/jansson wrappers and a CLI renderer)"
    license = "0BSD"
    homepage = "https://gitlab.com/jobol/mustach"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("c", "mustache", "template", "renderer")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_cjson": [True, False],
        "with_jsonc": [True, False],
        "with_jansson": [True, False],
        "with_tool": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_cjson": True,
        "with_jsonc": True,
        "with_jansson": True,
        "with_tool": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if bool(self.options.shared):
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # 可选 JSON 后端（上游 auto 探测的显式化；PF4 已逐个实查制品仓在架）
        if bool(self.options.with_cjson):
            self.requires("cjson/1.7.19")
        if bool(self.options.with_jsonc):
            self.requires("json-c/0.18")
        if bool(self.options.with_jansson):
            self.requires("jansson/2.15.1.1")

    def build_requirements(self):
        # 上游构建系统为 meson（制品仓已发布；c-list/3.1.0 同款先例）
        self.tool_requires("meson/1.11.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # 禁用 meson wrap 网络拉取（子项目一律走系统/Conan 依赖）
        tc.project_options["wrap_mode"] = "nofallback"
        # single：core + 已启用 wrapper 合为单一 libmustach（上游 Makefile libs=single 语义）
        tc.project_options["libs"] = "single"
        tc.project_options["cjson"] = "enabled" if bool(self.options.with_cjson) else "disabled"
        tc.project_options["jsonc"] = "enabled" if bool(self.options.with_jsonc) else "disabled"
        tc.project_options["jansson"] = "enabled" if bool(self.options.with_jansson) else "disabled"
        # CLI 工具（tool=auto 取第一个启用后端：cjson > jsonc > jansson）
        tc.project_options["tool"] = "auto" if bool(self.options.with_tool) else "none"
        tc.project_options["default_library"] = "shared" if bool(self.options.shared) else "static"
        # CI worker 的 PATH 不含 llvm-ar/llvm-ranlib，从 profile 编译器绝对路径推导
        # （c-list/3.1.0 先例：写入 machine file [binaries]）
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") if compilers else None
        if cc:
            tool_dir = os.path.dirname(cc)
            tc.binaries["ar"] = os.path.join(tool_dir, "llvm-ar")
            tc.binaries["ranlib"] = os.path.join(tool_dir, "llvm-ranlib")
        tc.generate()
        # meson dependency() 走 pkg-config：PkgConfigDeps 生成各依赖 .pc 到
        # generators 目录，MesonToolchain 已把 pkg_config_path 指向该目录
        pkg = PkgConfigDeps(self)
        pkg.generate()
        # 上游 meson.build 请求 dependency('libcjson')（系统发行版的 pc 名）；
        # Conan 的 cjson 包默认 pkg_config_name=cjson → 生成的是 cjson.pc。
        # 在 generators 目录补 libcjson.pc 别名（atk/2.36.0 补 pc 文件先例），
        # 不改上游 meson.build。json-c/jansson 的 pc 名与上游请求一致无需处理
        if bool(self.options.with_cjson):
            src = os.path.join(self.generators_folder, "cjson.pc")
            dst = os.path.join(self.generators_folder, "libcjson.pc")
            if os.path.isfile(src) and not os.path.isfile(dst):
                shutil.copy2(src, dst)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        self._run_upstream_tool_tests()

    def _run_upstream_tool_tests(self):
        """上游工具测试 test1..test8（dotest.sh 渲染 must 并比对 resu.ref）.

        说明：meson 注册的 'specs <backend>' 条目运行 test-specs 可执行文件时
        不带参数——test-specs main() 对空参数表产出全 0 summary 并返回 0（空跑），
        真实 spec 覆盖必须走 Makefile 路径 + mustache/spec v1.4.1 克隆，本配方
        不在 build() 内克隆外部 spec 仓（保持 CI 构建封闭），spec 三套件在真机
        采信轮单独真实执行并留档 reports/。
        """
        if not self.options.with_tool:
            self.output.info("with_tool=False: upstream tool tests skipped (no tool built)")
            return
        if cross_building(self):
            self.output.info("cross-building: upstream tool tests skipped (compile-only)")
            return
        # R33：编译器取 profile 的 tools.build:compiler_executables（dict 形态），
        # 绝不读 shell 环境变量（CI worker 上为空）
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = (compilers or {}).get("c") or "clang"
        tool = os.path.join(self.build_folder, "mustach")
        if not os.path.isfile(tool):
            raise ConanException(f"mustach tool not built: {tool}")
        # test1..test5/7/8：上游 CLI 渲染比对（上游 meson test 同款驱动方式：
        # NOVALGRIND=1 + mustach=<工具绝对路径> + make test）
        for n in ("1", "2", "3", "4", "5", "7", "8"):
            self.run(
                f"env NOVALGRIND=1 CC='{cc}' mustach='{tool}' make test",
                cwd=os.path.join(self.source_folder, "test" + n),
                env="conanbuild",
            )
        # test6：消费者形态（直编上游源码并 -ljson-c），需注入 conan json-c 的
        # 头/库路径（裸 -ljson-c 在 Conan 环境下系统路径不可见）；制品库为
        # libjson-c.so.5 共享形态，运行期还需 LD_LIBRARY_PATH 指向其 libdir
        if bool(self.options.with_jsonc):
            jsonc = self.dependencies["json-c"]
            incdirs = [p if os.path.isabs(p) else os.path.join(jsonc.package_folder, p)
                       for p in jsonc.cpp_info.includedirs]
            libdirs = [p if os.path.isabs(p) else os.path.join(jsonc.package_folder, p)
                       for p in jsonc.cpp_info.libdirs]
            self.run(
                "env NOVALGRIND=1 CC='{cc}' CPATH='{cp}' LIBRARY_PATH='{lp}' "
                "LD_LIBRARY_PATH='{lp}' "
                "mustach='./test-custom-write' make test".format(
                    cc=cc, cp=":".join(incdirs), lp=":".join(libdirs)),
                cwd=os.path.join(self.source_folder, "test6"),
                env="conanbuild",
            )

    def package(self):
        copy(self, "LICENSE.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        # 头文件：上游安装形态 <prefix>/include/mustach/*.h（pkg-config Cflags: -Imustach），
        # 消费者 #include <mustach/mustach.h>；后端头随开关交付
        inc_dst = os.path.join(self.package_folder, "include", "mustach")
        for header in ("mustach.h", "mustach-wrap.h"):
            copy(self, header, self.source_folder, inc_dst)
        if self.options.with_cjson:
            copy(self, "mustach-cjson.h", self.source_folder, inc_dst)
        if self.options.with_jsonc:
            copy(self, "mustach-json-c.h", self.source_folder, inc_dst)
        if self.options.with_jansson:
            copy(self, "mustach-jansson.h", self.source_folder, inc_dst)
        # 库：meson library() 未声明 version/soversion → 产物无版本符号链接链
        # （静态 libmustach.a / 动态 libmustach.so 单文件），规避 meson install 的
        # HMDFS 符号链接坑（account-utils/1.4.0 先例），直接从 build 目录收纳
        lib_dst = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            copy(self, "libmustach.so", self.build_folder, lib_dst)
        else:
            copy(self, "libmustach.a", self.build_folder, lib_dst)
        # CLI 工具（静态包含核心 + tool=auto 所选后端）
        if self.options.with_tool:
            copy(self, "mustach", self.build_folder,
                 os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "mustach")
        self.cpp_info.set_property("cmake_target_name", "mustach::mustach")
        self.cpp_info.set_property("pkg_config_name", "libmustach")
        # 消费者 #include <mustach/mustach.h>（上游 pkg-config 同形态）
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["mustach"]
        # 后端依赖传播给消费者（libmustach 内已编入 wrapper，符号来自后端库）
        if self.options.with_cjson:
            self.cpp_info.requires.append("cjson::cjson")
        if self.options.with_jsonc:
            self.cpp_info.requires.append("json-c::json-c")
        if self.options.with_jansson:
            self.cpp_info.requires.append("jansson::jansson")
        # mustach CLI 渲染工具（R38：commands.json 见包目录）
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
