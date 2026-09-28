# libslz 1.2.1 适配笔记

## 编译环境

- 构建系统: makefile（上游裸 Makefile，无 configure）
- 编译日期: 2026-09-25
- 编译器: clang / llvm-ar（HNP 工具链）
- 状态: built
- 上游: https://github.com/wtarreau/libslz （tag `v1.2.1`，`git ls-remote --tags` 实核存在）
- 源码: `https://github.com/wtarreau/libslz/archive/v1.2.1.tar.gz`
  sha256 `c1fa88556e97541a550e59fd1f0fc8f6b4c02444b14c13eb553c9827123122c5`（与任务卡/CCI conandata 一致）

## 上游测试清点（R51，适配前完成）

| 候选口径 | 计数 | 取数命令 / 证据 |
|---|---|---|
| 框架注册数（Makefile `test`/`check` 目标、`TESTS`/`check_PROGRAMS`/`add_test`） | 0 | `grep -nE "^(test\|check)" Makefile` → 无命中；`grep -rInE "check_PROGRAMS\|^TESTS\|add_test\|ENABLE_TESTING"` → 无命中 |
| 源码宏数 / assertion 数（`src/`、`tools/` 内测试宏与断言注册） | 0 | `grep -rInE "TEST\|assert(" src tools` → 无测试注册 |
| `tests/` 目录条目 | 3（**均为数据夹具，非用例**） | `ls tests/` → `daniels.html`、`index.html`、`noncomp.bin` |
| 上游 HEAD（master）注册项数 | 0（`Makefile` 同样无 `test`/`check` 目标） | `git clone --depth 1` 后 `grep -E "^(test\|check)" Makefile` → 无；master 新增的 `tests/*.c|*.sh` 属后续版本开发，不在 v1.2.1 内且无构建注册 |

**N = 上游可运行测试入口 = 0**（候选数法取最大值 = `tests/` 3 个条目，逐项归因为数据夹具
而非用例；差额全部归因如上，四种口径未混用）。因此 PR 正文「上游测试用例通过率」写
`0/0（不适用——上游 0 个可运行测试入口）`，功能验证由**适配后补全**的
`test_package` 消费者断言（31 条）+ 上游夹具 round-trip 回归（18 例）承担。

## 编译步骤

1. 构建（`conan create` 内 `build()`，工作目录为 source_folder）：
   ```bash
   make -j1 CC=<clang> AR=<llvm-ar> CFLAGS="-O3 -fomit-frame-pointer -Wall -g" static tools
   make -j1 CC=<clang> AR=<llvm-ar> CFLAGS="-O3 -fomit-frame-pointer -Wall -g" shared   # 仅 shared=True
   ```
2. 安装：不走 `make install`，`package()` 直接复制 `slz.h`、`libslz.a`（或 `libslz.so*`）、
   `zenc`、`zdec` 到 Conan 包目录。
