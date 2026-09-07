#!/usr/bin/env python3
"""Conan recipe — qalculate-gtk 5.8.2-r0 (Autotools).

qalculate-gtk 是 libqalculate 的 GTK3 图形前端（计算器 GUI）。Autotools 构建，
产出可执行文件 qalculate-gtk（bin/）与 qalculate-search-provider（libexec/）。

OHOS 适配（参考 main 上已合入的 gnumeric 同类 GTK 栈方案 + libqalculate 经验）:
- config.guess: 添加 HarmonyOS 检测（aarch64-HarmonyOS -> aarch64-unknown-linux-gnu）
- configure: 跳过 IT_PROG_INTLTOOL 的 XML::Parser(perl) 检查（OHOS 无该模块）；
  移除 umask 077（HMDFS 限制）
- GTK3 生态（gtk3/glib/cairo/pango/gdk-pixbuf/harfbuzz/fontconfig/freetype/
  libepoxy/pixman/fribidi/libpng）由 cmd-pkgs 预编译包体系提供（gnumeric 已验证，
  CI 与设备一致），libqalculate 及其 math 依赖链走 conan requires（R36）

⚠️ 不用 AutotoolsDeps/VirtualRunEnv（libqalculate 同坑）：
AutotoolsDeps 会把 conan 依赖 -l 全塞进 LIBS → configure 早期 conftest 链上依赖
运行期找不到 .so；VirtualRunEnv 会把 conan 依赖 lib 目录塞进 LD_LIBRARY_PATH →
llvm lld 自身依赖 SDK libxml2.so.16 被 conan libxml2.so.16 劫持崩溃。依赖路径用
include/lib flag 手动注入，LD_LIBRARY_PATH 在 build() 内 os.environ 显式注入。
"""
import os
import re

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, load, save
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

# cmd-pkgs GTK 生态（gnumeric 同款；gtk 包名含前导空格）
CMD_PKGS = [
    ("gdk-pixbuf", "2.42.12", "gdk-pixbuf-2.0.pc"),
    ("atk", "2.38.0", "atk.pc"),
    # fribidi 用 1.0.13：cmd-pkgs 的 1.0.16 包损坏（tar 非有效，CI 反复
    # ReadError）；1.0.13 包完好且含 fribidi.pc（gnumeric 已合入同款版本）
    ("fribidi", "1.0.13", "fribidi.pc"),
    ("libepoxy", "1.5.10", "epoxy.pc"),
    ("libpng", "1.6.43", "libpng.pc"),
    ("fontconfig", "2.16.0", "fontconfig.pc"),
    ("freetype", "2.14.3", "freetype2.pc"),
    ("harfbuzz", "14.2.0", "harfbuzz.pc"),
    ("pixman", "0.46.4", "pixman-1.pc"),
    ("pango", "1.50.14", "pango.pc"),
    # cairo 不走 cmd-pkgs（包仅含 .so 无 .pc，制品仓也无 1.18.2）——
    # 由 conan requires cairo-gobject/1.18.4 提供（对齐 gnumeric 已合入先例），
    # 并在 generate() 用 _derive_cairo_pc() 派生 cairo.pc
    ("gtk ", "3.24.38", "gtk+-3.0.pc"),
    ("glib", "2.88.0", "glib-2.0.pc"),
    # glib-2.0.pc 声明 Requires: libpcre2-8 >= 10.32——CI 干净环境需一并安装
    ("pcre2", "10.40", "libpcre2-8.pc"),
    # gobject-2.0.pc 声明 Requires: glib-2.0, libffi >= 3.0.0——CI 干净环境需一并安装
    ("libffi", "3.4.4", "libffi.pc"),
    # freetype2.pc 声明 Requires: zlib, libpng——CI 干净环境需一并安装
    ("zlib", "1.3.1", "zlib.pc"),
    # fontconfig.pc 声明 Requires: expat——注意 cmd-pkgs 的 expat-2.8.0 包已损坏
    # （tar bad header，CI 反复 ReadError），2.7.1 为可用版本
    ("expat", "2.7.1", "expat.pc"),
    # gdk-pixbuf-2.0.pc 声明 Requires: libpng, libjpeg——libjpeg.pc 由
    # cmd-pkgs libjpeg-turbo 包提供（gnumeric 已合入同款）
    ("libjpeg-turbo", "3.1.4.1", "libjpeg.pc"),
]
TOOL_PKGS = [
    ("intltool", "0.51.0", "bin/intltool-update"),
    # gettext 标记用 lib/libintl.so.8 而非 bin/msgfmt：CI worker 主目录跨构建
    # 复用，残留 bin/msgfmt 会跳过安装 → libintl.so.8 缺失 → configure 阶段
    # msgmerge 回落 conan/system 不完整 libintl（libintl_gettext 符号缺失，
    # CI #37565 回归根因）
    ("gettext", "0.22.5", "lib/libintl.so.8"),
]
GTK_PREFIX = os.path.expanduser("~/usr/local")


