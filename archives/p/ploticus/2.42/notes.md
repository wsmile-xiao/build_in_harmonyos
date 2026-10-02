# ploticus 2.42 适配笔记

## 编译环境

| 项 | 值 |
|----|----|
| 目标平台 | OpenHarmony / HarmonyOS PC aarch64（os=OHOS, os.version=6.0, arch=armv8, clang 15.0.4, libc++, cppstd 17, Release） |
| 构建系统 | 手写 GNU Makefile（`src/Makefile`），**无 configure / CMake / autotools** |
| 编译器 | clang（`tools.build:compiler_executables:c`，R33） |
| 依赖 | libpng/1.6.58.3（动态，Conan 管理依赖链）、zlib/1.3.2（静态 libz.a，R26） |
| 上游 tarball | `ploticus242_src.tar.gz`（535755 B）sha256 `3f29e4b9…e0b0` |

## 源码获取（本机 SourceForge 被 522 阻断）

```bash
$ curl -sIL https://downloads.sourceforge.net/project/ploticus/ploticus/2.42/ploticus242_src.tar.gz
HTTP/1.1 522            # master.dl/netix.dl/phoenixnap.dl 同样 522（与知识库 E421 一致）
$ curl -sSL https://cdn.netbsd.org/pub/pkgsrc/distfiles/ploticus242_src.tar.gz -o ploticus242_src.tar.gz
http=200 size=535755
$ sha512sum ploticus242_src.tar.gz
620232942096f73050633cdc37587833809b82dfb5965e4e9e977565925939c01a5e904c14faed3abe88bff2ae6e063494ed08e650708785c106673091befc6a
$ curl -sSL https://cdn.netbsd.org/pub/pkgsrc/current/pkgsrc/graphics/ploticus/distinfo
SHA512 (ploticus242_src.tar.gz) = 620232942096f73050633cdc37587833809b82dfb5965e4e9e977565925939c01a5e904c14faed3abe88bff2ae6e063494ed08e650708785c106673091befc6a
Size   (ploticus242_src.tar.gz) = 535755 bytes
```
→ SHA512 与 Size 完全一致：该文件即官方发布同字节文件；`conandata.yml` 仍写官方
SourceForge URL + 上游 sha256，CI 侧照常从官方源下载并校验通过。

## 编译步骤（真实命令）

```bash
# 源码：$BUILD_SRC_DIR = /tmp/builds/ploticus-2.42.work（含 src/ pltestsuite/ prefabs/）
$ cd $BUILD_SRC_DIR/src
$ make CC=clang \
      GD16H="-I<libpng>/include -I<zlib>/include" \
      GD16LIBS="-L<libpng>/lib -L<zlib>/lib -lpng -lz" -j1
# → src/Makefile 默认目标是 exetarget: plpng（bundled GD16，PNG + SVGZ）
# → EXIT=0，产物 src/pl（821824 字节）

# 嵌入 API 静态库（上游 target）
$ make CC=clang ARCOM="llvm-ar r" LIBEXT=a GD16H=... GD16LIBS=... libploticus-static
# → src/libploticus.a（1447522 字节）

# API 冒烟（README 指定的 api_test 路径）
$ clang -I<libpng>/include -I<zlib>/include apitest.c libploticus.a \
        -L<libpng>/lib -L<zlib>/lib -lpng -lz -lm -o apitest
$ ../src/apitest stock2.htm        # → apitest1.png + apitest2.png, EXIT=0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `pl proc drawcommands: error 522: Cannot open draw commands file (/tmp/ploXXXX)`，且进程仍返回 0（图元静默丢失） | 上游 `preliminaries.c` 把编译期宏 `TMPDIR`（`/tmp`）直接拷进 `TDH_tmpdir`，运行期完全不读环境变量；HarmonyOS PC 的 `/tmp` 是**只读挂载** | 补丁 `0001-src-preliminaries.c.patch`：运行期选择 `$TMPDIR` → 编译期默认 → 当前目录；可用性用“实际创建探测文件”判定（`access()` 在 HMDFS 不可靠）。无平台宏（R8） |
| 2 | 框架 `init-build` 的 F068“嵌套源码提升”把 `pltestsuite`（含 Makefile）误判为源码根，`.work` 树被提错 | ploticus 的构建标记在 `src/` 子目录，包根没有 Makefile | 本地探索改为手工固定源码树（`$TMPDIR/builds/ploticus-2.42.{orig,work}` 按 tarball 原样展开）；配方侧 `build()` 用 `cwd=src` 显式执行 make |
| 3 | 手写 API 探针程序 `ploticus_execline("#proc annotate")` → SIGSEGV(139) | `ploticus_init()/ploticus_execline()` **就地修改**入参字符串（按脚本语言解析），传字符串字面量会写只读段；且必须先经过一次 `execscript` 循环 | 照搬上游 `apitest.c` 的调用序列，并用可写缓冲区（`char buf[256]; strcpy(buf, ...)`） |
| 4 | `pl -version` 返回 1 | 上游行为：打印横幅后无脚本即退出 1 | L1 用例只校验横幅内容，不要求 rc=0 |
| 5 | `make` 报 `clang-15: error: no such file or directory: 'workspace/.conan...'` | conan 缓存路径含空格（`.../lan workspace/...`），Makefile 变量未加引号 | 每个 `-I`/`-L` 路径加引号；同时把 conan home 迁到无空格路径 |
| 6 | `cp -a` / `mkdir` 报 `No space left on device`（字节仍有 ~197G 空闲） | 共享文件系统 **inode 耗尽**（48,455,677 中仅剩 ~43K 空闲，`statvfs` 实测） | 改为原树内构建、避免整树拷贝；用 `statvfs` 取证定位根因（非字节空间问题） |

## 源码修改

只有一处，且已固化为 `patches/0001-src-preliminaries.c.patch`（+33/-1，仅 `src/preliminaries.c`）：

```c
- strcpy( TDH_tmpdir, TMPDIR );
+ /* 运行期选择临时目录：$TMPDIR(可用) → 编译期默认(可用) → 当前目录 */
+ { ... fopen() 探测候选目录 ... strcpy( TDH_tmpdir, chosen ); }
```

补丁不含任何平台宏（R8），是通用可移植性修复；`patches/` 之外未改动任何源码。

## 依赖版本

| 依赖 | 版本 | 链接方式 | 验证 |
|------|------|----------|------|
| libpng | 1.6.58.3 | 动态（系统无同名库） | `conan download libpng/1.6.58.3` rc=0（W0） |
| zlib | 1.3.2 | 静态（`libz.a`；系统同名库 R26） | `conan download zlib/1.3.2` rc=0（W0）；产物 `readelf` 无 libz.so NEEDED |

## 验证结果

```bash
# 上游套件（逐用例，46 例）
$ bash run_upstream_suite.sh $BUILD_SRC_DIR $TMPDIR/suite-final.tsv png
总用例=46 PASS=44 非PASS=2        # 2 例为上游自身缺陷（windbarbs.pl 缺失 / testpf_compare 空壳）

