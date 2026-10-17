#!/usr/bin/env python3
"""Conan recipe — libsoup3 3.6.5-r2 (Meson)."""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain


class Libsoup3Conan(ConanFile):
    name = "libsoup3"
    version = "3.6.5-r2"
    description = "libsoup3 3.6.5-r2"
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
        self.requires("glib2/2.88.0")
        # libsoup's meson requires libpsl >= 0.20 via pkg-config (meson.build
        # line 159-161). The CI worker's /usr/local has no libpsl (only
        # libnghttp2/sqlite3), so a system-dir fallback is not enough — consume
        # the published conan libpsl instead (PkgConfigDeps generates libpsl.pc).
        self.requires("libpsl/0.21.5.1")
        # libsoup meson also needs libnghttp2 (dependency('libnghttp2'),
        # meson.build:118) and sqlite3 (dependency('sqlite3', required:false)
        # with a find_library fallback, meson.build:123-132). Some CI workers
        # lack libnghttp2 in /usr/local, so consume the published conan
        # packages for both (PkgConfigDeps generates libnghttp2.pc/sqlite3.pc).
        self.requires("libnghttp2/1.70.0")
        self.requires("sqlite3/3.49.1")
        # glib2/*:shared=True forces a shared glib2 rebuild on CI (ohpcd only
        # publishes static glib2). That rebuild links zlib into libgio-2.0.so,
        # and the published zlib/1.3.1 libz.a is NOT -fPIC (R_AARCH64 relocation
        # failure). Override to the PIC variant zlib/1.3.1.1 (CFLAGS=-fPIC),
        # which is published on ohpcd, so the shared glib2 rebuild succeeds.
        self.requires("zlib/1.3.1.1", override=True)

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
        # (same fix as glib2/2.88.0 recipe)
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
        for opt in ("vapi", "introspection", "docs", "gssapi", "ntlm", "brotli",
                    "sysprof", "fuzzing", "autobahn", "pkcs11_tests"):
            tc.project_options[opt] = "disabled"
        # meson needs the real .pc files (gio/gmodule-no-export/...) from the
        # glib2 package (PkgConfigDeps only generates glib-2.0.pc), plus the
        # system /usr/local pc dir for the hard deps libpsl/libnghttp2.
        extra_pc = []
        if self.dependencies.get("glib2"):
            glib_pkg = self.dependencies["glib2"].package_folder
            extra_pc.append(os.path.join(glib_pkg, "lib", "pkgconfig"))
            # The glib2 package .pc files were installed with --prefix=/ so their
            # Cflags/Libs resolve to /include, /lib (broken). Copy them and fix
            # prefix to the real package folder; prepend so meson prefers these.
            pc_fix_dir = os.path.join(self.build_folder, "glib2-pc-fix")
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
            # glib2 package bin holds the meson gnome module tools
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
        extra_pc.append("/storage/Users/currentUser/usr/local/lib/pkgconfig")
        tc.pkg_config_path = os.pathsep.join([tc.pkg_config_path] + extra_pc)
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
        # generates empty data for the TRANSITIVE glib2 dep (conan 2.29), so
        # expose glib2's include dirs + libs here to let consumers compile/link.
        # ⚠️ package_folder 可能为 None（静态 glib2 作为传递依赖被 Skipped
        # binaries，或 compute 阶段依赖尚未下载），此时跳过——test_package 已
        # 显式 requires glib2 兜底，不在这里硬崩。
        glib2 = self.dependencies.get("glib2")
        if glib2 and glib2.package_folder:
            self.cpp_info.includedirs.append(os.path.join(glib2.package_folder, "include"))
            self.cpp_info.includedirs.append(os.path.join(glib2.package_folder, "include", "glib-2.0"))
            self.cpp_info.includedirs.append(os.path.join(glib2.package_folder, "lib", "glib-2.0", "include"))
            self.cpp_info.libdirs.append(os.path.join(glib2.package_folder, "lib"))
            for _lib in ("glib-2.0", "gobject-2.0", "gio-2.0", "gmodule-2.0",
                         "gthread-2.0", "ffi", "intl"):
                if _lib not in self.cpp_info.libs:
                    self.cpp_info.libs.append(_lib)
            # runtime: shared libs are needed at test run time; glib2 has no
            # runenv_info of its own, so expose both lib dirs here.
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(glib2.package_folder, "lib"))
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        # PkgConfigDeps picks up pkg_config_name; CMakeDeps (test_package) needs
        # cmake_file_name + cmake_target_name set explicitly (pkg_config_name
        # does NOT influence CMakeDeps in conan 2).
        self.cpp_info.set_property("pkg_config_name", "libsoup-3.0")
        self.cpp_info.set_property("cmake_file_name", "libsoup-3.0")
        self.cpp_info.set_property("cmake_target_name", "libsoup-3.0::libsoup-3.0")
