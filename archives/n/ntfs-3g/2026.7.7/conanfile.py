#!/usr/bin/env python3
"""Conan recipe — ntfs-3g 2026.7.7 (NTFS 文件系统读写库 + ntfsprogs 工具).

autotools 构建(上游 tarball 无 configure,需 autoreconf 自举;tool_requires automake+autoconf 提供 aclocal/autoconf)。
FUSE 挂载工具禁用(平台无 FUSE),仅交付 libntfs-3g 库 + ntfsprogs
工具集(mkntfs/ntfsls/ntfsinfo 等文件级操作,不依赖 FUSE)。
不做 strip(llvm-strip 产物被平台拒绝,yices 2.7.0 先例)。
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Ntfs3gConan(ConanFile):
    name = "ntfs-3g"
    version = "2026.7.7"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def build_requirements(self):
        self.tool_requires("automake/1.18")
        self.tool_requires("autoconf/2.72")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # --disable-ntfs-3g  关掉唯一的 FUSE 驱动依赖(平台无 FUSE)，只留 ntfsprogs + libntfs-3g
        tc.configure_args.append("--disable-ntfs-3g")
        # mount-helper 在 configure.ac 里对非 linux* 的 target_os 默认就是 no
        # (OHOS 走 *)，无需显式传；--disable-mount-helper 不是合法选项
        # (只有 --enable-mount-helper)，autoconf 只会 WARNING 不报错，故不传。
        tc.configure_args.append("--disable-ldconfig")
        tc.configure_args.append("--disable-plugins")
        tc.extra_cflags.append("-D_GNU_SOURCE")
        tc.extra_cflags.append("-Wno-error")
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        # conandata.yml 指向官方 release tarball，自带 configure，无需 autoreconf。
        # 保留兜底分支：若将来换回 GitHub archive(纯源码)，autoreconf 会因
        # perl/5.42.2 的 Cwd.so(XS 模块未 codesign)不可加载而失败，届时需改依赖版本。
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("源码树无 configure,先 autoreconf 自举")
            autotools.autoreconf()
        # E007: release tarball 自带的 config.guess(2024-07-27)不认 HarmonyOS，
        # uname -s=HarmonyOS 匹配不到任何 case → 落到 compile-and-run 探针 →
        # 探针往 mktemp -d 临时目录写 dummy.c → HMDFS 上 Permission denied →
        # "unable to guess system type" → configure "cannot guess build type"。
        # 正解是改 config.guess/config.sub 本身(0001/0002)，**不是** --build/--host：
        # 后者会置 cross_compiling=yes，AC_RUN_IFELSE 全跳过、config.h 全默认值
        # (铁律 P-AUTOTOOLS-001, level=critical)。
        # 补丁在 autoreconf 之后应用：autoreconf 会用系统版本重生成这两个文件，
        # 先打补丁会被覆盖。
        apply_conandata_patches(self)
        # 复核补丁确实落地(config.guess 认不认 HarmonyOS 决定 configure 成败)。
        guess = os.path.join(self.source_folder, "config.guess")
        if os.path.isfile(guess):
            with open(guess, encoding="utf-8", errors="ignore") as f:
                patched = "HarmonyOS" in f.read()
            self.output.info(f"config.guess OHOS 识别: {'已打补丁' if patched else '缺失!'}")
            if not patched:
                raise ConanException("E007: config.guess 未识别 HarmonyOS, configure 会失败")
        # hmdfs umask 077 陷阱(buildtorrent 0.9.1 先例)
        for _cfg in glob.glob(os.path.join(self.source_folder, '**', 'configure'), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # 复制许可文件
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["ntfs-3g"]
        self.cpp_info.set_property("cmake_file_name", "ntfs-3g")
        self.cpp_info.set_property("cmake_target_name", "ntfs-3g::ntfs-3g")
        bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.define_path("PATH", bindir)
