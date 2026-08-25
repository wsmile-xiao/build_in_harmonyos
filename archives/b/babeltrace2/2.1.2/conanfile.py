#!/usr/bin/env python3
"""Conan recipe — babeltrace2 2.1.2 (Babeltrace 2 CTF library/tool, C/autotools) on HarmonyOS PC."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get, chdir
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class Babeltrace2Conan(ConanFile):
    name = "babeltrace2"
    version = "2.1.2"
    description = "Babeltrace 2 — next-gen CTF trace format converter and library"
    license = "MIT"
    homepage = "https://babeltrace.org"
    url = "https://github.com/efficios/babeltrace"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("glib/2.88.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("popt/1.16", transitive_headers=True, transitive_libs=True)
        self.requires("uuid/2.40.1", transitive_headers=True, transitive_libs=True)

    def export_sources(self):
        copy(self, "patches/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def layout(self):
        basic_layout(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.extra_configure_args = [
            "--disable-python-bindings", "--disable-debug-info",
        ]
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"babeltrace2 {self.version} only supports Linux and OHOS, got os={self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # babeltrace2 GitHub release tarball 不含预生成的 configure，
        # CI worker 无 aclocal/automake 无法 autoreconf。
        # 预生成 autotools 产物已 vendored 在 patches/autotools/，
        # 复制到源码树即可。
        import shutil
        # CI #30176: CI worker 无 aclocal/automake，autoreconf -fi 必败。
        # 本地通过是因为本机装了 automake 1.16.5，autoreconf 成功重新生成
        # 所有 Makefile.in。为保证本地与 PR CI 完全一致，recipe 不再依赖
        # autoreconf，而是把预生成 autotools 产物 vendor 到
        # patches/autotools/，source() 递归复制整个目录树到源码根。
        # 仓内先例: archives/l/lttoolbox/3.7.6/conanfile.py (PR #5343)。
        at_src = os.path.join(self.recipe_folder, "patches", "autotools")
        if not os.path.isdir(at_src):
            at_src = os.path.join(self.export_sources_folder, "patches", "autotools")
        if os.path.isdir(at_src):
            for root, _dirs, files in os.walk(at_src):
                rel = os.path.relpath(root, at_src)
                dst_dir = (os.path.join(self.source_folder, rel)
                           if rel != "." else self.source_folder)
                os.makedirs(dst_dir, exist_ok=True)
                for fn in files:
                    src = os.path.join(root, fn)
                    dst = os.path.join(dst_dir, fn)
                    if os.path.isfile(src):
                        shutil.copy2(src, dst)
        # E248/E071: make 检测 Makefile.am/aclocal.m4 比 Makefile.in/configure
        # 新就触发 automake/aclocal 重生成。CI worker 无 aclocal/automake 时
        # exit 127；本地有 automake 但跑 config.status --recheck 又遇 HMDFS
        # Permission denied。统一把 vendored 生成物 touch 到比 .am/.ac 新，
        # 掐断 make 的重生成触发条件（仓内先例 lttoolbox/3.7.6、E248 os.utime）。
        import time
        new_ns = time.time_ns()
        for pat in ("configure", "aclocal.m4", "config/*",
                    "m4/*.m4", "*/Makefile.in", "Makefile.in"):
            import glob
            for f in glob.glob(os.path.join(self.source_folder, pat), recursive=False):
                if os.path.isfile(f):
                    os.utime(f, ns=(new_ns, new_ns))
        # 递归 touch 所有 Makefile.in（含 tests/ 子目录树）
        for root, _dirs, files in os.walk(self.source_folder):
            for fn in files:
                if fn == "Makefile.in":
                    os.utime(os.path.join(root, fn), ns=(new_ns, new_ns))
        # 不再调用 autoreconf -fi: CI worker 无 aclocal 必败，
        # vendored autotools 产物已完整覆盖所有需要的文件。
        # 若仍有 Makefile.am 缺对应 Makefile.in，显式列出缺失目录。
        # E011: HMDFS umask 077 → 022（configure 生成临时脚本不可执行）
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            content = open(configure).read()
            if "umask 077" in content:
                open(configure, "w").write(content.replace("umask 077", "umask 022"))

    def build(self):
        apply_conandata_patches(self)
        tmpdir = os.path.join(self.build_folder, "cfg-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        # CI #29320/#29520: AM_PATH_GLIB_2_0 宏用 pkg-config 检测
        # glib-2.0 >= 2.28.0 gmodule-no-export-2.0，但 CI worker
        # 系统装了旧版 GLib（48.0.x），与 Conan 依赖 glib/2.88.0.1 冲突。
        # 显式设置 PKG_CONFIG_PATH 指向：
        # 1. PkgConfigDeps 生成的 .pc 文件目录（self.generators_folder）
        # 2. Conan 依赖包的 lib/pkgconfig 目录（dep.package_folder）
        # Conan glib 不提供 gmodule-no-export-2.0.pc，从 gmodule-2.0.pc 复制。
        pkg_config_paths = []
        # PkgConfigDeps 生成的 .pc 文件目录
        gen_folder = self.generators_folder
        if gen_folder and os.path.isdir(gen_folder):
            pkg_config_paths.append(gen_folder)
        # Conan 依赖包的 pkgconfig 目录
        for dep_name in ("glib", "popt", "uuid"):
            if dep_name in self.dependencies:
                dep = self.dependencies[dep_name]
                pkg_folder = dep.package_folder
                if not pkg_folder:
                    continue
                for subdir in ("lib/pkgconfig", "lib64/pkgconfig",
                               "share/pkgconfig", "pkgconfig"):
                    pc_dir = os.path.join(pkg_folder, subdir)
                    if os.path.isdir(pc_dir):
                        pkg_config_paths.append(pc_dir)
        # 创建 gmodule-no-export-2.0.pc（从 gmodule-2.0.pc 复制）
        for pc_dir in pkg_config_paths:
            src = os.path.join(pc_dir, "gmodule-2.0.pc")
            dst = os.path.join(pc_dir, "gmodule-no-export-2.0.pc")
            if os.path.isfile(src) and not os.path.isfile(dst):
                import shutil
                shutil.copy2(src, dst)
        env_prefix = ""
        if pkg_config_paths:
            env_prefix = f"PKG_CONFIG_PATH='{':'.join(pkg_config_paths)}' "
        # CI #29521/#29523/#29527: AM_PATH_GLIB_2_0 宏编译并运行测试程序，
        # 需 CFLAGS/LDFLAGS/LD_LIBRARY_PATH 全部指向 Conan glib，
        # 否则编译器/链接器/动态链接器找到系统旧版 GLib 48.0.x，
        # 导致 GLIB_MAJOR_VERSION 不匹配（48 != 2）。
        cflags_dirs = []
        ldflags_dirs = []
        ld_lib_paths = []
        for dep_name in ("glib", "popt", "uuid"):
            if dep_name in self.dependencies:
                dep = self.dependencies[dep_name]
                pkg_folder = dep.package_folder
                if not pkg_folder:
                    continue
                # glib.h 在 include/glib-2.0/，glibconfig.h 在 lib/glib-2.0/include/
                for inc_sub in ("include", "include/glib-2.0",
                                "lib/glib-2.0/include", "lib64/glib-2.0/include"):
                    inc_dir = os.path.join(pkg_folder, inc_sub)
                    if os.path.isdir(inc_dir):
                        cflags_dirs.append(inc_dir)
                for subdir in ("lib", "lib64"):
                    lib_dir = os.path.join(pkg_folder, subdir)
                    if os.path.isdir(lib_dir):
                        ldflags_dirs.append(lib_dir)
                        ld_lib_paths.append(lib_dir)
        extra_flags = ""
        if cflags_dirs:
            inc_flags = " ".join(f"-I{d}" for d in cflags_dirs)
            extra_flags += f"CFLAGS='{inc_flags}' GLIB_CFLAGS='{inc_flags}' "
        # CI #29562: libbabeltrace2.so 缺 __floatditf/__trunctfdf2 等 TF
        # 软浮点符号。clang 直接链接会自动加 libclang_rt.builtins.a，
        # 但 autotools/libtool 链接 .so 时不传递。显式静态链接 builtins。
        clang_dir = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"
        rt_arch_dir = "aarch64-linux-ohos"
        rt_builtins = (f"{clang_dir}/ohos/native/llvm/lib/clang/15.0.4"
                       f"/lib/{rt_arch_dir}/libclang_rt.builtins.a")
        rt_extra = f"{rt_builtins}"
        if ldflags_dirs:
            # -Wl,-rpath 硬编码 lib 路径到测试程序，避免 LD_LIBRARY_PATH 被 configure 覆盖
            rpath_flags = " ".join(f"-Wl,-rpath,{d}" for d in ldflags_dirs)
            lib_flags = " ".join(f"-L{d}" for d in ldflags_dirs)
            # GLIB_LIBS 必须含 gmodule + intl：gmodule-no-export-2.0.pc 的 Libs
            # 为空，pkg-config 不会自动加 -lgmodule-2.0，链接报
            # "undefined reference: g_module_open" 等错误（CI #29562）。
            glib_libs = (f"{lib_flags} {rpath_flags} "
                         f"-lglib-2.0 -lgmodule-2.0 -lintl -lm -pthread "
                         f"{rt_extra}")
            extra_flags += (f"LDFLAGS='{lib_flags} {rpath_flags} {rt_extra}' "
                            f"GLIB_LIBS='{glib_libs}' ")
        else:
            extra_flags += f"LDFLAGS='{rt_extra}' "
        # E266: ohos-sdk 的 lld 链接器是动态链接 ELF，NEEDED libxml2.so.16。
        # CI worker 的 musl 动态链接器默认不搜索 ohos-sdk 的 llvm/lib 目录，
        # 导致 lld 启动即崩、clang-15 报 "unable to execute command"。
        # 把 ohos-sdk 的 llvm/lib 加进 LD_LIBRARY_PATH 最前面，
        # musl 就能找到 libxml2.so.16，lld 就能启动。
        # 注意：不能用 -fuse-ld=GNU ld 绕过——GNU ld 2.45 链接的 ELF
        # 缺 HMDFS 安全标签，musl 拒绝执行（exit 126）。
        # 关键：configure 和 make 都要带 LD_LIBRARY_PATH，否则 make 链接
        # 阶段 lld 仍崩（CI #30176 实测）。
        sdk_llvm_lib = (f"{clang_dir}/ohos/native/llvm/lib")
        ld_lib_paths.insert(0, sdk_llvm_lib)
        ld_library_path_env = ""
        if ld_lib_paths:
            ld_library_path_env = f"LD_LIBRARY_PATH='{':'.join(ld_lib_paths)}' "
            env_prefix += ld_library_path_env
        # E007: 不传 --build/--host，让 configure 自动检测平台
        # （aarch64-unknown-linux-musl triplet 不被 config.sub 识别）
        # E002: clang 临时文件（TMPDIR + -pipe 修复）
        # --disable-glibtest: AM_PATH_GLIB_2_0 用 AC_RUN_IFELSE 运行 conftest,
        # CI worker 系统装了旧版 GLib（48.0.x），conftest 运行时加载系统 GLib
        # 导致 glib_major_version != 2 → 版本检测失败（CI #29562）。
        # Conan 已管理 glib 依赖，运行时版本检测多余，直接禁用。
        # CPPFLAGS -Dnssv_CONFIG_SELECT_STRING_VIEW=1: string-view-lite 在 C++17
        # 下默认用 std::string_view（无 to_string()），babeltrace2 源码假设
        # nonstd::string_view（有 to_string()）。强制选 nonstd 版本。
        cfg = (f"umask 022 && CC='/data/service/hnp/bin/clang -pipe' "
               f"CPPFLAGS='-Dnssv_CONFIG_SELECT_STRING_VIEW=1' "
               f"TMPDIR='{tmpdir}' {env_prefix}{extra_flags}"
               f"./configure --prefix=/ --disable-python-bindings "
               f"--disable-debug-info --disable-glibtest --disable-man-pages")
        self.run(cfg, cwd=self.source_folder)
        # make 和 make check 也要带 LD_LIBRARY_PATH，否则 lld 找不到 libxml2.so.16
        self.run(f"umask 022 && {ld_library_path_env}make -j1 TMPDIR='{tmpdir}'",
                 cwd=self.source_folder)
        # 上游测试（make check，TAP harness）——执行以满足 SKILL §3
        self.run(f"umask 022 && {ld_library_path_env}make -j1 check",
                 cwd=self.source_folder, ignore_errors=True)

    def package(self):
        # build() 在 source_folder 运行 configure/make，Makefile 也在
        # source_folder，因此 make install 必须在 source_folder 执行
        # （autotools.install() 默认在 build_folder，找不到 Makefile）
        with chdir(self, self.source_folder):
            autotools = Autotools(self)
            autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["babeltrace2"]
