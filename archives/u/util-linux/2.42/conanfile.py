#!/usr/bin/env python3
"""Conan recipe — util-linux 2.42 (autotools, C).

Linux system utilities (kernel.org). Following main's 2.39 notes approach:
only build libblkid/libuuid/libmount (--disable-all-programs +
--enable-libblkid/libuuid/libmount), disabling all tools/programs.

OHOS adaptation notes:
- autotools: config.guess/config.sub OHOS patch (scamp/cif-api pattern).
- OHOS umask 077 (E011): configure/config.status tmp dir 700 perms on hmdfs
  -> patch umask + mkdir -p -m 755 (cloog/dfu pattern).
- Optional deps (selinux/ncurses/readline) are auto-detected; keep libs only.
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UtilLinuxConan(ConanFile):
    name = "util-linux"
    version = "2.42"
    description = "Linux system utilities (libblkid/libuuid/libmount)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.kernel.org/pub/linux/utils/util-linux/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._patch_compat_getusershell()
        self._patch_compat_versionsort()

    def _patch_compat_versionsort(self):
        """OHOS musl 无 versionsort（GNU scandir 版本排序扩展）——libmount/src/
        tab_parse.c 的 scandir(scandirat) 用它排序。写 compat 头（strverscmp 可用则
        用它否则 strcmp 的版本排序），patch tab_parse.c 包含。"""
        hdr_dir = os.path.join(self.source_folder, "include")
        compat = """/* OHOS compat: versionsort() absent in musl (GNU scandir sort ext).
 * strverscmp may also be missing — fall back to strcmp. */
#ifndef _OHOS_COMPAT_VERSIONSORT_H
#define _OHOS_COMPAT_VERSIONSORT_H
#include <dirent.h>
#include <string.h>
#if defined(__GLIBC__) && !defined(__MUSL__)
/* real glibc already provides it */
#else
static inline int __ohos_versionsort(const struct dirent **a, const struct dirent **b) {
    return strcmp((*a)->d_name, (*b)->d_name);
}
#define versionsort __ohos_versionsort
#endif
#endif
"""
        with open(os.path.join(hdr_dir, "versionsort.h"), "w") as f:
            f.write(compat)
        path = os.path.join(self.source_folder, "libmount", "src", "tab_parse.c")
        if os.path.isfile(path):
            text = open(path, encoding="utf-8", errors="ignore").read()
            if '#include "versionsort.h"' not in text:
                text = text.replace('#include <dirent.h>',
                                    '#include <dirent.h>\n#include "versionsort.h"', 1)
                open(path, "w", encoding="utf-8").write(text)
                self.output.info("patched libmount/src/tab_parse.c: compat versionsort")

    def _patch_compat_getusershell(self):
        """OHOS libc 无 getusershell/setusershell/endusershell（glibc/musl 的
        /etc/shells 读取 API，符号与头声明均缺失）→ configure 检测 HAVE_GETUSERSHELL
        失败，lib/shells.c 的 getusershell() 隐式 int 声明报类型错误。
        写 compat 头（读 /etc/shells，文件不存在返回 NULL 即循环结束），
        patch lib/shells.c 包含它。"""
        hdr_dir = os.path.join(self.source_folder, "include")
        os.makedirs(hdr_dir, exist_ok=True)
        compat = """/* OHOS compat: getusershell()/setusershell()/endusershell() absent in
 * OHOS libc (glibc/musl read /etc/shells API). Minimal stand-in reading
 * /etc/shells; returns NULL when file absent (loop naturally ends). */
