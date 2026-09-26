#!/usr/bin/env python3
"""Conan recipe — telepathy 0.8.1（≡ 上游 telepathy-glib / Telepathy-GLib 0.8.1，Autotools）。

Telepathy 框架的 GLib 绑定库（libtelepathy-glib）。上游官方发布件
telepathy-glib-0.8.1.tar.gz（freedesktop，2009-10-15）自带预生成 configure，
依赖 glib-2.0/gobject-2.0 >= 2.16、dbus-1 >= 0.95、dbus-glib-1 >= 0.73，
构建期强制 xsltproc（configure.ac:164-167）与 python（代码生成，configure.ac:168）。

OHOS 适配要点（每条都对应一个真实失败与修复，详见 notes.md）：
- config.guess/config.sub 补 HarmonyOS/aarch64 识别（patches/0001、0002）；
- 2009 年的代码生成脚本是 Python 2 产物（print 语句 / xrange / 内建 cmp /
  sets 模块 / codecs.getwriter 包装文本流），而 OHOS 与制品仓均无 python2
  （python/2.7.18 download exit 1）→ patches/0004-0015 做 py2→py3 最小移植；
- dbus 包经 PkgConfigDeps 只生成 dbus.pc（recipe 未声明 pkg_config_name），
  而 configure.ac:151 直接要求 dbus-1 → generate() 生成 dbus-1.pc 别名；
- glib-2.0.pc 声明 Requires: pcre2，但 pcre2 包只提供 libpcre2-8.pc，且包内
  libpcre2-8.la 的 libdir 硬编码为 '//lib' → pcre2.pc 别名 + .a/.la 重定位；
- glib 工具（glib-genmarshal/glib-mkenums）由 configure 经
  `pkg-config --variable=` 查询，conan 生成的 .pc 不含这些自定义变量 →
  make 变量注入；
- configure 的 umask 077 在 HMDFS/SELinux 下创建临时目录不可写（E011）→
  umask 000（patches/0003）；
- make 只构建 telepathy-glib 库子目录（examples/tests/docs 的交叉依赖与
  gtk-doc 与库产物无关）；package() 手动复制库/头/pc。
"""
import os
import re
import shutil
import sys

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class TelepathyConan(ConanFile):
    name = "telepathy"
    version = "0.8.1"
    description = "Telepathy-GLib — Telepathy 框架的 GLib 绑定库（0.8.1 官方发布件）"
    license = "LGPL-2.1-or-later"
    homepage = "https://telepathy.freedesktop.org/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    exports_sources = "patches/*"

    # tests/Makefile.am 的 noinst_PROGRAMS（上游顶层 C 用例，固定 7 个）
    _upstream_c_tests = (
        "test-asv",
        "test-availability-cmp",
        "test-heap",
        "test-internal-debug",
        "test-intset",
        "test-util",
        "test-debug-domain",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # configure.ac:47 PKG_PROG_PKG_CONFIG([0.21])——干净环境需自带 pkg-config
        self.tool_requires("pkgconf/3.0.6")

    def requirements(self):
        # configure.ac:142 PKG_CHECK_MODULES(GLIB, [glib-2.0 >= 2.16, gobject-2.0 >= 2.16])
        # configure.ac:151 PKG_CHECK_MODULES(DBUS, [dbus-1 >= 0.95, dbus-glib-1 >= 0.73])
        # telepathy-glib.pc.in Requires.private: dbus-glib-1, glib-2.0, gobject-2.0
        self.requires("glib/2.88.0", transitive_headers=True, transitive_libs=True)
        self.requires("dbus-glib/0.114", transitive_headers=True, transitive_libs=True)
        # 公开头文件链 proxy.h → dbus-glib.h → dbus/dbus-shared.h 需要 dbus 头，声明为直接依赖
        self.requires("dbus/1.14.10", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ---------------------------------------------------------------- pkg-config 铺垫

    def _pc_dirs(self):
        """PKG_CONFIG_PATH 目录列表：generators（含别名 .pc）+ 依赖包自带 pkgconfig。"""
        dirs = [self.generators_folder]
        for dep in self.dependencies.values():
            try:
                pkg = dep.package_folder
            except Exception:
                continue
            if not pkg:
                continue
            d = os.path.join(pkg, "lib", "pkgconfig")
            if os.path.isdir(d) and d not in dirs:
                dirs.append(d)
        return dirs

    def _dep_libdir(self, name):
        try:
            pkg = self.dependencies[name].package_folder
        except Exception:
            return None
        return os.path.join(pkg, "lib") if pkg else None

    def _alias_dbus1_pc(self):
        """configure.ac:151 要求 dbus-1，dbus 包只产出 dbus.pc → 生成 dbus-1.pc 别名。"""
        src = os.path.join(self.generators_folder, "dbus.pc")
        if not os.path.isfile(src):
            return
        data = open(src, encoding="utf-8", errors="replace").read()
        dst = os.path.join(self.generators_folder, "dbus-1.pc")
        with open(dst, "w", encoding="utf-8") as f:
            f.write(data.replace("Name: dbus\n", "Name: dbus-1\n", 1))
        self.output.info("telepathy-glib: 已生成 dbus-1.pc 别名")

    def _relocate_pcre2(self):
        """pcre2.pc 别名 + libpcre2-8.la 的 libdir 重定位。

        glib-2.0.pc Requires: pcre2（pcre2 包只有 libpcre2-8.pc）；包内
        libpcre2-8.la 的 libdir='//lib'（构建时 prefix=/ 硬编码），libtool 链接
        时以 .la 的 libdir 为准 → 找不到库。把 .a/.la 复制到可写目录并改写 libdir，
        pcre2.pc 的 prefix/libdir 指向该目录。
        """
        try:
            pkg = self.dependencies["pcre2"].package_folder
        except Exception:
            return
        if not pkg:
            return
        src_pc = os.path.join(pkg, "lib", "pkgconfig", "libpcre2-8.pc")
        if not os.path.isfile(src_pc):
            return
        reloc = os.path.join(self.build_folder, "pcre2-reloc-lib")
        os.makedirs(reloc, exist_ok=True)
        for name in os.listdir(os.path.join(pkg, "lib")):
            if name.startswith("libpcre2-8"):
                shutil.copy2(os.path.join(pkg, "lib", name), os.path.join(reloc, name))
        la = os.path.join(reloc, "libpcre2-8.la")
        if os.path.isfile(la):
            data = open(la, encoding="utf-8", errors="replace").read()
            data = re.sub(r"(?m)^libdir='[^']*'", "libdir='%s'" % reloc, data, count=1)
            with open(la, "w", encoding="utf-8") as f:
                f.write(data)
        data = open(src_pc, encoding="utf-8", errors="replace").read()
        data = data.replace("Name: libpcre2-8", "Name: pcre2", 1)
        data = re.sub(r"(?m)^prefix=.*$", "prefix=%s" % reloc, data, count=1)
        data = re.sub(r"(?m)^libdir=.*$", "libdir=%s" % reloc, data, count=1)
        data = re.sub(r"(?m)^includedir=.*$", "includedir=%s/include" % pkg, data, count=1)
        with open(os.path.join(self.generators_folder, "pcre2.pc"), "w", encoding="utf-8") as f:
            f.write(data)
        self.output.info("telepathy-glib: 已生成 pcre2.pc 别名 + .la libdir 重定位")

    def generate(self):
        PkgConfigDeps(self).generate()
        AutotoolsToolchain(self).generate()
        self._alias_dbus1_pc()
        self._relocate_pcre2()

    def _python_exe(self):
        """构建期 python3（逐候选实测可执行性后选用）。

        不能用 sys.executable 或裸 which("python3")：conan 进程 PATH 首位的解释器路径
        在 subprocess（非 conanbuild env）下可能不可执行（实测 exit 127
        "inaccessible or not found"，导致 tests/tools 脚本用例误报失败）。
        """
        import subprocess
        cands = [shutil.which("python3"), shutil.which("python"), sys.executable]
        cands += [os.path.join(d, "python3")
                  for d in os.environ.get("PATH", "").split(os.pathsep) if d]
        seen = set()
        for cand in cands:
            if not cand or cand in seen:
                continue
            seen.add(cand)
            try:
                r = subprocess.run([cand, "-c", "import sys; assert sys.version_info[0] == 3"],
                                   capture_output=True, timeout=30)
            except Exception:
                continue
            if r.returncode == 0:
                return cand
        return sys.executable

    def _glib_tool_vars(self):
        """make 命令行变量：注入 glib 工具绝对路径。

        configure.ac:147 用 `pkg-config --variable=glib_genmarshal glib-2.0` 取工具，
        conan 生成的 glib-2.0.pc 不含这些自定义变量（取到空 → make 报 Error 127）。
        """
        try:
            bin_dir = os.path.join(self.dependencies["glib"].package_folder, "bin")
        except Exception:
            return ""
        pairs = (("GLIB_GENMARSHAL", "glib-genmarshal"), ("GLIB_MKENUMS", "glib-mkenums"))
        return " ".join("%s=%s" % (k, os.path.join(bin_dir, v))
                        for k, v in pairs if os.path.isfile(os.path.join(bin_dir, v)))

    # ---------------------------------------------------------------- build

    def build(self):
        apply_conandata_patches(self)
        pkg_env = os.pathsep.join(self._pc_dirs())
        self.run('cd "%s" && PKG_CONFIG_PATH="%s" PYTHON="%s" ./configure --prefix=/'
                 % (self.source_folder, pkg_env, self._python_exe()), env="conanbuild")
        tool_vars = self._glib_tool_vars()
        # 只构建库子目录：examples 之间有交叉依赖、docs 需 gtk-doc，顶层 make all 必失败
        self.run('cd "%s/telepathy-glib" && make -j1 %s'
                 % (self.source_folder, tool_vars), env="conanbuild")
        self._run_upstream_tests(pkg_env, tool_vars)

    def _static_test_libs(self):
        """上游测试的链接库（静态）：测试与 .so 各内嵌一份静态 glib 时，glib ≥2.80
        的 GType 随机化会让跨副本的 G_TYPE_STRV 比较失效 → 统一静态链接保证单份 glib。"""
        src = self.source_folder
        parts = [os.path.join(src, p) for p in (
            "tests/lib/.libs/libtp-glib-tests.a",
            "telepathy-glib/.libs/libtelepathy-glib.a",
            "telepathy-glib/.libs/libtelepathy-glib-internal.a",
        )]
        g = self._dep_libdir("glib")
        if g:
            parts += ["-L%s" % g, "-lglib-2.0", "-lgobject-2.0", "-lgmodule-2.0",
                      "-lgthread-2.0", "-lgio-2.0", "-lintl", "-lffi"]
        parts += ["-L%s" % os.path.join(self.build_folder, "pcre2-reloc-lib"), "-lpcre2-8"]
        for name, flag in (("dbus", "-ldbus-1"), ("dbus-glib", "-ldbus-glib-1"),
                           ("expat", "-lexpat"), ("zlib", "-lz")):
            d = self._dep_libdir(name)
            if d:
                parts += ["-L%s" % d, flag]
        parts += ["-lm", "-lpthread", "-ldl", "-lrt"]
        return " ".join(parts)

    def _run_upstream_tests(self, pkg_env, tool_vars):
        """实际执行上游测试并逐例记录（容忍失败：统计写构建日志，不阻塞 conan create）。"""
        import subprocess
        src = self.source_folder
        tests_dir = os.path.join(src, "tests")
        if not os.path.isdir(tests_dir):
            self.output.warning("tests/ 不存在，跳过上游测试")
            return
        self.run('cd "%s/tests/lib" && make -j1 %s' % (src, tool_vars),
                 env="conanbuild", ignore_errors=True)
        self.run('cd "%s/tests" && make -j1 all-am LDADD= test_asv_LDADD= '
                 'test_debug_domain_LDADD= test_internal_debug_LDADD= LIBS="%s" %s'
                 % (src, self._static_test_libs(), tool_vars),
                 env="conanbuild", ignore_errors=True)

        ld_paths = [d for d in (self._dep_libdir("glib"), self._dep_libdir("dbus"),
                                self._dep_libdir("dbus-glib"), self._dep_libdir("expat"),
                                self._dep_libdir("zlib")) if d]
        env_prefix = ('LD_LIBRARY_PATH="%s" G_DEBUG=fatal_warnings,fatal_criticals '
                      'PYTHONPATH="%s/tools" abs_top_builddir="%s" abs_top_srcdir="%s" '
                      % (":".join(ld_paths), src, src, src))
        total = passed = 0
        for t in self._upstream_c_tests:
            if not os.path.isfile(os.path.join(tests_dir, t)):
                self.output.info("SKIP %s（未构建）" % t)
                continue
            total += 1
            cmd = 'cd "%s" && %s ./%s' % (tests_dir, env_prefix, t)
            r = subprocess.run(cmd, shell=True, capture_output=True)
            if r.returncode == 0:
                passed += 1
                self.output.info("PASS %s" % t)
            else:
                err = (r.stderr or b"").decode(errors="replace").strip().splitlines()
                self.output.info("FAIL %s (exit %d): %s"
                                 % (t, r.returncode, " | ".join(err[-2:])[-200:]))
        # all-errors-documented.py（py2→py3 移植后）
        script = os.path.join(tests_dir, "all-errors-documented.py")
        if os.path.isfile(script):
            total += 1
            r = subprocess.run('cd "%s" && %s %s "%s"'
                               % (tests_dir, env_prefix, self._python_exe(), script),
                               shell=True, capture_output=True)
            if r.returncode == 0:
                passed += 1
                self.output.info("PASS all-errors-documented.py")
            else:
                err = (r.stderr or b"").decode(errors="replace").strip().splitlines()
                self.output.info("FAIL all-errors-documented.py (exit %d): %s"
                                 % (r.returncode, " | ".join(err[-2:])[-200:]))
        # tests/tools 的脚本用例（校验 py2→py3 移植后的代码生成器输出）
        tools_dir = os.path.join(tests_dir, "tools")
        for sc in ("test-gobject-foo.sh", "test-glib-gtypes-generator.sh"):
            if not os.path.isfile(os.path.join(tools_dir, sc)):
                continue
            total += 1
            r = subprocess.run('cd "%s" && PYTHON="%s" srcdir=. top_srcdir="../.." sh %s'
                               % (tools_dir, self._python_exe(), sc), shell=True, capture_output=True)
            if r.returncode == 0:
                passed += 1
                self.output.info("PASS tests/tools/%s" % sc)
            else:
                self.output.info("FAIL tests/tools/%s (exit %d)" % (sc, r.returncode))
        note = ("（tests/dbus 的 39 个用例需要运行中的 D-Bus 会话总线，本环境无 "
                "dbus-daemon，见 notes.md 平台限制说明）")
        self.output.info("telepathy-glib upstream tests: %d/%d passed %s"
                         % (passed, total, note))

    # ---------------------------------------------------------------- package

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        lib_src = os.path.join(self.source_folder, "telepathy-glib", ".libs")
        lib_dst = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_dst, exist_ok=True)
        for name in sorted(os.listdir(lib_src)):
            if not (name.startswith("libtelepathy-glib.so") or
                    (name.startswith("libtelepathy-glib.a") and "-internal" not in name)):
                continue
            src_p = os.path.join(lib_src, name)
            dst_p = os.path.join(lib_dst, name)
            if os.path.islink(src_p):
                if os.path.lexists(dst_p):
                    os.remove(dst_p)
                os.symlink(os.readlink(src_p), dst_p)
            elif os.path.isfile(src_p):
                shutil.copy2(src_p, dst_p)
        # 头文件：telepathy-1.0/telepathy-glib/*.h + _gen/*.h（enums.h 等生成头）
        hdr_src = os.path.join(self.source_folder, "telepathy-glib")
        hdr_dst = os.path.join(self.package_folder, "include", "telepathy-1.0", "telepathy-glib")
        os.makedirs(hdr_dst, exist_ok=True)
        for name in sorted(os.listdir(hdr_src)):
            if name.endswith(".h"):
                shutil.copy2(os.path.join(hdr_src, name), os.path.join(hdr_dst, name))
        gen_src = os.path.join(hdr_src, "_gen")
        if os.path.isdir(gen_src):
            gen_dst = os.path.join(hdr_dst, "_gen")
            os.makedirs(gen_dst, exist_ok=True)
            for name in sorted(os.listdir(gen_src)):
                if name.endswith(".h"):
                    shutil.copy2(os.path.join(gen_src, name), os.path.join(gen_dst, name))
        pc_src = os.path.join(hdr_src, "telepathy-glib.pc")
        if os.path.isfile(pc_src):
            pc_dst = os.path.join(self.package_folder, "lib", "pkgconfig")
            os.makedirs(pc_dst, exist_ok=True)
            shutil.copy2(pc_src, os.path.join(pc_dst, "telepathy-glib.pc"))

    def package_info(self):
        self.cpp_info.libs = ["telepathy-glib"]
        self.cpp_info.includedirs = ["include/telepathy-1.0"]
        self.cpp_info.set_property("pkg_config_name", "telepathy-glib")
        self.cpp_info.requires = ["glib::glib-2.0", "glib::gobject-2.0",
                                  "dbus-glib::dbus-glib", "dbus::dbus"]