class QalculateGtkConan(ConanFile):
    name = "qalculate-gtk"
    version = "5.8.2-r0"
    description = "GTK3 GUI front-end for Qalculate! (multi-purpose desktop calculator)"
    license = "GPL-2.0-or-later"
    homepage = "https://qalculate.github.io/"
    url = "https://github.com/Qalculate/qalculate-gtk"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libqalculate：计算引擎核心硬依赖（configure PKG_CHECK_MODULES QALCULATE）
        self.requires("libqalculate/5.8.2-r0")
        # libqalculate 公共头文件（qalculate.h -> Number.h）直接 #include <gmp.h>，
        # gmp/mpfr 必须显式 requires（与 libqalculate 配方一致）才能把 include
        # 路径注入下游编译（CI #37465：Number.h fatal error 'gmp.h' not found）
        self.requires("gmp/6.3.0")
        self.requires("mpfr/4.2.2")
        # cairo/cairo-gobject：cmd-pkgs GTK 栈的 gdk-3.0.pc 声明 Requires
        # cairo/cairo-gobject，但 cmd-pkgs cairo 包仅含 .so 无 .pc 且制品仓仅
        # 有 1.18.4（1.18.2 不存在）——对齐已合入 main 的 gnumeric 先例：cairo
        # 走 conan requires，由 PkgConfigDeps 生成 cairo-gobject.pc，再派生
        # cairo.pc（_derive_cairo_pc），替代 CI 沙箱不可靠的手工补齐。
        self.requires("cairo-gobject/1.18.4")
        # cairo-gobject 传递 requires glib/2.84.Z，与 cmd-pkgs GTK 栈预编译用的
        # glib 2.88 符号集不一致会符号缺失（gnumeric 踩坑记录）→ override 统一
        self.requires("glib/2.88.0.1", override=True)
        # glib/2.88.0.1 依赖 zlib/1.3.1.1.1.1，而图内已有 zlib/1.3.1.1 →
        # 版本冲突（conan 报 Version conflict）；与 gnumeric 同款 override 统一
        self.requires("zlib/1.3.1.1.1.1", override=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        # cairo-gobject/1.18.4 只产出 cairo-gobject.pc（gnumeric 同款：PkgConfigDeps
        # 不为 cairo 包生成 cairo.pc）——从依赖包派生 cairo.pc 到 generators_folder
        self._derive_cairo_pc()
        tc = AutotoolsToolchain(self)
        # GNOME Shell 搜索集成禁用（鸿蒙 PC 无 GNOME Shell；gdbus-codegen 需
        # Python pyexpat 模块，conanbuild 环境不可用。search-provider 为可选
        # 组件，--disable-gnome-search 后不生成 gnome-search-provider2.c）
        tc.configure_args.append("--disable-gnome-search")
        # glib 工具 wrapper（gnumeric 已合入先例）：ELF 工具（glib-compile-
        # resources 等）设 LD_LIBRARY_PATH 指向 conan glib 包 lib，python 工具
        # unset LD_LIBRARY_PATH——避免 conan 依赖与 cmd-pkgs GTK 栈库混用
        # （固化绝对路径在本机生成 ui.c 时 Segfault；build() 内 os.environ PATH
        # 会被 conanbuild 环境覆盖，必须在此经 tc.environment() 注入生效）
        self._write_glib_tool_wrappers()
        # PATH 前置 ~/usr/local/bin + _glib_tools（通过 tc 环境下发，比独立 env
        # 脚本优先级高）：make 阶段 glib-compile-resources 必须用 wrapper/cmd-pkgs
        # 自带工具（RUNPATH=$ORIGIN/../lib 相对路径，可正常加载 libffi/libz）；
        # profile 的 PATH=+ 会把 /data/service/hnp/bin 前置（其 RUNPATH 指向不
        # 存在的 /home/lycium++/... 回落加载错误 libffi），故在此强制前置。
        _env = tc.environment()
        _env.prepend_path("PATH", os.path.join(GTK_PREFIX, "bin"))
        _env.prepend_path("PATH", os.path.join(self.build_folder, "_glib_tools"))
        # 依赖 include/lib 路径手动注入（不用 AutotoolsDeps，见模块 docstring）
        # 注意：必须在同一个 _env 对象上依次操作（再取 tc.environment() 会丢弃
        # 前面的 PATH 前置，W4 审计 code_style-3）
        for _ref, _dep in self.dependencies.items():
            _inc = " ".join("-I{}".format(_d)
                            for _d in (_dep.cpp_info.includedirs or [])
                            if os.path.isabs(_d))
            if _inc:
                _env.prepend("CPPFLAGS", _inc)
                _env.prepend("CXXFLAGS", _inc)
                _env.prepend("CFLAGS", _inc)
            _lp = " ".join("-L{}".format(_d)
                           for _d in (_dep.cpp_info.libdirs or [])
                           if os.path.isabs(_d))
            if _lp:
                _env.prepend("LDFLAGS", _lp)
        tc.generate(_env)

    def _derive_cairo_pc(self):
        """cairo-gobject/1.18.4 的 PkgConfigDeps 只生成 cairo-gobject.pc，而
        gdk-3.0.pc/gtk+-3.0.pc 的 Requires 同时需要 cairo.pc —— 从依赖包
        package_folder 派生 cairo.pc 到 generators_folder（gnumeric 已合入同款）。"""
        dst = os.path.join(self.generators_folder, "cairo.pc")
        if os.path.exists(dst):
            return
        dep = self.dependencies.get("cairo-gobject")
        if dep is None or dep.package_folder is None:
            self.output.warning("cairo-gobject dep not found, skip derive cairo.pc")
            return
        prefix = dep.package_folder
        text = (
            "prefix={prefix}\n"
            "libdir=${{prefix}}/lib\n"
            "includedir=${{prefix}}/include\n"
            "\n"
            "Name: cairo\n"
            "Description: Multi-platform 2D graphics library\n"
            "Version: 1.18.4\n"
            "Libs: -L${{libdir}} -lcairo\n"
            "Cflags: -I${{includedir}} -I${{includedir}}/cairo\n"
        ).format(prefix=prefix)
        save(self, dst, text)
        self.output.info("Derived cairo.pc from cairo-gobject package")

    def _install_cmd_pkg(self, name, version, prefix, marker=None):
        if marker and os.path.isfile(os.path.join(prefix, "lib", "pkgconfig", marker)):
            self.output.info(f"{name} already installed")
            return
        import ssl
        import tarfile
        import urllib.request
        from io import BytesIO
        fname = f"{name}-{version}-ohos-aarch64.tar.gz"
        url = ("https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/"
               f"download/pkgs/{fname.replace(' ', '%20')}")
        # 系统 CA 证书校验（W4 审计 R19：禁用校验存在供应链风险；
        # cmd-pkgs 为项目正式预编译包体系，与 gnumeric 已合入先例一致）
        ctx = ssl.create_default_context()
        data = None
        for attempt in (1, 2, 3):
            self.output.info(f"Installing {name} {version} from cmd-pkgs (try {attempt})")
            try:
                with urllib.request.urlopen(url, context=ctx, timeout=600) as resp:
                    data = resp.read()
                # gzip 魔数校验：CI worker 偶发返回非 gzip 内容（HTML/截断）
                if not (data[:2] == b"\x1f\x8b" and data):
                    self.output.warning(
                        f"  {name} download not gzip (len={len(data)}), retry")
                    data = None
                    continue
                # 解压同样纳入重试：数据可能含 gzip 魔数但 tar 内容损坏
                # （CI worker 污染）——tarfile.open 失败需重试而非中断
                with tarfile.open(fileobj=BytesIO(data), mode="r:gz") as tf:
                    os.makedirs(prefix, exist_ok=True)
                    tf.extractall(prefix)
                break
            except Exception as exc:
                self.output.warning(f"  {name} download/extract failed: {exc}, retry")
                data = None
        if data is None:
            # 降级：交由 .pc 补齐逻辑（_fill_pc_from_conan）接管
            self.output.warning(f"  {name} {version} download failed after 3 tries, "
                                f"defer to conan-fill")
            return
        self.output.info(f"  Installed {name} {version} from cmd-pkgs")

    def _ensure_gtk_stack(self):
        # CMD_PKGS 元组：name, version(cmd-pkgs), marker[, conan_version(制品仓补齐)]
        for item in CMD_PKGS:
            name, version, marker = item[0], item[1], item[2]
            self._install_cmd_pkg(name, version, GTK_PREFIX, marker)
        # libpng：cmd-pkgs 只产出 libpng16.pc，但 freetype2.pc 声明
        # Requires: libpng（需 libpng.pc）——补建别名（gnumeric 已合入同款处理）
        _pc_dir = os.path.join(GTK_PREFIX, "lib", "pkgconfig")
        _src16 = os.path.join(_pc_dir, "libpng16.pc")
        _dst = os.path.join(_pc_dir, "libpng.pc")
        if os.path.isfile(_src16) and not os.path.isfile(_dst):
            import shutil
            shutil.copy2(_src16, _dst)
            self.output.info("created libpng.pc alias from libpng16.pc")
        # 凡 cmd-pkgs 未产出标记 .pc（如 cairo 仅含 .so）的组件，从 conan 制品仓
        # 确定性补齐（避免 CI 干净环境缺 .pc 导致 configure 报 not found）。
        # 制品仓版本可能与 cmd-pkgs 不同（如 cairo: cmd-pkgs=1.18.2 无 .pc，
        # 制品仓=1.18.4 含 cairo.pc+cairo-gobject.pc）——取第 4 字段。
        for item in CMD_PKGS:
            name, version, marker = item[0], item[1], item[2]
            if marker and not os.path.isfile(os.path.join(_pc_dir, marker)):
                _cv = item[3] if len(item) > 3 else version
                self._fill_pc_from_conan(name, _cv, marker)
        for name, version, marker in TOOL_PKGS:
            if not os.path.isfile(os.path.join(GTK_PREFIX, marker)):
                self._install_cmd_pkg(name, version, GTK_PREFIX, marker)

    def _fill_pc_from_conan(self, name, version, pc_name):
        """cmd-pkgs 包缺 .pc（仅 .so）——从制品仓 conan 包补齐（确定性来源）。

        先 conan download <name>/<version>（remote 动态解析，不在源码硬编码
        remote 名称——L0g 门禁禁止 conanfile 出现硬编码 remote/-r= 写法），
        再从缓存复制 .pc 与同名 .so 到 GTK_PREFIX。

        缓存目录名按包名前 5 字符截断（Conan 2 行为，如 fribidi -> fribi*），
        glob 需用截断前缀匹配。"""
        import glob
        import shutil
        import subprocess
        # remote 动态解析（L0g：禁止硬编码 remote 名称）
        # 注意：必须选 Enabled: True 的 remote（conancenter 常为 disabled，
        # 选中会导致 download 失败——CI #37378 曾因此拿不到 fribidi）
        _remote = None
        try:
            _rout = subprocess.run(["conan", "remote", "list"],
                                   capture_output=True, text=True, timeout=60)
            for _line in (_rout.stdout or "").splitlines():
                if "Enabled: True" not in _line:
                    continue
                _tok = _line.strip().split(":")[0].strip()
                if _tok and not _tok.startswith("("):
                    _remote = _tok
                    break
        except Exception as exc:
            self.output.warning(f"conan remote list failed: {exc}")
        # 注意：必须全量下载（含 binary 包），不能用 --only-recipe——
        # 仅下载配方时缓存无安装目录，glob 找不到可复制的 .pc。
        if _remote:
            try:
                subprocess.run(["conan", "download", f"{name}/{version}:*",
                                "-r", _remote],
                               capture_output=True, timeout=600, check=False)
            except Exception as exc:
                self.output.warning(f"conan download {name} failed: {exc}")
        # 缓存路径随 CONAN_HOME 变化（本机 ~/.conan2，CI ~/.cache/conan2），
        # 遍历两种布局 + 环境变量兜底；目录名按前 5 字符截断（Conan 2 行为）
        _roots = set()
        for _env_key in ("CONAN_HOME", "CONAN_USER_HOME"):
            if os.environ.get(_env_key):
                _roots.add(os.path.expanduser(os.environ[_env_key]))
        _roots.update([
            os.path.expanduser("~/.conan2"),
            os.path.expanduser("~/.cache/conan2"),
        ])
        _pkg_cands = []
        _short = name[:5]
        for _root in _roots:
            _pkg_cands += sorted(glob.glob(
                os.path.join(_root, "p", f"{_short}*/p")))
        _pkg_cands = sorted(set(_pkg_cands))
        _pc_dir = os.path.join(GTK_PREFIX, "lib", "pkgconfig")
        os.makedirs(_pc_dir, exist_ok=True)
        for cand in _pkg_cands:
            pc_src = os.path.join(cand, "lib", "pkgconfig", pc_name)
            if not os.path.isfile(pc_src):
                continue
            # 复制包内全部 .pc（如 cairo.pc + cairo-gobject.pc——gdk-3.0 声明
            # Requires cairo-gobject，只复制 marker 单文件会漏）
            _pkg_pc_dir = os.path.join(cand, "lib", "pkgconfig")
            if os.path.isdir(_pkg_pc_dir):
                for _f in os.listdir(_pkg_pc_dir):
                    if _f.endswith(".pc"):
                        shutil.copy2(os.path.join(_pkg_pc_dir, _f),
                                     os.path.join(_pc_dir, _f))
            # 复制同名 .so 及全部依赖库（libcairo-gobject 等）避免链接期缺失
            _cand_lib = os.path.join(cand, "lib")
            if os.path.isdir(_cand_lib):
                for _f in os.listdir(_cand_lib):
                    if _f.startswith(f"lib{name}") or _f.startswith("libcairo"):
                        _src_f = os.path.join(_cand_lib, _f)
                        if os.path.isfile(_src_f):
                            shutil.copy2(_src_f,
                                         os.path.join(GTK_PREFIX, "lib", _f))
            # 复制头文件（cairo.h 等——无头文件时 qalculate-gtk 编译期缺 include）
            _cand_inc = os.path.join(cand, "include")
            if os.path.isdir(_cand_inc):
                _dst_inc = os.path.join(GTK_PREFIX, "include")
                os.makedirs(_dst_inc, exist_ok=True)
                for _sub in os.listdir(_cand_inc):
                    _src_sub = os.path.join(_cand_inc, _sub)
                    _dst_sub = os.path.join(_dst_inc, _sub)
                    if os.path.isdir(_src_sub):
                        os.makedirs(_dst_sub, exist_ok=True)
                        for _f in os.listdir(_src_sub):
                            if _f.endswith(".h"):
                                shutil.copy2(os.path.join(_src_sub, _f),
                                             os.path.join(_dst_sub, _f))
            self.output.info(f"Filled {pc_name} (+ all .pc/.so/headers) "
                             f"from conan registry cache ({cand})")
            return
        # 兜底：库已由 cmd-pkgs 安装（仅缺 .pc 元数据）时合成最小 .pc
        if os.path.isfile(os.path.join(GTK_PREFIX, "lib", f"lib{name}.so")):
            _libname = name.strip()
            _pc = (
                f"prefix={GTK_PREFIX}\n"
                f"exec_prefix=${{prefix}}\n"
                f"libdir=${{prefix}}/lib\n"
                f"includedir=${{prefix}}/include\n"
                f"\n"
                f"Name: GNU {_libname}\n"
                f"Description: {_libname} (cmd-pkgs, minimal pc)\n"
                f"Version: {version}\n"
                f"Libs: -L${{libdir}} -l{_libname}\n"
                f"Cflags: -I${{includedir}}\n"
            )
            with open(os.path.join(_pc_dir, pc_name), "w") as f:
                f.write(_pc)
            self.output.info(f"Synthesized minimal {pc_name} "
                             f"(lib{name}.so present)")
            return
        self.output.warning(f"No conan {name} cache found to fill {pc_name} "
                            f"(roots={sorted(_roots)})")

    def _write_intltool_shim(self):
        """替代 intltool-merge/extract：去 _ 翻译标记（XML::Parser 不可用）。
        必须覆盖 $HOME/usr/local/bin 同名工具（configure AC_PATH_PROG 优先命中，
        CI 干净环境复刻本地验证）。"""
        bin_dir = os.path.join(GTK_PREFIX, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        for tool in ("intltool-merge", "intltool-extract"):
            real = os.path.join(bin_dir, tool)
            if os.path.exists(real) and not os.path.exists(real + ".cmdpkgs"):
                os.rename(real, real + ".cmdpkgs")
            script = (
                "#!/bin/sh\n"
                "input=\"\"\n"
                "output=\"\"\n"
                "for arg in \"$@\"; do\n"
                "    input=\"$output\"\n"
                "    output=\"$arg\"\n"
                "done\n"
                "[ -n \"$input\" ] && [ -n \"$output\" ] || exit 1\n"
                "perl -pe 's/<(\\/?)_([a-zA-Z][a-zA-Z0-9_]*)>/<$1$2>/g' \"$input\" > \"$output\"\n"
            )
            with open(real, "w") as f:
                f.write(script)
            os.chmod(real, 0o755)
        self.output.info("Wrote intltool-merge/extract shims")

    def _fix_la_files(self):
        """依赖 .la 的 libdir='//lib'（libqalculate 同坑）——跨包全局映射修复。

        注（W4 audit R6）：此修复改写 conan 缓存依赖包 package_folder 下的 .la，
        与 main 上已合入的 libgsf 1.14.5 配方同款方案（E236 经验，依赖包 .la
        生成时即带 //lib 错误路径，需在链接期修正）；仅修正绝对路径字段，不
        影响依赖包功能，属构建期必要修复。"""
        la_registry = {}
        for _ref, _dep in self.dependencies.items():
            dep_pkg = _dep.package_folder
            if not dep_pkg:
                continue
            dep_lib = os.path.join(dep_pkg, "lib")
            if not os.path.isdir(dep_lib):
                continue
            for la_name in os.listdir(dep_lib):
                if la_name.endswith(".la"):
                    la_registry[la_name] = os.path.join(dep_lib, la_name)
        for la_path in la_registry.values():
            with open(la_path, "r", encoding="utf-8", errors="replace") as f:
                lac = f.read()
            own_lib = os.path.dirname(la_path)
            fixed = lac.replace("libdir='//lib'", f"libdir='{own_lib}'")
            for base, real in la_registry.items():
                fixed = fixed.replace(f"//lib/{base}", real)
                if not real.startswith(own_lib):
                    fixed = fixed.replace(f"{own_lib}/{base}", real)
            if fixed != lac:
                with open(la_path, "w", encoding="utf-8") as f:
                    f.write(fixed)
                self.output.info(
                    f"patched {os.path.basename(la_path)}: libdir/deps -> {own_lib}")

    def _fix_gdbus_codegen(self):
        """构建期 glib 工具固化为可执行路径（configure 后、make 前）。

        src/Makefile 中裸调用 gdbus-codegen/glib-compile-resources，make 时经
        PATH 解析会命中 /data/service/hnp/bin 坏版本：
        - gdbus-codegen：shebang #!/usr/bin/python3（OHOS 无此路径 -> bad
          interpreter）
        - glib-compile-resources：RUNPATH 指向不存在的 /home/lycium++/...，
          回落加载错误 libffi.so.8（符号缺失，Error 127）
        修复：把 src/Makefile 中这些工具调用替换为固定可执行绝对路径——
        - gdbus-codegen：cmd-pkgs 本地版（#!/usr/bin/env python3 可运行）
        - glib-compile-resources：_glib_tools wrapper（generate() 已生成，wrapper
          内 LD_LIBRARY_PATH 指向 conan glib 包 lib，工具与库同源，避免固化
          本地 cmd-pkgs 版与 conan 依赖混用的 Segfault）
        不依赖 PATH（conanbuildenv PATH=+ 会覆盖 generate() 的 PATH 前置，CI
        实证 toolchain PATH 已含 _glib_tools 但 make 仍命中 hnp 版）。"""
        import glob
        _fixes = [
            # gdbus-codegen：--disable-gnome-search 下 Makefile 可能已无引用，
            # 保留修复无害
            ("gdbus-codegen",
             os.path.join(GTK_PREFIX, "bin", "gdbus-codegen")),
            # glib-compile-resources：必须用 _glib_tools wrapper（LD_LIBRARY_PATH
            # 指向 conan glib lib，工具/库同源防 Segfault）
            ("glib-compile-resources",
             os.path.join(self.build_folder, "_glib_tools", "glib-compile-resources")),
        ]
        for _tool, good in _fixes:
            if not os.path.isfile(good):
                self.output.warning(f"{good} not found, skip {_tool} fix")
                continue
            for mk in glob.glob(os.path.join(self.build_folder, "src", "Makefile")):
                with open(mk, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                fixed = content.replace(_tool, good)
                if fixed != content:
                    with open(mk, "w", encoding="utf-8") as f:
                        f.write(fixed)
                    self.output.info(f"patched {mk}: {_tool} -> {good}")

    def _write_wrapper(self, wrapper, script):
        import os
        fd = os.open(wrapper, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(script)
        except Exception:
            os.close(fd)
            raise

    def _write_glib_tool_wrappers(self):
        """为 conan glib 包内工具生成 wrapper（gnumeric 已合入先例，全量照搬）。

        - ELF 工具（glib-compile-resources/glib-compile-schemas/gdbus）：运行需要
          conan glib 包的共享库 → wrapper 设 LD_LIBRARY_PATH 指向 glib 包 lib，
          避免与 cmd-pkgs GTK 栈 / system 的库混用（固化绝对路径会 Segfault）。
        - python 脚本工具（glib-genmarshal/gdbus-codegen）：构建环境
          LD_LIBRARY_PATH 含 GTK_PREFIX/lib/external（libintl.so.8 与 python3.12
          不兼容）→ wrapper unset LD_LIBRARY_PATH 再 exec python3.
        工具一律取 conan glib 包（recipe 依赖保证存在）。"""
        dep = self.dependencies.get("glib")
        if dep is None or dep.package_folder is None:
            self.output.warning("glib dependency not available; skipping wrappers")
            return
        glib_folder = dep.package_folder
        glib_bin = os.path.join(glib_folder, "bin")
        glib_lib = os.path.join(glib_folder, "lib")
        tools_dir = os.path.join(self.build_folder, "_glib_tools")
        os.makedirs(tools_dir, exist_ok=True)
        python = "/data/service/hnp/python.org/python_3.12/bin/python3.12"
        for tool in ("glib-compile-resources", "glib-compile-schemas", "gdbus"):
            real = os.path.join(glib_bin, tool)
            if not os.path.isfile(real):
                self.output.warning("glib tool missing: {}".format(real))
                continue
            wrapper = os.path.join(tools_dir, tool)
            script = (
                "#!/bin/sh\n"
                "export LD_LIBRARY_PATH=\"{glib_lib}\"${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\n"
                "exec \"{real}\" \"$@\"\n"
            ).format(glib_lib=glib_lib, real=real)
            self._write_wrapper(wrapper, script)
            self.output.info("Wrote {} wrapper -> {}".format(tool, real))
        if os.path.isfile(python):
            for tool in ("glib-genmarshal", "gdbus-codegen"):
                real = os.path.join(glib_bin, tool)
                if not os.path.isfile(real):
                    self.output.warning("glib tool missing: {}".format(real))
                    continue
                wrapper = os.path.join(tools_dir, tool)
                script = (
                    "#!/bin/sh\n"
                    "unset LD_LIBRARY_PATH\n"
                    "exec {python} {real} \"$@\"\n"
                ).format(python=python, real=real)
                self._write_wrapper(wrapper, script)
                self.output.info("Wrote {} wrapper -> {}".format(tool, real))
        else:
            self.output.warning("python3.12 not found; glib python tool wrappers skipped")
            return
        # PATH 前置 _glib_tools（ELF 工具 wrapper 优先于 GTK_PREFIX/bin 的同名工具）
        # 注：os 已在模块顶部 import，方法内不得再 import（会把 os 变为局部变量
        # 导致前面 os.path.join 处 UnboundLocalError）
        os.environ["PATH"] = os.pathsep.join(list(dict.fromkeys(
            [tools_dir] + ([os.environ.get("PATH", "")] if os.environ.get("PATH") else []))))

    def build(self):
        self._ensure_gtk_stack()
        self._write_intltool_shim()
        # 注：glib 工具 wrapper 在 generate() 生成并经 tc.environment() 注入
        # PATH（build() 内 os.environ 会被 conanbuild 环境覆盖，CI #37607 实证）
        apply_conandata_patches(self)
        self._fix_la_files()
        # 环境注入（libgsf/libqalculate 已验证：build() 内 os.environ 直接注入
        # 生效——bogofilter/libgsf 先例。仅 PATH 需走 tc.environment()（profile
        # [buildenv] PATH=+ 会覆盖 build() 内 os.environ 的 PATH，见 generate()）。
        # PKG_CONFIG_PATH：cmd-pkgs GTK 栈 .pc + conan 依赖 .pc
        _pkg_dirs = [os.path.join(GTK_PREFIX, "lib", "pkgconfig")]
        for _ref, _dep in self.dependencies.items():
            for _lp in (_dep.cpp_info.libdirs or []):
                if os.path.isabs(_lp):
                    _pkg_dirs.append(os.path.join(_lp, "pkgconfig"))
        os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(_pkg_dirs)
        # LD_LIBRARY_PATH：SDK libc++（构建期工具运行时）→ GTK_PREFIX/lib
        # （cmd-pkgs 本地完整库：libintl.so.8 含 libintl_gettext 等符号，须在
        # /system 之前——CI worker /system/lib64 的 libintl.so.8 缺符号，msgmerge
        # 若命中系统坏库会 relocation 失败致 configure 报 "GNU gettext tools
        # not found"；本机 /system 无此库故回落本地完整版而通过）→ /system →
        # conan 依赖（顺序防 lld 被 conan libxml2 劫持；SDK 路径优先读
        # OHC_SDK_LLVM_LIB，W4 audit P3）
        sdk_llvm_lib = os.environ.get(
            "OHC_SDK_LLVM_LIB",
            "/data/service/hnp/ohos-sdk.org/"
            "ohos-sdk_26.0.0.18/ohos/native/llvm/lib")
        sdk_ohos_lib = os.path.join(sdk_llvm_lib, "aarch64-linux-ohos")
        _lib_dirs = [sdk_llvm_lib, sdk_ohos_lib]
        if GTK_PREFIX + "/lib" not in _lib_dirs \
           and os.path.isdir(os.path.join(GTK_PREFIX, "lib")):
            _lib_dirs.append(os.path.join(GTK_PREFIX, "lib"))
        for _sd in ("/system/lib64", "/system/lib"):
            if _sd not in _lib_dirs and os.path.isdir(_sd):
                _lib_dirs.append(_sd)
        for _ref, _dep in self.dependencies.items():
            for _lp in (_dep.cpp_info.libdirs or []):
                if os.path.isabs(_lp) and _lp not in _lib_dirs:
                    _lib_dirs.append(_lp)
        _prev = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            list(dict.fromkeys(_lib_dirs + ([_prev] if _prev else []))))
        self.output.info("PKG_CONFIG_PATH=" + os.environ["PKG_CONFIG_PATH"])
        self.output.info("LD_LIBRARY_PATH=" + os.environ["LD_LIBRARY_PATH"])
        autotools = Autotools(self)
        autotools.configure()
        # gdbus-codegen 裸命令经 PATH 命中 hnp 坏 shebang 版 -> 固化本地可用版
        self._fix_gdbus_codegen()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]