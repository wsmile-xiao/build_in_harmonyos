#!/usr/bin/env python3
"""Conan recipe — appstream 1.2.0（AppStream 元数据解析/校验库，Meson 构建）

appstream 提供 libappstream（C 库）与 appstreamcli/ascli 命令行工具。
构建系统：Meson（meson.build，meson>=0.62，c_std=gnu17）。
上游：https://github.com/ximion/appstream
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class AppstreamConan(ConanFile):
    name = "appstream"
    version = "1.2.0"
    description = "AppStream — 软件元数据规范与工具库（libappstream + appstreamcli）"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.freedesktop.org/wiki/Distributions/AppStream/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    # PkgConfigDeps 为每个依赖生成 .pc（glib 家族经下方 pc-fix 副本解析，见 generate()）
    # PkgConfigDeps 由 generate() 手动调用（须先注入 glib 无后缀组件别名，
    # 否则类级 generators 先于 generate() 运行导致别名失效）
    generators = []

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R04 发现：pango 配方 package_info 引用 glib::glib-2.0/gobject-2.0 等组件
        # （针对 glib/2.84.0.1 组件键编写），glib/2.88.3 组件键为 glib/gobject/gio，
        # 2.88.3 链下 pango 的 PkgConfigDeps 必然报 "Component 'glib::glib-2.0'
        # not found"（create09 实测首错）。因此 compose 链必须走 ohpcd 预编译绑定
        # 的 glib/2.84.0.1 + pcre2/10.45 + zlib/1.3.1.1 + libffi/3.4.4 旧链：
        # pango/harfbuzz/cairo/freetype/fontconfig/blake3 命中预编译免重编；
        # 主链 libxmlb（精确 require glib/2.88.3）在旧链下需重编，链接静态 glib
        # 缺 zlib/libffi 符号问题在 generate() 中以 conf 注入链接参数解决。
        # 主链 glib 亦为 compose 链共享版本；force=True 强制全图版本并保留
        # direct requirement 语义（override=True 会被 cpp_info 组件 requires 校验
        # 排除报 "not a direct requirement"；force 不排除，实测 G2 干净构建
        # 在 force 下 package_info 通过且 libxmlb 的 glib/2.88.3 被强制为 2.84.0.1）
        self.requires("glib/2.84.0.1", force=True)
        self.requires("pcre2/10.45", override=True)
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("libffi/3.4.4", override=True)
        self.requires("libcurl/8.5.0")
        self.requires("libxml2/2.15.3.1")
        self.requires("libfyaml/0.9.6")
        self.requires("libstemmer/3.1.1")
        # compose 门控依赖链（R04：as-test_compose / as-test_compose-worker /
        # as-validate_metainfo.compose 必须纳入，14/14 硬门禁）
        self.requires("blake3/1.8.3.1")
        self.requires("cairo/1.18.4")
        self.requires("freetype/2.14.3")
        self.requires("pango/1.50.14")
        # pango 配方 force fontconfig/2.18.1.1（其 fontconfig 链），统一避免冲突
        self.requires("fontconfig/2.18.1.1")
        # R05：提升到 vips/8.18.4.1（ohpcd 制品仓 2026-09-16 已发布，启用 PNG/JPEG
        # loader，libjpeg-turbo/3.2.0 + libpng/1.6.58 + zlib/1.3.1.1）；8.18.4 全特性
        # 禁用导致 compose/mediaworker asw_image_backend_init 无法通过 PNG 硬性检查
        self.requires("vips/8.18.4.1")
        self.requires("zstd/1.5.7.1")
        # xmlb/libxmlb(>=0.3.14) 为 meson 必需依赖；需在旧链下重编
        self.requires("libxmlb/0.3.19")

    def build_requirements(self):
        # qt 门控（as-test_qt-pool / as-test_qt-misc）：Qt6 仅供本库测试目标链接，
        # 不进 appstream 库/组件的运行时依赖 → 用 test_requires（构建期依赖，
        # package_info 无需组件引用；qtbase 提供 Qt6Core/Qt6Test 与工具链）
        self.test_requires("qtbase/6.11.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # OHOS worker 导出 AR/AS/STRIP/NM/RANLIB 为 llvm-* 裸名且不在 PATH（posix_spawn 不搜索
        # PATH），meson 探测 archiver 时 `llvm-ar --version` 必失败；先剔除坏值再按绝对路径固定
        # （libxmlb/glib-networking 先例）。
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {
            name: shutil.which(name)
            for name in ("ar", "as", "strip", "nm", "ranlib")
        }
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}"
            )
        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = None
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        if not self.options.shared:
            tc.project_options["default_library"] = "static"
        tc.project_options["stemming"] = "true"
        tc.project_options["systemd"] = "false"
        tc.project_options["gir"] = "false"
        tc.project_options["man"] = "false"
        tc.project_options["docs"] = "true"
        tc.project_options["apidocs"] = "false"
        tc.project_options["qt"] = "true"
        tc.project_options["compose"] = "true"
        tc.project_options["blake3-support"] = "true"
        tc.project_options["vapi"] = "false"
        tc.project_options["apt-support"] = "false"
        tc.project_options["display-detection"] = "none"
        # OHOS 无 bash-completion 依赖包（pkg-config 不存在），且命令补全非运行必需
        tc.project_options["bash-completion"] = "false"

        # PkgConfigDeps 手动调用：类级 generators 会先于本 generate() 运行导致
        # glib 无后缀组件别名注入失效；必须在 glib 别名注入之后、libblake3.pc
        # 转发之前生成 .pc（转发块依赖已生成的 blake3.pc；libxmlb 等依赖组件
        # requires 引用 glib::gobject 旧名，见下方别名注入）。
        glib_dep = self.dependencies["glib"]
        # libxmlb 配方组件 requires 引用 glib::glib/gobject/gio/gmodule（无 -2.0 后缀，
        # 针对 glib/2.88.3 组件键编写），而 compose 链所需的 glib/2.84.0.1 组件键为
        # glib-2.0/gobject-2.0/gio-2.0/gmodule-2.0 → 为 glib 依赖 cpp_info 补无后缀
        # 别名键（指向同一组件对象），使 PkgConfigDeps 解析 libxmlb 引用时不报错。
        for _suffix, _plain in (
            ("glib-2.0", "glib"),
            ("gobject-2.0", "gobject"),
            ("gio-2.0", "gio"),
            ("gmodule-2.0", "gmodule"),
        ):
            if _suffix in glib_dep.cpp_info.components and _plain not in glib_dep.cpp_info.components:
                glib_dep.cpp_info.components[_plain] = glib_dep.cpp_info.components[_suffix]
        from conan.tools.gnu import PkgConfigDeps
        PkgConfigDeps(self).generate()

        # libblake3.pc 转发：上游 compose/meson.build 用 dependency('libblake3')，
        # 而 blake3 配方 package_info 无 pkg_config_name（PkgConfigDeps 只生成
        # blake3.pc）→ 在 generators 目录补转发型 .pc（E348 转发 pc 先例）。
        # 注意：PkgConfigDeps 需先于本块运行生成 blake3.pc（类级 generators 改为
        # 手动调用，见下方 PkgConfigDeps(self).generate()）。
        if os.path.isfile(os.path.join(self.generators_folder, "blake3.pc")) and \
           not os.path.isfile(os.path.join(self.generators_folder, "libblake3.pc")):
            with open(os.path.join(self.generators_folder, "libblake3.pc"), "w", encoding="utf-8") as _fh:
                _fh.write(
                    "Name: libblake3\n"
                    "Description: forwarding pc generated by appstream recipe (Requires blake3)\n"
                    "Version: 1.8.3\n"
                    "Requires: blake3\n"
                )

        # glib pc-fix（libxmlb 先例）：PkgConfigDeps 只对 package_info 声明的组件生成 .pc，
        # gio-unix-2.0.pc 只存在于 glib 包内 lib/pkgconfig；复制真实集合、重写 prefix
        # （glib 以 prefix=/ 安装）、剥离仅适用于静态内嵌的 Requires(.private)
        # （proxy-libintl/libpcre2-8/zlib/libffi），修正副本置于 PKG_CONFIG_PATH 最前。
        # （glib 无后缀别名组件已在 PkgConfigDeps 调用前注入，见上方。）
        extra_pc = []
        glib_pkg = glib_dep.package_folder
        # override=True 的 glib 依赖在部分干净解析（无 lockfile，如 conan-verify G2）
        # 下 package_folder 可能为 None；PkgConfigDeps 已生成 glib-2.0.pc（prefix 指向
        # 真实 glib 包目录），以此兜底解析 glib 包路径再补 gio-unix-2.0.pc 等副本。
        if not glib_pkg:
            _gp = self.generators_folder and os.path.join(self.generators_folder, "glib-2.0.pc")
            if _gp and os.path.isfile(_gp):
                with open(_gp, encoding="utf-8") as _fh:
                    for _ln in _fh:
                        if _ln.startswith("prefix="):
                            glib_pkg = _ln.strip().split("=", 1)[1]
                            break
        pc_fix_dir = os.path.join(self.build_folder, "glib-pc-fix")
        os.makedirs(pc_fix_dir, exist_ok=True)
        for pc in os.listdir(os.path.join(glib_pkg, "lib", "pkgconfig")):
            if not pc.endswith(".pc"):
                continue
            src = os.path.join(glib_pkg, "lib", "pkgconfig", pc)
            dst = os.path.join(pc_fix_dir, pc)
            with open(src, "r", encoding="utf-8") as fh:
                text = fh.read()
            text = re.sub(
                r"^prefix=.*$", f"prefix={glib_pkg}", text, count=1, flags=re.M
            )
            text = re.sub(
                r"^(Requires(?:\.private)?):\s*([^\n]*)$",
                lambda m: m.group(1) + ": "
                + re.sub(
                    r"\b(?:proxy-libintl|zlib|libpcre2-8|libffi)\b(?:\s*>=\s*[0-9.]+)?(?:\s*,\s*|\s*$)",
                    "",
                    m.group(2),
                ).strip().rstrip(",")
                if any(
                    t in m.group(2)
                    for t in ("proxy-libintl", "zlib", "libpcre2-8", "libffi")
                )
                else m.group(0),
                text,
                flags=re.M,
            )
            text = re.sub(
                r"^Requires\.private:\s*$", "Requires.private:", text, flags=re.M
            )
            with open(dst, "w", encoding="utf-8") as fh:
                fh.write(text)
        extra_pc.insert(0, pc_fix_dir)
        tc.pkg_config_path = os.pathsep.join(extra_pc + [tc.pkg_config_path])

        # glib-compile-resources / glib-mkenums 等 glib 包内 host 工具运行时需在
        # LD_LIBRARY_PATH 找到 libglib-2.0.so.0 等动态库，否则 ninja 生成 gresource
        # C 代码时 "Error loading shared library"。meson 在 configure 期已把工具解析
        # 为绝对路径（ninja 不再走 PATH），故不能只 prepend PATH；改为在机器文件
        # [binaries] 中把工具名映射到包装脚本（meson find_program 优先读机器文件），
        # 包装脚本先 export LD_LIBRARY_PATH 再 exec 原二进制（gtksourceview3 同思路）。
        #
        # R06 根治：glib 包内宿主 ELF（glib-compile-resources/glib-compile-schemas）
        # 在 CI 干净环境直接 exec 报 EPERM/code=126（未签名或 .codesign 失效）。
        # 在构建私有目录复制工具后先移除 .codesign 再用 OHOS binary-sign-tool 自签
        # （与 libcurl/cairo .so 同款流程：llvm-objcopy --remove-section .codesign
        # + binary-sign-tool sign -selfSign 1），wrapper 一律 exec 已签名副本。
        tools_dir = os.path.join(self.build_folder, "glib-tools")
        os.makedirs(tools_dir, exist_ok=True)
        for _tool in ("glib-compile-resources", "glib-mkenums"):
            _src = os.path.join(glib_pkg, "bin", _tool)
            if not os.path.isfile(_src):
                raise ConanInvalidConfiguration(f"GLib build tool missing: {_src}")
            _dst = os.path.join(tools_dir, _tool + ".bin")
            shutil.copy2(_src, _dst)
            # 仅对 ELF 工具签名（python 脚本无需 .codesign，签名工具对非 ELF 直接失败）
            _head = open(_dst, "rb").read(4)
            if _head == b"\x7fELF":
                import subprocess
                for _exe in ("llvm-objcopy", "binary-sign-tool"):
                    _p = shutil.which(_exe) or f"/data/service/hnp/bin/{_exe}"
                    if not os.path.isfile(_p):
                        raise ConanInvalidConfiguration(f"{_exe} not found for glib tool signing: {_p}")
                _objcopy, _signtool = (
                    shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy",
                    shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool",
                )
                subprocess.run(
                    [_objcopy, "--remove-section", ".codesign", _dst],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                _r = subprocess.run(
                    [_signtool, "sign", "-inFile", _dst, "-outFile", _dst, "-selfSign", "1"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                if _r.returncode != 0:
                    raise ConanInvalidConfiguration(
                        f"binary-sign-tool self-sign failed for {_tool}: {_r.stdout.strip()}"
                    )
            os.chmod(_dst, 0o755)
            _wrapper = os.path.join(tools_dir, _tool)
            with open(_wrapper, "w", encoding="utf-8") as _fh:
                _fh.write("#!/bin/sh\n")
                _fh.write(f"export LD_LIBRARY_PATH={glib_pkg}/lib:$LD_LIBRARY_PATH\n")
                _fh.write(f'exec "{_dst}" "$@"\n')
            os.chmod(_wrapper, 0o755)
            tc.binaries[_tool] = _wrapper
        self.buildenv_info.prepend_path("PATH", tools_dir)

        # stemmer 由上游用 cc.find_library('stemmer')/cc.has_header('libstemmer.h') 探测
        # （非 pkg-config），需显式补 -I/-L 指向 libstemmer 包目录
        stemmer_pkg = self.dependencies["libstemmer"].package_folder
        tc.extra_cflags.append(f"-I{os.path.join(stemmer_pkg, 'include')}")
        tc.extra_ldflags.append(f"-L{os.path.join(stemmer_pkg, 'lib')}")

        # R04 静态 glib 链（pango 强制 glib shared=False）下 libgobject-2.0.a 等
        # 需要 libffi 符号；干净构建（conan-verify G2 无 lockfile/conf 注入）时
        # glib pc-fix 剥离了 Requires.private 的 libffi → 可执行目标（appstreamcli/
        # asc-mediaworker）链接缺 ffi_type_void 等，此处补 -L/-lffi 兜底。
        # libffi 为 override=True 依赖（package_folder 可能为 None），静态 glib 包内
        # 自带 libffi.a（glib22586…/p/lib/libffi.a 实测存在），以其 lib 目录兜底。
        _ffi_pkg = self.dependencies["libffi"].package_folder if "libffi" in self.dependencies else None
        if not _ffi_pkg and glib_pkg and os.path.isfile(os.path.join(glib_pkg, "lib", "libffi.a")):
            _ffi_pkg = glib_pkg
        if _ffi_pkg:
            tc.extra_ldflags.append(f"-L{os.path.join(_ffi_pkg, 'lib')}")
            tc.extra_ldflags.append("-lffi")

        # compose/worker（asc-mediaworker）经 dependency('vips') 依赖 vips 头文件，
        # 但其 include 目录未随 vips.pc 正确传播到 asc-mediaworker 编译目标
        # （首错 asw-image-private.h: fatal error: 'vips/vips.h' file not found），
        # 全局补 -I 使 compose worker 目标也能解析 vips.h
        vips_pkg = self.dependencies["vips"].package_folder
        tc.extra_cflags.append(f"-I{os.path.join(vips_pkg, 'include')}")

        # 测试目标仅经 appstream_dep 拉入 as-yaml.h（其 include <libfyaml.h>），
        # 而 appstream_dep 不透传 fyaml include（上游假设系统默认路径装有头文件）；
        # 全局补 -I 使 tests/ 编译目标也能解析 libfyaml.h（与 stemmer 同款方案）
        fyaml_pkg = self.dependencies["libfyaml"].package_folder
        tc.extra_cflags.append(f"-I{os.path.join(fyaml_pkg, 'include')}")

        # gettext 声明（at-spi2-core 先例）：OHOS sysroot 的 libintl.h 空 stub 无
        # gettext/dgettext 声明；glib 包内 proxy libintl.h 把 gettext 映射到
        # g_libintl_*（链接期由 proxy-libintl 提供符号）。为保证 CI 可复现、
        # 不依赖任何本机缓存路径，直接在构建私有目录生成标准 proxy-libintl
        # 头（宏集与 glib proxy-libintl 一致），并前置 -I。
        proxy_intl_dir = os.path.join(self.build_folder, "proxy-libintl-include")
        os.makedirs(proxy_intl_dir, exist_ok=True)
        with open(os.path.join(proxy_intl_dir, "libintl.h"), "w", encoding="utf-8") as _fh:
            _fh.write(
                "/* Generated proxy-libintl header (gettext -> g_libintl_* macros, "
                "symbols provided by proxy-libintl at link time) */\n"
                "#ifndef _LIBINTL_H\n"
                "#define _LIBINTL_H 1\n"
                "#include <locale.h>\n"
                "#ifndef LC_MESSAGES\n"
                "# define LC_MESSAGES 1729\n"
                "#endif\n"
                "#ifndef __GNU_GETTEXT_SUPPORTED_REVISION\n"
                "# define __GNU_GETTEXT_SUPPORTED_REVISION\n"
                "#endif\n"
                "#define gettext g_libintl_gettext\n"
                "#define dgettext g_libintl_dgettext\n"
                "#define dcgettext g_libintl_dcgettext\n"
                "#define ngettext g_libintl_ngettext\n"
                "#define dngettext g_libintl_dngettext\n"
                "#define dcngettext g_libintl_dcngettext\n"
                "#define textdomain g_libintl_textdomain\n"
                "#define bindtextdomain g_libintl_bindtextdomain\n"
                "#define bind_textdomain_codeset g_libintl_bind_textdomain_codeset\n"
                "#define G_INTL_EXPORT extern\n"
                "#ifdef __cplusplus\n"
                "extern \"C\" {\n"
                "#endif\n"
                "G_INTL_EXPORT char *g_libintl_gettext (const char *msgid);\n"
                "G_INTL_EXPORT char *g_libintl_dgettext (const char *domainname, const char *msgid);\n"
                "G_INTL_EXPORT char *g_libintl_dcgettext (const char *domainname, const char *msgid, int category);\n"
                "G_INTL_EXPORT char *g_libintl_ngettext (const char *msgid1, const char *msgid2, unsigned long int n);\n"
                "G_INTL_EXPORT char *g_libintl_dngettext (const char *domainname, const char *msgid1, const char *msgid2, unsigned long int n);\n"
                "G_INTL_EXPORT char *g_libintl_dcngettext (const char *domainname, const char *msgid1, const char *msgid2, unsigned long int n, int category);\n"
                "G_INTL_EXPORT char *g_libintl_textdomain (const char *domainname);\n"
                "G_INTL_EXPORT char *g_libintl_bindtextdomain (const char *domainname, const char *dirname);\n"
                "G_INTL_EXPORT char *g_libintl_bind_textdomain_codeset (const char *domainname, const char *codeset);\n"
                "#ifdef __cplusplus\n"
                "}\n"
                "#endif\n"
                "#endif\n"
            )
        tc.extra_cflags.append(f"-I{proxy_intl_dir}")

        # PkgConfigDeps 手动调用：类级 generators 会先于本 generate() 运行导致
        # glib 无后缀组件别名注入失效；必须在注入之后、写 generators 之前生成
        # .pc（libxmlb 等依赖组件 requires 引用 glib::gobject 旧名，见上方别名注入）
        from conan.tools.gnu import PkgConfigDeps
        PkgConfigDeps(self).generate()

        # qt 门控工具链注入（as-test_qt-pool / as-test_qt-misc）：
        # qtbase 配方 cmake_find_mode=none（保留自身 Qt6Config.cmake），PkgConfigDeps
        # 不生成 qt6.pc；上游 qt/meson.build 用 dependency('qt6', modules: ['Core'])，
        # 需 qt6.pc 元包 + qmake6/moc/rcc 可执行（qtbase 装在 bin/ 与 libexec/）。
        qtbase_pkg = self.dependencies["qtbase"].package_folder
        qt_pc = os.path.join(self.generators_folder, "qt6.pc")
        with open(qt_pc, "w", encoding="utf-8") as _fh:
            _fh.write(
                "Name: qt6\n"
                "Description: forwarding pc generated by appstream recipe (Requires Qt6Core/Qt6Test)\n"
                "Version: 6.11.1\n"
                "Requires: Qt6Core Qt6Test\n"
            )
        # Qt6*.pc 真实文件在 qtbase 包内 lib/pkgconfig，但其 prefix 指向已清理的
        # conan 构建目录（b/.../p），meson qt6 模块会按该 prefix 找 moc/rcc 而失败；
        # 复制并重写 prefix 为已装包路径，置于 PKG_CONFIG_PATH 最前（glib pc-fix 同思路）。
        qtbase_pc_fix = os.path.join(self.build_folder, "qtbase-pc-fix")
        os.makedirs(qtbase_pc_fix, exist_ok=True)
        for _pc in os.listdir(os.path.join(qtbase_pkg, "lib", "pkgconfig")):
            if not _pc.endswith(".pc"):
                continue
            _src = os.path.join(qtbase_pkg, "lib", "pkgconfig", _pc)
            _dst = os.path.join(qtbase_pc_fix, _pc)
            with open(_src, "r", encoding="utf-8") as _fh:
                _text = _fh.read()
            _text = re.sub(
                r"^prefix=.*$", f"prefix={qtbase_pkg}", _text, count=1, flags=re.M
            )
            with open(_dst, "w", encoding="utf-8") as _fh:
                _fh.write(_text)
        # 真实 Qt6 工具在 qtbase bin/（qmake6）与 libexec/（moc/rcc/uic）
        for _d in ("bin", "libexec"):
            _p = os.path.join(qtbase_pkg, _d)
            if os.path.isdir(_p):
                self.buildenv_info.prepend_path("PATH", _p)
        tc.pkg_config_path = os.pathsep.join(
            [qtbase_pc_fix, tc.pkg_config_path]
        )
        # Qt6Core/Qt6Test 库目录显式加入链接搜索（组件 cmake 模式不生成 -L）
        tc.extra_ldflags.append(f"-L{os.path.join(qtbase_pkg, 'lib')}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        # 头文件安装在 include/appstream/（上游 meson 布局），消费者 `#include <appstream.h>`
        # 需要 -I.../include/appstream；默认 includedirs=["include"] 会导致 CMake consumer
        # 找不到头文件（test_package R34 实测首错），此处显式声明。
        # 采用 libxmlb 同款组件式声明：PkgConfigDeps 对根级 cpp_info.requires 的解析在
        # 组件式配方下才稳定（libxmlb 的 xmlb.pc Requires 生成正确、被 meson 正常消费），
        # 组件 requires 保证 appstream.pc 生成完整 Requires（glib 家族/gio-unix 经 glib
        # 组件、libcurl/libxmlb/libxml2/libfyaml/libstemmer/zstd），静态库消费者才能解析
        # 全部符号（fy_*/sb_* 实测首错）。
        self.cpp_info.set_property("cmake_file_name", "appstream")
        self.cpp_info.set_property("cmake_target_name", "appstream::appstream")
        self.cpp_info.set_property("pkg_config_name", "appstream")
        # appstreamcli CLI 装在 bin/（R38/L0k: commands.json 声明工具）
        self.cpp_info.bindirs = ["bin"]

        lib = self.cpp_info.components["appstream"]
        lib.includedirs = ["include/appstream"]
        lib.libs = ["appstream"]
        lib.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gio-2.0",
            "glib::gmodule-2.0",
            "blake3::blake3",
            "libcurl::libcurl",
            "libxml2::libxml2",
            "libxmlb::libxmlb",
            "libfyaml::libfyaml",
            "libstemmer::libstemmer",
            "zstd::zstd",
        ]
        lib.system_libs = ["m", "pthread"]
        lib.set_property("cmake_target_name", "appstream::appstream")
        lib.set_property("pkg_config_name", "appstream")

        # compose 库组件（R04 新增 libappstream-compose.a）：承载 compose 链 direct
        # 依赖引用（pango/cairo/freetype/fontconfig/vips/fribidi/expat 等），
        # 使 package_info 校验通过且 compose 消费者能获得完整链接依赖。
        comp = self.cpp_info.components["appstream-compose"]
        comp.includedirs = ["include/appstream"]
        comp.libs = ["appstream-compose"]
        comp.requires = [
            "appstream",
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gio-2.0",
            "glib::gmodule-2.0",
            "cairo::cairo",
            "freetype::freetype",
            "fontconfig::fontconfig",
            "pango::pango",
            "vips::vips",
            "blake3::blake3",
        ]
        comp.set_property("cmake_target_name", "appstream::appstream-compose")
        comp.set_property("pkg_config_name", "appstream-compose")
