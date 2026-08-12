# NASM 2.16.03 HarmonyOS 适配记录

## 范围

- Conan 引用：nasm/2.16.03
- Issue：#2050（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2050）
- 分支：feat/nasm-2.16.03-2050
- Worktree：D:\harmonyos\worktrees\nasm
- 本轮只修改 archives/n/nasm/2.16.03/。

## W0 依赖与构建系统分析

- 官方源码：https://www.nasm.us/pub/nasm/releasebuilds/2.16.03/nasm-2.16.03.tar.gz
- SHA-256：5bc940dd8a4245686976a8f7e96ba9340a0915f2d5b88356874890e207bdb581
- 构建系统：Autoconf/Make；release tarball 已包含 configure、生成后的 C 源码和 Makefile 模板。
- 编译 nasm、ndisasm 不依赖其他三方库。
- 上游 make test 运行 249 个汇编用例，测试驱动 test/performtest.pl 需要 Perl。Perl 不参与 release tarball 的正常编译，因此不把它设置成 NASM 的硬依赖。
- 2026-08-11 查询 OHPCD Conan 远端时，本机 DNS 无法解析 ohpcd.cn，所以本轮无法确认可选的 perl/5.42.2 是否已经发布。

## 既有档案审计

原档案记录了 2026-05-25 的一次 OHOS aarch64 手工构建成功，但缺少 Conan 配方、可信源码哈希和 test_package。原有前两个补丁分别大范围替换了 GNU config.guess 与 config.sub，超出了 NASM 适配所需范围。

本轮将它们缩减为：

1. 0001-autoconf-helpers-config.guess.patch
   - 编译器定义 __OHOS__ 时将 libc 标识为 ohos。
   - 兼容 uname -s 返回 HarmonyOS。
2. 0002-autoconf-helpers-config.sub.patch
   - 只增加 ohos OS 和 linux-ohos kernel/OS 组合。
3. 0003-configure.patch
   - 保留既有真机验证过的 HMDFS 修复，把 config.status 临时目录的 umask 077 改为 022。

三个补丁均以官方 2.16.03 tarball 为基线。

## Conan 配方

- package_type = "application"，安装 bin/nasm 和 bin/ndisasm。
- 支持 Linux 与 OHOS 原生构建。
- OHOS 使用 <arch>-unknown-linux-ohos 作为 build/host triplet。
- package_info() 将 bin 加入 build/run 环境的 PATH，供 smallerc 等下游通过 tool_requires("nasm/2.16.03") 使用。
- 构建阶段先用 NASM 生成 16-bit flat binary，并核对精确机器码 b8341283c001c3。

## test_package

测试包按构建工具消费者方式使用 tool_requires(self.tested_reference_str)，并通过打包目录中的绝对路径执行：

- nasm --version
- ndisasm --version
- 生成 16-bit flat binary 并核对精确机器码
- 反汇编 flat binary 并核对 mov、add、ret
- 生成 ELF64 object 并核对 ELF magic

测试只生成 x86/x86_64 目标文件，不在 aarch64 HarmonyOS 上执行所生成的 x86 代码。

## 历史真机证据

原档案记录 2026-05-25 在 OHOS aarch64 上完成：

- configure
- make -j4
- make install
- nasm --version 返回 NASM version 2.16.03
- 生成 nasm（约 3.2 MiB）和 ndisasm（约 1.7 MiB）

该证据说明三项平台补丁方向可行，但不等同于本轮新增 Conan 配方已经完成真机验证。

## 本机验证

本轮计划/执行的本机门槛：

    python -m py_compile archives\n\nasm\2.16.03\conanfile.py archives\n\nasm\2.16.03\test_package\conanfile.py
    conan inspect archives\n\nasm\2.16.03
    conan export archives\n\nasm\2.16.03
    git -C <official-source> apply --check archives\n\nasm\2.16.03\patches\0001-autoconf-helpers-config.guess.patch
    git -C <official-source> apply --check archives\n\nasm\2.16.03\patches\0002-autoconf-helpers-config.sub.patch
    git -C <official-source> apply --check archives\n\nasm\2.16.03\patches\0003-configure.patch

结果：

- Python 配方编译与三个 YAML 文件解析通过。
- 官方源码 SHA-256 复核通过。
- 三个补丁联合 git apply --check 通过；实际应用后 config.guess、config.sub、configure 的 shell 语法检查通过。
- 补丁后的 config.sub 将 aarch64-linux-ohos 规范化为 aarch64-unknown-linux-ohos，也接受 x86_64-unknown-linux-ohos。
- Conan inspect、export 和无远端 Linux graph info 通过；最终 recipe revision 为 f17435020cdb047fa928b1d8a67d10d2，依赖图为空。
- 使用官方 NASM 2.16.03 Windows 二进制执行同一组测试向量通过：flat binary 为 b8341283c001c3，反汇编包含预期三条指令，ELF magic 为 7f454c46。
- ndisasm 2.16.03 的版本参数是 -v，不是 --version；本机功能测试已据此修正 test_package。
- 文件均为 LF、无 UTF-8 BOM；worktree 改动只位于 archives/n/nasm/2.16.03/。
- git diff --check 对 0002 patch 的一行上游 tab 缩进上下文给出 space-before-tab 提示；该行只是 unified diff 上下文，不修改目标源码，且三补丁联合应用已通过。

本机没有 WSL、C 编译器、Make 或 Perl，因此未执行完整的本机 Autotools 编译和上游 make test。该限制不影响已完成的配方静态验证，新的 Conan create 仍需在真机或 Shadow CI 单包执行。

## 下一步真机 / Shadow CI

保持单包排队，在获得真机空闲窗口后运行：

    sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
      --user codex-nasm \
      --job nasm-2.16.03 \
      --package archives/n/nasm/2.16.03 \
      --repo-source "$HOME/validation/build_in_harmonyos"

    . "$HOME/ohos-users/codex-nasm/nasm-2.16.03/env.sh"
    cd "$CI_REPO_ROOT"
    git fetch origin feat/nasm-2.16.03-2050
    git checkout feat/nasm-2.16.03-2050
    sh "$OHOS_JOB_BASE/run-conan-heavy.sh"

单包 CI：

    CI_PACKAGES="archives/n/nasm/2.16.03" zsh ci/conan/build_and_test.sh

Shadow CI：

    sh "$HOME/bin/run-ohos-shadow-ci.sh" archives/n/nasm/2.16.03

真机通过并发布 nasm/2.16.03 后，回到 smallerc #2049，移除其 W0 阻塞并执行 conan create。
