# lutefisk 1.0.7 — HarmonyOS PC (OHOS aarch64) 适配记录

## 1. 上游身份与取源

| 项 | 值 |
|---|---|
| 软件 | lutefisk（de novo interpretation of peptide CID spectra） |
| 上游版本 | 1.0.7（`HISTORY.txt` 末条 2006-11-30） |
| 作者 | Richard S. Johnson（1995-2006），GPL-2.0-or-later |
| 上游主页 | http://www.hairyfatguy.com/lutefisk/ （**已下线**） |
| 原始发布 | SourceForge `lutefiskxp` 项目（Debian copyright 记载） |
| 实际取源 | Debian `+dfsg` 重打包 |
| URL | `https://deb.debian.org/debian/pool/main/l/lutefisk/lutefisk_1.0.7+dfsg.orig.tar.gz` |
| sha256 | `6b1624daaf4035ec596c5ce168eb5f7cc587d50e72025639722029fce2ebbf9a` |
| Debian 版本 | `1.0.7+dfsg-7`（`debian/pool`，sha256 来自 GPG 签名的 `.dsc`） |

上游站点已不可访问，SourceForge 项目页也不再提供可下载的原始 tarball；Debian 的
`+dfsg.orig.tar.gz` 是目前唯一可校验的权威副本（`.dsc` 有 GPG 签名，sha256 逐字可核），
因此按 R39 取权威镜像。上游样本数据 `Qtof_ELVISLIVESK.dta` 与作者 2005 年发布的参考
输出 `Qtof_ELVISLIVESK.lut` 在 `+dfsg` 包里完整保留（`+dfsg` 只剔除了非自由/无用文件），
所以本适配仍能对上作者自己的参考答案。

## 2. 源码与构建系统勘察

- 14 个 `.c` / 4 个 `.h`，纯 C89/K&R 时代风格（1995-2006），无 autotools / CMake。
- 6 个手写 Makefile：`src/Makefile.{linux,sun,AIX,irix,osf,osx}`。
  `Makefile.linux` 只有一条 `.c.o` 隐式规则 + 一条显式链接行。
- `src/LutefiskProbScorer.c`（26 KB）在任何 Makefile 目标里都没有被链接，是上游死代码。
- `src/getopt.c` 只给 Mac/Win32 用，Linux 目标不编译它（README 明说）。
- 平台类型 typedef 由 `LutefiskDefinitions.h` 的 `__LINUX` 分支提供（小端 + 32 位 INT_4），
  aarch64 完全适用。
- 依赖：**只要 libc + libm**，无第三方库。`nrand48` 未被使用（`NRAND` 变量在 Makefile
  里定义了但没有任何规则引用），OHOS musl libc 也不需要额外适配。

**W0 依赖发布检查**：`requires` 为空，无外部依赖需要先发布，R36 天然满足。

## 3. 构建方式（recipe 设计）

`conanfile.py` 直接驱动 `make -f Makefile.linux`，并把 `CC/CFLAGS/LFLAGS` 作为 make 命令行
变量传入。关键点：

- Makefile 里是普通 `=` 赋值（`CC= gcc -O` / `CFLAGS= -D__LINUX`），没有 `override`
  指令，因此 make 命令行的取值天然覆盖，无需像 Debian 那样先改成 `+=`。
- `CC` 取自 `self.conf.get("tools.build:compiler_executables")`（R33：不裸用 `${CC}`）。
- `-D__LINUX` 保留（它选择上游自己的小端/32 位 typedef），不是平台宏补丁，R8 不适用。
- `CFLAGS=-D__LINUX -O2 -fPIE`，`LFLAGS=-pie -Wl,-z,relro,-z,now -lm -o`
  （PIE + full RELRO + immediate binding，满足 L4 加固门禁）。

**R49 私有 prefix**：本包没有任何依赖注入（无 `generate()`），不存在写共享
`/usr/local` 的风险。

## 4. 补丁（5 个，全部为可移植性修复，无平台宏）

