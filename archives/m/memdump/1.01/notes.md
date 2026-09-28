# memdump 1.01 适配笔记

## 编译环境

- 构建系统: makefile（上游 raw Makefile，无 configure / 无 CMake / 无 autotools）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`；构建主机 **没有 gcc**）
- 构建主机: B 机（HarmonyOS PC，aarch64，HongMeng Kernel 1.12.0）
- 状态: built（W3 本地 CI 见 `.ci-result.json`，未 upload）

## 编译步骤

实际生效的命令（配方 `build()` 里就是这个形状）：

```sh
make all CC=clang DEFS=-DLINUX2 -j1
```

三个要素缺一不可，各自对应下面「问题 1/2/3」的一手读数。

## 遇到的问题与解决方案（症状 → 根因 → 最小复现 → 已试过的失败方案 → 最终方案 → 适用边界）

### 问题 1：裸 `make` 在 OHOS 上根本不进编译

- **症状**：`make -j1` 退出码 2，第一条真实错误：
  `unsupported system: HarmonyOS.HongMeng Kernel 1.12.0` → `make: *** [Makefile:12: what] Error 1`
- **根因**：Makefile 的**第一个目标**（即默认目标）是 `what:` → `@sh makedefs`。
  makedefs 用 `case "$SYSTEM.$RELEASE"` 匹配 `uname -s`.`uname -r` 决定 `DEFS`。
  本机构实测读数：`sysname=HarmonyOS`、`release=HongMeng Kernel 1.12.0`、`machine=aarch64`
  ⇒ 不匹配任何 `Linux.2*` / `FreeBSD.*` / `SunOS.5*` 分支，落到 `*)` 打印 unsupported 并 `exit 1`。
- **最小复现**：`sh makedefs`（在解包目录里单独跑）⇒ 同样打印 unsupported system、rc=1。
- **已试过的失败方案**：
  - `make -j1`（默认目标）：rc=2，如上；
  - `make CC=clang -j1`、`make CC=clang DEFS=-DLINUX2 -j1`：**照样 rc=2**——只要不指定目标，
    入口永远是 `what:`，DEFS/CC 传进去也没被用到。
- **最终方案**：显式指定目标 `make all`，并自带 `DEFS=-DLINUX2`（等于替 makedefs 做它做不了的平台判定）。
- **适用边界**：所有「首目标是平台探测脚本」的上游 raw Makefile（本包同作者的 TCT/makedefs 家族）。
  判定方法是看 Makefile 第一条 `目标:`，而不是假设有 `configure`。

### 问题 2：Makefile 写死 `CC = gcc -Wformat -Wunused`，构建主机没有 gcc

- **症状**：`make all -j1` rc=2，第一条真实错误：
  `make: gcc: No such file or directory` → `make: *** [<builtin>: memdump.o] Error 127`
- **根因**：`command -v gcc` 在本机为空（只有 `/data/service/hnp/bin/clang`），
  而上游把编译器名连告警选项一起写死在 Makefile 第 2 行。
- **最小复现**：`make all -j1`（不覆盖 CC）⇒ 127。
- **已试过的失败方案**：靠环境变量 `CC=clang` 导出给 make ——无效，
  Makefile 内的 `CC =` 赋值优先于环境（除非 `-e` 或命令行覆盖）。
- **最终方案**：命令行覆盖 `make all CC=<conf 取到的 c 编译器>`。按 R33 用
  `self.conf.get("tools.build:compiler_executables:c", "clang", check_type=str)`，
  不裸用 `${CC}`（CI worker 上为空）。上游 `-Wformat -Wunused` 随 gcc 串一起被替换，
  clang 默认告警保留，不影响产物。
- **适用边界**：本机及 CI worker 均无 gcc（CI 能力矩阵里 gcc/clang 皆可，但 PATH 上只有 clang），
  任何 CC 写死 gcc 的裸 Makefile 同此处置。

### 问题 3：`<paths.h>` 不暴露 `_PATH_MEM` / `_PATH_KMEM`（本包的实质适配点）

- **症状**：`make all CC=clang DEFS=-DLINUX2 -j1` rc=1，恰好 3 条错误：
  ```
  memdump.c:338:24: error: use of undeclared identifier '_PATH_MEM'
  memdump.c:360:13: error: use of undeclared identifier '_PATH_KMEM'
  memdump.c:414:40: error: use of undeclared identifier '_PATH_KMEM'
  ```
- **根因**：`DEFS=-DLINUX2` 分支只 `#include <paths.h>` 并指望它给两个设备路径宏。
  glibc/BSD 的 `paths.h` 有 `_PATH_MEM`/`_PATH_KMEM`，OHOS libc（musl 系）的 `paths.h`
  **没有这两项**（同一份 `paths.h` 里的 `_PATH_DEFPATH` 等仍在），于是 3 处引用全部未定义。
  另外不带 `DEFS` 时先在 `memdump.c:131` 撞 `#error "This operating system version is not supported"`
  （`SUPPORTED` 仅在 SUNOS5/FREEBSD/OPENBSD/BSDI/LINUX2 五个分支里定义）。
