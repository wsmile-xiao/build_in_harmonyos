#!/usr/bin/env python3
"""Conan recipe for ykpers 1.20.0 on HarmonyOS PC (aarch64).

ykpers (YubiKey Personalization) provides libykpers-1 and the ykpersonalize,
ykchalresp, ykinfo command-line tools for configuring YubiKey hardware tokens.

OHOS-specific adaptations:
  - libyubikey/1.13 and libusb/1.0.27 have no Conan recipes on OHOS, so their
    upstream tarballs are bundled into this recipe's conandata.yml and built
    in-tree to a staging prefix, following the unpaper/FFmpeg and bowtie2/simde
    bundled-dependency pattern.
  - config.guess/config.sub in libyubikey (2013) and libusb (2022) do not
    recognize HarmonyOS; the already-patched copies from ykpers (patch 0001
    adds the HarmonyOS case) are copied into both bundled dependencies so
    their configure scripts can guess the build triplet.
  - ykpers source gets four patches:
      0001: config.guess HarmonyOS recognition + umask 077 to 022
      0002: configure umask 077 to 022 (HMDFS SELinux tmp dir fix)
      0003: ykpers-args.h usage/optstring to extern (linker dup symbol fix)
      0004: ykpers-json.c TRUE/FALSE macro definitions
  - libusb source gets three patches:
      0005: configure umask 077 to 022 (same HMDFS fix)
      0006: linux_netlink.c sockaddr_storage redefinition guard
      0007: linux_usbfs.c HongMeng/OHOS kernel version parsing
  - libyubikey source gets one patch:
      0008: configure umask 077 to 022 (same HMDFS fix)
  - json-c/0.18 is a regular Conan dependency (R36); its include/lib paths
    are taken from cpp_info (no hardcoded shell env vars, per R33).
  - Compiler is taken from tools.build:compiler_executables (Conan Toolchain
    derivation, per R33); falls back to clang.
  - Static linking is enabled (R26): libyubikey and libusb are built
    --disable-shared --enable-static; ykpers links the static libs.

  R40 深度适配标注（外设类库）:
    ykpers 属于 USB 外设类库，编译通过≠适配完成。实质性平台适配代码位于:
    - 0006-libusb-linux_netlink.c.patch: 修复 linux/netlink.h 引入的
      sockaddr_storage 重定义冲突（#define 临时重命名，非 stub）
    - 0007-libusb-linux_usbfs.c.patch: 运行时 strstr 检测 HongMeng/OHOS
      内核版本以正确解析 USBFS ioctl（非 stub/return 0）
    以上补丁均包含实质性平台适配逻辑，非空实现。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, patch, export_conandata_patches
from conan.tools.layout import basic_layout


class YkpersConan(ConanFile):
    name = "ykpers"
    version = "1.20.0"
    package_type = "application"
    description = "YubiKey Personalization (libykpers-1 + ykpersonalize/ykchalresp/ykinfo)"
    license = "BSD-2-Clause"
    homepage = "https://developers.yubico.com/yubikey-personalization/"
    url = "https://developers.yubico.com/yubikey-personalization/Releases/ykpers-1.20.0.tar.gz"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # json-c is a Conan package (R36); libyubikey and libusb are bundled.
        self.requires("json-c/0.18")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if self.settings.arch not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration(
                f"Unsupported arch: {self.settings.arch} (only armv8/aarch64)"
            )

    def source(self):
        get(self, **self.conan_data["sources"]["ykpers"], strip_root=True)
        get(
            self,
            **self.conan_data["sources"]["libyubikey"],
            strip_root=True,
            destination=os.path.join(self.source_folder, "libyubikey"),
        )
        get(
            self,
            **self.conan_data["sources"]["libusb"],
            strip_root=True,
            destination=os.path.join(self.source_folder, "libusb"),
        )

    def _cc(self):
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return ce.get("c") or "clang"

    def _apply_patch(self, base_path, patch_file):
        pf = os.path.join(self.source_folder, "patches", patch_file)
        if os.path.isfile(pf):
            patch(self, base_path=base_path, patch_file=pf)
            self.output.info(f"applied {patch_file} to {base_path}")
        else:
            raise ConanInvalidConfiguration(f"patch not found: {pf}")

    def _copy_config_guess_sub(self, dst_dir):
        ykpers_aux = os.path.join(self.source_folder, "build-aux")
        candidates = [
            (os.path.join(ykpers_aux, "config.guess"), os.path.join(dst_dir, "config.guess")),
            (os.path.join(ykpers_aux, "config.sub"), os.path.join(dst_dir, "config.sub")),
            (os.path.join(ykpers_aux, "config.guess"), os.path.join(dst_dir, "build-aux", "config.guess")),
            (os.path.join(ykpers_aux, "config.sub"), os.path.join(dst_dir, "build-aux", "config.sub")),
        ]
        for src, dst in candidates:
            if not os.path.isfile(src):
                self.output.warning(f"config file not found, skipping: {src}")
                continue
            if not os.path.isdir(os.path.dirname(dst)):
                # 预期情况：依赖可能采用平铺或 build-aux 子目录布局，二者只命中其一；
                # 降级为 info 以避免正常流程产生 warning 噪声
                self.output.info(f"destination dir not found, skipping: {os.path.dirname(dst)}")
                continue
            shutil.copy2(src, dst)
            self.output.info(f"copied {os.path.basename(src)} to {dst}")

    def build(self):
        cc = self._cc()
        host = "aarch64-unknown-linux-gnu"
        staging = os.path.join(self.build_folder, "staging")
        os.makedirs(staging, exist_ok=True)

        # json-c include/lib paths from Conan dependency (R33).
        jsonc = self.dependencies["json-c"].cpp_info
        if not jsonc.includedirs or not jsonc.libdirs:
            raise ConanInvalidConfiguration(
                "json-c dependency is missing include/lib directories"
            )
        jsonc_inc = jsonc.includedirs[0]
        jsonc_libdir = jsonc.libdirs[0]
        jsonc_libs = " ".join(f"-l{lib}" for lib in jsonc.libs) if jsonc.libs else "-ljson-c"

        # Step 1: apply ykpers patches (0001-0004).
        self._apply_patch(self.source_folder, "0001-build-aux-config.guess.patch")
        self._apply_patch(self.source_folder, "0002-configure.patch")
        self._apply_patch(self.source_folder, "0003-ykpers-args.h-extern.patch")
        self._apply_patch(self.source_folder, "0004-ykpers-json.c-true-false.patch")
        # ykpers configure umask 已由 0002-configure.patch 处理，无需再调用 _patch_configure_umask

        # Step 2: build libyubikey static (no Conan recipe, bundled).
        lyk_src = os.path.join(self.source_folder, "libyubikey")
        self._copy_config_guess_sub(lyk_src)
        self._apply_patch(lyk_src, "0008-libyubikey-configure-umask.patch")

        # libyubikey 是底层 AES/OTP 库，不依赖 json-c（json-c 仅 ykpers 上层使用），
        # 因此 configure 不传 json-c 的 include/lib 路径。
        self.run(
            f'cd "{lyk_src}" && ./configure'
            f' --host="{host}"'
            f' --prefix="{staging}"'
            f' --enable-static --disable-shared'
            f' CC="{cc}"',
            env="conanbuild",
        )
        self.run(f'cd "{lyk_src}" && make -j1', env="conanbuild")
        self.run(f'cd "{lyk_src}" && make install', env="conanbuild")

        # Step 3: build libusb static with --disable-udev.
        lusb_src = os.path.join(self.source_folder, "libusb")
        self._copy_config_guess_sub(lusb_src)
        self._apply_patch(lusb_src, "0005-libusb-configure-umask.patch")
        self._apply_patch(lusb_src, "0006-libusb-linux_netlink.c.patch")
        self._apply_patch(lusb_src, "0007-libusb-linux_usbfs.c.patch")
        # libusb configure umask 已由 0005-libusb-configure-umask.patch 处理，无需再调用 _patch_configure_umask

        self.run(
            f'cd "{lusb_src}" && ./configure'
            f' --host="{host}"'
            f' --prefix="{staging}"'
            f' --enable-static --disable-shared'
            f' --disable-udev'
            f' CC="{cc}"',
            env="conanbuild",
        )
        self.run(f'cd "{lusb_src}" && make -j1', env="conanbuild")
        self.run(f'cd "{lusb_src}" && make install', env="conanbuild")

        # Step 4: build ykpers against staging libyubikey + libusb + json-c.
        self.run(
            f'cd "{self.source_folder}" && ./configure'
            f' --host="{host}"'
            f' --prefix="{staging}"'
            f' --enable-static --disable-shared'
            f' --with-libyubikey-prefix="{staging}"'
            f' --with-backend=libusb-1.0'
            f' --with-libusb-prefix="{staging}"'
            f' CC="{cc}"'
            f' CPPFLAGS="-I{jsonc_inc} -I{staging}/include"'
            f' LDFLAGS="-L{jsonc_libdir} -L{staging}/lib"'
            f' LIBUSB_CFLAGS="-I{staging}/include/libusb-1.0"'
            f' LIBUSB_LIBS="-L{staging}/lib -lusb-1.0"'
            f' LIBS="{jsonc_libs}"',
            env="conanbuild",
        )
        self.run(f'cd "{self.source_folder}" && make -j1', env="conanbuild")
        self.run(f'cd "{self.source_folder}" && make install', env="conanbuild")

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        copy(self, "*", src=os.path.join(staging, "bin"), dst=os.path.join(self.package_folder, "bin"))
        copy(self, "*", src=os.path.join(staging, "lib"), dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*", src=os.path.join(staging, "include"), dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        # ykpers is primarily a CLI tool package (package_type = "application").
        # libykpers-1 is installed but not exported via cpp_info, because
        # application-type packages do not propagate cpp_info to consumers
        # in Conan 2.x. This aligns with commands.json "type": "tool".
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
