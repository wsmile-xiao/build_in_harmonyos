# lucy 1.20 适配笔记

## 编译环境

- 上游版本：1.20（tar 包解出目录名 `lucy-1.20p`）
- 构建系统：裸 Makefile（目标 `all` / `lucy` / `beep` / `clean`；**无** configure / install / check）
- 编译日期：2026-09-28
- 编译器：clang 15.0.4（OHOS SDK 26.0.0.18），`make -j1 CC=<clang>`
- Conan：2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`
- 状态：published

## 编译步骤

```bash
# 配方内部实际执行（等价命令）
cd <source_folder>
make -j1 CC=/data/service/hnp/bin/clang
sh check/upstream-regression.sh <source_folder>   # 上游官方测试（README.FIRST §Testing）
```

落盘产物：

- `bin/lucy`（63872 B，ELF64 aarch64，PIE + BIND_NOW + RELRO + NX）
- `share/man/man1/lucy.1`（上游自带 man page；上游无 install 目标，由配方手动落盘）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ConanException: [conf] 'tools.build:compiler_executables:c' does not exist in configuration list` | 本仓 OHOS 版 conan 未注册 `:c` 子键形式；`templates/conanfile-makefile.py.tmpl` 给出的 `self.conf.get("tools.build:compiler_executables:c", ..., check_type=str)` 在本环境不可用 | 按仓内既有惯例读整字典：`self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}`，再 `.get("c", "clang")` |
| 2 | `make: *** No targets specified and no makefile found.  Stop.` | `basic_layout` 下 build 目录（`build-release/`）≠ 源码目录，而 lucy 是 in-source 裸 Makefile 工程，不支持 out-of-tree 构建 | `build()` 内先 `cd '<source_folder>'` 再 `make`（与 `archives/a/abcm2ps/8.14.15` 先例一致）；`package()` 亦从 source_folder 取产物 |
| 3 | 黄金文件比对出现 15 条记录差异 | `abi.c:70-80` 用 libc `random()` 解析歧义碱基（N/B/R/Y…），glibc 与 OHOS musl 的 `random()` 生成器不同 → ABI 挽救判定不同 → CLZ 及派生的 CLB/CLR/CLV 变动 | 不裸用 `diff`：`check/golden-compare.py` 按上游 README.FIRST FAQ #6 陈述的机制实施判定不变式（无歧义碱基记录必须逐字节一致；含歧义碱基记录只允许 CLZ/CLB/CLR/CLV 变动，CLN 必须一致）→ 硬失败 0 |

## 源码修改

无。1.20 源码在 clang 15 下零修改编译通过，`patches: []`。

编译期告警（非错误，均为上游 2008 年前的 C89 风格代码）：
`-Wimplicit-int`、`-Wdeprecated-non-prototype`、`-Wimplicit-function-declaration`、
`-Wcomment`（qual_trim.c 文件头连续 `/*` 注释），未做任何处理。

## 依赖版本

无编译依赖、无运行依赖（仅 libc；多线程版另需 pthread，已含于 OHOS musl libc）。

W0/R36 依赖核验：`init-build` 依赖解析 ✅ 所有依赖已就绪（空依赖集）；
`conanfile.py` 的 `requires`/`tool_requires` 为空 → PF4/L0i 依赖闸无待探测包。

## 验证结果

### 上游官方测试（在 `conan create` 的 build 阶段执行）

```bash
$ lucy -v PUC19 PUC19splice atie.seq atie.qul atie.2nd -debug lucy.info   # README.FIRST §Testing
  1582 sequence cleavage information written in lucy.info
  golden records          : 1582
  identical to golden     : 1567
  ABI random() noise      : 15  (documented platform effect, README.FIRST FAQ #6)
  ambiguous-base records  : 1369 / 1582
  hard failures           : 0
RESULT=PASS
CASE T1 RESULT=PASS

$ lucy -x 4 -v ... -debug lucy_mt.info -output lucy_mt.seq lucy_mt.qul
  identical  lucy.info == lucy_mt.info
  identical  lucy.seq == lucy_mt.seq
  identical  lucy.qul == lucy_mt.qul
CASE T2 RESULT=PASS

SUITE upstream-regression: total=2 pass=2 fail=0
```

### test_package 消费者用例（鸿蒙特有测试）

```bash
$ bash consumer_case.sh      # lucy 取自已安装包 bin/lucy
read set              : 6 reads, 3954 bytes of sequence + 11760 bytes of quality
Phase 7: 5 good sequences written in trimmed.seq and trimmed.qul.
--- step 2/3: consumer post-processing (upstream zapping.awk) ------------
  ATIEA01TF    clean-range 30-491 (462 bp)  vector-trim 30-0
  ATIEA06TF    clean-range 39-493 (455 bp)  vector-trim 29-0
  ATIEA07TF    clean-range 47-455 (409 bp)  vector-trim 39-0
  ATIEA09TF    clean-range 9-434 (426 bp)   vector-trim 0-0
  ATIEA10TF    clean-range 47-314 (268 bp)  vector-trim 39-0
  clean.seq records: 5 / input reads: 6
OHOS-CASE ohos-consumer-quality-vector-trim: PASS
```

