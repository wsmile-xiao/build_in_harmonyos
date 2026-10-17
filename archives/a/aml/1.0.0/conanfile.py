#!/usr/bin/env python3
"""Conan recipe — aml 1.0.0 (Meson project).

aml is "Another Main Loop" — a small main-loop / event-loop library for C.
Build system: Meson. Public header installed as <prefix>/include/aml1/aml.h,
pkg-config name: aml1.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class AmlConan(ConanFile):
    name = "aml"
    version = "1.0.0"
    description = "aml - Another Main Loop: a small main-loop/event-loop library for C"
    license = "ISC"
    homepage = "https://github.com/any1/aml"
    url = "https://github.com/any1/aml"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external runtime requirements; only libc + pthreads + librt.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.generate()
        # conan MesonToolchain 不把 tools.build:compiler_executables 的 ar/ranlib 写进 native file，
        # meson 便按裸名 llvm-ar 探归档器，而 clang 工具链在 /data/service/hnp/bin，PATH 上无 llvm-ar
        # 时 configure 失败。直接把 ar/ranlib 全路径注入 conan_meson_native.ini，不污染 PATH。
        # （同款先例：cairo/1.18.4、pixman/0.46.4）
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
        meson = Meson(self)
        meson.install()

    def package_info(self):
        # aml installs its header to <prefix>/include/aml1/aml.h (meson subdir)
        self.cpp_info.includedirs = ["include/aml1"]
        self.cpp_info.libs = ["aml"]
        self.cpp_info.set_property("pkg_config_name", "aml1")
