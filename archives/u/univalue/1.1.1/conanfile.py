#!/usr/bin/env python3
"""Conan recipe for univalue 1.1.1 (autotools, HarmonyOS PC / aarch64).

Build notes (task univalue-1.1.1-r01-pc1-30; E007/E072/E114/E074):
  - upstream tarball ships no generated `configure`, so build() runs
    `autoreconf -fi` first (abiword-plugin-clarisworks 同款 bootstrap);
  - config.guess/config.sub 不识别 HarmonyOS（uname -s="HarmonyOS"）：
    build() 内联等价 patch-autotools-ohos.pl 的五处修改（E007/E072），
    否则 configure 报 "cannot guess build type" / "Kernel 'linux' not
    known to work with OS 'ohos'"；
  - E114: HMDFS setgid 目录下 configure 内 `umask 077 && mktemp -d` 生成
    drwx--S--- 不可写临时目录，config.status 写 subs1.awk 报 Permission
    denied → 运行时从生成的 configure 中删除 umask 077（a52dec/abiword
    同款；补丁对象是生成文件，不放入 patches/）；
  - E074: 鸿蒙 SELinux 禁止 jobserver FIFO → 全部 make 用 -j1。
  - 配方完全自包含（不引用仓库外脚本），CI 只读 conanfile.py/conandata.yml/
    test_package/patches/ 即可复现。
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _drop_umask_077(conanfile, path):
    """E114: remove `umask 077` from the generated configure (HMDFS)."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


def _patch_ohos_triplet(conanfile, src_dir):
    """E007/E072: teach config.guess/config.sub the aarch64-*-linux-ohos
    triplet.  Equivalent to scripts/patch-autotools-ohos.pl (self-contained)."""
    cg_path = os.path.join(src_dir, "build-aux", "config.guess")
    cs_path = os.path.join(src_dir, "build-aux", "config.sub")
    changed = 0

    # --- config.guess ---
    with open(cg_path, "r", encoding="utf-8") as f:
        gc = f.read()

    if "__OHOS__" not in gc:
        new_gc, n = re.subn(
            r'(#\s*if\s+defined\(__ANDROID__\)\s*\n\s*LIBC=android)',
            r'\1\n#elif defined(__OHOS__)\n    LIBC=ohos',
            gc, count=1, flags=re.M)
        if n:
            gc = new_gc
            changed += 1
            conanfile.output.info("config.guess: __OHOS__ LIBC detection added")
        else:
            conanfile.output.warning("config.guess: __ANDROID__ anchor not found")
    else:
        conanfile.output.info("config.guess: __OHOS__ already present")

    if "HarmonyOS" not in gc:
        block = (
            "    *:HarmonyOS:*:*)\n"
            "\tcase \"$UNAME_MACHINE\" in\n"
            "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
            "\t    armv7*|armv8*) MACHINE=arm ;;\n"
            "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
            "\t    i?86)         MACHINE=i686 ;;\n"
            "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
            "\tesac\n"
            "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
            "\t;;\n\n")
        new_gc, n = re.subn(
            r'(^[ \t]+\*:NetBSD:\*:\*\)[ \t]*\n)', block + r'\1',
            gc, count=1, flags=re.M)
        if n:
            gc = new_gc
            changed += 1
            conanfile.output.info("config.guess: HarmonyOS case added")
        else:
            conanfile.output.warning("config.guess: NetBSD anchor not found")
    else:
        conanfile.output.info("config.guess: HarmonyOS already present")

    with open(cg_path, "w", encoding="utf-8") as f:
        f.write(gc)

    # --- config.sub ---
    with open(cs_path, "r", encoding="utf-8") as f:
        sc = f.read()

    if "ohos-linux" not in sc:
        new_sc, n = re.subn(
            r'(\s*android-linux\)\s*\n'
            r'((?:\s*)basic_machine=\$field1-unknown\s*\n)'
            r'((?:\s*)basic_os=linux-android\s*\n)'
            r'(\s*;;\s*\n))',
            r'\1'
            r'\tohos-linux)\n'
            r'\2'
            r'\3'
            r'\4',
            sc, count=1)
        if n:
            sc = new_sc
            changed += 1
            conanfile.output.info("config.sub: ohos-linux triplet added")
        else:
            conanfile.output.warning("config.sub: android-linux anchor not found")
    else:
        conanfile.output.info("config.sub: ohos-linux already present")

    if not re.search(r'gnu\*\s*\|\s*android\*\s*\|\s*ohos\*', sc):
        new_sc, n = re.subn(
            r'(gnu\*\s*\|\s*android\*)', r'\1 | ohos*', sc, count=1)
        if n:
            sc = new_sc
            changed += 1
            conanfile.output.info("config.sub: ohos* added to OS list")
        else:
            conanfile.output.warning("config.sub: gnu*|android* anchor not found")
    else:
        conanfile.output.info("config.sub: ohos* already in OS list")

    if re.search(r'linux-ohos\*', sc) is None:
        # kernel-OS whitelist (case $kernel-$os-$obj in): insert linux-ohos*
        # after the linux-uclibc*- entry (variants across config.sub versions)
        m = re.search(r'linux-(mlibc|uclibc|musl|relibc)\*?-?\s*\)', sc)
        if m:
            anchor = m.group(0)
            new_sc = sc.replace(
                anchor, anchor.replace(')', '| linux-ohos*- )'), 1)
            sc = new_sc
            changed += 1
            conanfile.output.info("config.sub: linux-ohos* added to kernel whitelist")
        else:
            conanfile.output.warning("config.sub: kernel whitelist anchor not found")
    else:
        conanfile.output.info("config.sub: linux-ohos* already in kernel whitelist")

    with open(cs_path, "w", encoding="utf-8") as f:
        f.write(sc)

    conanfile.output.info(f"OHOS triplet patch applied ({changed} change(s))")


class UnivalueConan(ConanFile):
    name = "univalue"
    version = "1.1.1"
    description = "C++ universal value object library (JSON, used by Bitcoin Core)"
    license = "MIT"
    homepage = "https://github.com/jgarzik/univalue"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "univalue is supported only on Linux/OHOS, not "
                + str(self.settings.os))

    def build_requirements(self):
        # autoreconf bootstrap needs automake/libtool; the CI sandbox only
        # ships autoconf under /data/service/hnp/bin (same approach as
        # abiword-plugin-clarisworks / argp-standalone).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # 上游 test/object.cpp 的 BOOST_CHECK 宏依赖 assert() 激活（含
        # `BOOST_CHECK(v5.read("..."))` 的表达式副作用）；conan Release 默认
        # 在 CPPFLAGS 注入 -DNDEBUG 会把整条 assert 编译掉，导致 v5 保持 VNULL
        # 后裸调 getValues() 抛未捕获异常。CXXFLAGS 在编译命令行中位于
        # CPPFLAGS 之后，追加 -UNDEBUG 可正确撤销它（手动构建无 NDEBUG 时
        # make check 3/3 全过，即为佐证）。
        tc.extra_cxxflags.append("-UNDEBUG")
        tc.generate()

    def build(self):
        # 0) apply any conandata patches (patches: [] currently; kept for G1)
        apply_conandata_patches(self)
        # 1) bootstrap: tarball ships no configure
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # 2) E007/E072: OHOS triplet for config.guess/config.sub
        _patch_ohos_triplet(self, self.source_folder)
        # 3) E114: drop umask 077 from generated configure (HMDFS)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # L1: upstream regression suite (TESTS = object/unitester/no_nul)
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # remove libtool *.la wrappers
        import glob as _glob
        for _la in _glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        self.cpp_info.libs = ["univalue"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
