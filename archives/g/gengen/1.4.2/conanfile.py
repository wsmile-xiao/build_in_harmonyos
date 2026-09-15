#!/usr/bin/env python3
"""Conan recipe — gengen 1.4.2 (autotools, 纯工具型包)

gengen 是 GNU 的"通用代码文本生成器"：读 .cc_skel 骨架文件生成带缩进
文本生成能力的 C/C++ 类（gengetopt 就是它的下游用户）。构建产物只有
bin/gengen 一个可执行文件（libgengen.a 为 noinst 不安装，无公开头文件），
故 package_type=application 并声明 commands.json（R38/PF8）。

实撞坑位（同作者同构建体系的 gengetopt 2.23 配方在设备+CI 已验证同一套模式）：
  1. 2010 年 config.guess/config.sub：config.guess 在 HMDFS 上无法创建
     临时文件直接失败、不认识 HarmonyOS；config.sub 拒绝
     aarch64-unknown-linux-{ohos,musl}、只认 -gnu。显式
     --build=--host=aarch64-unknown-linux-gnu 跳过猜测（本机构建目标即
     本机 aarch64 OHOS，native 语义正确，conftest 可直接运行）（E007/E160）。
  2. configure 内嵌 2 处 `umask 077`（E011/E129：HMDFS 上 config.status
     建临时目录 Permission denied），替换为 022；必须在 autoreconf 之后改。
  3. 2010 年代 C++ 与本仓 profile 的 cppstd=17 不兼容（E293）：flex 生成的
     src/scanner.cc 含 15 处 `register`（C++17 移除），src/skelstruct.cc 使用
     std::bind1st/bind2nd/mem_fun（C++17 移除，报 no member named）。
     处理：configure() 里 rm_safe("compiler.cppstd")（仓库先例 boost-ext-ut/
     c-client/cunit/cif-api）——工具链不再注入 -std=c++17，clang 15 默认
     gnu++14，这一代际特性全部可用；设备探索构建（默认标准）全量通过。
     scanner.cc 的 register 仍顺带清理（gnu++14 下仅告警，清掉保零告警）。
  4. 设备/CI 无 texinfo：MAKEINFO=true 跳过 .info；顶层 Makefile 的
     SUBDIRS 行改写为 lib src 跳过 doc/。不能传命令行 SUBDIRS（递归传播
     进子 make）、不能用 make -C src（HMDFS 上 libtool getcwd 坑，
     gengetopt 实撞）。
"""
import glob
import os
import re

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GengenConan(ConanFile):
    name = "gengen"
    version = "1.4.2"
    description = "GNU gengen — 通用代码文本生成器，从骨架文件生成带缩进文本生成能力的 C/C++ 类"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/gengen/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def configure(self):
        # E293：2010 年代代码含 C++17 移除特性（register / bind1st / bind2nd /
        # mem_fun）。profile 的 cppstd=17 会让工具链注入 -std=c++17 直接硬错误
        # （bind1st 系"no member named"彻底移除，连 -Wno-error 都救不回）。
        # 去掉 cppstd 后工具链不再注入 -std，clang 15 默认 gnu++14——与设备
        # 探索构建条件一致（全量通过）。仓库先例：boost-ext-ut / c-client /
        # cunit / cif-api。
        self.settings.rm_safe("compiler.cppstd")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 2010 版 config.sub 只认 -gnu 结尾的 triplet（ohos/musl 均被
        # "Invalid configuration" 拒绝），且必须显式给出以跳过 config.guess
        # （它在 HMDFS 上无法创建临时文件、也不认识 HarmonyOS）。
        # 本机构建目标即本机（aarch64 OHOS），native 语义下 conftest 可直接运行。
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # 设备与 CI 均无 texinfo：MAKEINFO=true 让 automake 把 .info 生成整段跳过
        tc.configure_args.append("MAKEINFO=true")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # GNU 发布包自带 configure，直接用；无 configure 的源（GitHub archive
        # 快照）才需要 autoreconf 自举——判在运行期，同一份配方两种源都能用。
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("源码树无 configure，先 autoreconf 自举")
            autotools.autoreconf(build_script_folder=self.source_folder)
        # ⚠️ E011：umask 修补必须在 autoreconf 之后——自举会重新生成 configure。
        for cfg in glob.glob(os.path.join(self.source_folder, "configure")):
            with open(cfg, encoding="utf-8", errors="ignore") as f:
                text = f.read()
            if "umask 077" in text:
                with open(cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        # C++17 移除了 register 存储说明符；flex 生成的 src/scanner.cc 有
        # 15 处。configure() 已去掉 cppstd（默认 gnu++14 下 register 仅告警），
        # 这里顺带清掉，保持零告警并对未来更严的默认标准免疫。
        scanner = os.path.join(self.source_folder, "src", "scanner.cc")
        if os.path.isfile(scanner):
            with open(scanner, encoding="utf-8", errors="ignore") as f:
                text = f.read()
            text2 = re.sub(r"(?m)^(\s*)register\s+", r"\1", text)
            if text2 != text:
                with open(scanner, "w", encoding="utf-8") as f:
                    f.write(text2)
                self.output.info("移除 src/scanner.cc 的 register 存储说明符")
        # E490：HMDFS 适配路径可能丢掉 autotools 助手脚本的可执行位，防御性恢复
        for script in ("configure", "config.guess", "config.sub",
                       "install-sh", "missing"):
            p = os.path.join(self.source_folder, script)
            if os.path.isfile(p):
                try:
                    os.chmod(p, 0o755)
                except OSError:
                    pass
        autotools.configure()
        # 顶层 SUBDIRS 收窄为 lib src：跳过需要 texinfo 的 doc/。
        # 必须改 Makefile 文件本身：命令行 SUBDIRS 会递归传播给子 make
        # （src/Makefile 拿到它再去 cd 不存在的子目录）；`make -C src` 在
        # HMDFS 上会触发 libtool getcwd 坑（gengetopt 实撞）。
        top_mk = os.path.join(self.build_folder, "Makefile")
        if os.path.isfile(top_mk):
            with open(top_mk, encoding="utf-8", errors="ignore") as f:
                text = f.read()
            text2 = re.sub(r"(?m)^SUBDIRS\s*=.*$", "SUBDIRS = lib src", text, count=1)
            if text2 != text:
                with open(top_mk, "w", encoding="utf-8") as f:
                    f.write(text2)
                self.output.info("顶层 SUBDIRS 收窄为 lib src（跳过 doc/）")
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        # libtool 的 .la 烤死 libdir 绝对路径（conan prefix=/ 时是 /lib），
        # 下游 libtool 会找 //lib/libxxx.la（graphviz 实撞）。gengen 实际
        # 不安装 .la，防御性清理。
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)

    def package_info(self):
        # 纯命令行工具：产物只有 bin/gengen，无库、无公开头文件
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "gengen")
        self.cpp_info.set_property("cmake_target_name", "gengen::gengen")
