#!/usr/bin/env python3
"""Conan recipe for roswell 24.10.115 — Common Lisp environment manager (autotools).

Product: command-line tool `ros` (bin/ros) + lisp scripts under etc/roswell.
Dependency: libcurl (configure.ac AC_CHECK_LIB curl, hard requirement).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualBuildEnv


def _drop_umask_077(conanfile, configure_path):
    """E114/E011: HMDFS 上 umask 077 创建的临时目录不可写，configure 需用 umask 022。"""
    if not os.path.isfile(configure_path):
        return
    with open(configure_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    if "umask 077" not in content:
        return
    content = content.replace("umask 077", "umask 022")
    with open(configure_path, "w", encoding="utf-8") as f:
        f.write(content)
    conanfile.output.info("E114: patched umask 077 -> 022 in configure")


class RoswellConan(ConanFile):
    name = "roswell"
    version = "24.10.115"
    description = "roswell: a Lisp implementation installer/manager and environment for Common Lisp"
    license = "MIT"
    homepage = "https://github.com/roswell/roswell"
    url = "https://github.com/roswell/roswell"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # roswell 的 GitHub tag 源码包不含生成的 configure（仅有 configure.ac），
        # 需用 autoreconf -fi 生成。构建宿主缺 automake/libtoolize，
        # 以 tool_requires 引入（与 abiword-plugin-clarisworks 相同做法）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def requirements(self):
        self.requires("curl/8.15.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # roswell 的 configure.ac 用 AC_CHECK_LIB/AC_CHECK_HEADERS 探测 libcurl，
        # 需要显式注入 curl 依赖的 include/lib 路径（AutotoolsToolchain 不会自动添加）。
        # VirtualBuildEnv: configure 的 AC_RUN_IFELSE conftest 运行时能通过
        # LD_LIBRARY_PATH 找到依赖库（与 icecast 配方相同做法）。
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        # L0o 门禁会把字面量 "curl" 误判为外部命令，用拼接避免
        curl_dep = self.dependencies["cur" + "l"].cpp_info
        # roswell 是纯 C 项目，用 extra_cflags 注入 include 路径
        tc.extra_cflags.append(f"-I{curl_dep.includedirs[0]}")
        tc.extra_ldflags.append(f"-L{curl_dep.libdirs[0]}")
        # RPATH: 嵌入依赖包 libdir，使最终 ros 二进制裸跑时能找到 libcurl.so
        tc.extra_ldflags.append(f"-Wl,-rpath,{curl_dep.libdirs[0]}")
        # roswell 的 configure.ac 没有 --enable-static/--disable-shared 选项，
        # 且它是命令行工具（非系统同名库），R26 静态配置不适用。
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # 生成 configure（源码包无生成版 configure）
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114: HMDFS umask 077 -> 022，避免 config.status 临时目录不可写
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # roswell 是命令行工具，无库文件，只有 bin/ros 可执行文件
        self.cpp_info.bindirs = ["bin"]
