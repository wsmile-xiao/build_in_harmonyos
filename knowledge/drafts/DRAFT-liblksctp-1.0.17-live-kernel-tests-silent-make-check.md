# autotools 包上游测试为内核实时用例且未注册 TESTS= 时 make check 静默零执行

- **草稿 ID**: DRAFT-liblksctp-1.0.17-live-kernel-tests-silent-make-check
- **来源**: liblksctp/1.0.17 适配（任务 14796；上游 sctplab/lksctp-tools）
- **分类**: ohos / c / autotools / test-harness / live-kernel / platform-triple / signing
- **状态**: 草稿（随 PR 提交，待审核）

## 问题 / 错误签名

- `grep '^TESTS' */Makefile.am` 为空、测试程序写成 `noinst_PROGRAMS` → `make check`
  「成功但零执行」，给出虚假绿色。
- 随包 `bin/config.guess` 过老，HarmonyOS 上 `uname -s` 返回 `HarmonyOS`
  → `configure: error: cannot guess build type`；`config.sub` 不认 `linux-ohos`。
- 直接实跑测试程序时全 FAIL，但根因是内核未启用所需协议（本例 SCTP），
  而非「用例本身不通过」。

## 根因

autotools 工程若把测试程序写成 `noinst_PROGRAMS`（而非 `check_PROGRAMS` + `TESTS=`），
`make check` 不含任何测试目标，会**静默零执行**；其真正驱动是上游自定义目标
（lksctp-tools 为 `src/func_tests` 的 `v4test`/`v6test`）。这些用例又常是
**内核实时（live-kernel）**用例——每条都要
`socket(AF_INET, SOCK_STREAM, IPPROTO_SCTP)` 起真实关联，依赖内核启用对应协议。
CI worker 内核通常未启用该协议，直接实跑会全 FAIL；据此归因成「用例不通过」会误导
评审，静默删用例/缩分母则违反规则 4。

同源平台坑：随包 `bin/config.guess`（本例 2015 版）在 HarmonyOS 上无法识别系统；
`bin/config.sub` 的 KERNEL-OS 列表无 `linux-ohos*`。

## 最小修复方案

在 `archives/l/liblksctp/1.0.17/**` 范围内：

1. **E007 双保险**：打归档自带 `0001-bin-config.guess.patch`（加 HarmonyOS 分支）+
   `0002-bin-config.sub.patch`（加 `linux-ohos*`）；并在 `generate()` 显式传
   `--build=<arch>-unknown-linux-gnu`、`--host=<arch>-unknown-linux-ohos`
   （build 侧 gnu、host 侧 ohos；两侧都写 ohos 会被 `config.sub` 误判）。
   框架的 `patch-autotools-ohos.pl` 在 CI worker 上取不到，故不依赖它。
2. **测试如实驱动**：`--enable-tests` 全量编译测试程序；`build()` 内先用上游自带
   资源探针 `checksctp` 判定内核是否启用 SCTP——可用则逐条实跑 v4 用例并输出
   `§10 通过 N / 失败 M / 共 K`；不可用则逐条标记「资源未执行（内核未启用 SCTP）」，
   不删用例、不缩分母。
3. **消费者确定性断言**：`test_package` 链接 `-lsctp` 调用库内**纯用户态** API
   `sctp_getaddrlen(AF_INET/AF_INET6/AF_UNSPEC)`（`addrs.c:135`，按地址族返回
   `sizeof`，不碰 socket/内核），断言返回值；同时验证头闭包、链接与运行期可加载
   （`.codesign` 签名有效）。库本身不依赖内核 SCTP 即可编译、安装、被链接。
4. **签名（E077）**：`package()` 对 `libsctp.so*`、`libwithsctp.so*` 与 bin 工具
   统一剥旧签名段 + `binary-sign-tool` 自签。

## 验收判据

- `grep '^TESTS' */Makefile.am` 为空且 `noinst_PROGRAMS` 命中 → 确认 `make check` 静默。
- 上游 `checksctp` 探针给出内核 SCTP 可用性；构建日志出现 §10 汇总行。
- `test_package`（链接 + 运行 `sctp_getaddrlen` 断言）exit 0。
