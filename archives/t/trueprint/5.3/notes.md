# trueprint 5.3 适配笔记

## 编译环境
- 构建系统: autotools（2001 年 autoconf/automake，仅支持 `--prefix`）
- 编译日期: 2026-09-13
- 编译器: clang 15.0.4（OHOS aarch64 工具链）
- 状态: built
- 任务号: 13410（开源鸿蒙PC专项积分赛-依赖）
- 分支: feat/trueprint-5.3

## W0 依赖发布检查
- configure.in 检查项：diff/lpr/lp（运行时外部命令，非链接库）、系统头文件
  （fcntl.h/sys/time.h/unistd.h/libintl.h）、libc 函数
  （vprintf/strerror/strdup/strtol/gettext，缺失者由 replace/ 目录自带替代实现）。
- **无任何外部链接库依赖** → 依赖清单为空，R36 拓扑约束不适用。

## W0b 历史经验核验
- 归档树 archives/t/ 无 trueprint（本任务为首适配），无历史 notes.md。
- 老项目处理模式参照同仓库 termcap 1.3.1 先例（`sh configure --prefix=` 直调、
  E490 exec-bit 规避、package() 直拷产物）。

## 编译步骤

```bash
# 探索编译（设备原生 OHOS aarch64）
mkdir -p stubbin && printf '#!/bin/sh\ncat >/dev/null\nexit 0\n' > stubbin/lpr
cp stubbin/lpr stubbin/lp && chmod +x stubbin/lpr stubbin/lp
PATH="$PWD/stubbin:$PATH" CC=clang sh configure --prefix=<prefix>
touch doc/trueprint.info
make MAKEINFO=true LDADD="../replace/libreplace.a" -j1
make install MAKEINFO=true LDADD="../replace/libreplace.a" DESTDIR=<staging>

# 上游测试（49 用例）
PATH="/data/service/hnp/bin:$PATH" make check MAKEINFO=true \
    LDADD="../replace/libreplace.a" TMPDIR=$HOME/tmp/trueprint-tmp
# → 49/49 passed, 0 failed（补丁后）

# 冒烟
./src/trueprint --version   # → GNU Trueprint 5.3
```

配方构建（conan create 路径）：`build()` 先建私有 stubbin（lpr/lp）前置 PATH，
`sh configure --prefix=<package_folder>`，`autotools.make(-j1, MAKEINFO=true,
LDADD=../replace/libreplace.a)`；`package()` 直拷 src/trueprint 到 bin/。

## 上游测试（R51 四维账本）

| 维度 | 数值 | 说明 |
|---|---|---|
| N_static（上游静态声明） | 49 | tests/Run 按 `test=N` 块静态清点（grep -c "^test=" Run = 49，test=1..49） |
| N_registered | 1 | make check 注册 TESTS=Run（1 个 runner 脚本，承载 49 个原子用例） |
| N_executed | 49 | 设备实测 make check，runner 报告 "49 out of 49 tests passed"（补丁后） |
| 通过/失败/跳过 | 49/0/0 | 补丁前 47 通过 + 2 失败（用例 47/48 stdin 段错误，见问题 #4） |
| N_consumer（新增消费者测试） | 1（断言 3 项） | test_package/test_trueprint.sh：版本标识、C 文件→PostScript、stdin→PostScript |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `Cannot find either an lpr command or an lp command`（AC_MSG_ERROR 硬失败） | 2001 configure 把打印机命令当构建前提；构建/CI 环境无打印系统 | build() 生成私有 stub lpr/lp 前置 PATH（PF6 合规：非系统前缀，stub 不入包）；运行时打印由 -P/TP_PRINT_CMD 决定，PRINT_CMD 常量仅为默认值 |
| 2 | diffs.c/getopt.c/output.c 等大量 `implicit declaration of gettext` → 链接 `undefined symbol: gettext` | OHOS sysroot 的 libintl.h 是空壳（只有宏，不声明 gettext），但 configure 检测到头文件存在 → HAVE_LIBINTL_H=1，replace.h/getopt.c 走"信任系统头"分支；同时 HAVE_GETTEXT 未定义 → replace/gettext.c 有实现但没被链入 | 补丁 0001/0002：replace.h 与 getopt.c 的分支条件改为 `HAVE_LIBINTL_H && HAVE_GETTEXT` 同时成立才信任系统头；make 时 `LDADD=../replace/libreplace.a` 把自带实现链入 |
| 3 | make 报 makeinfo 缺失（doc/trueprint.texi） | 构建机无 texinfo | `touch doc/trueprint.info` + `make MAKEINFO=true`（autotools 惯例跳过） |
| 4 | 上游用例 47/48（stdin 输入）SIGSEGV，"47 out of 49 tests passed" | main.c:465 `stdin_stream = fileno(tmpfile())`——musl tmpfile() 固定用 /tmp，OHOS 设备 /tmp 只读（E002）→ tmpfile() 返回 NULL → fileno(NULL) 解引用崩溃 | 补丁 0003：tmpfile() 前先尝试 `mkstemp("$TMPDIR/trueprintXXXXXX")`，成功则用之；平台无关健壮性修复。补丁后用例 47/48 通过 → 49/49 |

## 源码修改（patches/）

| 补丁 | 文件 | 内容 | 原因 |
|---|---|---|---|
| 0001 | replace/replace.h | gettext 声明分支条件 `HAVE_LIBINTL_H` → `HAVE_LIBINTL_H && HAVE_GETTEXT` | OHOS libintl.h 空壳头不声明 gettext，需回落到本地声明 |
| 0002 | src/getopt.c | 同上（getopt.c 自带的 libintl 分支） | 同上 |
| 0003 | src/main.c | stdin 暂存文件优先 `mkstemp($TMPDIR/...)`，失败回落 tmpfile() | OHOS 设备 /tmp 只读（E002）导致 tmpfile() NULL → SIGSEGV，修复上游用例 47/48 |

## 验证结果

```bash
# 探索编译（设备 OHOS aarch64 原生）
PATH="stub:$PATH" CC=clang sh configure --prefix=$TEST_PREFIX   # rc=0
make MAKEINFO=true LDADD=../replace/libreplace.a -j1             # rc=0
./src/trueprint --version                                        # → GNU Trueprint 5.3, rc=0

# 上游测试（补丁后）
PATH="/data/service/hnp/bin:$PATH" TMPDIR=$HOME/tmp/trueprint-tmp \
  make check MAKEINFO=true LDADD=../replace/libreplace.a         # rc=0
# Run: 49 out of 49 tests passed
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/trueprint | 源码→PostScript 美化打印工具（含 diffs/索引/多语言支持，49 项上游用例全过） |

## 已知限制

- 构建期 configure 将 stub lpr 路径写入 config.h 的 PRINT_CMD 常量（仅影响
  不带 -P 时的默认打印目标）；包内 trueprint 的实际打印通道应经 `-P <命令>`
  或环境 `TP_PRINT_CMD` 指定，与上游运行时行为一致。
- doc/trueprint.info 未随包发布（构建机无 makeinfo；info/man 为文档产物，
  不影响工具功能）。

## 注意事项

- 消费者测试用 `TP_PRINT_CMD=cat` + `TP_OPTS=--N`（与上游 tests/Run 相同机制）
  将 PostScript 输出重定向到 stdout 做断言，无需真实打印机。
- OHOS 无系统 gettext/libintl 是通用平台事实（非本包特有），相关判定经验已
  写入 manifest.yaml knowledge_gained。
---

**编译结束**: 2026-09-14 02:11
**最终状态**: built
