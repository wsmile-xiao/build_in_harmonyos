# TapTempo 1.4.5 适配记录（候选）

状态：built；当前七份自动生成补丁候选在 H1-008 的 OHOS/armv8 `conan create` 和正式 W3 均通过包内消费者 10/10，W3 两脚本 rc0、`.ci-result.json exit_code=0`。整体 `finish` 原次仍 rc1：独立 G0 clean-verify 未找到原始 tarball，W5/summary 与 staging 收尾未完成，不能称完整流程通过。随后 H1-008 私有补证在同一七补丁源码上单独构建并运行 Catch2 上游 19/19、95 条断言，并在保留官方 G2 warning 的前提下从真实 Conan ELF 续跑官方 release/debug 打包，未重跑 Conan/W3。官方 CI、独立 W4、push 和 PR 尚未执行。

独立 W4 对 `16da0234` 发现计时断言不稳定和误纳入 PR 报告两个 P1；`2a576b72` 已修复它们，H1-007 在先前真实包内程序及新 Conan 包内程序上分别 10/10，但独立预审又发现单个手写多文件补丁不符当前自动补丁规则。当前候选改用官方 `refresh-patch --auto` 生成的七份逐文件补丁，并移出两份运行报告。消费者逐拍同步、按发送与确认区间核对 BPM；Windows 真程序 10/10，固定返回 80 BPM 和忽略 `-s` 的反例被拦下。主机与先前 H1 结果都不能替代当前七补丁输入的 Conan/W3 复测。

### 对话 #1：七份补丁的本地合规修订

从固定作者源码和先前已应用补丁的目标树出发，仅将两侧 `src/main.cpp` 的 CRLF 统一为 LF，使用当前官方 `refresh-patch --auto` 生成七份逐文件补丁。两次生成的补丁哈希一致；固定源码经相同换行规范化后应用七份补丁，23/23 文件与旧目标树（同样规范化）逐字节一致。此项仅是本机来源与补丁等价性检查；后续 H1-008 的实际 Conan/W3 结果见下条，不能以等价性检查代替它们。

### 对话 #2：七份补丁候选的 H1-008 实测

H1 在独立私有根核对 17 文件完整差异与候选树 `d346f4ae09cbe7e1fd17357ecb0f18d02d30983a`，官方 JC 对完整 PR 范围显示 `prdiff (17 个文件)`、rc0/pass。OHOS/armv8 Conan G2 与正式 W3 分别从源码建包、运行包消费者 10/10；W3 `setup.sh`、`build_and_test.sh` rc0，`.ci-result.json exit_code=0` 且日志 SHA-256 `c47d096f8c430508ce303402ca4d9b4d357af44023c2feef60c161f69875314f` 匹配。真实 Conan 包内 `bin/taptempo` 为 ELF64 AArch64，SHA-256 `a2597cca2e24b9c7c1f933034ac18be4ac42e3086f5009780714362478db23ae`。原始结果 tar SHA-256 `231b88781f4dcfeb40c6390b030ffc5ca8d9e8aec7f3ad36bb7140e83b16745f`，独立审计逐项核对。工具 `finish` rc1、`finalize-archive` 内部 rc2；G4 内的 L2/L4/L5 因包目录未定位而跳过，不能按顶部 PASS 标签写产物全检通过。真实 release tar、独立 W4 与官方 CI 待完成。

### 对话 #3：同一七补丁输入的 H1 上游测试与打包前验证

H1 在新私有目录以固定作者源码、七份候选补丁及已验 Catch2 v2.13.10 单头运行 CMake `test` 目标，真实返回 0、19/19 个上游用例及 95/95 条断言通过。原始补证包 `D:\华为鸿蒙\work\taptempo\evidence\h1-package-proof-008\taptempo-proof-008-JPClki-results.tar.gz` SHA-256 `3cbf1d1d59b0b39c86e7be4e043694301183ac72589ea1343df5cf4b99c1324d`，包含固定输入、构建与原始日志。此补证使用 H1-008 已验真实 Conan 包，未重跑 Conan 或正式 W3。

同轮官方 `verify-build` rc0、生成 `.verify-passed`，但质量报告 G2 实为 `0 pass / 1 warning / 0 fail`，错误文本 `taptempo: --version failed`；直接运行该相同 ELF 的 `--version` 返回 0 并输出 `Tap Tempo 1.4.5`。固定官方 `verify_build.py` 的 `_run()` 调用 `subprocess.run(..., timeout=15, **kw)`，G2 又传 `timeout=5`，同名参数异常被泛化 `except Exception` 吞成失败；因此这是 G2 工具误警，**不能将官方 G2 写为执行通过**。补证脚本据更严格 G2 条件退出 1，原始 warning 保留。

