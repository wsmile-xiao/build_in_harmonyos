#!/usr/bin/env python3
"""Conan recipe — glib 2.88.0 (Meson).

GLib is the low-level core library of GNOME: data structures, object system
(GObject), main loop, I/O (GIO), threading, regex (via PCRE2) and more.
Adapted to HarmonyOS PC (aarch64). See notes.md for the platform adaptations.
"""
import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class GlibConan(ConanFile):
    name = "glib"
    version = "2.88.0.1"
    description = "GLib — GNOME core C utility library (glib, gobject, gio, gmodule, gthread)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/glib"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    # Generate .pc files for the conan deps (pcre2, zlib) so meson's
    # dependency('pcre2'/'zlib') finds them via pkg-config. MesonToolchain is
    # produced manually in generate() (customized project_options).
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # glib regex needs pcre2; GIO compression needs zlib. libffi (gobject
        # closures) is not published in the registry, so glib builds it from its
        # bundled meson subproject (subprojects/libffi.wrap) — see patch 0005.
        self.requires("pcre2/10.45")
        # zlib/1.3.1.1.1.1 builds libz.a from PIC objects (static + -fPIC), so it
        # can be linked into glib's shared libraries (shared=True) without the
        # AArch64 non-PIC relocation failure. See zlib 1.3.1.1.1 notes.md.
        self.requires("zlib/1.3.1.1.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # libffi is not published in the OHOS conan registry, so vendor it as a
        # meson subproject: place its source + the wrapdb meson build files into
        # subprojects/libffi-3.5.2/. glib then builds libffi offline (patch 0005).
        # Both URLs use github hosts so CI's mirror fallback rewrites them to a
        # mirror list (workers can't reach github.com directly); conan get()
        # accepts a url list and the .zip patch is auto-extracted.
        ffi = self.conan_data["libffi_subproject"]
        subprojects = os.path.join(self.source_folder, "subprojects")
        ffi_dir = os.path.join(subprojects, "libffi-3.5.2")
        get(self, url=ffi["source"]["url"], sha256=ffi["source"]["sha256"],
            destination=ffi_dir, strip_root=True)
        # wrapdb meson build files (zip, libffi-3.5.2/<meson.build>) overlay the source
        get(self, url=ffi["patch"]["url"], sha256=ffi["patch"]["sha256"],
            destination=subprojects)
        # glib unconditionally requires gettext/intl; musl has none, so vendor the
        # proxy-libintl subproject (glib falls back to it via allow_fallback).
        pintl = self.conan_data["proxy_libintl"]
        get(self, url=pintl["source"]["url"], sha256=pintl["source"]["sha256"],
            destination=os.path.join(subprojects, "proxy-libintl-0.5"), strip_root=True)
        # proxy-libintl 默认以 SONAME libintl.so.8 构建，与系统 gettext 的
        # libintl.so.8 同名冲突：shared 构建下测试 LD_LIBRARY_PATH 把 proxy-libintl
        # 置于首位，导致 Python 解释器加载 proxy-libintl（只导出 g_libintl_* 符号）
        # 而启动失败（exit 127）。把 soversion 提升为 9（SONAME 变为 libintl.so.9），
        # 与系统 gettext 的 libintl.so.8 彻底错开。
        _pintl_meson = os.path.join(subprojects, "proxy-libintl-0.5", "meson.build")
        with open(_pintl_meson, encoding="utf-8") as _handle:
            _pintl_content = _handle.read()
        _pintl_content = _pintl_content.replace(
            "soversion : 8,",
            "soversion : 9,",
        )
        with open(_pintl_meson, "w", encoding="utf-8") as _handle:
            _handle.write(_pintl_content)

    def generate(self):
        # The CI worker exports AR/AS/STRIP/NM/RANLIB as llvm-* names (llvm-ar,
        # llvm-as, ...) that are NOT on its PATH — only the GNU binutils
        # (ar/as/strip/nm/ranlib) and ld.lld exist. meson probes these and aborts
        # at configure ("Unknown linker(s): llvm-ar"), and its name search does
        # not resolve bare names, so pin the real tools by ABSOLUTE PATH (resolved
        # from PATH) and drop the broken env values.
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(f"Required build tools not found in PATH: {', '.join(missing)}")
        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = tools["strip"]
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Conan's MesonToolchain defaults wrap_mode=nofallback, which blocks the
        # libffi subproject fallback (libffi is not in the registry; vendored in
        # subprojects/libffi-3.5.2/ by source()). nodownload re-enables fallback
        # to the pre-existing (vendored) subproject without allowing network wraps.
        tc.project_options["wrap_mode"] = "nodownload"
        # OHOS has no libmount / selinux / gettext (nls) in the toolchain sysroot.
        tc.project_options["libmount"] = "disabled"
        tc.project_options["selinux"] = "disabled"
        tc.project_options["nls"] = "disabled"
        # No gobject-introspection / man pages / gtk-doc / fuzzing on the target.
        tc.project_options["introspection"] = "disabled"
        tc.project_options["man-pages"] = "disabled"
        tc.project_options["gtk_doc"] = "false"
        tc.project_options["oss_fuzz"] = "disabled"
        # Build upstream tests; native OHOS/HarmonyOS runs them in build().
        tc.project_options["tests"] = "true"
        tc.project_options["installed_tests"] = "false"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        if self.options.shared and self.settings.os == "OHOS":
            # OHOS HMDFS 的 dlopen 无法通过符号链接加载 .so（报 Permission
            # denied）。meson 生成的是"版本化 .so + 符号链接别名"
            # （libgio-2.0.so.0 -> libgio-2.0.so.0.8800.0），构建期工具
            # （glib-compile-resources 等）运行时会因此加载失败。所以先把
            # 主共享库构建出来，把符号链接替换为硬拷贝，再继续构建其余目标。
            self._build_shared_libs_then_fix_symlinks(meson)
        meson.build()
        if self.options.shared and self.settings.os == "OHOS":
            # 完整构建后，测试插件等剩余 .so 的符号链接也替换为硬拷贝。
            self._fix_so_symlinks()
        if cross_building(self):
            self.output.info(
                "cross-building: skip meson.test() (OHOS binaries are not runnable on the build host)"
            )
        else:
            if hasattr(os, "uname") and os.uname().sysname in ("OHOS", "HarmonyOS"):
                build_folder = self.build_folder

                def _ohos_meson_test():
                    self.run(
                        'meson test -v -C "{}" --timeout-multiplier=16 '
                        "--no-rebuild --no-suite=failing".format(build_folder)
                    )

                meson.test = _ohos_meson_test

            meson.test()

    def _shared_lib_targets(self):
        # glib-compile-resources 等构建期工具链接 libgio，而 libgio 又链接
        # libglib/libgobject/libgmodule 以及两个子项目库（libffi/libintl）。
        # 只有这些库先构建出来并把符号链接换成硬拷贝，工具才能运行。
        # 注意：这里必须用 meson 的 target 名（introspect --targets），
        # 不能用 ninja 的路径形式（ffi/intl 是子项目 target 名）。
        return " ".join(
            ["ffi", "intl", "glib-2.0", "gobject-2.0", "gmodule-2.0", "gio-2.0"]
        )

    def _build_shared_libs_then_fix_symlinks(self, meson):
        meson.build(target=self._shared_lib_targets())
        self._fix_so_symlinks()

    def _fix_so_symlinks(self):
        self._fix_so_symlinks_in(self.build_folder)

    def _fix_so_symlinks_in(self, folder):
        """Replace meson-generated .so symlinks with hard copies.

        OHOS HMDFS's dynamic loader refuses to dlopen a shared library through a
        symlink ("Permission denied"), so every ``lib*.so``/``lib*.so.N`` alias
        must be a real file copy of its versioned target.
        """
        for link in glob.glob(os.path.join(folder, "**", "*.so*"), recursive=True):
            if not os.path.islink(link):
                continue
            target = os.path.realpath(link)
            if not os.path.isfile(target):
                continue
            os.unlink(link)
            shutil.copyfile(target, link)
            os.chmod(link, 0o755)

    def package(self):
        meson = Meson(self)
        meson.install()
        if self.options.shared and self.settings.os == "OHOS":
            # 安装目录里的 .so 别名同样需要是硬拷贝，供下游消费者 dlopen。
            self._fix_so_symlinks_in(self.package_folder)
            # meson install 会改动 ELF（如 strip），使 .codesign 失效，必须
            # 对安装产物重新签名，否则 OHOS 动态链接器拒绝加载（Permission denied）。
            self._sign_installed_elfs()

    def _sign_installed_elfs(self):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip signing installed ELFs")
            return
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        patterns = [
            os.path.join(self.package_folder, "bin", "*"),
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
        ]
        candidates = []
        for pattern in patterns:
            candidates.extend(glob.glob(pattern, recursive=True))
        for binary in sorted(set(candidates)):
            if not os.path.isfile(binary) or os.path.islink(binary):
                continue
            # 跳过非 ELF 文件（如 gdbus-codegen 实为 Python 脚本）。
            with open(binary, "rb") as handle:
                if handle.read(4) != b"\x7fELF":
                    continue
            if os.path.isfile(objcopy):
                self.run(
                    f"{shlex.quote(objcopy)} --remove-section .codesign "
                    f"{shlex.quote(binary)} 2>/dev/null || true"
                )
            self.run(
                shlex.join(
                    [signer, "sign", "-inFile", binary, "-outFile", binary, "-selfSign", "1"]
                )
            )

    def package_info(self):
        # GLib installs libglib-2.0/libgobject-2.0/libgio-2.0/libgmodule-2.0/
        # libgthread-2.0 plus libffi.a (vendored subproject) and libintl.a
        # (proxy-libintl subproject). Component metadata makes Conan's
        # PkgConfigDeps emit glib-2.0.pc / gobject-2.0.pc / gio-2.0.pc /
        # gmodule-2.0.pc / gthread-2.0.pc with the real Libs/Requires.
        glib_includedirs = ["include/glib-2.0", "lib/glib-2.0/include"]
        self.cpp_info.includedirs = glib_includedirs

        glib = self.cpp_info.components["glib-2.0"]
        glib.set_property("pkg_config_name", "glib-2.0")
        glib.libs = ["glib-2.0", "intl"]
        glib.system_libs = ["m", "pthread", "dl", "rt"]
        glib.includedirs = ["include", "include/glib-2.0", "lib/glib-2.0/include"]
        glib.requires = ["pcre2::pcre2"]

        gobject = self.cpp_info.components["gobject-2.0"]
        gobject.set_property("pkg_config_name", "gobject-2.0")
        gobject.libs = ["gobject-2.0", "ffi"]
        gobject.includedirs = glib_includedirs
        gobject.requires = ["glib-2.0"]

        gio = self.cpp_info.components["gio-2.0"]
        gio.set_property("pkg_config_name", "gio-2.0")
        gio.libs = ["gio-2.0", "intl"]
        gio.includedirs = glib_includedirs
        gio.requires = ["glib-2.0", "gobject-2.0", "gmodule-2.0", "zlib::zlib"]

        gmodule = self.cpp_info.components["gmodule-2.0"]
        gmodule.set_property("pkg_config_name", "gmodule-2.0")
        gmodule.libs = ["gmodule-2.0"]
        gmodule.includedirs = glib_includedirs
        gmodule.requires = ["glib-2.0"]

        gthread = self.cpp_info.components["gthread-2.0"]
        gthread.set_property("pkg_config_name", "gthread-2.0")
        gthread.libs = ["gthread-2.0"]
        gthread.includedirs = glib_includedirs
        gthread.requires = ["glib-2.0"]
