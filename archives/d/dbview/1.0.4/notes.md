# dbview 1.0.4 适配笔记

## 编译环境

- 构建系统: makefile（上游手写 Makefile，无 configure）
- 编译日期: 2026-09-11
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，profile `ci/conan/profiles/ohos-aarch64`）
- 目标平台: OHOS 6.0 / armv8（aarch64）
- 状态: built（conan-verify/W3 通过；release upload 未确认）

## 编译步骤

上游 Makefile 只有 `all/dbview/depend/install/clean/clobber` 目标，没有 configure 与可用的
install（`install` 以 `-o root -g root` 安装，并把字面量 `MAN=man` 当 man page 属主）。配方
不调用 `make install`，而是：

1. `get(self, **self.conan_data["sources"], strip_root=True)` 取官方 tarball（顶层目录
   `dbview-1.0.4/`）；
2. `apply_conandata_patches(self)` 应用 `patches/0001-dbview.c.patch`；
3. `make -j1 CC="<profile clang>" CFLAGS="<GnuToolchain cflags + -D defines>"`（R9：三目标
   Makefile 工程保持单 job）；
4. 显式安装 `bin/dbview` 与 `share/man/man1/dbview.1`。

原生（裸 make）与 Conan 两条路径都实跑过，命令与结果见 `manifest.yaml` 的
`validation.native_build` / `validation.patched_native_build` / `validation.conan_create`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Conan 首轮 create 失败：`clang-15: error: no such file or directory: 'NDEBUG'` | `GnuToolchain.defines` 返回裸宏名（Release 下 `['NDEBUG']`），`-D` 前缀由消费方补；raw Makefile 配方按 `tc.cflags + tc.defines` 直接相加就产生非法参数 | 逐项补前缀：`tc.cflags + [f"-D{d}" for d in tc.defines]`（知识条目 E573） |
| 2 | 上游 `make CC=clang` 有 3 条 `optimization level '-O6' is not supported; using '-O3'` 告警 | 上游 Makefile 写死 `CFLAGS=-O6` | 配方用 profile 的 `CFLAGS` 覆盖上游默认值，告警消失（原生裸 make 仍为 17 条告警，Conan 构建 14 条） |
| 3 | 查看数据库成功时退出码为 1、文件打不开时退出 0 | `db3_process()` 返回 TRUE/FALSE 布尔值，`main()` 直接 `exit()` 该值 | 补丁 0001 取反：`exit (!db3_process(...))`；与 Debian dbview 的 `negate_exit_code` 补丁同源 |
| 4 | 上游 tarball 内没有 COPYING/LICENSE | 1.0.4 发行包只带 Makefile、源文件、man page 与格式说明文本 | 许可证按 Makefile 声明记 `GPL-2.0-or-later`，包内不安装 license 文件（不伪造上游未提供的文件） |

## 源码修改

1 个补丁，无平台条件编译（R8）：

- `patches/0001-dbview.c.patch`：`main()` 末尾
  `exit (db3_process (dbfile, flags, delim));` → `exit (!db3_process (dbfile, flags, delim));`
  （附带说明性注释）。修正后成功退出 0、失败退出 1。

## 依赖版本

- 编译依赖：无第三方库（profile 中的 clang 15.0.4）
- 运行依赖：`libc.so`（OHOS musl）

## 验证结果

命令与原始结果以 `manifest.yaml` 的 `validation.*` 为权威副本（本节不复制）：

- `validation.source_fetch`：官方源 HTTP 200 / 9857 字节 / sha256 `bca41716…`
- `validation.upstream_ledger`：上游测试入口计数 0
- `validation.conan_create`：`conan create` exit 0，补丁应用 1 条
- `validation.test_package`：`TOTAL=22 PASS=22 FAIL=0`（标记行 `dbview test_package summary`）
- `validation.l1e_negative`：破坏产物后 `TOTAL=22 PASS=2 FAIL=20`、exit 1

工具侧的告警、跳过与未覆盖范围如实记录（均为非阻断项；完整命令、原始输出与判据见
`reports/conan-verify-supplement.md`）：

- **conan-verify 的 G4/L2/L4/L5 四行是 `⏭️ 跳过（无 cache 路径）`**，G4 另打印
  `⚠️ 无法找到程序包 ID`；报告行同时显示 `✅ PASS` 是工具文案缺陷，以跳过行为准。已按
  workflow 第 7.2 节对同一 SHA 的产物**人工补测**：G4 产物清单、L2 消费者实测 22/22、
  L4 `readelf` 加固属性、L5 产物 sha256 基线与 man page 字节比对。
