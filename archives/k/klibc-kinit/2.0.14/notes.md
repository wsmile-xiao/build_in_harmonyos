# klibc-kinit 2.0.14 适配笔记

## 编译环境
- 构建系统: makefile（kernel-style kbuild，自定义 Makefile，非 autotools/cmake）
- 适配日期: 2026-09-22
- 编译器: clang 15（aarch64-linux-ohos，OHOS native SDK 工具链）
- 目标平台: HarmonyOS PC（os=OHOS arch=armv8 → klibc KLIBCARCH=arm64）
- 交付物: `bin/kinit`（上游 `usr/kinit/static/kinit`，静态链接 klibc）

## 上游信息
- 名称: klibc-kinit（klibc 上游 `usr/kinit` 组件，initramfs 的 PID 1 程序）
- 版本: 2.0.14（上游 tag 2.0.14，2025-03-04）
- 许可证: 混合 — MIT AND BSD-3-Clause AND GPL-2.0-only（见 usr/klibc/LICENSE）
- 官网: https://www.kernel.org/pub/linux/libs/klibc/
- 源码: https://www.kernel.org/pub/linux/libs/klibc/2.0/klibc-2.0.14.tar.xz
- SHA256: 281bfb683e196818412af70b8968b7726475a80ff1c4bd67119e6bf5059f9075
  （真机 curl 实下 `sha256sum -c` = OK，与 kernel.org sha256sums.asc 一致）
- 架构支持: arm64 Working（usr/klibc/arch/arm64 完整；kinit 无架构专属代码）

## 与同上游兄弟任务的关系
kernel.org 的 klibc-2.0.14 一个归档被平台拆成 8 条任务：`klibc`（libc 本体，已由
PR #11156 合入）、`libklibc`、`klibc-kinit`（本条）、`klibc-dash`、`klibc-klcc`、
`klibc-fstype`、`klibc-nfsmount`、`klibc-run-init`。本包只交付 `usr/kinit` 的产物
`kinit` 一个可执行文件；构建期必须先建 `usr/klibc`（kinit 静态链它的 libc.a 与 crt0.o），
这与 `package_type=application` 的常见「依赖先发布到制品仓」不同——它用的正是**同一份
上游源码树内**的构建产物，因此 `requires` 为空，也不引入 R36/L0i 依赖顺序问题。

## W0 依赖结论

```
依赖数量：0 个 Conan 运行时/库依赖
已满足依赖：无（无 Conan 依赖）
构建期依赖：
  - Linux UAPI 头（KLIBCKERNELSRC）—— OHOS SDK sysroot 提供 linux/、asm-generic/，
    但 asm 头布局是 aarch64-linux-ohos/asm，已用 patch 0001 + KLIBCASMDIR 适配
  - 工具链 clang/llvm-ar/llvm-ranlib/llvm-strip/llvm-nm/llvm-objcopy/llvm-objdump/ld.lld
    —— 从 tools.build:compiler_executables 的 clang 同目录推导（R33）
  - perl —— syscalls.pl/makeerrlist.pl 生成 syscall 桩、errlist 与 klibc/havesyscall.h
  - GNU make + bash/shell + cp/find —— kbuild 依赖
是否需要拆分依赖适配：否
阻塞点：无
```

## 构建步骤（配方 build()）

1. 物化干净的内核 UAPI 头目录 `kernel-headers/include/{linux,asm-generic,asm}`
   （只从 sysroot 复制这三类，避开 OHOS musl 头经 `#include_next` 污染），
   同时把 `asm/asm-generic/linux` 物化进源码树 `usr/include/`。
