#!/usr/bin/env python3
"""Conan recipe — libepoxy 1.5.10 (Meson).

Epoxy is a library for handling OpenGL function pointer management.
It builds `libepoxy.so.0.0.0` and generates GL/EGL/GLX dispatch code
from Khronos XML registries via src/gen_dispatch.py.

On HarmonyOS PC there is no window system (no X11/Wayland), so GLX,
EGL and X11 support are disabled; only the core GL dispatch headers
(libepoxy.so) are produced.  Patch 0001 makes the gen_dispatch.py
custom_target invoke python3 explicitly, because the device
filesystem cannot execute Python scripts via shebang (E081-like).

R26: libepoxy ships a system-name shared library; build it static to
avoid polluting /lib on OHOS.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class LibEpoxyConan(ConanFile):
    name = "libepoxy"
    version = "1.5.10"
    license = "MIT"
    description = "OpenGL epoxy library - GL function pointer management"
    homepage = "https://github.com/anholt/libepoxy"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    # R26: default to static to avoid polluting /lib on OHOS
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libepoxy 无外部库依赖（仅需要系统 GL/EGL 头；OHOS 上禁用 GLX/EGL/X11）
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        # R26: static build to avoid polluting /lib on OHOS
        if not self.options.shared:
            tc.project_options["default_library"] = "static"
        # OHOS 无窗口系统：禁用 GLX/EGL/X11（glx/egl 为 combo，x11 为 boolean）；
        # Linux 保留默认（有 GL 库），仅 OHOS 条件化禁用，与 package_info 的
        # os in ("Linux", "OHOS") 平台分支一致
        if self.settings.os == "OHOS":
            tc.project_options["glx"] = "no"
            tc.project_options["egl"] = "no"
            tc.project_options["x11"] = "false"
        tc.project_options["tests"] = "false"
        # Don't let meson download wrap subprojects
        tc.project_options["wrap_mode"] = "nofallback"
        tc.generate()
        # conan MesonToolchain 不把 tools.build:compiler_executables 的 ar/ranlib 写进 native file，
        # meson 便按裸名 llvm-ar 探归档器，而 clang 工具链在 /data/service/hnp/bin，PATH 上无 llvm-ar
        # 时 configure 失败。直接把 ar/ranlib 全路径注入 conan_meson_native.ini，不污染 PATH
        # （与 cairo/pango/atk 配方一致）。
        import os as _os
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        _ar = _ce.get("ar"); _rl = _ce.get("ranlib")
        # CI profile 仅提供 c/cpp，未给 ar/ranlib：从 c 编译器同目录推导 llvm-ar/llvm-ranlib 全路径。
        if not _ar:
            _cc = _ce.get("c") or ""
            _bindir = _os.path.dirname(_cc) if _os.path.sep in _cc else ""
            if _bindir:
                _cand = _os.path.join(_bindir, "llvm-ar")
                if _os.path.isfile(_cand):
                    _ar = _cand
                    _rlc = _os.path.join(_bindir, "llvm-ranlib")
                    if _os.path.isfile(_rlc):
                        _rl = _rlc
        _nf = _os.path.join(self.generators_folder, "conan_meson_native.ini")
        if _ar and _os.path.isfile(_nf):
            with open(_nf) as _f: _c = _f.read()
            if "\nar =" not in _c and "[binaries]" in _c:
                _ins = "[binaries]\nar = '%s'\n" % _ar
                if _rl: _ins += "ranlib = '%s'\n" % _rl
                _c = _c.replace("[binaries]\n", _ins, 1)
                with open(_nf, "w") as _f: _f.write(_c)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        # 仅 shared 构建时需要 .so 符号链接：meson 安装会生成
        # libepoxy.so.0.0.0 与符号链接；设备文件系统不支持 ln -sf 覆盖，
        # 用 rm -f && ln -s 模式补齐缺失的 .so / .so.0 链接。
        # （R26 静态默认下 meson 只装 libepoxy.a，此逻辑为安全空操作。）
        if self.options.shared:
            import glob, os as _os
            libdir = _os.path.join(self.package_folder, "lib")
            target = None
            for cand in sorted(glob.glob(_os.path.join(libdir, "libepoxy.so.*")), reverse=True):
                if cand.endswith(".so.0.0.0"):
                    target = cand
                    break
            if target:
                base = _os.path.basename(target)
                for link in ("libepoxy.so.0", "libepoxy.so"):
                    lp = _os.path.join(libdir, link)
                    try:
                        _os.remove(lp)
                    except OSError:
                        pass
                    if not _os.path.exists(lp):
                        _os.symlink(base, lp)

    def package_info(self):
        self.cpp_info.libs = ["epoxy"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "epoxy")
        self.cpp_info.set_property("cmake_target_name", "epoxy::epoxy")
        self.cpp_info.set_property("pkg_config_name", "epoxy")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
