# conan-verify 门禁人工补测 — cdtool 2.1.8-release

> **为什么有本文件**：`conan-verify` 对 `package_type = "application"` 的纯可执行包
> 会整组跳过 G4/L2/L4/L5——报告里 `✅ PASS` 与 `⏭️ 跳过` 并存，裸 `✅` 是工具文案
> 缺陷，**以跳过行为准**。本轮实测原文（`reports/conan-verify-report.md`）：
>
> ```
> ## G4: ✅ PASS
>   ⚠️ 无法找到程序包 ID
> ## L2: ✅ PASS
>   ⏭️ 跳过（无 cache 路径）
> ## L4: ✅ PASS
>   ⏭️ 跳过（无 cache 路径）
> ## L5: ✅ PASS
>   ⏭️ 跳过（无 cache 路径）
> ```
>
> 因此按应用包口径**人工补测**，判据与原始输出如下。被验证的包目录按 ref 精确解析：
> `conan cache path "cdtool/2.1.8-release@ohpcd/stable:6b129b068851896169fae42d399fa922d239ce8a"`。

- 参考 ref：`cdtool/2.1.8-release@ohpcd/stable`
- recipe revision：`3ff64316d19bee10c1edeec46af2997d`
- package_id：`6b129b068851896169fae42d399fa922d239ce8a`
- settings：`os=OHOS os.version=6.0 arch=armv8 compiler=clang 15 libcxx=libc++ cppstd=17 build_type=Release`
- 补测日期：2026-09-13

---

## G4：产物完整性（`find` 清单 ↔ `package_info()` 的 `bindirs`）

`package_info()` 声明 `bindirs = ["bin"]`、`libdirs = []`。实测包目录清单：

```
# 常规文件（14）
bin/cdadd              bin/cdctrl             bin/cdloop
bin/cdown              bin/cdtool2cddb        conaninfo.txt
conanmanifest.txt      lib/cdtool/cdtool
share/man/man1/cdadd.1     share/man/man1/cdctrl.1   share/man/man1/cdloop.1
share/man/man1/cdown.1     share/man/man1/cdtool.1   share/man/man1/cdtool2cddb.1

# 符号链接（20）
bin/{cdclose,cdeject,cdinfo,cdir,cdpause,cdplay,cdreset,cdshuffle,cdstop,cdvolume}
      → ../lib/cdtool/cdtool                      （10 条，均指向同一主程序）
share/man/man1/{同名 10 个}.1 → cdtool.1           （10 条）
```

| 判据 | 实测 | 结论 |
|---|---|---|
| `bin/` 顶层条目数 | 15（5 个独立产物 + 10 个别名符号链接） | 与上游 `Makefile.in` 的 `install-files`(5) + `install-links`(10) 一致 |
| 包内常规文件 / 符号链接 | 14 / 20 | 与 `package_info()` 的 `bindirs=["bin"]` 一致；无 `include/`、无 `.so`，`libdirs=[]` 正确 |
| `bin/` 下是否有 `cdtool` | **没有**（上游设计：主程序只在 `lib/cdtool/cdtool`） | `package_info()` 未声明 `bin/cdtool`，声明与产物一致 |
| 悬空符号链接 | 0（20 条全部可解析） | 无 |

> 与同类尝试的差异（如实记录）：另有他人针对同一平台的实现声称"安装后存在悬空符号链接、
> `cdctrl`/`cdown`/`cdtool2cddb`/`cdloop` 未落盘、需要在打包阶段重建链接与回填二进制"。
> **本包实测不存在该现象**（同一上游 tarball、同 `make install` 路径），故本配方不含任何
> 安装后修复逻辑。差异原因未进一步追查，仅记录事实。

## L2：平台功能矩阵（可执行包人工补测——真实运行）

逐条对**包内已安装产物**真实执行，`stdin=/dev/null` 且每条 15s 超时：

| 命令 | rc | 首行输出 |
|---|---|---|
| `lib/cdtool/cdtool -V` | 0 | `cdtool CDTOOL 2.1.8pre3 (c) 1994-2004 Thomas Insel, et al.  Licensed under GPL.` |
| `bin/cdplay -V` | 0 | `cdplay CDTOOL 2.1.8pre3 (c) 1994-2004 Thomas Insel, et al.  Licensed under GPL.` |
| `bin/cdinfo -V` | 0 | `cdinfo CDTOOL 2.1.8pre3 (c) 1994-2004 Thomas Insel, et al.  Licensed under GPL.` |
| `bin/cdctrl -h` | 0 | `cdctrl:` / `Command line CDROM control` / `Options:` |
| `bin/cdown -V` | 0 | `cdown 0.6` |
| `bin/cdtool2cddb -h` | 0 | `Usage: cdtool2cddb [-rvx] [-d dir] [-l len] [input]` |
| `bin/cdadd -h` | 0 | `Usage: cdadd [-[0-7]]` / `This program is part of cdtool.` |

同时验证了「单程序多名字」在 OHOS 上的真实可用性：`bin/cdplay`、`bin/cdinfo` 是符号链接，
经 `argv[0]` 分派后各自打印**自己的程序名**（`cdplay`/`cdinfo`），说明符号链接 + argv[0]
分派机制在 OHOS 文件系统上工作正常。

**未覆盖范围（如实声明，不写成 PASS）**：cdtool 的核心功能是 CD-ROM 音频控制
（`CDROMPLAYMSF`/`CDROMSTOP`/`CDROMEJECT` 等 ioctl 与 `/dev/cdrom` 访问），
**运行需要真实光驱，OHOS PC 设备无光驱**，因此播放/停止/弹出/音量等核心路径
**无真机验证**；`-V`/`-h` 只覆盖参数解析后的早退分支。

