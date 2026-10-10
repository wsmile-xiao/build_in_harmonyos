#!/usr/bin/env python3
"""Conan recipe — libsbig 4.9.9 (SBIG Universal CCD camera driver library).

上游 indi-3rdparty 的 libsbig 子目录是「预编译二进制分发」：源码包里没有
C 源码，只有官方编译好的共享库 blob（libsbig_arm64.bin / libsbig_x64.bin /
libsbig_armhf.bin）+ 头文件 sbigudrv.h + 固件 hex。因此本配方不做任何编译
（build() 为空，R33 不适用：不裸用 ${CC}/${CFLAGS}），只按目标架构挑选对应
二进制、补齐 soname 符号链并打包。本包只产共享库、无静态变体，故
package_type 用 Conan 2 合法枚举 "shared-library"（无需声明 shared option）。

系统依赖：libsbig_arm64.bin 的 DT_NEEDED 为 libm.so.6 / libudev.so.1 /
libc.so.8。libudev 由 eudev/3.2.14（ohpcd 制品仓已发布，W0/R36 已验证
conan download 通过）提供，声明为 recipe 依赖传递给消费者。

OHOS 适配（沿用 systemd 261.1 同款做法）：
- 预编译 .so 在 OHOS 设备上必须 ELF 签名才能 dlopen/加载（E318），
  package() 末尾用 binary-sign-tool 自签名（工具存在才签，方法内 guard）。
- 固件 hex 装到 res/sbig（不写系统 /lib/firmware）。
- 上游无任何测试（清点证据见 notes.md / test_package/MANIFEST.yml）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy


class LibsbigConan(ConanFile):
    name = "libsbig"
    version = "4.9.9"
    description = "SBIG Universal CCD camera driver library (prebuilt shared library + header + firmware)"
    license = "LicenseRef-Proprietary-SBIG-Binary"
    homepage = "https://github.com/indilib/indi-3rdparty/tree/main/libsbig"
    url = ""  # CI fills this

    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # libsbig_arm64.bin DT_NEEDED: libudev.so.1（USB 相机后端）。
        # eudev/3.2.14 已发布到 ohpcd 制品仓（conan download --only-recipe 验证通过）。
        self.requires("eudev/3.2.14")

    def layout(self):
        # 无构建步骤，basic_layout 即可（src_folder=. 与归档惯例一致）
        from conan.tools.layout import basic_layout
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 上游为预编译二进制分发，无源码可编译。
        # 选择的二进制随 arch 在 package() 落位。
        pass

    def _pick_blob(self):
        # 上游 CMakeLists.txt 的选择逻辑：aarch64 -> libsbig_arm64.bin，
        # x86_64 -> libsbig_x64.bin（armhf/armv7 blob 不在本配方支持范围）。
        blobs = {
            "armv8": "libsbig_arm64.bin",
            "x86_64": "libsbig_x64.bin",
        }
        arch = str(self.settings.arch)
        if arch not in blobs:
            from conan.errors import ConanInvalidConfiguration
            raise ConanInvalidConfiguration(
                f"libsbig 4.9.9 仅提供 armv8(aarch64)/x86_64 预编译库，收到 arch='{arch}'"
            )
        return blobs[arch]

    def package(self):
        src = self.source_folder
        libdir = os.path.join(self.package_folder, "lib")
        os.makedirs(libdir, exist_ok=True)

        blob = self._pick_blob()
        real = os.path.join(libdir, "libsbig.so.4.9.9")
        shutil.copy2(os.path.join(src, blob), real)
        os.chmod(real, 0o755)
        # 上游 CMake: VERSION 4.9.9 / SOVERSION 4；补齐 soname 符号链，
        # 使 -lsbig 与运行时 liblibsbig.so.4 均可解析。
        for link, target in (("libsbig.so.4", "libsbig.so.4.9.9"),
                             ("libsbig.so", "libsbig.so.4")):
            lp = os.path.join(libdir, link)
            if not os.path.islink(lp):
                os.symlink(target, lp)

        # 头文件（上游姭装到… include/libsbig/sbigudrv.h ）
        inc = os.path.join(self.package_folder, "include", "libsbig")
        os.makedirs(inc, exist_ok=True)
        shutil.copy2(os.path.join(src, "sbigudrv.h"), os.path.join(inc, "sbigudrv.h"))

        # 固件（上游装 /lib/firmware；conan 包内放 res/sbig，不写系统目录）
        res = os.path.join(self.package_folder, "res", "sbig")
        os.makedirs(res, exist_ok=True)
        for fw in ("sbigucam.hex", "sbiglcam.hex", "sbigfcam.hex",
                   "sbigpcam.hex", "stfga.bin"):
            copy(self, fw, src, res)

        # 许可证（二进制再分发条款）+ udev 规则样例（文档化，不装系统目录）
        lic = os.path.join(self.package_folder, "licenses")
        os.makedirs(lic, exist_ok=True)
        copy(self, "LICENSE.firmware", src, lic)
        copy(self, "51-sbig-debian.rules", src, res)
        copy(self, "libsbig.spec", src, lic)

        # CI：OHOS 拒绝加载未签名 .so——test_package 的 dlopen/链接运行报
        # "Permission denied"（E318 同类）。与 systemd 261.1 同款：工具存在
        # 即自签名，工具缺失则跳过（方法内 guard，不依赖 settings.os 判定）。
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        import glob as _glob
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.info("libsbig: binary-sign-tool not found, skip signing")
            return
        for target in sorted(_glob.glob(os.path.join(self.package_folder,
                                                     "lib", "libsbig.so*"))):
            if os.path.islink(target):
                continue
            self.run(f'{objcopy} --remove-section .codesign "{target}" '
                     f'2>/dev/null || true')
            self.run(f'{signer} sign -inFile "{target}" -outFile "{target}" '
                     f'-selfSign 1')

    def package_info(self):
        self.cpp_info.libs = ["sbig"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include/libsbig"]
        self.cpp_info.set_property("cmake_file_name", "libsbig")
        self.cpp_info.set_property("cmake_target_name", "libsbig::libsbig")
        # 预编译 blob 自带 DT_NEEDED libm.so.6（libudev.so.1 由 eudev
        # recipe 依赖在 conan 图里传递提供）。
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]

