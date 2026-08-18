#!/usr/bin/env python3
"""Conan recipe — dvdauthor 0.7.2（DVD 制作命令行工具）

dvdauthor 提供 dvdauthor/dvdunamae/dvddirdel 等命令（C，autotools），
依赖 libdvdread + libxml2（均已发布，R36 ✅）。tarball 无 configure
（仅 configure.ac）→ autoreconf 生成。GraphicsMagick/ImageMagick
为可选（--without-... 禁用）。上游无测试套件（规则 4 如实申报 0）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class DvdauthorConan(ConanFile):
    name = "dvdauthor"
    version = "0.7.2"
    description = "dvdauthor — DVD authoring tools (dvdauthor/dvdunamae/dvddirdel)"
    license = "GPL-2.0-or-later"
    homepage = "https://dvdauthor.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("libdvdread/7.1.0")
        self.requires("libxml2/2.15.3")
        self.requires("libpng/1.6.58.1")
        self.requires("freetype/2.14.3")

    def build_requirements(self):
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # libxml2/libpng/freetype 通过 pkg-config 检测
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            if self.settings.arch != "armv8":
                raise ConanInvalidConfiguration(
                    "dvdauthor/0.7.2 currently supports only OHOS armv8"
                )
            tc.configure_args.extend([
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
            ])
        # GraphicsMagick/ImageMagick 可选（OHOS 无）→ 禁用
        tc.configure_args.append("--without-imagemagick")
        # AC_CHECK_LIB(dvdread) 不走 pkg-config → 显式注入依赖 include/lib 路径
        incs, libs = [], []
        for dep in ("libdvdread", "libxml2", "libpng", "freetype"):
            if self.dependencies.get(dep):
                pkg = self.dependencies[dep].package_folder
                # freetype 头在 include/freetype2/freetype/ → -I{inc}/freetype2
                if dep == "freetype":
                    incs.append(f"-I{pkg}/include/freetype2")
                else:
                    incs.append(f"-I{pkg}/include")
                libs.append(f"-L{pkg}/lib")
        if incs:
            tc.configure_args.append("CPPFLAGS=" + " ".join(incs))
        if libs:
            tc.configure_args.append("LDFLAGS=" + " ".join(libs))
        tc.generate()

    def build(self):
        # 先应用补丁（0001-xml2-pkg-config.patch 改 configure.ac：
        # 移除 AM_ICONV/AM_PATH_XML2，改 PKG_CHECK_MODULES）
        apply_conandata_patches(self)
        # tarball 无 configure → autoreconf 生成（automake/libtool）
        self.run(
            "autoreconf -fi",
            cwd=self.source_folder,
            env="conanbuild",
        )
        # config.status 用 mktemp -d 创建 confXXXXXX（0700，HMDFS 跨用户
        # 不可写，同 sstp-client/itstool 坑）→ mktemp wrapper 自动 chmod
        wrapper_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(wrapper_dir, exist_ok=True)
        wrapper = wrapper_dir + "/mktemp"
        with open(wrapper, "w") as f:
            f.write(
                "#!/bin/sh\n"
                "real_mktemp=$(command -v mktemp || echo /data/service/hnp/bin/mktemp)\n"
                "d=$($real_mktemp \"$@\")\n"
                "chmod 0755 \"$d\" 2>/dev/null\n"
                "echo \"$d\"\n"
            )
        os.chmod(wrapper, 0o755)
        # config.status 临时目录需可写（out-of-source + umask 000，
        # 同 sstp-client 先例）；手动 configure 需显式注入依赖路径
        # （AC_CHECK_LIB(dvdread) 不走 pkg-config/toolchain env）
        incs, libs = [], []
        for dep in ("libdvdread", "libxml2", "libpng", "freetype"):
            if self.dependencies.get(dep):
                pkg = self.dependencies[dep].package_folder
                # freetype 头在 include/freetype2/freetype/ → -I{inc}/freetype2
                if dep == "freetype":
                    incs.append(f"-I{pkg}/include/freetype2")
                else:
                    incs.append(f"-I{pkg}/include")
                libs.append(f"-L{pkg}/lib")
        self.run(
            f"umask 000 && PATH={wrapper_dir}:$PATH "
            f"{self.source_folder}/configure "
            f"--prefix={self.package_folder} "
            f"--host=aarch64-linux-ohos --build=aarch64-linux-ohos "
            "--without-imagemagick "
            f"CPPFLAGS='{' '.join(incs)}' LDFLAGS='{' '.join(libs)}'",
            cwd=self.build_folder,
            env="conanbuild",
        )
        # -j1: OHOS 沙箱不支持 mkfifo（jobserver），并行编译失败；
        # docbook2man 缺失（OHOS 无）→ make 前替换为 touch 占位生成 man 页
        self.run(
            "sed -i 's|docbook2man root.sgml|touch $(man1_MANS) $(man7_MANS)|' "
            f"{self.build_folder}/doc/Makefile 2>/dev/null || true",
        )
        # @XML_CPPFLAGS@/@XML_LIBS@ 未被 configure 替换（AC_SUBST 依赖
        # LIBXML2_CFLAGS 空）→ make 前直接 sed 替换为 libxml2 实际路径
        # （libxml2 头在 include/libxml2/libxml/ → -I{inc}/libxml2）
        if self.dependencies.get("libxml2"):
            xml_inc = os.path.join(
                self.dependencies["libxml2"].package_folder,
                "include", "libxml2",
            )
            xml_lib = os.path.join(
                self.dependencies["libxml2"].package_folder, "lib"
            )
            self.run(
                f"sed -i 's|@XML_CPPFLAGS@|-I{xml_inc}|g; "
                f"s|@XML_LIBS@|-L{xml_lib} -lxml2|g; "
                f"s|\\$(XML_LIBS)|-L{xml_lib} -lxml2|g' "
                f"{self.build_folder}/src/Makefile 2>/dev/null || true",
            )
        self.run("umask 000 && make -j1", cwd=self.build_folder, env="conanbuild")

    def package(self):
        bin_dst = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dst, exist_ok=True)
        # out-of-source 构建：产物在 build_folder/src/（非 source_folder）
        import glob as _glob
        for name in ("dvdauthor", "dvdunamae", "dvddirdel"):
            cands = _glob.glob(
                os.path.join(self.build_folder, "**", name), recursive=True
            )
            if cands:
                copy(self, name, src=os.path.dirname(cands[0]),
                     dst=bin_dst, keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.runenv_info.append_path("PATH", bin_path)
            self.buildenv_info.append_path("PATH", bin_path)
