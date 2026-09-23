#!/usr/bin/env python3
"""Conan recipe — dfu-util 0.11 (autotools, C).

Device Firmware Upgrade Utilities — host-side USB DFU programmer
(produces CLI tools: dfu-util, dfu-suffix, dfu-prefix).

OHOS adaptation notes:
- Dep: libusb/1.0.27 (ohpcd) — configure uses PKG_CHECK_MODULES(USB libusb-1.0).
- autotools OHOS platform: config.guess/config.sub inline patch (scamp/cif-api
  pattern) + explicit --host=aarch64-unknown-linux-ohos.
- Runtime: needs a USB DFU device (absent on OHOS) — test_package verifies
  CLI --version / -l (list, no-device is fine), device interaction is
  declared per rule 1.2.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps


class DfuUtilConan(ConanFile):
    name = "dfu"
    version = "0.11"
    description = "DFU-util - Device Firmware Upgrade Utilities (USB DFU programmer)"
    license = "GPL-2.0-or-later"
    homepage = "https://dfu-util.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libusb-1.0（ohpcd 已发布，gusb 同款依赖）
        self.requires("libusb/1.0.27", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # libusb-1.0 的 .pc（PkgConfigDeps 生成，PKG_CHECK_MODULES(USB libusb-1.0) 命中）
        PkgConfigDeps(self).generate()
        self.buildenv_info.append_path("PKG_CONFIG_PATH", self.generators_folder)
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.generate()
        # autoconf 的 $ac_tmp 临时目录默认落在 /tmp（OHOS 只读）→ 指向 build_folder
        # （cloog 同款方案，config.status 写 subs1.awk 不再 Permission denied）
        env = Environment()
        env.define("TMPDIR", self.build_folder)
        envvars = env.vars(self)
        envvars.save_script("conantmpdir")
        # 注入 libusb 的 include/lib（PKG_CHECK_MODULES 需要 pkg-config 能找到）
        for _n, dep in self.dependencies.items():
            if str(dep.ref.name) == "libusb":
                for p in dep.cpp_info.includedirs:
                    tc.extra_cflags.append("-I" + p)
                for p in dep.cpp_info.libdirs:
                    tc.extra_ldflags.append("-L" + p)

    def build(self):
        apply_conandata_patches(self)
        self._patch_ohos_platform()
        # 清理前次失败残留的 conf* 临时目录（umask 077 时创建的 700 权限目录，
        # config.status 复用时会写不进去 → subs1.awk: Permission denied）
        import glob
        for stale in glob.glob(os.path.join(self.build_folder, "conf*")):
            if os.path.isdir(stale):
                import shutil as _sh
                _sh.rmtree(stale, ignore_errors=True)
                self.output.info(f"removed stale tmp dir: {os.path.basename(stale)}")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def _patch_ohos_platform(self):
        """config.guess/config.sub 识别 OHOS（scamp/cif-api 同款模式）。
        另：OHOS umask 077 持久（E011）→ configure 脚本开头注入 umask 000，
        使 configure 生成的 config.status 创建 conf$$ 临时目录权限宽松
        （否则 subs1.awk: Permission denied）。"""
        import os as _os
        cfg = _os.path.join(self.source_folder, "configure")
        if _os.path.isfile(cfg):
            ctext = open(cfg, encoding="utf-8", errors="ignore").read()
            if "umask 000" not in ctext:
                # 插到 #! 行之后
                nl = ctext.find("\n")
                ctext = ctext[:nl+1] + "umask 000\n" + ctext[nl+1:]
                changed_cfg = True
            else:
                changed_cfg = False
            # 关键：configure（及其生成的 config.status）用 `(umask 077 && mktemp -d)`
            # 创建 700 权限临时目录——hmdfs 上写文件被拒（subs1.awk: Permission denied）。
            # 把显式 umask 077 改为 000（cloog/cif-api HMDFS patch 同款思路）
            old_mkt = '(umask 077 && mktemp -d "./confXXXXXX")'
            if old_mkt in ctext:
                ctext = ctext.replace(old_mkt, '(umask 000 && mktemp -d "./confXXXXXX")')
                changed_cfg = True
            if changed_cfg:
                with open(cfg, "w") as f:
                    f.write(ctext)
                self.output.info("patched configure: umask 077->000 in mktemp tmp dir + inject umask 000")
        for name in ("config.guess", "config.sub"):
            path = _os.path.join(self.source_folder, name)
            if not _os.path.isfile(path):
                continue
            text = open(path, encoding="utf-8", errors="ignore").read()
            changed = False
            if name == "config.sub":
                # OS 合法性列表加 ohos
                old1 = "| nsk* | powerunix* | genode* | zvmoe* | qnx* | emx* | zephyr*)"
                if old1 in text and "ohos*)" not in text:
                    text = text.replace(old1, old1.replace("zephyr*)", "zephyr* \\\n\t     | ohos*)"), 1)
                    changed = True
                # kernel-os 验证加 linux-ohos
                old2 = "linux-gnu* | linux-dietlibc* | linux-android* | linux-newlib* \\\n\t\t   | linux-musl* | linux-relibc* | linux-uclibc* )"
                if old2 in text and "linux-ohos*" not in text:
                    text = text.replace(old2, old2.replace("linux-uclibc* )", "linux-uclibc* | linux-ohos* )"), 1)
                    changed = True
            else:  # config.guess
                old3 = "    aarch64:Linux:*:*)\n\tGUESS=$UNAME_MACHINE-unknown-linux-$LIBC\n\t;;"
                new3 = "    aarch64:Linux:*:*)\n\tcase `uname` in\n\t  *OHOS*) GUESS=$UNAME_MACHINE-unknown-linux-ohos ;;\n\t  *) GUESS=$UNAME_MACHINE-unknown-linux-$LIBC ;;\n\tesac\n\t;;"
                if old3 in text and "OHOS" not in text:
                    text = text.replace(old3, new3, 1)
                    changed = True
            if changed:
                with open(path, "w") as f:
                    f.write(text)
                self.output.info(f"patched {name}: OHOS platform recognition")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
