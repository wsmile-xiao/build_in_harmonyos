# ppunpack 1.0 适配笔记

## 编译环境

- 构建系统: makefile（上游手写 Makefile，25 行）
- 编译日期: 2026-09-25
- 编译器: OHOS NDK clang 15（`/data/service/hnp/bin/clang` → `aarch64-unknown-linux-ohos-clang`）
- 构建机: x86_64 runner，交叉目标 aarch64-linux-ohos；qemu-aarch64（binfmt）可用
- 状态: built（conan-verify G1-G4 通过，test_package 8/8：上游 1/1 + 新增 7/7）

## 源码

- `https://ftp.fau.de/aminet/misc/unix/ppsmall-1.0.tar.Z`（Aminet 官方镜像，5251 字节，
  sha256 `d305c14162f9039e65c0a2fea0087ba190e7e5732e3f8efacee8187892e603a9`）
- Aminet 同时列出 short（`ppsmall-1.0.tar.Z`，5.1 KB）与 long（`ppunpack-1.0.tar.Z`，约 198 KB）两个包；
  本配方**只用 short 版**。short 版内容：`PPUnpack/{README,Makefile,depack.c,depack.h,ppunpack.c}`。
  readme 原文 "This small archive does not include any test file."

## 编译步骤

```bash
# 手工探索（init-build 解不开 .tar.Z，先手工解到 .orig 再重跑 init-build）
zcat ~/tmp/builds/ppunpack-1.0.tar.gz | tar xf - -C ~/tmp/builds/ppunpack-1.0.orig --strip-components=1
python3 scripts/ohc-run.py init-build ppunpack 1.0 --url=https://ftp.fau.de/aminet/misc/unix/ppsmall-1.0.tar.Z
cp --remove-destination ...            # 断开 .work 与 .orig 的硬链接（E543）

# 配方中实际执行的构建
make -j1 ppunpack CC=/data/service/hnp/bin/clang COPTS='-O3 -fPIE -static-pie'
```

产物：`bin/ppunpack` —— ELF 64-bit LSB pie executable, ARM aarch64, static-pie linked。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` 报 `解压失败: not a gzip file` | `.tar.Z` 是 compress(1) LZW（魔数 `1f 9d`），`_guess_tar_format()` 对未知扩展名缺省 `tar.gz` | 探索阶段手工 `zcat` 解到 `.orig` 后重跑 init-build |
| 2 | conan `get()`/`unzip()` 对 `.tar.Z` 报 `BadZipFile: File is not a zip file`（本地实测） | `unzip()` 只认 gz/bz2/xz/tar，其余落入 zip 分支；设备 toybox gzip 无 LZW；`source()` 时 buildenv 未生效，cmake 是否在 PATH 不受控（本 runner 默认 PATH 里就没有 cmake） | `source()` 用 `download(..., sha256=...)` + 配方内置 Python `_unlzw()`（gzip `unlzw.c` 移植）+ `tarfile` 逐成员解出（剥顶层目录、拒绝绝对路径和 `..`）。与 GNU `zcat` 结果逐字节一致（16384 字节 tar）。知识草稿 **E6417-draft-CC63** |
| 3 | `make` → `acc: No such file or directory`，`CC=clang make` 同样失败 | Makefile 里 `CC=acc` 是文件内赋值，压过环境变量；只有命令行赋值能覆盖（E392 raw-makefile 同类） | 命令行传 `CC=<compiler_executables.c>`，编译器取自 profile conf（R33） |
| 4 | 命令行传入 CC 后仍在 `check` 失败：`ppunpack sf.pp sf` → No such file | `all: ppunpack check`，check 依赖的 `sf.pp`/`sf.chk` 只在 long 版里 | 只构建 `ppunpack` 目标；不打补丁 |
| 5 | x86 runner 上动态链接的 OHOS 产物无法执行（缺 `/lib/ld-musl-aarch64.so.1`，E544） | binfmt 下的 qemu 找不到 OHOS musl loader | 以 `-static-pie` 链接（仅依赖 libc，保留 PIE/RELRO），交付产物本身即可被 qemu-aarch64 执行；同思路先例 whichman 2.4（E544-draft-0ADA） |

编译告警（未处理，非错误）：3 处 `-Wdeprecated-non-prototype`（上游 1995 年的 K&R 函数定义）；
编译阶段 `-static-pie` 的 `-Wunused-command-line-argument`（COPTS 同时用于编译与链接规则，链接时才生效）。

## 源码修改

无补丁。所有适配都在配方里完成（源码解码、make 命令行、链接方式）。

## 依赖版本

无第三方依赖（W0：只用 libc；`conan download ppunpack/1.0 -r=ohpcd --only-recipe` 确认制品仓无同名同版本）。

## 测试

### 上游测试清点（R51）

| 项 | 数量 | 证据 |
|---|---|---|
| tests/ 目录 | 0 | 分发包只有 5 个文件 |
| ctest/pytest 注册 | 0 | 无 CMake / Python |
| Makefile 测试目标 | 1（`check`） | `check: sf` → `ppunpack sf.pp sf` + `diff sf sf.chk` |
| 已执行 | 1 | 见下 |

上游 N=1，N′=1，通过 1/1。

`sf.pp`/`sf.chk` 不在 short 分发包内（readme："This small archive does not include any test file."），
而 Aminet 的 long 版 `ppunpack-1.0.tar.Z`（202559 字节，sha256
`1b06fd4d699b2e543ff06c6258082057098be0f379d815dae6925e4e8c9f13be`，FAU 镜像与 aminet.net 两源一致）
带这两个文件（readme："This archive does include a test file."）。已逐文件核对：long 版的
README / Makefile / depack.c / depack.h / ppunpack.c 与 short 版**逐字节相同**，只多出 `sf.pp`（78060 B）
与 `sf.chk`（140095 B）。

因此**包的源码仍只用 short 版**，long 版只作为上游测试数据来源：test_package 的 U1 从 Aminet 官方镜像
下载 long 版（sha256 固定），只取 `sf.pp`/`sf.chk`，用安装后的 `bin/ppunpack` 按 check 目标原样执行
`ppunpack sf.pp sf`，再逐字节比较 `sf` 与 `sf.chk`（等价于 `diff`）。上游测试文件未做任何修改。

### 适配后测试（test_package，上游 1 + 新增 7 项）

U1 即上游 `make check`（见上）。以下 7 项为新增：

`pp20.py` 是按 `depack.c` 位流逆推出来的 PP20 编码器，test_package 现场生成输入，
由安装后的 `bin/ppunpack` 还原并逐字节比对：

| # | 用例 | 类型 |
|---|---|---|
| 1 | 无参数 → exit 1，输出含 `ppunpack 1.0` / `Usage:` | 功能 |
| 2 | 1320 字节文本往返 | 功能 |
| 3 | 700000 字节往返，并断言 6 条码路径（字面量串、2/3/4 字节匹配、5+ 匹配的 7 位与 13 位偏移）全部被用到 | 功能 |
| 4 | 1 字节载荷往返（纯字面量 + 循环终止） | 功能 |
| 5 | 非 PP20 输入 → exit 10 + `not a powerpacked file`，且不生成输出文件 | 功能（负向） |
| 6 | 输入不存在 → exit 10 + `can't open input file` | 功能（负向） |
| 7 | **[鸿蒙特有] 消费者流程**（`test_package/consumer.c`）。前置：交付产物为 ELF64 AArch64、带 OHOS NDK `.note.ohos.ident`、static PIE（无 `PT_INTERP`，不依赖 `/lib/ld-musl-aarch64.so.1`）。a) 把 consumer.c 编成 PP20，由 ppunpack 还原，还原结果须与原文件逐字节相同——**工具产出就是下一步要编译的源码**；b) 用 profile 的 OHOS clang（`tools.build:compiler_executables`）把还原出的源码编成 AArch64 static PIE，并校验产物带 OHOS note；c) 运行消费者：它在 OHOS musl 上 fork/execv/waitpid 调用 ppunpack 还原 700000 字节 PP20 文件并 `memcmp` 校验，再确认普通文件被拒（exit 10、不产生输出） | 鸿蒙特有 |

统计：上游 1（执行 1/1 通过）→ 适配后 8（上游 1 + 新增功能 6 + **鸿蒙特有 N=1**：用例 7）。

执行方式：AArch64 runner（CI 的鸿蒙设备）原生执行；其他架构经 `qemu-aarch64` 执行，
**缺 qemu 直接失败，不做 skip**。

### 验证结果

```text
conan-verify ppunpack 1.0  → G1/G2/G3/G4 PASS（ohos-aarch64 profile，x86_64 runner）
test_package（runner: /usr/bin/qemu-aarch64）:
  ok   OHOS artefact: ELF64 AArch64, note owners ['OHOS'], static PIE
  ok   U1 upstream make check: ppunpack sf.pp sf -> 140095 bytes, identical to sf.chk
  ok   usage banner (exit 1)
  ok   text: 1320 -> 188 bytes PP20 restored exactly {'lit': 14, 'm2': 13, 'm3': 4, 'm4': 1, 'm5_short': 6, 'm5_long': 0}
  ok   big: 700000 -> 76138 bytes PP20 restored exactly {'lit': 1832, 'm2': 169, 'm3': 12, 'm4': 12, 'm5_short': 10261, 'm5_long': 11636}
  ok   one: 1 -> 14 bytes PP20 restored exactly
  ok   non-PP20 input refused (exit 10)
  ok   missing input refused (exit 10)
  ok   7a consumer.c restored by ppunpack (4040 bytes)
  ok   7b consumer built with /data/service/hnp/bin/clang (OHOS AArch64 static PIE)
  consumer: ppunpack restored 700000 bytes, memcmp identical
  consumer: non-PP20 input refused with exit 10
  ok   7c consumer ran ppunpack via fork/execv and verified the output
  all 8 ppunpack checks passed (upstream 1/1, added 7/7)
```

说明：本地是 x86_64 runner 上 **qemu-aarch64 用户态模拟执行交付产物本身**（static-pie，无需 loader），
不等于在鸿蒙 PC 真机上运行；CI 的 test_package 在鸿蒙设备上原生执行同一组 8 项断言，结果以 CI 为准。

## 注意事项

- 许可：上游 README 原文 "THIS SOURCE-CODE CAN BE USED FOR NON COMMERCIAL PURPOSES ONLY, IN PPDECRUNCH
  OR TRACKER. PLEASE CONTACT Nico Francois ... FOR ANY OTHER USES."（Marc Espie 1995，基于 Nico Francois
  的解包代码）——仅限非商业、且限定用于 ppdecrunch/tracker，其他用途须联系作者。无对应 SPDX 标识，
  声明为 `LicenseRef-ppunpack-noncommercial`，README 原样装入 `licenses/`。作为独立包分发是否符合该条款，
  需主编审核确认。
- 上游既有缺陷（未修改）：`depackedlen()`/`ppdepack()` 不检查输入长度，短于 8 字节的文件在比对签名、
  读取 trailer 与偏移表时会越界读；`fread`/`fwrite` 返回值未检查。仅影响畸形输入，正常 PP20 文件不受影响。
- `ulong` 在 aarch64 LP64 上是 64 位；解包长度来自 24 位字段，行为与 32 位平台一致。
---

**编译结束**: 2026-09-26 06:13
**最终状态**: built
