#!/usr/bin/env python3
"""Conan recipe — libsoup3 3.6.5-r3 (Meson).

libsoup3 3.6.5-r3 修复发布形态：r2 已发布二进制把 gobject 静态内嵌进
libsoup-3.0.so.0（NEEDED 无 libgobject-2.0.so.0，自带 g_type_register_fundamental
强定义），与 gtk4/4.22.4 链接的共享 glib/2.84.0.1.1（NEEDED libgobject-2.0.so.0）
在同时加载的进程中造成双 GObject 类型系统冲突（cannot register existing type
'gchar'，SIGABRT）。本版本声明 glib/2.84.0.1.1（shared）依赖（对齐 gtk4 链
r85/r86 硬约束），使 libsoup-3.0.so.0 链接共享 libgobject-2.0.so.0，消除静态
内嵌 gobject 副本。
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain


class Libsoup3Conan(ConanFile):
    name = "libsoup3"
    version = "3.6.5-r3"
    description = "libsoup3 3.6.5-r3 (shared glib release form fix)"
    license = "MIT"
    homepage = "https://gitlab.gnome.org/GNOME/libsoup"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libsoup meson dependency() names → conan package names:
        #   glib-2.0/gobject-2.0/gmodule-no-export-2.0/gio-2.0/gio-unix-2.0
        #   → glib/2.84.0.1.1 (pkg-config glib-2.0/gobject-2.0/gio-2.0/
        #   gmodule-2.0 components; the package also ships gmodule-no-export-2.0.pc
        #   and gio-unix-2.0.pc, copied into the pc-fix dir below).
        #   ⚠️ 必须共享 glib：gtk4/4.22.4 链接共享 glib/2.84.0.1.1（NEEDED
        #   libgobject-2.0.so.0）。r2 用静态内嵌 gobject 导致双 GObject 类型系统
        #   冲突（libshumate 16 上游测试 0/16）。本版本强制 shared=True 与 gtk4
        #   链共用同一共享 glib。
        self.requires("glib/2.84.0.1.1", options={"shared": True},
                      transitive_headers=True, transitive_libs=True)
        # libsoup's meson requires libpsl >= 0.20 via pkg-config (meson.build
        # line 159-161). Consume the published conan libpsl (PkgConfigDeps
        # generates libpsl.pc).
        self.requires("libpsl/0.21.5.1")
        # libsoup meson also needs libnghttp2 (dependency('libnghttp2'),
        # meson.build:118) and sqlite3 (dependency('sqlite3', required:false)
        # with a find_library fallback, meson.build:123-132). Consume the
        # published conan packages for both (PkgConfigDeps generates
        # libnghttp2.pc; sqlite3.pc uses the default package-name naming).
        self.requires("libnghttp2/1.70.0")
        self.requires("sqlite3/3.49.1")
        # brotli-decompressor-test 恢复（源码测试入口恢复规则）：ohpcd registry
        # 已有 brotli/1.2.0.1（revision 79807221，shared），meson 探测
        # dependency('libbrotlidec') 命中后注册 brotli-decompressor 测试
        # （3 注册点），不能沿用"brotli 禁用"的旧排除结论。
        self.requires("brotli/1.2.0.1")
        # glib/2.84.0.1.1 already pins zlib/1.3.1.1 in its own requirements;
        # no zlib override is needed (unlike the r1 recipe, which had to
        # fight glib2/2.88.0's zlib/1.3.1 pin).

    def layout(self):
        # meson_layout was removed in conan 2.29.x; replicate its folders here
        self.folders.build = "builddir"
        self.folders.generators = "builddir/generators"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # The CI worker exports AR/AS/STRIP/NM/RANLIB as llvm-* names (llvm-ar,
        # ...) that are NOT on its PATH — only the GNU binutils and ld.lld exist.
        # meson probes these and aborts at configure; pin the real tools by
        # ABSOLUTE PATH (resolved from PATH) and drop the broken env values.
        # (same fix as glib/2.84.0.1.1 recipe)
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(f"Required build tools not in PATH: {', '.join(missing)}")
        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        # ⚠️ 绝不可 strip 共享库：OHOS loader 校验 .codesign 段内嵌哈希与文件内容
        # 是否一致，strip 会改写 .so 内容导致哈希失配，dlopen 报 Permission
        # denied（本地实验铁证：libbar.so strip 前 dlopen OK，strip 后
        # Permission denied；libsoup 构建产物带 strip 即无法加载）。libsoup3
        # 是 shared 库，test/下游必须 dlopen 它，因此禁用 strip。
        tc.strip = None
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # boolean options -> "false"
        for opt in ("tests", "installed_tests", "doc_tests"):
            tc.project_options[opt] = "false"
        # glib-networking (TLS backend) is not packaged on OHOS; libsoup meson
        # asserts at configure when tls_check is enabled, so disable the
        # compile-time check (TLS is a runtime dependency, not needed to build).
        tc.project_options["tls_check"] = "false"
        # feature options -> "disabled"
        for opt in ("vapi", "introspection", "docs", "gssapi", "ntlm",
                    "sysprof", "fuzzing", "autobahn", "pkcs11_tests"):
            tc.project_options[opt] = "disabled"
        # ⚠️ brotli 恢复（R08 测试迁移补丁）：上游 brotli-decompressor-test
        # （3 注册点）因 brotli 禁用未实例化；ohpcd 已有 brotli/1.2.0.1
        # （shared），恢复为 enabled 使 meson dependency('libbrotlidec') 命中并
        # 注册该测试入口（不能沿用旧排除结论）。
        tc.project_options["brotli"] = "enabled"
        # meson needs the real .pc files (gio/gmodule-no-export-2.0/... +
        # gio-unix-2.0) from the glib package: PkgConfigDeps generates
        # glib-2.0.pc/gobject-2.0.pc/gio-2.0.pc/gmodule-2.0.pc/gthread-2.0.pc,
        # but libsoup also probes gmodule-no-export-2.0 and gio-unix-2.0,
        # which only exist inside the glib package's own lib/pkgconfig.
        extra_pc = []
        if self.dependencies.get("glib"):
            glib_pkg = self.dependencies["glib"].package_folder
            extra_pc.append(os.path.join(glib_pkg, "lib", "pkgconfig"))
            # Defensive prefix fix (same as r1): if the glib package .pc files
            # were installed with --prefix=/ their Cflags/Libs resolve to /include,
            # /lib (broken). Copy them and fix prefix to the real package folder;
            # prepend so meson prefers these over the PkgConfigDeps stubs for the
            # extra probe names (gmodule-no-export-2.0.pc, gio-unix-2.0.pc).
            pc_fix_dir = os.path.join(self.build_folder, "glib-pc-fix")
            os.makedirs(pc_fix_dir, exist_ok=True)
            for pc in os.listdir(os.path.join(glib_pkg, "lib", "pkgconfig")):
                if not pc.endswith(".pc"):
                    continue
                src = os.path.join(glib_pkg, "lib", "pkgconfig", pc)
                dst = os.path.join(pc_fix_dir, pc)
                with open(src, "r", encoding="utf-8") as fh:
                    text = fh.read()
                text = re.sub(r"^prefix=.*$", f"prefix={glib_pkg}", text, count=1, flags=re.M)
                with open(dst, "w", encoding="utf-8") as fh:
                    fh.write(text)
            extra_pc.insert(0, pc_fix_dir)
            # ⚠️ 关键修复：PkgConfigDeps 生成的 glib-2.0.pc 的 Libs 只有
            # -lglib-2.0 -lm -lpthread -ldl，缺 -lintl；libsoup 的 soup-init.c
            # 经 glib i18n 宏直接引用 g_libintl_bindtextdomain/g_libintl_gettext
            # （glib 包的 libintl.so.8 提供 T 符号，官方 glib-2.0.pc 的 Libs 含
            # -lintl），链接 libsoup-3.0.so.0 时 ld.lld 报 undefined symbol:
            # g_libintl_bindtextdomain（-Wl,--no-undefined 开启必现）。用官方
            # glib-2.0.pc（修正 prefix）覆盖 generators 的同名文件，保证 meson
            # 解析到带 -lintl 的真实 Libs 行（gtk4 配方同机制）。
            _official = os.path.join(glib_pkg, "lib", "pkgconfig", "glib-2.0.pc")
            if os.path.isfile(_official):
                with open(_official, "r", encoding="utf-8") as _fh:
                    _text = _fh.read()
                _text = re.sub(r"^prefix=.*$", f"prefix={glib_pkg}", _text, count=1, flags=re.M)
                # 官方 .pc 的 Requires.private 引用 libpcre2-8/zlib 等 glib 的
                # 传递依赖，其 .pc 不在 libsoup3 的 PkgConfigDeps 输出里；
                # pkg-config 解析 Requires.private 缺包即报
                # "Package libpcre2-8 ... not found"（共享库链接不需要
                # Requires.private —— pcre2/zlib 由 libglib-2.0.so 的 NEEDED
                # 运行时传递，链接期只有 Libs 行参与）。
                _text = re.sub(r"^Requires\.private:.*$", "", _text, count=1, flags=re.M)
                with open(os.path.join(self.generators_folder, "glib-2.0.pc"), "w", encoding="utf-8") as _fh:
                    _fh.write(_text)
                self.output.info("glib-2.0.pc: overridden with official package .pc (adds -lintl)")
            # glib package bin holds the meson gnome module tools
            # (glib-mkenums, glib-genmarshal, gdbus-codegen, ...) as python3
            # scripts; pin them in the meson native file [binaries] section so
            # gnome.mkenums()/gdbus_codegen() resolve them without pkg-config
            # variable fallback (the conan-generated glib-2.0.pc has none).
            glib_bin = os.path.join(glib_pkg, "bin")
            if os.path.isdir(glib_bin):
                self.buildenv_info.prepend_path("PATH", glib_bin)
                for tool in ("glib-mkenums", "glib-genmarshal", "gdbus-codegen",
                             "glib-compile-resources", "glib-compile-schemas",
                             "gio-querymodules"):
                    tool_path = os.path.join(glib_bin, tool)
                    if os.path.isfile(tool_path):
                        tc.binaries[tool] = tool_path
        tc.pkg_config_path = os.pathsep.join([tc.pkg_config_path] + extra_pc)
        # ⚠️ brotli pc 注入（R08 测试迁移补丁）：brotli/1.2.0.1 配方的
        # pkg_config_name 取自包内第一个 .pc stem（libbrotlicommon），
        # PkgConfigDeps 只生成 libbrotlicommon.pc；而 libsoup meson 探测
        # dependency('libbrotlidec')（meson.build:137）。把 brotli 包内真实
        # libbrotlidec.pc 复制进 pc-fix 目录并修正 prefix，保证 meson 命中。
        brotli = self.dependencies.get("brotli")
        if brotli and brotli.package_folder:
            _brotli_pc_dir = os.path.join(brotli.package_folder, "lib", "pkgconfig")
            _brotli_fix = os.path.join(self.build_folder, "brotli-pc-fix")
            os.makedirs(_brotli_fix, exist_ok=True)
            for _pc in ("libbrotlidec.pc", "libbrotlienc.pc", "libbrotlicommon.pc"):
                _src = os.path.join(_brotli_pc_dir, _pc)
                if not os.path.isfile(_src):
                    continue
                with open(_src, "r", encoding="utf-8") as _fh:
                    _text = _fh.read()
                _text = re.sub(r"^prefix=.*$", f"prefix={brotli.package_folder}", _text, count=1, flags=re.M)
                with open(os.path.join(_brotli_fix, _pc), "w", encoding="utf-8") as _fh:
                    _fh.write(_text)
            tc.pkg_config_path = os.pathsep.join([tc.pkg_config_path, _brotli_fix])
            self.output.info("brotli pc: copied real libbrotlidec.pc into pkg-config path")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        # ⚠️ meson install 会清理 DT_RUNPATH：把 .dynstr 中的 rpath 路径字符串
        # 用 'X' 覆盖并删除 DT_RUNPATH 条目。这改写了 .so 内容，使链接时写入的
        # .codesign 哈希失配，OHOS loader 校验失败 → dlopen 报 Permission denied
        # （本地铁证：builddir 原始产物 dlopen OK，meson.install() 后的包产物
        # Permission denied）。用 build 目录的原始链接产物覆盖被修改的 .so。
        for _lib in ("libsoup-3.0.so.0.7.4",):
            _src = os.path.join(self.build_folder, "libsoup", _lib)
            _dst = os.path.join(self.package_folder, "lib", _lib)
            if os.path.exists(_src):
                shutil.copy2(_src, _dst)

    def package_info(self):
        self.cpp_info.libs = ["soup-3.0"]
        self.cpp_info.includedirs = ["include/libsoup-3.0"]
        self.cpp_info.system_libs = ["m", "pthread", "dl"]
        # libsoup3 public headers include glib/gio/gobject headers; CMakeDeps
        # generates empty data for the TRANSITIVE glib dep (conan 2.29), so
        # expose glib's include dirs + libs here to let consumers compile/link.
        # ⚠️ package_folder 可能为 None（共享 glib 作为传递依赖被 Skipped
        # binaries，或 compute 阶段依赖尚未下载），此时跳过——test_package 已
        # 显式 requires glib 兜底，不在这里硬崩。
        glib = self.dependencies.get("glib")
        if glib and glib.package_folder:
            self.cpp_info.includedirs.append(os.path.join(glib.package_folder, "include"))
            self.cpp_info.includedirs.append(os.path.join(glib.package_folder, "include", "glib-2.0"))
            self.cpp_info.includedirs.append(os.path.join(glib.package_folder, "lib", "glib-2.0", "include"))
            self.cpp_info.libdirs.append(os.path.join(glib.package_folder, "lib"))
            for _lib in ("glib-2.0", "gobject-2.0", "gio-2.0", "gmodule-2.0",
                         "gthread-2.0"):
                if _lib not in self.cpp_info.libs:
                    self.cpp_info.libs.append(_lib)
            # runtime: shared libs are needed at test run time; glib has no
            # runenv_info of its own, so expose both lib dirs here.
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(glib.package_folder, "lib"))
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        # PkgConfigDeps picks up pkg_config_name; CMakeDeps (test_package) needs
        # cmake_file_name + cmake_target_name set explicitly (pkg_config_name
        # does NOT influence CMakeDeps in conan 2).
        self.cpp_info.set_property("pkg_config_name", "libsoup-3.0")
        self.cpp_info.set_property("cmake_file_name", "libsoup-3.0")
        self.cpp_info.set_property("cmake_target_name", "libsoup-3.0::libsoup-3.0")
