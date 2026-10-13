#!/usr/bin/env python3
"""Conan recipe — sprai 0.9.9.23（single-pass read accuracy improver）。

sprai 是 Takamasa Imai（Kasahara Lab, UTokyo）写的 PacBio CLR 纠错流水线。
它的**可编译部分**是 4 个纯 C 命令行程序，彼此用管道串成一条四段流水线：

    bowtie -m5 输出 ──m52bfmt7──▶ blastn -outfmt 7 风格表格
                              ──bfmt72s──▶ sprai 私有 SAM（含 AS:/EV:/PI: 标签）
                              ──nss2v_v3──▶ 纵向比对 .nss
                              ──myrealigner──▶ 共识 FASTA/FASTQ

17 个 .pl 脚本（ezez_vx1.pl 等）是驱动层，需要 Perl + NCBI BLAST+ + Celera
Assembler 才能跑；制品仓里既没有 OHOS aarch64 的 perl 也没有 blast
（conan list "perl/*@ohpcd/stable" -r=ohpcd → 0 recipes），所以它们不进 bin/，
而是作为**参考载荷**装到 share/sprai/（理由见 notes.md §5）。

构建系统是上游自己的**裸 makefile**（文件名小写 makefile），只有 all / install
两个 target。tarball 里另有一个 configure，但它只是 waf 的包装脚本
（生成 Makefile 后调 waf），而 +dfsg 重打包已按 debian/copyright 的
Files-Excluded 删掉 waf/waflib/wscript —— 也就是说 configure 在本包里根本不可用，
这也和 Debian 用 --buildsystem=makefile（而非 configure）一致。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

# makefile 的 COMPILED：4 个 ELF，全部进 bin/
COMPILED = ("bfmt72s", "nss2v_v3", "myrealigner", "m52bfmt7")

# makefile 的 SCRIPTS：17 个 Perl 驱动脚本，装到 share/sprai/
PERL_SCRIPTS = (
    "ca_ikki_v5.pl",
    "ezez4makefile_v4.pl",
    "ezez4qsub_vx1.pl",
    "ezez_vx1.pl",
    "dumbbell_filter.pl",
    "fa2fq.pl",
    "fq2fa.pl",
    "fq2idfq.pl",
    "fqfilt.pl",
    "get_top_20x_fa.pl",
    "partition_fa.pl",
    "get_target_fasta_records.pl",
    "dfq2fq_v2.pl",
    "extract_fq.pl",
    "bfmtx2m4.pl",
    "check_redundancy.pl",
    "check_circularity.pl",
)

# 运行期配置文件：ec.spec 是 sprai 的主 spec，pbasm.spec 来自 PacBio（BSD-3）
SPEC_FILES = ("ec.spec", "pbasm.spec")

# 上游把 sphinx 构建产物（_sources/*.txt）打进 tarball，Debian 拿其中 6 个当
# 文档/示例；随包保留，因为它们是上游唯一的用户文档。
DOC_FILES = (
    "doc/_build/html/_sources/README.txt",
    "doc/_build/html/_sources/FAQ.txt",
    "doc/_build/html/_sources/Example.txt",
    "doc/_build/html/_sources/Contact.txt",
    "doc/_build/html/_sources/Download.txt",
    "doc/_build/html/_sources/index.txt",
)


class SpraiConan(ConanFile):
    name = "sprai"
    version = "0.9.9.23"
    package_type = "application"
    license = "MIT"
    homepage = "https://kasahara-lab.github.io/sprai_doc/"
    description = ("Sprai (single-pass read accuracy improver): 4 C tools that turn "
                   "PacBio CLR all-vs-all BLAST alignments into a consensus sequence "
                   "(m52bfmt7 / bfmt72s / nss2v_v3 / myrealigner)")
    url = ""

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "conandata.yml", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 4 个程序只用 libc（stdio/stdlib/string/unistd/getopt/ctype/assert），
        # 无任何外部库依赖；ohpcd 里也没有必须先拿到的二进制依赖。
        pass

    def layout(self):
        # 上游 makefile 的规则全部写成相对路径（`$(CC) ... -o $@ $<`），
        # 没有 srcdir/builddir 概念 —— 只能就地构建（与 magicrescue / termdebug 同款）。
        self.folders.source = self.source_folder

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: 编译器必须取自 Conan conf，不能用 shell 里的 ${CC}
        # （CI worker 上它是空的，会静默退回宿主 gcc 编出 x86-64 产物）。
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={})
        cc = compiler_executables.get("c") or "clang"

        # 上游原本硬编码 `-Wall -O3 -g`。-O3 保留（作者的优化意图），
        # -g 去掉（Conan 包是发布件，不带调试信息）。
        #
        # -fsigned-char 是**必需项**，不是可选项：
        #   col2fqcell.h 的 `typedef struct base_t { char base; ... }` 里，
        #   myrealigner.c 用 -1 当 base 的哨兵（628/745/977/1007 行）。
        #   plain char 在 x86-64 上默认 signed，在 aarch64 上默认 **unsigned**，
        #   于是 `base != -1` 恒真，片段链表被 walk 出界，myrealigner **每次调用
        #   都 SIGSEGV**。clang 在编译期就会报
        #   -Wtautological-constant-out-of-range-compare。详见
        #   patches/0001-makefile-honour-cflags.patch 与 notes.md §4.1。
        cflags = "-O3 -fsigned-char"
        # R9: 恒用 -j1
        self.run(f"make CC={cc} CFLAGS='{cflags}' -j1")

        for binary in COMPILED:
            path = os.path.join(self.source_folder, binary)
            if not os.path.isfile(path):
                raise ConanException("%s was not produced by make" % binary)
            if os.path.getsize(path) < 4096:
                raise ConanException("%s is implausibly small (%d bytes)"
                                     % (binary, os.path.getsize(path)))

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        share = os.path.join(self.package_folder, "share", "sprai")

        # copy() 的多模式写法（空格分隔）对顶层文件不生效，逐个拷更可靠。
        for name in COMPILED:
            copy(self, name, src=self.source_folder, dst=bin_dir)
            os.chmod(os.path.join(bin_dir, name), 0o755)

        # Perl 驱动层：装成参考载荷而不是 bin/ 命令（见 notes.md §5）
        for name in PERL_SCRIPTS:
            copy(self, name, src=self.source_folder, dst=share)
            os.chmod(os.path.join(share, name), 0o755)

        for name in SPEC_FILES + ("ChangeLog.txt", "LICENSE.txt"):
            copy(self, name, src=self.source_folder, dst=share)
        # 文档在 doc/_build/html/_sources/ 下：copy() 遇到带 / 的 pattern 会**保留**
        # 相对路径（不会拍平），所以直接把 src 指到那一层再 *.txt。
        copy(self, "*.txt",
             src=os.path.join(self.source_folder, "doc/_build/html/_sources"),
             dst=share)

        # 上游 make install 的规则是 `chmod 766`；Conan 包要常规的 755。
        # bin/ 必须恰好是 makefile 的 COMPILED 四个目标：多一个就是发了不该发的
        # 二进制，少一个就是 make 静默没编出来。
        for binary in COMPILED:
            path = os.path.join(bin_dir, binary)
            if not os.path.isfile(path):
                raise ConanException("bin/%s missing after packaging" % binary)
            self._sign_ohos_binary(path)

    def _sign_ohos_binary(self, path):
        """真机 HMDFS 拒绝执行未签名 ELF，交叉编译的产物必须自签一次。"""
        if str(self.settings.os) != "OHOS":
            return
        signer = self.conf.get("user.ohos:sign_tool", default="", check_type=str)
        signer = (signer or os.environ.get("OHOS_SIGN_TOOL", "")
                  or shutil.which("binary-sign-tool")
                  or "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool unavailable; skipping OHOS ELF "
                                "signing (cross build only, consumer test on a "
                                "real device will need it)")
            return
        objcopy = self.conf.get("user.ohos:objcopy", default="", check_type=str)
        objcopy = (objcopy or os.environ.get("OHOS_OBJCOPY", "")
                   or shutil.which("llvm-objcopy")
                   or "/data/service/hnp/bin/llvm-objcopy")
        if os.path.isfile(objcopy):
            self.run('"%s" --remove-section .codesign "%s"' % (objcopy, path),
                     ignore_errors=True)
        signed = path + ".signed"
        self.run('"%s" sign -inFile "%s" -outFile "%s" -selfSign 1'
                 % (signer, path, signed))
        if not os.path.isfile(signed):
            raise ConanException("binary-sign-tool produced no output for %s" % path)
        os.replace(signed, path)
        os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
