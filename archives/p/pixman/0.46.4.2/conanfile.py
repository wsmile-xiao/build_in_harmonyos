#!/usr/bin/env python3
"""Conan recipe — pixman 0.46.4.2 (Meson)"""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class PixmanConan(ConanFile):
    name = "pixman"
    version = "0.46.4.2"
    description = "Low-level pixel manipulation library used by Cairo and Xorg"
    license = "MIT"
    homepage = "https://cairographics.org/"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    package_type = "shared-library"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        # 鸿蒙 PC 无 gtk/glib/libpng/openmp，且不需要测试/demo：只留核心库（依赖 libm+pthread 系统库）。
        tc.project_options["tests"] = "disabled"
        tc.project_options["demos"] = "disabled"
        tc.project_options["gtk"] = "disabled"
        tc.project_options["libpng"] = "disabled"
        tc.project_options["openmp"] = "disabled"
        tc.generate()
        # conan MesonToolchain 不把 tools.build:compiler_executables 的 ar/ranlib 写进 native file，
        # meson 便按裸名 llvm-ar 探归档器，而 clang 工具链在 /data/service/hnp/bin，PATH 上无 llvm-ar
        # 时 configure 失败。直接把 ar/ranlib 全路径注入 conan_meson_native.ini，不污染 PATH。
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        _ar = _ce.get("ar"); _rl = _ce.get("ranlib")
        # CI profile 仅提供 c/cpp，未给 ar/ranlib：从 c 编译器同目录推导 llvm-ar/llvm-ranlib 全路径。
        if not _ar:
            _cc = _ce.get("c") or ""
            _bindir = os.path.dirname(_cc) if os.path.sep in _cc else ""
            if _bindir:
                _cand = os.path.join(_bindir, "llvm-ar")
                if os.path.isfile(_cand):
                    _ar = _cand
                    _rlc = os.path.join(_bindir, "llvm-ranlib")
                    if os.path.isfile(_rlc):
                        _rl = _rlc
        _nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if _ar and os.path.isfile(_nf):
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

    def package_info(self):
        self.cpp_info.libs = ['pixman-1']
        # pixman 头装在 include/pixman-1/（pixman.h + pixman-version.h）；pixman.h 内部
        # #include <pixman-version.h> 需 -I.../include/pixman-1。
        self.cpp_info.includedirs = ["include/pixman-1", "include"]
        self.cpp_info.set_property("cmake_file_name", "pixman")
        self.cpp_info.set_property("cmake_target_name", "pixman::pixman")
        self.cpp_info.set_property("pkg_config_name", "pixman-1")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ['m', 'pthread']