### conan create

```bash
$ conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
lucy/1.20: RUN: cd '<b>' && make -j1 CC=/data/service/hnp/bin/clang
lucy/1.20: package(): Packaged 1 file: lucy
lucy/1.20: package(): Packaged 1 '.1' file: lucy.1
lucy/1.20: Package '6b129b068851896169fae42d399fa922d239ce8a' created
======== Testing the package: Executing test ========
lucy/1.20 (test package): Running test()
→ 退出码 0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/lucy` | 63872 B | 主程序（aarch64 PIE / BIND_NOW / RELRO / NX） |
| `share/man/man1/lucy.1` | 22153 B | 上游 man page |

## 注意事项

1. **`-debug` 陷阱**：`lucy.c:313` 的默认调试输出文件名就是随包发布的黄金基准
   `lucy.debug`。测试与示例中**必须**显式写 `-debug <文件名>`，否则会覆盖基准文件，
   后续比对退化为"自比对"假通过。`check/upstream-regression.sh` 已在运行前固定校验
   `lucy.debug` 的 sha256。
2. **黄金文件判定口径**：见 `reports/test-report.md` §3.2，不得改成裸 `diff`；
   改动判定不变式需同步更新 `check/golden-compare.py` 与 MANIFEST 中的 `expected` 字段。
3. 上游 `lucy-s/` 子目录是非 pthread 版本源码（同版本附带）；本适配使用 pthread 版本，
   多线程能力由 T2 用例覆盖。
4. `test_package/consumer_case.sh` 默认把运行目录建在**配方树之外**的临时目录并在退出时
   清理（传显式路径可保留产物），避免测试产物落进配方目录被误提交。

## 对话记录

### 对话 #1 [2026-09-28]

- 问题: 上游 Makefile 只有 `all`/`lucy`/`beep`/`clean`，没有 `check`/`test` 目标，
  「上游测试」门禁没有可直接调用的入口
- 操作: 按 `README.FIRST §Testing` 的官方测试流程实现 `check/upstream-regression.sh`，
  并由 `conanfile.build()` 在 `make` 之后执行（TEST_QUALITY_SPEC 层 1）
- 结果: `conan create` 内自动执行上游套件，2 个用例全部通过（0 失败 / 0 跳过）

### 对话 #2 [2026-09-28]

- 问题: 按上游流程裸 `diff lucy.debug lucy.info` 出现 15 条记录差异
- 操作: 逐字段分析，确认 15 条差异**全部**落在 `atie.2nd` 含歧义碱基的读段集合内、
  `CLN` 全部一致，根因是 `abi.c` 的 libc `random()`（glibc vs OHOS musl）；
  按 `README.FIRST` FAQ #6 陈述的机制实现判定不变式 `check/golden-compare.py`
- 结果: 1582 条记录比对，1567 条逐字节一致 + 15 条已登记平台噪声，**硬失败 0**

### 对话 #3 [2026-09-28]

- 问题: `lucy.c:313` 的 `-debug` 默认输出名就是随包发布的黄金基准文件 `lucy.debug`，
  裸写 `-debug` 会原地覆盖基准，使后续比对退化为"自比对"假通过
- 操作: 所有调用一律显式写 `-debug lucy.info`；`check/upstream-regression.sh` 在运行前对
  `lucy.debug`/`atie.2nd`/`PUC19`/`PUC19splice` 做 sha256 固定校验
- 结果: 基准文件不会被覆盖，比对不会假通过

### 对话 #4 [2026-09-28]

- 问题: 配方首次 `conan create` 连续两处失败——`[conf] 'tools.build:compiler_executables:c'
  does not exist`；以及 `make: *** No targets specified and no makefile found`
- 操作: 改按仓内惯例读整字典 `tools.build:compiler_executables` 再取 `c`；
  因 lucy 是 in-source 裸 Makefile 工程，`build()` 内先 `cd` 到 `source_folder` 再 `make`
- 结果: `conan create` 退出码 0，两次独立构建产物 sha256 完全一致（可复现）

### 对话 #5 [2026-09-28]

- 问题: 鸿蒙消费者用例把工作目录建在配方树内（`test_package/consumer-work/`），
  运行产物会被 `git add` 收进提交，破坏 PR 原子性
- 操作: `consumer_case.sh` 改为默认在配方树之外建 scratch 目录（`TMPDIR`→`/tmp`→
  `$HOME/.cache` 依次回退）并用 `trap … EXIT` 清理；同时有意不传 2nd/ABI 序列，
  使该用例在字节层面保持确定性
- 结果: 用例仍为 6 读段 → 5 存活、4 条发生 3′ 载体修剪；`git add` 的文件集稳定为
  19 个纯配方/知识文件

### 对话 #6 [2026-09-28]

- 问题: `ohc-run.py review` 自检报 manifest 的 `test_results` 全零
- 操作: 按上游惯例补 `test_passed`/`test_failed` 顶层字段与 `test_results`、`verified` 段
- 结果: 该项转 PASS
---

**编译结束**: 2026-09-28 18:34
**最终状态**: published
