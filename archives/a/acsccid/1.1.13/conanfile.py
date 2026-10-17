#!/usr/bin/env python3
"""Conan recipe for acsccid 1.1.13 — ACS CCID smartcard reader driver for HarmonyOS PC (aarch64).

构建系统：autotools (configure/make)。

适配要点：
- config.guess/config.sub 不识别 HarmonyOS → 0001 补丁（__OHOS__/ohos-linux 分支）
- config.status 动态临时目录在 HMDFS 上写入失败 (E167) → 0002 补丁改为固定目录
- conftest 运行时依赖 libpcsclite.so.1/libusb-1.0.so.0 → LD_LIBRARY_PATH 指向 conan 缓存
- libusb-1.0/libpcsclite 由 conan 依赖提供（PkgConfigDeps 生成 .pc）
- 产物为 IFD 驱动 bundle（pcsc/drivers/ifd-acsccid.bundle/Contents/<host>/libacsccid.so），
  install 重写 rpath 会使链接器自签失效 → package() 里重签 (E077)
"""
import glob
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class AcsccidConan(ConanFile):
    name = "acsccid"
    version = "1.1.13"
    description = "ACS CCID smart card reader PC/SC IFD handler"
    license = "LGPL-2.1"
    homepage = "https://acsccid.sourceforge.io/"
    url = "https://github.com/acshk/acsccid"

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libusb/1.0.27")
        self.requires("pcsc-lite/2.4.0")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 为 configure 的 PKG_CHECK_MODULES(libpcsclite/libusb-1.0) 提供 .pc
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--enable-usbdropdir=/usr/local/pcsc/drivers")
        tc.generate()

        # conftest 运行时需找到 libpcsclite.so.1 / libusb-1.0.so.0
        env = Environment()
        env.append_path("LD_LIBRARY_PATH", os.path.join(self.dependencies["pcsc-lite"].package_folder, "lib"))
        env.append_path("LD_LIBRARY_PATH", os.path.join(self.dependencies["libusb"].package_folder, "lib"))
        env.vars(self).save_script("conanruntime_env")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # 上游 acsccid 1.1.13 未注册 CUnit 测试目标，make check 为空操作（见 reports/test-report.md）
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        self._sign_elf()

    def _sign_elf(self):
        """install 重写 rpath 会改动链接后的 ELF → 链接器自签失效，OHOS 加载报
        Permission denied。剥旧 .codesign + binary-sign-tool -selfSign 1 重签。"""
        hnp = "/data/service/hnp/bin"
        objcopy = os.path.join(hnp, "llvm-objcopy")
        signer = os.path.join(hnp, "binary-sign-tool")
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            self.output.warning("binary-sign-tool/llvm-objcopy 不可用，跳过 ELF 重签")
            return
        elfs = []
        for pat in ("lib/pcsc/drivers/**/*.so", "lib/pcsc/drivers/**/*.so.*", "bin/*"):
            elfs += glob.glob(os.path.join(self.package_folder, pat), recursive=True)
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
        # IFD 驱动 bundle 由 pcscd 在运行期 dlopen，无常规 -l 链接入口
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["lib/pcsc/drivers"]