#ifndef _OHOS_COMPAT_GETUSERSHELL_H
#define _OHOS_COMPAT_GETUSERSHELL_H
#include <stdio.h>
#include <string.h>
static FILE *__ohos_shells_fp;
static char __ohos_shells_buf[256];
static inline void setusershell(void) {
    if (__ohos_shells_fp) fclose(__ohos_shells_fp);
    __ohos_shells_fp = fopen("/etc/shells", "r");
}
static inline char *getusershell(void) {
    if (!__ohos_shells_fp) return NULL;
    while (fgets(__ohos_shells_buf, sizeof(__ohos_shells_buf), __ohos_shells_fp)) {
        size_t l = strlen(__ohos_shells_buf);
        while (l && (__ohos_shells_buf[l-1] == '\\n' || __ohos_shells_buf[l-1] == '\\r'))
            __ohos_shells_buf[--l] = '\\0';
        if (l == 0 || __ohos_shells_buf[0] == '#') continue;
        return __ohos_shells_buf;
    }
    return NULL;
}
static inline void endusershell(void) {
    if (__ohos_shells_fp) { fclose(__ohos_shells_fp); __ohos_shells_fp = NULL; }
}
#endif
"""
        with open(os.path.join(hdr_dir, "getusershell.h"), "w") as f:
            f.write(compat)
        # patch lib/shells.c：<unistd.h> 之后包含 compat 头
        path = os.path.join(self.source_folder, "lib", "shells.c")
        if os.path.isfile(path):
            text = open(path, encoding="utf-8", errors="ignore").read()
            if '#include "getusershell.h"' not in text:
                text = text.replace('#include <unistd.h>',
                                    '#include <unistd.h>\n#include "getusershell.h"', 1)
                open(path, "w", encoding="utf-8").write(text)
                self.output.info("patched lib/shells.c: compat getusershell")
        # 强制 HAVE_GETUSERSHELL（compat 提供符号，configure 检测绕过）
        cfg = os.path.join(self.source_folder, "configure")
        if os.path.isfile(cfg):
            ctext = open(cfg, encoding="utf-8", errors="ignore").read()
            if "ac_cv_func_getusershell=yes" not in ctext:
                nl = ctext.find("\n")
                ctext = ctext[:nl+1] + "ac_cv_func_getusershell=yes\n" + ctext[nl+1:]
                open(cfg, "w", encoding="utf-8").write(ctext)
                self.output.info("patched configure: force ac_cv_func_getusershell=yes")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        # 沿用 2.39 裁剪：只编三个库，禁用所有工具/程序
        tc.configure_args.append("--disable-all-programs")
        tc.configure_args.append("--enable-libblkid")
        tc.configure_args.append("--enable-libuuid")
        tc.configure_args.append("--enable-libmount")
        tc.configure_args.append("--disable-pam")
        tc.configure_args.append("--disable-libudev")
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
        autotools.make(args=["-j4"])

    def _patch_ohos_platform(self):
        """config.guess/config.sub OHOS 识别 + configure umask 077 修复（E011）。
        util-linux 的 config.guess/config.sub 在 config/ 子目录且为 2026 新版
        （config.sub os 列表含 fiwix/mlibc 等、linux 组合为 linux-xxx*- 格式、
        config.guess aarch64 用 set_cc_for_build+CPU 变量）——按新版格式 patch。"""
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
        # util-linux 的 config.guess/config.sub 在 config/ 子目录
        for name in ("config.guess", "config.sub"):
            path = _os.path.join(self.source_folder, "config", name)
            if not _os.path.isfile(path):
                path = _os.path.join(self.source_folder, name)
            if not _os.path.isfile(path):
                continue
            text = open(path, encoding="utf-8", errors="ignore").read()
            changed = False
            if name == "config.sub":
                # OS 合法性列表加 ohos（新版含 fiwix/mlibc/cos/mbr/ironclad）
                # 注意：插入行必须带 `\` 续行符，否则破坏 case 语句语法
                old1 = "| nsk* | powerunix* | genode* | zvmoe* | qnx* | emx* | zephyr* \\"
                if old1 in text and "ohos*)" not in text:
                    text = text.replace(old1, old1.replace("zephyr* \\", "zephyr* \\\n\t     | ohos* \\"), 1)
                    changed = True
                # kernel-os 验证加 linux-ohos（新版 linux-xxx*- 格式）
                old2 = "linux-gnu*- | linux-android*- | linux-dietlibc*- | linux-llvm*- \\"
                if old2 in text and "linux-ohos*-" not in text:
                    text = text.replace(old2, old2.replace("linux-llvm*- \\", "linux-llvm*- | linux-ohos*- \\"), 1)
                    changed = True
            else:  # config.guess — 新版 aarch64:Linux 用 set_cc_for_build + CPU 变量
                old3 = "    aarch64:Linux:*:*)\n\tset_cc_for_build"
                if old3 in text and "OHOS" not in text:
                    new3 = ("    aarch64:Linux:*:*)\n"
                            "\tcase `uname` in\n"
                            "\t  *OHOS*) echo $UNAME_MACHINE-unknown-linux-ohos ; exit ;;\n"
                            "\tesac\n"
                            "\tset_cc_for_build")
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
        self.cpp_info.libs = ["blkid", "uuid", "mount"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []  # 只编库，无 bin
