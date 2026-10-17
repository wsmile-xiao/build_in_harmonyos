#!/usr/bin/env python3
"""Conan recipe for adplay 1.9 (AdPlay/UNIX — OPL2 player) on HarmonyOS PC.

真实构建模式：声明 adplug/2.4 依赖（PR #4614 已合并 published），
autoreconf + configure + make 真实构建，test_package 真实验证 adplay。
"""

import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class AdplayConan(ConanFile):
    name = "adplay"
    version = "1.9"
    description = "AdPlay/UNIX — console-based OPL2 audio player (AdPlug frontend)"
    license = "GPL-2.0"
    homepage = "https://github.com/adplug/adplay-unix"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # adplay 是 AdPlug 前端播放器，configure 需找到 AdPlug >= 2.0。
        # adplug/2.4 PR #4614 已合并（08-08 published），制品仓有包。
        self.requires("adplug/2.4")

    def build_requirements(self):
        # 源码树只有 configure.ac，须 autoreconf 自举；CI 缺 automake/libtool。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_env(self):
        # OHOS 编译器（clang/clang++）位于 /data/service/hnp/bin/，不在默认 PATH 中。
        # configure 探测 aarch64-unknown-linux-ohos-gcc 得到 clang，但缺编译环境
        # 导致 "C compiler cannot create executables"。参照 jack/1.9.22 先例。
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or "clang"
        cxx = compilers.get("cpp") or "clang++"
        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        bindir = os.path.dirname(cc) if os.path.sep in cc else ""
        ar = compilers.get("ar") or (os.path.join(bindir, "llvm-ar") if bindir else "")
        ranlib = compilers.get("ranlib") or (os.path.join(bindir, "llvm-ranlib") if bindir else "")
        if ar:
            env.define("AR", ar)
        if ranlib:
            env.define("RANLIB", ranlib)
        # configure.ac 用 PKG_CHECK_MODULES([adplug], [adplug >= 2.0])
        # 检查 AdPlug——但制品仓 adplug.pc 的 prefix=/（指向系统根目录
        # 而非包实际路径）且 Requires: libbinio（libbinio 无 pkgconfig），
        # pkg-config 检查必失败（checking for adplug >= 2.0... no）→
        # adplug_LIBS 为空 → AC_LINK_IFELSE 无 -ladplug 链接失败。
        # 生成修正版 adplug.pc（prefix 指向包实际路径、去 Requires），
        # 注入 PKG_CONFIG_PATH，使 PKG_CHECK_MODULES 成功。
        if "adplug" in self.dependencies:
            ap = self.dependencies["adplug"].package_folder
            inc = os.path.join(ap, "include")
            lib = os.path.join(ap, "lib")
            # libbinio 是 adplug 的传递依赖——静态链接 libadplug.a 还需
            # -lbinio 且 adplug/fprovide.h include <binio.h>（无前缀）——
            # libbinio 包头文件在 include/libbinio/ 子目录，需注入
            # include/libbinio 路径（configure 的 AC_LINK_IFELSE 需要）
            binio_inc = ""
            binio_lib = ""
            if "libbinio" in self.dependencies:
                bp = self.dependencies["libbinio"].package_folder
                # binio.h 实际在 include/libbinio/（#include <binio.h> 无前缀）
                for cand in (os.path.join(bp, "include", "libbinio"),
                             os.path.join(bp, "include")):
                    if os.path.isfile(os.path.join(cand, "binio.h")):
                        binio_inc = cand
                        break
                if os.path.isdir(os.path.join(bp, "lib")):
                    binio_lib = os.path.join(bp, "lib")
            pcdir = os.path.join(self.build_folder, "_adplug_pc")
            os.makedirs(pcdir, exist_ok=True)
            libs = "-L${libdir} -ladplug"
            if binio_lib:
                libs += f" -L{binio_lib} -lbinio"
            cflags = "-I${includedir}"
            if binio_inc:
                cflags += f" -I{binio_inc}"
            with open(os.path.join(pcdir, "adplug.pc"), "w") as f:
                f.write(
                    "prefix=%s\nexec_prefix=${prefix}\n"
                    "libdir=${prefix}/lib\nincludedir=${prefix}/include\n\n"
                    "Name: adplug\nDescription: A free AdLib sound player library\n"
                    "URL: http://adplug.github.io\nVersion: 2.4\n"
                    "Libs: %s\nCFlags: %s\n" % (ap, libs, cflags)
                )
            env.prepend_path("PKG_CONFIG_PATH", pcdir)
            if os.path.isdir(inc):
                env.append("CPPFLAGS", f"-I{inc}")
            if binio_inc:
                env.append("CPPFLAGS", f"-I{binio_inc}")
            if os.path.isdir(lib):
                env.append("LDFLAGS", f"-L{lib}")
        return env

    def build(self):
        apply_conandata_patches(self)
        # 上游使用 autotools；GitHub archive 无 configure，先 autoreconf 自举。
        import os as _os

        if not _os.path.isfile(_os.path.join(self.source_folder, "configure")):
            self.run(
                f'cd "{self.source_folder}" && autoreconf -fi',
                env="conanbuild",
            )
        # autoreconf 生成的 configure 其 config.status 用 confstat 机制
        # （umask 077 + mktemp ./confXXXXXX 创建 0700 临时目录）——OHOS
        # HMDFS 上 0700 目录不可写导致 "config.status: could not setup
        # config files machinery"（boa/catdoc 同款，DRAFT-ohos-autoconf-
        # confstat-umask-077-perm 覆盖）——patch umask 077→000。
        cf = _os.path.join(self.source_folder, "configure")
        if _os.path.isfile(cf):
            with open(cf, "r", encoding="utf-8", errors="replace") as f:
                c = f.read()
            c = c.replace('(umask 077 && mktemp -d "./confXXXXXX")',
                          '(umask 000 && mktemp -d "./confXXXXXX")')
            c = c.replace('(umask 077 && mkdir "$tmp")',
                          '(umask 000 && mkdir "$tmp")')
            with open(cf, "w", encoding="utf-8") as f:
                f.write(c)
        with self._compiler_env().vars(self).apply():
            self.run(
                f'cd "{self.source_folder}" && ./configure --prefix="{self.package_folder}" '
                # config.guess 无法识别 HarmonyOS（UNAME_SYSTEM=HarmonyOS），
                # 显式 --build/--host。
                "--build=aarch64-unknown-linux-gnu "
                "--host=aarch64-unknown-linux-ohos --disable-shared --enable-static "
                # OHOS 制品仓无 libao 且无 oss/alsa/esound/qsa/sdl 音频
                # 输出驱动——disable 这些 output 机制（保留 null/raw/disk
                # 文件型输出），否则编译报 ao/ao.h not found
                "--disable-output-oss --disable-output-ao "
                "--disable-output-alsa --disable-output-esound "
                "--disable-output-qsa --disable-output-sdl",
                env="conanbuild",
            )
            # libtool 链接依赖包时读 .la 文件——制品仓 adplug/libbinio
            # 包的 .la 其 libdir='//lib'（构建时 prefix=/ 残留，双斜杠）
            # 且 dependency_libs 硬编码 //lib/libbinio.la，导致
            # "cannot find the library '//lib/libbinio.la'"——patch
            # .la：libdir='//lib' → 实际 lib 路径、//lib/<dep>.la →
            # 实际路径。
            la_dirs = {}
            for dep_name in ("adplug", "libbinio"):
                if dep_name not in self.dependencies:
                    continue
                pkg = self.dependencies[dep_name].package_folder
                la_dir = _os.path.join(pkg, "lib")
                if _os.path.isdir(la_dir):
                    la_dirs[dep_name] = la_dir
            for dep_name, la_dir in la_dirs.items():
                for la in _os.listdir(la_dir):
                    if not la.endswith(".la"):
                        continue
                    la_p = _os.path.join(la_dir, la)
                    with open(la_p, "r", encoding="utf-8", errors="replace") as f:
                        c = f.read()
                    fixed = c.replace("libdir='//lib'", f"libdir='{la_dir}'")
                    fixed = fixed.replace('libdir="//lib"', f'libdir="{la_dir}"')
                    for other_name, other_dir in la_dirs.items():
                        fixed = fixed.replace(f"//lib/{other_name}.la",
                                              f"{other_dir}/{other_name}.la")
                    if fixed != c:
                        with open(la_p, "w", encoding="utf-8") as f:
                            f.write(fixed)
            self.run(f'cd "{self.source_folder}" && make -j1', env="conanbuild")
            self.run(f'cd "{self.source_folder}" && make install', env="conanbuild")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