2. `make KLIBCARCH=arm64 KLIBCKERNELSRC=<kernel-headers> KLIBCASMDIR=aarch64-linux-ohos/asm
   CC=clang HOSTCC=clang AR=llvm-ar RANLIB=llvm-ranlib STRIP=llvm-strip NM=llvm-nm
   OBJCOPY=llvm-objcopy OBJDUMP=llvm-objdump LD=ld.lld PERL=<探测到的 perl>
   EXTRA_KLIBCCFLAGS=--target=aarch64-linux-ohos EXTRA_KLIBCLDFLAGS="-m aarch64linux" -j1`
   —— patch 0004 已把顶层 Kbuild 的 all 目标收敛为 scripts/basic + usr/klibc + usr/kinit。
   产物 `usr/kinit/static/kinit`（63144 B）与 `usr/kinit/shared/kinit`、`usr/klibc/libc.a`。
3. 构建并运行上游自测（见下）。
4. Conan copy 手动打包（HarmonyOS 无 GNU install，E098）：static/kinit → bin/kinit，
   usr/klibc/LICENSE → licenses/，上游自测取证 → res/。

## 上游测试

klibc 顶层 Makefile 的 `test` 目标只构建 `usr/klibc/tests`（39 个程序，属 libc 本体，
已由 PR #11156 以 klibc/2.0.14 声明），**不涉及 usr/kinit**。kinit 组件自带的是两段用编译期
宏包起来的 standalone 自测 main：

| 文件 | 宏 | 测的东西 |
|---|---|---|
| `usr/kinit/devname.c` | `#ifdef TEST_DEVNAME` | `bdevname()`：dev_t → "(major,minor)" 分解 |
| `usr/kinit/name_to_dev.c` | `#ifdef TEST_NAMETODEV` | `name_to_dev_t()`：内核命令行 `root=` 的 8 类变体解析 |

取数命令与结果：
- `grep -rn '#ifdef TEST' usr/kinit/` → **2**（devname.c:100、name_to_dev.c:264）
- `grep -rln 'dummypmap_test\|_test\.c' usr/kinit/` → **1**（nfsmount/dummypmap_test.c，见下）

配方在 `build()` 里用刚建好的 klibc 把这两个自测**静态编译并真跑**，逐输入断言输出行：

- devname 7 个输入、name_to_dev 10 个输入，共 **17 项断言全部通过**。
- 期望值取自 klibc 自己的定义，不依赖宿主环境：
  `usr/include/sys/sysmacros.h` 的 `major=(dev>>8)&0xfff`、
  `minor=(dev&0xff)|((dev>>12)&0xfff00)`，以及 `usr/kinit/do_mounts.h` 的
  `Root_RAM0=(1,0)`、`Root_NFS=(0,255)`、`Root_MTD=(0,254)`、`Root_MULTI=(0,253)`。
- 断言只比对行尾的 `(major,minor)`，**不比对盘名**：`bdevname()` 会扫 `/sys/block`
  反查真实盘名，真机上该目录对普通用户 `Permission denied` → 回落成 `dev`；
  CI worker 上若可读则可能给出盘名。两种情况下 (major,minor) 分解都必须一致。
- name_to_dev 的输出走 `kinit.h` 的 `dprintf`，而 `dprintf` 只在 `-DDEBUG` 下被定义成
  `printf`（否则是 `((void)0)`）——这是上游自测的设计，故该自测按上游约定带 `-DDEBUG` 编译。
- 第 3 个自测入口 `usr/kinit/nfsmount/dummypmap_test.c` **未运行**，原因不是本环境缺依赖：
  上游 `usr/kinit/nfsmount/Kbuild:6` 原话是 `#FIXME - build is broken static-y := dummypmap`，
  该目标根本没登记进 `static-y/shared-y`，构建系统从不构建它；且该文件全文只有
  `#define TEST` + `#include "dummypmap.c"` 两行，而 2.0.14 的 `dummypmap.c` 里
  没有任何 `TEST` 条件块也没有 `main()`（`grep -c 'ifdef TEST' usr/kinit/nfsmount/dummypmap.c` = 0），
  按上游源码现状构造也无法链接。属上游自身失效的用例，如实记 0 跑。

