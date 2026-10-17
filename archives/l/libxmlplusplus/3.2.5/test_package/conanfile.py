#!/usr/bin/env python3
"""Conan test_package — libxmlplusplus 3.2.5 (libxml++ 3.0 API 线).

Compiles a real consumer program against libxml++-3.0 and runs it. The test
calls genuine 3.0-API entry points:
  * xmlpp::DomParser::parse_file(path) / parse_memory(contents)
  * Document::get_root_node() / Element::get_name() / get_attribute_value()
  * Node::get_children() (NodeSet iteration, range-for)
This is a substantive API test (R34): the program must link against and call
into the packaged library, so the L1e destructive re-link MUST FAIL when
bin/lib/include are moved away.

glibmm/2.66.9 is the 2.4-ABI provider (libxml++ hard-depends on glibmm-2.4:
Glib::ustring / Glib::RefPtr). The recipe already requires glibmm/2.66.9,
so this consumer require is largely redundant but kept explicit to let
PkgConfigDeps emit glibmm-2.4.pc and put libglibmm-2.4.so on conanrun's
LD_LIBRARY_PATH so the built binary actually runs.

libxml2 is a CONAN dependency of the main recipe: libxmlplusplus/3.2.5
requires libxml2/2.15.3 (ohpcd recipe, pkg_config_name "libxml-2.0"), so
PkgConfigDeps generates libxml-2.0.pc and libxml2.so comes from the conan
package — no system prefix involvement.
"""
import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.gnu import PkgConfigDeps


class LibxmlplusplusTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Consumer dep of libxml++-3.0 (glibmm 2.66.9 = 2.4-ABI provider)。
        self.requires("glibmm/2.66.9")
        # libxml2 由主配方的 conan 传递依赖链提供（libxmlplusplus requires
        # libxml2/2.15.3，PkgConfigDeps 生成 libxml-2.0.pc）。

    def generate(self):
        # libxml-2.0.pc / glibmm-2.4.pc / libxml++-3.0.pc 全部由 PkgConfigDeps
        # 生成在 generators_folder。必须把该目录注入 build env 的 PKG_CONFIG_PATH，
        # 否则 pkg-config --exists libxml++-3.0 找不到 .pc（CI 实测失败）。
        PkgConfigDeps(self).generate()
        env = VirtualBuildEnv(self)
        env.environment().append_path("PKG_CONFIG_PATH", self.generators_folder)
        env.generate()
        vre = VirtualRunEnv(self)
        vre.generate()

    def build(self):
        # self.run() 默认加载 conanbuild env（profile buildenv 的 PATH 含
        # /data/service/hnp/bin 与 ~/usr/local/bin，pkg-config 可解析）。
        # 硬失败：被测包 pc 找不到 = 空壳测试（R34）。
        if self.run("pkg-config --exists libxml++-3.0", ignore_errors=True) != 0:
            raise RuntimeError(
                "pkg-config cannot resolve 'libxml++-3.0' — check "
                "package_info() pkg_config_name and that the package really "
                "installed libxml++-3.0.")
        # libxml++-3.0.pc / glibmm-2.4.pc / libxml-2.0.pc 全部来自 PkgConfigDeps
        # （主配方 conan 依赖链：libxmlplusplus requires glibmm/2.66.9 + libxml2/2.15.3）。
        flags_file = os.path.join(self.build_folder, "pc_flags.txt")
        self.run("pkg-config --cflags --libs libxml++-3.0 glibmm-2.4 libxml-2.0 "
                 "> %s 2>&1" % flags_file)
        with open(flags_file, encoding="utf-8") as f:
            flags = f.read().strip()
        # R33：编译器从 Conan conf 获取，禁止 ${CXX} 裸环境变量。
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = ce.get("cpp") or ce.get("c") or "clang++"
        self.run(f"{cxx} test_libxmlplusplus.cpp {flags} -o test_libxmlplusplus")

    def test(self):
        self.run("./test_libxmlplusplus", env="conanrun")