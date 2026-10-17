#!/usr/bin/env python3
"""Conan recipe for newsraft 0.37 — lightweight terminal RSS/Atom feed reader."""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class NewsraftConan(ConanFile):
    name = "newsraft"
    version = "0.37"
    description = "Lightweight terminal RSS/Atom feed reader (termbox2-based, no curses dependency)"
    license = "ISC"
    homepage = "https://codeberg.org/newsraft/newsraft"
    url = "https://codeberg.org/newsraft/newsraft"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libcurl/8.5.0")
        self.requires("expat/2.8.2.1.1")
        self.requires("sqlite3/3.53.4")
        self.requires("gumbo-parser/0.10.1")

    def layout(self):
        basic_layout(self)

    def _compiler(self):
        # OHOS profile 通过 tools.build:compiler_executables 提供真实编译器路径
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("c", "clang") if compilers else "clang"

    def _dep_flags(self):
        """从 Conan 依赖显式拼接 include/lib 路径（makefile 走 pkg-config 探测无法感知 Conan 环境）。"""
        cflags, ldflags = [], []
        for dep_name in ("libcurl", "expat", "sqlite3", "gumbo-parser"):
            dep = self.dependencies[dep_name]
            for inc in dep.cpp_info.includedirs:
                cflags.append(f"-I{inc}")
            for libdir in dep.cpp_info.libdirs:
                ldflags.append(f"-L{libdir}")
        return " ".join(cflags), " ".join(ldflags)

    def source(self):
        # conan tools.files.download() only uses the FIRST url of a list, so try each
        # mirror explicitly. All urls point to byte-identical archives (same sha256):
        # official codeberg tarball first, then the FreeBSD ports distfile mirror
        # (codeberg rate-limits CI workers with HTTP 429).
        sources = self.conan_data["sources"]
        url_list = sources["url"] if isinstance(sources["url"], list) else [sources["url"]]
        last_error = None
        for url in url_list:
            try:
                get(self, url=url, sha256=sources["sha256"], strip_root=True)
                return
            except ConanException as exc:
                last_error = exc
                self.output.warning(f"source download failed for {url}: {exc}")
        raise last_error

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler()
        inc_flags, lib_flags = self._dep_flags()
        opt = "-O2" if self.settings.build_type == "Release" else "-O0 -g"
        # makefile 对 4 个依赖先 pkg-config 探测、失败回退 -lcurl/-lexpat/-lgumbo/-lsqlite3。
        # 注入 AUXCFLAGS(-I)/LDFLAGS(-L) 并把 PKG_CONFIG_* 指向空目录，强制探测失败走回调，
        # 保证链接落在 Conan 依赖制品上（避免误链系统库）。
        pkg_off = "PKG_CONFIG_LIBDIR=/nonexistent PKG_CONFIG_PATH=/nonexistent"
        self.run(
            f"{pkg_off} make CC={shlex.quote(cc)} CFLAGS='{opt}' AUXCFLAGS='{inc_flags}' LDFLAGS='{lib_flags}'",
            cwd=self.source_folder,
        )
        # 上游无头纯函数单测（tests/*.c 共 16 个，见 makefile check -> tests/run-check.sh）。
        # CI 与本地均为同 profile（build==host），此处显式比对 os/arch 而非 can_run()，
        # 因为 OHOS 适配版 Conan 的 can_run() 对 OHOS 返回 False，会跳过上游测试。
        # run-check.sh 的测试进程需要加载 libcurl.so/libexpat.so 等，把依赖 lib 目录
        # 注入 LD_LIBRARY_PATH（补丁已改为 LD_LIBRARY_PATH="$LD_LIBRARY_PATH:." 保留外部值）。
        same_platform = (
            str(self.settings.os) == str(self.settings_build.os)
            and str(self.settings.arch) == str(self.settings_build.arch)
        )
        if same_platform:
            dep_lib_dirs = []
            for dep_name in ("libcurl", "expat", "sqlite3", "gumbo-parser"):
                dep = self.dependencies[dep_name]
                if dep.cpp_info.libdirs:
                    dep_lib_dirs.append(dep.cpp_info.libdirs[0])
            ld_path = ":".join(dep_lib_dirs)
            self.run(
                f"{pkg_off} LD_LIBRARY_PATH='{ld_path}:$LD_LIBRARY_PATH' "
                f"make check CC={shlex.quote(cc)} AUXCFLAGS='{inc_flags}' LDFLAGS='{lib_flags}'",
                cwd=self.source_folder,
            )

    def package(self):
        # upstream "make install" invokes the external `install` utility, which is
        # not available in the OHOS build environment; copy the binary directly
        # (the man page / icon / examples are documentation, not required in the package).
        copy(self, "newsraft", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []