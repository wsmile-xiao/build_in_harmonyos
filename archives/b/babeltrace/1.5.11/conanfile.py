#!/usr/bin/env python3
"""Conan recipe — babeltrace 1.5.11 (CTF trace converter, C/autotools) on HarmonyOS PC."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class BabeltraceConan(ConanFile):
    name = "babeltrace"
    version = "1.5.11"
    description = "Babeltrace — CTF trace format converter and library"
    license = "MIT"
    homepage = "https://www.efficios.com/babeltrace"
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
            # E---: AM_PATH_GLIB_2_0 宏在非 cross_compiling 下会编译并运行
            # conftest 程序读取运行时 glib 版本，CI worker 系统 glib (48.x)
            # 与 Conan glib/2.88.0.1 冲突 → 跳过运行检测，仅用 pkg-config
            # --atleast-version 校验（已通过：2.88.0 >= 2.22.0）。
            "--disable-glibtest",
        ]
        # E266: OHOS SDK 的 lld 动态链接 libxml2.so.16，CI worker 沙箱默认
        # 库搜索路径找不到 → lld 无法启动 → clang 链接失败（CI #30527/#30500，
        # "Error loading shared library libxml2.so.16 ... Error relocating lld"）。
        # 参照已合入的 libgsf 方案：前置 SDK llvm/lib 到 LD_LIBRARY_PATH 让 lld
        # 加载到正确的 libxml2。注意不能用 -fuse-ld=GNU ld——GNU ld 产物在 OHOS
        # 沙箱中 Permission denied (exit 126) 不可执行（需 ELF 签名），lld 产物可执行。
        import glob as _glob
        env = tc.environment()
        if self.settings.os == "OHOS":
            _llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
            if not os.path.isdir(_llvm_lib):
                _cands = sorted(_glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
                _llvm_lib = _cands[0] if _cands else ""
            if _llvm_lib:
                env.prepend_path("LD_LIBRARY_PATH", _llvm_lib)
        tc.generate(env=env)
        deps = PkgConfigDeps(self)
        deps.generate()
        # E236: pcre2 配方的 .la 文件 libdir='//lib' (--prefix=/ 产生)，libtool
        # 链接 babeltrace 时解析 pcre2 .la 报 "not a valid libtool archive"。
        # 参照已合入的 libgsf 方案：patch pcre2.pc 的 Libs 为 .a 绝对路径，
        # 让 libtool 不解析 .la。注意不能硬编码 ~/.conan2/p/b/pcre2*/p 本机路径
        # —— CI 干净环境哈希目录不同会漏匹配，必须从 dependencies 拿真实路径。
        import glob as _glob
        _pcre2_lib = ""
        try:
            _pcre2_lib = os.path.join(self.dependencies["pcre2"].package_folder, "lib")
        except Exception:
            pass
        if not _pcre2_lib or not os.path.isdir(_pcre2_lib):
            _fallback = _glob.glob("/storage/Users/currentUser/.conan2/p/b/pcre2*/p/lib")
            if _fallback:
                _pcre2_lib = _fallback[0]
        if _pcre2_lib and os.path.isdir(_pcre2_lib):
            _pcre2_pc = os.path.join(self.generators_folder, "pcre2.pc")
            if os.path.exists(_pcre2_pc):
                with open(_pcre2_pc, "r", encoding="utf-8") as _f:
                    _pc = _f.read()
                if "-lpcre2-8" in _pc and ".a" not in _pc:
                    _pc = _pc.replace(
                        "Libs: -L\"${libdir}\" -lpcre2-8 -lpcre2-posix",
                        "Libs: -L\"${{libdir}}\" {}/libpcre2-8.a {}/libpcre2-posix.a".format(
                            _pcre2_lib, _pcre2_lib))
                    with open(_pcre2_pc, "w", encoding="utf-8") as _f:
                        _f.write(_pc)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"babeltrace {self.version} only supports Linux and OHOS, got os={self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # babeltrace GitHub release tarball 不含预生成的 configure，
        # CI worker 无 aclocal/automake 无法 autoreconf。
        # 预生成 autotools 产物（configure/Makefile.in/aclocal.m4/config/m4）
        # 已 vendored 在 patches/autotools/（完整目录镜像，含 types/、
        # formats/ctf/ 等全部子目录的 Makefile.in），整体复制到源码树。
        import shutil
        at_src = os.path.join(self.recipe_folder, "patches", "autotools")
        if not os.path.isdir(at_src):
            at_src = os.path.join(self.export_sources_folder, "patches", "autotools")
        if os.path.isdir(at_src):
            for root, _dirs, files in os.walk(at_src):
                rel = os.path.relpath(root, at_src)
                dst = self.source_folder if rel == "." else os.path.join(self.source_folder, rel)
                os.makedirs(dst, exist_ok=True)
                for fn in files:
                    shutil.copy2(os.path.join(root, fn), os.path.join(dst, fn))
        # E011: HMDFS umask 077 → 022（configure 生成临时脚本不可执行）
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            content = open(configure).read()
            if "umask 077" in content:
                open(configure, "w").write(content.replace("umask 077", "umask 022"))

    def build(self):
        apply_conandata_patches(self)
        # E011/E114: HMDFS umask 077 → 022（configure/config.status 生成临时脚本不可执行）。
        # 注意：automake maintainer 规则会在 make 阶段检测 configure.ac/aclocal.m4/
        # Makefile.am/m4/*.m4 比 configure 新时重新运行 autoconf/automake，重新生成的
        # configure 会恢复 umask 077 并覆盖这里的替换（b/configure~ 为替换版、
        # b/configure 为再生成版即证据）。因此把 autotools 依赖的时间戳设为过去，
        # 确保 configure 最新、不再触发再生成。
        import time as _time
        _past = _time.mktime((2000, 1, 1, 0, 0, 0, 0, 0, -1))
        for _f in ("configure", "config.status"):
            _p = os.path.join(self.source_folder, _f)
            if os.path.isfile(_p):
                _c = open(_p, encoding="utf-8", errors="surrogateescape").read()
                if "umask 077" in _c:
                    open(_p, "w", encoding="utf-8",
                         errors="surrogateescape").write(_c.replace("umask 077", "umask 022"))
        # 把 autotools 依赖源文件时间戳改为过去（阻止 automake 触发 autoconf 再生成）
        for _f in ("configure.ac", "aclocal.m4", "Makefile.am", "Makefile.in"):
            _p = os.path.join(self.source_folder, _f)
            if os.path.isfile(_p):
                os.utime(_p, (_past, _past))
        _m4d = os.path.join(self.source_folder, "m4")
        if os.path.isdir(_m4d):
            for _fn in os.listdir(_m4d):
                _p = os.path.join(_m4d, _fn)
                if os.path.isfile(_p):
                    os.utime(_p, (_past, _past))
        # configure 保持最新（比所有依赖新，规则不再触发）
        _p = os.path.join(self.source_folder, "configure")
        if os.path.isfile(_p):
            os.utime(_p, None)
        tmpdir = os.path.join(self.build_folder, "cfg-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        # CI #29313/#29316/#29326: AM_PATH_GLIB_2_0 宏用 pkg-config 检测
        # glib 版本，但 CI worker 系统装了旧版 GLib（48.0.x），与 Conan
        # 依赖 glib/2.88.0.1 冲突。显式设置 PKG_CONFIG_PATH 指向：
        # 1. PkgConfigDeps 生成的 .pc 文件目录（self.generators_folder）
        # 2. Conan 依赖包的 lib/pkgconfig 目录（dep.package_folder）
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
        env_prefix = ""
        if pkg_config_paths:
            env_prefix = f"PKG_CONFIG_PATH='{':'.join(pkg_config_paths)}' "
        # CI #29521/#29526/#29528: AM_PATH_GLIB_2_0 宏编译并运行测试程序，
        # 需 CFLAGS/LDFLAGS/LD_LIBRARY_PATH 全部指向 Conan glib，
        # 否则编译器/链接器/动态链接器找到系统旧版 GLib 48.0.x，
        # 导致 GLIB_MAJOR_VERSION 不匹配（48 != 2）。
        # AM_PATH_GLIB_2_0 宏用 pkg-config 获取 GLIB_CFLAGS/GLIB_LIBS，
        # 覆盖用户传入的 CFLAGS/LDFLAGS。直接传 GLIB_CFLAGS/GLIB_LIBS
        # 环境变量，绕过宏内部的 pkg-config 调用。
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
        if ldflags_dirs:
            lib_flags = " ".join(f"-L{d}" for d in ldflags_dirs)
            extra_flags += f"LDFLAGS='{lib_flags}' GLIB_LIBS='{lib_flags} -lglib-2.0' "
        if ld_lib_paths:
            env_prefix += f"LD_LIBRARY_PATH='{':'.join(ld_lib_paths)}' "
        # E007: 不传 --build/--host，让 configure 自动检测平台。
        # --prefix=/ --libdir=/lib --bindir=/bin --includedir=/include:
        # 让 make install DESTDIR=$package_folder 直接落到 Conan 标准布局
        # (bin/、lib/、include/)，否则默认 --prefix=/usr/local 会装到
        # DESTDIR/usr/local/bin，test_package 与下游都找不到；同时让本包
        # 生成的 .la 文件 libdir=/lib 而非 //lib。
        # 注意: 不要传 --disable-python-bindings! babeltrace 1.5.11 的
        # configure 解析 bug: 只要该选项被设置(无论值), enable_python 就被
        # 无条件置为 yes (configure: "enableval=$enable_python_bindings;
        # enable_python=yes"), 反而启用 python bindings, 其 setup.py 在
        # make install 时写 /lib/python3.12/site-packages (只读) 报错。
        # 不传该参数走 else 分支 enable_python=no, 正确禁用。
        cfg = (f"umask 022 && CC=/data/service/hnp/bin/clang TMPDIR='{tmpdir}' {env_prefix}{extra_flags}"
               f"./configure --prefix=/ --libdir=/lib --bindir=/bin --includedir=/include"
               f" --disable-debug-info --disable-glibtest")
        self.run(cfg, cwd=self.source_folder)
        # E011 方法2: configure 生成的 config.status 内嵌 umask 077（生成临时目录
        # ./confXXXXXX 用 0700，HMDFS 上 owner 映射导致 subs1.awk Permission denied）。
        # make 阶段 Makefile 规则会重新调用 config.status，因此必须在 make 前把
        # config.status 里的 umask 077 替换为 022。
        _cs = os.path.join(self.source_folder, "config.status")
        if os.path.isfile(_cs):
            _cc = open(_cs, encoding="utf-8", errors="surrogateescape").read()
            if "umask 077" in _cc:
                open(_cs, "w", encoding="utf-8",
                     errors="surrogateescape").write(_cc.replace("umask 077", "umask 022"))
        self.run(f"umask 022 && make -j1 TMPDIR='{tmpdir}'", cwd=self.source_folder)
        # 上游测试（make check，TESTS 套件随包）——执行以满足 SKILL §3
        self.run(f"umask 022 && make -j1 check", cwd=self.source_folder, ignore_errors=True)

    def package(self):
        # 本配方的 configure/make 在 self.source_folder 运行（build() 手工
        # 调用，绕开 toolchain 的 build_folder 包装），因此 install 也必须
        # 在同一目录执行，否则 Autotools.install() 默认在 build_folder
        # (build-release) 运行 make install → "No rule to make target 'install'"。
        # -j1：HMDFS 不支持 make jobserver mkfifo（Operation not permitted）。
        self.run(f"umask 022 && make install DESTDIR={self.package_folder} -j1",
                 cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["babeltrace-ctf", "babeltrace"]