## 源码修改（patch）

前 3 个与已合入的 klibc/2.0.14 同源同内容（libc 本体与 kinit 共用同一份 kbuild 上下文）：

- `0001-usr-include-ohos-asm-layout.patch`（usr/include/Kbuild：asm 头 ln→cp + KLIBCASMDIR）
- `0002-signal-kernel-nsig-compat.patch`（usr/include/signal.h：_KERNEL__NSIG → _NSIG）
- `0003-kbuild-sharedlib-cp-not-ln.patch`（usr/klibc/Kbuild：soname ln -f → cp -f，HMDFS 不支持硬链接 E079）
- `0004-kbuild-libc-kinit-only.patch`（顶层 Kbuild：all 目标收敛为 scripts/basic + usr/klibc +
  usr/kinit，跳过与本包无关的 usr/dash、usr/utils、usr/gzip）

不改任何测试文件、不改任何测试期望值、不关闭任何测试。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make` 停在 `sigsuspend.c:8: fatal error: 'klibc/havesyscall.h' file not found` | 该头是 `usr/klibc/syscalls/Kbuild` 跑 `syscalls.pl` 的副产物；而 `syscalls.mk` 是以 `-include` 引入的，**perl 路径无效时 make 会忽略这个 include 的重建失败并继续**，一路走到很远的地方才炸。配方最初把 PERL 设成 `dirname(CC)/perl`，真机上 SDK 的 `native/llvm/bin` 里根本没有 perl（CI worker 的 `/data/service/hnp/bin` 才有） | 配方按 `[cc目录/perl, /data/service/hnp/bin/perl, ~/.harmonybrew/bin/perl, PATH 里的 perl]` 顺序探测后取第一个可执行的；探测不到才退回裸 `perl` |
| 2 | kinit 组件没有 `make check`/`ctest` 可跑 | 上游 `make test` 只覆盖 `usr/klibc/tests`；kinit 的测试是 `#ifdef TEST_*` 的 standalone main，上游从不自动构建 | 配方显式用刚建好的 libc.a + crt0.o 以 `-DTEST_DEVNAME` / `-DTEST_NAMETODEV -DDEBUG` 编译并运行，断言 17 项 |
| 3 | 自测程序的链接命令报 `clang-15: error: unknown argument: '-m'` | `EXTRA_KLIBCLDFLAGS="-m aarch64linux"` 是给 **ld.lld** 的原生参数（kbuild 直接 `$(LD) -o`）；配方里改由 clang 驱动链接时同一个串会被当成 clang 自己的 `-m` | 由 clang 链接时包成 `-Wl,-m,aarch64linux`，喂给 make 的仍保持 lld 原生形式 |
| 4 | name_to_dev 自测跑起来一声不出 | `usr/kinit/kinit.h:53` 只在 `-DDEBUG` 下 `# define dprintf printf`，否则 `((void)0)` | 按上游设计带 `-DDEBUG` 编译该自测（只影响这个独立测试程序的编译，不动 kinit 本体、不动任何期望值） |
| 5 | 消费者脚本的字面量断言恒为「找不到」 | toybox 0.8.12 的 `grep -ac` 对二进制文件不做行匹配（恒 0），`tr -c '[:print:]' '\n'` 又是恒等变换（输出字节数 == 文件大小），两者叠加导致断言**假通过/假失败** | 改用 `od -An -v -tx1 \| tr -d ' \n'` 得到整文件的十六进制流，再把待查字面量同样编码后用 shell `case` 匹配；与设备上的 `strings` 逐条交叉验证一致 |
| 6 | OHOS clang 不支持 `--print-sysroot` | SDK clang-15 无该选项 | 用 `--print-resource-dir` 向上 4 级推导 sysroot（与 klibc/2.0.14 同法） |
| 7 | `usr/kinit/static/kinit` 与 `usr/kinit/shared/kinit` 都产出来 | 上游 Kbuild 在 `KLIBCSHAREDFLAGS` 非空（arm64）时同时出静态与动态版 | 只打包 `static/kinit`：shared 版 PT_INTERP 指向 `/lib/klibc-<hash>.so`（属 klibc 包），单独发布本包无法解析 |