- **W3 日志中 `L4_RESULT=warn: dangerous functions in patches`**：命中对象是补丁里作为
  **unified diff 上下文行**出现的上游原有 `strcpy`（↔ 上游 `dbview.c:129`）；对补丁**新增行**
  做 `grep -E '^\+' | grep -cE 'strcpy|strcat|sprintf|gets|system'` 计数为 **0**。该告警源为
  `ci/conan/build_and_test.sh` 对补丁**整文件**的 `grep -rlE`（无 `^+` 锚定），属扫描器误报，
  按仓库审计分级表为非阻断项（审计已复核确认）。
- **conan-verify 的 G0 另有 `E490 未在配方中处理` 提示**：G0 依据 `init-build` 误判的构建系统
  （`autotools`）预查询知识图谱所致；本包无 `configure` 也无任何 autotools 脚本
  （`Makefile` 手写，无 `configure.ac`），该风险不适用。构建系统以版本级 `manifest.yaml`
  的 `build.system: makefile` 为准。
- **`reports/conan-create.log` 被缓存轮覆盖**：`finish` 内嵌重跑后该文件由采信轮的 13019 B
  变成缓存命中轮的 5421 B（`Calling build()`/`RUN: make`/`Apply patch` 三项计数由 1/1/1 变 0/0/0）。
  采信轮干净构建日志按 workflow 第 7.2 节在每次 `finish` 前留存任务私有副本，命名规则为
  `$HOME/tmp/dbview-1.0.4/conan-create-<该轮 SHA 的短哈希前缀>.log`（本任务统一用
  `git rev-parse --short` 的默认长度，实测为 **10 位**，例如
  `conan-create-f1dcfc425a.log` ↔ SHA `f1dcfc425aed47210b186933e0c4c5fa458004b9`）。
  该目录下的 `conan-create-*.log` 即全部采信轮副本，可直接用 glob 定位而不必推算文件名；
  本包构建输入多轮逐字节未变、产物 `bin/dbview` 的
  sha256 各轮一致为 `8f8fdb4a60ec56f9d40eeb2d6d1998f65322610654c663e39c1d6a9fbfb59ddf`。
  凡引用"采信轮 create 日志"处的指针以这些副本为准。
- **CI 检出阶段禁止新增二进制文件（本任务实测）**：首个 PR 版本把 8 个 `.dbf` 夹具作为二进制
  文件提交，CI 的 `checkout-pr` 步骤直接失败——平台生成的 PR diff 对新增二进制文件只写
  `Binary files /dev/null and ... differ`，**不含 `GIT binary patch` 数据**，`git apply` 报
  `error: missing binary patch data for '...fixtures/basic.dbf'`（8 条），随后 `patch` 兜底又因
  `Unknown option 'fuzz=3'` 失败，最终判「PR diff 无法应用」（CI run #44073）。
  处置：`.dbf` 夹具改为不提交，由 `test_package/fixtures/make_fixtures.py`（纯标准库 Python，
  源码随 PR 提交）在测试运行时逐字节确定性重建；已实测生成结果与原先提交的 8 个夹具
  sha256 全部一致，22 项用例仍全绿。本仓库全部 `test_package` 均无二进制夹具，本包现在与之一致。
- **未覆盖范围**：`share/man/man1/dbview.1` 只做安装与字节比对，未做 man 渲染验证（设备上无
  `man`/`mandoc` 前端，`groff` 虽存在但未纳入验证）；该产物属正交的文档文件。L2 的 smoke
  判定使用 `--version`，功能面由 `test.sh` 的 22 项用例覆盖。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/dbview` | CLI 可执行文件，ELF 64-bit LSB arm64，PIE + BIND_NOW + RELRO + NX |
| `share/man/man1/dbview.1` | 上游 man page（原样安装） |

## 注意事项

- `package_type = "application"`；`commands.json` 位于软件级目录（R38）。
- 上游未修复的限制（本次刻意不改，避免扩大补丁面）：`db3_process()` 在
  `db3_read_dic()` 失败时仍返回 TRUE，因此版本字节不受支持的文件（如 dBase IV `0x8B`）
  只打印诊断、退出码仍为 0；`main()` 用 `strcpy()` 把路径拷进 256 字节栈缓冲区。
- 上游源码是 1987–2006 年的 K&R 风格 C，clang 15 会报 14 条原型相关告警（10 条
  `-Wdeprecated-non-prototype` + 4 条 `-Wknr-promoted-parameter`）；非致命，未改源码。

## 发现与知识

- ✅ raw Makefile 配方手工拼 `GnuToolchain` 的 CFLAGS 时 `defines` 是裸宏名，缺 `-D` 前缀会被 clang 当成源文件 # knowledge_ref: E573
- ✅ 上游 CLI 直接用内部布尔返回值当退出码会导致成功/失败退出码整体反转，需按发行版同源补丁取反后再断言 # reference: conandata.yml patches[0]
- ✅ 上游零测试入口按可审计台账记 0，替代验证用独立构造的字节级夹具加人工核对黄金输出 # reference: knowledge/drafts/DRAFT-cute_files-1.0.0-upstream-zero-test-ohos-validation.md
