#!/usr/bin/env python3
"""Conan recipe — imlib2 1.9.1 (Enlightenment legacy image library).

imlib2 是 Enlightenment 项目的通用图像加载/渲染库，GNU Autotools 构建。
1.9.1 为官方 git tag（legacy-imlib2，git.enlightenment.org 官方源）。

适配要点：
- configure.ac 硬依赖 freetype2（PKG_CHECK_MODULES 无 fallback）；X11 用
  --without-x 禁用（OHOS 无 X）。
- 各图像格式 loader（gif/heif/jpeg/j2k/jxl/png/ps/svg/tiff/webp/bz2/lzma/
  zlib/id3）默认 auto，缺依赖自动禁用；本配方启用 freetype/libpng/zlib
  三组（registry 已发布），其余禁用。
- git 源无预生成 configure：build() 用 aclocal→autoconf→autoheader→
  ltmain.sh→automake 直跑链生成（绕 OHOS HMDFS 下 autoreconf 链
  autoconf.m4f 加载冲突，同 abiword-plugin-eml 先例）。
- configure.ac 将 BUILD_TEST 硬编码 false（上游测试永不构建）；配方以
  -o test=True 打最小补丁启用 --enable-test 并编译运行上游 gtest 套件。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import get, save, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.scm import Git


class Imlib2Conan(ConanFile):
    name = "imlib2"
    version = "1.9.1"
    description = "通用图像加载和渲染库（Enlightenment 项目核心组件）"
    license = "BSD-2-Clause"
    homepage = "https://enlightenment.org"
    url = "https://git.enlightenment.org/old/legacy-imlib2"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "test": [True, False]}
    default_options = {"shared": True, "test": False}

    exports_sources = "patches/*", "upstream-test/*"

    def requirements(self):
        # configure.ac: PKG_CHECK_MODULES(FREETYPE, freetype2) 硬依赖
        self.requires("freetype/2.14.3.1")
        # PNG/ZLIB loader：libpng/1.6.58.2 依赖 zlib/1.3.2
        self.requires("libpng/1.6.58.2")
        # r02：全部可选 loader 依赖已在 registry 发布，逐一启用
        # （test_save/test_load 的 jpeg/tiff/webp/gif/id3/jpg.mp3 入口）
        self.requires("libjpeg/10")
        self.requires("libtiff/4.7.2")
        self.requires("giflib/6.1.3")
        self.requires("libwebp/1.6.0")
        self.requires("libid3tag/0.16.3")
        self.requires("bzip2/1.0.8.2")
        self.requires("liblzma/5.8.1")
        # zlib 版本由 libtiff/4.7.2 链统一为 1.3.1.1（registry 二进制丰富，
        # libtiff 二进制即基于 1.3.1.1 构建，无需重建；libpng/1.6.58.2 为
        # 1.3.2 → 由 --build=missing 从源码构建，同 abiword-plugin-eml 先例）
        self.requires("zlib/1.3.1.1", override=True)
        if self.options.test:
            # 上游测试 test/Makefile.am 链接 -lgtest -lstdc++
            self.requires("gtest/1.17.0.1")

    def build_requirements(self):
        # git 源无 configure，需 autogen；CI 沙箱无 automake/libtool，
        # 以 tool_requires 拉入（同 abiword 先例）
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # r03：官方 sourceforge release 归档（任务头列明的官方 HTTPS URL），
        # SHA-256 见 conandata.yml；git.enlightenment.org 在 CI 侧 clone 失败
        # （curl 18 early EOF），sourceforge 在 CI 可达（libpng 同源成功）。
        # get() 下载并解压到 source_folder（strip_root 剥掉顶层目录），
        # export_sources 已放置的 patches/ 保留不受影响。
        get(self, **self.conan_data["sources"], strip_root=True)
        # 官方 release 归档不含 test/（上游 DIST_SUBDIRS 排除 git-only 测试
        # 套件），配方随 export_sources 携带官方 git tag v1.9.1 同版本
        # 测试源（upstream-test/），此处落地为 test/ 以支持 -o test=True。
        # 注意：测试图片（41 个二进制）以 base64 文本形式随配方携带
        # （upstream-test/images.b64.txt），避免二进制文件进入 PR diff
        # 导致远端 checkout-pr 阶段 patch 应用失败（CI #49401 教训）；
        # source() 阶段解码还原为 test/images/。
        import shutil
        import base64
        _up_test = os.path.join(self.export_sources_folder, "upstream-test")
        _dst_test = os.path.join(self.source_folder, "test")
        if os.path.isdir(_up_test) and not os.path.exists(_dst_test):
            shutil.copytree(_up_test, _dst_test)
            self.output.info("  [ok] carried official upstream-test/ -> test/")
        # 解码 base64 测试图片
        _b64f = os.path.join(_dst_test, "images.b64.txt")
        if os.path.isfile(_b64f):
            _imgdir = os.path.join(_dst_test, "images")
            os.makedirs(_imgdir, exist_ok=True)
            _n = 0
            with open(_b64f, "r", encoding="ascii") as _f:
                for _line in _f:
                    _line = _line.rstrip("\n")
                    if not _line or "\t" not in _line:
                        continue
                    _name, _b64 = _line.split("\t", 1)
                    with open(os.path.join(_imgdir, _name), "wb") as _g:
                        _g.write(base64.b64decode(_b64))
                    _n += 1
            self.output.info("  [ok] decoded {} test images to test/images/".format(_n))

    def generate(self):
        PkgConfigDeps(self).generate()
        # freetype 配方未设 pkg_config_name → PkgConfigDeps 生成 freetype.pc，
        # 而 configure.ac 检查 freetype2.pc（PKG_CHECK_MODULES(FREETYPE,
        # freetype2)）；freetype 包内自带的 freetype2.pc 是 DESTDIR 安装的
        # 原始文件（prefix=/，指向 //include 无效），补写指向包内实际路径的
        # freetype2.pc 桥接（绝对路径，不依赖 pkg-config 相对解析）
        if "freetype" in self.dependencies:
            _ft = self.dependencies["freetype"]
            _pf = getattr(_ft, "package_folder", None) or ""
            if _pf:
                _ft2pc = os.path.join(self.generators_folder, "freetype2.pc")
                save(self, _ft2pc,
                     "prefix={0}\n"
                     "libdir={0}/lib\n"
                     "includedir={0}/include\n"
                     "\n"
                     "Name: freetype2\n"
                     "Description: Conan package: freetype2 (bridge)\n"
                     "Version: 2.14.3\n"
                     "Libs: -L{0}/lib -lfreetype\n"
                     "Cflags: -I{0}/include/freetype2\n".format(_pf))
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            env = tc.environment()
            shell = "/data/service/hnp/bin/bash"
            env.define_path("SHELL", shell)
            env.define_path("CONFIG_SHELL", shell)
            env.define_path("CC", "/data/service/hnp/bin/clang")
            env.define_path("CXX", "/data/service/hnp/bin/clang++")
            env.define_path("LD", "/data/service/hnp/bin/ld.lld")
            env.define_path("AR", "/data/service/hnp/bin/llvm-ar")
            env.define_path("RANLIB", "/data/service/hnp/bin/llvm-ranlib")
            env.define_path("STRIP", "/data/service/hnp/bin/llvm-strip")
            env.define_path("NM", "/data/service/hnp/bin/llvm-nm")
        # OHOS 无 X11；AC_PATH_X 失败且未 --without-x 会 AC_MSG_ERROR
        tc.configure_args.append("--without-x")
        # OHOS 不被 config.guess 识别（uname -s=HarmonyOS 无匹配），显式传
        # --build/--host 跳 config.guess（同 abiword-plugin-eml 先例）
        tc.configure_args.append("--build=aarch64-linux")
        tc.configure_args.append("--host=aarch64-linux")
        # 启用全部可选 loader（r02：依赖均已发布；禁用依赖未发布的
        # heif/j2k/jxl/ps/svg，与上游 #ifdef 守卫一致不进入台账分母）
        tc.configure_args.append("--without-heif")
        tc.configure_args.append("--without-j2k")
        tc.configure_args.append("--without-jxl")
        tc.configure_args.append("--without-ps")
        tc.configure_args.append("--without-svg")
        if self.options.test:
            tc.configure_args.append("--enable-test")
            # gtest 头/库路径（-lgtest 直链，不走 pkg-config）
            _g_incs, _g_libs = [], []
            if "gtest" in self.dependencies:
                _g = self.dependencies["gtest"]
                _pf = getattr(_g, "package_folder", None) or ""
                for _i in _g.cpp_info.includedirs:
                    _g_incs.append("-I" + (_i if os.path.isabs(_i) or not _pf
                                           else os.path.join(_pf, _i)))
                for _l in _g.cpp_info.libdirs:
                    _g_libs.append("-L" + (_l if os.path.isabs(_l) or not _pf
                                           else os.path.join(_pf, _l)))
            if _g_incs:
                tc.configure_args.append("CPPFLAGS=" + " ".join(_g_incs))
            if _g_libs:
                tc.configure_args.append("LDFLAGS=" + " ".join(_g_libs))
        tc.configure_args.append("PKG_CONFIG_PATH={}".format(self.generators_folder))
        # configure.ac 检查 freetype2.pc（PKG_CHECK_MODULES(FREETYPE,
        # freetype2)），但 freetype 配方未设 pkg_config_name → PkgConfigDeps
        # 生成的是 freetype.pc；freetype 包内自带官方 freetype2.pc
        # （lib/pkgconfig/），把依赖包的 pkgconfig 目录也加入查找路径
        if "freetype" in self.dependencies:
            _ft = self.dependencies["freetype"]
            _pf = getattr(_ft, "package_folder", None) or ""
            _ft_pc = os.path.join(_pf, "lib", "pkgconfig")
            if _pf and os.path.isdir(_ft_pc):
                tc.configure_args.append(
                    "PKG_CONFIG_PATH={}:{}".format(
                        self.generators_folder, _ft_pc))
        # GIF loader 用 AC_CHECK_LIB(gif)（非 pkg-config），需显式注入
        # giflib 的 include/lib 路径
        _gif_incs, _gif_libs = [], []
        if "giflib" in self.dependencies:
            _gf = self.dependencies["giflib"]
            _pf = getattr(_gf, "package_folder", None) or ""
            for _i in _gf.cpp_info.includedirs:
                _gif_incs.append("-I" + (_i if os.path.isabs(_i) or not _pf
                                         else os.path.join(_pf, _i)))
            for _l in _gf.cpp_info.libdirs:
                _gif_libs.append("-L" + (_l if os.path.isabs(_l) or not _pf
                                         else os.path.join(_pf, _l)))
        # configure.ac 检查 libwebpdemux / id3tag（PKG_CHECK_MODULES），
        # 依赖配方 pkg_config_name 不匹配时补绝对路径桥接 .pc。
        # libid3tag 为静态库且依赖 zlib（compress2/uncompress），桥接 .pc
        # 的 Libs 需追加 zlib 路径（否则 id3.so dlopen 报 compress2
        # symbol not found）。
        _zlib_libdir = ""
        if "zlib" in self.dependencies:
            _zl = self.dependencies["zlib"]
            _zpf = getattr(_zl, "package_folder", None) or ""
            if _zpf:
                _zlib_libdir = os.path.join(_zpf, "lib")
        for _dep_name, _pcname, _libnames in (
                ("libwebp", "libwebpdemux", ["webpdemux", "webp"]),
                ("libid3tag", "id3tag", ["id3tag"])):
            if _dep_name in self.dependencies:
                _dp = self.dependencies[_dep_name]
                _dpf = getattr(_dp, "package_folder", None) or ""
                if _dpf:
                    _pc = os.path.join(self.generators_folder, _pcname + ".pc")
                    if not os.path.exists(_pc):
                        _extra_libs = ""
                        if _dep_name == "libid3tag" and _zlib_libdir:
                            _extra_libs = "-L{0} -lz".format(_zlib_libdir)
                        save(self, _pc,
                             "prefix={0}\n"
                             "libdir={0}/lib\n"
                             "includedir={0}/include\n"
                             "\n"
                             "Name: {1}\n"
                             "Description: Conan package: {1} (bridge)\n"
                             "Version: 1.0\n"
                             "Libs: -L{0}/lib {2} {3}\n"
                             "Cflags: -I{0}/include\n".format(
                                 _dpf, _pcname,
                                 " ".join("-l{}".format(x)
                                          for x in _libnames),
                                 _extra_libs))
        # giflib 路径注入（AC_CHECK_LIB 不需要 .pc）
        if _gif_incs:
            _prev_cpp = next((a for a in tc.configure_args
                              if a.startswith("CPPFLAGS=")), None)
            _cpp = " ".join(_gif_incs)
            if _prev_cpp:
                tc.configure_args[tc.configure_args.index(_prev_cpp)] = (
                    _prev_cpp + " " + _cpp)
            else:
                tc.configure_args.append("CPPFLAGS=" + _cpp)
        if _gif_libs:
            _prev_ld = next((a for a in tc.configure_args
                             if a.startswith("LDFLAGS=")), None)
            _ld = " ".join(_gif_libs)
            if _prev_ld:
                tc.configure_args[tc.configure_args.index(_prev_ld)] = (
                    _prev_ld + " " + _ld)
            else:
                tc.configure_args.append("LDFLAGS=" + _ld)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._run_autogen()
        # E114 (同 abiword/libgsf): OHOS 安全框架拦 configure 子进程写
        # ./confXXXXXX 临时目录 → 预建可写 TMPDIR 并把 configure 内嵌
        # config.status 的 ac_tmp 指向它
        self._fix_hmdfs_configure_tmpdir()
        autotools = Autotools(self)
        autotools.configure()
        # r02：make 前把生成的 test/Makefile 处理为受控测试模式：
        #  - SRC_DIR 相对化（编译期内嵌；否则 out-of-tree 绝对 srcdir 破坏
        #    test_load incorrect-suffix 的 "../"+SRC_DIR symlink 构造，
        #    err=2 ENOENT；上游 in-tree 构建天然相对）
        #  - all-local: run 禁用（make 期自动跑测试会在 HMDFS cwd 下执行，
        #    chmod 000 无效 → file_can_read 必失败；改为 _run_upstream_tests
        #    在真实权限挂载点受控运行）
        if self.options.test:
            self._patch_test_makefile_for_r02()
        autotools.make(args=["-j1"])
        if self.options.test:
            self._run_upstream_tests()

    def _patch_test_makefile_for_r02(self):
        """make 前处理生成的 test/Makefile（仅改生成 Makefile，不改上游源码）。"""
        import re
        tst_src = os.path.join(self.source_folder, "test")
        mkf = os.path.join(self.build_folder, "test", "Makefile")
        if not os.path.isfile(mkf):
            self.output.warning("  [warn] test/Makefile not found, skip patch")
            return
        with open(mkf, "r", encoding="utf-8", errors="ignore") as _f:
            _mk = _f.read()
        _changed = []
        # 1) SRC_DIR 相对化：-D SRC_DIR='"$(srcdir)"' → 相对 build test 目录
        _old = '-D SRC_DIR=\'"$(srcdir)"\''
        if _old in _mk:
            _rel = os.path.relpath(tst_src, os.path.join(self.build_folder, "test"))
            _new = '-D SRC_DIR=\\"{0}\\"'.format(_rel)
            _mk = _mk.replace(_old, _new)
            _changed.append("SRC_DIR -> '{}'".format(_rel))
            self.output.info("  [ok] test/Makefile SRC_DIR -> '{}'".format(_rel))
        else:
            self.output.info("  [ok] SRC_DIR already relative or handled")
        # 2) all-local: run → all-local:（make 期不自动跑测试）
        if re.search(r'^all-local: run\s*$', _mk, re.M):
            _mk = re.sub(r'^all-local: run\s*$', 'all-local:', _mk, count=1,
                         flags=re.M)
            _changed.append("all-local: run -> all-local:")
            self.output.info("  [ok] test/Makefile all-local run disabled")
        with open(mkf, "w", encoding="utf-8") as _f:
            _f.write(_mk)
        return _changed

    def _run_upstream_tests(self):
        """运行上游 gtest 测试（test/ 目录 9 个非 X11 程序）。

        r02 修复：
        1. test/Makefile 默认 -D SRC_DIR='"$(srcdir)"'（out-of-tree 构建下
           srcdir 为绝对路径），test_load 的 "Load incorrect suffix" 段用
           "../"+SRC_DIR 构造 symlink 目标会断裂（err=2 ENOENT）。把生成的
           test/Makefile 中 SRC_DIR 改为相对源码 test 目录的路径，使
           "../"+相对路径 从 generated/ 能解析回真实图片。
        2. FILE.file_can_read 需 chmod 000 语义（HMDFS 忽略 chmod）：
           在真实权限挂载点（/data/storage/el2/log 等，chmod 生效）创建
           0700 目录并设置 TMPDIR/TMP/TEMP 后运行 test_file，
           并复制 Makefile 满足用例的 "./Makefile" 相对引用。
        """
        import stat as statmod
        src = self.source_folder
        tst_src = os.path.join(src, "test")
        tst_bld = os.path.join(self.build_folder, "test")
        mkf = os.path.join(tst_bld, "Makefile")
        if not os.path.isdir(tst_bld) or not os.path.isfile(mkf):
            self.output.warning("  [warn] test build dir not found, skip test run")
            return
        # 1) SRC_DIR 相对化（仅改生成 Makefile 的宏值，不改上游测试逻辑）
        try:
            with open(mkf, "r", encoding="utf-8", errors="ignore") as _f:
                _mk = _f.read()
            _old = '-D SRC_DIR=\'"$(srcdir)"\''
            if _old in _mk:
                _rel = os.path.relpath(tst_src, tst_bld)
                _mk = _mk.replace(_old, '-D SRC_DIR=\\"{0}\\"'.format(_rel))
                with open(mkf, "w", encoding="utf-8") as _f:
                    _f.write(_mk)
                self.output.info("  [ok] test/Makefile SRC_DIR -> relative '{}'".format(_rel))
        except Exception as _e:
            self.output.warning("  [warn] SRC_DIR relativize failed: {}".format(_e))
        # 2) 生成 conanrun 环境（依赖库路径），确定测试运行 env
        self.run("bash -c 'source conanrun.sh >/dev/null 2>&1; "
                 "env | grep -E \"LD_LIBRARY_PATH|PATH\" | head'",
                 cwd=self.generators_folder, ignore_errors=True)
        # 运行时 loader 与依赖路径（构建产物 + 生成器 .pc 的包路径）
        import subprocess
        _env = dict(os.environ)
        _loaders = os.path.join(self.build_folder, "src", "modules",
                                "loaders", ".libs")
        _libs = os.path.join(self.build_folder, "src", "lib", ".libs")
        _ld = _env.get("LD_LIBRARY_PATH", "")
        _deps = ""
        _gen = self.generators_folder
        for _pc in sorted(os.listdir(_gen)):
            if _pc.endswith(".pc"):
                try:
                    for _line in open(os.path.join(_gen, _pc),
                                      encoding="utf-8", errors="ignore"):
                        if _line.startswith("prefix="):
                            _deps += ":" + os.path.join(
                                _line.strip().split("=", 1)[1], "lib")
                            break
                except Exception:
                    pass
        _env["LD_LIBRARY_PATH"] = "{}{}{}".format(_libs, _deps, _ld)
        _env["IMLIB2_LOADER_PATH"] = _loaders
        # 真实权限挂载点候选（chmod 生效），构造 0700 专用目录
        _rmounts = ["/data/storage/el2/log", "/data/storage/shader_cache/cloud",
                    "/data/storage/el1/base", "/data/storage/el3/base",
                    "/data/storage/el4/base"]
        _rundir = None
        for _m in _rmounts:
            _cand = os.path.join(_m, "imlib2-tests-r02")
            try:
                os.makedirs(_cand, exist_ok=True)
                os.chmod(_cand, 0o700)
                _st = os.stat(_cand)
                if statmod.S_IMODE(_st.st_mode) == 0o700:
                    _p = os.path.join(_cand, "permprobe")
                    with open(_p, "w") as _f:
                        _f.write("x")
                    os.chmod(_p, 0)
                    try:
                        with open(_p, "r"):
                            pass
                        # chmod 000 未生效（HMDFS），淘汰
                    except PermissionError:
                        _rundir = _cand
                        break
                    finally:
                        os.chmod(_p, 0o600)
                        try:
                            os.unlink(_p)
                        except OSError:
                            pass
            except OSError:
                continue
        if not _rundir:
            _rundir = os.path.join(os.environ.get("HOME", "/tmp"),
                                   "imlib2-tests-r02")
            os.makedirs(_rundir, exist_ok=True)
            self.output.warning("  [warn] no real-permission mount found; "
                                "FILE.file_can_read may fail (HMDFS chmod)")
        _env["TMPDIR"] = _rundir
        _env["TMP"] = _rundir
        _env["TEMP"] = _rundir
        _bin = os.path.join(tst_bld)
        _tests = ["test_misc", "test_string", "test_file", "test_context",
                  "test_load", "test_load_2", "test_save", "test_scale",
                  "test_rotate"]
        # file_can_read 需要 ./Makefile 在 cwd（真实权限目录）
        if os.path.isfile(mkf):
            import shutil
            shutil.copy2(mkf, os.path.join(_rundir, "Makefile"))
        _failed = []
        for _t in _tests:
            _exe = os.path.join(_bin, _t)
            if not os.path.isfile(_exe):
                _failed.append((_t, "binary missing"))
                continue
            _cwd = _rundir if _t == "test_file" else _bin
            _rc = subprocess.run([_exe], cwd=_cwd, env=_env)
            if _rc.returncode != 0:
                _failed.append((_t, "exit {}".format(_rc.returncode)))
            self.output.info("  [test] {} rc={} cwd={}".format(
                _t, _rc.returncode, _cwd))
        if _failed:
            raise ConanException(
                "upstream tests failed: {}".format(_failed))

    def _run_autogen(self):
        """Generate configure from configure.ac (direct chain, avoid autoreconf
        autoconf.m4f conflict on OHOS HMDFS — same as abiword-plugin-eml)."""
        src = self.source_folder
        self.output.info("Running aclocal...")
        self.run("${ACLOCAL:-aclocal} --force", cwd=src, env="conanbuild",
                 ignore_errors=True)
        self.output.info("Running autoconf...")
        self.run("autoconf -o configure configure.ac", cwd=src,
                 env="conanbuild", ignore_errors=True)
        if not os.path.exists(os.path.join(src, "configure")):
            raise ConanException("autoconf failed to generate configure")
        self.output.info("Running autoheader...")
        self.run("autoheader", cwd=src, env="conanbuild", ignore_errors=True)
        _cfg_h_in = os.path.join(src, "config.h.in")
        if not os.path.exists(_cfg_h_in):
            open(_cfg_h_in, "w").close()
        # ltmain.sh 必须先于 automake 存在，否则 "required file './ltmain.sh'
        # not found"
        _ltmain = os.path.join(src, "ltmain.sh")
        if not os.path.exists(_ltmain):
            self.run('lt="$LIBTOOLIZE"; '
                     'if [ -n "$lt" ] && [ -f "$lt" ]; then '
                     '  srcdir="$(cd "$(dirname "$(dirname "$lt")")" && pwd)"; '
                     '  src="$srcdir/share/libtool/build-aux/ltmain.sh"; '
                     '  [ -f "$src" ] && cp "$src" ltmain.sh && '
                     '  echo "  [ok] Copied ltmain.sh via LIBTOOLIZE env"; '
                     'fi', cwd=src, env="conanbuild", ignore_errors=True)
            if not os.path.exists(_ltmain):
                try:
                    _lt_pkg = self.dependencies["libtool"].package_folder
                    _cand = os.path.join(_lt_pkg, "share", "libtool",
                                         "build-aux", "ltmain.sh")
                    if _lt_pkg and os.path.exists(_cand):
                        shutil.copy(_cand, _ltmain)
                        self.output.info("  [ok] ltmain.sh from tool_requires")
                except Exception:
                    pass
            if not os.path.exists(_ltmain):
                _libtool_aux = os.path.join(
                    os.path.dirname(shutil.which("libtool") or ""),
                    "..", "share", "libtool", "build-aux", "ltmain.sh")
                if os.path.exists(_libtool_aux):
                    shutil.copy(_libtool_aux, _ltmain)
        self.output.info("Running automake...")
        self.run("${AUTOMAKE:-automake} --add-missing --copy --no-force",
                 cwd=src, env="conanbuild", ignore_errors=True)

    def _fix_hmdfs_configure_tmpdir(self):
        """E114: HMDFS 下 configure 的 config.status 建 ./confXXXXXX 临时目录
        被安全框架拦截，预建可写目录并让 ac_tmp 指向它（abiword 先例）。"""
        import tempfile
        fixed_tmp = os.path.join(tempfile.gettempdir(), "imlib2-ac-tmp")
        os.makedirs(fixed_tmp, exist_ok=True)
        os.environ["TMPDIR"] = fixed_tmp
        _cfg = os.path.join(self.source_folder, "configure")
        if not os.path.exists(_cfg):
            return
        with open(_cfg, "r", encoding="utf-8") as _f:
            _text = _f.read()
        if "ac_tmp=$tmp" in _text:
            _text = _text.replace("ac_tmp=$tmp", "ac_tmp={}".format(fixed_tmp))
            _old_trap = '{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; } && exit $exit_status'
            _new_trap = 'exit $exit_status'
            if _old_trap in _text:
                _text = _text.replace(_old_trap, _new_trap)
            with open(_cfg, "w", encoding="utf-8") as _f:
                _f.write(_text)
            os.chmod(_cfg, 0o755)
            self.output.info("  [ok] Patched configure ac_tmp -> {} (HMDFS)".format(fixed_tmp))
        else:
            self.output.warning("  [warn] ac_tmp=$tmp pattern not found in configure")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["Imlib2"]
        # 无 X 构建（--without-x）下 Imlib2.h 用 #ifndef X_DISPLAY_MISSING
        # 守卫 X11 头；config.h 不会被消费者包含，需显式向消费者注入宏
        if str(self.settings.os) == "OHOS":
            self.cpp_info.cflags = ["-DX_DISPLAY_MISSING"]
        self.cpp_info.set_property("cmake_file_name", "imlib2")
        self.cpp_info.set_property("cmake_target_name", "imlib2::imlib2")
        self.cpp_info.set_property("pkg_config_name", "imlib2")
