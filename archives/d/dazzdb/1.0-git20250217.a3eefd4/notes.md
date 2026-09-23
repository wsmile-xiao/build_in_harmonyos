# dazzdb 1.0-git20250217.a3eefd4 适配笔记

## 编译环境

- 构建系统: makefile（上游手写 Makefile，无 configure）
- 编译日期: 2026-09-11
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，aarch64-linux-ohos）
- 状态: built
- 源码: `thegenemyers/DAZZ_DB` commit `a3eefd4e3b31b6701f57268f8353e136a6f80525`（2025-02-17 快照），
  sha256 `82b26d29e42eaeb833ff2c8bb34ba5ce864fae64fb9ea3501c26e39f412b0351`，
  解包树与 Debian 源码包 `dazzdb 1.0+git20250217.a3eefd4-1` 的 orig.tar.xz 逐文件一致

## 编译步骤

上游 Makefile 的 21 条规则各自 `gcc $(CFLAGS) ... -o <tool> ...`。配方不直接调用
make 的默认规则，而是在 `generate()` 里生成本包的 conanbuild 环境（CC 取
`tools.build:compiler_executables` 的 `c`，CFLAGS 复述上游默认值，
CPPFLAGS/LDFLAGS 追加 zlib 依赖的 include/lib 目录），`build()` 再执行：

```bash
make -j1        # 工作目录 = source_folder，env = conanbuild
```

产物为 21 个可执行文件，`package()` 逐一点名 install 到 `bin/`，缺任何一个即失败。

## 遇到的问题与解决方案

| # | 问题（第一条真实错误） | 根因 | 解决方案 |
|---|------------------------|------|----------|
| 1 | `make: gcc: No such file or directory`（Makefile:11，exit 127） | Makefile 的 21 条规则全部硬编码 `gcc`，且其中 20 条还写死了 `-lm` 或 `-lz`（实测 21 条中带 `-lm` 的 18 条、带 `-lz` 的 2 条，两者交集为空，`rangen` 两者都没有），既不读 CC 也不读 LDFLAGS/LDLIBS；设备与 CI worker 只有 clang | 0001：每条规则改为 `$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ <该目标原有的源文件列表> $(LDFLAGS) $(LDLIBS)`——源文件列表逐条保留而不是用 `$^`（`$^` 会把依赖里的 `.h` 也带进编译命令），并新增 `CC ?= gcc`、`CFLAGS ?=`、`LDLIBS = -lm -lz` |
| 2 | `ld.lld: error: undefined symbol: rindex`（DB.c:117，另有两处 `did you mean: index`） | OHOS libc 导出 `index`（`nm -D` 计数 1）但不导出 BSD 遗留别名 `rindex`（计数 0） | 0002：DB.c/DB2ONE.c/DBshow.c 共 9 处 `rindex(` 统一改写为 POSIX `strrchr(` |
| 3 | `DB2ONE -h <db>` 运行即 abort（exit 134），stderr 无任何信息 | ONElib.c 把模式临时文件硬编码为 `/tmp/OneSchema.%d` 与 `/tmp/OneTextSchema-%d.def`，而设备 `/tmp` 是只读挂载（实测 `fopen` 返回 NULL、`errno=30 EROFS`） | 0003：新增 `oneTempDir()` 运行时探测（依次 `access(W_OK)` 试 `$TMPDIR`、`/tmp`、`$HOME`、`.`），并把两处 `static char template[64]` 改为 1024 字节 + 有界 `snprintf` + 越界即 `die` |
| 4 | 无参数执行 `DB2ONE` 段错误（exit 139） | `if (argc >= 1)` 分支在 argc==1 时对 NULL 的 `argv[1]` 做 `sprintf`，而缓冲区按 `argc-1` 个参数长度分配（n=0 → `Malloc(1)`） | 0004：守卫条件改为 `argc > 1`（无参数时正常打印用法并 exit 1） |
| 5 | `DB2arrow <A-DB>`：`Arrow data is not available (Load_Arrow)`（exit 1） | DB2arrow 只检查 `allarr & DB_ARROW`，从不调用 `Open_Arrow(db)` 挂载轨对象，`db->tracks` 恒为 NULL | 0005：检查通过后调用 `Open_Arrow(db)`，与 DBshow 的同名路径一致；修复后 arrow 往返逐字节一致 |
| 6 | `DBstats -mdust <db>` 段错误（exit 139） | 掩码轨统计循环 `for (track = db->tracks; track; track = track->next)` 内调用 `Close_Track(db,track)` 释放当前节点，随后解引用 `track->next`（与 Debian `debian/patches/use-after-free.patch`、上游 issue 41 同源） | 0006：移除该调用 |

