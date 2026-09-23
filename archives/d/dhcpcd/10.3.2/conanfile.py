#!/usr/bin/env python3
"""Conan recipe — dhcpcd 10.3.2 (autotools, C).

RFC2131 DHCP client daemon (Roy Marples). Zero external deps — libc only;
optional --with-dns/--with-ssl/--with-libpcap are disabled by default.

OHOS adaptation notes:
- autotools: config.guess/config.sub OHOS patch (scamp/cif-api pattern).
- OHOS umask 077 (E011): configure/config.status tmp dir 700 perms on hmdfs
  -> patch umask + mkdir -p -m 755 (cloog/dfu pattern).
- Runtime: DHCP negotiation needs network; test_package verifies
  `dhcpcd --version` / interface listing.
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DhcpcdConan(ConanFile):
    name = "dhcpcd"
    version = "10.3.2"
    description = "RFC2131 compliant DHCP client daemon"
    license = "BSD-2-Clause"
    homepage = "https://roy.marples.name/projects/dhcpcd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # dhcpcd 是 in-source 构建：configure 生成 config.h/config.mk 到源码目录，
        # Makefile 也在源码根（非标准 out-of-source autotools）——build 与 source 同目录
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        # 裁剪可选依赖（默认关闭，确保零外部依赖构建）
        tc.configure_args.append("--disable-dhcp6")  # 可选：IPv6 支持
        # OHOS sysroot 头冲突：sys/socket.h 用 `#ifndef __MUSL__` 保护
        # sockaddr_storage，但 OHOS 编译未定义 __MUSL__ → sys/socket.h 先定义、
        # 随后 linux/socket.h 再定义 → redefinition。注入 -D__MUSL__ 让
        # sys/socket.h 跳过该定义（linux/socket.h 保留一份）。
        tc.extra_cflags.append("-D__MUSL__")
        tc.extra_cxxflags.append("-D__MUSL__")
        tc.generate()
        # autoconf $ac_tmp 落 /tmp（OHOS 只读）→ build_folder（cloog/dfu 同款）
        env = Environment()
        env.define("TMPDIR", self.build_folder)
        envvars = env.vars(self)
        envvars.save_script("conantmpdir")

    def build(self):
        apply_conandata_patches(self)
        self._patch_ohos_platform()
        # 清理前次失败残留的 conf* 临时目录（umask 077 建 700 权限写不进）
        for stale in glob.glob(os.path.join(self.build_folder, "conf*")):
            if os.path.isdir(stale):
                shutil.rmtree(stale, ignore_errors=True)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def _patch_ohos_platform(self):
        """config.guess/config.sub OHOS 识别 + configure umask 077 修复（E011）。"""
        import os as _os
        cfg = _os.path.join(self.source_folder, "configure")
        if _os.path.isfile(cfg):
            ctext = open(cfg, encoding="utf-8", errors="ignore").read()
            if "umask 000" not in ctext:
                nl = ctext.find("\n")
                ctext = ctext[:nl+1] + "umask 000\n" + ctext[nl+1:]
                changed = True
            else:
                changed = False
            old_mkt = '(umask 077 && mktemp -d "./confXXXXXX")'
            if old_mkt in ctext:
                ctext = ctext.replace(old_mkt, '(umask 000 && mktemp -d "./confXXXXXX")')
                changed = True
            if changed:
                with open(cfg, "w") as f:
                    f.write(ctext)
                self.output.info("patched configure: umask 077->000 (E011 hmdfs tmp dir)")
        for name in ("config.guess", "config.sub"):
            path = _os.path.join(self.source_folder, name)
            if not _os.path.isfile(path):
                continue
            text = open(path, encoding="utf-8", errors="ignore").read()
            changed = False
            if name == "config.sub":
                old1 = "| nsk* | powerunix* | genode* | zvmoe* | qnx* | emx* | zephyr*)"
                if old1 in text and "ohos*)" not in text:
                    text = text.replace(old1, old1.replace("zephyr*)", "zephyr* \\\n\t     | ohos*)"), 1)
                    changed = True
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
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["sbin"]
        self.cpp_info.libs = []
