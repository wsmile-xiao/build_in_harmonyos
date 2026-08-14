#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for ATK — Accessibility Toolkit for GNOME.

HarmonyOS PC (aarch64) adaptation. Uses Meson build system.
"""

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps
import os

class AtkConan(ConanFile):
    name = "atk"
    version = "2.36.0"
    package_type = "library"
    license = "LGPL-2.1-or-later"
    homepage = "https://wiki.gnome.org/Projects/ATK"
    url = "https://wiki.gnome.org/Projects/ATK"
    description = "ATK is a toolkit for developing accessibility support."
    topics = ("accessibility", "gnome")

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def requirements(self):
        # 仓库已上架 glib/2.84.0（2.88.0 未上架），降版到 2.84.0 避免 Conan 解析失败
        self.requires("glib/2.84.0")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # CI 真根因: Conan 2.29 apply_conandata_patches 补丁路径解析炸（source_folder/export_sources_folder 歧义）
        # + Conan 锁旧 hash es/patches 旧版补丁头 → 反复多轮 patch 头格式改都炸
        # → 最简方案: 绔补丁 0001 直接 shutil 写 intl-wrapper.c 文件（避 Conan patch 路径解析）
        # intl-wrapper.c: OHOS musl libintl.h 完全无 gettext/textdomain/bindtextdomain 声明
        # （只有 __USE_GNU_GETTEXT 宏）→ intl-wrapper.c 走这些全 implicit int 炸
        # → 改走 g_strdup/字符串兜底避 gettext 依赖（g_libintl_* 返 g_strdup(msgid) 避 int 转换）
        intl_wrapper = os.path.join(self.source_folder, "atk", "intl-wrapper.c")
        with open(intl_wrapper, "w") as f:
            f.write("""/* Wrapper: g_libintl_* 转型避 OHOS musl libintl.h 无 gettext 声明 + 避 g_strdup 内存泄漏（aireview P2） */