### 对话 #4：同一真实 Conan ELF 的官方打包续跑

H1 在上述唯一私有根复核原始质量报告、`.verify-passed`、输入 ELF 和官方脚本 SHA 后，仅续跑一次官方 `package_cli`，脚本退出 0、`package-cli.exit=0`；官方日志依次记录质量门禁、ELF 签名步骤和打包完成。原始续跑证据 `D:\\华为鸿蒙\\work\\taptempo\\evidence\\h1-package-resume-008\\taptempo-resume-008-results.tar.gz` SHA-256 `bc42053b33baea547221efdac01f1f978ffaceebf0e2221faff808db5023b3ae`。release tar SHA-256 `2d3eb9db42f8a6cf8a11657bb7a284e19a4b5d2aec3a8612b31792e8798f11a5`，含 AArch64 `bin/taptempo` 和许可证；debug tar SHA-256 `dd9358d2bb11e4fc54cbc72c0af77f6b9b021941736bd353fec305aea2589ce9`，含 AArch64 `taptempo.debug`。三个 tar 均经回收端独立计算 SHA-256，与原始清单一致。release ELF 不同于打包前输入，含 `.codesign` 节且无 `.unsigned` 成员，只能证明官方签名路径有可观察结果，**未独立验证密码学签名有效性**。这次仅是打包收尾，不改变原 `finish` rc1、官方 G2 warning、未完成 W5/staging 的事实。

## 固定源码与许可

