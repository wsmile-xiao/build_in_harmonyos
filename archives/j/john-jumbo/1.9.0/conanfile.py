#!/usr/bin/env python3
"""Conan recipe for john-jumbo 1.9.0 -- John the Ripper jumbo for HarmonyOS PC.

平台任务卡指定包名 john-jumbo、版本 1.9.0（上游 1.9.0-jumbo-1，2019-05 发布）。
官方 main archives/j/john/1.9.0-jumbo-1 仅含 manifest/notes 与两条占位补丁
（无 conanfile.py / test_package，从未进入 CI、从未发布制品仓），本配方按
ARCHIVE-SPEC v2.0 补全适配（平台任务卡口径即本包名）。
"""

import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class JohnJumboConan(ConanFile):
    name = "john-jumbo"
    version = "1.9.0"
    description = "John the Ripper jumbo -- password security auditing and recovery toolkit"
    license = "GPL-2.0-or-later"
    homepage = "https://www.openwall.com/john/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def configure(self):
        # OHOS settings.yml 为 OHOS 定义 version 子设置（无默认值），配方未声明
        # os.version 时 package_id 校验会报 "Invalid: 'settings.os.version' value
        # not defined"（知识库 DRAFT-glpk-4.65-ohos-conan-os-version-rm-safe）：
        # 有该子设置才 rm_safe 移除，Windows 等无此子设置的平台不受影响。
        if hasattr(self.settings, "os") and hasattr(self.settings.os, "version"):
            self.settings.rm_safe("os.version")

    def export_sources(self):
        # 补丁必须随配方导出进缓存（e/ 目录），apply_conandata_patches 从
        # export_sources_folder 读取补丁文件；缺此步则补丁不生效。
        # （方法顺序遵循规范：export_sources → requirements → layout → source…）
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/1.1.1w")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        ssl_root = self.dependencies["openssl"].package_folder
        zlib_root = self.dependencies["zlib"].package_folder

        # 上游 configure 的 OS 探测无法识别 HarmonyOS（config.guess 不识别 +
        # config.status 临时文件权限问题，官方 main john 旧适配笔记同款结论），
        # Makefile.legacy 的 linux-arm64le 是上游官方为不支持系统提供的构建路径。
        #
        # 用户扩展点是 JOHN_CFLAGS/JOHN_LDFLAGS（追加在默认值之后；Makefile 内
        # 不存在 CFLAGS_EXTRA 变量）。默认值已含 -DHAVE_LIBSSL/-lssl/-lcrypto/
        # -lm/-lz，故只需补 conan 依赖的头文件/库搜索路径。
        # -DJOHN_NO_SIMD：NEON vroti_epi32 宏在 OHOS clang 下编译失败
        # （官方 main john 旧适配笔记实测结论），arm64le.h 有 !JOHN_NO_SIMD 回退。
        # HAVE_LIBGMP/GMP_LDFLAGS/REXGEN_FLAGS/REXGEN_LDFLAGS 置空：设备上
        # 无 gmp.h/librexgen，命令行变量压过 Makefile 内反引号探测（无 override）。
        # -j8：真机进程配额有限（约 550），并行度过高会 fork EAGAIN（知识库记录）。
        self.run(
            f"make -f Makefile.legacy linux-arm64le CC={cc} "
            f'JOHN_CFLAGS="-DJOHN_NO_SIMD -I{ssl_root}/include -I{zlib_root}/include" '
            f'JOHN_LDFLAGS="-L{ssl_root}/lib -L{zlib_root}/lib" '
            f"HAVE_LIBGMP= GMP_LDFLAGS= REXGEN_FLAGS= REXGEN_LDFLAGS= -j8",
            cwd=os.path.join(self.source_folder, "src"),
        )

    def package(self):
        src = os.path.join(self.source_folder, "run")
        bin_dir = os.path.join(self.package_folder, "bin")
        share_dir = os.path.join(self.package_folder, "share", "john")
        lic_dir = os.path.join(self.package_folder, "licenses")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(share_dir, exist_ok=True)
        os.makedirs(lic_dir, exist_ok=True)

        copy(self, "john", src, bin_dir)

        # 运行时必需数据必须与 john 同目录：1.9.0-jumbo-1 的 path.c 不读 JOHN
        # 环境变量（该支持为后续 jumbo 版本引入），john_home_path = dirname(argv[0])，
        # $JOHN/... 一律从二进制所在目录解析——上游 run/ 布局即如此。john.conf
        # 的 .include 链引用全部 11 个 run/*.conf（540 dynamic_disabled.conf、
        # 1162 korelogic.conf、3929-3947 hybrid/dumb16/dumb32/repeats16/
        # repeats32/dynamic/regex_alphabets；dynamic.conf 再引
        # dynamic_flat_sse_formats.conf；john.local/john-local 为可选），
        # 缺一即 fopen 失败（真机实测三轮：先缺 dynamic_disabled.conf +
        # rules/best64.rule，再缺 korelogic.conf）→ 全部 .conf 与 rules/ 随
        # 二进制进 bin/。
        for f in os.listdir(src):
            if f.endswith(".conf"):
                copy(self, f, src, bin_dir)
        copy(self, "password.lst", src, bin_dir)
        for f in os.listdir(src):
            if f.endswith(".chr"):
                copy(self, f, src, bin_dir)
        # conan copy() 不复制目录（真机实测 rules/ 未落盘），目录用 shutil
        shutil.copytree(os.path.join(src, "rules"), os.path.join(bin_dir, "rules"))

        # 其余内容进 share/john：辅助工具（relbench/mailer/makechr/genmkvpwd/
        # benchmark-unify）、108 个 *2john 提取脚本、dns/ 等。
        # 跳过：8 个 argv[0] 别名（run/ 内为 john 的 cp 副本，消费者按需自建；
        # OHOS 禁 symlink，无法提供链接形态）、ztex/opencl（固件/内核，与 OHOS
        # 无关，ztex 单目录 19MB）。
        ALIASES = ("unshadow", "unafs", "undrop", "zip2john",
                   "gpg2john", "rar2john", "base64conv", "unique")
        AUX = ("relbench", "mailer", "makechr", "genmkvpwd", "benchmark-unify")
        SKIP = ("john", "rules", "ztex", "opencl")
        for f in AUX:
            copy(self, f, src, share_dir)
        for f in os.listdir(src):
            if f in ALIASES or f in AUX or f in SKIP or f == "password.lst":
                continue
            if f.endswith(".chr") or f.endswith(".conf"):
                continue
            sp = os.path.join(src, f)
            if os.path.isdir(sp):
                shutil.copytree(sp, os.path.join(share_dir, f))
            else:
                copy(self, f, src, share_dir)

        # 许可证全文（GPL-2.0-or-later，上游 doc/ 内 COPYING + LICENSE）
        doc_dir = os.path.join(self.source_folder, "doc")
        for f in ("COPYING", "LICENSE"):
            copy(self, f, doc_dir, lic_dir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
