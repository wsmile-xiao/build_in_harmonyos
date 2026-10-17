#!/usr/bin/env python3
"""Conan recipe for cpufrequtils 008 — CPU frequency scaling tools for HarmonyOS PC.

上游形态（本机解包实测）：顶层 5 个 Makefile 的**纯 make** 工程（非 autotools、
非 cmake），源码树 56 条目；`make all` 产出 `libcpufreq.so.0.0.0` +
`cpufreq-info` / `cpufreq-set` / `cpufreq-aperf` 三个工具。

本配方相对上游的四处适配（证据与逐条实测见 notes.md / manifest.yaml）：

1. **空壳 `<libintl.h>` + 链接桩无 gettext** —— OHOS sysroot 的 libintl.h 只有
   353 B、零函数声明，clang 15 把随后的 `-Wint-conversion` 判 error；SDK 的链接桩
   libc.so（1592 符号）也不导出 gettext/textdomain ⇒ 生成一份按 musl 公开声明的
   私有 libintl.h 前置进 include 搜索路径，并从系统 musl
   （`/lib/ld-musl-aarch64.so.1`，SONAME libc.so）取**真实** gettext 符号。
2. **本机（OHOS/鸿蒙）没有 `install` 二进制** ⇒ 不跑 `make install`，由
   `package()` 按上游 install 布局手工拷贝（E098 的 cp+chmod 口径）。
3. **`cpufreq-aperf` 是 x86 专用**（`utils/cpuid.h` 的 `cpuid` 内联汇编带
   `"=a"` 约束 + 读 `MSR_IA32_APERF/MPERF`）⇒ aarch64 不构建、不打包。
4. **签名顺序** —— 上游 `STRIPCMD`（`llvm-strip -s`）会连 `.codesign` 段一起剥掉，
   被剥掉 `.codesign` 的 ELF 在 OHOS 上 exec 直接 EACCES(126) ⇒ `package()`
   先 strip 后 `objcopy --remove-section .codesign` + `binary-sign-tool` 重签 + chmod。
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get, save
from conan.tools.layout import basic_layout


# OHOS musl sysroot 的 <libintl.h> 是空壳（只留 __USE_GNU_GETTEXT /
# __GNU_GETTEXT_SUPPORTED_REVISION 两个宏，零函数声明），见模块 docstring。
# 下面按 musl libc 公开的 <libintl.h> 逐字补齐声明；只加声明、不改语义，
# 且只作用于本配方（-I 私有目录前置于 sysroot），不改 sysroot、不改上游源码。
LIBINTL_HEADER = """\
#ifndef _LIBINTL_H
#define _LIBINTL_H
#ifdef __cplusplus
extern "C" {
#endif

#define __USE_GNU_GETTEXT 1
#define __GNU_GETTEXT_SUPPORTED_REVISION(major) ((major) == 0 ? 1 : -1)

char *gettext(const char *);
char *dgettext(const char *, const char *);
char *dcgettext(const char *, const char *, int);
char *ngettext(const char *, const char *, unsigned long);
char *dngettext(const char *, const char *, const char *, unsigned long);
char *dcngettext(const char *, const char *, const char *, unsigned long, int);
char *textdomain(const char *);
char *bindtextdomain(const char *, const char *);
char *bind_textdomain_codeset(const char *, const char *);

#ifdef __cplusplus
}
#endif
#endif /* _LIBINTL_H */
"""


class CpufrequtilsConan(ConanFile):
    name = "cpufrequtils"
    version = "008"
    description = ("libcpufreq plus the cpufreq-info / cpufreq-set command line "
                   "tools for reading and setting CPU frequency scaling policies")
    license = "GPL-2.0-or-later"
    homepage = "http://www.kernel.org/pub/linux/utils/kernel/cpufreq/cpufrequtils.html"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 库 + CLI 混合包必须声明为 library（否则 package_info() 对消费者不生效），
    # CLI 侧按 R38 另交软件级 commands.json。
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        # 无补丁、无源外文件（经验库 12.54：无 patches 时为 no-op）；
        # 私有 libintl.h 由 build() 现场生成，见模块 docstring 第 1 条。
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "cpufrequtils targets a POSIX target (Linux or OHOS)")
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "the upstream Makefile only builds the shared libcpufreq "
                "(libcpufreq.so.$(LIB_MAJ)); a static build is not supported")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        ranlib = compilers.get("ranlib", "llvm-ranlib")
        strip = compilers.get("strip", "llvm-strip")

        # 私有 include 目录：把补齐声明的 libintl.h 放在 sysroot 之前。
        compat_dir = os.path.join(self.build_folder, "ohos-compat-include")
        save(self, os.path.join(compat_dir, "libintl.h"), LIBINTL_HEADER)

        cppflags = "-I" + compat_dir
        ldflags = ""
        if str(self.settings.os) == "OHOS":
            # SDK 链接桩 libc.so 不导出 gettext/textdomain；系统 musl loader
            # （SONAME libc.so）导出。取真实符号，不引入 conan 依赖、不用桩函数。
            ldflags = "-L/lib -l:ld-musl-aarch64.so.1"

        # 只构建 aarch64 适用的两个工具：cpufreq-aperf 是 x86 专用
        # （utils/cpuid.h 的 "=a" 约束 + MSR_IA32_APERF/MPERF），aarch64 编不过。
        # V=true 关掉上游 build/ccdv 包装器（省掉在构建树里先执行一个新链接的
        # 宿主 ELF），同时让 CI 日志逐条可见；NLS=false 去掉对 xgettext/msgfmt
        # 宿主工具的依赖（运行时本就没有消息目录，输出与 NLS 关闭逐字一致）。
        cmd = (
            'CPPFLAGS="{cpp}" LDFLAGS="{ld}" make '
            'V=true NLS=false '
            'CC="{cc}" HOSTCC="{cc}" AR="{ar}" RANLIB="{ranlib}" STRIP="{strip}" '
            'cpufreq-info cpufreq-set'
        ).format(cpp=cppflags, ld=ldflags, cc=cc, ar=ar, ranlib=ranlib, strip=strip)

        self.run(cmd, cwd=self.source_folder)

    def _sign_ohos_elf(self, path):
        """OHOS ELF 必须带 .codesign 才允许 exec；签名前先摘掉残留占位段。"""
        if str(self.settings.os) != "OHOS":
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise ConanException(
                "binary-sign-tool is missing; OHOS refuses to exec unsigned ELF")
        if os.path.isfile(objcopy):
            self.run(
                '"{0}" --remove-section .codesign "{1}"'.format(objcopy, path),
                ignore_errors=True,
            )
        signed = path + ".signed"
        self.run('"{}" sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
            signer, path, signed))
        if not os.path.isfile(signed):
            raise ConanException("binary-sign-tool produced no output for " + path)
        os.replace(signed, path)
        os.chmod(path, 0o755)

    def package(self):
        # 上游 `make install` 依赖 `/usr/bin/install -c`，本机/CI 均无 install
        # 二进制（E098）⇒ 按上游 install 布局手工拷贝，语义等价（cp + chmod）。
        src = self.source_folder
        pf = self.package_folder

        copy(self, "COPYING", src=src,
             dst=os.path.join(pf, "licenses"), keep_path=False)
        copy(self, "README", src=src,
             dst=os.path.join(pf, "licenses"), keep_path=False)
        copy(self, "cpufreq.h", src=os.path.join(src, "lib"),
             dst=os.path.join(pf, "include"), keep_path=False)
        for tool in ("cpufreq-info", "cpufreq-set"):
            copy(self, tool, src=src, dst=os.path.join(pf, "bin"),
                 keep_path=False)
        for page in ("cpufreq-info.1", "cpufreq-set.1"):
            copy(self, page, src=os.path.join(src, "man"),
                 dst=os.path.join(pf, "share", "man", "man1"),
                 keep_path=False)

        # libcpufreq.so.0.0.0 是真实文件，两个软链由本配方重建（上游 make 已建，
        # 这里按上游命名重建以便包内容与上游 install 布局一致）。
        libdir = os.path.join(pf, "lib")
        copy(self, "libcpufreq.so.0.0.0", src=src, dst=libdir, keep_path=False)
        for link in ("libcpufreq.so", "libcpufreq.so.0"):
            link_path = os.path.join(libdir, link)
            if os.path.lexists(link_path):
                os.remove(link_path)
            os.symlink("libcpufreq.so.0.0.0", link_path)

        bindir = os.path.join(pf, "bin")
        for name in ("cpufreq-info", "cpufreq-set"):
            path = os.path.join(bindir, name)
            os.chmod(path, 0o755)
            self._sign_ohos_elf(path)
        self._sign_ohos_elf(os.path.join(libdir, "libcpufreq.so.0.0.0"))
        os.chmod(os.path.join(libdir, "libcpufreq.so.0.0.0"), 0o755)

    def package_info(self):
        self.cpp_info.libs = ["cpufreq"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        # 库包随附 CLI：VirtualRunEnv 只聚合 run=True 依赖的 cpp_info，
        # 库依赖默认 run=False ⇒ 必须显式声明 runenv_info，消费者 conanrun 才有 PATH。
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
