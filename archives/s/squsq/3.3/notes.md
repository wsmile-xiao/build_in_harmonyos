# squsq 3.3 适配笔记

## 编译环境

- 构建系统：**无上游构建系统**（`custom`）——配方按发行版 port 的目标映射直接调用 profile 编译器
- 编译日期：2026-09-24
- 编译器：OHOS SDK `clang 15.0.4`（`Target: aarch64-unknown-linux-ohos`）
- profile：`ci/conan/profiles/ohos-aarch64`（os=OHOS / arch=armv8 / clang 15 / Release）
- Conan：2.29.1（OHOS 适配版）
- 状态：built

## 编译步骤

```bash
# 1) 取官方 distfile（NetBSD pkgsrc 分发，与 FreeBSD ports distinfo 同 sha256）
curl -sSL -o t20-squsq-3.3.tar.gz \
  https://cdn.netbsd.org/pub/pkgsrc/distfiles/t20-squsq-3.3.tar.gz
sha256sum t20-squsq-3.3.tar.gz
# aeafff976c18ffc178871be25b9bf403cb25414773ed4e8157813f98b8f3fb37

# 2) 本源码包不含任何构建文件，按发行版 port（FreeBSD archivers/squsq 的
#    files/Makefile）的目标映射直接编译：
CC=/data/service/hnp/bin/clang
$CC -O2 -Wall -Wno-error=return-type -Wno-error=int-conversion -o sq  sq.c tr1.c tr2.c sqio.c
$CC -O2 -Wall -Wno-error=return-type -Wno-error=int-conversion -o usq usq.c utr.c

# 3) Conan 流程
python3 scripts/ohc-run.py init-build squsq 3.3 --url=https://cdn.netbsd.org/pub/pkgsrc/distfiles/t20-squsq-3.3.tar.gz
python3 scripts/ohc-run.py lang-preflight squsq 3.3 --src $BUILD_SRC_DIR
python3 scripts/ohc-run.py conan-init squsq 3.3
python3 scripts/ohc-run.py conan-verify squsq 3.3      # G1–G4 + L2/L4/L5 全通过
python3 scripts/ohc-run.py finish squsq 3.3 built
```

上游 tarball 结构（15 个条目）：`sq.c sqio.c tr1.c tr2.c sq.h sqcom.h` → `sq`；
`usq.c utr.c usq.h` → `usq`；`sqdbug.c` 无任何目标编译（1986 年的调试残留）；
`makesq.mic` / `makeusq.mic` 是 TOPS-20 MIC 脚本（`@cc -DTOPS20 …` / `@load …,c:libt20/se`），
Unix/OHOS 无法使用；`lusq.exe` 是 1988 年的 TOPS-20 可执行文件（未打包）。

## 遇到的问题与解决方案

| # | 问题（首个真实错误） | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `sq.c:138:7: error: non-void function 'obey' should return a value [-Wreturn-type]`（4 errors generated） | K&R 时代源码里函数隐式返回 `int`，却写裸 `return;`；ISO C99+ 起这是约束违反，clang 默认按 **error** 处理（`-Wreturn-type` 的 error 升级） | 加 `-Wno-error=return-type`——与 FreeBSD port `CFLAGS+= -Wno-error=return-type` 完全一致，源码零改动 |
| 2 | `tr2.c:350:10: error: incompatible pointer to integer conversion returning 'void *' from a function with result type 'int' [-Wint-conversion]` | `buildenc()` 用 `return ((level > 16) ? ERROR : NULL);`，在 `int` 函数里返回 `void*` | 加 `-Wno-error=int-conversion`——FreeBSD port 在 FreeBSD 上正是加这一条 |
| 3 | `conan-verify` G2 失败：`Error in package() method, line 117 / AttributeError: 'int' object has no attribute 'stdout'` | Conan 2 的 `self.run()` 返回**退出码 int**（不像 Conan 1 返回对象），签名探测代码却取 `.stdout` | `_has_codesign_section()` 改用 `subprocess.run([...], capture_output=True, text=True)` 解析节区表；重新 `conan-verify` → G1–G4 + L2/L4/L5 全通过 |
| 4 | 编译告警 `usq.c:218:12: warning: extra tokens at end of #ifdef directive [-Wextra-tokens]`（`#ifdef C70 \| TOPS20`） | 上游 1988 年的写法不合法但语义确定（两个宏都未定义 → 走 `#else` 的 `getw16`） | **不修**：FreeBSD port 有一条同名补丁，但它在 Unix 下不改变任何行为，只消除一条 warning；依「最小改动」原则保留源码原样，仅在此记录（`-Wno-error` 未覆盖它，也不影响构建） |
| 5 | **远端 CI 红**（PR #12396，构建 #59456 / #59543）：`TOTAL 27 PASSED 25 FAILED 2`，两例 `TimeoutExpired: Command '[.../bin/sq']` / `[.../bin/usq']' timed out after 120 seconds`（本地与 W3 全绿，仅远端复现） | `sq`/`usq` **无参数**调用会进入上游的交互式提示循环（`sq.c main()`: `printf("Enter file names, one line at a time, or type <RETURN> to quit.")` 后 `getchar()` 循环）。用例运行器用 `capture_output=True` 但**未指定 stdin**，子进程继承父进程 stdin：本机 stdin 立即 EOF → 正常退出；CI worker（buildbot 管道）的 stdin **永不 EOF** → `getchar()` 永久阻塞 → 用例 120s 超时（CI 侧误判为"构建超时/交互式测试卡住"，但实际 elapsedTime 仅 257s，不是预算问题） | **修 in test_package（不改被测程序）**：`Context.run()` 统一 `stdin=subprocess.DEVNULL`，等价于用户直接按 `<RETURN>`/EOF——上游文档规定的非交互退出路径；并把"无参数时打印交互提示 + 遇 EOF 干净退出（rc=0）"写入该 2 例断言。**复现与验证**：以永不 EOF 的匿名管道作 stdin，修复前 `sq`/`usq` 5s 仍在运行（复现），修复后整集 `TOTAL 27 PASSED 27 FAILED 0 SKIPPED 0`、耗时 0.9s；`conan create` 内 test_package 亦 27/27 |

