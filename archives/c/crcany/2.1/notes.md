# crcany 2.1 适配笔记

## 状态

- 分支：`feat/crcany-2.1`
- 上游：<https://github.com/madler/crcany>（tag `v2.1`，2021-09-19，commit `41db4b3`）
- 许可证：Zlib
- 当前状态：工作树已完成，真机预检待 HMBS 后台执行；本轮未提交、未推送、未创建 PR

## W0 依赖检查

crcany 是纯 C99 项目，无第三方 Conan 依赖（仅需系统 C 工具链：clang/make/ar，均由真机与 HMBS 基建提供）。
无需先行适配依赖库。

## 源码与构建系统

- 源码 URL：<https://github.com/madler/crcany/archive/refs/tags/v2.1.tar.gz>
- SHA256：`e07cf86f2d167ea628e6c773369166770512f54a34a3d5c0acd495eb947d8a1b`
  （以官方 tag 归档实测 115037 字节计算；CI 会继续用该值校验）
- 构建系统：纯 GNU Makefile，无 configure、无 `make install`
- 默认目标构建 `crcany`、`crctest`、`crcall`、`crcadd`、`mincrc` 与生成式 `src/` 目录
- 可调用例程：`model.[ch]`、`crc.[ch]`、`crcdbl.[ch]`、`crcgen.[ch]`；
  可执行程序：`crcany.c`（按名计算 CRC）、`crcall.c`/`crcadd.c`（生成代码）、
  `crctest.c`（官方校验）、`mincrc.c`（定义缩写）
- `CFLAGS=-O3 -Wall -Wextra -Wcast-qual -std=c99 -pedantic`，OHOS clang 15 可直接编译

## 打包决策（纯库，不发工具）

只打包库消费者需要的文件：

- `lib/libcrcany.a`（由 `model.o`、`crc.o`、`crcdbl.o`、`crcgen.o` 归档）
- `include/model.h`、`include/crc.h`、`include/crcdbl.h`、`include/crcgen.h`
- `licenses/LICENSE`
- `res/upstream_test_result.json`（构建期上游实测计数，供 test_package 原样重发证据）

`crcany` 等可执行文件会随上游默认目标构建（`make test` 需要它们），但不复制到 `bin/`。
这样本 PR 保持纯库包，不触发软件级 `archives/c/crcany/commands.json` 要求，
也不修改版本目录之外的软件级文件。上游只支持静态构建，
配方保留 `shared` 选项接口但在 `shared=True` 时抛 `ConanInvalidConfiguration`。

## 上游测试（含证伪说明）

`make test` 做两件事：

1. 把 `allcrcs-abbrev.txt`（113 个 CRC 模型定义）喂给 `./crctest`，
   每个模型做 bit、residue、byte、word、combine 五项校验；
2. 运行生成代码检查 `src/test_src`（由 `crcall` 在构建中生成并编译）。

该目标无需联网（联网的 `getcrcs` 对比只在独立的 `checklists` 目标里）。

证伪要点（已在配方里落实）：

- `crctest.c` 的 `main` 无论校验成败都 `return 0`，
  即使打印 `** verification failed`，`make test` 退出码仍为 0。
  因此配方不只看退出码，必须解析输出：
  要求出现 `-- all good`，且 bit/residue/byte/word/combine 五组
  `verified … out of … usable` 计数全部等于可用模型数、且大于 0，
  否则抛错阻断构建。
- 要求 `allcrcs-abbrev.txt` 非空、`make test` 输出非空，
  防止空固件比空输出的假通过。
- 配方把解析出的 `discovered/executed/passed`（可用模型数）写入
  `upstream_test_result.json`，随包带到 `res/`，test_package 原样重发，
  保证 `HMBS_UPSTREAM_TEST_RESULT` 的数字来自真机实测输出。

消费者测试 `test_package/test.c` 覆盖（5 个检查）：

- `read_model` 解析 CRC-32/ISO-HDLC 完整参数串（含 width/check/name 校验）
- `crc_bitwise` 计算 `"123456789"` 等于标准值 `0xCBF43926`
- `crc_bytewise` 同上
- `crc_wordwise` 同上（含端序探测与建表）
- `crc_combine` 分段合并等于整体计算

每个检查打印 `PASS … 0xCBF43926`（非零真实值），空输出或 PASS 数不符都会失败。

## 本机验证（Windows 宿主）

已完成：源码下载与 SHA256 复算、归档大小确认、构建系统与测试入口核对
（`make test` 目标、`crctest` 行为、`allcrcs-abbrev.txt` 113 行）、
配方与 YAML 语法检查、补丁无（`patches_applied: []`，无需补丁）。

宿主是 Windows 且无 OHOS 工具链，不在本机运行 `conan create`；
`conan create`、test_package 与上游测试以 HMBS 真机预检日志为准，
通过率数字待证据轮回填，不在本机猜测。

## 风险与限制

- 本包只发静态库；需要 `crcany` 命令行工具的场景不在本 PR 范围。
- `make test` 耗时随模型数线性增长，属秒级到分钟级，无需调超时预算。
- Windows 检出会把 `archives/l/libXext` 与 `archives/l/libxext`
  视为同一目录而显示脏文件，属上游大小写同名目录在 Windows 的固有冲突，
  与本 PR 无关；本 PR 只新增 `archives/c/crcany/2.1/` 文件。