#include <glib.h>
char *g_libintl_gettext(const char *msgid) { return (char *)(msgid); }
char *g_libintl_dgettext(const char *d, const char *m) { (void)d; return (char *)(m); }
char *g_libintl_dcgettext(const char *d, const char *m, int c) { (void)d; (void)c; return (char *)(m); }
char *g_libintl_ngettext(const char *m1, const char *m2, unsigned long n) { return (char *)((n==1)?m1:m2); }
char *g_libintl_dngettext(const char *d, const char *m1, const char *m2, unsigned long n) { (void)d; return (char *)((n==1)?m1:m2); }
char *g_libintl_dcngettext(const char *d, const char *m1, const char *m2, unsigned long n, int c) { (void)d; (void)c; return (char *)((n==1)?m1:m2); }
char *g_libintl_textdomain(const char *d) { return (char *)(d); }
char *g_libintl_bindtextdomain(const char *d, const char *dir) { (void)dir; return (char *)(d); }
char *g_libintl_bind_textdomain_codeset(const char *d, const char *cs) { (void)d; return (char *)(cs); }
""")
        # 补丁 0002/0003 走 patch() 应用（meson.build 改动是真 patch 真改非新建文件）
        patches = self.conan_data.get("patches", {}).get(str(self.version), []) if self.conan_data else []
        from conan.tools.files import patch as _patch
        import glob as _glob2
        for entry in patches:
            pf = entry.get("patch_file")
            if not pf:  # 0001 声明已从 conandata.yml 删（shutil 直接写），无需跳过守卫
                continue
            # glob 全 cache 找补丁 basename 避路径推算炸
            patch_basename = os.path.basename(pf)
            cache_root = os.path.dirname(os.path.dirname(self.source_folder))
            candidates = _glob2.glob(os.path.join(cache_root, "**", patch_basename), recursive=True)
            candidates += _glob2.glob(os.path.join(self.recipe_folder, "**", patch_basename), recursive=True)
            found = None
            for candidate in candidates:
                if candidate and os.path.exists(candidate):
                    kwargs = {k: v for k, v in entry.items() if k != "patch_file"}
                    try:
                        _patch(self, patch_file=candidate, **kwargs)
                        found = candidate
                        break
                    except ConanException:
                        continue
            if not found:
                raise ConanException(f"patch file not found: {pf}")

    def export_sources(self):
        # Conan 2.x export_conandata_patches 真管理补丁 export（避手写 copy() 路径歧义）
        export_conandata_patches(self)

    def generate(self):
        tc = MesonToolchain(self)
        # OHOS: disable introspection to avoid build failures
        # meson 1.11 要 true/false 非 disabled（disabled 非 boolean 致 configure 炸）
        tc.project_options["introspection"] = "false"
        # glib 2.84.0 已通过 Conan 可用，禁用 meson fallback 克隆行为
        tc.project_options["wrap_mode"] = "nofallback"
        # aireview P2: default_library 根据 shared 选项动态设（硬编码 static 致 shared=True 时产物仍 static 死选项）
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # CI 真根因: atk 源码真用 dgettext(domain, msgid)/dcgettext(domain, msgid, cat) 但 OHOS musl
        # libintl.h 完全无 gettext 声明（只有 __USE_GNU_GETTEXT 宏）→ implicit int 致 clang -Wint-conversion 炸
        # → 用 Conan conf tools.build:cflags 注入宏（list 格式，MesonToolchain c_args 从此渲染）
        # musl 单域 domain 忽略，dgettext/dcgettext 走返 msgid 的宏避 int→pointer 转换错（g_strdup 参数数不对）
        # 用 my_dgettext/my_dcgettext 静态inline兜底返 (gchar*)msgid 避宏参数数错
        self.conf.define("tools.build:cflags", [
            "-Ddgettext(a,b)=((char*)(b))",   # musl 单域，domain 忽略，返 msgid 避 int 转换
            "-Ddcgettext(a,b,c)=((char*)(b))",  # 同上，category 忽略
        ])
        # CI 真根因: meson 找 static linker 走 llvm-ar-15/llvm-ar/ar/gar guess 链全缺炸
        # OHOS 工具链 llvm-ar 在 /data/service/hnp/bin/llvm-ar（无 -15 后缀）
        # Conan 生成的 native file [binaries] 段只注入 c/cpp 无 ar → tc.generate() 后手动追加 ar 行
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        # aireview P3: 避硬编码路径脆弱性 — compilers.get 拿 Conan 解析的 ar，fallback shutil.which 解析绝对路径
        import shutil as _shutil
        ar = compilers.get("archive") or _shutil.which("llvm-ar") or "/data/service/hnp/bin/llvm-ar"
        tc.generate()
        # 手动追加 ar 到 Conan 生成的 meson native file [binaries] 段（避 meson guess linker 炸）
        # aireview P3: 硬编码 clang++ 路径脆弱 → 动态拿 compilers.get("cpp") 匹配真 cpp 行
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if os.path.exists(native_file):
            with open(native_file, "r") as _nf:
                content = _nf.read()
            if "ar = " not in content:
                # 动态匹配真 cpp 行（避硬编码 /data/service/hnp/bin/clang++ 路径脆弱性）
                import re as _re
                content_new, n = _re.subn(
                    r"(cpp = '[^']*')",
                    rf"\1\nar = '{ar}'",
                    content,
                    count=1,
                )
                if n:
                    with open(native_file, "w") as _nf:
                        _nf.write(content_new)
        # P2: PkgConfigDeps 让 atk configure 通过 pkg-config 找到 glib
        pkg = PkgConfigDeps(self)
        pkg.generate()
        # CI 真根因: PkgConfigDeps 只生成 glib-2.0.pc（主包名）非 gobject-2.0.pc（子模块），
        # meson dependency('gobject-2.0') 找不到 → 需补 glib 包的 lib/pkgconfig 路径
        # glib 包真含 gobject-2.0.pc/gio-2.0.pc/gmodule-2.0.pc 等子模块 .pc 在 lib/pkgconfig/
        # Conan PkgConfigDeps 生成 env 时 PKG_CONFIG_PATH 含 glib 包路径但 meson 走 native file 不读 env
        # → 手动复制 glib 包的子模块 .pc（gobject/gio/gmodule 等，非主 glib-2.0.pc）到 generators folder
        # CI 真根因2: Conan 生成的 glib-2.0.pc 缺 variables 段（glib_mkenums/gobject_query 等），
        # atk/meson.build glib_dep.get_variable() 取这些炸 → 补 glib_mkenums 等变量到 Conan 生成版
        glib_pkg = self.dependencies["glib"]
        glib_pkgconfig = os.path.join(glib_pkg.package_folder, "lib", "pkgconfig")
        if os.path.isdir(glib_pkgconfig):
            import shutil as _sh2, glob as _glob3
            # 只复制子模块 .pc（gobject/gio/gmodule 等），保留 Conan 生成版主 glib-2.0.pc（pcre2 包名匹配）
            for pc in _glob3.glob(os.path.join(glib_pkgconfig, "*.pc")):
                if os.path.basename(pc) == "glib-2.0.pc":
                    continue  # 跳过主包名（用 Conan 生成版避 Requires libpcre2-8 包名不匹配）
                dst_pc = os.path.join(self.generators_folder, os.path.basename(pc))
                if not os.path.exists(dst_pc):
                    _sh2.copy2(pc, dst_pc)
            # 补 variables 段到 Conan 生成版 glib-2.0.pc（避 atk/meson.build get_variable 炸）
            conan_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
            if os.path.exists(conan_pc):
                with open(conan_pc, "r") as _cpf:
                    pc_content = _cpf.read()
                if "glib_mkenums" not in pc_content:
                    # 在 Name: 段前插入 variables 段（atk/meson.build 真用 glib_mkenums/glib_genmarshal）
                    variables_block = (
                        "glib_genmarshal=${bindir}/glib-genmarshal\n"
                        "gobject_query=${bindir}/gobject-query\n"
                        "glib_mkenums=${bindir}/glib-mkenums\n"
                    )
                    pc_content = pc_content.replace("Name: glib-2.0", variables_block + "Name: glib-2.0")
                    with open(conan_pc, "w") as _cpf:
                        _cpf.write(pc_content)

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["atk-1.0"]
        self.cpp_info.includedirs = ["include/atk-1.0"]
        self.cpp_info.set_property("pkg_config_name", "atk")
        # P1: 传播 glib 依赖给消费者，否则编译/链接必然失败
        # glib 包 cpp_info 只声明主 glib-2.0（无 cmake_target_components 组件名）→
        # 用 glib::glib 单名避 glib::gobject-2.0 组件未找到致 CMakeDeps 炸（glib 把 gobject 合入主 libs）
        self.cpp_info.requires = ["glib::glib"]