## 源码修改

**无。** `patches/` 目录不存在，`conandata.yml` 中 `patches: {}`，tar 包 sha256 与发行版 distinfo 一致，
配方只使用编译器开关（发行版 port 既有做法），未触碰 1986–1988 年的源码。

## 依赖版本

**无第三方依赖**（DIRECT_DEPS = 0，TRANSITIVE = 0）。
源码只用到 libc（`printf/fopen/fwrite/fgetc/fclose/strcpy/strlen/sprintf/getc/fputc/atoi/exit` 等），
唯一命中的 `system()` 位于 `usq.c:343`，被 `#ifdef TOPS20` 包裹、Unix 构建不编译。
构建工具链 `clang`/`make` 由 OS/工具链自带。

## OHOS 平台适配要点

1. **编译器来自 Conan profile（R33）**：`tools.build:compiler_executables.c`，不读 shell 的 `${CC}`。
2. **OHOS ELF 签名（E077）**：OHOS SDK 的 clang 驱动默认启用 `ld.lld --code-sign`，
   新链接出的 ELF 天然带 `.codesign` 与 `.note.ohos.ident`；本包不做任何 link 后 ELF 改写，
   因此签名保持有效。配方只在**签名缺失**时才调用 `binary-sign-tool` 补签（当前环境中未触发）。
3. **无平台宏补丁**：`patches/` 为空，不存在 `__OHOS__` 守卫，也没有空壳 stub。
4. 交叉编译产物实测可在 HarmonyOS PC（aarch64）与 conan 包缓存路径下直接执行。

## 验证结果

```bash
$ python3 scripts/ohc-run.py conan-verify squsq 3.3
✅ G1 PASS / G2 PASS / G3 PASS / G4 PASS / L2 / L4 / L5
✅ 配方验证通过: squsq 3.3

$ conan create archives/s/squsq/3.3 -pr:h=… -pr:b=… --build=missing --user=ohpcd --channel=stable
TOTAL 27  PASSED 27  FAILED 0  SKIPPED 0

$ python3 archives/s/squsq/3.3/test_package/test_squsq.py <conan 包>/bin
TOTAL 27  PASSED 27  FAILED 0  SKIPPED 0

$ llvm-readelf -h <pkg>/bin/sq | grep Machine        → Machine: AArch64
$ llvm-readelf -S <pkg>/bin/sq | grep codesign       → [37] .codesign  PROGBITS
```

### 上游测试账目（R51 申报表）

| 项 | 值 |
| --- | --- |
| 上游测试目录数 | 0（tarball 无 `test/`、`tests/`） |
| 上游注册测试数（ctest/pytest/make check） | 0（无构建系统、无 `check`/`test` 目标；发行版 port 亦无 `TEST_TARGET`/`do-test`） |
| 上游测试入口命令 | 无（`make -n check` → `No rule to make target 'check'`，exit=2） |
| 本包实际执行用例 | 27（上游行为派生 24 + 鸿蒙特有 3），通过 27 / 失败 0 / 跳过 0 |
| 上游测试修改说明 | 不适用（上游用例集为空，未修改、未跳过任何上游测试） |
| 证据 | `reports/upstream-test-entry.md`、`reports/upstream-test-cases.md`、`reports/test-report.md`（原始 `.log` 属规则 19 禁止文件，不随 PR 提交） |

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/sq` | 27008 | CP/M Squeeze 压缩工具（`File squeezer version 3.3`） |
| `bin/usq` | 22912 | CP/M Squeeze 解压工具（支持 `-<n>`/`-F` 预览） |
| `share/doc/squsq/readme` | 2598 | 上游 readme（作者变更清单） |

## 注意事项

- `sq` 的输出名遵循 CP/M 3.0 约定（替换原扩展名、`FNM_LEN 14` 截断），
  **不是**「直接追加 `.SQ`」——`sqcom.h` 的 `UNIX` 宏是注释掉的，走的是 `#ifndef UNIX` 分支，
  与 FreeBSD/NetBSD 发行版构建行为一致。若将来有人加 `-DUNIX`，输出命名会变成追加式，测试会立刻变红。
- `usq` 解压会用文件头里记录的**原始文件名**落盘，可能覆盖同名文件；改名后的 `.SQ` 仍还原为原名。
- `bin/sq` 与部分发行版（`squirrel`、`sequoia`）的 `bin/sq` 同名，同一 PATH 下会冲突（发行版用
  `CONFLICTS` 声明），Conan 侧由各包自己的 `bin/` 目录隔离。
---

**编译结束**: 2026-09-24 17:10
**最终状态**: built