| 补丁 | 内容 | 为什么必须改 |
|---|---|---|
| `0001-math-include.patch` | `LutefiskHaggis.c` / `LutefiskMain.c` 补 `#include <math.h>` | `sqrt()` / `fabs()` 之前是**隐式声明**，C89 隐式 `int` 返回值在 LP64 上把 double 结果截断成 int（clang: `call to undeclared library function 'sqrt' with type 'double (double)'`）。这是真实的数值错误，不只是告警。 |
| `0002-format-specifiers.patch` | 改写 44 处转换说明符（`%ld`→`%d`、`%d`→`%lu`、`%d`→`%p`） | aarch64 LP64 上 int 实参写进 w 寄存器并**零扩展**到 x 寄存器，`printf("%ld", int)` 会按无符号数打印（负数打印成 4294967295）；`%d` 配 `size_t` 则截断。44 条 `-Wformat` 全部清零。 |
| `0003-printf-safety.patch` | `printf(versionString)` → `printf("%s", versionString)`；两处 `"%d\0"` → `"%d"` | 版本串被当成格式串（`-Wformat-security`）；`"%d\0"` 里的 `\0` 让格式串提前结束，转换说明符根本不生效，打印的是垃圾而不是文件计数器。 |
| `0004-char-scan-and-labs.patch` | `while(*pSeq != NULL)` → `while(*pSeq != '\x0')`；3 处 `sprintf(p, "\0")` → `*p = '\0'`；`abs((long)x)` → `labs(x)` | 前者把 char 和指针常量比（`-Wpointer-integer-compare`）；语义与原意相同，属于类型正确性清理。`abs()` 收 int、`labs()` 收 long。 |
| `0005-filename-buffers.patch` | `tParam` 里 8 个 `char[256]` 路径字段 → `MAX_FILENAME_SIZE`(4096) | 命令行解析用 `strncpy(optarg, sizeof(field))`，而 conan / CI 的工作目录嵌套极深，256 字节不够。 |

补丁全部用 `diff -u --label a/... --label b/...` 机器生成，写在 `patches/` 并在
`conandata.yml` 逐条注册；`apply_conandata_patches()` 放在 **`source()`**（不是
`build()`）——因为 `build()` 直接在 `source_folder/src` 里编译，若在 `build()` 里打补丁，
Conan 2 会打到导出树的副本上而 make 编的是原始文件，补丁零作用但日志照样打印
`Apply patch`（pitfall T132）。

### 4.1 换行符：为什么不能用 `refresh-patch --auto`，也不能用 GNU patch 验证

上游 tarball 里 `LutefiskGetCID.c` / `LutefiskHaggis.c` / `LutefiskProbScorer.c` /
`LutefiskScore.c` 是 **CRLF 行尾**（且整体是混合换行：同文件内 LF/CRLF 混用）。

- `refresh-patch --auto` 内部用 GNU `patch --dry-run -p1` 校验，GNU patch 遇到
  LF 补丁 vs CRLF 源码会报 `Hunk #1 FAILED (different line endings)` 直接失败，
  因此**本包无法走 `refresh-patch --auto`**（R3 偏离，原因记录在此）。
- 本包的 5 个补丁统一提交为 **LF 行尾**（`core.autocrlf=input` 本来也会把补丁里的 `\r`
  当行尾剥掉），只有 Conan 的 `patch_ng` 对行尾 CR 不敏感，能干净应用；实测
  `conan create` 的 5 条 `Apply patch` 全部成功且 `conan create` rc=0。
- 手工验证补丁时请**用 Conan 的 `patch_ng` 或先 `sed -i 's/\r$//'` 规范化副本**，
  直接 `patch -p1` 会误判为失败。

## 5. 编译结果对比

| | 上游原始源码 | 打补丁后 |
|---|---|---|
| 编译错误 | 0 | 0 |
| clang 告警 | 66 | 9 |
| 样例谱 de novo 结果 | — | 与作者 2005 年参考输出 top-10 肽段集合完全一致 |

剩下 9 条告警全部是上游遗留的行为疑点，**故意不改**（改了会动数值结果）：
- 6 × `-Wcomment: '/*' within block comment`（注释里嵌套 `/*`）
- 2 × `-Wreturn-type: non-void function does not return a value in all control paths`（`LutefiskScore.c:2964/3052`）
- 1 × `-Wtautological-constant-out-of-range-compare: result of comparison of constant -1 with expression of type 'char' is always false`（`LutefiskGetCID.c:2731`，`goodOrBad[i] == -1`）

### 5.1 数值一致性证据（OHOS 产物 vs 上游参考）

```
$ lutefisk -q -m 1229.74 -d Lutefisk.details -p Lutefisk.qtof_params \
           -r Lutefisk.residues -s database.sequence -o out.lut Qtof_ELVISLIVESK.dta
Average signal (noise) = 128.53
Data points = 1622
Lutefisk sequences: 233
Haggis sequences: 1211
1 database sequences added.
```

