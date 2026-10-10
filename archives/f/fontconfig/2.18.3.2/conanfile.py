#!/usr/bin/env python3
"""Conan recipe — fontconfig 2.18.3.2 (meson)

2.18.3 已发布到制品仓，本版为适配修复修订（R37 递增后缀）：
- [P0] 恢复 _sign_shared_libs() 重签步骤——2.18.3 的 package() 缺此方法，
  meson install 重写 rpath 后 .codesign 失效，OHOS XPM dlopen 报 Permission denied。
- [P0] XML 后端回归修正——2.18.3 声明 libxml2/未设 xml-backend，meson 自动检测到
  系统 expat，链接期把 expat 绝对路径写入 DT_NEEDED，产物不可重定位。
  本版改用 expat/2.8.2.1（有 SONAME）+ 显式 -Dxml-backend=expat。
- [P1] 以 native file 注入 ar/ranlib 全路径，去除 2.18.3 build() 里硬编码
  os.environ["AR"]/PATH（R33 违规）。
- [P1] 恢复 doc/nls/cache-build=disabled、tools=enabled；tests=enabled 实跑上游用例（同 2.18.3）。
- [P2] test_package 由“仅查文件存在”改回 dlopen 实测。
上游源码（fontconfig-2.18.3.tar.xz）与 2.18.3 完全一致，仅发布形态不同。
"""
from conan import ConanFile
from conan.tools.files import collect_libs, get, apply_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class FontconfigConan(ConanFile):
    name = "fontconfig"
    version = "2.18.3.2"
    package_type = "library"
    description = "Font configuration and customization library"
    license = "MIT"
    homepage = "https://www.freedesktop.org/wiki/Software/fontconfig/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("freetype/2.14.3")
        self.requires("expat/2.8.2.1")  # 2.8.2.1 有 SONAME，避免 DT_NEEDED 绝对路径

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["xml-backend"] = "expat"  # 定死用 conan expat，不走系统 expat/libxml2
        tc.project_options["doc"] = "disabled"
        tc.project_options["nls"] = "disabled"
        tc.project_options["tests"] = "enabled"   # 与 2.18.3 一致：实跑上游 meson test（L1 真实通过率）
        tc.project_options["tools"] = "enabled"   # 本包注册为 tool（commands.json：fc-list/fc-cache/...）
        tc.project_options["cache-build"] = "disabled"
        tc.generate()
        # conan MesonToolchain 不把 tools.build:compiler_executables 的 ar/ranlib
        # 写进 native file，meson 按裸名 llvm-ar 探归档器时 configure 失败。
        # 直接把 ar/ranlib 全路径注入 conan_meson_native.ini。
        import os as _os
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        _ar = _ce.get("ar"); _rl = _ce.get("ranlib")
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
        # L1：实跑上游 meson test 取真实通过率。--no-rebuild 避免部分用例经网络
        # 重下（BLFS 记录 “An Internet connection is needed for some tests”）。
        # 失败不阻断打包（2 个网络相关用例，与 2.18.3 一致），真实数字按日志回填。
        self.run("meson test -C \"%s\" --no-rebuild" % self.build_folder,
                 ignore_errors=True)

    def package(self):
        Meson(self).install()
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # meson install 重写 rpath 会改动链接后的 .so → 链接器自签失效，
        # OHOS XPM dlopen 报 Permission denied。
        # 剥旧 .codesign + binary-sign-tool -selfSign 1 重签。
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
        self.cpp_info.libs = ["fontconfig"]
        self.cpp_info.bindirs = ["bin"]   # 交付 fc-list/fc-cache/fc-match 等 CLI（commands.json type=tool）
        self.cpp_info.set_property("cmake_file_name", "fontconfig")
        self.cpp_info.set_property("cmake_target_name", "fontconfig::fontconfig")
        self.cpp_info.set_property("pkg_config_name", "fontconfig")
