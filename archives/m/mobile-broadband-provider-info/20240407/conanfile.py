#!/usr/bin/env python3
"""Conan recipe for mobile-broadband-provider-info 20240407.

Data-only package: ships the mobile broadband service provider database
(serviceproviders.xml + serviceproviders.2.dtd + xsltproc-generated
apns-conf.xml) and a data-only pkg-config file. No C/C++ artifact is
produced — upstream meson.build declares the 'c' language but compiles
nothing (the only build step is an xsltproc custom_target), so the
recipe is package_type="unknown" with resdirs=["share"].

OHOS adaptation notes:
- MesonToolchain machine file per iso-codes 4.20.1 precedent; the
  profile provides meson/ninja/xsltproc/xmllint/grep via buildenv PATH
  (/storage/Users/currentUser/usr/local/bin + /data/service/hnp/bin).
- meson test (check-blanks + xmllint DTD validation) runs inside
  build() so the upstream suite executes on the real device.
- meson install uses prefix=/ (Conan destdir semantics for data
  packages); package() rewrites the installed .pc pkgdatadir to a
  ${pcfiledir}-relative path so on-device consumers (ModemManager,
  NetworkManager) can locate the database without a baked-in prefix.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    load,
    save,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class MobileBroadbandProviderInfoConan(ConanFile):
    name = "mobile-broadband-provider-info"
    version = "20240407"
    description = "Mobile Broadband Service Provider Information Database"
    license = "public-domain"  # upstream COPYING: public domain certification
    homepage = "https://gitlab.gnome.org/GNOME/mobile-broadband-provider-info"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "unknown"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # 上游 meson.build 声明了 'c' 语言（虽无编译产物），meson 仍会在
        # project() 做静态链接器探测；该探测子进程不走 shell PATH 搜索，
        # 本机环境下 PATH 中的 ar/llvm-ar（符号链接）会报 ENOENT。
        # 通过 machine file [binaries] 给绝对路径绕过 PATH 搜索。
        ar = shutil.which("llvm-ar") or shutil.which("ar")
        if not ar:
            # 兜底：OHOS HNP 工具链目录（与 profile compiler_executables 同源）
            for cand in ("/data/service/hnp/bin/llvm-ar", "/data/service/hnp/bin/ar"):
                if os.path.isfile(cand):
                    ar = cand
                    break
        if ar:
            tc.binaries["ar"] = ar
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cross_file = os.path.join(
            self.generators_folder, MesonToolchain.cross_filename
        )
        native_file = os.path.join(
            self.generators_folder, MesonToolchain.native_filename
        )
        if os.path.isfile(cross_file):
            machine_arg = '--cross-file "{}"'.format(cross_file)
        elif os.path.isfile(native_file):
            machine_arg = '--native-file "{}"'.format(native_file)
        else:
            raise RuntimeError("MesonToolchain did not generate a machine file")
        self.run(
            'meson setup {} "{}" "{}" --prefix=/'.format(
                machine_arg, self.build_folder, self.source_folder
            ),
            env="conanbuild",
        )
        Meson(self).build()
        self.run(
            'meson test -C "{}" --print-errorlogs --no-rebuild'.format(
                self.build_folder
            ),
            env="conanbuild",
        )

    def package(self):
        Meson(self).install()
        # --prefix=/ 配合 Conan destdir 安装（数据包无二进制，无需真实前缀）；
        # 重写 .pc 的 pkgdatadir 为 pcfiledir 相对路径，设备侧消费方才能
        # 正确定位数据库文件（避免固化 /share 绝对前缀）。
        pc = os.path.join(
            self.package_folder, "share", "pkgconfig",
            "mobile-broadband-provider-info.pc",
        )
        if os.path.isfile(pc):
            content = load(self, pc)
            content = content.replace(
                "pkgdatadir=/share/mobile-broadband-provider-info",
                "pkgdatadir=${pcfiledir}/../mobile-broadband-provider-info",
            )
            save(self, pc, content)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share"]
        self.runenv_info.append_path(
            "PKG_CONFIG_PATH",
            os.path.join(self.package_folder, "share", "pkgconfig"),
        )
