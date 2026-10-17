# 测试报告 — dict 1.13.3 (HarmonyOS PC, aarch64)

## 结论

- 上游测试（`make test`）：**47/47 (100%) 通过**（DICTFMT 21 + DICTD 17 + DICTZIP 9）
- test_package 消费者冒烟：**通过**（dict/dictd 版本 banner、dictzip→dictunzip 往返、dictfmt+dictd `--stdin2stdout` 协议应答）
- 全量通过率口径：`executed_passed_total/source_declared_total = 47/47 (100%)`
- 完整枚举台账见 `reports/upstream-test-ledger.md`；权威执行日志见 `reports/conan-create.log`（conan create 内 `make test` 段）

## 上游测试入口

- 入口命令：`make test`（Makefile.in `test:` 目标 → `cd test && sh dictd_test && sh dictzip_test`）
- 说明：上游未提供 `make check` 目标（`make check` 无此规则）

### DICTFMT 段（dictfmt 词典格式化/索引生成，21 项）
`-c5 == -t`、`-c5.utf8`、`-c5 == -X`、`c5 == e/f/j/p`、`c5 == expected` 等基础断言 8 项；
`smiley_1..5`、`hello_1..5`、`cyrillic_1`、`mixedcase_1`、`indexdata_1` 词典构建比对 13 项。

### DICTD 段（dictd 服务器协议应答，17 项）
`hello_1..5`、`smiley_2/4/5`、`cyrillic_1/3/4`、`mixedcase_1`、`indexdata_1`、`limits_1`、
`defstrat_1/2` 共 16 个 server 用例（dictd + dict + 期望文件比对），外加
`cyrillic_1 nodetach nofork`（绑定 localhost:26281）1 项。

### DICTZIP 段（dictzip 压缩/随机访问解压，9 项）
尺寸×步长：116630×11663、1000000×500000、100000×25000、10000×250、0×1、1×1、10×1、100×1、1000×25。

## 消费者验证（test_package，R34 实质依赖）

`test.sh` 通过已安装产物调用公开 CLI：
1. `dict --version` / `dictd --version` → 断言输出含 `1.13.3`（上游设计为 banner 后 exit 1，故断言 banner 文本）
2. `dictzip -k` → `dictunzip -f` 往返 → `cmp` 字节一致
3. `dictfmt -c5` 构建词典 → `dictd -i --stdin2stdout` 应答 DEFINE → 断言
   `definitions retrieved` 与定义行

证据：`reports/conan-create.log` 尾部 test_package 段（`dictzip roundtrip passed`、
`dictd stdin2stdout passed`、`SMOKE_OK`）。

## 双口径说明

| 口径 | 数量 |
|------|------|
| source_declared_total | 47 |
| configured_executable_total | 47（无互斥分支/条件宏/禁用条件） |
| executed_passed_total | 47 |
| failed / uninstantiated | 0 / 0 |
| 全量通过率 | 47/47 (100%) |

## 环境

- 平台：HarmonyOS PC aarch64（os=OHOS, os.version 6.0）
- 工具链：clang 15.0.4 / clang++ libc++ / llvm-ar
- 构建：conan 2.32.0 + profile `ci/conan/profiles/ohos-aarch64`；构建目录
  `/data/storage/el2/base` tmpfs（HMDFS 临时文件/getcwd 语义不可靠）