- **最小复现**：解包后 `make all CC=clang DEFS=-DLINUX2 -j1` 即得上述 3 条；
  去掉 `DEFS` 则得到 `#error` 那条。
- **已试过的失败方案**：
  - `DEFS="-DLINUX2 -D_LARGEFILE_SOURCE -D_FILE_OFFSET_BITS=64"`（makedefs 给 Linux 2.4 的完整串）
    ⇒ 仍然 3 条同款错误（大文件宏与 paths.h 无关，实测 make_rc=2/错误数 3）；
  - `DEFS=-DSUNOS5`（该分支自己 `#define _PATH_MEM "/dev/mem"`，看着能绕过）
    ⇒ 会连带启用 `sysconf(_SC_PAGESIZE)` 与 SunOS 的 `get_memory_size()` 分支，
      给 OHOS 谎报成 SunOS，语义错误，不用；
  - 在 conanfile 里 `-D_PATH_MEM='"/dev/mem"'` 命令行注入宏 ⇒ 引号穿透 make/shell 两层，
    可读性差且 CI 端易被 L0h 误判，放弃，改走补丁。
- **最终方案**：`patches/0001-memdump.c.patch` 给 LINUX2 分支加 `#ifndef` 特征守卫
  （+6/-0，10 行上下文）：
  ```c
  #ifdef LINUX2
  #include <paths.h>
  #ifndef _PATH_MEM
  #define _PATH_MEM "/dev/mem"
  #endif
  #ifndef _PATH_KMEM
  #define _PATH_KMEM "/dev/kmem"
  #endif
  #define GETPAGESIZE getpagesize
  #define SUPPORTED
  #endif
  ```
  写法直接抄上游自己的 SUNOS5 分支（那里就内联定义了这两个宏），因此是**上游既有风格的补齐**，
  不是新功能；glibc/BSD 上宏已存在 ⇒ `#ifndef` 自动跳过，行为逐字节不变。
  补丁不含任何平台宏（无 `__OHOS__`），R8/PF5 无绕道。
- **适用边界**：`paths.h` 的 `_PATH_*` 宏集在 libc 之间不统一（glibc/BSD 全，musl 少设备类宏）。
  同类上游「`#include <paths.h>` 直接取 `_PATH_MEM`/`_PATH_KMEM`/`_PATH_X`」都应加特征守卫，
  而不是加平台宏判断。

### 问题 4：上游没有 install 目标，man 页目标依赖私有工具

- **症状**：`make install` 报无此目标；`make manpages` 依赖 `srctoman`（上游私有，发行包内没有）。
- **根因**：上游只发布源码 + 预生成的 `memdump.1`，安装交给发行版打包。
- **最终方案**：`package()` 手动搬运三件——`bin/memdump`、`share/man/man1/memdump.1`
  （手册页里 `.TH MEMDUMP 1` 就是 1 节）、`licenses/LICENSE`（IBM Public License 1.0 全文）。
  不伪造 install 目标、不动生成物。

### 问题 5：官方站的老 Apache 会「当场解压」，`get()` 的 sha256 校验对象变了

- **症状**：`conan create` 在 `source()` 直接失败：
  ```
  ConanException: sha256 hash failed for '76de8ff167d0…' file.
   Provided hash: 76de8ff167d0779d6c3b2f2f52ca9d1cc22af179c51e976fe6e3b9a5d1e5799f
   Computed hash: 179ea799af3dfb7aa7b219bc06a9038f30726e6d81978046ddf4f91c2558c2c4
  ```
- **根因**（一手对照，探针 `~/tmp/uc2/z74-memdump/dlprobe{,2}/conanfile.py` + `dlprobe.py`）：
  该站 Apache 1.3.29 对 `.tar.gz` 挂了 `Content-Encoding: x-gzip`，且只要客户端声明接受 gzip
  （Conan 下载器就是），它就**先把文件解开再发**，而 `Content-Length` 仍是旧的 `.gz` 长度。
  同一个 URL 的三种读法：
  | 客户端 | 字节数 | 首 2 字节 | sha256 |
  |---|---|---|---|
  | `curl`（不发 Accept-Encoding） | 12713 | `1f 8b`（gzip） | `76de8ff167…`（= Debian `.orig`） |
  | `urllib`（同上） | 12713 | `1f 8b` | `76de8ff167…` |
  | `conan.tools.files.download` | 51200 | `6d 65`（`memdump-1.01/…` ustar 头） | `179ea799af…` |
  `gunzip -c 官方件 | sha256sum` == `179ea799af…` ⇒ 二者是**同一份字节的两种传输形态**，
  不是两个不同发布物，也不是截断。
- **最小复现**：`conan source <只含 download 探针的临时配方>` ⇒ 直接看到 size=51200 head=6d65。
- **已试过的失败方案**（都实测过）：
  - 用 `get(self, **sources)` 直连：就是上面的失败（`G2 FAIL`，日志 `reports/conan-create.log`）；
  - 请求头改 `Accept-Encoding: identity` / `deflate` / `x-gzip` / 空串：
    **全部 `Download failed, check server`**（这台 2004 年的 Apache 只吃 gzip/缺省），
    没有「让 conan 拿回原始 .gz」的干净开关；
  - 把 `sha256` 直接写成解压后的 `179ea799af…`：源码身份哈希会偏离发布件本体，且 CI 的
    pre-download（curl 形态，拿 .gz）与 L0/身份比对用的就是 (文件名, sha256)，
    单一哈希会在另一条形态上必挂 ⇒ 不采用；
  - 走 Ubuntu 池 `https://archive.ubuntu.com/ubuntu/pool/universe/m/memdump/memdump_1.01.orig.tar.gz`
    （实测 200）：属重打包池，按任务口径不写进配方，只留作可达性备查。
- **最终方案**：`source()` 归一化校验——先 `download()`（不传 sha256，避免 conan 侧
  「按错误形态校验」），再按 **gzip magic** 判实际形态，对 `sha256`（压缩态=发布件本体）
  或 `sha256_uncompressed`（同一字节的解压态）**必中其一**，都不中即 `ConanException` 失败；
  解包用 `unzip()`（`tarfile` mode `r:*` 自动识别，两种形态都吃）。curl 形态与 conan 形态
  因此都能过，CI 的 file:// 预下载形态同样落在这两条之内。
  ⇒ 实测通过：`Sources correctly downloaded` + `G2: PASS`。
- **适用边界**：任何「官方站在老 Apache/mod_gzip 上、`.tar.gz` 带 `Content-Encoding`」的源
  （porcupine 系、部分大学系服务器）。判据：同一 URL 用 curl 与 conan 各取一次比 sha256；
  不一致且 `gunzip` 后一致，就是这个坑。

### 问题 6：conan 2.29.1 的 `tools.build:compiler_executables` 是 dict conf

- **症状**：`Error in build() method, line 106 … ConanException: [conf]
  'tools.build:compiler_executables:c' does not exist in configuration list.`
- **根因**：本仓带的 conan 2.29.1 不把 `…:c` 子键注册进 conf 清单，取子键写法直接抛异常。
  （同仓 `archives/a/abc/0.0.0.20260511/notes.md` 已记过这个坑。）
- **最终方案**：整体取 dict 再取键——
  `comp = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)`，
  `cc = comp.get("c") or "clang"`。仍不裸用 shell 的 `${CC}`（R33）。
- **适用边界**：所有需要从 profile 拿编译器的 raw-make/custom 配方。

## 源码修改

- `patches/0001-memdump.c.patch`：memdump.c 的 LINUX2 分支补 `_PATH_MEM`/`_PATH_KMEM`
  的 `#ifndef` 特征守卫（+6 行，无删除）。由 `refresh-patch --auto` 从 `.orig`/`.work`
  基线指纹（`.orig` 侧 `feab9b52655e8a41`；`.work` 侧首版写下的是 `b09ede81583b2496`，而交付态 manifest 现值是 `0eb759e0eb8fac58` —— 两值分属该任务内两次 refresh-patch 重生成时刻的 `.work` 快照，**以盘上 manifest 现值为准**；复算：`grep -n source_.*_hash archives/m/memdump/1.01/manifest.yaml`）生成。

## 依赖版本

- **无外部依赖**。一手核过：Makefile 的 `SYSLIBS` 在本平台分支为空、链接命令
  `clang ... -o memdump memdump.o convert_size.o error.o mymalloc.o`（无 `-l*`）；
  include 面是 9 个系统头（`sys/types.h` `sys/mman.h` `time.h` `fcntl.h` `unistd.h`
  `string.h` `stdio.h` `stdlib.h` `paths.h`）+ 3 个包内头（`convert_size.h` `error.h`
  `mymalloc.h`）。产物 `readelf -d` 只 `NEEDED libc.so`。
- `preflight_check.sh memdump/1.01` → 「预检通过（无依赖需要检查）」。

## 平台行为面取证（本包交付口径的依据，全部一手实测）

设备节点与调用面（探针 `~/tmp/uc2/z74-memdump/probe.c`，clang 编译执行，输出原文）：

```
page_size=4096
stat(/dev/mem): FAIL val=-1 errno=2 (No such file or directory)
open(O_RDONLY): FAIL val=-1 errno=2 (No such file or directory)
open(O_RDWR): FAIL val=-1 errno=2 (No such file or directory)
open(/dev/kmem,O_RDONLY): FAIL val=-1 errno=2 (No such file or directory)
```
`ls -l /dev/mem` → `ls: /dev/mem: No such file or directory`；`/dev/kmem` 同。
⇒ **不是 EACCES/EPERM（权限不够），是 ENOENT（节点不存在）**；O_RDWR 也一样 ENOENT。
对照组：`/proc/iomem` 与 `/proc/self/maps` 在本机**可读**（说明缺的是设备节点，不是整个 procfs）。

制品真执行读数（B 机，未签名、未 strip 的本包产物可直接 exec，无 E077 签名问题）：

| 调用 | rc | 第一条 stderr |
|---|---|---|
| `memdump -s 4k` | 1 | `memdump: open /dev/mem: No such file or directory` |
| `memdump -k -s 4k` | 1 | `memdump: open /dev/kmem: No such file or directory` |
| `memdump -Z` | 1 | `memdump: unrecognized option: Z` + usage 横幅 |
| `memdump -s xyz` | 1 | `memdump: bad memory dump size` + usage |
| `memdump -s 4k too_many` | 1 | `memdump: too many arguments` + usage |
| `memdump --help` | 1 | `memdump: unrecognized option: -` + usage（上游无 --help/--version） |
| `memdump -v -s 4k` | 1 | `dump size 0x1000` / `page size 0x1000` / `buffer size 0x1000` 三行 remark 先行 |

**台账更正**：任务台账写「核心行为 = mmap `/dev/mem` 做内存取证转储」。一手核对源码：
memdump 只 `#include <sys/mman.h>`，**全文件没有任何 mmap/munmap 调用**；实际用
`open()` + `read()` + `lseek()`（仅定义 `USE_PREAD` 的 SunOS 分支用 `pread()`，本平台分支不走）。
因此「mmap 家族探针」对本包并不适用，本包真正的平台行为面是**物理内存设备节点的可用性**。

## 交付口径申报

- 上游 0 测试体系 + 本包功能路径依赖 `/dev/mem` 设备节点，而该节点在 OHOS PC 上不存在 ⇒
  本包的验证口径 = 编译门禁（W2/R36/W3）+ 静态安全属性 + **消费者测试真执行制品并断言其真实
  失败形态**（`open /dev/mem: No such file or directory` + rc=1）。
- 内存转储功能在本平台不可用，属**运行级环境限制（平台未暴露 /dev/mem 设备节点），非适配缺陷**
  ——申报口径同 `archives/b/bridge-utils/1.5/notes.md` 先例。未删改上游任何测试或功能代码，
  未把断言改成「不执行只查存在」。
- 制品静态安全属性（`readelf`）：`Type: DYN (Position-Independent Executable file)`、
  `Machine: AArch64`、`FLAGS BIND_NOW`、`FLAGS_1: NOW PIE`、`NEEDED libc.so`。

## 上游测试用例盘点（R51 三步法，如实申报 N=0）

清点命令与读数（tar 内成员全列）：

```sh
tar tzvf memdump-1.01.tar.gz          # 12 个成员
Makefile 目标: what all manpages memdump memdump.1 clean depend
make -n check                          # No rule to make target 'check'
```

| 依据 | 读数 |
|---|---|
| tar 成员 | LICENSE、Makefile、README、convert_size.c、convert_size.h、error.c、error.h、makedefs、memdump.1、memdump.c、mymalloc.c、mymalloc.h（共 12 项，无 tests/ 目录、无测试源文件） |
| Makefile 目标 | 无 `check` / 无 `test`（`make -n check` 报无此规则） |
| 结论 | **上游测试总数 = 0**，故 `build()` 不集成 `make check`（MANIFEST.yml 的 `upstream_test_in_build: false` 与之一致） |

消费者测试实测账本（`test_package/test.c`，数字与 conan create 日志同源）：

| 维度 | 数 | 说明 |
|---|---|---|
| 上游测试总数 | 0 | 见上表清点证据 |
| 本包可执行测试数 | 1 | `test_package/test.c` 编成 `test_memdump`，真执行交付二进制 |
| 实测通过断言 | 21 | conan create 的 test 阶段打印 `assertions 21/21 passed` |
| 跳过 | 0 | 无按平台裁剪的断言（设备形态现场探测，分支自适应） |
| 失败 | 0 | — |

## 验证结果

```bash
# 一键（W3 本地 CI 模拟）
python3 scripts/ohc-run.py conan-verify memdump 1.01     # ✅ 配方验证通过（G1/G2/G3/G4 PASS）
python3 scripts/ohc-run.py finish memdump 1.01 built
```

`reports/conan-verify-report.md`（2026-09-27T01:09 实测）逐项读数：

