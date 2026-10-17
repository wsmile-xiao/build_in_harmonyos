#!/usr/bin/env python3
"""Conan recipe — lite (lite-xl) 2.1.8 (meson, application).

Lite XL is a lightweight text editor written in C with an embedded Lua
runtime, built with Meson.  This recipe produces the `lite-xl` executable
(bin/) plus its runtime data (share/lite-xl).

Dependency policy (R27/R36): every dependency comes from the conan registry
via pkg-config (PkgConfigDeps); meson subprojects are disabled
(wrap_mode=nodownload) so a missing dependency fails loudly instead of being
silently replaced by a network download.

Source-verified dependency contract (lite-xl 2.1.8, src/meson.build):
  - sdl_dep    = dependency('sdl3', static: true)   → requires sdl3/3.4.8
                  (2.1.8 源码硬编码 SDL3，无 sdl2 回退 —— 已核实)
  - freetype   = dependency('freetype2')            → freetype/2.14.3
  - lua        = use_system_lua=true 时遍历
                  dependency('lua5.4') / ('lua-5.4') / ('lua')
                  → lua/5.4.8 (pkg-config 名 lua-5.4 + 别名补丁见下)
  - pcre2      = dependency('libpcre2-8')           → pcre2/10.45.1
  - libm/libdl = cc.find_library('m'|'dl')          → system_libs
  - subprojects/ 仅含 freetype2.wrap / lua.wrap / pcre2.wrap，
    无 agg.wrap、无 agg 引用（已核实，移除 agg 相关假设）。
"""
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LiteConan(ConanFile):
    name = "lite"
    version = "2.1.8"
    description = "Lite XL — a lightweight, fast and free text editor written in Lua and C (lite-xl 2.1.8)"
    license = "MIT"
    homepage = "https://lite-xl.com/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # lite-xl 2.1.8 的 meson 依赖（均经 pkg-config 查找，PkgConfigDeps 生成 .pc）。
        # SDL3 依据（已核实源码 src/meson.build:62）：`sdl_dep = dependency('sdl3', static: true)`
        # 硬编码 SDL3，**无 SDL2 回退**，故本配方 requires sdl3/3.4.8。
        # sdl3/3.4.8 的 conan 配方由协作者并行补全（archives/s/sdl3/3.4.8/ 有 OHOS 适配归档：
        # status built、G0-G4 pass、4 个 OHOS 补丁）。若配方未就绪，conan create 前需 W0 复核。
        self.requires("sdl3/3.4.8")
        self.requires("freetype/2.14.3")   # pkg-config 名 freetype2（本仓配方已正确设置）
        self.requires("lua/5.4.8")         # pkg-config 名 lua-5.4（generate() 补 lua.pc/lua5.4.pc 别名）
        self.requires("pcre2/10.45.1")     # pkg-config 名 libpcre2-8（本仓配方组件化输出）
        # agg：已核实 lite-xl 2.1.8 subprojects/ 只有 freetype2.wrap/lua.wrap/pcre2.wrap，
        #   无 agg.wrap，src/meson.build 也无 dependency('agg') —— agg **不是依赖**，移除。

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        # 依赖全走 conan（R36）：禁止 meson 偷偷下载 wrap 子项目，缺了当场报错。
        tc.project_options["wrap_mode"] = "nodownload"
        # 使用系统 Lua（pkg-config，走 conan lua 配方）：源码 meson_options 的
        # use_system_lua 选项（默认 false → 走 lua.wrap 需要下载 wrap，nodownload 下会失败）。
        # 置 true 后遍历 lua_names {lua5.4, lua-5.4, lua}，全部经 pkg-config 命中。
        tc.project_options["use_system_lua"] = True
        # dav1d 教训（musl）：严格 c99 不自动定义 _POSIX_C_SOURCE，POSIX 函数检测误判失败。
        # lite-xl 上游默认 gnu11，这里显式钉死，避免检测函数在 musl 上失败。
        tc.project_options["c_std"] = "gnu11"
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.generate()
        self._inject_meson_archiver()
        self._ensure_lua_pkgconfig_alias()

    def _inject_meson_archiver(self):
        # 【OHOS 必需】conan 的 MesonToolchain 不把 tools.build:compiler_executables 里的
        # ar/ranlib 写进 native file，meson 便按裸名 llvm-ar 探归档器；而 clang 工具链在
        # /data/service/hnp/bin，PATH 上没有 llvm-ar 时 meson configure 直接失败。
        # 把 ar/ranlib 全路径注入 conan_meson_native.ini，不污染 PATH。（dav1d/fontconfig 实证）
        import os
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        _ar, _rl = _ce.get("ar"), _ce.get("ranlib")
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
        if not (_ar and os.path.isfile(_nf)):
            return
        with open(_nf, encoding="utf-8") as _f:
            _c = _f.read()
        if "\nar =" in _c or "[binaries]" not in _c:
            return
        _ins = "[binaries]\nar = '%s'\n" % _ar
        if _rl:
            _ins += "ranlib = '%s'\n" % _rl
        with open(_nf, "w", encoding="utf-8") as _f:
            _f.write(_c.replace("[binaries]\n", _ins, 1))

    def _ensure_lua_pkgconfig_alias(self):
        # 源码（已核实 src/meson.build:25-29）在 use_system_lua=true 时遍历
        #   lua_names = ['lua5.4', 'lua-5.4', 'lua']
        # 而本仓 lua/5.4.8 配方生成的 .pc 名是 lua-5.4（pkg_config_name="lua-5.4"）。
        # 这里在 generators 目录补 lua5.4.pc / lua.pc 别名（Requires: lua-5.4），
        # 覆盖全部三个探测名（顺序：lua5.4 → lua-5.4 → lua，命中即停）。
        import os
        _gf = self.generators_folder
        _version = "5.4.8"
        try:
            _version = str(self.dependencies["lua"].ref.version)
        except (KeyError, AttributeError):
            pass
        for _alias in ("lua5.4", "lua"):
            _p = os.path.join(_gf, _alias + ".pc")
            if os.path.isfile(_p):
                continue
            try:
                with open(_p, "w", encoding="utf-8") as _f:
                    _f.write(
                        "Name: %s\n"
                        "Description: pkg-config alias for conan lua "
                        "(lite-xl meson requests dependency('%s'))\n"
                        "Version: %s\n"
                        "Requires: lua-5.4\n" % (_alias, _alias, _version)
                    )
            except (IOError, OSError):
                self.output.warning("failed to write %s.pc alias (non-fatal)" % _alias)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        # R32: settings.os 判断必须用 in ("Linux", "OHOS")，不能 == "Linux"。
        # 签名工具仅在 OHOS 设备存在，_sign_binaries 内部按工具是否存在跳过
        # （Linux 主机上执行无副作用）。
        if self.settings.os in ("Linux", "OHOS"):
            self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求被 exec 的可执行文件（及 dlopen 的 .so）带代码签名，否则报
        # Permission denied / Operation not permitted（dav1d/1.5.0、fontconfig 实证）。
        # ① lib/ 的 .so  ② bin/ 的 ELF 可执行文件（lite-xl 本体）。
        import glob
        import os
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            self.output.info("sign tool not found — skip signing (non-OHOS host?)")
            return
        for f in targets:
            if os.path.islink(f):  # 只签真实 ELF，跳版本化 .so 的软链（否则对同一目标重复签）
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        # application package：可执行文件在 bin/，运行时数据在 share/lite-xl（非库，无 cpp_info.libs）。
        self.cpp_info.bindirs = ["bin"]
        # R32: Linux-like 平台（Linux / OHOS）统一处理。lite-xl 运行期依赖 libm/libdl/libpthread
        # （内嵌 Lua + dlopen），供可能的消费者参考。
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "m", "pthread"]