| Rank | 本适配输出（X-corr） | 上游 2005 参考（X-corr） |
|---|---|---|
| 1 | `NQVLSLLVESK 0.990 0.713 0.800 0.951 0.829` | `NQVLSLLVESK 0.990 0.713 0.800 0.951 0.831` |
| 2 | `NQVLSLLVESK 0.990 0.691 0.800 0.952 0.829` | `NQVLSLLVESK 0.990 0.691 0.800 0.952 0.831` |
| 3 | `AGNVLSLLVESQ 0.990 0.668 0.822 0.951 0.773` | `AGNVLSLLVESQ 0.990 0.668 0.822 0.951 0.775` |
| 4 | `AGNVLSLLVESK 0.990 0.668 0.822 0.951 0.773` | `AGNVLSLLVESK 0.990 0.668 0.822 0.951 0.775` |
| 9 | `[212.08]ELSLLVESK 0.932 0.447 0.822 0.872 0.582` | `[212.08]ELSLLVESK 0.933 0.447 0.822 0.872 0.585` |
| 5-8, 10 | 序列与 PevzScr/Quality/IntScr 完全一致 | 同左 |

**逐项核对结论（不要当成"逐字一致"）**：

- **排名顺序**：top-10 序列顺序与参考**完全一致**。
- **肽段集合**：完全一致（10 条，含重复项）。
- **`PevzScr` / `Quality` / `IntScr`**：完全一致。
- **`Pr(c)`**：rank 9 是 `0.932` vs 参考 `0.933`，其余一致。
- **`X-corr`**：全列在小数第三位有 0.002~0.003 级差异。

后两项都是 **libm / 浮点实现差异**：参考值由作者 2005 年在另一套工具链上算出，
X-corr 列来自三角/卷积的本地 libm 实现。因此测试断言锁定「序列列 + 排名前 10 的
`Pr(c)/PevzScr/Quality/IntScr`（数值容差 0.005）」，**排除 `X-corr` 列**——
如果连 `X-corr` 一起比，本包在 CI 上会因为 libm 版本差异而随机红。

## 6. E077：可执行文件签名

OHOS 内核只加载带**合法 `.codesign` 段**的 ELF，链接器只生成 4096 字节的未签名占位段，
因此真机上 `execve()` 会 EPERM、调用方一律看到 126。`package()` 在 `os == "OHOS"` 时
执行四步自签流程（去掉占位 `.codesign` → `binary-sign-tool sign -selfSign 1` →
替换 → 恢复 0o755）。本机 WSL 无 OHOS SDK，签名工具缺失时**只告警、绝不假装成功**
（同 `tmatrix` 的做法）。

## 7. 产物布局

```
bin/lutefisk
share/lutefisk/{Lutefisk.details, Lutefisk.residues, Lutefisk.params,
                 Lutefisk.paramsLCQ, Lutefisk.lcq_params, Lutefisk.qtof_params,
                 database.sequence, License.txt, README.txt, HISTORY.txt}
share/lutefisk/examples/{Qtof_ELVISLIVESK.dta, Qtof_ELVISLIVESK.lut}
```

R38：产物是可执行 CLI，已在**软件级** `archives/l/lutefisk/commands.json`
声明（`type: "tool"`，`ref: lutefisk/1.0.7`）。

上游 `docs/`（9 个 html/htm 说明页）未打包——那是 Mac 时代的本地文档，不影响功能，
需要时按 README 自行查阅。

## 8. 测试

上游**没有任何自动化测试**（无 `make check`、无 test 目录），只随包发布 1 个样本谱 +
作者自己产出的参考输出。`test_package/` 补齐为 **20 条 shell 断言 + 8 条 ELF 断言 = 28 条**：

- T1–T3：`--help` 打印 usage 且按上游约定 `exit(1)`；9 个选项全部列出。
- T4–T16：跑完整的 de novo 流程——样本谱已安装、退出码 0、输出文件非空、版本横幅、
  `Molecular Weight: 1228.73`、`Charge State:  2`、排名表头、`Search time:`、
  ≥10 条候选、**肽段集合与上游参考输出相符**（T13）、**排名前 10 的顺序与参考相符**
  （T13b，不只是集合）、**top-10 的 `Pr(c)/PevzScr/Quality/IntScr` 与参考数值相符
  （容差 0.005，T13c）**、top-1 为 `NQVLSLLVESK`(Pr(c)=0.990)（T14）、
  stdout 报出真实数据点数与数据库载入数。
- T17 反向：输入文件不存在时必须非零退出（证明正向路径不是空转）。
- T18（含 8 条子断言，鸿蒙特有）：ELF magic、64 位小端、`EM_AARCH64`、`ET_DYN`(PIE)、
  `PT_GNU_STACK` 不可执行(NX)、`PT_GNU_RELRO`、immediate binding、
  `DT_NEEDED` 只含系统库（实测只有 `libc.so`）。`elf_check.py` 只用标准库解析 ELF，
  不依赖 `readelf`，因此 CI worker 与裸 OHOS 镜像上都能跑。

T13 / T13b / T13c 分开是有意的：只比「集合」会让「把 rank 2-10 整体倒序、分数列改成
任意值」这种变异蒙混过关（T13b/T13c 就是为堵这个盲区加的）。

### 8.1 L1e 反向破坏验证（证明测试非空壳）

| 变异 | conan test rc | 结果 |
|---|---|---|
| 基线 | 0 | 20/20 |
| 隐藏 `bin/lutefisk` | 1 | 17 条失败（T1/T17 报 rc=127） |
| 改 `e_machine` 为 x86-64 | 1 | `e_machine is EM_AARCH64 62` 失败，16 条失败 |
| 隐藏 `share/lutefisk/Lutefisk.details` | 1 | T13/T13b/T13c/T14/T15/T16 失败，12 条失败 |
| 恢复 | 0 | 20/20 |

三种变异都被抓到，说明断言真的依赖产物内容，不可能被 `echo`/`print` 空壳骗过。

## 9. 本地验证结果

| 项 | 结果 |
|---|---|
| `conan create -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing` | rc=0 |
| 编译错误 / 告警 | 0 / 9 |
| test_package 断言 | 28 条全过（20 shell + 8 ELF） |
| L1e 反向变异（手工 3 种） | 3/3 被抓 |
| 同源门禁 `ci/conan/build_and_test.sh` | **rc=0** |

门禁各阶段（`CI_BRANCH=feat/lutefisk-1.0.7 CONAN_PROFILE=ohos-aarch64-wsl
CI_PACKAGES="archives/l/lutefisk/1.0.7" zsh ci/conan/build_and_test.sh`）：

| 阶段 | 结论 |
|---|---|
| G0 知识图谱完整性 | `pass` |
| L0 质量门禁（L0a-L0q） | `pass: all checks passed` |
| KC 知识检查 | `pass`（KC1-KC5） |
| JC 垃圾文件（JC1-JC6，incremental 模式 18 文件） | `pass` |
| L1 测试执行 | `pass: test_package executed`（L1a/L1b 通过） |
| L1e 反向破坏 | `[ok] Negative test confirmed — test genuinely depends on lutefisk` |
| L2 冒烟 | `skip: --version/--help failed`（非阻塞）——上游 `case 'h'` 打印 usage 后 `exit(1)`（`LutefiskMain.c:663-677`），是上游约定不是回归 |
| L4 补丁危险函数扫描 | `warn`（非阻塞）——命中的 `sprintf`/`strcpy` 全部出现在 diff 的**上下文行**里（上游既有代码），本配方没有新增任何危险调用 |
| L5 产物基线 | `pass: bin/ has content` |

### 9.1 换行符（CRLF）注意事项

上游 tarball 的 `.c`/`.h` 是**混合换行**（部分行 CRLF、部分 LF）。补丁由
`diff -u --label` 机器生成后统一规范成 LF 提交（`core.autocrlf=input` 本来就会把
`\r` 当行尾剥掉）；实测 Conan's `patch_ng` 对行尾 CR 不敏感，LF 版补丁能干净应用到
CRLF 源码上（`conan create` rc=0，5 条 `Apply patch` 全部成功），因此不需要
`.gitattributes` 特判。

## 10. 已知限制

1. `X-corr` 列与上游 2005 参考有 0.002 级浮点差异（libm 实现差异），已在测试断言中排除。
2. 真机部署需 `binary-sign-tool` 自签（E077），本机无 SDK 无法本地验证签名步骤，
   但缺失时是告警而非失败。
3. 上游 `LutefiskScore.c:2964/3052` 两个函数存在「非 void 函数部分路径不返回值」，
   属未定义行为；修它需要理解算法分支并可能改变数值结果，本次适配**故意保留**并在此记录。
4. 数据文件默认路径是相对文件名（`Lutefisk.details`），所以必须用 `-d/-p/-r/-s` 显式
   指到 `share/lutefisk/`；未改成 Debian 的 `/usr/share/lutefisk` 硬编码路径，因为
   OHOS 上那个目录不存在。