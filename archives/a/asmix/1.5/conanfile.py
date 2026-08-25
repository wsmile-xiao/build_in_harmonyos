#!/usr/bin/env python3
"""Conan recipe — asmix 1.5 (AfterStep 音量旋钮 X11 小程序, autotools)."""
import os
import shlex

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AsmixConan(ConanFile):
    name = "asmix"
    version = "1.5"
    description = "asmix 1.5 (AfterStep 音量旋钮 X11 小程序)"
    license = "GPL-2.0"
    homepage = "https://www.afterstep.org/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # X11 依赖（ohpcd 已发布）；libxpm 未发布，由 0001 补丁剔除 XPM 图标
        self.requires("libx11/6.4.0")
        self.requires("libxext/6.4.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 交叉编译 host 三元组；--srcdir 使生成 Makefile 设 VPATH（源码在上级目录）
        tc.configure_args.append("--host=aarch64-linux-ohos")
        tc.configure_args.append(f"--srcdir={self.source_folder}")
        # X11 依赖头/库路径注入（ohos toolchain 交叉编译）
        for dep in self.dependencies.values():
            for inc in dep.cpp_info.includedirs:
                tc.extra_cflags.append(f"-I{os.path.join(dep.package_folder, inc)}")
            for lib in dep.cpp_info.libdirs:
                tc.extra_ldflags.append(f"-L{os.path.join(dep.package_folder, lib)}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # 旧 autoconf（2004）不生成 VPATH，make 在 build-release 找不到上级源码；
        # 改在源码目录 in-source 构建（conanbuild 环境提供 CC/CFLAGS）。
        # Makefile 链接用 $(LIBRARIES)=$(LIBS_X) $(LIBS_XEXTS) $(LIBS_M)，
        # 库名必须放进变量值（不能作为 make 裸参数）。
        libs = "-lX11 -lXext"
        for dep in self.dependencies.values():
            for lib in dep.cpp_info.libs:
                libs += f" -l{lib}"
        # CI #30003: configure try_compile 链接时 clang 调用 SDK ld.lld，其运行时
        # NEEDED libxml2.so.16（位于 SDK llvm/lib/），CI worker LD_LIBRARY_PATH 未含
        # 该目录 → "C compiler cannot create executables"。configure 前注入
        # os.environ（clang→lld 子进程继承），与 adaptivecpp #29603 同根因修复。
        try:
            lld = os.path.realpath("/data/service/hnp/bin/ld.lld")
            sdk_lib = os.path.join(os.path.dirname(os.path.dirname(lld)), "lib")
            if os.path.isdir(sdk_lib):
                os.environ["LD_LIBRARY_PATH"] = sdk_lib + ":" + os.environ.get("LD_LIBRARY_PATH", "")
        except Exception:
            pass
        self.run(f"./configure --host=aarch64-linux-ohos --prefix={self.package_folder} --disable-jpeg", env="conanbuild",
                 cwd=self.source_folder)
        self.run(f"make -j1 EXTRA_INCLUDES='{self._incs()}' LIBS_X='{self._libdirs()} {libs}'",
                 env="conanbuild", cwd=self.source_folder)
        # 编译并运行补全的上游单元测试（tests/test_asmix.c：include 真实 asmix.c
        # 的 aToVol/VolToa，11 项断言；真实 asmix.c 引用 X11 符号，需 X11 头/库）
        self.run(f"make -C tests check X11_INCDIRS='{self._incs()}' X11_LIBDIRS='{self._libdirs()}' X11_LDPATH='{self._ldpaths()}'",
                 env="conanbuild", cwd=self.source_folder)

    def _incs(self):
        out = ""
        for dep in self.dependencies.values():
            for inc in dep.cpp_info.includedirs:
                out += f" -I{os.path.join(dep.package_folder, inc)}"
        return out

    def _ldpaths(self):
        # 冒号分隔的库目录（运行期 LD_LIBRARY_PATH，供单元测试运行）
        out = []
        for dep in self.dependencies.values():
            for lib in dep.cpp_info.libdirs:
                out.append(os.path.join(dep.package_folder, lib))
        return ":".join(out)

    def _libdirs(self):
        out = ""
        for dep in self.dependencies.values():
            for lib in dep.cpp_info.libdirs:
                out += f" -L{os.path.join(dep.package_folder, lib)}"
        return out

    def package(self):
        # in-source 构建：make 在源码复制目录（build_folder 的上一级）运行，
        # 产物 asmix 位于 os.path.dirname(self.build_folder)。conan copy() 在此
        # 场景未复制（No files in this package），改用 shutil 直接复制。
        import shutil
        src_root = os.path.dirname(self.build_folder)
        bin_dir = os.path.join(self.package_folder, "bin")
        doc_dir = os.path.join(self.package_folder, "share", "doc", "asmix")
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(doc_dir, exist_ok=True)
        os.makedirs(man_dir, exist_ok=True)
        shutil.copy2(os.path.join(src_root, "asmix"), bin_dir)
        shutil.copy2(os.path.join(src_root, "README"), doc_dir)
        shutil.copy2(os.path.join(src_root, "LICENSE"), doc_dir)
        shutil.copy2(os.path.join(src_root, "asmix.man"), man_dir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.conf_info.define("user.asmix:bin", "asmix")