## L4：静态安全扫描（逐可执行产物 `readelf`）

判据：`DYN`（PIE） + `GNU_STACK RW`（NX） + `GNU_RELRO` + `FLAGS BIND_NOW` + `FLAGS_1 … PIE`。

| 产物 | Class / Type | GNU_STACK | GNU_RELRO | FLAGS | FLAGS_1 | NEEDED |
|---|---|---|---|---|---|---|
| `lib/cdtool/cdtool` | ELF64 / DYN (PIE) | RW（NX） | ✅ | `BIND_NOW` | `NOW PIE` | `libc.so` |
| `bin/cdctrl` | ELF64 / DYN (PIE) | RW（NX） | ✅ | `BIND_NOW` | `NOW PIE` | `libc.so` |
| `bin/cdown` | ELF64 / DYN (PIE) | RW（NX） | ✅ | `BIND_NOW` | `NOW PIE` | `libc.so` |
| `bin/cdtool2cddb` | ELF64 / DYN (PIE) | RW（NX） | ✅ | `BIND_NOW` | `NOW PIE` | `libc.so` |

- 4 个 ELF 产物全部 `Machine: AArch64`、`INTERP` 指向 `/lib/ld-musl-aarch64.so.1`。
- 动态依赖仅 `libc.so`（无第三方库、无 glibc 残留）。
- `bin/cdadd`、`bin/cdloop` 是 `#!/bin/sh` 脚本，无 ELF 安全属性可判。

## L5：产物基线与可复现性

方法：**清缓存后重建两轮**，逐产物 sha256 比对（清缓存用容器层
`tools/clean_conan_cache.sh`，判据是 `p/cache.sqlite3` 的 `recipes`/`packages` 两表对
`cdtool` 回查为空）。

**结论：本包整体不可完全复现，根因已定位为上游源码内嵌构建时间戳；可复现子集给出基线。**

| 项 | 实测 |
|---|---|
| 包内条目总数 | 34（14 常规文件 + 20 符号链接） |
| 两轮逐字节一致 | **30**（含全部 20 条符号链接及其目标） |
| 两轮 sha256 不一致 | **4**：`lib/cdtool/cdtool`、`bin/cdctrl`、`bin/cdown`、`conanmanifest.txt` |
| 一致的非二进制产物 | `bin/cdadd`、`bin/cdloop`（`#!/bin/sh` 脚本）、6 份实体手册页 |
| 一致的 ELF 产物 | `bin/cdtool2cddb`（**不引用**构建时间戳） |

**根因（源码级，4 处调用点）**：

```
cdctrl.c:72   printf ("  Built on %s %s\n", __DATE__, __TIME__);
cdctrl.c:112  infomsg("Build: %s %s [%s]", __DATE__, __TIME__, svnid);
cdown.c:725   printf ("Build %s %s [%s]\n",__DATE__,__TIME__, svnid);
cdtool.c:218  printf("Build: %s %s [%s]\n", __DATE__, __TIME__, svnid);
```

**字节级定位证据**（round2 保留副本 vs round3，`cmp -l` 首个差异偏移处上下文）：

```
./lib/cdtool/cdtool  不同（cmp -l 行数=729），首个差异偏移=8021
   round2: ...%s %s..x.removed.%P: invalid first tra
   round3: ...%s %s..02:19:37.x.removed.%P: invalid
                        ^^^^^^^^ 差异字节即 __TIME__ 展开的时钟串
./bin/cdctrl   不同（cmp -l 行数=1210）
./bin/cdown    不同（cmp -l 行数=2409）
./bin/cdtool2cddb  逐字节一致
./bin/cdadd        逐字节一致
./bin/cdloop       逐字节一致
```

- `conanmanifest.txt` 首行是打包时间戳，**必然跨轮漂移**，按已知口径排除在全包聚合之外。
- 因此本包基线只对**可复现子集**给出：20 条符号链接的目标串 + `bin/cdadd`/`bin/cdloop`/
  `bin/cdtool2cddb` + 6 份实体手册页，两轮 sha256 完全相同（原始清单见
  `round2.sha256` / `round3.sha256` 的比对结果）。
- 该类漂移**属预期**，不是构建缺陷：上游把 `__DATE__`/`__TIME__` 写进版本横幅是
  2004 年的设计，且时间戳只在 `-V` 输出里出现，不影响功能。

## 附：G0 提示 E490 的处置说明

`conan-verify` 的 G0 打印：

```
⚠️ 已知风险 E490 未在配方中处理
   方案: restore-known-autotools-script-modes
   修复: chmod +x configure config.guess config.sub install-sh missing; ./configure; make -j1
   ⚡ G2 conan create 可能因此失败，建议先修复
```

**实测结论：本包不需要该处置。** 上游 tarball 本身保留了辅助脚本的可执行位，
conan 构建副本实测：

```
-rwxr-x--- config.guess   (43499 B)
-rwxr-x--- config.sub     (31743 B)
-rwxr-x--- configure      (177183 B)
-rwxr-x--- install-sh     (6406 B)
```

清缓存后的 G2 干净 `conan create` 两轮均 **rc=0 PASS**，未出现 E490 描述的重生成
`configure` 触发的权限/执行失败。故不在配方里添加多余 `chmod`（避免引入无错误依据的改动）。
