# ctronome 0.5.6 适配笔记（HarmonyOS PC / aarch64）

## 软件概述

ctronome 是一个极简的可编程命令行节拍器（C 语言，2014 年发布）。它读取两个
WAV 采样文件作为声音素材，按 BPM / 拍号把音频数据循环写入 OSS 设备
（默认 /dev/dsp）；支持 `-p programfile` 使用节拍程序文件、`-c count`
指定播放次数、`-b/-t` 指定 BPM 与拍号。因为声音素材要外置，作者刻意把
它做得极简可改。

## 编译环境

| 项 | 值 |
|----|----|
| 目标平台 | HarmonyOS PC / OpenHarmony 6.0 / aarch64 |
| 编译器 | clang 15.0.4（OHOS SDK，/data/service/hnp/bin/clang） |
| C 运行库 | musl（ELF 解释器 /lib/ld-musl-aarch64.so.1） |
| 构建系统 | 顶层裸 Makefile（无 configure、无 install / check 目标） |
| 第三方依赖 | 无 |
| 编译日期 | 2026-09-14 |
| 状态 | built |
| 补丁 | 0001-ctronome.c.patch、0002-ctronome.h.patch（均为 portability，无平台宏） |

## 上游源码与校验

- 上游官方项目页：https://sourceforge.net/projects/ctronome/
- 源码包：ctronome-0.5.6.tar.gz（17 个条目，顶层目录 ctronome-0.5.6/）
- 下载 URL：https://downloads.sourceforge.net/project/ctronome/ctronome-0.5.6.tar.gz
- sha256：d8c17282235759491eae36efbc8fe93514dcac655efa68d3cb8db0132c29a24d
- md5：29e3ae6bbc1fb32a429ab1613c374e87
  - 与 SourceForge 项目 RSS 官方公布的 md5（29e3ae6bbc1fb32a429ab1613c374e87）
    完全一致，确认下载到的源码为上游官方原件。

> 说明：任务初始给出的
> https://download.savannah.nongnu.org/releases/ctronome/ctronome-0.5.6.tar.gz
> 现已 404（savannah nongnu 的 ctronome 发布目录已下线；重定向到的各 nongnu
> 镜像同样 404；作者旧个人站点 waterlan.home.xs4all.nl 也已随 XS4ALL 个人
> 主页服务下线）。SourceForge 官方项目页是该软件当前可用的官方发布源。
>
> 另外，SourceForge 的 `.../files/<file>/download` 链接末段没有扩展名，
> 会让 Conan 的 `get()` 按 zip 解压并报 `BadZipFile: File is not a zip file`
> （知识库 E483）。因此 conandata.yml 改用带 `.tar.gz` 末段的
> `downloads.sourceforge.net/project/...` 直链（E483 的回退方案
> rewrite-url-with-extension）。

## 编译步骤（实测）

本项目没有 configure 脚本，也没有 install / check 目标。实际流程：

```bash
# 1) 解包（conan 的 get(strip_root=True) 等价操作）
tar xzf ctronome-0.5.6.tar.gz

# 2) 应用 2 个 portability 补丁（见下节，由 conanfile.py 的
#    apply_conandata_patches 自动完成）

# 3) 编译（不需要任何额外编译标志）
make CC=/data/service/hnp/bin/clang -j1

# 4) 打包（上游无 install target，由 conanfile.py package() 用 copy() 完成）
#    bin/ctronome、share/ctronome/*.wav|README|NOTES|prog_example.txt、
#    licenses/COPYING
```

`make install DESTDIR=...` 不可用：上游 Makefile 只有 `all` 与 `clean`
两个目标。因此在 `package()` 中显式 copy，等价于上游 README 描述的
“手工 cp 安装”，并在 staging 目录做了验证。

conan create 日志中的实际构建命令：
```
ctronome/0.5.6@ohpcd/stable: RUN: make CC="/data/service/hnp/bin/clang" -j1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接期 ld.lld 报 12 处 `duplicate symbol: programfile / dsp_channels / dsp_format / dsp_speed / dsp_depth / debug` | ctronome.c、dsp.c、routines.c 都 include ctronome.h，而 ctronome.h 里**直接定义**了这些全局变量（2014 年的暂定义写法），依赖 GCC 10 以前的 common symbol 合并语义；clang 15 默认 -fno-common，每个 .o 都落成强定义 | **打补丁从源码修复**：把 ctronome.h 中这 6 个暂定义改成 `extern` 声明，并在 ctronome.c 中给出唯一一份定义（C99 起的标准做法）。**刻意不使用 `-fcommon`**——知识库 E491 明确禁止 `-fcommon`，它只会掩盖非法的声明/定义关系 |
| 2 | `source()` 报 `BadZipFile: File is not a zip file` | conan 的 `get()` 按下载 URL 末段扩展名推断压缩格式；SourceForge 的 `.../files/<file>/download` 末段没有扩展名 | 改用带 `.tar.gz` 扩展名的下载直链（知识库 E483 的回退方案 rewrite-url-with-extension），未改 `get()` 调用本身 |
| 3 | `build()` 报 `ConanException: [conf] tools.build:compiler_executables:c does not exist in configuration list` | `tools.build:compiler_executables` 是字典型 conf，不存在 `:c` 这种子键形态 | 整体读取字典再取子键：`self.conf.get("tools.build:compiler_executables", check_type=dict, default={})` 然后 `.get("c", "clang")` |
| 4 | 单独设置 `CFLAGS` 完全无效 | 上游 Makefile 的编译规则是 `$(CC) -c $<`，根本没有引用 `$(CFLAGS)` | 编译标志只能随 `CC` 一起传入（`make CC="..."`）；配方中 CC 取自 conan conf（R33）。本包最终不需要任何额外标志 |
| 5 | 运行时报 `FATAL: cannot open dsp device /dev/dsp` | 程序音频输出使用 OSS（dsp.c 里的 open/ioctl），HarmonyOS PC 没有 /dev/dsp 字符设备 | 平台限制，非编译问题。可用 `-d <device>` 指向其它 OSS 兼容设备；test_package 据此把该输出作为“已跑到音频输出阶段”的判据 |

**未遇到**：OSS 头文件缺失。OHOS SDK sysroot 自带 `sys/soundcard.h` 与
`linux/soundcard.h`，`SNDCTL_DSP_*` 常量齐全，`dsp.c` 无需任何移植改动
即编译通过。

## 源码修改

共 2 个补丁，均为 **portability** 类型，**不包含任何平台宏**（无 `__OHOS__`）：

| 补丁 | 内容 |
|------|------|
| `0001-ctronome.c.patch` | 在 ctronome.c 中新增 6 个全局变量的定义（+10 行） |
| `0002-ctronome.h.patch` | 把 ctronome.h 中 6 个暂定义改为 `extern` 声明（+6/-6） |

补丁由 `refresh-patch --auto` 基于编辑追踪器（`track-edit`）生成，
`conandata.yml` 中已声明并被 `apply_conandata_patches()` 自动应用
（conan create 日志可见 `Apply patch (portability)` 两行）。

## 上游测试清点与实测（R51 三步法）

### 第一步：清点上游测试

```bash
$ tar tzf ctronome-0.5.6.tar.gz | grep -icE "test|check"
0
$ make -n check
make: *** No rule to make target check.  Stop.        # rc=2
$ make -n test
make: *** No rule to make target test.  Stop.         # rc=2
```

上游源码包共 17 个条目，无 tests/ 或 test/ 目录，无 CMakeLists.txt、
无 pytest / ctest 注册，顶层 Makefile 只有 `all` 与 `clean` 两个目标。

**结论：上游没有官方自动化测试**（这是实测清点结论，不是“未填写”），
因此 `test_package/MANIFEST.yml` 的 `upstream_tests` 为空列表，
`upstream_test_in_build: false`。

### 第二步：在可运行环境实际运行

上游没有可运行的测试程序，因此无可执行的上游用例；改为在 test_package
中做真实的消费者视角验证（真实执行被测二进制，并在 conan create 的
test 阶段实际运行）。

### 第三步：如实回填实测结果

| 项 | 数值 |
|----|------|
| 上游测试用例数 N | 0（清点证据见上） |
| 实际可运行数 N2 | 0 |
| 通过率 | 不适用（无上游用例） |
| test_package 自测断言 | 19 条（功能 3 + 鸿蒙特有 16），conan create 实测全部 PASS（`ALL 3 ASSERTIONS PASSED`、`OHOS ASSERTIONS PASSED: 16/16`、`ALL OHOS TESTS PASSED`） |

## 鸿蒙特有测试（test_package/test_ohos.sh，16 条断言）

除保留上游行为视角的功能测试外，新增针对鸿蒙平台特性的测试脚本
`test_package/test_ohos.sh`（写法参考仓库先例
`archives/m/mkp224o/1.7.0/test_package/test_ohos.sh`）。该脚本由
`test_package/conanfile.py` 的 `test()` 在 `conan create` 的 test 阶段**真实执行包内最终
产物** `<pkg>/bin/ctronome`（R34），不是只打印字符串的空壳测试。

脚本 `set -euo pipefail`；readelf / strings / bash 三类工具全部**探测式 fail closed**
（首选 `/data/service/hnp/bin/llvm-readelf`、`/data/service/hnp/bin/strings`，回退 PATH 同名
工具，都找不到即失败，绝不静默跳过断言）；每次真实运行都用 `timeout 60` 包裹，任何非零
退出、信号（rc≥128）、超时（124）、崩溃标记一律判失败。每条断言打印 `OK: n/16 ...`，
末尾打印 `OHOS ASSERTIONS PASSED: 16/16` 与 `ALL OHOS TESTS PASSED`。

| # | 测试项 | 覆盖的鸿蒙平台特性 | 实测结果 |
|---|--------|--------------------|----------|
| 1 | `Class: ELF64` | 目标 ABI 位宽 | OK |
| 2 | `Machine: AArch64` + `Type: DYN` | 目标架构 + 位置无关可执行（PIE） | OK |
| 3 | `.interp == /lib/ld-musl-aarch64.so.1` | OHOS 使用 musl libc 而非 glibc | OK |
| 4 | `readelf -l` 的 "Requesting program interpreter" 与 `.interp` 一致 | 解释器交叉校验 | OK |
| 5 | 无 RPATH / RUNPATH | 鸿蒙 `$ORIGIN` 解析不稳定，产物必须无 RPATH | OK |
| 6 | `NEEDED` 仅 `libc.so` | 动态依赖只有 musl libc；显式拒绝 libc.so.6 / libpthread.so.0 / libdl.so.2 / librt.so.1 / libm.so.6 / libgcc_s.so 等 glibc 专有库 | OK |
| 7 | `.codesign` 恰好 1 个 + `.note.ohos.ident` 存在 | OHOS ELF 签名与平台标识 | OK |
| 8 | 可加载段（.interp/.rodata/.data/.dynstr/.dynamic）内无 `/storage/`、`/home/`、`/data/service/hnp`、`/build/`、`/devcloud/`、`/root/`、`/tmp/`、`/workspace/` 等构建路径 | 产物不泄漏构建环境 | OK |
| 9 | 整个二进制内无 `/storage/`、`/home/`、`/data/service/hnp`、`/build/` 绝对路径 | 无构建机绝对路径（同时不误伤上游硬编码的 `/usr/share/ctronome/*.wav` 与 `/dev/dsp`） | OK |
| 10 | `bash -c "<bin> -h"` 正常（rc=0 且打印 usage） | **鸿蒙 shell 约束**：OHOS `/system/bin/sh` 不能直接 exec ELF，程序须经 bash 调用（本包 conanfile 用 `CONFIG_SHELL`/bash 包裹执行的原因） | OK |
| 11 | 包内产物完备：4 个采样 WAV（mono/stereo 各 2）+ README/NOTES/prog_example.txt + licenses/COPYING | 打包完整性 | OK |
| 12 | 不传 `-w1/-w2` → `cannot open /usr/share/ctronome/metronome1.wav`、rc=1、无崩溃 | **上游硬编码默认路径在 OHOS 不存在**（无 `/usr/share`），平台差异被优雅处理并如实记录 | OK |
| 13 | 传包内采样 → WAV 头与数据解析成功（无 `too short` / `cannot open` / 通道·位深不一致） | 随包采样真实可用 | OK |
| 14 | `/dev/dsp` 不存在 → `FATAL: cannot open dsp device /dev/dsp`、rc=1、无崩溃 | **OSS 平台能力缺口**：程序在完成参数解析 + WAV 解析后到达音频输出阶段并优雅退出 | OK |
| 15 | `-d /dev/ctronome-ohos-probe` → 报错文本中出现该自定义设备名、rc=1 | `-d` 覆盖默认设备生效 | OK |
| 16 | 上述 3 次真实运行均无 rc≥128 / `Segmentation fault` / `core dumped` | 鸿蒙上不得崩溃 | OK |

实跑命令（独立 worktree，避免与并发 agent 冲突）：

```bash
cd /storage/Users/currentUser/tmp/ctronome-ohos-tests
conan create archives/c/ctronome/0.5.6 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

实测结论：`conan create` rc=0；功能测试 `ALL 3 ASSERTIONS PASSED`；
鸿蒙特有测试 `OHOS ASSERTIONS PASSED: 16/16` + `ALL OHOS TESTS PASSED`；
conanfile 最终输出 `ctronome: functional + OHOS tests OK (3 + 16 assertions)`。

### 鸿蒙测试暴露的环境事实（记录，非适配缺陷）

1. 二进制 debug 段（`.debug_info` / `.debug_str` / `.debug_line` / `.debug_line_str`）中出现
   OHOS SDK 自身的构建路径 `/devcloud/slavespace/usr1/.../harmony_code/codearts_workspace/out/sdk`
   （共 4 处）。定位确认它只落在**非可加载的 DWARF 段**（断言 8 已证明可加载镜像内为 0 处），
   来源是 OHOS SDK 预编译 crt 目标文件自带的调试信息，**不是本机构建路径泄漏**，故不计缺陷；
   测试脚本以 `[info]` 行记录出现次数作为证据，供评审核对。
2. 上游硬编码默认值 `/usr/share/ctronome/metronome1.wav`、`metronome2.wav`、`/dev/dsp`
   属"上游默认路径"，不是构建机路径，因此断言 8/9 的白名单据此设计，不误伤。
3. 测试机上的 `/usr/bin/sh -c` 直接 exec ELF 恰好成功（rc=0），说明它并非受限的
   `/system/bin/sh`；因此断言 10 只对 **bash 包裹执行**这条 OHOS 官方可用路径做硬断言，
   直接 exec 的探测结果仅以 `[info]` 记录，避免把环境差异写成假阳性断言。

## 验证结果

### conan-verify（本地 W3 前置，8 道门禁）

```
G1: PASS  配方完整性
G2: PASS  conan create（干净构建 + test_package 执行）
G3: PASS  系统同名库隔离（纯可执行包，无 lib/ 冲突）
G4: PASS  产物完整性
L2/L4/L5: PASS（本机未缓存路径时跳过，另做手工核验见下）
Verdict: PASS
```

### 手工核验（补充 L2/L4/L5 证据）

```bash
$ conan cache path ctronome/0.5.6@ohpcd/stable:<pkgid>
$ find <pkg> -type f
  bin/ctronome
  share/ctronome/{metronome1,metronome2,metronome1_stereo,metronome2_stereo}.wav
  share/ctronome/{README,NOTES,prog_example.txt}
  licenses/COPYING
$ <pkg>/bin/ctronome -h          # rc=0，打印 usage
$ <pkg>/bin/ctronome -b 120 -t 4 -c 1 -w1 .../metronome1.wav -w2 .../metronome2.wav
  FATAL: cannot open dsp device /dev/dsp    # rc=1（平台无 OSS 设备，预期）

# L4 静态安全（手工 checksec 口径）
Type:      DYN (Position-Independent Executable file)   # PIE ✓
GNU_RELRO  存在                                          # RELRO ✓
FLAGS: BIND_NOW / FLAGS_1: NOW PIE                       # Full RELRO ✓
GNU_STACK  RW（无 E）                                    # NX ✓

# L5 产物基线
sha256(bin/ctronome) = b3ec22c521660208d4b1ecf0b4c76c4b635d14bce7b5e938562585bb2bfb84d4
size                 = 35200 bytes
```

### test_package 实测输出（conan create 日志：功能测试 + 鸿蒙特有测试）

```
ctronome/0.5.6 (test package): RUN: "/data/service/hnp/bin/bash" test.sh "<pkg>/bin/ctronome"
[step] binary: <pkg>/bin/ctronome
[step] share : <pkg>/share/ctronome
OK: 1/3 -h prints usage
OK: 2/3 -v prints version banner
FATAL: cannot open dsp device /dev/dsp
/dev/dsp: No such file or directory
OK: 3/3 wav parsed, reached audio output stage (rc=1)
ALL 3 ASSERTIONS PASSED

ctronome/0.5.6 (test package): RUN: "/data/service/hnp/bin/bash" test_ohos.sh "<pkg>/bin/ctronome"
[ohos] binary : <pkg>/bin/ctronome
[ohos] share  : <pkg>/share/ctronome
[ohos] readelf: /data/service/hnp/bin/llvm-readelf (...)
[ohos] bash   : /data/service/hnp/bin/bash
OK: 1/16 ELF class is ELF64
OK: 2/16 AArch64 DYN (PIE)
OK: 3/16 interpreter /lib/ld-musl-aarch64.so.1 (musl, not glibc)
OK: 4/16 readelf -l confirms /lib/ld-musl-aarch64.so.1
OK: 5/16 no RPATH/RUNPATH
OK: 6/16 NEEDED = libc.so (musl libc only)
OK: 7/16 .codesign x1 + .note.ohos.ident present
OK: 8/16 loadable image has no host/SDK build paths
OK: 9/16 no build-machine absolute path in binary
OK: 10/16 bash -c "ctronome -h" works (rc=0)
OK: 11/16 package ships 4 WAV samples + docs + COPYING
OK: 12/16 default /usr/share path missing -> graceful exit rc=1, no crash
OK: 13/16 packaged WAV samples parsed successfully
OK: 14/16 /dev/dsp absent -> 'FATAL: cannot open dsp device /dev/dsp', rc=1, no crash
OK: 15/16 -d override honoured (diagnostic names /dev/ctronome-ohos-probe)
OK: 16/16 all 3 real runs exited gracefully (no signals, no core dump)
OHOS ASSERTIONS PASSED: 16/16
ALL OHOS TESTS PASSED

ctronome/0.5.6 (test package): ctronome: functional + OHOS tests OK (3 + 16 assertions)
```

备注：`-v` 打印的版本串是 `ctronome v0.5.5`，这是**上游自身的版本号笔误**
（Makefile 里 `VERSION = 0.5.5`、ctronome.h 里 `#define VERSION "0.5.5"`，
但发布包是 0.5.6）。属上游现状，未做修改；test_package 因此只断言版本
横幅前缀 `ctronome v`。

## 依赖版本

无第三方依赖（`requirements()` 为空，init-build 的依赖解析报
“所有依赖已就绪”）。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（Makefile 工程 + application 类型） |
| conandata.yml | 源码 URL、sha256 与 2 个 portability 补丁声明 |
| patches/ | 0001-ctronome.c.patch、0002-ctronome.h.patch |
| test_package/ | 真实执行被测包产物的测试：conanfile.py（test() 依次调用两个脚本）+ test.sh（功能测试 3 断言）+ test_ohos.sh（鸿蒙特有测试 16 断言）+ MANIFEST.yml（assertion_count=19） |
| manifest.yaml | 版本级元数据 |
| commands.json（软件级） | 命令行工具声明（R38） |

## 注意事项

1. ctronome 的音频输出强依赖 OSS /dev/dsp，HarmonyOS PC 无此设备，
   因此**开箱即用时只能验证到参数解析 + WAV 解析 + 到达音频输出**，
   实际发声需要 OSS 兼容层或改走其它音频后端（上游未提供）。
2. 默认 WAV 路径被硬编码为 `/usr/share/ctronome/metronome1.wav`
   （ctronome.h），本配方把采样安装到 `<prefix>/share/ctronome/`，
   运行时需用 `-w1/-w2` 显式指定。
3. 源码里的 `metronome1.wav` 是单声道、`metronome1_stereo.wav` 是立体声，
   两者不能混用（程序会检查两个 WAV 的通道数与位深必须一致）。
---

**编译结束**: 2026-09-14 10:12
**最终状态**: built