| 门禁 | 结果 | 原文备注 |
|---|---|---|
| G0 预构建风险评估 | PASS | 「无法识别构建系统，跳过预查询」（构建系统判为 unknown） |
| G1 配方完整性 | PASS | name/version/source/build/package/package_info/export_sources + 补丁调用 + conandata + test_package + MANIFEST.yml 全 ✅；R26「未检测到静态链接配置（非系统同名库无需静态）」 |
| G2 conan create | PASS | 含 test_package 真执行（见下） |
| G3 系统同名库隔离 | PASS | 「无 lib/ 目录（纯可执行包）」 |
| G4 产物完整性 | PASS | ⚠️ 「无法找到程序包 ID」（工具在本路径未定位到 package_id，非产物缺失；产物由 test_package 真执行证明存在且可运行） |
| L2 烟雾 | PASS（**跳过**） | 「⏭️ 跳过（无 cache 路径）」——本版本 ConanVerifier 未设 `_cache_path`，**未真执行** `--version`/`--help` |
| L4 安全扫描 | PASS（**跳过**） | 同上，未真执行；静态属性改用手工 readelf 读数（见上节） |
| L5 产物基线 | PASS（**跳过**） | 同上 |

> 如实申报：L2/L4/L5 是**被工具跳过**而非本包通过，不作为「已通过」写入 PR 正文；
> CI 侧的 L4/L5 才是这两项的实际执行点。上游无 `--version`/`--help`，
> 本包未为此改上游 CLI 语义（若 L2 真执行会命中，读数已在「平台行为面取证」列明）。

test_package 真执行证据（`reports/conan-create.log` 第 1204-1227 行）：

```
RUN: "./test_memdump" "/storage/Users/currentUser/tmp/ch/home-memdump/p/b/…/p/bin/memdump"
probed /dev/mem=absent (No such file or directory) /dev/kmem=absent (No such file or directory)
ok   A1 rc==1 when /dev/mem unusable
…（A1-A4 B1-B3 C1-C4 D1-D2 E1-E2 F1-F3 G1-G2 H1 全 ok）…
memdump consumer test: assertions 21/21 passed
```

手工等价复现（B 机，解包后）：

```sh
make all CC=clang DEFS=-DLINUX2 -j1          # rc=0，产物 39360 B PIE
./memdump -s 4k                              # rc=1, open /dev/mem: No such file or directory
```

## 交付物

| 文件 | 说明 |
|---|---|
| `bin/memdump` | aarch64 PIE 可执行（39360 B，NEEDS libc.so） |
| `share/man/man1/memdump.1` | 上游手册页原样搬运（`.TH MEMDUMP 1`） |
| `licenses/LICENSE` | IBM Public License version 1.0 全文 |

## 注意事项

- 上游源码是 2003–2005 年风格，clang 会报 338 条 `-Wcomment`（Wietse 的 `/*++ ... /* */`
  文档注释块）与若干旧式声明告警，**全是告警，0 error**，不改上游源码风格。
- 上游无 `--version`/`--help`：任何未知选项都 `usage()` → `error()` → `exit(1)`。
  本包不为过 L2 烟雾门禁去改上游 CLI 语义，读数已如实记录在上一节。
- 官方源 `www.porcupine.org` 只有 http（443 无监听），且 5 次实测有 1 次 40s 超时——
  配方保留官方址并在 conandata.yml 顶部写清 R39/PF7 例外依据，抖动属上游老旧服务器（同
  `archives/c/chrootuid/1.3` 对 porcupine 的实测结论）。
- `makedefs` 的 `make depend` 目标会**原地重写 Makefile**，`manpages` 目标需要私有
  `srctoman`——两者都不要调用。
---

**编译结束**: 2026-09-27 01:12
**最终状态**: built

---

## W3 判决互锁（收口窗实算，非转抄）

