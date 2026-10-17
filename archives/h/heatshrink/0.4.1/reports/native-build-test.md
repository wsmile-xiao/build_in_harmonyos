# heatshrink 0.4.1 原生探索与上游测试（设备实测）

- 日期: 2026-09-04
- 设备: OHOS aarch64（HarmonyPC 单端模式）
- 工具链: clang 15.0.4 (`/data/service/hnp/bin/clang`, Target aarch64-unknown-linux-ohos),
  GNU ar 2.45 (`/data/service/hnp/bin/ar`), GNU Make 4.4.1, git 2.45.2
- 源码: 官方 GitHub v0.4.1 tag tarball
  SHA-256 `7529a1c8ac501191ad470b166773364e66d9926aad632690c72c63a1dea7e9a6`
- 任务源码副本: `$HOME/tmp/heatshrink-0.4.1/src/heatshrink-0.4.1`（探索期修改前为纯净解压）

## 1. 原生构建（阶段 7.2 第 1 步）

| 尝试 | 命令 | 结果 |
| --- | --- | --- |
| 1 | `make -j1` | 失败: `make: cc: No such file or directory`（设备无 `cc`，首错证据） |
| 2 | `make CC=clang -j1` | **成功**，零修改、零警告错误（仅上游代码自身的 -Wstrict-prototypes 警告，位于 greatest.h 测试主宏） |

产物: `heatshrink`（CLI）、`libheatshrink_dynamic.a`、`libheatshrink_static.a`、
`test_heatshrink_static`、`test_heatshrink_dynamic`。

## 2. 上游测试（阶段 7.2 第 2 步）

统计单位: greatest 运行器的单个 test case（含参数化实例）。
取数命令: `./test_heatshrink_static | grep -E "Total:"`、`./test_heatshrink_dynamic | grep -E "Total:"`。

| 套件 | TOTAL | PASS | FAIL | SKIP | NOT_RUN | 断言 |
| --- | --- | --- | --- | --- | --- | --- |
| test_heatshrink_static（静态分配构建） | 1600 | 1600 | 0 | 0 | 0 | 6,938,281 |
| test_heatshrink_dynamic（encoding 11 / decoding 23 / regression 4 / integration 12244） | 12282 | 12282 | 0 | 0 | 0 | 96,647,621 |
| **合计** | **13882** | **13882** | **0** | **0** | **0** | **103,585,902** |

- 原始日志: `upstream-test-static.log`、`upstream-test-dynamic.log`（任务 tmp，摘要摘录至
  reports/native-build-test.md 与 PR 正文）。
- properties 属性套件: `test_heatshrink_dynamic_theft.c` 全部位于
  `#ifdef HEATSHRINK_HAS_THEFT`；上游默认 Makefile 注释掉相关 CFLAGS、不链接可选库
  libtheft，编译为空翻译单元 → 贡献 0 用例（与上游默认口径一致，非跳过）。

## 3. CLI 真实行为（软件级 commands.json 依据）

```sh
./heatshrink -h            # 输出 heatshrink version 0.4.1 ... 用法（exit 1）
./heatshrink -e -v -w 8 -l 4 sample.txt sample.hsh   # 940 -> 120 字节 (87.23%)
./heatshrink -d -v -w 8 -l 4 sample.hsh sample.out   # 120 -> 940 字节
cmp sample.txt sample.out  # 一致 (ROUNDTRIP_OK)
```

## 4. test_package 消费者预检（配方定稿前）

- `test_heatshrink_dynamic.c`: `clang -std=c99 -Wall -Wextra -Werror -DHEATSHRINK_DYNAMIC_ALLOC=1`，
  链接 `libheatshrink_dynamic.a` → **6/6 PASS**（SUMMARY total=6 pass=6 fail=0）
- `test_heatshrink_static.c`: 同上 `-DHEATSHRINK_DYNAMIC_ALLOC=0`，链接
  `libheatshrink_static.a` → **3/3 PASS**（SUMMARY total=3 pass=3 fail=0）

## 5. 结论

上游源码零修改即可在 OHOS 原生构建与测试全通过；不需要平台补丁。
适配面收敛为: 配方传 `CC=/AR=`（R33 conf 绑定）、**规避** `make CFLAGS+=...`
命令行追加（会使上游 -O3 等静默丢失，见知识草稿）、组件化声明两种分配模式、
CLI 登记 commands.json。
