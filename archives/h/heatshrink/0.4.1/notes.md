# heatshrink 0.4.1 — OHOS 适配笔记

- 上游: https://github.com/atomicobject/heatshrink （v0.4.1 tag）
- 源码: https://github.com/atomicobject/heatshrink/archive/refs/tags/v0.4.1.tar.gz
- SHA-256: `7529a1c8ac501191ad470b166773364e66d9926aad632690c72c63a1dea7e9a6`
- 许可证: ISC
- 主体语言: C（99），构建系统: 顶层 Makefile（无 configure/CMake/pkg-config）
- 依赖: 无（仅 libc）

## 上游产物形态

`make all`（默认目标）构建:

1. `heatshrink` — 独立 CLI 编码/解码器（stdin/stdout 或文件参数）
2. `libheatshrink_dynamic.a` — `HEATSHRINK_DYNAMIC_ALLOC=1`（运行时分配，默认）
3. `libheatshrink_static.a` — `HEATSHRINK_DYNAMIC_ALLOC=0`（固定缓冲，嵌入式）
4. `test_heatshrink_static` / `test_heatshrink_dynamic` — greatest 测试运行器

`make install` 安装 CLI + 两个静态库 + 4 个头文件
（heatshrink_common.h / heatshrink_config.h / heatshrink_encoder.h / heatshrink_decoder.h）。

## 关键适配事实

1. **无上游补丁。** Makefile 全程使用 `${CC}`；`ar` 虽为字面量，但配方通过
   `make AR=...` 无法覆盖字面量，而实际验证中 PATH 内 `ar`
   （`/data/service/hnp/bin/ar`，GNU Binutils 2.45）与 clang 15 工具链工作正常，
   因此无需修改上游源文件。配方只传 `CC=/AR=`（R33：取自 Conan conf）。
2. **最小构建参数。** 设备无 `cc`（`make: cc: No such file or directory`），
   加 `CC=clang` 后一次构建成功；CI 场景由 conf
   `tools.build:compiler_executables:c` 提供。构建命令为
   `make CC=<conf cc> AR=<conf ar|ar> all -j1`，严格保持上游 Makefile 的
   CFLAGS（含 -O3）。**不要**用命令行 `CFLAGS+=...` 追加 flags：GNU make
   命令行变量优先级最高，会使上游 Makefile 的 `CFLAGS +=` 追加全部失效，
   库退化为 -O0；上游 `heatshrink_decoder_free` 对 NULL 的死代码解引用在
   -O0 显形，greatest 的 `decoder_sink_should_reject_null_input_pointer`
   用例（`free(alloc(256,4,4)=NULL)`）即段错误（已在设备 A/B 实证：
   -O3 12282 全过，-O0 必现）。该坑已沉淀知识草稿。
3. **上游测试真实执行。** CI worker 即 OHOS 设备（profile 使用
   `/data/service/hnp/bin` 工具链路径），因此在配方 `build()` 内直接运行
   `./test_heatshrink_static` 与 `./test_heatshrink_dynamic`（即 `make test`），
   失败即 conan create 失败。设备实测: static 1600/1600 PASS，dynamic
   12282/12282 PASS，合计 13882 用例、103,585,902 断言、0 失败 0 跳过。
4. **properties 属性套件说明。** `test_heatshrink_dynamic_theft.c` 整体位于
   `#ifdef HEATSHRINK_HAS_THEFT` 内，上游默认 Makefile 将相关 CFLAGS 注释掉、
   不链接可选库 libtheft，故该文件编译为空翻译单元，贡献 0 个用例。本适配与
   上游默认口径一致，不引入额外依赖。
5. **两种分配模式必须二选一链接。** 两个库导出同名核心 API
   （sink/poll/finish/reset），但状态结构体布局随 `HEATSHRINK_DYNAMIC_ALLOC`
   不同。消费者同时链接两个库会造成符号二义与布局错配，因此 `package_info()`
   用两个 component（`heatshrink::dynamic` / `heatshrink::static`）分别声明，
   并各自携带 `HEATSHRINK_DYNAMIC_ALLOC=1/0` define；test_package 用两个
   独立可执行文件分别消费两种模式。
6. **CLI 产物。** `heatshrink` CLI 随包安装在 `bin/`，软件级
   `archives/h/heatshrink/commands.json` 已登记（R38）。真实行为验证:
   `-e -w 8 -l 4` 将 940B 重复文本压至 120B（87.23%），`-d` 解压后与原文
   逐字节一致（cmp 通过），`-h` 输出版本 0.4.1 与用法（exit 1）。
7. **上游不提供共享库构建规则**，`options = {"shared": [False]}` 如实声明。

## 与历史/知识库的关系

- 仓库内无 heatshrink 历史配方（recipe-search 语料 0 条），本包为首次适配。
- prescan 零发现（构建系统 make，有测试）。
- 调试过程中发现可跨库复用的 GNU make 变量优先级坑（命令行 CFLAGS 覆盖上游
  Makefile 的 CFLAGS +=），已沉淀知识草稿：
  `knowledge/drafts/DRAFT-heatshrink-0.4.1-make-cflags-commandline-override.md`。