0006 的实测形态需要说明清楚：这是 use-after-free，**行为随堆布局而变、不是每次必崩**。同一份未修
二进制在验收库（仅含 1 个区间、由 2 块 `Catrack` 合并而成）上连续 5 次全部 SIGSEGV，而在任务期
另建的一个库上连续 5 次都正常退出；修复版在两个库上都是 exit 0。判据因此不是"未修版本必然崩溃"，
而是"释放后继续解引用"这一代码事实加上可复现的崩溃样本。

0003 的兜底行为（已知边界，经实测确认，不构成本包缺陷）：`oneTempDir()` 按 `$TMPDIR` → `/tmp` →
`$HOME` → `.` 依次用 `access(W_OK)` 探测，**四个候选全部不可写时返回空串**。此时的行为与"给出清晰
报错"不同，实测如下（构造方式：cwd 与 `HOME` 都置于只读挂载 `/tmp`、`TMPDIR` 指向不存在的路径，
从而让四个候选全部落空）：

- 路径退化为 **`/OneTextSchema-<pid>.def`**（不是 `/OneSchema.<pid>`）：先被调用的是
  `oneSchemaCreateFromText()`，`oneSchemaCreateFromFile()` 里那个 `OneSchema.<pid>` 模板还没轮到；
- `fopen` 返回 NULL、`errno = 13 (EACCES)`（写根目录，不是 EROFS）；
- 紧随其后的 `fprintf(NULL, ...)` 直接 SIGABRT，进程以 **exit 134 静默结束、stderr 无任何输出**——
  `oneSchemaCreateFromText()` 末尾那道 `if (errno) die(...)` 位于 `fclose` **之后**，根本不可达。

实测命令与输出：

```console
$ cd /tmp && HOME=/tmp TMPDIR=<不存在的路径> DB2ONE -h <abs>/G
exit=134   stderr 0 字节
```

该退化分支在正常 OHOS 场景下不可达（`/tmp` 只读，但 `$HOME` 与工作目录可写），因此不影响本包功能；
记录在此是为了避免把"静默 abort"误当成"带 errno 的清晰报错"。另外 `snprintf` 的负返回值（编码错误；
在 `%s`/`%d` 下实际不可达）未单独判定。四种边界（TMPDIR 缺失 / 不存在 / 存在但不可写 / 超长路径）
均实测 exit 0 且导出载荷完整，见测试第 11 节。

测试第 11 节的两条「不可写目录」用例需要说明口径：本工作区是 hmdfs，**不执行 POSIX 权限位**
（`chmod 500` 落盘仍是 2771、`touch` 仍成功、`access(W_OK)` 仍为真），所以"用 chmod 造一个不可写目录"
在本设备上会空转。脚本改为现场遍历 `/tmp`、`/var/tmp`、`/usr/tmp`，用 `[ -d ] && [ ! -w ]` 找一个
**宿主上真实不可写的挂载点**（本设备命中 `/tmp`，erofs 只读）。该断言验证的是"TMPDIR 为存在但不可写的
目录时导出仍能完成"——能观察到的是退出码与载荷完整性；"确实没有写进 TMPDIR"由该目录是只读挂载这一
前提保证（任何实现都无法在其中落盘后仍成功），因此措辞不写"skips"（那属推断而非断言事实）。

宿主若不存在这样的挂载点（例如常规 Linux 上 `/tmp` 可写），这两条记 **SKIP** 并单列计数：既不冒充
PASS，也不把宿主差异误报成产品缺陷。届时输出为 `PASS=91 FAIL=0 TOTAL=91 SKIP=2` 且 `RESULT: OK`；
本设备实测为 `PASS=93 FAIL=0 TOTAL=93 SKIP=0`。分母口径固定为 `TOTAL = PASS + FAIL`。

补充：`/tmp` 只读的常规解法（知识 E002：设置 TMPDIR）在本包不成立——路径是源码里的字面量，
运行中的进程不会把 TMPDIR 代进去。反证实测：TMPDIR 指向可写目录时，未打 0003 的
`DB2ONE -h <db>` 仍以 exit 134 结束，且该目录内零文件。

## 源码修改

`patches/` 六个补丁，按序应用（全部为 delete/add 以外的普通上下文补丁，`patch_strip` 用默认值 1）：

