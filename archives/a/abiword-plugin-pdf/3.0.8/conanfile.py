#!/usr/bin/env python3
"""Conan recipe — abiword-plugin-pdf 3.0.8

AbiWord PDF export plugin.
Part of the AbiWord 3.0.8 source tree.
"""
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class AbiwordPluginEmlConan(ConanFile):
    name = "abiword-plugin-pdf"
    version = "3.0.8"
    description = "AbiWord PDF export plugin"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/World/AbiWord"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)
        # autoconf-archive/libgcrypt 宏(ax_cxx_compile_stdcxx_11.m4 等)随配方
        # 导出——CI 沙箱(USER=100)看不到 $HOME/.local/share/aclocal 的手工宏,
        # AbiWord configure.ac 的 AX_CXX_COMPILE_STDCXX_11/AM_PATH_LIBGCRYPT
        # 若无宏定义, configure 生成后报 syntax error(CI 实测)。导出后由
        # generate() 注入 ACLOCAL_PATH, aclocal 即可展开这些宏。
        # 用 shutil.copytree 直接复制(conan copy 的 src/dst 路径语义在
        # export_sources 下有坑, CI 实测 es/ 为空)。
        import shutil
        _src_m4 = os.path.join(self.recipe_folder, "m4")
        _dst_m4 = os.path.join(self.export_sources_folder, "m4")
        if os.path.isdir(_src_m4) and not os.path.exists(_dst_m4):
            shutil.copytree(_src_m4, _dst_m4)
            self.output.info(f"  [ok] exported m4 macros to {_dst_m4}")

    def requirements(self):
        # AbiWord 主 configure 强检 libgsf-1 >= 1.14.18(PKG_CHECK_MODULES),
        # PDF 插件亦需 libgsf 处理 MIME/OLE 附件,必须声明依赖
        self.requires("libgsf/1.14.53")
        # AbiWord 主 configure 强依赖 png.h/jpeglib.h + 链接 -ljpeg/-lpng
        # (AC_MSG_ERROR, CI 实测 'png.h not found')——必须显式声明 libpng/libjpeg,
        # 依赖图才有这两个包, generate() 的 glob 才能注入 include/lib 路径。
        # 制品仓已发布 libpng/1.6.58 与 libjpeg/10 (armv8/clang15/OHOS 二进制)。
        self.requires("libpng/1.6.58")
        self.requires("libjpeg/10")
        # libpng/1.6.58 配方 requires zlib/1.3.1.1, 与 libgsf 传递链的 zlib/1.3.1
        # 冲突(CI 实测 "Version conflict between zlib/1.3.1.1 and zlib/1.3.1")。
        # consumer 用 override=True 统一。注意: 必须统一到 **1.3.1.1** 而非
        # 1.3.1——制品仓 libpng/1.6.58 二进制基于 zlib/1.3.1.1 构建, 若 override
        # 到 1.3.1 则 libpng 二进制不匹配 → --build=missing 从源码构建 → libpng
        # 配方无 E114 ac_tmp 修复 → CI 沙箱 configure conftest 失败("C compiler
        # cannot create executables", CI 实测)。统一到 1.3.1.1 后 libpng 直接
        # 用制品仓二进制; libgsf 需从源码构建但其配方含 E114 修复可成功;
        # libxml2 配方 LIBXML2_WITH_ZLIB=OFF 不依赖 zlib 不受影响。
        self.requires("zlib/1.3.1.1", override=True)
        # glib/libxml2 是 libgsf 的传递依赖,但 generate() 中 self.dependencies
        # 对传递依赖的 package_folder 为 None(实测)→ cpp_info 相对路径无法
        # 归一化为绝对路径(DEPS_CFLAGS 出现裸 "-Iinclude"), 且 glib .pc 补写
        # 取不到路径 → configure 报 "No package 'glib-2.0' found"。显式声明为
        # 直接 requires(版本与 libgsf 传递依赖一致,无冲突), package_folder 可用。
        # (同 docbook 51f2d808de 修复, CI 实测 "No package 'fribidi' found")
        self.requires("glib/2.84.0")
        self.requires("libxml2/2.15.3")
        # src/af/util/xp/ut_string.h 强制 #include <fribidi.h>(编译时
        # "fribidi.h not found" CI 实测),必须显式声明 fribidi 直接依赖
        # (制品仓已发布 fribidi/1.0.16, armv8/clang15/OHOS 二进制)。
        self.requires("fribidi/1.0.16")
        # AbiWord 头文件链(pd_Document.h 等)真实使用 boost::shared_ptr 等,
        # 且主 configure 有 AX_BOOST_BASE 硬检查; boost/1.91.0.1.1 已发布到
        # 制品仓,直接声明依赖(旧插件用 stub version.hpp 是 boost 未发布时的
        # 权宜, pdf 插件头文件实际引用 boost 模板必须用真实头)。
        self.requires("boost/1.91.0.1.1")

    def build_requirements(self):
        # AbiWord 的 git archive tarball 不带 configure/aclocal.m4/Makefile.in，
        # build() 必须跑 aclocal/autoconf/autoheader/automake 自举。
        # CI 沙箱(USER=100)对 $HOME/.local 手工安装的 automake 不可见(ENOENT)，
        # /data/service/hnp/bin 只有 autoconf 家族(777)没有 automake/libtool，
        # 故将 automake + libtool 作为 tool_requires 拉入(制品仓已发布 1.18/2.5.4，
        # 同 abiword-plugin-clarisworks / abiword-plugin-epub 先例)。
        # tool_requires 按 *build* profile 解析，conan create 需同时传 -pr:h 与 -pr:b。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps: AbiWord 主 configure 用 PKG_CHECK_MODULES 发现
        # libgsf-1/glib 等依赖,必须生成依赖的 .pc 文件并注入 PKG_CONFIG_PATH
        PkgConfigDeps(self).generate()
        # 注入 ACLOCAL_PATH 指向配方自带 m4 宏(export_sources 导出的
        # autoconf-archive/libgcrypt 宏)——CI 沙箱看不到 $HOME/.local/share/
        # aclocal, 缺 ax_*.m4 则 AX_CXX_COMPILE_STDCXX_11 未定义, configure
        # 生成后 syntax error(CI 实测)。source_folder/m4 由 conan 自动合并。
        # 注意: 必须**先** append buildenv_info **再** VirtualBuildEnv.generate(),
        # 否则环境文件已生成, ACLOCAL_PATH 注入不生效(CI 实测 AX_* 仍未定义)。
        _m4_dir = os.path.join(self.source_folder, "m4")
        if os.path.isdir(_m4_dir):
            self.buildenv_info.append_path("ACLOCAL_PATH", _m4_dir)
        # VirtualBuildEnv: 把 tool_requires(automake/libtool) 的 bin 目录注入
        # conanbuild 环境的 PATH——CI 沙箱(USER=100)看不到 $HOME/.local 的
        # 手工工具, aclocal/automake 只存在于 tool_requires 包内, 不注入 PATH
        # 则 self.run(env="conanbuild") 报 "aclocal: not found"(CI 实测)。
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        # Enable only the pdf plugin, disable all others
        tc.configure_args.append("--enable-plugins=pdf")
        tc.configure_args.append("--disable-default-plugins")
        # Skip gtk checks for plugin-only build
        tc.configure_args.append("--with-gtk2=no")
        # OHOS 不被 config.guess 识别,显式传 --build/--host 跳 config.guess
        tc.configure_args.append("--build=aarch64-linux")
        tc.configure_args.append("--host=aarch64-linux")
        # AbiWord 主 configure 强依赖 png.h/jpeglib.h/boost(AX_BOOST_BASE 硬检查),
        # libpng/libjpeg 未在制品仓发布时 CI 用 --build=missing 从源编译,
        # boost 用 stub version.hpp(PDF 插件本身不 include boost 头)满足检查;
        # 注入 include+lib 路径供 pkg-config/头检查/链接检查
        # 注意: 用 self.dependencies[...].cpp_info 而非 glob 硬编码 conan 缓存
        # 路径(/storage/Users/currentUser/.conan2/p/b/libjp*/p/include)——CI 上
        # 包目录 hash 与本地不同, glob 会漏匹配 → configure 报 "jpeglib.h not
        # found"(docbook CI 实测)。cpp_info 是 conan 标准依赖路径接口, 与
        # 缓存目录名无关(同 docbook/epub 配方修复模式)。
        _cpps = []
        _lds = []
        for _dep_name in ("libpng", "libjpeg"):
            if _dep_name in self.dependencies:
                _dep = self.dependencies[_dep_name]
                _cpps.extend(_dep.cpp_info.includedirs)
                _lds.extend(_dep.cpp_info.libdirs)
        # boost: pdf 插件头文件链(pd_Document.h)真实 include boost/shared_ptr.hpp,
        # 必须注入真实 boost 头(boost/1.91.0.1.1 已发布制品仓)。
        if "boost" in self.dependencies:
            _dep = self.dependencies["boost"]
            _pf = getattr(_dep, "package_folder", None) or ""
            for _g in _dep.cpp_info.includedirs:
                _cpps.append(_g if (os.path.isabs(_g) or not _pf) else os.path.join(_pf, _g))
            for _l in _dep.cpp_info.libdirs:
                _lds.append(_l if (os.path.isabs(_l) or not _pf) else os.path.join(_pf, _l))
        if _cpps:
            tc.configure_args.append("CPPFLAGS={}".format(
                " ".join("-I{}".format(i) for i in _cpps)))
        if _lds:
            tc.configure_args.append("LDFLAGS={}".format(
                " ".join("-L{}".format(i) for i in _lds)))
        # PkgConfigDeps 生成的 .pc 在 generators_folder,但 conanbuild env 未自动
        # 注入 PKG_CONFIG_PATH,configure 的 PKG_CHECK_MODULES 找不到 libgsf-1。
        # 显式注入 PKG_CONFIG_PATH 指向 generators_folder(含 libgsf-1.pc 等)。
        _gens = self.generators_folder
        tc.configure_args.append("PKG_CONFIG_PATH={}".format(_gens))
        # AbiWord 主 configure 用 PKG_CHECK_MODULES 单独检查 glib-2.0/gthread-2.0/
        # gobject-2.0(PkgConfigDeps 因 glib 无 components 且经 libgsf 传递依赖,
        # 未生成 glib-2.0.pc),configure 报 "No package 'glib-2.0' found"
        # (CI 实测)。补写 glib-2.0.pc 本体 + 从它派生 gobject/gthread .pc。
        # 注意: 用 self.dependencies["glib"].package_folder 而非 glob 硬编码
        # ~/.conan2(p/b/glib*)——CI 缓存目录实际是 ~/.cache/conan2, 硬编码 glob
        # 全部 miss → .pc 未补写 → configure 报 "No package 'glib-2.0' found"
        # (CI 实测, 同 docbook 51f2d808de 修复)。
        _glib_root = None
        if "glib" in self.dependencies:
            _glib_root = self.dependencies["glib"].package_folder
        _glib_pc_src = os.path.join(_gens, "glib-2.0.pc")
        _glib_pc_cflags = "-I${includedir} -I${includedir1}"
        if os.path.exists(_glib_pc_src):
            with open(_glib_pc_src, "r", encoding="utf-8", errors="ignore") as _f:
                _glib_pc_text = _f.read()
            _m = re.search(r"^Cflags:\s*(.+)$", _glib_pc_text, re.M)
            if _m:
                _glib_pc_cflags = _m.group(1).strip()
        # glib-2.0.pc 本体(缺失时补写: Requires 链的根,不写则 gthread/gobject
        # 的 Requires: glib-2.0 解析失败 → configure 报 No package 'glib-2.0')
        if not os.path.exists(_glib_pc_src) and _glib_root:
            _pc_text = (
                "prefix={}\n"
                "libdir=${{prefix}}/lib\n"
                "includedir=${{prefix}}/include/glib-2.0\n"
                "includedir1=${{prefix}}/lib/glib-2.0/include\n"
                "\n"
                "Name: glib-2.0\n"
                "Description: Conan package: glib-2.0\n"
                "Version: 2.84.0\n"
                "Libs: -L${{libdir}} -lglib-2.0\n"
                "Cflags: -I${{includedir}} -I${{includedir1}}\n"
            ).format(_glib_root)
            with open(_glib_pc_src, "w", encoding="utf-8") as _f:
                _f.write(_pc_text)
        for _pcname, _libname in (("gobject-2.0.pc", "gobject-2.0"),
                                  ("gthread-2.0.pc", "gthread-2.0")):
            _pf = os.path.join(_gens, _pcname)
            if not os.path.exists(_pf):
                _pc_text = (
                    "prefix=${{pcfiledir}}/../..\n"
                    "libdir=${{prefix}}/lib\n"
                    "includedir=${{prefix}}/include/glib-2.0\n"
                    "includedir1=${{prefix}}/lib/glib-2.0/include\n"
                    "\n"
                    "Name: {}\n"
                    "Description: Conan package: {}\n"
                    "Version: 2.84.0\n"
                    "Libs: -L${{libdir}} -l{}\n"
                    "Cflags: {}\n"
                    "Requires: glib-2.0\n"
                ).format(_pcname.replace(".pc", ""), _pcname.replace(".pc", ""),
                         _libname, _glib_pc_cflags)
                with open(_pf, "w", encoding="utf-8") as _f:
                    _f.write(_pc_text)
        # AbiWord 主 configure 强检全套 GUI 依赖(gtk+-3.0/cairo/pangocairo 等),
        # PDF 插件仅需 libgsf/glib。configure 支持 DEPS_CFLAGS/DEPS_LIBS 预置
        # 绕过 pkg-config 检测,注入指向 libgsf/glib 的 include/lib 路径。
        # 注意: 用 self.dependencies[...].cpp_info 而非 glob 硬编码 conan 缓存
        # 路径(/storage/Users/currentUser/.conan2/p/b/...)——CI 缓存目录实际是
        # ~/.cache/conan2, 硬编码 glob 全部 miss → DEPS_CFLAGS 为空 → configure
        # 报 "No package 'fribidi' found" 等一串 not found(CI 实测)。
        _deps_cflags = []
        _deps_libs = []
        for _dep_name, _deps_lib_flags in (("libgsf", ["-lgsf-1"]),
                                           ("glib", ["-lglib-2.0", "-lgobject-2.0"])):
            if _dep_name in self.dependencies:
                _dep = self.dependencies[_dep_name]
                _pf = getattr(_dep, "package_folder", None) or ""
                for _i in _dep.cpp_info.includedirs:
                    if os.path.isabs(_i) or not _pf:
                        _deps_cflags.append("-I{}".format(_i))
                    else:
                        _deps_cflags.append("-I{}".format(os.path.join(_pf, _i)))
                for _l in _dep.cpp_info.libdirs:
                    if os.path.isabs(_l) or not _pf:
                        _deps_libs.append("-L{}".format(_l))
                    else:
                        _deps_libs.append("-L{}".format(os.path.join(_pf, _l)))
                _deps_libs.extend(_deps_lib_flags)
        if _deps_cflags:
            tc.configure_args.append("DEPS_CFLAGS={}".format(" ".join(_deps_cflags)))
        if _deps_libs:
            tc.configure_args.append("DEPS_LIBS={}".format(" ".join(_deps_libs)))
        # PDF 插件编译需 AbiWord 主程序接口头(ut_string/ut_assert/ie_exp_Text/xap_Module),
        # 且 ie_types.h 需 glib.h,注入源码 include + glib include 目录到 CXXFLAGS
        _src = self.source_folder
        _src_incs = [
            os.path.join(_src, "src", "af", "ev", "xp"),
            os.path.join(_src, "src", "af", "gr", "xp"),
            os.path.join(_src, "src", "af", "tf", "xp"),
            os.path.join(_src, "src", "af", "util", "xp"),
            os.path.join(_src, "src", "af", "xap", "xp"),
            os.path.join(_src, "src", "text", "fmt", "xp"),
            os.path.join(_src, "src", "text", "ptbl", "xp"),
            os.path.join(_src, "src", "wp", "ap", "xp"),
            os.path.join(_src, "src", "wp", "impexp", "xp"),
            os.path.join(_src, "src", "wp", "main", "xp"),
        ]
        _src_incs = [i for i in _src_incs if os.path.isdir(i)]
        # 依赖头目录用 self.dependencies[...].cpp_info.includedirs 获取
        # (不能用 glob 硬编码 ~/.conan2——CI 缓存目录是 ~/.cache/conan2,
        #  硬编码 glob 全部 miss → CXXFLAGS 缺依赖 include, 编译报头缺失)。
        # includedirs 可能是相对路径(如 glib 的 "include"), 需拼 package_folder
        # 归一化为绝对路径(否则 CXXFLAGS 出现 "-Iinclude" 裸相对路径, 实测失效)。
        # package_folder 可能为 None(传递依赖/未构建), 此时保留原值防崩溃。
        for _dep_name in ("libgsf", "glib", "libxml2", "fribidi"):
            if _dep_name in self.dependencies:
                _dep = self.dependencies[_dep_name]
                _pf = getattr(_dep, "package_folder", None) or ""
                for _g in _dep.cpp_info.includedirs:
                    _abs = _g if (os.path.isabs(_g) or not _pf) else os.path.join(_pf, _g)
                    if _abs not in _src_incs:
                        _src_incs.append(_abs)
                # fribidi 包的 cpp_info.includedirs=["include"], 但 ut_string.h
                # 是 `#include <fribidi.h>`(fribidi.h 实际在 include/fribidi/ 下)
                # → 需额外注入 include/fribidi 子目录, 否则编译报 "fribidi.h
                # not found"(docbook 本机验证实测)。
                if _dep_name == "fribidi" and _pf:
                    _fb = os.path.join(_pf, "include", "fribidi")
                    if os.path.isdir(_fb) and _fb not in _src_incs:
                        _src_incs.append(_fb)
        if _src_incs:
            tc.configure_args.append("CXXFLAGS={}".format(
                " ".join("-I{}".format(i) for i in _src_incs)))
        tc.generate()

    def build(self):
        # Generate configure from configure.ac (no pre-generated configure)
        self._run_autogen()

        # Patch config.guess/config.sub for OHOS
        self._patch_config_for_ohos()

        apply_conandata_patches(self)

        if self.settings.os == "OHOS":
            # 记忆坑①/ E114 (同 libgsf 配方): 鸿蒙安全框架拦脚本子进程在新目录
            # 写文件。autoconf 的 config.status 默认用 AS_TMPDIR 在 build 目录建
            # ./confXXXXXX 临时目录,子进程写 subs1.awk 被拦; 且 configure 编译
            # conftest 时 clang 写 TMPDIR 临时文件也被拦(Permission denied)——
            # CI 实测 configure 报 "C compiler cannot create executables"。
            # 修法: 配方(主进程) os.makedirs 预建可写目录, 设置 TMPDIR 指向它,
            # 并把 configure 内嵌 config.status 模板 ac_tmp 改指该目录。
            import tempfile
            fixed_tmp = os.path.join(tempfile.gettempdir(), "pdf-ac-tmp")
            os.makedirs(fixed_tmp, exist_ok=True)
            os.environ["TMPDIR"] = fixed_tmp
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
                # 后续轮次就找不到目录。把 trap 改为只透传退出码,不再删除。
                _old_trap = '{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; } && exit $exit_status'
                _new_trap = 'exit $exit_status'
                if _old_trap in _cfg:
                    _cfg = _cfg.replace(_old_trap, _new_trap)
                with open(_cfg_path, "w", encoding="utf-8") as _f:
                    _f.write(_cfg)
                os.chmod(_cfg_path, 0o755)
                self.output.info("  [ok] Patched configure: ac_tmp -> {} + TMPDIR (HMDFS)".format(fixed_tmp))

        autotools = Autotools(self)
        autotools.configure()
        # TOOLKIT is hardcoded to "gtk" on non-darwin/mingw platforms (incl.
        # OHOS), so config.h defines TOOLKIT_GTK_ALL and ut_misc.h then pulls in
        # <gtk/gtk.h> — but gtk is not published for OHOS.  The pdf plugin does
        # not use any gtk API; undefine the macro so ut_misc.h falls back to
        # `typedef void AbiNativeWidget` (same tradeoff as the other plugins,
        # which only build plugin code, not the GUI).
        import re as _re
        for _cfg_h in (
            os.path.join(self.build_folder, "config.h"),
            os.path.join(self.source_folder, "config.h"),
        ):
            if os.path.exists(_cfg_h):
                _txt = open(_cfg_h, "r", encoding="utf-8", errors="ignore").read()
                _txt = _re.sub(r"^#define TOOLKIT_GTK_ALL[^\n]*\n?", "", _txt, flags=_re.M)
                open(_cfg_h, "w", encoding="utf-8").write(_txt)
                self.output.info("  [ok] removed TOOLKIT_GTK_ALL from {}".format(_cfg_h))
        # Build the plugin subdirectory only
        autotools.make(target="-C plugins/pdf")

    def _run_autogen(self):
        """Run autogen.sh to generate configure and plugin configuration files.

        OHOS HMDFS 环境下 autoreconf 链存在 autoconf.m4f 加载冲突
        (AC_DEFINE/AC_MSG_ERROR 等基础宏报"未定义",实为 warning 被
        当 hard error),改用 autoconf + automake 直跑链绕过。
        """
        import shutil

        # 定位 tool_requires(automake/libtool) 的工具路径。
        # automake/libtool 包的 package_info 用 buildenv_info.define_path 注入
        # $ACLOCAL/$AUTOMAKE/$LIBTOOLIZE 环境变量(conanbuildenv 已 export, 实测
        # conanbuildenv-release-armv8.sh 含 export ACLOCAL=/.../bin/aclocal)。
        # 这些变量只对 conan build 环境生效, 且不注入 PATH——CI 干净 PATH 下裸
        # `aclocal` 找不到(CI 实测 "aclocal: not found")。因此用 $ACLOCAL/$AUTOMAKE
        # 环境变量(在 self.run(env="conanbuild") 子 shell 中展开)而非裸命令。
        # autoconf/autoheader 在 hnp/bin(profile buildenv PATH 已含), 裸调即可。
        self.output.info("Running autogen-common.sh to generate plugin configuration...")
        # 用 self.run(env="conanbuild") 而非裸 subprocess.run: tool_requires
        # 注入的 ACLOCAL/AUTOMAKE/ACLOCAL_PATH/PERL5LIB 只对 conan build 环境生效。
        self.run(
            "bash autogen-common.sh",
            cwd=self.source_folder,
            env="conanbuild",
        )

        # 先跑 aclocal 生成 aclocal.m4(提供 AM_* 宏)
        # 配方自带 m4 宏(ax_*.m4/libgcrypt.m4)已由 export_sources 导出到
        # source_folder/m4。在 aclocal 命令内联注入 ACLOCAL_PATH(CI 实测
        # buildenv_info.append_path 在 VirtualBuildEnv 里不生效, aclocal 找不到
        # AX_CXX_COMPILE_STDCXX_11 → configure 生成后 syntax error)。
        _m4_dir = os.path.join(self.source_folder, "m4")
        self.output.info("Running aclocal to generate aclocal.m4...")
        self.run(
            f'ACLOCAL_PATH="{_m4_dir}:$ACLOCAL_PATH" "${{ACLOCAL:-aclocal}}" --force',
            cwd=self.source_folder,
            env="conanbuild",
            ignore_errors=True,  # aclocal 有 warning 不影响
        )

        # autoconf 直接编译 configure.ac → configure(绕 autoreconf 链冲突)
        self.output.info("Running autoconf to generate configure...")
        self.run(
            'autoconf -o configure configure.ac',
            cwd=self.source_folder,
            env="conanbuild",
            ignore_errors=True,  # AC_DEFINE 等 warning 非硬错,configure 仍生成
        )
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            raise ConanException("autoconf failed to generate configure")

        # autoheader 生成 config.h.in
        self.output.info("Running autoheader to generate config.h.in...")
        self.run(
            'autoheader',
            cwd=self.source_folder,
            env="conanbuild",
            ignore_errors=True,
        )
        _cfg_h_in = os.path.join(self.source_folder, "config.h.in")
        if not os.path.exists(_cfg_h_in):
            # autoheader 靡输出时 touch 兜底
            open(_cfg_h_in, "w").close()

        # automake 补 Makefile.in + install-sh 等(--add-missing)
        # 注意: ltmain.sh 必须先于 automake 补齐,否则 automake 报
        # "required file './ltmain.sh' not found" 而不生成 Makefile.in
        _ltmain = os.path.join(self.source_folder, "ltmain.sh")
        if not os.path.exists(_ltmain):
            # $LIBTOOLIZE 由 libtool 包 buildenv_info.define_path 注入 conanbuild
            # 环境(子 shell 有效), 在 self.run(env="conanbuild") 内用 shell 展开
            # 复制 ltmain.sh——Python 进程 os.environ 取不到该变量(CI 实测
            # ltmain.sh not found)。$LIBTOOLIZE 在 <pkg>/bin/libtoolize,
            # ltmain.sh 在 <pkg>/share/libtool/build-aux/。
            self.run(
                'lt="$LIBTOOLIZE"; '
                'if [ -n "$lt" ] && [ -f "$lt" ]; then '
                '  srcdir="$(cd "$(dirname "$(dirname "$lt")")" && pwd)"; '
                '  src="$srcdir/share/libtool/build-aux/ltmain.sh"; '
                '  [ -f "$src" ] && cp "$src" ltmain.sh && echo "  [ok] Copied ltmain.sh via LIBTOOLIZE env"; '
                'fi',
                cwd=self.source_folder,
                env="conanbuild",
                ignore_errors=True,
            )
            # fallback 1: self.dependencies (tool_requires 的 package_folder)
            if not os.path.exists(_ltmain):
                try:
                    _lt_pkg = self.dependencies["libtool"].package_folder
                    if _lt_pkg:
                        _cand = os.path.join(_lt_pkg, "share", "libtool", "build-aux", "ltmain.sh")
                        if os.path.exists(_cand):
                            shutil.copy(_cand, _ltmain)
                            self.output.info("  [ok] Copied ltmain.sh from tool_requires libtool")
                except Exception:
                    pass
            # fallback 2: shutil.which (本机有手工工具时)
            if not os.path.exists(_ltmain):
                _libtool_aux = os.path.join(
                    os.path.dirname(shutil.which("libtool") or ""),
                    "..", "share", "libtool", "build-aux", "ltmain.sh"
                )
                if os.path.exists(_libtool_aux):
                    shutil.copy(_libtool_aux, _ltmain)
                    self.output.info("  [ok] Copied ltmain.sh from PATH libtool")
            if not os.path.exists(_ltmain):
                self.output.warning("  [warn] ltmain.sh not found, libtool macros may fail")
        self.output.info("Running automake to generate Makefile.in...")
        self.run(
            '"${AUTOMAKE:-automake}" --add-missing --copy --no-force',
            cwd=self.source_folder,
            env="conanbuild",
            ignore_errors=True,  # 部分 Makefile.am 有 GNU make 扩展 warning
        )

    def _patch_config_for_ohos(self):
        """Patch config.guess and config.sub for OHOS (R15)."""
        # Check if the skill's perl script is available
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

    def package(self):
        # Copy the plugin .so to the package folder via glob + copy.
        # 不用 autotools.make(target="... install")：Conan 2.x 的 make() 不追加
        # DESTDIR，配合 configure 阶段 --prefix=/ 会把 .so 装到系统目录(/lib/)
        # 而非 Conan 包目录，在非 root CI worker 上会因无写权限失败。
        # glob + copy 直接从 build_folder/.libs/ 取产物到 package_folder，正确且幂等。
        import glob
        for so in glob.glob(os.path.join(self.build_folder, "plugins", "pdf", ".libs", "*.so*")):
            dst = os.path.join(self.package_folder, "lib", "abiword", "plugins")
            os.makedirs(dst, exist_ok=True)
            copy(self, os.path.basename(so), os.path.dirname(so), dst)

    def package_info(self):
        self.cpp_info.libs = []
        # Set the plugin directory for discovery
        self.runenv_info.define_path("ABIWORD_PLUGINS_DIR",
            os.path.join(self.package_folder, "lib", "abiword", "plugins"))