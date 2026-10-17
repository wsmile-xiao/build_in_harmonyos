#!/usr/bin/env python3
"""Conan recipe for mksh 59c — MirBSD Korn Shell（自定义 Build.sh，application）。

构建形态：mksh 不走 configure/make，用自带的 Build.sh（ksh 语法 shell 脚本）
  依次完成：特性 conftest 探测 → 生成 signames.inc/rlimits 等表 → 编译单文件
  汇总链接出 mksh → 生成回归测试入口 test.sh（shebang 指向刚构建出的 mksh，
  内部寻找 perl 执行 check.pl 解析 check.t）。
  因此本配方 build() 直接驱动 Build.sh，并随后调用 ./test.sh 跑上游回归套件。

平台口径：TARGET_OS=Linux。OHOS 为 Linux 内核 + musl libc；Build.sh 的
  Linux 分支注入 -D_GNU_SOURCE 与 -DSETUID_CAN_FAIL_WITH_EAGAIN；缺省时
  uname -s=HarmonyOS 落 unknown 分支（仅 "; it may or may not work" 警告
  继续，曾实测 setresuid/setresgid 隐式声明告警且 conftest 判定轮间波动，
  该配置不稳定）。与上游 Android→Linux 映射同口径。

上游测试：check.t 共 604 个用例（name: 计数），经 test.sh→perl check.pl 执行。
  本机（OHOS aarch64）实测口径：530 PASS / 0 FAIL / 74 SKIP（35 个静态类别
  不适用 + 39 个 need-ctty 经上游开关 -C regress:no-ctty 关闭），逐桶归因见
  manifest.yaml 与 notes.md。
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class MkshConan(ConanFile):
    name = "mksh"
    version = "59c"
    description = "MirBSD Korn Shell: a Bourne/POSIX-compatible shell, the default shell of MirBSD and Android's legacy shell"
    license = "MirOS"
    homepage = "https://www.mirbsd.org/mksh.htm"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        # 本包零补丁（conandata.yml patches: {}），调用为 no-op；
        # 保留标准形态以便后续补丁经 conandata 自动导出/应用。
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _toolchain_env(self):
        """取 OHOS 交叉工具链变量（与 smstools 配方同款， refusing PATH 偶遇 clang）。"""
        tc = AutotoolsToolchain(self)
        vars_ = tc.vars()
        cc = vars_.get("CC")
        if not cc:
            raise ConanException("AutotoolsToolchain did not provide CC; refusing "
                                 "to fall back to a PATH clang that could silently "
                                 "build a non-OHOS ELF")
        # L4 硬化：PIE + RELRO + BIND_NOW + stack protector（mksh 为单体可执行）。
        # Build.sh 默认 CFLAGS 仅 -O2（+ -fwrapv -Wall），不会自行加这些。
        cflags = vars_.get("CFLAGS", "") + " -fstack-protector-strong -fPIE"
        ldflags = vars_.get("LDFLAGS", "") + " -pie -Wl,-z,relro -Wl,-z,now"
        return cc, cflags, ldflags

    def build(self):
        # 零补丁（patches: {}），apply 为 no-op；保持配方标准形态
        apply_conandata_patches(self)
        cc, cflags, ldflags = self._toolchain_env()
        src = self.source_folder
        # 测试宿主工具口径（仅测试期 PATH 内生效，不进包、不改全局）：
        #   - fgrep：check.t 两个用例（regression-63/pipeline-3）断言 fgrep 的
        #     stderr 为空；GNU grep>=3.8 的 fgrep 每次打印弃用告警污染 stderr。
        #     shim 恢复 fgrep 的历史契约（= grep -F，静默）。
        shim = os.path.join(src, ".ohos-test-shim")
        os.makedirs(shim, exist_ok=True)
        with open(os.path.join(shim, "fgrep"), "w") as fh:
            fh.write("#!/bin/sh\nexec grep -F \"$@\"\n")
        os.chmod(os.path.join(shim, "fgrep"), 0o755)
        # 测试临时目录：OHOS 的 /tmp 只读，mksh 的 here-doc/here-string 走
        # $TMPDIR（缺省 /tmp 即失败），check.pl 又不把 TMPDIR 透传给用例子进程。
        tmpd = os.path.join(src, ".ohos-test-tmp")
        os.makedirs(tmpd, exist_ok=True)
        # TARGET_OS 必须显式经环境传入（Build.sh 仅在值为空时才退回 uname）；
        # PATH 前置 shim 目录——test.sh 会把 Build.sh 运行期的 PATH 冻结进自身。
        self.run(
            f'PATH="{shim}:$PATH" CC="{cc}" CFLAGS="{cflags}" LDFLAGS="{ldflags}" '
            f'TMPDIR="{tmpd}" TARGET_OS=Linux sh ./Build.sh -r -j -Q',
            cwd=src,
        )
        # 上游官方回归套件：test.sh 由 Build.sh 按本次构建产物生成（shebang 即
        # 新 mksh 的绝对路径；内部 $PERL/perl5/perl 找解释器跑 check.pl）。
        #   -C regress:no-ctty：无控制终端的自动化环境按 check.t 自述关闭
        #     need-ctty 用例（39 个，history/job-control 类），逐个具名归因
        #     见 manifest.yaml 与 notes.md；
        #   -e TMPDIR=…：check.pl 唯一环境注入开关，把可写临时目录交给用例。
        # 1 个 unexpected FAIL 即非零退出，build() 随之失败。
        self.run(
            f'PATH="{shim}:$PATH" TMPDIR="{tmpd}" '
            f'./test.sh -C regress:no-ctty -e TMPDIR="{tmpd}"',
            cwd=src,
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "mksh", src=self.source_folder, dst=bin_dir, keep_path=False)
        copy(self, "mksh.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "dot.mkshrc", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "mksh"),
             keep_path=False)

        binary = os.path.join(bin_dir, "mksh")
        os.chmod(binary, 0o755)
        if str(self.settings.os) == "OHOS":
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            if os.path.isfile(sign_tool):
                self.run(f"{objcopy} --remove-section .codesign {binary} "
                         f"2>/dev/null || true", quiet=True)
                signed = binary + ".signed"
                self.run(f"{sign_tool} sign -inFile {binary} -outFile {signed} "
                         f"-selfSign 1", quiet=True)
                if os.path.isfile(signed):
                    os.replace(signed, binary)
                os.chmod(binary, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.resdirs = ["share"]
