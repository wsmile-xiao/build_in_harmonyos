#!/usr/bin/env python3
"""Conan recipe — liblksctp 1.0.17（lksctp-tools：Linux 内核 SCTP 用户空间库）

上游 lksctp-tools 提供三样东西：

  * `src/lib`        → libsctp.so.1.0.17（`sctp_sendmsg`/`sctp_recvmsg`/
                       `sctp_getladdrs` … 的用户态封装，版本脚本 Versions.map
                       导出到 VERS_1..VERS_3）
  * `src/apps`       → bin/sctp_darn、bin/sctp_test、bin/sctp_status
  * `src/withsctp`   → bin/checksctp、bin/withsctp（LD_PRELOAD 包装脚本）+
                       lib/lksctp-tools/libwithsctp.so.1.0.17

适配要点：

1. **平台三元组（E007）**。autotools 随包 `bin/config.guess` 是 2015 年的旧版，
   在 HarmonyOS 上 `uname -s` 返回 "HarmonyOS" → `cannot guess build type`。
   本配方同时做两件事：(a) 打上 `0001/0002` 两个 E007 补丁，让 `bin/config.guess`
   认识 HarmonyOS、`bin/config.sub` 接受 `linux-ohos*`；(b) 在 generate() 里按
   仓库既有口径显式传 `--build=aarch64-unknown-linux-gnu`
   `--host=aarch64-unknown-linux-ohos`（build 侧 gnu、host 侧 ohos，避免两侧都写
   ohos 被 config.sub 误判）。框架的 `patch-autotools-ohos.pl` 在 CI worker 上
   拿不到（REPO_ROOT 不 export，remctl 3.18 已证），故不依赖它。

2. **OHOS ELF 签名（E077）**。鸿蒙内核只加载带有效 `.codesign` 段的 ELF；
   链接器自签在 `make install`/strip 后可能失效，因此 package() 对 libsctp.so、
   libwithsctp.so 及三个 bin 工具统一「先 objcopy 剥旧段、再 binary-sign-tool
   自签、最后恢复 0755」。

3. **上游测试（§10）**。`src/func_tests` 的 v4/v6 用例是 `noinst_PROGRAMS`，
   上游没有 `TESTS=` 注册，`make check` 因此**静默零执行**；它们的真正驱动是
   自定义目标 `v4test`/`v6test`，而这些用例是**内核实时（live-kernel）用例**——
   每条都 `socket(AF_INET, SOCK_STREAM, IPPROTO_SCTP)` 起真实关联。本配方用
   上游自带的 `checksctp` 探针先判内核是否启用 SCTP：启用则逐条实跑 v4 用例并
   汇总通过/失败；未启用则逐条标记为「资源未执行（内核未启用 SCTP）」，不做
   静默删除、不缩分母。产品库本身（libsctp）不依赖内核 SCTP 即可编译、安装、
   被链接，故构建照常产出。

4. **HMFS 临时目录（0003 补丁）**。`configure` 的安全临时目录惯用法
   `(umask 077 && mktemp -d ./confXXXXXX)` 在 HMFS 上建 0700 目录后往里写
   `subs*.awk` 被拒（`Permission denied` / `could not setup config files
   machinery`）。`TMPDIR` 重定向无效（目录名硬编码、子 shell 显式 umask 不受
   ambient 影响）。打 `0003-configure-umask-022.patch` 全文 `umask 077`→
   `umask 022`（生成的 config.status 从 here-doc 继承同文本，一次替换同步修复）。

5. **musl uapi 头冲突（R8，配方层 shim）**。`src/func_tests/*.c` 同时包含
   `<sys/socket.h>` 与内核 uapi 头 `<linux/socket.h>`（`test_1_to_1_rtoinfo.c`
   另含 `<linux/in.h>`/`<linux/in6.h>`）。musl 上用户态头已定义
   `struct sockaddr_storage`/`sockaddr_in`/`in6_addr`，uapi 头再定义一次 →
   `error: redefinition of 'sockaddr_storage'`，func_tests 编译失败。规则 R8 禁止
   把平台宏写进补丁，故用 `shim/linux/{socket,in,in6}.h`（`#ifndef __GLIBC__` 时
   `#include <sys/socket.h>`/`<netinet/in.h>`，glibc 时 `#include_next` 落回真头）
   经 `exports` + `generate()` 的 `-I <recipe_folder>/shim` 前置 shadow 掉 uapi 头，
   上游源码零改动（先例 kbd/2.9.0）。
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# 上游 src/func_tests/Makefile.am 的 `PASSING_KERN_TESTS`（v4 内核实时用例，
# 共 32 条）。仅用于 v4test 汇总时对齐分母；不改动、不删减。
_V4_TESTS = [
    "test_assoc_abort", "test_assoc_shutdown", "test_autoclose", "test_basic",
    "test_fragments", "test_inaddr_any", "test_peeloff", "test_sockopt",
    "test_connect", "test_connectx", "test_recvmsg", "test_timetolive",
    "test_sctp_sendrecvmsg", "test_getname", "test_tcp_style",
    "test_1_to_1_socket_bind_listen", "test_1_to_1_accept_close",
    "test_1_to_1_connect", "test_1_to_1_connectx", "test_1_to_1_send",
    "test_1_to_1_sendto", "test_1_to_1_sendmsg", "test_1_to_1_recvfrom",
    "test_1_to_1_recvmsg", "test_1_to_1_shutdown", "test_1_to_1_sockopt",
    "test_1_to_1_addrs", "test_1_to_1_nonblock", "test_1_to_1_rtoinfo",
    "test_1_to_1_events", "test_1_to_1_threads", "test_1_to_1_initmsg_connect",
]


class LiblksctpConan(ConanFile):
    name = "liblksctp"
    version = "1.0.17"
    description = "Linux Kernel SCTP user-space library and utilities (lksctp-tools)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/sctplab/lksctp-tools"
    url = "https://github.com/sctplab/lksctp-tools"
    # 交付形态为共享库（libsctp.so.1.0.17 / libwithsctp.so.1.0.17，须 E077 签名）；
    # 用 "shared-library" 而非裸 "library"——后者在 Conan 2 要求配方自行声明 shared
    # 选项，否则 conan create 报 "Package type is 'library', but no 'shared' option
    # declared"。（先例：libass/0.17.5。）
    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    # R8：musl 上 <linux/{socket,in,in6}.h> 与 <sys/socket.h>/<netinet/in.h>
    # 冲突（`struct sockaddr_storage` 等重定义），而 src/func_tests 同时包含两者。
    # 用配方层 shim 头 shadow 掉内核 uapi 头，经 generate() 的 -I 注入，上游源码零改动
    # （先例 kbd/2.9.0）。glibc 上 shim 用 #include_next 落回真头，自动失效。
    exports = ["shim/linux/*.h"]

    # ── 布局 / 源码 ─────────────────────────────────────────────────
    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"]["liblksctp"], strip_root=True)
        apply_conandata_patches(self)

    # ── 配置 ────────────────────────────────────────────────────────
    def generate(self):
        tc = AutotoolsToolchain(self)
        # E007：显式交叉三元组（build=gnu / host=ohos），不依赖 config.guess 的
        # 自动探测，也不依赖 framework 的 patch-autotools-ohos.pl。
        arch = "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
        tc.configure_args.append("--build=%s-unknown-linux-gnu" % arch)
        tc.configure_args.append("--host=%s-unknown-linux-ohos" % arch)
        # 默认即 yes；显式写明，保证 src/func_tests 被编译（供 §10 实跑）。
        tc.configure_args.append("--enable-tests")
        # R8：把 shim/ 前置到包含路径，shadow 掉 OHOS SDK 的 <linux/socket.h> 等
        # （其 struct sockaddr_storage 与 <sys/socket.h> 重定义）；shim 内 #include_next
        # 落回真头，glibc 上无副作用。上游源码零改动（先例 kbd/2.9.0）。
        shim = os.path.join(self.recipe_folder, "shim")
        tc.extra_cflags.append("-I" + shim)
        tc.extra_cxxflags.append("-I" + shim)
        tc.generate()

    # ── 构建 + 上游测试 ─────────────────────────────────────────────
    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        tests_dir = os.path.join(self.build_folder, "src", "func_tests")
        if not os.path.isdir(tests_dir):
            self.output.info("§10 上游测试：未找到 src/func_tests（--enable-tests 未生效）")
            return

        checksctp = os.path.join(self.build_folder, "src", "withsctp", "checksctp")
        supported = False
        if os.path.isfile(checksctp):
            try:
                self.run('"%s"' % checksctp, env="conanbuild")
                supported = True
            except ConanException:
                supported = False
        kernel_state = "已启用 SCTP" if supported else "未启用 SCTP（checksctp 探测失败）"

        if not supported:
            # 内核未启用 SCTP：这些 live-kernel 用例没有可执行前提。逐条标为
            # 「资源未执行」并附技术原因，不静默删用例、不缩分母（同 remctl 3.18 口径）。
            self.output.info(
                "§10 上游测试：src/func_tests 共 %d 条 v4 内核实时用例，"
                "worker 内核%s → 全部标记为资源未执行（不删用例、不缩分母）"
                % (len(_V4_TESTS), kernel_state)
            )
            return

        passed, failed = [], []
        cwd = os.getcwd()
        try:
            os.chdir(tests_dir)
            for name in _V4_TESTS:
                try:
                    self.run("./%s" % name, env="conanbuild")
                    passed.append(name)
                except ConanException:
                    failed.append(name)
        finally:
            os.chdir(cwd)
        self.output.info(
            "§10 上游测试（v4 内核实时用例）: 通过 %d / 失败 %d / 共 %d"
            % (len(passed), len(failed), len(_V4_TESTS))
        )
        for name in failed:
            self.output.info("  | FAIL %s" % name)

    # ── 打包 ────────────────────────────────────────────────────────
    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        for lic in ("COPYING", "COPYING.lib"):
            copy(
                self,
                lic,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
                keep_path=False,
            )
        self._sign_package()

    def package_info(self):
        self.cpp_info.libs = ["sctp"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]

    # ── OHOS ELF 签名（E077）────────────────────────────────────────
    def _sign_package(self):
        """对包内所有 ELF（libsctp.so*、libwithsctp.so*、bin 工具）重签。

        鸿蒙内核只加载带有效 .codesign 段的 ELF（E077）。顺序不可变：先
        llvm-objcopy 移除旧签名段 → binary-sign-tool 自签 → 恢复 0755。
        """
        if str(self.settings.os) != "OHOS":
            return
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.exists(sign_tool) and os.path.exists(objcopy)):
            return
        for root in ("bin", "lib"):
            base = os.path.join(self.package_folder, root)
            for dirpath, _dirnames, filenames in os.walk(base):
                for name in filenames:
                    path = os.path.join(dirpath, name)
                    if not self._is_elf(path):
                        continue
                    self.run(
                        '%s --remove-section .codesign "%s" 2>/dev/null || true'
                        % (objcopy, path)
                    )
                    self.run(
                        '%s sign -inFile "%s" -outFile "%s" -selfSign 1'
                        % (sign_tool, path, path)
                    )
                    try:
                        os.chmod(path, 0o755)
                    except OSError:
                        pass

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False