## 验证结果

本机（Windows）：只做 `python -m py_compile` / `sh -n` / JSON 解析的结构自检，不做构建。

真机（HarmonyOS PC，HongMeng Kernel 1.12.0 aarch64，独立
`CONAN_HOME=~/work/psj/ch-klibc-kinit`，profile 从 `~/.conan2/profiles/ohos-aarch64` 复制）：

```
conan create archives/k/klibc-kinit/2.0.14 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

- **`CREATE_EXIT:0`**，窗口 2026-09-22 03:31:03 → 03:34:23 CST（3 min 20 s），日志
  `work/psj/kk12863-ch2.log`（3608 行，先 `conan remove "klibc-kinit/*" -c` 后全新构建）
- 包引用 `klibc-kinit/2.0.14:6b129b068851896169fae42d399fa922d239ce8a`（二进制包 ID 由
  settings/options 决定，与配方修订无关；配方修订随文档改动变化，故不在此钉死）
- `kinit built: .../usr/kinit/static/kinit (63144 bytes)`
- **`upstream kinit self-tests: 17/17 case assertions passed`**（`programs=2 cases=17 failures=0`，
  逐条输出转录在包内 `res/upstream-tests-summary.txt` 与 `reports/test-report.md`）
- 消费者 `test_package`：**`ASSERTIONS: 18, FAILURES: 0` / `HMBS_TEST_PACKAGE_RESULT: PASS`**
- L1e/R34 破坏性反向：`POS_EXIT:0` → 隐藏包内 `p/bin` → `NEG_EXIT:1`（test_package `build()`
  的 bindir 校验即报错）→ 还原 → `POS2_EXIT:0`，日志 `work/psj/kk12863-neg.log{,.neg,.pos2}`
- 包内产物：`bin/kinit`(63144) / `licenses/LICENSE` / `res/README` / `res/upstream-tests-summary.txt`

## 注意事项
- `kinit` 是 initramfs 的 PID 1 程序，**不得在在线系统上 exec**：`usr/kinit/kinit.c` 的
  失败路径 `umount2("/proc")`/`umount2("/sys")`（288-320 行），成功路径经
  `usr/kinit/initrd.c:113-154` 与 `usr/kinit/run-init/` 用 `MS_MOVE` 重挂根 + `chroot`
  后接管 init。因此消费者对它做装载前静态校验，理由写进 `test_package/MANIFEST.yml`。
- `package_type=application` + 产物有 `bin/` → 必须有软件级 `archives/k/klibc-kinit/commands.json`
  （L0k/R38）。
- 版本号 2.0.14 与上游一致，未递增。
- 不提交 reports/、ci-metadata.json 等生成物；`res/upstream-tests-summary.txt` 是包内产物，
  不随配方提交。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | kbuild 交叉编译 + copy 打包配方（工具链/sysroot/asm 头/perl 探测；上游自测编译并实跑断言） |
| conandata.yml | 源码 URL/SHA256 + 4 个 patch 声明（list 格式，L0f） |
| patches/0001~0004 | OHOS 移植补丁（前 3 个与已合入的 klibc/2.0.14 同源） |
| test_package/conanfile.py | 校验包内产物路径（R34/L1e）+ 跑消费者脚本 |
| test_package/test_klibc_kinit.sh | 18 项消费者断言 |
| test_package/MANIFEST.yml | 上游测试声明（含 dummypmap_test 不运行的技术原因、kinit 不 exec 的原因） |
| manifest.yaml / notes.md | 版本级 manifest 与适配笔记 |
| ../commands.json | 软件级 CLI 声明（L0k/R38） |