3. 上游测试：上游无入口（见上表）；设备侧补做上游夹具 round-trip 回归 18 例。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 不覆盖 CC 直接 `make` 失败：`/bin/sh: gcc: inaccessible or not found` → `make: gcc: No such file or directory` → `make: *** [Makefile:72: src/slz.o] Error 127`（rc=2） | 上游 Makefile `CC := $(CROSS_COMPILE)gcc`，设备与 CI worker 都没有 gcc | make 命令行显式 `CC=<clang> AR=<llvm-ar>`；配方从 `tools.build:compiler_executables` 整体取 dict 再索引（R33，不读环境变量）。`PLATFORM` 由 `$(CC) -dumpmachine` 推导为 `linux` → 产出 `libslz.so.1` + 软链 `libslz.so`，非 darwin/aix 分支 |
| 2 | `ASSERT_FAIL zlib_adler32_trailer`、`ASSERT_FAIL adler32_vector_123456789` | `slz_adler32_by1/by4` 是**裸累加器**，不做 Adler-32 初值归一化；Adler-32 规范初值是 1（zlib 内部以 1 起算），传 0 得 `091501DD` 而非 `091E01DE`；CRC32 侧初值 0 才对，两个函数约定相反 | 断言改为 `slz_adler32_by1(1, buf, len)`；不改上游源码、不打补丁。沉淀为知识草稿 `DRAFT-E735`，复现命令落 `$HOME/tmp/libslz-1.2.1/` |
| 3 | 上游无测试入口，无法给出「上游测试通过率」 | v1.2.1 无 `test`/`check` 目标、`tests/` 只有 3 个数据夹具 | 按 R51 候选数法清点（上表）声明 N=0 并逐项归因；补 `test_package` 31 条断言 + 上游夹具 round-trip 18 例做替代验证（引用既有草稿 `DRAFT-cute_files-...-upstream-zero-test` 的计数规则） |
| 4 | `make install` 会对 `zenc` 执行 `$(STRIP)` | HarmonyOS 对可执行文件有 `.codesign` 执行策略，strip 改变 section 布局后签名校验失配 → EPERM（先例 integrit/E703） | 不走 `make install`，`package()` 用 `copy()` 直接落产物；不向配方注入 `STRIP=` 掩盖问题 |
| 5 | 想用 `zdec` 做 round-trip 却拿不到还原数据 | `zdec` 是 **gzip 位流 dump/调试器**（逐位打印 BTYPE/BFINAL/码字），不是解码器，且 `btype=0`（无压缩块）直接 `exit(1)` | round-trip 改用**独立解码器** python 标准库 `zlib`（wbits 31/15/-15）逐字节比对；`zdec` 保留为「位流 dump 校验」断言（对 level-1 gzip 输出检查 `BFINAL = 1` 与 `=> EOB`） |

## 源码修改

无源码补丁（`patches: []`；上游 v1.2.1 源码在 OHOS clang 下零改动可编译）。

## 依赖版本

无第三方 Conan 依赖（零运行依赖、零编译依赖，只用 libc 头）。

## 验证结果

```text
# 1) 上游夹具 round-trip 回归（3 夹具 × 3 格式 × 2 级别 = 18 例，独立解码器 python zlib）
ROUNDTRIP_TOTAL=18 PASS=18 FAIL=0

# 2) conan create（干净源码构建 + test_package 消费者断言）
ASSERT_TOTAL ok=31 fail=0        # test.c 21 条 + roundtrip.py 10 条
```

断言构成（31 条，全部 `ASSERT_OK` 逐条打印，可被 `check_asserts.py` 复算）：

- `test.c` 21 条：三格式 `slz_init`、gzip 封套（magic / ISIZE / CRC32 trailer）、
  zlib 封套（CMF/FLG / Adler32 trailer）、raw deflate 非空、CRC32 与 Adler32 标准测试向量
  （`123456789` → `CBF43926` / `091E01DE`）、`slz_crc32_by1 == by4`、level 0 三格式可编码、
  产物落盘 4 条。
- `roundtrip.py` 10 条：libslz C API 编码 3 格式 + 已打包 `zenc` 编码 3 格式 × 2 级别
  （共 9 份输出）经 python `zlib` 解码后与原始输入逐字节相等，外加已打包 `zdec` 对
  gzip 位流的 dump 校验。

## 注意事项

- 分支 `feat/libslz-1.2.1`（去 `feat/` == 包目录名-版本，CI 分支门禁精确匹配）。
- 包内交付 `bin/zenc`、`bin/zdec` → 软件级 `archives/l/libslz/commands.json`（R38/L0k）；
  该文件与包级 `README.md`、`manifest.yaml` 是 4 段路径，会被 PF9 确定性误报
  （`notes/defects/preflight-and-audit.md`，每个全新包必命中），按既定例外走
  `--no-preflight` + 正文留痕。
- `status: built`（O5：未合并、未 release upload，不写 `published`）。

---

**编译结束**: 2026-09-25
**最终状态**: built
