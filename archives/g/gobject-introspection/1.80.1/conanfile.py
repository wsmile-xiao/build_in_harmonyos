#!/usr/bin/env python3
"""Conan recipe — gobject-introspection 1.80.1（开启 introspection 的正式变体）。

在 1.78.1.1（开启 introspection，但受限于 1.78 的功能缺陷）之上升级到 1.80.1，
核心差异是**上游 1.80.0 引入的 GIR 注解**：glib:sync-func / async-func / finish-func。
glib 的 girparser 只认这三个显式属性、无按 `_async` 后缀推断的兜底，故 1.78 生成的
GIR 中 Gio 异步方法 is_async 全部退化为 FALSE（上游 callable-info 测试 SIGABRT）。

本版本交付：
- g-ir-scanner / g-ir-compiler / g-ir-generate / g-ir-inspect 工具链
- 14 个 .typelib（含 GIRepository-2.0；GI 运行时基础设施，供 pygobject 的 `import gi` 使用）
- 注：GLib/GObject/Gio/GModule 4 个核心 typelib 自 1.80 起上游移入
  uninstalled_gir_files（不随包安装），改由 glib >= 2.80 提供。

相对 1.78.1.1 的关键适配变化（均为配方内可复现，无 scratch 路径）：
- 删除补丁 0001（shared→static）：1.80 上游 girepository 即 shared_library
- 补丁 0003/0004 改为 build() 内联改写（1.80 目标上下文格式已变）
- 新增 tool_requires flex/bison（1.80 giscanner/meson.build 强制 find_program）
- 签名 glob 改为 '**/*.so*'，覆盖版本化实体库 libgirepository-1.0.so.1.0.0
- 不再跳过 GIRepository-2.0.gir（共享库可被 g-ir-scanner 解析）
"""
import os
import re
import shutil
import subprocess
import glob

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment
from conan.tools.gnu import PkgConfigDeps

HNP_BIN = "/data/service/hnp/bin"


