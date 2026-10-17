#!/usr/bin/env python3
"""Conan test_package — libxmlpp 2.42.3 (libxml++ OLD 2.6 API line).

Compiles a real consumer program against libxml++-2.6 and runs it. The test
calls genuine 2.6-API entry points:
  * xmlpp::Document::parse_file(path)   (static factory)
  * Document::get_root_node() / Element::get_name() / get_attribute_value()
  * Node::get_children() (NodeSet iteration, range-for)
  * xmlpp::DomParser::parse_memory()
This is a substantive API test (R34): the program must link against and call
into the packaged library, so the L1e destructive re-link MUST FAIL when
bin/lib/include are moved away.

glibmm/2.66.9 is the 2.4-ABI provider (libxml++ 2.x hard-depends on glibmm-2.4:
Glib::ustring / Glib::RefPtr). The recipe already requires glibmm/2.66.9 (no
user/channel, consistent with the main recipe),
so this consumer require is largely redundant but kept explicit for PkgConfigDeps
to emit glibmm-2.4.pc and put libglibmm-2.4.so on conanrun's LD_LIBRARY_PATH so
the built binary actually runs.

libxml2 is a CONAN dependency of the main recipe: libxmlpp/2.42.3 requires
libxml2/2.15.3 (ohpcd recipe, pkg_config_name "libxml-2.0"), so PkgConfigDeps
generates libxml-2.0.pc in the generators folder and libxml2.so comes from the
conan package — no system prefix involvement (cmd-pkgs system libxml2 removed).
"""
import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.gnu import PkgConfigDeps


class LibxmlppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Consumer dep of libxml++-2.6 (glibmm 2.66.9 = 2.4-ABI provider)。
        # 与主配方一致：无 user/channel（glibmm 作为 synfig 依赖项随 PR 从源码构建，
        # 不带 user/channel 避免与 synfig 的无 channel 引用产生版本冲突）。
        self.requires("glibmm/2.66.9")
        # libxml2 由主配方的 conan 传递依赖链提供（libxmlpp requires libxml2/2.15.3，
        # PkgConfigDeps 生成 libxml-2.0.pc），不再 require 系统包。

    def generate(self):
        # libxml-2.0.pc / glibmm-2.4.pc / libxml++-2.6.pc 全部由 PkgConfigDeps
        # 生成在 generators_folder。必须把该目录注入 build env 的 PKG_CONFIG_PATH，
        # 否则 pkg-config --exists libxml++-2.6 找不到 .pc（CI 实测失败）。
        # 不再注入系统 prefix（libxml2 由主配方 conan 传递链提供，无系统依赖）。
        PkgConfigDeps(self).generate()
        env = VirtualBuildEnv(self)
        env.environment().append_path("PKG_CONFIG_PATH", self.generators_folder)
        env.generate()
        vre = VirtualRunEnv(self)
        vre.generate()

    def build(self):
        # self.run() 默认加载 conanbuild env（profile buildenv 的 PATH 含
        # /data/service/hnp/bin 与 ~/usr/local/bin，pkg-config 可解析）。
        # ⚠️ 不要用裸 subprocess.run(["pkg-config",...])：它跑在 conan 进程原环境里，
        # PATH 不含工具链目录 → FileNotFoundError。
        # 硬失败：被测包 pc 找不到 = 空壳测试（R34）。
        if self.run("pkg-config --exists libxml++-2.6", ignore_errors=True) != 0:
            raise RuntimeError(
                "pkg-config cannot resolve 'libxml++-2.6' — check "
                "package_info() pkg_config_name and that the package really "
                "installed libxml++-2.6.")
        # libxml++-2.6.pc / glibmm-2.4.pc / libxml-2.0.pc 全部来自 PkgConfigDeps
        # （主配方 conan 依赖链：libxmlpp requires glibmm/2.66.9 + libxml2/2.15.3）。
        flags_file = os.path.join(self.build_folder, "pc_flags.txt")
        self.run("pkg-config --cflags --libs libxml++-2.6 glibmm-2.4 libxml-2.0 "
                 "> %s 2>&1" % flags_file)
        with open(flags_file, encoding="utf-8") as f:
            flags = f.read().strip()
        # R33：编译器从 Conan conf 获取，禁止 ${CXX} 裸环境变量
        # （与主配方及 glibmm test_package 一致，worker 上 $CXX 可能未设置）。
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = ce.get("cpp") or ce.get("c") or "clang++"
        self.run(f"{cxx} test_libxmlpp.cpp {flags} -o test_libxmlpp")

    def test(self):
        self.run("./test_libxmlpp", env="conanrun")
