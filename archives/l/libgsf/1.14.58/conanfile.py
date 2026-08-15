#!/usr/bin/env python3
"""Conan recipe — libgsf 1.14.58

GNOME Structured File Library. Pure C library for reading/writing
structured file formats (OLE2, ZIP, tar, etc.). Used by abiword plugins
(docbook, epub) via libgsf-1.pc pkg-config.
"""
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.env import VirtualRunEnv
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibgsfConan(ConanFile):
    name = "libgsf"
    version = "1.14.58"
    description = "GNOME Structured File Library (OLE2/ZIP/tar)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libgsf"
    url = ""

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {"shared": True, "fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 上游 Gentoo/Debian 声明: glib >=2.36, libxml2 >=2.4.16, zlib
        # R44/真机预检修复: 2.84.0/2.15.3/1.3.1 与 conancenter 同版本冲突——预检
        # remote 顺序 conancenter 在前,依赖解析到 conancenter 上游配方,其依赖树
        # (pcre2/libxml2 等 tool_require cmake/4.4.2)在 OHOS 上无法构建
        # (cmake 配方 build() 按 OS 键取预编译包, OHOS 无键 → KeyError 'OHOS')。
        # 改用 R37 仓库独有版本 (.1, conancenter 无同版本), 自动解析到 ohpcd
        # 本仓适配配方 (meson/autotools, 无 conan cmake tool_require), 与
        # atk/cairo-gobject/chafa/libgda/netcdf 同款做法。
        self.requires("glib/2.84.0.1")
        self.requires("libxml2/2.15.3.1")
        self.requires("zlib/1.3.1.1")
        # R46/R47/R48 真机预检修复: glib 依赖链的 libffi/3.4.4 与 pcre2/10.45 在
        # conancenter 也有同版本,预检 remote 顺序 conancenter 在前 → 解析到
        # conancenter 上游配方,libffi 源码构建在 HMDFS 上 configure 报
        # "working directory cannot be determined"(getcwd 不可达, E011/E129
        # 同款, adms 配方已记录)。pin recipe revision 强制走 ohpcd 本仓适配
        # 配方(已发布二进制,无需源码构建),同 pycairo/graalvm/r-base pin 模式。
        # R48 修正: 本地按仓库 HEAD 复算 RREV 与 ohpcd 实际值不符(配方发布后
        # 被改动, glib/libxml2 亦记录同现象), RREV 以 ohpcd v2 API
        # conans/{n}/{v}/_/_/revisions 实测值为准:
        #   libffi/3.4.4 -> ca8b0eb4102edbca48730e504e3afbdc (2026-07-17T04:29:02Z)
        #   pcre2/10.45  -> 5ecd2f9871deb549e2ae07489f2e40df (2026-07-11T02:18:09Z)
        # 对照: zlib/1.3.1.1 -> 9a23e7d51311d0440b6e4d36cf44e4d9 与本地
        # FileTreeManifest.summary_hash 计算一致, 佐证方法。
        self.requires("libffi/3.4.4#ca8b0eb4102edbca48730e504e3afbdc")
        self.requires("pcre2/10.45#5ecd2f9871deb549e2ae07489f2e40df")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps: autotools 的 configure 用 pkg-config 发现依赖
        # (glib-2.0/gobject-2.0/gio-2.0/libxml-2.0),必须生成依赖的 .pc 文件
        # 并注入 PKG_CONFIG_PATH,否则 configure 报 "No package 'glib-2.0' found"。
        PkgConfigDeps(self).generate()
        # pcre2 配方的 .la 文件 libdir='//lib'(--prefix=/ 产生),libtool 链接
        # libgsf 时解析 pcre2 .la 报 "not a valid libtool archive" → patch
        # pcre2.pc 的 Libs 为 .a 绝对路径,让 libtool 不解析 .la。
        # 注意: 不能硬编码 ~/.conan2/p/b/pcre2*/p 本机路径——CI 干净环境
        # 哈希目录不同会漏匹配,必须从 self.dependencies 拿真实 package_folder。
        import glob as _glob
        _pcre2_lib = ""
        try:
            _pcre2_lib = os.path.join(self.dependencies["pcre2"].package_folder, "lib")
        except Exception:
            pass
        if not _pcre2_lib:
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
        # glib-2.0.pc 的 Libs 带 "-L/lib -l:ld-musl-aarch64.so.1"(glib 配方把
        # musl loader 写入 system_libs),ld.lld 对 "-l:filename" 语法在无
        # 显式搜索路径时找不到 → 改为绝对路径 /lib/ld-musl-aarch64.so.1。
        # 其余 -l{lib} 的处理必须按包内容自适应: 真机 ohpcd 的 glib/2.84.0.1
        # 是 shared 包(仅 .so, 无 .a),R50 实测 "clang: error: no such file or
        # directory: .../libglib-2.0.a" —— 无条件改写为 .a 绝对路径会硬失败。
        # 仅当 .a 实际存在(如本机旧 static 包)才替换为绝对路径强制静态链接,
        # 否则保留 -l{name},由 Libs 行原有的 -L"${libdir}" 解析到共享 .so。
        _glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if os.path.exists(_glib_pc):
            with open(_glib_pc, "r", encoding="utf-8") as _f:
                _pc = _f.read()
            # 同样不能用硬编码 ~/.conan2/p/b/glibfebb*/p 探测——CI 干净环境
            # 哈希目录不同会漏匹配(glib-2.0.pc 的 -l:ld-musl-aarch64.so.1
            # 未替换 → ld.lld unable to find library)。从 dependencies 拿真实路径。
            _glib_cur = ""
            try:
                _glib_cur = os.path.join(self.dependencies["glib"].package_folder, "lib")
            except Exception:
                pass
            if not _glib_cur:
                _fallback = _glob.glob("/storage/Users/currentUser/.conan2/p/b/glibfebb*/p/lib")
                if _fallback:
                    _glib_cur = _fallback[0]
            if _glib_cur and os.path.isdir(_glib_cur):
                _gl = _glib_cur
                _pc = _pc.replace("-l:ld-musl-aarch64.so.1",
                                  "/lib/ld-musl-aarch64.so.1")
                for _libn in ("glib-2.0", "gobject-2.0", "gio-2.0",
                              "gmodule-2.0", "gthread-2.0"):
                    _a_path = os.path.join(_gl, "lib{}.a".format(_libn))
                    _so_path = os.path.join(_gl, "lib{}.so".format(_libn))
                    # R59/CI 修复 (build #25316): 仅当 glib 包为纯静态 (只有 .a
                    # 无 .so) 才替换为 .a 绝对路径强制静态链接。若包同时提供 .so
                    # 仍按 .a 静态链接, libgsf-1.so 会内嵌一份 glib, 而 test_package
                    # 的测试二进制动态链接另一份 → 进程内两套 GObject 类型系统,
                    # test-csv (唯一直接 g_object_new 的测试) 报
                    # "object class '(null)' has no property named 'sink'",
                    # GSF_OUTPUT_CSV_TYPE 类型 ID 在另一副本中无效。
                    if os.path.isfile(_a_path) and not os.path.exists(_so_path):
                        _pc = _pc.replace(
                            "-l{}".format(_libn), _a_path)
                with open(_glib_pc, "w", encoding="utf-8") as _f:
                    _f.write(_pc)
        # libgsf configure.ac 的 libgsf_reqs 单独检查 "gobject-2.0" 和 "gio-2.0"
        # (PKG_CHECK_MODULES 按包名逐个查),而 PkgConfigDeps 只生成聚合的
        # glib-2.0.pc → 显式补写 gobject-2.0.pc / gio-2.0.pc。
        # 注意: 不能依赖探测 ~/.conan2/p/b/glib*/p 包目录——本机源码构建的 glib
        # 是 R26 static 包(仅 .a),但 CI 从 registry 下载的二进制包(tgz 解压)
        # 目录结构不同,libgobject-2.0.a/.so 探测会漏匹配(CI 实测报
        # "No package 'gobject-2.0' found",即使 PKG_CONFIG_PATH 已注入)。
        # 改为从 PkgConfigDeps 生成的 glib-2.0.pc 派生: 复用其 prefix/
        # includedir/Cflags,仅改 Name/Libs(→ -lgobject-2.0 / -lgio-2.0)。
        _glib_pc_src = os.path.join(self.generators_folder, "glib-2.0.pc")
        _glib_pc_cflags = "-I${includedir} -I${includedir1}"
        _glib_pc_prefix = "${pcfiledir}/../.."
        if os.path.exists(_glib_pc_src):
            with open(_glib_pc_src, "r", encoding="utf-8", errors="ignore") as _f:
                _glib_pc_text = _f.read()
            # 提取 Cflags(含 includedir 展开)供派生 .pc 复用
            _m = re.search(r"^Cflags:\s*(.+)$", _glib_pc_text, re.M)
            if _m:
                _glib_pc_cflags = _m.group(1).strip()
        _pc_extra = {
            "gobject-2.0": "gobject-2.0",
            "gio-2.0": "gio-2.0",
        }
        for _name, _libname in _pc_extra.items():
            _pf = os.path.join(self.generators_folder, _name + ".pc")
            if not os.path.exists(_pf):
                _pc_text = (
                    "prefix={}\n"
                    "libdir=${{prefix}}/lib\n"
                    "includedir=${{prefix}}/include/glib-2.0\n"
                    "includedir1=${{prefix}}/lib/glib-2.0/include\n"
                    "\n"
                    "Name: {}\n"
                    "Description: Conan package: {}\n"
                    "Version: 2.84.0.1\n"
                    "Libs: -L${{libdir}} -l{}\n"
                    "Cflags: {}\n"
                    "Requires: glib-2.0\n"
                ).format(_glib_pc_prefix, _name, _name, _libname, _glib_pc_cflags)
                with open(_pf, "w", encoding="utf-8") as _f:
                    _f.write(_pc_text)
        # R60/CI 修复 (build #25316/#25537, test-csv exit=1): 绝对 .so 路径钉死
        # (与 test_package generate() 对称)。CI 进程内存在两份 GObject 类型系统
        # (quark/类型 ID 跨副本失效), 系统 /usr/local/lib 的静态开发库在链接期
        # 可能被解析为第二副本 (已证实 configure 把系统 libintl.a 静态嵌进
        # libgsf-1.so)。对已存在的 glib-2.0.pc / gobject-2.0.pc / gio-2.0.pc,
        # 把 Libs 行的 -lglib-2.0 / -lgobject-2.0 / -lgio-2.0 / -lgmodule-2.0 /
        # -lgthread-2.0 替换为 glib 包 lib 目录下对应库文件的绝对路径: 优先
        # lib<名>.so, 不存在则取第一个 lib<名>.so.* (版本库名), 两者都无才保留
        # -l 形式并 warning。保证 libgsf-1.so 与测试二进制链接同一批物理文件。
        _glib_lib60 = ""
        try:
            _glib_lib60 = os.path.join(self.dependencies["glib"].package_folder, "lib")
        except Exception:
            pass
        if not _glib_lib60:
            _fallback60 = _glob.glob("/storage/Users/currentUser/.conan2/p/b/glib*/p/lib")
            if _fallback60:
                _glib_lib60 = _fallback60[0]
        if _glib_lib60 and os.path.isdir(_glib_lib60):
            for _pcname60 in ("glib-2.0.pc", "gobject-2.0.pc", "gio-2.0.pc"):
                _pf60 = os.path.join(self.generators_folder, _pcname60)
                if not os.path.exists(_pf60):
                    continue
                with open(_pf60, "r", encoding="utf-8") as _f:
                    _pc60 = _f.read()
                _changed60 = False
                for _libn60 in ("glib-2.0", "gobject-2.0", "gio-2.0",
                                "gmodule-2.0", "gthread-2.0"):
                    _flag60 = "-l{}".format(_libn60)
                    if _flag60 not in _pc60:
                        continue
                    _abs60 = ""
                    _so60 = os.path.join(_glib_lib60, "lib{}.so".format(_libn60))
                    if os.path.isfile(_so60):
                        _abs60 = _so60
                    else:
                        _vers60 = sorted(_glob.glob(
                            os.path.join(_glib_lib60, "lib{}.so.*".format(_libn60))))
                        if _vers60:
                            _abs60 = _vers60[0]
                    if _abs60:
                        _pc60 = _pc60.replace(_flag60, _abs60)
                        _changed60 = True
                    else:
                        self.output.warning(
                            "[R60] no lib{}.so* in {}, keeping -l{}".format(
                                _libn60, _glib_lib60, _libn60))
                if _changed60:
                    with open(_pf60, "w", encoding="utf-8") as _f:
                        _f.write(_pc60)
                    self.output.info(
                        "[R60] Pinned {} Libs to absolute .so paths".format(_pcname60))
        tc = AutotoolsToolchain(self)
        # 禁用可选依赖: gdk-pixbuf (图形), introspection (GObject 反射)
        tc.configure_args.append("--disable-gdk-pixbuf")
        tc.configure_args.append("--disable-introspection")
        # 不构建自带的 thumbnailer (图形相关)
        tc.configure_args.append("--disable-thumbnailer")
        # 不构建自带工具 (只输出库)
        tc.configure_args.append("--disable-tools")
        # OHOS 不被 config.guess 识别,且 HMDFS 沙箱拦 config.guess 写 TMPDIR
        # 临时文件(Permission denied: .../tmp/cgEcJAnf/dummy.c)→ 显式传
        # --build/--host 跳过 config.guess(CI Worker 干净环境无本机 hack,
        # 必须写入配方,否则 configure 报 "cannot guess build type")。
        tc.configure_args.append("--build=aarch64-linux")
        tc.configure_args.append("--host=aarch64-linux")
        # PkgConfigDeps 生成的 .pc 在 generators_folder,但 conanbuild env 未自动
        # 注入 PKG_CONFIG_PATH → 显式注入指向 generators_folder(含 libgsf-1.pc/
        # glib-2.0.pc/gobject-2.0.pc/gio-2.0.pc),否则 configure 的
        # PKG_CHECK_MODULES 报 "No package 'gobject-2.0' found"(CI 实测)。
        tc.configure_args.append("PKG_CONFIG_PATH={}".format(self.generators_folder))
        # R56/CI 修复(E106/E004 家族, wolfssl/sipcalc/libyubikey/babeld/abuild
        # 同款先例, 已合入 main): OHOS SDK 的 lld 链接器依赖 libxml2.so.16,
        # CI worker 沙箱的默认库搜索路径找不到它 → configure 的 conftest 链接
        # 失败 "C compiler cannot create executables"(真机 hmbs 环境自带该
        # LD_LIBRARY_PATH 故预检通过, CI worker 未带)。前置 SDK llvm/lib 到
        # LD_LIBRARY_PATH 让 lld 能加载正确的 libxml2。
        # 注意: 不能用 -fuse-ld=GNU ld——GNU ld 产物在 OHOS 沙箱中
        # Permission denied (exit 126) 不可执行(需 ELF 签名), lld 产物可执行。
        env = tc.environment()
        if self.settings.os == "OHOS":
            _llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
            if not os.path.isdir(_llvm_lib):
                _cands = sorted(_glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
                _llvm_lib = _cands[0] if _cands else ""
            if _llvm_lib:
                env.prepend_path("LD_LIBRARY_PATH", _llvm_lib)
        # R60/CI 修复 (build #25316/#25537): configure 的 AM_GNU_GETTEXT 探测会把
        # 系统 /usr/local/lib 的静态 libintl.a 嵌进 libgsf-1.so (已证实: 系统
        # /storage/Users/currentUser/usr/local/lib/libintl.a 被静态链接), 该副本与
        # 测试进程内的共享 glib 构成第二套 GObject 类型系统 (quark/类型 ID 跨副本
        # 失效)。在 configure 探测 gettext 前把 glib 包 lib 目录前置进 LDFLAGS,
        # 让 AM_GNU_GETTEXT 命中包内共享 libintl.so 而非系统静态 libintl.a。
        _glib_libdir60 = ""
        try:
            _glib_libdir60 = os.path.join(self.dependencies["glib"].package_folder, "lib")
        except Exception:
            pass
        if _glib_libdir60 and os.path.isdir(_glib_libdir60):
            env.prepend("LDFLAGS", "-L{}".format(_glib_libdir60))
        tc.generate(env=env)
        # 运行上游 C 测试程序时需要依赖库的运行时路径(glib 为 .a 静态,
        # libxml2/zlib 的动态 .so 由 conanrun 注入 LD_LIBRARY_PATH)。
        VirtualRunEnv(self).generate()

    def build(self):
        # Patch config.guess/config.sub for OHOS (R15)
        self._patch_config_for_ohos()

        apply_conandata_patches(self)

        # HMDFS: conan 建树后父目录对 getcwd() 不可达 (shell_getcwd 平台诊断),
        # configure 内 `pwd` 失败报 "working directory cannot be determined"。
        # 预置 PWD=build_folder 让 shell 的 pwd 内建走逻辑路径, 配合下方
        # configure 的 ac_pwd 回退 $PWD (adms/analog/homebrew 同款, 已合入 main)。
        os.environ["PWD"] = self.build_folder

        # 记忆坑①: 鸿蒙安全框架拦脚本子进程在新目录写文件。autoconf 的
        # config.status 默认用 AS_TMPDIR 在 build 目录建 ./confXXXXXX 临时目录,
        # 子进程写 subs1.awk 被拦 → "could not setup config files machinery"。
        # 修法同 bird/abiword-plugin-epub 配方: 配方(主进程) os.makedirs 预建
        # 可写目录,再把 configure 里嵌入的 config.status 模板 ac_tmp 改指它。
        # ac_tmp=$tmp 同时出现在 configure 与内嵌 config.status 模板,改 configure 即两者都修。
        if self.settings.os == "OHOS":
            import tempfile
            fixed_tmp = os.path.join(tempfile.gettempdir(), "libgsf-ac-tmp")
            os.makedirs(fixed_tmp, exist_ok=True)
            _cfg_path = os.path.join(self.source_folder, "configure")
            if os.path.exists(_cfg_path):
                with open(_cfg_path, "r", encoding="utf-8") as _f:
                    _cfg = _f.read()
                if "ac_tmp=$tmp" not in _cfg:
                    raise ConanException(
                        "E114: ac_tmp=$tmp pattern not found in configure; "
                        "autoconf may have changed the template")
                _cfg = _cfg.replace("ac_tmp=$tmp", "ac_tmp={}".format(fixed_tmp))
                # config.status 的 trap 在退出时 rm -fr "$ac_tmp" 会删掉预建目录,
                # 后续轮次就找不到目录。把 trap 改为只透传退出码,不再删除
                # (目录由配方主进程管理,残留无害)。
                _old_trap = '{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; } && exit $exit_status'
                _new_trap = 'exit $exit_status'
                if _old_trap in _cfg:
                    _cfg = _cfg.replace(_old_trap, _new_trap)
                # HMDFS: conan 建树后父目录对 getcwd() 不可达, configure 内
                # `pwd` 失败报 "working directory cannot be determined"
                # (E011/E129 同款, adms 配方已记录)。pwd 失败时回退 $PWD
                # (build() 已预置 PWD=build_folder)。
                _old_acpwd = 'ac_pwd=`pwd` && test -n "$ac_pwd" &&'
                _new_acpwd = ('ac_pwd=`pwd` 2>/dev/null || ac_pwd=$PWD\n'
                              'test -n "$ac_pwd" &&')
                if _old_acpwd not in _cfg:
                    raise ConanException(
                        "E115: ac_pwd=`pwd` pattern not found in configure; "
                        "autoconf may have changed the template")
                _cfg = _cfg.replace(_old_acpwd, _new_acpwd)
                # config.status 临时目录 umask 077→022 (HMDFS 新目录固定 setgid,
                # umask 077 生成 drwx--S--- 属主不可写, E011/E129 同款)。
                _old_umask = '(umask 077 && mktemp -d "./confXXXXXX")'
                _new_umask = '(umask 022 && mktemp -d "./confXXXXXX")'
                if _old_umask in _cfg:
                    _cfg = _cfg.replace(_old_umask, _new_umask)
                _old_umask2 = '(umask 077 && mkdir "$tmp")'
                _new_umask2 = '(umask 022 && mkdir "$tmp")'
                if _old_umask2 in _cfg:
                    _cfg = _cfg.replace(_old_umask2, _new_umask2)
                with open(_cfg_path, "w", encoding="utf-8") as _f:
                    _f.write(_cfg)
                os.chmod(_cfg_path, 0o755)
                self.output.info("  [ok] Patched configure: ac_tmp -> {} (HMDFS)".format(fixed_tmp))

            # libgsf configure.ac 无 --disable-tools/--disable-thumbnailer/
            # --disable-tests 选项(CI 实测 unrecognized),tools/gsf.c 用 glib
            # 2.84 的 gi18n.h 无条件展开 gettext() → clang -Werror
            # implicit-function-declaration 编译失败。patch 顶层 Makefile.in
            # 的 SUBDIRS,去掉非库必需子目录,只保留 po gsf gsf-win32 doc。
            # tests/ 不纳入主构建: 上游 C 测试程序 (check_PROGRAMS 子集) 的
            # 源码已复制到 test_package/, 由 test_package 编译执行 (R58)。
            _mf_in = os.path.join(self.source_folder, "Makefile.in")
            if os.path.exists(_mf_in):
                with open(_mf_in, "r", encoding="utf-8") as _f:
                    _mf = _f.read()
                _old_subdirs = "SUBDIRS = po gsf gsf-win32 doc tools tests thumbnailer python"
                _new_subdirs = "SUBDIRS = po gsf gsf-win32 doc"
                if _old_subdirs in _mf:
                    _mf = _mf.replace(_old_subdirs, _new_subdirs)
                    with open(_mf_in, "w", encoding="utf-8") as _f:
                        _f.write(_mf)
                    self.output.info("  [ok] Disabled tools/tests/thumbnailer/python in Makefile.in")

        autotools = Autotools(self)
        autotools.configure()
        if self.settings.os == "OHOS":
            # E182/E188: 真机 HMDFS 的 install (toybox/HMBS shim) 带 -m 644
            # (INSTALL_DATA 展开 `${INSTALL} -m 644`) 调 chmod 设权限时返回
            # Error 64 —— 本库 install-libgsf_1_includeHEADERS 实测失败
            # (libfstconst/adms/libxcb 同款先例, 已过门禁)。用 cp/mkdir shim
            # 替换生成的 Makefile 的 INSTALL 变量, make install 全程不碰真机
            # install; libtool 单源安装 (install -c file dest) 不受影响
            # (adms 实测通过)。
            shim = self._write_install_shim()
            self._redirect_install_to_shim(shim)
        autotools.make()
        # R58: 上游 C 测试的构建/执行/标记全部移到 test_package test()——
        # 主配方 RREV 不变时真机 `conan create --build=missing` 命中缓存跳过
        # build(), 原先在本方法输出的 HMBS_UPSTREAM_TEST_RESULT 从未出现
        # (R58 evidence 失败指纹); test_package 每次必跑, 保证标记必然输出。

    def _patch_config_for_ohos(self):
        """Patch config.guess and config.sub for OHOS (R15)."""
        skill_root = os.environ.get("OHC_SKILL_ROOT", "")
        if skill_root:
            script = os.path.join(skill_root, "scripts", "patch-autotools-ohos.pl")
            if os.path.exists(script):
                self.output.info("Patching config.guess/config.sub with skill script")
                for f in ("config.guess", "config.sub"):
                    path = os.path.join(self.source_folder, f)
                    if os.path.exists(path):
                        subprocess.run(["perl", script, path], check=True)
                return
        self.output.info("OHC_SKILL_ROOT not set or script not found, skipping autotools patch")

    def _write_install_shim(self):
        # E182/E188 (libfstconst/adms/libxcb 同款, 已过门禁): 真机 HMDFS 的
        # install (toybox/HMBS shim) 带 `-m 644` (INSTALL_DATA 展开) 调 chmod
        # 设权限时返回 Error 64 (本库 install-libgsf_1_includeHEADERS 实测),
        # 也没有 GNU coreutils install。autotools `make install` 仅需文件复制 +
        # 目录创建 + 可选 chmod → 写一个 install shim 用 cp/mkdir 替代, chmod
        # 容错跳过。返回 shim 绝对路径, 供 sed 改生成的 Makefile 的 INSTALL 变量。
        # HMFS 在创建时按 open mode 给权限, chmod 能力为 0 → 用 os.open 指定
        # 0o755 直接生成可执行 shim (adms 同款, 避免 open()+os.chmod 在真机失效)。
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        script = (
            "#!/bin/sh\n"
            "set -eu\n"
            "mode=\n"
            "while [ $# -gt 0 ]; do\n"
            "  case \"$1\" in\n"
            "    -p|-c) shift ;;\n"
            "    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;\n"
            "    -d) shift; [ $# -gt 0 ] || exit 2; mkdir -p \"$@\"; exit 0 ;;\n"
            "    --) shift; break ;;\n"
            "    -*) shift ;;\n"
            "    *) break ;;\n"
            "  esac\n"
            "done\n"
            "[ $# -ge 2 ] || exit 2\n"
            "dest=\n"
            "for arg in \"$@\"; do dest=$arg; done\n"
            "count=$(($# - 1))\n"
            "mkdir -p \"$(dirname \"$dest\")\"\n"
            "i=1\n"
            "for src in \"$@\"; do\n"
            "  [ $i -gt $count ] && break\n"
            "  cp -f \"$src\" \"$dest\"\n"
            "  # HMDFS 不支持 chmod (E087), 设权限失败不阻断复制。\n"
            "  if [ -n \"$mode\" ]; then\n"
            "    if [ -d \"$dest\" ]; then\n"
            "      chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true\n"
            "    else\n"
            "      chmod \"$mode\" \"$dest\" 2>/dev/null || true\n"
            "    fi\n"
            "  fi\n"
            "  i=$((i + 1))\n"
            "done\n"
        )
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(script)
        except Exception:
            os.close(fd)
            raise
        return install

    def _redirect_install_to_shim(self, shim_install):
        # configure 已把 install 命令路径写死进所有子 Makefile 的 INSTALL 变量,
        # 且 conan build env 的 PATH 前置会被 source conanbuild.sh 覆盖, 靠 PATH
        # 让 configure 探测 shim 无效 → sed 直接改已生成的 Makefile:
        # `INSTALL = <install 命令>` → `INSTALL = <shim>`; INSTALL_DATA/
        # INSTALL_PROGRAM 默认 `${INSTALL} -m 644`/`${INSTALL}` 引用 ${INSTALL}
        # 自动重算, make install 全程走 shim (libfstconst/adms 同款, 已过门禁)。
        bf = self.build_folder
        for root, _, files in os.walk(bf):
            for name in files:
                if name != "Makefile":
                    continue
                mp = os.path.join(root, name)
                with open(mp, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if "INSTALL =" not in content:
                    continue
                lines = []
                changed = False
                for line in content.splitlines(True):
                    stripped = line.lstrip()
                    if stripped.startswith("INSTALL = ") and "/install" in stripped:
                        indent = line[: len(line) - len(stripped)]
                        lines.append("{}{}\n".format(
                            indent, "INSTALL = {}".format(shim_install)))
                        changed = True
                    else:
                        lines.append(line)
                if changed:
                    with open(mp, "w", encoding="utf-8") as f:
                        f.write("".join(lines))

    def package(self):
        autotools = Autotools(self)
        # P3 review: 移除冗余 copy —— autotools.install() 用 DESTDIR 已把
        # libgsf-1.pc 装到 package_folder/lib/pkgconfig（上游 Makefile install 段），
        # 手动 copy 源路径 (build_folder/libgsf) 可疑且重复。
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["gsf-1"]
        # 头文件实际装在 include/libgsf-1/gsf/gsf.h (autotools 标准布局),
        # 必须显式声明 includedirs,否则下游 #include <gsf/gsf.h> 找不到
        self.cpp_info.includedirs = ["include/libgsf-1"]
        # pkg-config name for downstream PKG_CHECK_MODULES
        self.cpp_info.set_property("pkg_config_name", "libgsf-1")
        # Requires for downstream pkg-config chain
        # glib/2.84.0.1 无 components,conan 2 对无组件包用 pkg::pkg 自引用格式
        # (裸包名会被当作本包内部组件报 not defined)
        # R55: conan 要求每个直接依赖都必须被 (cpp_info/components).requires 引用,
        # 否则 package_info() 报 "The direct dependency 'X' is not used by any
        # (cpp_info/components).requires" (libffi 真机实测, 报错逐个列出, pcre2
        # 同为直接依赖一并登记)。libffi/pcre2 是 R46-R48 为强制解析到 ohpcd 适配
        # 配方而 pin 的直接依赖, 引用格式与 glib 配方同款 (libffi::libffi/pcre2::pcre2)。
        self.cpp_info.requires = [
            "glib::glib", "libxml2::libxml2", "zlib::zlib",
            "libffi::libffi", "pcre2::pcre2",
        ]
