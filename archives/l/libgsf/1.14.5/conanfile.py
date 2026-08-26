#!/usr/bin/env python3
"""Conan recipe for libgsf 1.14.5 — GNOME structured file format library (C).

libgsf 是 GNOME 的 OLE2/OOXML 等结构化文件格式库（LGPL-2.1），Autotools
构建（自带 configure）。核心库 libgsf 依赖 glib-2.0/libxml-2.0/zlib
（制品仓均发布）；libgsf-gnome 子库依赖 gnome-vfs/gconf 等老 GNOME 组件
（制品仓无）→ 禁用 --without-gnome。

OHOS 适配:
- configure 用 --build=aarch64-linux --host=aarch64-linux（鸿蒙 clang
  驱动仍目标 aarch64-linux-ohos）；
- TMPDIR 注入 build 内可写目录（CI 沙箱 TMPDIR 不可写，configure
  conftest 阶段需写临时文件）；
- umask 077 前置修复（鸿蒙 HMDFS 拦 077 临时目录）；
- 测试: test_package 用 gsf-1 头文件 + gsf_input 读内存文件验证库可用。
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import copy, get, load, save
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps


class LibgsfConan(ConanFile):
    name = "libgsf"
    version = "1.14.5"
    description = "Structured File Library (OLE2, OOXML, etc.) for GNOME"
    license = "LGPL-2.1"
    homepage = "https://gitlab.gnome.org/GNOME/libgsf"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def requirements(self):
        # 核心依赖（制品仓均发布）
        self.requires("glib/2.84.0")
        self.requires("libxml2/2.15.3")
        self.requires("zlib/1.3.1")
        # gettext：libgsf-1.so 引用 gettext/textdomain 等符号（通过 glib 的
        # pkg-config 传递），显式 requires 使依赖图可见（test_package 链接
        # -lintl 需要）
        self.requires("gettext/0.22.5")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        # compat/config.sub：libgsf 1.14.5 自带 config.sub（2009 版）不认识
        # aarch64——用新版替换（R39 合规，config.sub 为构建工具非源码）
        copy(self, "compat/*", self.recipe_folder, self.export_sources_folder)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--build=aarch64-linux",
                "--host=aarch64-linux",
                # libgsf-gnome 依赖 gnome-vfs/gconf（老 GNOME 组件，
                # 制品仓无）→ 仅构建核心 libgsf
                "--without-gnome",
                "--disable-gtk-doc",
            ]
        )
        tc.generate()
        # 注意：TMPDIR 不再用 buildenv_info 注入——CI 沙箱中 buildenv
        # 链路不生效，且 autotools.configure() 以 env="conanbuild" 运行，
        # conanbuild.sh 携带的 TMPDIR 会覆盖 build() 里 os.environ 的注入。
        # 统一在 build() 内用 os.environ 直接注入（bogofilter 验证有效）。
        VirtualBuildEnv(self).generate()
        # pkg-config 依赖路径（PkgConfigDeps 生成 glib-2.0.pc 等）
        deps = PkgConfigDeps(self)
        deps.generate()
        # PKG_CONFIG_PATH 注入：PkgConfigDeps 生成的 .pc 在 build 目录；
        # 依赖包 pkgconfig 目录也加入。注意：不用 buildenv_info 注入——
        # 与 TMPDIR 同型问题（CI 沙箱 conanbuild 环境覆盖 build() 的
        # os.environ 注入，configure 的 PKG_CHECK_MODULES 找不到
        # glib-2.0.pc → conftest 失败）。统一在 build() 内用 os.environ
        # 直接注入。

    def _patch_configure_umask(self, build):
        path = os.path.join(build, "configure")
        if not os.path.exists(path):
            return
        content = load(self, path)
        fixed = content.replace("umask 077 && mktemp", "mktemp")
        fixed = fixed.replace("umask 077 && mkdir", "mkdir")
        # intltool 检查（鸿蒙无 perl）：--disable-nls 已传，po/ 不参与构建
        # ——跳过 perl/XML::Parser 三连检查（AM_GLIB_GNU_GETTEXT 宏引入）
        fixed = fixed.replace(
            'if test -z "$INTLTOOL_PERL"; then',
            'if false; then  # OHOS: no perl, nls disabled',
        )
        fixed = fixed.replace(
            'if test -z "`$INTLTOOL_PERL -v | fgrep \'5.\' 2> /dev/null`"; then',
            'if false; then  # OHOS: no perl, nls disabled',
        )
        fixed = fixed.replace(
            'if test "x" != "xno-xml"; then',
            'if test "x" = "xno-xml"; then  # OHOS: skip xml-parser check',
        )
        if fixed != content:
            save(self, path, fixed)
            self.output.info("patched configure: removed umask 077 + intltool checks")
        # po/Makefile.in.in：禁用 .gmo 目录构建（鸿蒙无 msgfmt/GMSGFMT，
        # --disable-nls 后仍进入 po/ 构建 es.gmo 等）
        po_mk = os.path.join(build, "po", "Makefile.in.in")
        if os.path.exists(po_mk):
            pcontent = load(self, po_mk)
            pfixed = pcontent.replace(
                "all-yes: $(CATALOGS)", "all-yes:  # OHOS: no msgfmt"
            )
            if pfixed != pcontent:
                save(self, po_mk, pfixed)
                self.output.info("patched po/Makefile.in.in: disabled gmo builds")
        # gsf-input-http.c：制品仓 libxml2 无 xmlNanoHTTP* 符号（nanohttp
        # 模块未启用）——不移除源文件（gsf 主程序仍引用 gsf_input_http_get_type，
        # 移除会导致链接失败），改为 patch 其 xmlNanoHTTP 调用为 stub：
        # HTTP 输入函数保持存在，运行时返回失败（可接受的退化）
        gsf_http = os.path.join(build, "gsf", "gsf-input-http.c")
        if os.path.exists(gsf_http):
            hc = load(self, gsf_http)
            hf = hc
            hf = hf.replace(
                "xmlNanoHTTPClose ((gpointer) input->ctx);",
                "/* OHOS stub: no libxml2 nanohttp */",
            )
            hf = hf.replace(
                "ctx = xmlNanoHTTPOpen (url, &content_type);",
                "ctx = NULL;  /* OHOS stub: no nanohttp */",
            )
            hf = hf.replace(
                "gsf_input_set_size (GSF_INPUT (obj), xmlNanoHTTPContentLength (ctx));",
                "gsf_input_set_size (GSF_INPUT (obj), 0);  /* OHOS stub */",
            )
            hf = hf.replace(
                "nread = xmlNanoHTTPRead (ctx, buffer, num_bytes - total_read);",
                "nread = 0;  /* OHOS stub: no nanohttp */",
            )
            if hf != hc:
                save(self, gsf_http, hf)
                self.output.info(
                    "patched gsf-input-http.c: xmlNanoHTTP* -> stubs")
        # gsf-config.h：禁用 ENABLE_NLS（否则 glibintl.h 把 gettext 宏映射为
        # g_libintl_* 符号，glib 包 --disable-nls 构建未提供 → gsf 可执行链接
        # undefined g_libintl_bind_textdomain_codeset）。改为 G_DISABLE_NLS，
        # 直接用 libintl 的 gettext（已链接真实 libintl.a）。
        cfg_h = os.path.join(build, "gsf-config.h")
        if os.path.exists(cfg_h):
            cc_h = load(self, cfg_h)
            cf = cc_h
            cf = cf.replace("#define ENABLE_NLS 1",
                            "/* #undef ENABLE_NLS */\n#define G_DISABLE_NLS 1")
            if cf != cc_h:
                save(self, cfg_h, cf)
                self.output.info("patched gsf-config.h: disable NLS")

    def build(self):
        # PKG_CONFIG_PATH 用 os.environ 注入（buildenv_info 在 generate()
        # 里 VirtualBuildEnv.generate() 之后定义不生效；os.environ 让
        # configure 子进程直接继承——bart/bogofilter 验证过的可靠方式）。
        # PkgConfigDeps 生成的 .pc 在 build 目录；依赖包 pkgconfig 目录也加入。
        pkg_dirs = [self.build_folder]
        for dep in ("glib", "libxml2", "zlib"):
            dep_pkg = self.dependencies[dep].package_folder
            pkg_dirs.append(os.path.join(dep_pkg, "lib", "pkgconfig"))
        os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(pkg_dirs)
        # TMPDIR 用 os.environ 直接注入（bogofilter 教训：buildenv_info
        # 注入在 CI 沙箱不生效——CI TMPDIR=/data/storage/el2/base/cache
        # 不可写，clang 链接 conftest 失败 → "C compiler cannot create
        # executables"）。注入 build 目录内可写 .conan_tmp，configure 子进程
        # 直接继承。
        _tmp_dir = os.path.join(self.build_folder, ".conan_tmp")
        os.makedirs(_tmp_dir, exist_ok=True)
        os.environ["TMPDIR"] = _tmp_dir
        # configure 的 AM_PATH_PYTHON 检查需找到解释器（鸿蒙 python3）
        os.environ["PYTHON"] = "python3"
        # LDFLAGS 注入 gettext 包 lib 路径（放链接命令开头）——libgsf 链接
        # 时 -lintl 默认命中 PkgConfigDeps 聚合的空壳 libintl.a（git- 前缀
        # dep_pkgs，无 gettext 符号），导致 libgsf-1.so 残留未定义
        # gettext/textdomain 符号（运行时加载即崩 Error 139）。gettext 包
        # 的真实 libintl.a 含 4 个 gettext 符号。
        gt_pkg = self.dependencies["gettext"].package_folder
        # 用 libintl.a 绝对路径（而非 -L/-lintl）：-lintl 会命中 PkgConfigDeps
        # 聚合的空壳 libintl.a（git- 前缀 dep_pkgs，无 gettext 符号）；
        # gettext 包 libintl.a 无同名 .la，libtool 按普通归档直接链接，
        # 正确解析 libgsf-1.so 残留的 gettext/textdomain 符号
        os.environ["LDFLAGS"] = os.path.join(gt_pkg, "lib", "libintl.a")
        # g_libintl_* 符号 stub（glibintl.h 宏映射，glib 包 --disable-nls
        # 未提供）：编译 compat/g_libintl_stub.c 并加入链接
        stub_src = os.path.join(
            self.source_folder, "compat", "g_libintl_stub.c")
        stub_o = os.path.join(self.build_folder, "g_libintl_stub.o")
        if os.path.exists(stub_src):
            self.run(f"{os.environ.get('CC', 'clang')} -c {stub_src} -o {stub_o}",
                     cwd=self.build_folder)
            os.environ["LDFLAGS"] += f" {stub_o}"
        # 依赖 .la 的 libdir='//lib'（conan 包 prefix=/ 拼接错误）——libtool
        # 创建 libgsf-1.la 时按 libdir 读取依赖 .la 失败（sed //lib/...）。
        # 修正 pcre2/libffi 的 .la：libdir 与 dependency_libs 中的 //lib 引用
        # 一并替换为真实 lib 路径。
        for dep in ("pcre2", "libffi"):
            dep_pkg = self.dependencies.get(dep)
            if not dep_pkg:
                continue
            dep_lib = os.path.join(dep_pkg.package_folder, "lib")
            for la_name in os.listdir(dep_lib):
                if not la_name.endswith(".la"):
                    continue
                la_path = os.path.join(dep_lib, la_name)
                lac = load(self, la_path)
                fixed_la = lac.replace("libdir='//lib'",
                                       f"libdir='{dep_lib}'")
                fixed_la = fixed_la.replace(
                    "//lib/", f"{dep_lib}/")
                if fixed_la != lac:
                    save(self, la_path, fixed_la)
                    self.output.info(
                        f"patched {la_name}: libdir/deps -> {dep_lib}")
        # 与 bogofilter 同型：configure 运行前修 umask 077
        self._patch_configure_umask(self.build_folder)
        # 用 compat/config.sub（新版，支持 aarch64）覆盖源码自带旧版
        compat_sub = os.path.join(
            self.source_folder, "compat", "config.sub")
        if os.path.exists(compat_sub):
            save(self, os.path.join(self.build_folder, "config.sub"),
                 load(self, compat_sub))
            self.output.info("patched config.sub: aarch64 support")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # 鸿蒙要求共享库/可执行 ELF 有效签名才能加载（libtool 生成的
        # libgsf-1.so 无有效 .codesign，运行时加载段错误）——对 lib/*.so
        # 与 bin/* 可执行统一重签名（同 bart/protobuf 模板）
        self._sign_installed_elfs()

    def _elf_type(self, path):
        try:
            with open(path, "rb") as binary:
                header = binary.read(18)
        except OSError:
            return None
        if header[:4] != b"\x7fELF":
            return None
        return header[16]  # e_type: 2=EXEC, 3=DYN

    def _has_codesign_section(self, objdump, path):
        result = subprocess.run(
            [objdump, "-h", path], capture_output=True, text=True, timeout=60)
        return any(".codesign" in line.split()
                   for line in result.stdout.splitlines())

    def _sign_installed_elfs(self):
        import shutil
        import stat
        import tempfile

        binaries = []
        for root, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                candidate = os.path.join(root, filename)
                if os.path.islink(candidate):
                    continue
                if self._elf_type(candidate) in (2, 3):
                    binaries.append(candidate)
        if not binaries:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        objdump = "/data/service/hnp/bin/llvm-objdump"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for binary in sorted(binaries):
            original_mode = stat.S_IMODE(os.stat(binary).st_mode)
            with tempfile.TemporaryDirectory(
                prefix=".conan-sign-", dir=os.path.dirname(binary)
            ) as temp_dir:
                unsigned = os.path.join(temp_dir, "unsigned")
                signed = os.path.join(temp_dir, "signed")
                shutil.copy2(binary, unsigned)
                if self._has_codesign_section(objdump, unsigned):
                    subprocess.run(
                        [objcopy, "--remove-section", ".codesign", unsigned],
                        check=True, capture_output=True, text=True, timeout=60)
                result = subprocess.run(
                    [signer, "sign", "-inFile", unsigned, "-outFile", signed,
                     "-selfSign", "1"],
                    capture_output=True, text=True, timeout=60)
                if result.returncode != 0 or not os.path.isfile(signed):
                    self.output.warn(
                        f"sign {binary} failed: {result.stderr.strip()[:200]}")
                    continue
                os.replace(signed, binary)
                os.chmod(binary, original_mode)

    def package_info(self):
        self.cpp_info.libs = ["gsf-1"]
        self.cpp_info.set_property("pkg_config_name", "libgsf-1")
        self.cpp_info.includedirs = ["include/libgsf-1"]