# 鸿蒙适配对照（TMPDIR=/tmp 只读）
$ TMPDIR=/tmp <未打补丁>/pl -png v4.pl    → error 522: Cannot open draw commands file (/tmp/ploqa1e12Nze_Z)
$ TMPDIR=/tmp <已打补丁>/pl -png v4.pl    → 无 error，573 字节 PNG

# L1 消费者测试（test_package/test.sh）
== 汇总: 用例 7 / 通过 7 / 失败 0 / 跳过 0 ==   # 含 3 个鸿蒙特有用例
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/pl` | 821824 B | 主程序（PS/EPS/SVG/SVGZ/PNG） |
| `lib/libploticus.a` | 1447522 B | 嵌入 API 静态库 |
| `include/libploticus.h` | — | API 头文件 |
| `share/ploticus/prefabs/` | 30 文件 | prefab 库 |

## 注意事项

- 运行期需要 libpng 动态库：用 Conan 的 `VirtualRunEnv`（`conanrun.sh`）提供
  `LD_LIBRARY_PATH` 与 `PLOTICUS_PREFABS`（配方 `runenv_info` 已设置后者）。
- 上游 `pltestsuite` 内嵌在源码包里而未安装；如需复跑上游套件，请从源码树运行。
- `/tmp` 只读是平台事实（E002）：本适配让 `pl` 在无 `TMPDIR` 时回退到当前目录，
  因此建议在脚本目录可写的环境下运行，或显式 `export TMPDIR=<可写目录>`。

## 对话记录

### 对话 #1 — 2026-10-01 · 取源与首轮真实构建
- 官方 SourceForge 源 522 阻断 → 改用 pkgsrc distfiles 并交叉核对 SHA512/Size（见「源码获取」）。
- `init-build` 的 F068 嵌套提升误把 `pltestsuite` 当源码根 → 手工固定源码树。
- 首轮构建：`make CC=clang GD16H=... GD16LIBS=...`（默认目标 `plpng`）→ `src/pl` 821824 字节。
- 首轮 `run_script_test -png` 暴露 `drawcom.htm` 失败：`error 522: Cannot open draw commands file (/tmp/ploqa1dQrRua_Z)`。
- 状态：built

### 对话 #2 — 2026-10-01 · 鸿蒙临时目录适配
- 根因定位到 `src/preliminaries.c`：`strcpy( TDH_tmpdir, TMPDIR )`（编译期宏 `/tmp`，运行期不看环境变量）。
- 修复为运行期选择 `$TMPDIR` → 编译期默认 → 当前目录，用 `fopen` 探测可用性。
- 对照实测（`TMPDIR=/tmp`）：未打补丁 → error 522；已打补丁 → 无 error、正常出图。
- 上游套件逐用例执行：46 例 → 44 通过 + 2 例上游自身缺陷（windbarbs.pl 缺失 / testpf_compare 空壳）。
- 状态：built

### 对话 #3 — 2026-10-01 · 配方与门禁
- `conan-init` 后手写 Makefile 配方（模板为 autotools，不适用）；`conan-verify` G1/G2/G3/G4 + L2/L4/L5 全绿。
- `conan create` 内建 test_package 7/7（含 3 个鸿蒙特有用例：`ohos_tmpdir_readonly` / `ohos_elf_abi` / `ohos_prefab_render`）。
- W3 本地 CI 模拟：JC 门禁需 prdiff 作用域（工作树按要求未提交 → 回退 full 模式会误报 main 中既有状态文件），见 `reports/w3-local-ci.log`。
- 状态：built
---

**编译结束**: 2026-10-01 14:40
**最终状态**: built
