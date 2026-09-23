#!/usr/bin/env python3
"""Conan recipe for zeitgeist 1.0.4 on HarmonyOS PC.

Zeitgeist is an event-logging framework for desktop activity.
Autotools + Vala build. Depends on glib, sqlite3, json-glib, vala.
Optional deps (dee-icu, telepathy-glib, valadoc, introspection, python)
disabled or relaxed for OHOS.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import (
    get,
    apply_conandata_patches,
    export_conandata_patches,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.env import Environment


class ZeitgeistConan(ConanFile):
    name = "zeitgeist"
    version = "1.0.4"
    package_type = "library"
    license = "LGPL-2.1"
    homepage = "https://zeitgeist.freedesktop.org"
    url = "https://launchpad.net/zeitgeist"
    description = ("Event-logging framework for desktop activity — "
                   "tracks file usage, browsing, chat and more")
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def requirements(self):
        self.requires("glib/2.84.0.1")
        self.requires("sqlite/3.53.3")
        self.requires("json-glib/1.10.6")
        # glib-2.0.pc 的 Requires: libpcre2-8 需要 libpcre2-8.pc 可被
        # pkg-config 找到。pcre2 是 glib 的传递依赖，若不显式 requires，
        # 在依赖图中被标 Skipped（binary 不下载）→ 干净 CI 缓存里没有
        # pcre2 的 .pc → configure 报 "Package 'libpcre2-8' not found"。
        # 显式 requires 使其成为直接依赖、binary 被下载并进入
        # self.dependencies，下方 generate() 的 pkgconfig 循环即覆盖。
        self.requires("pcre2/10.45")
        # gobject-2.0.pc 的 Requires: libffi 需要 libffi.pc 可被 pkg-config
        # 找到。libffi 是 glib 的传递依赖，与 pcre2 同理——必须显式
        # requires 让其成为直接依赖、binary 下载并进入 self.dependencies，
        # 否则 configure 报 "Package 'libffi', required by 'gobject-2.0'"
        # （此前用 glob 探测缓存路径不可靠：CI 缓存 CONAN_HOME 是
        # .cache/conan2 而非 ~/.conan2，探测落空）。
        self.requires("libffi/3.4.4")
        # gio-2.0.pc 的 Requires: zlib 需要 zlib.pc 可被 pkg-config 找到。
        # zlib 是 glib 的传递依赖（recipe glib1664f39decd98 声明
        # libffi+pcre2+zlib 三个），与 pcre2/libffi 同理——显式 requires
        # 补全 glib 完整传递依赖链，避免 configure 逐个报缺失。
        self.requires("zlib/1.3.1.1")

    def build_requirements(self):
        self.tool_requires("vala/0.56.18")

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True)
        apply_conandata_patches(self)

    def export_sources(self):
        export_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Disable optional deps not in ohpcd / not needed on OHOS
        tc.configure_args += [
            "--with-dee-icu=no",
            "--disable-telepathy",
            "--disable-datahub",
            "--disable-docs",
            "--disable-introspection",
        ]
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()
        # PkgConfigDeps：为所有依赖生成 .pc 到 generators folder（sqlite →
        # sqlite.pc），供下方复制 sqlite3.pc 别名；否则 configure 报
        # "No package 'sqlite3' found"（此前漏掉此生成器，sqlite3.pc
        # 别名从未生效）。
        PkgConfigDeps(self).generate()
        # configure 编译器测试 = clang 调 SDK lld 链接测试程序，而 SDK lld
        # 的 DT_NEEDED 含 libxml2.so.16（在 llvm/lib/）——CI worker 上若
        # LLVM lib 不在 loader 默认搜索路径，lld 运行即失败 →
        # "C compiler cannot create executables"（picotool/libseccomp 先例，
        # works 检查在 CI 运行间不稳定即此因）。用 realpath(clang) 推导
        # SDK llvm lib 并注入 LD_LIBRARY_PATH。
        _llvm_lib = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.realpath("/data/service/hnp/bin/clang"))),
            "lib")
        if os.path.isdir(_llvm_lib):
            self.buildenv_info.prepend("LD_LIBRARY_PATH", _llvm_lib)

        # Point pkg-config at conan deps (glib/gio-unix/json-glib/sqlite)
        env = Environment()
        # 显式 requires 的 pcre2/libffi（glib 传递依赖）已进入
        # self.dependencies，由下方循环自动加入 pkgconfig 路径——
        # 不再用 glob 探测缓存路径（CI 缓存 CONAN_HOME 是
        # .cache/conan2 而非 ~/.conan2，glob 探测不可靠）。
        for dep in self.dependencies.values():
            if dep.package_folder:
                pkg_path = os.path.join(dep.package_folder, "lib",
                                        "pkgconfig")
                if os.path.isdir(pkg_path):
                    env.append_path("PKG_CONFIG_PATH", pkg_path)
        # sqlite3.pc 由 PkgConfigDeps 生成时名为 sqlite.pc，configure 找
        # sqlite3.pc——复制一份别名
        gen = self.generators_folder
        for name in ("sqlite.pc",):
            src = os.path.join(gen, name)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(gen, "sqlite3.pc"))
        # valac wrapper：vala 包自带 valac 的默认 datadir（/usr/share/
        # vala-0.56/vapi）在本环境不存在，且其运行依赖 vala/glib 动态库——
        # 仿 xmlbird：wrapper 注入 --vapidir + LD_LIBRARY_PATH（vala 与
        # glib 的 lib/ 前置）
        wrap_dir = os.path.join(self.build_folder, "binwrap")
        os.makedirs(wrap_dir, exist_ok=True)
        self._wrap_dir = wrap_dir
        vala_dep = self.dependencies.build.get("vala")
        if vala_dep and vala_dep.package_folder:
            vp = vala_dep.package_folder
            vapi_dir = os.path.join(vp, "share", "vala-0.56", "vapi")
            valac_bin = os.path.join(vp, "bin", "valac-0.56")
            if not os.path.isfile(valac_bin):
                valac_bin = os.path.join(vp, "bin", "valac")
            ld = os.path.join(vp, "lib", "vala-0.56") + ":" + os.path.join(vp, "lib")
            for dep in self.dependencies.values():
                if dep.package_folder and ("glib" in str(dep.ref)):
                    ld = ld + ":" + os.path.join(dep.package_folder, "lib")
            vapidir_args = f'--vapidir="{vapi_dir}"' if os.path.isdir(vapi_dir) else ""
            vala_wrap = os.path.join(wrap_dir, "valac")
            with open(vala_wrap, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "#!/bin/sh\n"
                    f'exec env LD_LIBRARY_PATH="{ld}:$LD_LIBRARY_PATH" '
                    f'"{valac_bin}" {vapidir_args} "$@"\n'
                )
            os.chmod(vala_wrap, 0o755)
            self.output.info(f"valac wrapper → {ld}")
            if vapidir_args:
                self.output.info(f"valac wrapper --vapidir={vapi_dir}")
            env.prepend_path("PATH", wrap_dir)
        # 自定义 env（PKG_CONFIG_PATH + valac PATH）存独立脚本，不覆盖
        # conan 聚合的 conanbuild.sh（AutotoolsToolchain/Deps 生成）
        # 关键：works 检查（configure 的 ac_link_default）会带 AutotoolsDeps
        # 注入的 LIBS（含 -lintl）链接 conftest——OHOS libintl 是 glib 的
        # stub/代理库（libgio-2.0.so 引用 g_libintl_* 未定义符号）→ ld.lld
        # 严格模式报 undefined reference → "C compiler cannot create
        # executables"。works 检查只需编译器能链接空程序，不需要任何依赖
        # 库——在 zeitgeist_env 里清空 LIBS（build() 时 env 列表将其放在
        # conanbuild 之后覆盖），pkg-config 检查/make 用 configure 固化的
        # ZEITGEIST_LIBS，不受影响。
        env.define("LIBS", "")
        env.vars(self, scope="build").save_script("zeitgeist_env")

    def build(self):
        # E011: config.status on HMDFS — copy to writable cache
        work = "/data/storage/el2/base/cache/zeitgeist-src"
        shutil.rmtree(work, ignore_errors=True)
        shutil.copytree(self.source_folder, work, symlinks=True)
        # OHOS quirk（dee 1.2.7 同款实测）：configure 的 config.status 模板
        # 用 umask 077 建临时目录（0700），在 cache 路径上 owner 无法写 →
        # config.status 生成文件 "Permission denied" → configure 走完所有
        # 检查后在最后一步 exit 1。configure 前把 umask 077 改 022。
        conf = os.path.join(work, "configure")
        if os.path.exists(conf):
            with open(conf) as f:
                s = f.read()
            if "umask 077" in s:
                with open(conf, "w") as f:
                    f.write(s.replace("umask 077", "umask 022"))
        # E007: config.guess cannot identify OHOS
        cache_file = os.path.join(work, "cross.cache")
        # zeitgeist configure 是新版 autoconf 2.71：AC_PROG_CC 不读
        # ac_cv_prog_cc_works/ac_cv_prog_cc_cross 缓存变量（旧版才认），
        # cross 判定读 $cross_compiling（configure 1442-1448 行：有 --host
        # 且 --host≠--build 才置 yes）。仅传 --build → cross_compiling=no
        # → 尝试运行 conftest → CI 沙箱无法运行 → "cannot run C compiled
        # programs"/"C compiler cannot create executables"。
        # 修复：--host=aarch64-unknown-linux-ohos（config.sub 补丁 0002 认
        # linux-ohos*）与 --build 不同 → cross_compiling=yes → 跳过运行测试
        with open(cache_file, "w") as f:
            f.write("ac_cv_prog_cc_works=yes\n"
                    "ac_cv_prog_cc_cross=yes\n")

        # 修复依赖包的 libtool 包装问题：
        # 1) 依赖 .la 的 libdir 硬编码 '//lib'/'/lib'（pcre2 包的
        #    libpcre2-8.la/libpcre2-posix.la）——libtool 链接时读 .la 的
        #    libdir 并固化进中间 .la 的 dependency_libs，最终展开时报
        #    "cannot find //lib/libpcre2-8.la"。删除 .la 让 libtool 退化
        #    用 -L/-l 直接链接（.pc 提供正确路径），彻底绕开错误 libdir。
        # 2) 依赖 .pc 的 prefix=/ 硬编码（pcre2 的 .pc 里 prefix=/ →
        #    libdir=//lib → pkg-config 返回 -L//lib）。只精确替换整行的
        #    "prefix=/"，避免子串替换破坏已是正确路径的 .pc
        #    （"prefix=/storage/..." 不能被误改成重复路径）。
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            lib_dir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(lib_dir):
                for name in os.listdir(lib_dir):
                    if name.endswith(".la"):
                        os.remove(os.path.join(lib_dir, name))
                        self.output.info(f"removed {name}")
            pc_dir = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pc_dir):
                # -lintl 不能移除：OHOS 上 glib 的 libglib-2.0.so/libgio-2.0.so
                # 引用 g_libintl_* 符号，由 glib 包内 libintl 代理库
                # （libintl.so）提供。链接可执行文件（如 zeitgeist-daemon）
                # 时若缺它 → ld.lld --no-allow-shlib-undefined 报 undefined
                # reference（CI 实证：移除 -lintl 后 daemon 链接失败）。
                # 把 -lintl 替换为 glib 包内 libintl.so 完整路径（提供
                # g_libintl_*），而非简单移除。
                glib_lib_dir = ""
                for _dep in self.dependencies.values():
                    if _dep.ref and "glib" in str(_dep.ref):
                        _g = os.path.join(_dep.package_folder, "lib")
                        if os.path.isfile(os.path.join(_g, "libintl.so")):
                            glib_lib_dir = _g
                            break
                for name in os.listdir(pc_dir):
                    if not name.endswith(".pc"):
                        continue
                    pc_path = os.path.join(pc_dir, name)
                    with open(pc_path) as f:
                        content = f.read()
                    # 仅当该行恰好是 "prefix=/"（错误硬编码）时替换
                    lines = content.split("\n")
                    new_lines = []
                    changed = False
                    for ln in lines:
                        if ln.strip() == "prefix=/":
                            new_lines.append(
                                f"prefix={dep.package_folder}")
                            changed = True
                        elif ln.startswith("Libs:") and "-lintl" in ln:
                            if glib_lib_dir:
                                new_lines.append(
                                    ln.replace(
                                        "-lintl",
                                        os.path.join(glib_lib_dir,
                                                     "libintl.so")).replace(
                                        "  ", " ").strip())
                            else:
                                new_lines.append(
                                    ln.replace("-lintl", "").replace(
                                        "  ", " ").strip())
                            changed = True
                        else:
                            new_lines.append(ln)
                    if changed:
                        with open(pc_path, "w") as f:
                            f.write("\n".join(new_lines))
                        self.output.info(f"fixed pc {name}")

        # 不用 shell source conanbuild.sh（会全量灌入环境变量 → printenv
        # Argument list too long / Error -11）；conan 直接以 env 列表注入
        # 子进程环境：zeitgeist_env（PKG_CONFIG_PATH + valac PATH）+ 默认
        # conanbuild（AutotoolsToolchain/Deps 编译器标志）
        self.run(
            f"./configure --cache-file={cache_file} "
            f"--build=aarch64-unknown-linux-gnu "
            f"--host=aarch64-unknown-linux-ohos "
            f"--prefix={self.package_folder} "
            "--enable-shared --disable-static "
            "--with-dee-icu=no --disable-telepathy "
            "--disable-datahub --disable-docs --disable-introspection "
            "|| { echo '===== CONFIG.LOG (works check) ====='; "
            "grep -n -A8 'checking whether the C compiler works' "
            "config.log | head -60; "
            "grep -nE 'ld\\.lld|error while loading|cannot find|"
            "undefined reference|error:' config.log | head -40; "
            "echo '===== CONFIG.LOG (tail) ====='; "
            "tail -80 config.log; exit 1; }",
            cwd=work,
            # 顺序：conanbuild 在前、zeitgeist_env 在后——zeitgeist_env 里
            # LIBS="" 覆盖 conanbuild 注入的 LIBS（含 -lintl），works 检查
            # 链接空程序不被 OHOS libintl stub 污染。
            env=["conanbuild", "zeitgeist_env"],
        )
        # make 必须用 conan vala 包的 valac wrapper：configure 探测到的
        # VALAC 是系统 /usr/local/bin/valac（静态链接 glib），启动即崩
        # "cannot register existing type gchar"。用 generate() 建的
        # binwrap/valac（动态链接 valac + --vapidir + LD_LIBRARY_PATH）
        # 防御：make 前扫描 work 下生成的 Makefile 和中间 .la，把残留的
        # //lib（pcre2 依赖路径硬编码 /lib 经 configure 固化进链接参数）
        # 统一替换为 pcre2 实际 lib 路径，杜绝 libtool 展开 dependency_libs
        # 时 "cannot find //lib/libpcre2-8.la"。
        pcre2_lib = ""
        for dep in self.dependencies.values():
            if dep.ref and "pcre2" in str(dep.ref):
                pcre2_lib = os.path.join(dep.package_folder, "lib")
        if pcre2_lib:
            for _root, _dirs, _files in os.walk(work):
                for _f in _files:
                    if _f.endswith((".la", ".pc")) or "Makefile" in _f:
                        _p = os.path.join(_root, _f)
                        with open(_p) as fh:
                            _c = fh.read()
                        if "//lib" in _c:
                            _n = _c.replace("//lib", pcre2_lib)
                            with open(_p, "w") as fh:
                                fh.write(_n)
                            self.output.info(
                                f"fixed //lib in {os.path.relpath(_p, work)}")
        self.run(
            f"make -j1 VALAC={self._wrap_dir}/valac",
            cwd=work,
            env=["conanbuild", "zeitgeist_env"],
        )

    def package(self):
        work = "/data/storage/el2/base/cache/zeitgeist-src"
        # Autotools.install() 不接受 cwd 参数——直接跑 make install，
        # 与 build() 一致（work 目录 + zeitgeist_env/conanbuild 环境）
        self.run(
            f"make install VALAC={self._wrap_dir}/valac",
            cwd=work,
            env=["conanbuild", "zeitgeist_env"],
        )

    def package_info(self):
        self.cpp_info.libs = ["zeitgeist-2.0"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include/zeitgeist-2.0"]