- 复算时刻载体：`reports/w3-local-ci.log` 字节数 = 48313
- `sha256sum` 实算 = `0a19960d18449a1e9a845671c62ed3155c13137d5bad13f8b50713e9ca397e36`
- `.ci-result.json`：`exit_code=0`、`step=W3_local_ci`、`timestamp=2026-09-27T01:13:07.956750`、`integrity_hash=4d7e4bf7a8b277d2`、`log_sha256=0a19960d18449a1e9a845671c62ed3155c13137d5bad13f8b50713e9ca397e36`
- 两侧对字：`.ci-result.json` 的 `log_sha256` == 上面的 `sha256sum` 实算值 ⇒ 判决件与日志同源
- 判决标记：`[step]` 行 **47** 枚、`_RESULT=` 行 **8** 枚（G0/KC/JC/L0/L1/L2/L4/L5 形态）
- 交付判定行：上文引用的 create test 阶段原文 `memdump consumer test: assertions 21/21 passed` 即出自本日志；本包 `test_package/test.c` 是 **1 枚可执行测试**，其内部 21 条断言属该测试的自检粒度（两种口径都写，⛔ 混用）。
- 构建主机侧日志（`reports/w3-local-ci.log`、`conan-create.log`、`conan-verify-report.md`）属本仓 `.gitignore` 通配 `reports/` 排除范围、**不随 PR 入库** ⇒ 上面读数按本窗盘上实算抄录，供有设备权限者以同一命令复算。


## 发现与知识（收口窗主理-74 按 manifest 的 knowledge_ref/knowledge_gained 逐条交代）

- ✅ `DRAFT-MEMDUMP-1.01-PATHS-H-MACRO-ABSENT-FEATURE-GUARD-FALLBACK` **applied（本包新增，随本 PR 的 `knowledge/drafts/` 成对件送审，Issue #3497）**：OHOS 的 `<paths.h>` 实测只导出 24 枚 `_PATH_` 宏、`_PATH_MEM`/`_PATH_KMEM` 命中 0 ⇒ 未打补丁时编译报三行未声明标识符（本 notes:60-62）。一手复算命令与两读一致证据见该草稿的「验证」节。
- ✅ **E007 同族参照（不挂为本包处方）**：E007 讲的是 `config.guess` 不识别 HarmonyOS，本包**没有** `config.guess`（裸 Makefile），撞上的是同一"平台识别"目的的另一层载体——上游 `makedefs` 用 `uname -s/-r` 猜平台、OHOS 读数落到未支持分支 ⇒ 处方只能是显式 `make all` 自带 `DEFS`。按"字面命中≠症状同形"的口径只作同族登记，⛔ 拿 E007 的处方当本包依据。
- ✅ **E129 判定不适用（读原文后）**：`grep -rl 'paths.h' knowledge/` 全库只命中 `knowledge/graph/E129.kv`，但其原文讲的是 HMDFS 上 `umask 077` 与 `mktemp -d` 的目录权限（处方＝`umask 022`/`TMPDIR`），与本包的"头文件宏常量缺失"不同因不同处方 ⇒ 不进本包 `knowledge_ref`。
- ✅ **musl 符号层与 syscall 层均不适用**：`E051`（未实现 syscall ⇒ SIGSYS）与本包无关（本包错误停在编译期，进程未跑起来）；libc 函数/变量符号层条目亦不覆盖宏名缺失这一层。
- ✅ **`platform_only` 取值更正为 `False` 并给依据**：`git diff HEAD~1 HEAD` 一手实读：`d2cbd7ed9c` 那次提交里 `guard` 字段被复原、而 `platform_only` 是由 `False` 被工具翻成 `True` 且**无判定依据** ⇒ 本窗按同形态先例 `tcpkali` 取 `False`，依据是本补丁守卫的是"宏是否存在"这一特征（glibc/BSD 侧不触发），不按平台身份分支、也不落在平台专属目录。⛔ 把这个字段的真伪交给收口窗自己宣布 ⇒ 已交 W4 独立复 judge（r1 判 False 侧）。
- ✅ **`patch_classification.type` 由占位 `auto` 回填为 `portability`**：与 `conandata.yml` 的 `patch_type` 同一口径，属"为补 OHOS libc 差异而加特征守卫"，非 bugfix、非 vendoring。
