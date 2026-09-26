#!/usr/bin/env python3
"""Conan recipe — delaunay-triangulation 2.1 (Meson build).

Builds the upstream Bl4ckb0ne/delaunay-triangulation library (shared lib +
public headers under include/dt). Optional upstream deps (catch2 for tests,
sfml-graphics for example) are NOT packaged; the recipe builds the library
itself, matching the OHOS aarch64 CI profile.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class DelaunaytriangulationConan(ConanFile):
    name = "delaunay-triangulation"
    version = "2.1"
    description = "C++ version of the delaunay triangulation"
    license = "MIT"
    homepage = "https://github.com/Bl4ckb0ne/delaunay-triangulation"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # R26: system-name libraries default to static; this is a library only,
        # no CLI tooling is produced (R38: no commands.json needed).
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.generate()
        # conan MesonToolchain 不把 tools.build:compiler_executables 的 ar/ranlib 写进 native file，
        # meson 便按裸名 llvm-ar 探归档器（CI 首错 Unknown linker(s): [['llvm-ar']]）。直接把
        # ar/ranlib 全路径注入 conan_meson_native.ini [binaries] 段，不污染 PATH、不改 CI profile。
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
        self.cpp_info.libs = ["delaunay-triangulation"]
        self.cpp_info.includedirs = ["include"]