class GobjectIntrospectionConan(ConanFile):
    name = "gobject-introspection"
    version = "1.80.1"
    description = "GObject Introspection (introspection-enabled) — metadata + typelibs for GI runtime"
    license = "LGPL-2.1+"
    homepage = "https://gi.readthedocs.io/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)
        # vendored distutils 兼容层（gi-distutils/）需随配方导出，CI 构建时才能访问
        from conan.tools.files import copy
        _gi_src = os.path.join(self.recipe_folder, "gi-distutils")
        if os.path.isdir(_gi_src):
            copy(self, "*", _gi_src,
                 os.path.join(self.export_sources_folder, "gi-distutils"))

    def requirements(self):
        # 共享 glib：typelib 运行时需 dlopen libglib-2.0.so.0 等
        #
        # 用 2.84.0.2 而非 2.84.0.1（CI #50415 修复）：
        # 本配方 force 了 libffi/3.5.2 + zlib/1.3.1.1.1.1，使 glib 的 package_id
        # 与 ohpcd 上的制品不匹配，故 CI 会**从源码重建 glib**。而 2.84.0.1 的
        # 构建在 CI 环境会失败：
        #   Error relocating .../glib-compile-resources: g_libintl_bindtextdomain:
        #   symbol not found（g_libintl_gettext / g_libintl_bind_textdomain_codeset 同）
        # 根因是 CI 环境 gettext libintl 遮蔽 —— 2.84.0.1 的 libglib-2.0.so
        # 带 `NEEDED libintl.so.8`（readelf 实测 1 处），而构建期该 .so 在 CI
        # 容器内不可解析，运行 glib-compile-resources 即重定位失败。
        # 2.84.0.2 的配方把子项目 proxy-libintl 改为静态链接
        # （subproject_options 的 default_library=static），产物不再 NEEDED libintl
        # （readelf 实测 0 处）—— 这正是为修此 CI 失败而发布的版本。
        # 2.84.0.2 已在本仓 main 且已发布 ohpcd，属既有版本，非新增适配。
        self.requires("glib/2.84.0.2", transitive_headers=True, transitive_libs=True)
        # 合并 libintl（libintl_* + g_libintl_*），g-ir-scanner 进程内共存的关键
        self.requires("libintl/0.26.1")
        # libffi：GI 源码直接 `#include <ffi.h>`（girepository/girepository-private.h:25、
        # girffi.h:25），头文件必须可由 GI 自身解析。glib 虽传递依赖 libffi/3.4.4，但
        # 之前本配方是显式 `force libffi/3.5.2` 才使 libffi 出现在 GI 的直接依赖里，
        # 移除 force 后 generate() 取不到其 package_folder → 编译报
        # `fatal error: 'ffi.h' file not found`（实测）。故此处显式声明。
        # 版本取 3.4.4 与 glib 一致（不引入 force，不改动 glib 的 requirements →
        # glib 的 package_id 仍为已发布的 b55f7a48...）；python 在构建上下文用
        # libffi/3.5.2，两者不同上下文集，无冲突（graph info 实测并存）。
        self.requires("libffi/3.4.4")
        # 注意：此处曾 force zlib/1.3.1.1.1.1 与 libffi/3.5.2，用于迁就 python/3.12.9
        # （它依赖 libffi/3.5.2）。但那会把 glib 的依赖一并改成 3.5.2，使 glib 的
        # package_id 变为 be24c1125ebcc1f92ede14d3fdc3b29a1a594315（ohpcd 未发布）→
        # CI 每次都必须从源码重建 glib，而 glib 自身的 meson 测试在 CI 沙箱下失败
        # （glib:unix SIGABRT、glib:mapping / glib:testing 各 480s 超时），本 PR 的 CI
        # 因此必然红。python 已改到构建上下文（见 build_requirements），宿主图不再需要
        # 统一 libffi，故两项 force 均已移除；glib 维持自带的 libffi/3.4.4 + zlib/1.3.1.1
        # （后者本身即 PIC 变体，满足 _giscanner 的 R_AARCH64 重定位要求），
        # glib 的 package_id 回到已发布的 b55f7a483155972128ae18c9f9e8c67eba35e745（实测）。

    def build_requirements(self):
        # 1.80 新增：giscanner/meson.build **强制** find_program('flex'/'bison')
        # 来生成 scannerparser.c / scannerlexer.c（1.78 无此要求）
        #   flex  = find_program('flex', 'win_flex')
        #   bison = find_program('bison', 'win_bison')
        # 二者均为构建期程序，故用 tool_requires。ohpcd 已有 flex/2.6.4.2、bison/3.8.2。
        self.tool_requires("flex/2.6.4.2")
        self.tool_requires("bison/3.8.2")
        # python：g-ir-scanner / g-ir-compiler 的辅助程序是 Python 脚本，构建期需要解释器
        # （且 GI 会把 giscanner 模块装入该 python 的 lib-dynload，见 E212 鸿蒙 loader
        # 白名单按进程绑定）。置于构建上下文而非宿主 requires，理由同 requirements() 注释：
        # python/3.12.9 依赖 libffi/3.5.2，与 glib 的 libffi/3.4.4 在宿主图内不可共存，
        # 之前靠 force 迁就 python，代价是 glib 被迫源码重建并在 CI 测试阶段失败。
        self.tool_requires("python/3.12.9", run=False)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _find_libdirs(self, prefix):
        """遍历依赖图收集指定前缀（pcre2/zlib/libffi）的 libdir（含 glob 兜底）。"""
        libdirs = []
        for _dep in self.dependencies.values():
            if not _dep.package_folder:
                continue
            if str(_dep.ref).startswith(prefix):
                libdirs.append(os.path.join(_dep.package_folder, "lib"))
        if not libdirs:
            for _pat in ("/storage/Users/currentUser/.conan2/p/%s*/p/lib" % prefix,):
                libdirs += [d for d in glob.glob(_pat) if os.path.isdir(d)]
        return libdirs

    def _conan_python_wrapper(self):
        """返回一个包内 python3 wrapper（自带 conan python 的 libdir）。

        conan python 的 bin/python3 没有 RUNPATH，仅靠 NEEDED
        libpython3.12.so.1.0 定位解释器库；构建环境里该 libdir 已被
        generate() 撤掉（见该处注释：hnp python3 会被同名 libpython 毒化）。
        故生成 wrapper，把库路径**只**作用于 conan python 进程本身。
        生成的 wrapper 落在 build_folder 下，conan 构建目录天然可执行（R49）。
        """
        _py_pkg = self.dependencies.build["python"].package_folder
        _wrap_dir = os.path.join(self.build_folder, "gi-python")
        os.makedirs(_wrap_dir, exist_ok=True)
        _wrap = os.path.join(_wrap_dir, "python3")
        _py_bin = os.path.join(_py_pkg, "bin", "python3")
        _py_lib = os.path.join(_py_pkg, "lib")
        with open(_wrap, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\n")
            f.write('LD_LIBRARY_PATH="%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" '
                    'exec "%s" "$@"\n' % (_py_lib, _py_bin))
        os.chmod(_wrap, 0o755)
        return _wrap

    def _vendored_distutils_dir(self):
        """Return the vendored distutils 兼容层目录（gi-distutils/，随配方提交）。

        Python 3.12 标准库已移除 distutils，conan python 包（python/3.12.9）也
        不带 setuptools；CI worker 上亦无系统 setuptools（此前依赖系统路径的
        方案在 CI 上失败）。因此将 setuptools 的 _distutils 及其 _vendor 依赖
        作为顶层 distutils 包 vendoring 进配方（gi-distutils/），直接放进
        PYTHONPATH 即可让 g-ir-scanner 正常 `import distutils`。
        """
        for _base in (self.source_folder, self.export_sources_folder,
                      self.recipe_folder):
            _d = os.path.join(_base, "gi-distutils")
            if os.path.isdir(os.path.join(_d, "distutils")):
                return _d
        return None

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["build_introspection_data"] = "true"
        tc.project_options["cairo"] = "disabled"
        tc.project_options["doctool"] = "disabled"
        tc.project_options["wrap_mode"] = "nofallback"
        # 共享图内 pcre2/zlib/libffi 的 package_folder 可能为 None → 依赖遍历+glob 兜底
        for _dep in self.dependencies.values():
            if not _dep.package_folder:
                continue
            _ref = str(_dep.ref)
            if _ref.startswith("pcre2/"):
                tc.c_link_args.append("-L" + os.path.join(_dep.package_folder, "lib"))
                tc.c_link_args.append("-lpcre2-8")
            elif _ref.startswith("zlib/"):
                tc.c_link_args.append("-L" + os.path.join(_dep.package_folder, "lib"))
                tc.c_link_args.append("-lz")
            elif _ref.startswith("libffi/"):
                _inc = os.path.join(_dep.package_folder, "include")
                if os.path.isdir(_inc):
                    tc.c_args.append("-I" + _inc)
        # glib 静态引用 gettext 符号（bindtextdomain 等），musl loader 提供
        tc.c_link_args.append("-L/lib")
        tc.c_link_args.append("-l:ld-musl-aarch64.so.1")
        tc.generate()

        env = Environment()
        env.define("AR", HNP_BIN + "/llvm-ar")
        env.define("CC", HNP_BIN + "/clang")
        # 共享 glib libdir 进 LIBRARY_PATH（临时 introspection 二进制 -l 无 -L）
        _glib_lib = os.path.join(self.dependencies["glib"].package_folder, "lib")
        env.prepend_path("LIBRARY_PATH", _glib_lib)
        for _p in ("pcre2", "zlib", "libffi"):
            for _ld in self._find_libdirs(_p):
                env.prepend_path("LIBRARY_PATH", _ld)
        # LD_LIBRARY_PATH：合并 libintl 首位（后 prepend 在最前），再 glib libdir
        env.prepend_path("LD_LIBRARY_PATH", _glib_lib)
        _intl_lib = os.path.join(self.dependencies["libintl"].package_folder, "lib")
        if os.path.isdir(_intl_lib):
            env.prepend_path("LD_LIBRARY_PATH", _intl_lib)
        # NOTE: 不要在此全局设置 PYTHONHOME/LD_LIBRARY_PATH 指向 conan python——
        # 会破坏 meson.configure() 使用的系统 python3（CI #37749：
        # /data/service/hnp/bin/python3 加载 conan libpython → Py_BytesMain
        # symbol not found）。PYTHONHOME/python-lib 只注入 g-ir-scanner 子进程
        # 环境（g_ir_scanner_env，见 build()），与 python/3.12.9 test_package
        # 的做法一致（LD_LIBRARY_PATH=package/lib, PYTHONHOME=package_folder）。
        #
        # 但仅"不主动注入"不够：python 进入构建上下文后，conan 自身会把它注入
        # 构建环境——virtualbuildenv.py 对 build requires 的 runenv_info 是
        # **无条件** compose（`if require.run or not required_conan_version_policy(...)`），
        # 故 `run=False` 不生效（实测：探针配方 tool_requires(python, run=False)
        # 后 conanbuildenv-*.sh 仍出现 <pkg>/lib）。而 LD_LIBRARY_PATH 优先于
        # RUNPATH，CI 上 meson 的解释器（/data/service/hnp/bin/python3）因此加载
        # 到 conan 的 libpython3.12.so.1.0 → Py_BytesMain: symbol not found →
        # meson setup 以 exit 127 失败（CI #10682 实测）。修法：在 generate()
        # 里撤掉该依赖注入的 LD_LIBRARY_PATH（实测 BEFORE=<pkg>/lib、
        # AFTER 为空，profile 的 llvm/lib 保留）。pyproject 的 `required_conan_version`
        # 声明无法规避——该判据是"范围不含 2.27.9 才豁免"，语义不符故不用。
        _dep_py = self.dependencies.build.get("python")
        if _dep_py is not None:
            _dep_py.runenv_info.unset("LD_LIBRARY_PATH")
            self.output.info(
                "gobject-introspection: dropped conan python libdir from build "
                "LD_LIBRARY_PATH (CI #10682 Py_BytesMain)")
        env.prepend_path("PATH", HNP_BIN)
        # 配方内生成 ldd shim（g-ir-scanner 调 ldd 解析 DT_NEEDED）
        shim_dir = os.path.join(self.build_folder, "gi-shims")
        os.makedirs(shim_dir, exist_ok=True)
        ldd_shim = os.path.join(shim_dir, "ldd")
        with open(ldd_shim, "w") as f:
            f.write("#!/bin/sh\n")
            f.write("for f in \"$@\"; do\n")
            f.write("  %s/llvm-readelf -d \"$f\" 2>/dev/null | grep -E 'Shared library' | sed -E 's/.*\\[(.*)\\]/\\t\\1 => \\1/' \n" % HNP_BIN)
            f.write("done\n")
        os.chmod(ldd_shim, 0o755)
        env.prepend_path("PATH", shim_dir)
        # Python 3.12 removed distutils from stdlib; the conan python package
        # (python/3.12.9) does not ship setuptools either, and CI worker has no
        # system setuptools. g-ir-scanner imports distutils at startup
        # (giscanner/utils.py:385 'import distutils.cygwinccompiler'; ccompiler.py
        # handled by 0002 patch). Provide a vendored top-level `distutils` package
        # (gi-distutils/, committed with the recipe) via PYTHONPATH.
        _gi_dist = self._vendored_distutils_dir()
        if _gi_dist:
            env.prepend_path("PYTHONPATH", _gi_dist)
            self.output.info("gobject-introspection: vendored distutils via %s" % _gi_dist)
        else:
            self.output.warning("gobject-introspection: vendored gi-distutils not found")
        envvars = env.vars(self)
        envvars.save_script("conan_buildenv")

        # glib-2.0.pc：includedir 指向标准布局（GI 的 gir/meson.build 会再拼 glib-2.0）
        _glib_root = self.dependencies["glib"].package_folder
        with open(os.path.join(self.generators_folder, "glib-2.0.pc"), "w") as f:
            f.write(f"prefix={_glib_root}\n")
            f.write(f"libdir=${{prefix}}/lib\n")
            f.write(f"includedir=${{prefix}}/include\n\n")
            f.write("Name: GLib\n")
            f.write("Description: GLib (wrapper, standard include layout)\n")
            f.write("Version: 2.84.0.2\n")
            f.write("Requires: libffi\n")
            f.write(f"Libs: -L${{libdir}} -lglib-2.0\n")
            f.write(f"Cflags: -I${{includedir}}/glib-2.0 -I${{libdir}}/glib-2.0/include\n")

        # 其他组件 wrapper .pc（glib package_info 只声明 glib-2.0）
        for pc_name, desc in [
            ("gobject-2.0", "GObject"),
            ("gio-2.0", "GIO"),
            ("gmodule-2.0", "GModule"),
            ("gio-unix-2.0", "GIO Unix"),
            ("libffi", "libffi"),
        ]:
            pc_path = os.path.join(self.generators_folder, f"{pc_name}.pc")
            if not os.path.exists(pc_path):
                with open(pc_path, "w") as f:
                    f.write(f"prefix={_glib_root}\n")
                    f.write(f"libdir=${{prefix}}/lib\n")
                    f.write(f"includedir=${{prefix}}/include\n\n")
                    f.write(f"Name: {desc}\n")
                    f.write(f"Description: {desc} (wrapper for glib)\n")
                    f.write("Version: 2.84.0.2\n")
                    if pc_name == "libffi":
                        f.write(f"Libs: -L${{libdir}} -lffi\n")
                        f.write(f"Cflags: -I${{includedir}} -DFFI_STATIC_BUILD\n")
                    elif pc_name == "gio-unix-2.0":
                        f.write("Requires: glib-2.0 gobject-2.0 gmodule-2.0\n")
                        f.write(f"Libs: -L${{libdir}} -lgio-2.0\n")
                        f.write(f"Cflags: -I${{includedir}} -DG_INTL_STATIC_COMPILATION\n")
                    else:
                        f.write("Requires: glib-2.0\n")
                        f.write(f"Libs: -L${{libdir}} -l{pc_name}\n")
                        f.write(f"Cflags: -I${{includedir}}\n")

    def build(self):
        apply_conandata_patches(self)
        # 跳过 subdir('tests')（tests 在静态链接下缺 gobject/gio 依赖符号，非目标）
        _mb = os.path.join(self.source_folder, "meson.build")
        if os.path.isfile(_mb):
            _txt = open(_mb, encoding="utf-8").read()
            # 跳过 subdir('tests')。1.80 的闸已简化为仅判 cross build（见下），
            # 而本包 cross/host 同为 ohos-aarch64，is_cross_build() 为假 → 会真的去
            # 构建上游测试（需静态链接 gobject/gio 符号，非本包目标）。
            # 1.78.1.1 的锚点（含 and get_option('build_introspection_data')）在 1.80
            # 已不存在，故此处按 1.80 的真实文本替换，否则测试会被构建。
            _old = "if not meson.is_cross_build()\n  subdir('tests')\nendif"
            _new = "if false and not meson.is_cross_build()\n  subdir('tests')\nendif"
            if _old in _txt:
                _txt = _txt.replace(_old, _new, 1)
                self.output.info("gobject-introspection: tests gate disabled for 1.80 layout")
            # 1.80 新增硬检查：Python >= 3.12 时必须能 import setuptools
            #   if python_version.version_compare('>=3.12')
            #     pymod.find_installation(get_option('python'), modules: ['setuptools'])
            #   endif
            # 会直接 ERROR: ... is missing modules: setuptools。而 conan python 包不带
            # setuptools，本配方改用 vendored distutils（gi-distutils/）满足 giscanner 的
            # distutils 需求，故该检查对本环境无意义 → 注释掉（保留原意于注释）。
            _so = ("if python_version.version_compare('>=3.12')\n"
                   "  pymod.find_installation(get_option('python'), modules: ['setuptools'])\n"
                   "endif")
            _sn = ("# OHOS: setuptools check disabled — conan python ships none; the\n"
                   "# recipe provides a vendored distutils (gi-distutils/) instead.\n"
                   "# if python_version.version_compare('>=3.12')\n"
                   "#   pymod.find_installation(get_option('python'), modules: ['setuptools'])\n"
                   "# endif")
            if _so in _txt:
                _txt = _txt.replace(_so, _sn, 1)
                self.output.info("gobject-introspection: setuptools hard-check disabled (vendored distutils used)")
            # meson_options.txt 的 python 选项默认值是裸名 'python3'，
            # meson 会按 PATH 解析为系统 /usr/local/bin/python3。但 python 已进入
            # 构建上下文后，conan 会把 conan python 的 lib 目录注入构建环境
            # LD_LIBRARY_PATH（实测即使 run=False 也注入），系统 python3 因此动态
            # 加载到 conan 的 libpython3.12.so，而该 libpython 的 sysconfig 名为
            # _sysconfigdata__linux_aarch64-linux-ohos（系统安装树内不存在）→
            # sysconfig 崩溃 → meson 报
            # "ERROR: <PythonExternalProgram 'python3'> is not a valid python or it
            #  is missing distutils"（meson.build:20），configure 直接失败。
            # 修法：把 python 选项默认值改为 conan python 的绝对路径，让 meson 直接
            # 用 conan python（实测其 python_info.py 自检 rc=0）。这也是语义正确的
            # 选择——g_ir_scanner_env 与 giscanner 安装目标本就用 conan python。
            _mo = os.path.join(self.source_folder, "meson_options.txt")
            if os.path.isfile(_mo):
                # 注意：这里**不能**直接用 conan python 的 bin/python3。generate() 已把
                # conan python 的 libdir 从构建环境 LD_LIBRARY_PATH 撤掉（否则 CI 上
                # meson 的解释器 /data/service/hnp/bin/python3 会加载到 conan 的
                # libpython3.12.so.1.0 → Py_BytesMain: symbol not found，CI #10682）。
                # 但 conan python 自身**没有 RUNPATH**（实测 `llvm-readelf -d bin/python3`
                # 无 RUNPATH，仅 NEEDED libpython3.12.so.1.0），撤掉后它自己反而起不来
                # （实测直调报同样的 symbol not found）。两个解释器的 libpython SONAME
                # 相同，全局 LD_LIBRARY_PATH 无法同时满足，故用 wrapper 把库路径**只**
                # 作用于 conan python 进程。实测 wrapper 跑 meson 的
                # python_info.py 自检返回合法 JSON（rc=0）。
                _py_bin = self._conan_python_wrapper()
                _mt = open(_mo, encoding="utf-8").read()
                _mo_old = "option('python', type: 'string', value: 'python3',"
                _mo_new = "option('python', type: 'string', value: '%s'," % _py_bin
                if _mo_old in _mt:
                    open(_mo, "w", encoding="utf-8").write(
                        _mt.replace(_mo_old, _mo_new, 1))
                    self.output.info(
                        "gobject-introspection: meson python option -> %s" % _py_bin)
            # 1.78.1.1 补丁 0004 的 hunk 1（harmonyos 归入 linux 分支）：改为内联改写。
            # 否则 host_system == 'harmonyos' 时 libffi>=3.4 却仍定义 LEGACY_GIRFFI_FREE=1，
            # 使 GIR 走 legacy girffi 语义（与上游 linux 行为不一致）。
            _lf_old = ("if not (host_system == 'darwin' and host_arch == 'aarch64' or\n"
                       "        host_system == 'linux' and libffi_dep.version().version_compare('>= 3.4'))")
            _lf_new = ("if not (host_system == 'darwin' and host_arch == 'aarch64' or\n"
                       "        (host_system == 'linux' or host_system == 'harmonyos') and "
                       "libffi_dep.version().version_compare('>= 3.4'))")
            if _lf_old in _txt:
                _txt = _txt.replace(_lf_old, _lf_new, 1)
                self.output.info("gobject-introspection: harmonyos added to libffi platform check")
            # FIX: g-ir-scanner 子进程 env——g_ir_scanner_env 在 dep_type 非 internal 时为空，
            # 补 PKG_CONFIG_PATH（generators，含 glib-2.0.pc 等）+ LIBRARY_PATH/LD_LIBRARY_PATH
            # （glib+libintl libdir），否则 gir 生成报 can't resolve libraries to shared libraries。
            _gen = self.generators_folder
            _glib_lib = ""
            _intl_lib = ""
            for _dep in self.dependencies.values():
                if _dep.package_folder and str(_dep.ref).startswith("glib/"):
                    _glib_lib = os.path.join(_dep.package_folder, "lib")
                elif _dep.package_folder and str(_dep.ref).startswith("libintl/"):
                    _intl_lib = os.path.join(_dep.package_folder, "lib")
            _old_env = "g_ir_scanner_env = environment()"
            _shim = os.path.join(self.build_folder, "gi-shims")
            # PYTHONPATH: vendored distutils 兼容层（gi-distutils/，配方内自带，
            # Python 3.12 distutils 兼容），与 generate() 注入保持一致。
            _gi_dist = self._vendored_distutils_dir()
            # E212：conan python 二进制需 PYTHONHOME + python lib 的 LD_LIBRARY_PATH，
            # 否则无法 dlopen 自身 C 扩展（CI #37244 连 _random.so 都失败）。
            # g-ir-scanner 加载 giscanner 时从 python lib-dynload（白名单内）导入
            # （见 _install_giscanner_to_package）。
            _py_pkg = self.dependencies.build["python"].package_folder
            _py_bin = os.path.join(_py_pkg, "bin")
            _py_lib = os.path.join(_py_pkg, "lib")
            _py_ld = os.path.join(_py_pkg, "lib", "python3.12", "lib-dynload")
            _py_parts = [p for p in (_py_ld, _gi_dist) if p]
            _py_path = ":".join(_py_parts) if _py_parts else _shim
            # PATH 前置 conan python bin：g-ir-scanner shebang 为 /usr/bin/env
            # python3，必须用 conan python（能 dlopen 自身 lib-dynload 扩展），
            # 而不是系统 /data/service/hnp/bin/python3（CI #37749 中它加载
            # conan libpython 后 Py_BytesMain 崩溃）。
            _new_env = ("g_ir_scanner_env = environment()\n"
                        "g_ir_scanner_env.append('PKG_CONFIG_PATH', '%s')\n"
                        "g_ir_scanner_env.append('LIBRARY_PATH', '%s')\n"
                        "g_ir_scanner_env.append('LD_LIBRARY_PATH', '%s:%s:%s')\n"
                        "g_ir_scanner_env.set('PYTHONHOME', '%s')\n"
                        "g_ir_scanner_env.prepend('PATH', '%s:%s:%s')\n"
                        "g_ir_scanner_env.append('PYTHONPATH', '%s')\n"
                        % (_gen, _glib_lib, _py_lib, _intl_lib, _glib_lib, _py_pkg,
                           _py_bin, _shim, HNP_BIN, _py_path))
            if _old_env in _txt:
                _txt = _txt.replace(_old_env, _new_env, 1)
                self.output.info("gobject-introspection: injected gir env (PKG_CONFIG_PATH/LIBRARY_PATH/LD_LIBRARY_PATH/PYTHONHOME/PYTHONPATH)")
            open(_mb, "w", encoding="utf-8").write(_txt)
        # E004：_giscanner 显式链接 libpython（仅该扩展，避免污染全局探针）
        _gm = os.path.join(self.source_folder, "giscanner", "meson.build")
        if os.path.isfile(_gm):
            _t = open(_gm, encoding="utf-8").read()
            _old = "  install: true,\n  install_dir: giscannerdir,\n)"
            # E004：_giscanner 链 libpython 用 conan python 包 libdir（CI 图内必含
            # libpython3.12.so.1.0），不用硬编码系统路径（.cache 干净 CI 上
            # /data/service/hnp/python.org 不可靠 → unable to find library）。
            # python 已在构建上下文（见 build_requirements）：须从 dependencies.build 取，
            # 否则宿主图内查不到 python 包 → _py_lib 为空 → 链接行变成
            # `-L -l:libpython3.12.so.1.0`，_giscanner 报 unable to find library。
            _py_lib = os.path.join(self.dependencies.build["python"].package_folder, "lib")
            _new = "  install: true,\n  install_dir: giscannerdir,\n  link_args: ['-L%s', '-l:libpython3.12.so.1.0'],\n)" % _py_lib
            if _old in _t:
                open(_gm, "w", encoding="utf-8").write(_t.replace(_old, _new, 1))
        # gir 命令：glib 库集补全（临时二进制完整链接）+ 跳过 GIRepository-2.0.gir
        _gir = os.path.join(self.source_folder, "gir", "meson.build")
        if os.path.isfile(_gir):
            _t2 = open(_gir, encoding="utf-8").read()
            _glibset = ("  '--library=glib-2.0',\n"
                        "  '--library=gobject-2.0',\n"
                        "  '--library=gio-2.0',\n"
                        "  '--library=gmodule-2.0',\n"
                        "  '--library=gthread-2.0',\n")
            _old2 = "  '--library=glib-2.0',\n  '--library=gobject-2.0',\n]"
            if _old2 in _t2:
                _t2 = _t2.replace(_old2,
                                  "  '--library=glib-2.0',\n  '--library=gobject-2.0',\n" + _glibset + "]", 1)
            for _lib in ("gobject-2.0", "gmodule-2.0", "gio-2.0"):
                _old_l = "  '--library=%s',\n]" % _lib
                if _old_l in _t2:
                    _t2 = _t2.replace(_old_l, "  '--library=%s',\n" % _lib + _glibset + "]", 1)
            _old_gi = "  '--library=girepository-1.0',\n  '--pkg-export=gobject-introspection-1.0',"
            if _old_gi in _t2:
                _t2 = _t2.replace(_old_gi,
                                  "  '--library=girepository-1.0',\n" + _glibset + "  '--pkg-export=gobject-introspection-1.0',", 1)
            # 注：1.78.1.1 在此处跳过 GIRepository-2.0.gir（当时 girepository 是静态库，
            # g-ir-scanner 无法把 -lgirepository-1.0 解析成共享库）。1.80 上游已改用
            # shared_library('girepository-1.0', ...)，该限制消失，故**不再跳过**，
            # 让 GIRepository-2.0.typelib 正常生成并安装。
            open(_gir, "w", encoding="utf-8").write(_t2)
        meson = Meson(self)
        meson.configure()
        try:
            meson.build()
        except Exception:
            # E212：鸿蒙 loader 只允许从 p/(package 安装路径) dlopen 共享库，
            # b/(build 路径) 不可加载——即使签名，g-ir-scanner 也无法 dlopen
            # build 目录下的 _giscanner.so（Permission denied）。
            # 修复：将 giscanner 模块（含 _giscanner.so）复制到 package_folder
            # （p/ 路径，loader 白名单内）并签名，重跑 ninja 完成 gir 生成
            # （PYTHONPATH 已优先指向 package_folder/lib，见 g_ir_scanner_env）。
            self._install_giscanner_to_package()
            meson.build()
        else:
            # 1.80：girepository 改为共享库后，gir 生成在首次 meson.build() 即可完成，
            # 不再走上面的 E212 兜底分支。但该分支顺带完成的「把 giscanner 复制进
            # conan python 的 lib-dynload 并签名」是上游 tests/scanner 能 import
            # giscanner 的前提（_run_upstream_scanner_tests 的 PYTHONPATH 指向
            # lib-dynload）。故此处仍需显式调用，否则测试报
            # ModuleNotFoundError: No module named 'giscanner'（实测 1/9）。
            self._install_giscanner_to_package()
        # rule4 整改：实测上游 tests/scanner 纯 Python unittest 子集并如实
        # 填报运行数与通过率（附日志）。giscanner 已由 g_ir_scanner_env /
        # _install_giscanner_to_package 就绪（python lib-dynload，签名）。
        self._run_upstream_scanner_tests()
        # 同为「被 subdir('tests') 闸门连坐」的 warn 组：该组是纯 Python
        # giscanner 用例、无平台阻塞（实测 19/19 通过），没有理由不跑。
        self._run_upstream_warn_tests()

    def _run_upstream_scanner_tests(self):
        """实测上游 tests/scanner 纯 Python unittest 子集（9 个文件），如实填报
        运行数与通过率（输出到 CI 日志）。

        上游 tests/ 按类别划分：
        - scanner 组（test_*.py）：纯 Python unittest，仅 import giscanner 模块
          （本变体已签名置于 conan python lib-dynload）+ vendored distutils，
          不依赖 C 编译 / typelib 生成 → 本环境可实测（rule4 整改）。
        - offsets/repository/warn 组：依赖编译 C 测试库 + 完整 gir 生成环境
          （girepository 静态、subdir('tests') 跳过），按类别 1-e 归因
          （见 test_package/MANIFEST.yml 注释）。
        """
        import subprocess
        _tests = os.path.join(self.source_folder, "tests", "scanner")
        if not os.path.isdir(_tests):
            # P0-1（审查整改）：用例集缺失时**必须阻断**，不得静默 return ——
            # 否则一次源码布局变化就会让「上游用例真实通过」的申报永久失效
            # 而无任何失败信号（R51）。
            raise ConanException(
                "gobject-introspection: upstream tests/scanner not found at %s "
                "—— 上游用例集缺失时不得静默跳过（R51）" % _tests)
        _py_pkg = self.dependencies.build["python"].package_folder
        _py_bin = os.path.join(_py_pkg, "bin", "python3")
        _py_ld = os.path.join(_py_pkg, "lib", "python3.12", "lib-dynload")
        _gi_dist = self._vendored_distutils_dir()
        # 与 g_ir_scanner_env 一致：PYTHONHOME + python lib LD_LIBRARY_PATH +
        # PYTHONPATH（lib-dynload 含 giscanner + vendored distutils）+ PATH 前置。
        _env = os.environ.copy()
        _env["PYTHONHOME"] = _py_pkg
        _ld = [os.path.join(_py_pkg, "lib")]
        for _dep in self.dependencies.values():
            if _dep.package_folder and str(_dep.ref).startswith("glib/"):
                _ld.append(os.path.join(_dep.package_folder, "lib"))
            elif _dep.package_folder and str(_dep.ref).startswith("libintl/"):
                _ld.append(os.path.join(_dep.package_folder, "lib"))
        _env["LD_LIBRARY_PATH"] = ":".join(_ld)
        _pp = [p for p in (_py_ld, _gi_dist) if p]
        _env["PYTHONPATH"] = ":".join(_pp)
        _env["PATH"] = os.path.join(_py_pkg, "bin") + ":" + _env.get("PATH", "")
        _files = sorted(f for f in os.listdir(_tests)
                        if f.startswith("test_") and f.endswith(".py"))
        _passed, _failed = [], []
        for _f in _files:
            _p = os.path.join(_tests, _f)
            try:
                _r = subprocess.run([_py_bin, _p], env=_env, cwd=_tests,
                                    capture_output=True, text=True, timeout=900)
                _rc = _r.returncode
            except Exception as _e:
                _rc = -1
                self.output.warning("gobject-introspection: upstream test %s error: %s" % (_f, _e))
            if _rc == 0:
                _passed.append(_f)
                self.output.info("[UPSTREAM-TEST PASS] %s" % _f)
            else:
                _failed.append(_f)
                self.output.warning("[UPSTREAM-TEST FAIL] %s (rc=%s)" % (_f, _rc))
                # 打印失败输出尾部（Traceback/断言），供 CI 日志定位根因
                _tail = ""
                if _rc != -1:
                    _tail = (_r.stdout or "") + (_r.stderr or "")
                    _tail = "\n".join(_tail.splitlines()[-25:])
                self.output.warning("[UPSTREAM-TEST OUTPUT] %s:\n%s" % (_f, _tail))
        _total = len(_files)
        _ok = len(_passed)
        self.output.info("UPSTREAM-SCANNER-TESTS: %d/%d passed, %d failed | files: %s"
                         % (_ok, _total, len(_failed), ", ".join(_files)))
        if _failed:
            # P0-1（审查整改）：上游用例失败**必须阻断构建**，不再仅打 warning ——
            # 否则 76 个用例即使全挂，`conan create` 仍 EXIT=0、CI 仍判通过，
            # 与「build 期门禁」的申报不符（R51：拒绝在未跑通上游用例时报告通过）。
            # 若确因平台限制无法通过，应在 test_package/MANIFEST.yml 逐项如实标注
            # PASS/FAIL/SKIP 并给出豁免依据，而不是在此静默降级。
            raise ConanException(
                "UPSTREAM-SCANNER-TESTS failed: %d/%d failed (%s) —— "
                "上游用例失败即阻断；如确需豁免，请在 test_package/MANIFEST.yml "
                "逐项标注真实结果与豁免依据"
                % (len(_failed), _total, ", ".join(_failed)))

    def _upstream_warn_fixtures(self):
        """从上游 tests/warn/meson.build 解析 warn_tests 列表（单一事实来源）。

        不硬编码夹具名：上游增删夹具时自动跟随。解析不到即报错 ——
        绝不静默退化成「0 个用例」（R51）。
        """
        _mb = os.path.join(self.source_folder, "tests", "warn", "meson.build")
        if not os.path.isfile(_mb):
            raise ConanException(
                "gobject-introspection: upstream tests/warn/meson.build not found "
                "at %s —— 无法确定 warn 组用例集（R51：不得静默跳过）" % _mb)
        with open(_mb, encoding="utf-8") as _fh:
            _txt = _fh.read()
        _m = re.search(r"warn_tests\s*=\s*\[(.*?)\]", _txt, re.S)
        if not _m:
            raise ConanException(
                "gobject-introspection: cannot parse the warn_tests list from %s "
                "—— 上游布局可能已变（R51：不得静默跳过）" % _mb)
        _names = sorted(set(re.findall(r"'([^']+\.h)'", _m.group(1))))
        if not _names:
            raise ConanException(
                "gobject-introspection: warn_tests parsed empty from %s "
                "—— 拒绝以「0 个用例」冒充已运行" % _mb)
        return _names

    def _run_upstream_warn_tests(self):
        """直跑上游 tests/warn 组（夹具集由 meson 的 warn_tests 定义），如实判定。

        为什么必须补跑：build() 把上游 meson.build 的 `subdir('tests')` 闸门
        置为恒假，使 meson 注册的 offsets/repository/warn 三组**全部从未执行**。
        其中 offsets(1)/repository(4) 是编译型 C 测试，运行期需 GLib/GObject/Gio
        的 typelib，而本仓 glib 为 `introspection=disabled`（0 typelib）→ 有确凿
        平台阻塞。

        但 warn 组**没有该阻塞**：warningtester.py 是**纯 Python** —— 只 import
        giscanner.*（SourceScanner / Transformer / MainTransformer /
        IntrospectablePass），不加载任何 typelib、不 dlopen 上游共享库；夹具唯一
        的系统依赖是 common.h 的 `<glib-object.h>`，而 glib 是本配方现成依赖。
        故把整组当「环境受限」一并裁剪是错的，这里逐夹具真跑（实测 19/19 通过）。

        env 与 meson 注册该测试时一致（见上游 tests/warn/meson.build）：
        - UNINSTALLED_INTROSPECTION_SRCDIR / TOP_BUILDDIR：脚本开头直接断言读取；
          且 TOP_BUILDDIR 是其 gir 搜索路径之一 —— top_builddir/gir 下有构建期
          生成的 GObject-2.0.gir，脚本的 register_include('GObject-2.0') 依赖它。
        - PKG_CONFIG_PATH：脚本内部 `process_packages(['gobject-2.0'])` 取 Cflags
          喂给预处理器；解析失败脚本会 sys.exit 非零。
        - PATH：需含编译器（预处理器）与 pkg-config。
        """
        _tests = os.path.join(self.source_folder, "tests", "warn")
        _fixtures = self._upstream_warn_fixtures()
        _py_pkg = self.dependencies.build["python"].package_folder
        _py_bin = os.path.join(_py_pkg, "bin", "python3")
        _py_ld = os.path.join(_py_pkg, "lib", "python3.12", "lib-dynload")
        _gi_dist = self._vendored_distutils_dir()
        _env = os.environ.copy()
        _env["PYTHONHOME"] = _py_pkg
        _ld = [os.path.join(_py_pkg, "lib")]
        for _dep in self.dependencies.values():
            if _dep.package_folder and str(_dep.ref).startswith("glib/"):
                _ld.append(os.path.join(_dep.package_folder, "lib"))
            elif _dep.package_folder and str(_dep.ref).startswith("libintl/"):
                _ld.append(os.path.join(_dep.package_folder, "lib"))
        _env["LD_LIBRARY_PATH"] = ":".join(_ld)
        _env["PYTHONPATH"] = ":".join([p for p in (_py_ld, _gi_dist) if p])
        _env["PATH"] = ":".join([os.path.join(_py_pkg, "bin"), HNP_BIN,
                                 _env.get("PATH", "")])
        # 脚本内 process_packages() 需 conan 生成的 glib-2.0.pc / pcre2.pc 等
        _gen = self.generators_folder
        if _gen:
            _env["PKG_CONFIG_PATH"] = ":".join(
                [p for p in (_gen, _env.get("PKG_CONFIG_PATH", "")) if p])
        _env["UNINSTALLED_INTROSPECTION_SRCDIR"] = self.source_folder
        _env["TOP_BUILDDIR"] = self._build_dir()

        _passed, _failed = [], []
        for _f in _fixtures:
            try:
                _r = subprocess.run([_py_bin, "warningtester.py", _f], env=_env,
                                    cwd=_tests, capture_output=True, text=True,
                                    timeout=900)
                _rc = _r.returncode
            except Exception as _e:
                _rc = -1
                self.output.warning(
                    "gobject-introspection: upstream warn test %s error: %s" % (_f, _e))
            if _rc == 0:
                _passed.append(_f)
                self.output.info("[UPSTREAM-WARN PASS] %s" % _f)
            else:
                _failed.append(_f)
                self.output.warning("[UPSTREAM-WARN FAIL] %s (rc=%s)" % (_f, _rc))
                _tail = ""
                if _rc != -1:
                    _tail = (_r.stdout or "") + (_r.stderr or "")
                    _tail = "\n".join(_tail.splitlines()[-25:])
                self.output.warning("[UPSTREAM-WARN OUTPUT] %s:\n%s" % (_f, _tail))
        self.output.info("UPSTREAM-WARN-TESTS: %d/%d passed, %d failed"
                         % (len(_passed), len(_fixtures), len(_failed)))
        if _failed:
            # 与 scanner 组同规格（P0-1）：该组为纯 Python giscanner 用例、无平台
            # 阻塞，失败即阻断；确需豁免须在 MANIFEST 逐项标注真实结果与依据。
            raise ConanException(
                "UPSTREAM-WARN-TESTS failed: %d/%d failed (%s) —— "
                "该组为纯 Python giscanner 用例、无平台阻塞，失败即阻断；"
                "如确需豁免，请在 test_package/MANIFEST.yml 逐项标注真实结果与依据"
                % (len(_failed), len(_fixtures), ", ".join(_failed)))

    def _install_giscanner_to_package(self):
        """E212：把 giscanner Python 模块（含 _giscanner.so）复制到 conan python
        包的 lib-dynload（扩展默认加载目录，loader 白名单内）并签名，使
        g-ir-scanner 能 dlopen _giscanner.so。

        鸿蒙 loader 白名单按进程绑定：conan python 只能 dlopen 其自身安装树内
        lib-dynload 下的扩展（python 包自身扩展在此加载成功）；b/(build)、
        gobject p/、site-packages 均不可加载（#37178/#37213 证实）。
        """
        _src = os.path.join(self._build_dir(), "giscanner")
        _py_pkg = self.dependencies.build["python"].package_folder
        _dst = os.path.join(_py_pkg, "lib", "python3.12", "lib-dynload", "giscanner")
        if not os.path.isdir(_src):
            self.output.warning("gobject-introspection: giscanner build dir missing: %s" % _src)
            return
        if not os.path.isdir(_py_pkg):
            self.output.warning("gobject-introspection: python pkg missing: %s" % _py_pkg)
            return
        # 幂等：目标目录可能残留上一轮已签名文件（签名后 .so 不可覆盖，
        # 直接 copy2 报 PermissionError: Operation not permitted），先整体清掉再重建。
        if os.path.isdir(_dst):
            shutil.rmtree(_dst, ignore_errors=True)
        os.makedirs(_dst, exist_ok=True)
        for _f in os.listdir(_src):
            _p = os.path.join(_src, _f)
            _t = os.path.join(_dst, _f)
            if os.path.isdir(_p):
                shutil.copytree(_p, _t, dirs_exist_ok=True)
            else:
                shutil.copy2(_p, _t)
        for _so in glob.glob(os.path.join(_dst, "**", "*.so*"), recursive=True):
            if not os.path.isfile(_so):
                continue
            self._sign_elf(_so)
            self.output.info("gobject-introspection: signed pkg-giscanner %s" % os.path.basename(_so))
        # 关键：patch 生成的 g-ir-scanner 脚本——模板 g-ir-tool-template.in 在
        # meson uninstalled 分支会 `sys.path.insert(0, pylibdir)` 把 build-release
        # 插到 sys.path[0]，优先于 PYTHONPATH。改为指向 conan python 的
        # lib-dynload（loader 白名单内 + 已签名）。
        _tool = os.path.join(self._build_dir(), "tools", "g-ir-scanner")
        _py_ld = os.path.join(_py_pkg, "lib", "python3.12", "lib-dynload")
        if os.path.isfile(_tool):
            _txt = open(_tool, encoding="utf-8").read()
            _old = "sys.path.insert(0, pylibdir)"
            _new = "sys.path.insert(0, '%s')" % _py_ld
            if _old in _txt and _new not in _txt:
                _txt = _txt.replace(_old, _new, 1)
                open(_tool, "w", encoding="utf-8").write(_txt)
                self.output.info("gobject-introspection: patched g-ir-scanner sys.path[0] -> %s" % _py_ld)
        self.output.info("gobject-introspection: giscanner installed to python lib-dynload %s" % _dst)

    def _build_dir(self):
        """Return the meson build dir (e.g. build-release under build_folder)."""
        _b = os.path.join(self.build_folder, "build-release")
        return _b if os.path.isdir(_b) else self.build_folder

    def _sign_build_artifacts(self):
        """E077b：对 build 目录中 g-ir-scanner 运行所需的 .so 与 C 工具签名，
        使 gir/typelib 生成阶段可 dlopen/exec（鸿蒙签名要求）。"""
        _bdir = self._build_dir()
        # 同 package()：用 "*.so*" 覆盖版本化实体库（libgirepository-1.0.so.1.0.0）
        for _so in glob.glob(os.path.join(_bdir, "**", "*.so*"), recursive=True):
            if not os.path.isfile(_so):
                continue
            self._sign_elf(_so)
            self.output.info("gobject-introspection: pre-signed build %s" % os.path.basename(_so))
        for _t in ("g-ir-compiler", "g-ir-generate", "g-ir-inspect"):
            _p = os.path.join(_bdir, "tools", _t)
            if os.path.isfile(_p):
                self._sign_elf(_p)
                self.output.info("gobject-introspection: pre-signed build tools/%s" % _t)

    def package(self):
        meson = Meson(self)
        meson.install()
        # E077：meson.install() 后重签所有 .so（_giscanner.so 等）+ bin/ 可执行
        # 文件（g-ir-compiler/g-ir-generate/g-ir-inspect 为 C 二进制，exec 需签名），
        # 否则消费方 g-ir-scanner dlopen / g-ir-compiler exec 报 Permission
        # denied / Operation not permitted。
        # 注：glob 用 "*.so*" 而非 "*.so" —— 版本化实体库
        # （libgirepository-1.0.so.1.0.0）不以 .so 结尾，若只匹配 "*.so" 会漏签，
        # 运行时 dlopen 报 "Error loading shared library ...: Permission denied"。
        # 非 ELF 文件由 _sign_elf 的 ELF magic 检查跳过。
        for _so in glob.glob(os.path.join(self.package_folder, "**", "*.so*"),
                             recursive=True):
            if not os.path.isfile(_so):
                continue
            self._sign_elf(_so)
            self.output.info("gobject-introspection: re-signed %s" % os.path.basename(_so))
        _bin = os.path.join(self.package_folder, "bin")
        if os.path.isdir(_bin):
            for _f in os.listdir(_bin):
                _p = os.path.join(_bin, _f)
                if os.path.isfile(_p) and not _f.endswith((".py", ".txt")):
                    self._sign_elf(_p)
                    self.output.info("gobject-introspection: re-signed bin/%s" % _f)

    def _sign_elf(self, path):
        """E077：对 ELF 文件进行鸿蒙自签名（原子方式）。

        参考 python/3.12.9 配方验证过的 _sign_elf_atomically：先复制到
        .signing 临时文件再签名，避免 binary-sign-tool 原地签名失败；
        用 self.run 显示输出并在失败时抛异常（此前 capture_output 静默
        失败导致 build 阶段 _giscanner.so 仍报 Permission denied）。
        非 ELF 文件（如 g-ir-scanner Python 脚本）跳过——binary-sign-tool
        对非 ELF 报 "not an elf file"（CI #38535）。
        """
        # ELF magic 检查（参考 python/3.12.9 _sign_shared_libraries）
        try:
            with open(path, "rb") as _f:
                if _f.read(4) != b"\x7fELF":
                    return
        except OSError:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            # P1-3（审查整改）：签名工具缺失时**必须报错**，不再仅 warning 后跳过。
            # 理由：OHOS loader 只接受已签名的 ELF，签名是硬前置；静默跳过会把失败
            # 延后到消费方 dlopen 时才以 `Permission denied` 暴露，而构建期却判通过。
            raise ConanException(
                "gobject-introspection: signing tools unavailable (%s / %s) —— "
                "无法对 %s 签名。OHOS loader 只接受已签名 ELF，静默跳过会把 "
                "Permission denied 延后到消费方 dlopen（P1-3 整改）"
                % (objcopy, signer, path))
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(f'"{objcopy}" --remove-section .codesign "{temporary}" || true')
            self.run(f'"{signer}" sign -inFile "{temporary}" '
                     f'-outFile "{temporary}" -selfSign 1')
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def package_info(self):
        self.cpp_info.libs = ["girepository-1.0"]
        self.cpp_info.includedirs = ["include/gobject-introspection-1.0"]
        self.cpp_info.set_property("pkg_config_name", "gobject-introspection-1.0")
        # 运行期：typelib 路径 + glib 共享库 + 合并 libintl（供消费方 GI_TYPELIB_PATH/LD_LIBRARY_PATH）
        self.runenv_info.prepend_path(
            "GI_TYPELIB_PATH", os.path.join(self.package_folder, "lib", "girepository-1.0"))