- [TapTempo 官网](https://taptempo.tuxfamily.org/)指向作者的签名源码发布目录。本候选固定该目录的 [1.4.5 原始归档](https://mzf.fr/taptempo/download/1.4.5/taptempo-1.4.5.tar.gz) `taptempo-1.4.5.tar.gz`，22,156 字节，SHA-256 `6a471bc693516529dfc7b8bb3cf7e237dde675068cce0f0d99d2831e2e378753`；同目录 [分离签名](https://mzf.fr/taptempo/download/1.4.5/taptempo-1.4.5.tar.gz.asc) 833 字节，SHA-256 `ca66d0ada5b536b536ea9e9f7c756ab6a53e7a56ac92fc748853e68e20b23879`。签名文件已保存供后续密钥验证，当前未宣称已完成 GPG 信任验证。
- 作者托管归档与 [Debian 保存的原始归档](https://deb.debian.org/debian/pool/main/t/taptempo/taptempo_1.4.5.orig.tar.gz) 逐字节相同；该 SHA 同时与 Debian [1.4.5-3.1 `.dsc` 校验清单](https://deb.debian.org/debian/pool/main/t/taptempo/taptempo_1.4.5-3.1.dsc) 的 `Checksums-Sha256` 字段相同。配方选作者域名以满足当前框架 PF7 源 URL 门禁。解包根目录为 `taptempo-1.4.5/`。
- 原始包 `LICENSE.txt` 为 GPL 第 3 版全文；源码文件头和 README 声明 GPLv3 或更新版本，配方使用 SPDX `GPL-3.0-or-later`。Catch2 v2.13.10 单头仅进入 H1 测试输入包，遵循其 BSL-1.0 许可；不进入最终 Conan 包。

## 适配范围

- 七份逐文件补丁由当前官方 `refresh-patch --auto` 在隔离副本中生成，将 `cmake_minimum_required` 从 3.1 提至 3.5，并提供可选 NLS 与测试开关。七份补丁应用后的 23 个源码文件，与先前固定补丁的结果在仅将 `src/main.cpp` 行尾统一为 LF 后逐字节相同；生成和对照原始证据在本地 `work/taptempo/patch-regen-008/lf-experiment/`，该工作目录不进入 PR。
- 增加 `TAPTEMPO_ENABLE_NLS` 与 `TAPTEMPO_BUILD_TESTS` 两个 CMake 开关。配方打包时关闭测试，原生 H1 作业另用固定 Catch2 v2.13.10 单头执行原有测试。
- 配方默认 `with_nls=False`，避免在未核实目标端 `libintl.h`/链接及构建端 `msgfmt` 前引入未经确认的依赖。关闭 NLS 时 gettext 文本返回原始英文消息，不产出 `.mo` 翻译文件；节拍、参数和游戏逻辑保持原样。若 H1 证明 gettext/Intl 可用，再测试 `with_nls=True` 并补足本地化验收。
- `source()` 默认从固定作者 URL 下载并验证 SHA；H1 隔离执行可设置 `TAPTEMPO_SOURCE_ARCHIVE` 指向同一已验哈希的本地归档。固定归档中的 `src/main.cpp` 为 CRLF，而当前官方逐文件补丁生成器输出 LF 上下文；配方仅在该文件精确匹配固定原始 SHA 时将 CRLF 规范为 LF，再应用七份自动补丁，并校验规范化后 SHA。`test_package` 跑包内可执行文件，`can_run()` 为假时显式失败。

## 已有本机证据

在全新解包的精确补丁树上，`git apply --check` 与 `git apply` 均返回 0。Windows UCRT64 g++ 15.2 直接编译 CLI 与上游 `optionsTest`，两条构建均返回 0；Catch2 报告 19/19、95 断言，消费者驱动 10/10。另在临时 ASCII 盘符中使用 CMake 4.1.2、MinGW Makefiles 和同一 g++ 对该树执行配置、构建和上游 `test` 目标，三阶段返回码均为 0，`test` 再报告 19/19、95 断言。原始日志和退出码位于团队工作区 `work/taptempo/local-build/host-build/`、`work/taptempo/local-build/cmake-logs/`；它们不证明 OHOS、Conan 或官方 CI 成功。

## H1 目标平台证据

- 003：OHOS Clang 15 / CMake 4.1.2 原生配置、构建与上游 `test` 目标均 rc0；19 个 Catch2 用例、95 条断言通过，原生消费者 10/10。Conan 2.29.1 使用 OHOS armv8 profile 从相同源码构建并打包，包内可执行文件为 ELF64 AArch64，SHA-256 `a2597cca2e24b9c7c1f933034ac18be4ac42e3086f5009780714362478db23ae`。`conan create` 在计时敏感消费者测试只过 7/10，因此该命令 rc1，不能将其写成通过。
- 004：原生与 Conan 包内二进制 SHA 相同；在同一 H1 上对三个计时场景做 24 次进程诊断，均退出 0，实际送入间隔接近请求值。此轮是诊断，不等于完整消费者测试通过，也不能证明 003 失败原因。
- 005：在无其他本项目编译/调度作业时，复用 003 已建 Conan 包和同一 `test_package`，不重建；一次 `conan test` rc0，10/10 通过。原始 13/13 文件 SHA-256 清单已核对，旧 003 失败记录仍保留。
- 006：官方框架 `d47316a87dce1998ebce15efd5eda305d8ae4d47` 的隔离副本应用完整 13 文件候选并逐 blob 核对。正式 `finish` 内 Conan G2 从官网成功下载源码、建包并运行消费者 10/10；W3 `setup.sh` 与 `build_and_test.sh` 均 rc0，工具生成的 `.ci-result.json` 为 exit_code=0，日志 SHA-256 `820e0b5f00655f070f2ee97d7362dfe09ddf14080b222c3e890f470a6fc4a696`。完整 `finish.exit=1`：Step6 缺 packaging、Step8 `gen_summary` 抛出 `'str' object has no attribute 'append'`，Step10 缺 `.staging-verified`；共享验证器的 G4 无 package ID、L2/L4/L5 无 cache 路径却写 PASS，均不算真正通过。原始证据包 71/71 SHA 核对，存于团队工作区 `work/taptempo/evidence/h1-006/`；H1 自动追加的两行 notes 状态已合并进本段。
- 007：固定 `2a576b72` 输入的阶段 1 在先前真实 AArch64 包内二进制上单次 10/10；阶段 2 独立 OHOS/armv8 Clang 15 `conan create` 退出 0，`test_package` 10/10。第一版证据收集器找错消费者 JSON 目录而退出 1，同 UID 只读收集器找回原始 10/10 JSON；未重跑 Conan。这些结果仅属于 007 输入，当前七补丁候选以随后 008 的独立结果为准。
- 008：当前七份自动补丁候选在私有根从固定源码完成 OHOS/armv8 Conan G2 与正式 W3，二者消费者 10/10；JC `prdiff (17 个文件)`/pass，W3 两脚本 rc0，CI 结果 exit_code=0、日志 SHA 与回执相符。`finish` 整体 rc1，独立 G0 clean-verify、归档、W5/summary 和 staging 仍有缺口。随后同输入上游 Catch2 19/19 补证见“对话 #3”；不能将补证视作整个 `finish` 通过。

## 待核

1. 处理当前候选 `finish` 的真实未完成项：独立 clean-verify 首先未找到原始 tarball，且官方脚本固定调用 `./configure`/`make`，不适用于本库 CMake 构建；保留实际失败并向审阅者披露具体例外，不伪造脚本或门禁结果。W5/summary 和 staging 仍未完成；保留首次 rc1 原始结果，不在未验证前写全流程通过。
2. 官方 `verify-build` G2 假 warning 必须连同直接执行的反证披露，不覆盖原报告。补准确测试报告、状态与收尾，并对最终候选做独立 W4；官方远端 CI、PR 审核与发布结果仍待办。
3. H1 本地化构建与 French `.mo` 运行，如可行再考虑将 NLS 作为默认能力；未验收前明确保留限制。
