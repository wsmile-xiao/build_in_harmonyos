#!/usr/bin/env python3
"""Conan recipe — fontconfig 2.18.1 (meson)"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout


class FontconfigConan(ConanFile):
    name = "fontconfig"
    version = "2.18.1.1"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}


    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("freetype/2.14.3")
        self.requires("expat/2.8.2.1")   # 2.8.2 的 .so 无 SONAME，链它会把绝对路径写进本包 DT_NEEDED

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        # 依赖经 pkg-config 找：freetype2（conan freetype）、expat（conan expat）。
        tc.project_options["xml-backend"] = "expat"   # 定死用 expat，不走 libxml2
        tc.project_options["doc"] = "disabled"        # 无 docbook/pdf
        tc.project_options["nls"] = "disabled"        # 无 gettext
        tc.project_options["tests"] = "disabled"
        tc.project_options["tools"] = "disabled"      # 不装 fc-cache/fc-list（库包保持最小）
        tc.project_options["cache-build"] = "disabled"  # 关键：不在构建期跑 aarch64 fc-cache（见 notes/ML）
        tc.generate()
        # conan MesonToolchain 不把 tools.build:compiler_executables 的 ar/ranlib 写进 native file，
        # meson 便按裸名 llvm-ar 探归档器，而 clang 工具链在 /data/service/hnp/bin，PATH 上无 llvm-ar
        # 时 configure 失败。直接把 ar/ranlib 全路径注入 conan_meson_native.ini，不污染 PATH。
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
        # CI 环境已全局提供 meson/ninja，无需再手动前置设备侧 usr/local/bin、hnp/bin 到 PATH。
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        self._sign_shared_libs()



    def _sign_shared_libs(self):
        # meson install 重写 rpath 会改动链接后的 .so → 链接器自签失效，OHOS XPM dlopen 报 Permission denied。
        # 剥旧 .codesign + binary-sign-tool -selfSign 1 重签（ML-0043 场景）。
        import glob, os
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        explicit_libs = ['fontconfig']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "fontconfig")
        self.cpp_info.set_property("cmake_target_name", "fontconfig::fontconfig")
        pkg = "fontconfig" or self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
        import os
        for _env in []:
            _k, _v = _env.split("=", 1)
            self.runenv_info.define_path(_k, os.path.join(self.package_folder, _v))

    def _detect_pkg_config_name(self):
        # 未显式给 --pkgconfig-name 时，从 install 出的 lib/pkgconfig/*.pc 取第一个文件名 stem。
        import glob
        import os
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