1. `0001-Makefile-honour-toolchain-variables.patch` — Makefile 尊重工具链变量
2. `0002-replace-BSD-rindex-with-POSIX-strrchr.patch` — 3 文件 9 处 `rindex` → `strrchr`
3. `0003-onelib-probe-writable-scratch-directory.patch` — ONElib 临时目录运行时探测 + 有界路径
4. `0004-db2one-guard-command-buffer-without-arguments.patch` — DB2ONE 命令行副本越界写
5. `0005-db2arrow-open-arrow-track-before-reading.patch` — DB2arrow 打开 arrow 轨
6. `0006-dbstats-drop-use-after-free-in-track-loop.patch` — DBstats 掩码轨 use-after-free

上游测试文件未作任何修改（上游本就没有测试套件）。

关于 CFLAGS 的取舍：`generate()` 用 `env.define("CFLAGS", <上游默认值>)` **完全设定** CFLAGS，
而不是追加 `tools.build:cflags`。理由是：① 上游 Makefile 写的是 `CFLAGS ?=`（"未定义时才用默认值"），
不设定就会依赖调用环境的 shell 变量，而 workflow 明令禁止；② 21 条规则共用同一组 flags，注入点唯一
且可复核。代价是 CI 若通过 profile 配置 `tools.build:cflags` 不会生效——需要改优化级别时改配方常量即可。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| zlib | 1.3.1 | 仅链接期：满足上游 Makefile 为 `arrow2DB`/`DB2arrow` 写的 `-lz` |

关于 zlib 的实测结论（2026-09-11）：

- 上游 Makefile 给 `arrow2DB`/`DB2arrow` 链 `-lz`，但**本版本源码并不使用 zlib**：
  全树没有 `#include <zlib.h>`，也没有 `compress/uncompress/deflate/inflate/crc32` 调用；
  打包产物 `readelf -sW` 的未定义符号只有 libc 一族，`readelf -d` 的 `NEEDED` 只有 `libc.so`。
- 因此 zlib 是**链接期依赖**：它让 `-lz` 解析到包管理器提供的静态 `libz.a`，
  而不是 OHOS sysroot 里的桩 `libz.so`。对照实测：探索期直接对 sysroot 链接的
  `DB2arrow` 带上了一条 `NEEDED libz.so`（设备只有 `/usr/lib/libz.so.1`，没有 `libz.so`），
  配方构建的产物则只有 `NEEDED libc.so`。
- 其余 19 个工具只需 libc 与 libm（`-lm` 同样由 `LDLIBS` 提供）。

## 验证结果

```bash
# 配方与门禁（命令唯一权威副本见 manifest.yaml 的 validation 段）
python3 scripts/ohc-run.py conan-verify dazzdb 1.0-git20250217.a3eefd4 --project-dir <repo>

# 适配侧用例（test_package 以 env=conanrun 调用同一脚本）
sh test_package/test.sh <package_folder>/bin <work-dir>
# -> adaptation cases: PASS=93 FAIL=0 TOTAL=93 / RESULT: OK
```

上游测试为 0 用例（非跳过、非部分执行），零入口证据与取数命令见
`test_package/MANIFEST.yml` 的 `upstream_tests` 段与版本级 `manifest.yaml` 的
`test_results.upstream.evidence`。适配侧 93 项断言覆盖全部 21 个产物，
统计单位为断言（`test.sh` 的 ok/no 计数），取数命令写在
`test_package/MANIFEST.yml`。

## 注意事项

- 上游把 `simulator` 这类通用名直接安装为可执行文件。本包安装到 Conan 包内独立的
  `bin/`，不落系统目录；Debian 为避免 `/usr/bin` 冲突把它重命名为 `dsimulator`，
  本包保留上游原名。
- `DBsplit` / `DBtrim` 会交互式询问 `[Y/N]`，脚本化使用时需要 `printf 'Y\n' | ...`。
- `rangen` 的长度参数单位是 **Mbp**（源码 `GENOME = glen*1000000`），
  `rangen 20000` 会试图生成 200 亿碱基。
- `DB2fasta`/`DAM2fasta`/`DB2arrow`/`DB2quiva` 的输出文件名由 DB 记录的源文件名派生的
  root 决定（不是命令行给的 DB 名），会**覆盖同名输入文件**；测试脚本因此先留存期望副本。
- `arrow` 文件的脉冲宽度字母表是 `'1'`–`'4'`（`Number_Arrow`/`Letter_Arrow` 互逆），
  写 `'0'` 会被静默映射成 `'4'`。
- `.daz`（ONE）导出是二进制格式：ASCII 部分只有版本行、provenance 行与嵌入 schema，
  其余为压缩载荷，校验只能依赖头部/schema/载荷增量而不是行首字母。
