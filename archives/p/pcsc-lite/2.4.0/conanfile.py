#!/usr/bin/env python3
"""Conan recipe for pcsc-lite 2.4.0 — HarmonyOS PC (aarch64)。

构建系统：meson（autoreconf 在鸿蒙上因宏缺失失败，改用 meson，见 notes.md）。

适配要点：
- pthread_cancel 未在鸿蒙实现 → meson has_function → HAVE_PTHREAD_CANCEL；无则回退 stop-polling
- meson 在鸿蒙上探测不到 llvm-ar（PATH 无），generate() 里把 ar/ranlib 全路径注入 native file
- meson install 重写 rpath 使链接器自签的 .codesign 失效 → package() 里用 binary-sign-tool 重签
- libusb-1.0 由 conan 依赖提供（PkgConfigDeps 生成 libusb-1.0.pc）
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class PcscliteConan(ConanFile):
    name = "pcsc-lite"
    version = "2.4.0"
    description = "Middleware to access a smart card using SCard API (PC/SC)"
    license = "GPL-3.0"
    homepage = "https://pcsclite.apdu.fr/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # 非系统同名库，默认动态（R27）
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R27: 依赖使用已发布到 ohpcd 的 conan 包
        self.requires("libusb/1.0.27")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 为 meson dependency('libusb-1.0') 提供 libusb-1.0.pc（指向 conan 包路径）
        PkgConfigDeps(self).generate()

        tc = MesonToolchain(self)
        # 鸿蒙平台特性选项（与历史 manifest 一致）
        tc.project_options["libsystemd"] = "false"
        tc.project_options["libudev"] = "false"
        tc.project_options["libusb"] = "true"
        tc.project_options["polkit"] = "false"
        tc.project_options["usb"] = "true"
        tc.project_options["serial"] = "true"
        # 禁止 meson 偷偷下载 wrap 子项目
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.generate()

        # conan MesonToolchain 不把 ar/ranlib 写进 native file，meson 便按裸名 llvm-ar
        # 探测归档器，而 PATH 上无 llvm-ar 时 configure 失败。直接把 ar/ranlib 全路径
        # 注入 conan_meson_native.ini，不污染 PATH（与 cairo 配方同款处理）。
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        _ar = _ce.get("ar")
        _rl = _ce.get("ranlib")
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
            with open(_nf) as _f:
                _c = _f.read()
            if "\nar =" not in _c and "[binaries]" in _c:
                _ins = "[binaries]\nar = '%s'\n" % _ar
                if _rl:
                    _ins += "ranlib = '%s'\n" % _rl
                _c = _c.replace("[binaries]\n", _ins, 1)
                with open(_nf, "w") as _f:
                    _f.write(_c)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        self._sign_elf()

    def _sign_elf(self):
        """meson install 重写 rpath 会改动链接后的 ELF → 链接器自签失效，OHOS 加载报
        Permission denied。剥旧 .codesign + binary-sign-tool -selfSign 1 重签。"""
        hnp = "/data/service/hnp/bin"
        objcopy = os.path.join(hnp, "llvm-objcopy")
        signer = os.path.join(hnp, "binary-sign-tool")
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            self.output.warning("binary-sign-tool/llvm-objcopy 不可用，跳过 ELF 重签")
            return
        elfs = []
        for pat in ("sbin/*", "bin/*", "lib/*.so", "lib/*.so.*"):
            elfs += glob.glob(os.path.join(self.package_folder, pat))
        for f in sorted(set(elfs)):
            if not os.path.isfile(f):
                continue
            try:
                if open(f, "rb").read(4) != b"\x7fELF":
                    continue
            except OSError:
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}.signed" -selfSign 1'.format(sg=signer, f=f))
            if os.path.isfile(f + ".signed"):
                os.replace(f + ".signed", f)
                os.chmod(f, 0o755)

    def package_info(self):
        # 消费者链接 -lpcsclite（libpcsclite.so.1 = redirect，运行时 dlopen libpcsclite_real）
        self.cpp_info.libs = ["pcsclite"]
        # 头文件全部安装在 include/PCSC/（winscard.h / pcsclite.h / wintypes.h ...）
        self.cpp_info.includedirs = ["include/PCSC", "include"]
        self.cpp_info.set_property("pkg_config_name", "libpcsclite")
        if self.settings.os in ("Linux", "OHOS"):
            # libredirect.c 用 dlopen 加载 libpcsclite_real.so.1
            self.cpp_info.system_libs = ["dl", "pthread"]
