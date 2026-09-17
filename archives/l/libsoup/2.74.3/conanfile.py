#!/usr/bin/env python3
"""Conan recipe — libsoup 2.74.3 (Meson).

libsoup is an HTTP client/server library for GNOME, based on GLib.
This recipe builds the 2.x API (libsoup-2.4) with shared libraries.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain


class LibsoupConan(ConanFile):
    name = "libsoup"
    version = "2.74.3"
    description = "libsoup is an HTTP client/server library for GNOME, based on GLib"
    license = "LGPL-2.0-or-later"
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
        self.requires("libpsl/0.21.5.1")
        self.requires("libxml2/2.15.3")
        self.requires("sqlite3/3.49.1")
        self.requires("brotli/1.2.0")
        self.requires("libnghttp2/1.70.0")
        # glib2/*:shared=True forces a shared glib2 rebuild on CI (ohpcd only
        # publishes static glib2). That rebuild links zlib into libgio-2.0.so,
        # and the published zlib/1.3.1 libz.a is NOT -fPIC (R_AARCH64 relocation
        # failure). Override to the PIC variant zlib/1.3.1.1 (CFLAGS=-fPIC),
        # which is published on ohpcd, so the shared glib2 rebuild succeeds.
        self.requires("zlib/1.3.1.1", override=True)

    def layout(self):
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
        # lld (LLVM linker) depends on libxml2.so.16; the shared lib lives
        # in the OHOS SDK's llvm/lib dir but lld has no RPATH to find it.
        # Locate the SDK llvm/lib dir from clang's real path and add to
        # LD_LIBRARY_PATH so meson linker detection succeeds.
        # 注意：必须用 buildenv_info.prepend_path 持久化到 conan 构建环境
        # （conanbuild.sh），Meson 运行时才会带上；仅修改 os.environ 在
        # CI 上会被 conanbuild 环境的 LD_LIBRARY_PATH 覆盖（依赖注入只含
        # 依赖包 lib 目录），导致 lld 加载到错误的 libxml2 而 configure 失败
        # （Error relocating lld: xmlCopyNamespace: symbol not found）。
        clang_path = shutil.which("clang")
        if clang_path:
            clang_real = os.path.realpath(clang_path)
            llvm_lib = os.path.join(os.path.dirname(os.path.dirname(clang_real)), "lib")
            if os.path.isdir(llvm_lib):
                self.buildenv_info.prepend_path("LD_LIBRARY_PATH", llvm_lib)
                os.environ["LD_LIBRARY_PATH"] = (
                    llvm_lib + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
                )
        # ninja（meson 后端）与 lld 同为 HNP 工具链二进制，NEEDED
        # libc++_shared.so；conan 构建环境把 LD_LIBRARY_PATH 覆盖为依赖包
        # lib 目录后 ninja 加载 libc++ 失败 → meson "Could not detect Ninja
        # v1.8.2 or newer"（实测复现：加回 /system/lib64 即检测成功）。
        # 与 test_package 中 cmake 的同类修复保持一致。
        self.buildenv_info.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        os.environ["LD_LIBRARY_PATH"] = (
            "/system/lib64" + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        )
        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        # OHOS loader validates .codesign hash against file content; strip
        # rewrites .so content → hash mismatch → dlopen Permission denied.
        tc.strip = None
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # 构建上游测试二进制（规则5 要求真实运行上游测试并提供证据；
        # 测试在 build() 之后由 test_package/CI 阶段逐个真实执行）
        tc.project_options["tests"] = "true"
        tc.project_options["installed_tests"] = "false"
        # glib-networking (TLS backend) is not packaged on OHOS; libsoup meson
        # asserts at configure when tls_check is enabled — disable the check
        # (TLS is a runtime dependency, not needed to build).
        tc.project_options["tls_check"] = "false"
        tc.project_options["gnome"] = "false"
        # feature options -> "disabled" (not available on OHOS)
        for opt in ("vapi", "introspection", "gssapi", "ntlm", "sysprof"):
            tc.project_options[opt] = "disabled"
        tc.project_options["gtk_doc"] = "false"
        # meson needs the real .pc files (gio/gmodule-no-export/...) from the
        # glib2 package (PkgConfigDeps only generates glib-2.0.pc), plus the
        # system /usr/local pc dir for hard deps.
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
        # 部分 ohpcd 依赖包（如 brotli/1.2.0）发布时 .pc 的 prefix 指向
        # 已不存在的构建路径（b/brotlb671aafc9e833/p），直接用会链接失败；
        # 且不能回退系统 /usr/local pkg-config（DT_NEEDED 含绝对路径，
        # 产物不可移植）。将每个依赖包的 .pc 复制到本地并重写 prefix 为
        # conan 包真实路径（与上面 glib2 的处理一致，推广到全部依赖）。
        pc_fix_dir = os.path.join(self.build_folder, "deps-pc-fix")
        os.makedirs(pc_fix_dir, exist_ok=True)
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            _pc_dir = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if not os.path.isdir(_pc_dir):
                continue
            for pc in os.listdir(_pc_dir):
                if not pc.endswith(".pc"):
                    continue
                src = os.path.join(_pc_dir, pc)
                dst = os.path.join(pc_fix_dir, pc)
                with open(src, "r", encoding="utf-8") as fh:
                    text = fh.read()
                text = re.sub(r"^prefix=.*$", f"prefix={dep.package_folder}",
                              text, count=1, flags=re.M)
                with open(dst, "w", encoding="utf-8") as fh:
                    fh.write(text)
        extra_pc.insert(0, pc_fix_dir)
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
        # meson install may strip DT_RUNPATH from .so files, causing OHOS
        # loader .codesign hash mismatch. Copy original build artifacts.
        for _lib in ("libsoup-2.4.so.1.11.2",):
            _src = os.path.join(self.build_folder, "libsoup", _lib)
            _dst = os.path.join(self.package_folder, "lib", _lib)
            if os.path.exists(_src):
                shutil.copy2(_src, _dst)

    def package_info(self):
        self.cpp_info.libs = ["soup-2.4"]
        self.cpp_info.includedirs = ["include/libsoup-2.4"]
        self.cpp_info.system_libs = ["m", "pthread", "dl"]
        # libsoup public headers include glib/gio/gobject headers; CMakeDeps
        # generates empty data for the TRANSITIVE glib2 dep (conan 2.29), so
        # expose glib2's include dirs + libs here to let consumers compile/link.
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
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(glib2.package_folder, "lib"))
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        self.cpp_info.set_property("pkg_config_name", "libsoup-2.4")
        self.cpp_info.set_property("cmake_file_name", "libsoup-2.4")
        self.cpp_info.set_property("cmake_target_name", "libsoup-2.4::libsoup-2.4")
