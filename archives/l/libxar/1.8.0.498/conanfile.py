#!/usr/bin/env python3
"""Conan recipe for libxar 1.8.0.498 — Autotools build system (configure + make).

xar（eXtensible ARchive）源码取自 Apple 官方开源发行 apple-oss-distributions/xar
（tag xar-498，Debian/Ubuntu 的 1.8.0.498 与此同源）。产出 libxar 库与 xar 命令行工具。

Adaptation lessons applied:
- E007: config.guess/config.sub 为 2005 年版本，无 HarmonyOS/OHOS 支持——补丁补齐
  aarch64 与 linux-ohos 识别。
- E011: configure 内 `umask 077` 在 HMDFS 上导致 config.status 临时目录不可写——
  build() 运行时替换为 022，并配 mktemp 包装脚本强制 configure 走 mkdir 兜底。
- conan libxml2 包自带的 xml2-config 硬编码构建期前缀 /usr/local（juise 3.0.0 同款
  问题）；xar 的 configure 支持 --with-xml2-config，配方生成指向 conan 缓存真实
  路径的包装脚本传入。
- configure 不检测 OpenSSL：lib/hash.c 在非 Apple 平台无条件使用 OpenSSL EVP
  摘要接口——经 CPPFLAGS/LIBS 注入，不改源码。
- 上游默认不启用 lzma：lib/lzmaxar.c 针对 2006 年 LZMA SDK 4.42 API 编写
  （LZMA_FILTER_COPY/lzma_preset_lzma/lzma_memlimit_* 等，xz 5.x 已全部移除），
  且上游 configure 从不定义 HAVE_LIBLZMA——保持上游默认（gzip/bzip2/none），
  不强行对接 xz 5.x。
- 上游 linuxattr.c 调用不存在的 safe_dirname（实际函数 xar_safe_dirname），
  Apple 构建不编译该分支故未暴露——补丁 0003 修复。
"""
import os
import shutil
import stat
from pathlib import Path

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class LibxarConan(ConanFile):
    name = "libxar"
    version = "1.8.0.498"
    description = "Xar — eXtensible ARchive library and tool for the xar archive format"
    license = "BSD-3-Clause"
    homepage = "https://github.com/apple-oss-distributions/xar"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.2")
        self.requires("bzip2/1.0.8")
        self.requires("libxml2/2.15.3.1")
        self.requires("openssl/3.5.8.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # tarball 顶层是 xar-xar-498（strip_root 已剥去一层），autoconf 工程在其
        # xar/ 子目录；上移为源码根，使 configure 位于标准位置
        src = self.source_folder
        nested = os.path.join(src, "xar")
        moved = os.path.join(src, ".xar-project-tmp")
        os.rename(nested, moved)
        for entry in os.listdir(moved):
            os.rename(os.path.join(moved, entry), os.path.join(src, entry))
        os.rmdir(moved)

    def generate(self):
        # E011 伴随处理：HMDFS 上 mktemp -d 产生坏权限目录，让其失败以强制
        # configure 使用 mkdir 兜底（配合 build() 中的 umask 替换）
        wrapper_dir = Path(self.build_folder) / ".hmos_fix"
        wrapper_dir.mkdir(exist_ok=True, parents=True)
        mktemp = wrapper_dir / "mktemp"
        mktemp.write_text(
            "#!/bin/sh\n"
            "# HarmonyOS: mktemp -d creates dirs with broken perms (hmdfs, E011).\n"
            "# Return failure to force autoconf AS_TMPDIR to use mkdir fallback.\n"
            "exit 1\n"
        )
        mktemp.chmod(mktemp.stat().st_mode | stat.S_IEXEC)

        xml2_dep = self.dependencies["libxml2"]
        xml2_pkg = xml2_dep.package_folder
        xml2_inc = os.path.join(xml2_pkg, "include", "libxml2")
        xml2_lib = os.path.join(xml2_pkg, "lib")
        xml2_config = wrapper_dir / "xml2-config"
        xml2_config.write_text(
            "#!/bin/sh\n"
            "# conan libxml2 包的 xml2-config 硬编码构建期前缀 /usr/local，\n"
            "# 本包装输出 conan 缓存中 libxml2 包的真实 include/lib 路径。\n"
            'case "$1" in\n'
            '  --version) echo "{v}" ;;\n'
            '  --cflags) echo "-I{i}" ;;\n'
            '  --libs) echo "-L{l} -lxml2" ;;\n'
            '  --prefix) echo "{p}" ;;\n'
            '  *) echo "-I{i} -L{l} -lxml2" ;;\n'
            "esac\n".format(v=xml2_dep.ref.version, i=xml2_inc, l=xml2_lib, p=xml2_pkg)
        )
        xml2_config.chmod(xml2_config.stat().st_mode | stat.S_IEXEC)

        deps_inc, deps_lib = [], []
        for dep_name in ("zlib", "bzip2", "libxml2", "openssl"):
            dep = self.dependencies[dep_name]
            deps_inc.extend(dep.cpp_info.includedirs)
            deps_lib.extend(dep.cpp_info.libdirs)
        inc_flags = " ".join("-I" + d for d in deps_inc)
        lib_flags = " ".join("-L" + d for d in deps_lib)
        rpath_flags = " ".join("-Wl,-rpath," + d for d in deps_lib)

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                # 上游默认同时产 .so+.a 且安装版 CLI(ixar) 链接共享库，其 RUNPATH
                # 为 configure 期 LIBDIR（conan 2 配置期无法预知包目录）→ 运行期
                # 无法定位 libxar.so.1。采用上游自带静态口径，CLI 静态自含
                # （xz 5.8.3 对工具 -static 同款思路）
                "--disable-shared",
                "--enable-static",
                # configure 硬性要求 xml2-config（AC_MSG_ERROR without it）
                "--with-xml2-config={}".format(xml2_config),
                "CPPFLAGS={inc}".format(inc=inc_flags),
                "LDFLAGS={lib} {rpath}".format(lib=lib_flags, rpath=rpath_flags),
                # hash.c（非 Apple 平台）需 libcrypto；bz2 为可选编码（configure 自查）
                "LIBS=-lcrypto -lbz2",
            ]
        )
        tc.generate()

        # OHOS: CONFIG_SHELL 指向实际存在的 bash（profile 可能给出不存在的路径）
        env = Environment()
        bash_path = shutil.which("bash") or "/bin/sh"
        env.define("CONFIG_SHELL", bash_path)
        env.define("SHELL", bash_path)
        env.prepend_path("PATH", str(wrapper_dir))
        env.vars(self).save_script("ohos_env")

    def _fix_conanbuild_shell(self):
        """修正生成的 env 脚本中 profile 注入的不存在工具路径（同 xz 5.8.3 处理）。"""
        clang = shutil.which("clang") or "clang"
        clangxx = shutil.which("clang++") or "clang++"
        bash = shutil.which("bash") or "/bin/sh"
        bad_prefix = "/data/service/hnp/bin"
        good_prefix = os.path.dirname(clang) if os.path.sep in clang else ""
        if os.path.isdir(self.generators_folder):
            for fname in os.listdir(self.generators_folder):
                if not fname.endswith(".sh"):
                    continue
                fpath = os.path.join(self.generators_folder, fname)
                with open(fpath, "r") as f:
                    content = f.read()
                if bad_prefix not in content:
                    continue
                if good_prefix:
                    content = content.replace(
                        "{}/clang++".format(bad_prefix), clangxx
                    )
                    content = content.replace("{}/clang".format(bad_prefix), clang)
                content = content.replace("{}/bash".format(bad_prefix), bash)
                with open(fpath, "w") as f:
                    f.write(content)

    def build(self):
        apply_conandata_patches(self)
        # E011: HMDFS 上 umask 077 创建的临时目录对当前进程不可写（同 xz 5.8.3）
        configure_path = os.path.join(self.source_folder, "configure")
        with open(configure_path, "r") as f:
            content = f.read()
        if "umask 077" in content:
            content = content.replace("umask 077", "umask 022")
            with open(configure_path, "w") as f:
                f.write(content)
        self._fix_conanbuild_shell()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # libtool 风格 .la 对 conan 消费者无意义
        la = os.path.join(self.package_folder, "lib", "libxar.la")
        if os.path.isfile(la):
            os.unlink(la)

    def package_info(self):
        # 头安装为 <prefix>/include/xar/xar.h，消费者 #include <xar/xar.h>
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["xar"]
        # libxar.a 的静态消费者需要全部传递依赖
        self.cpp_info.requires = [
            "zlib::zlib",
            "bzip2::bzip2",
            "libxml2::libxml2",
            "openssl::openssl",
        ]
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            self.cpp_info.bindirs = ["bin"]
