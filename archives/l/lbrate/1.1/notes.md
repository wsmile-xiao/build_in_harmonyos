# lbrate 1.1 适配笔记

## 编译环境
- 构建系统: makefile（上游手写 Makefile，无 configure）
- 编译日期: 2026-09-25
- 编译器: OHOS clang 15（`aarch64-unknown-linux-ohos-clang`，profile `tools.build:compiler_executables`）
- 目标: aarch64-linux-ohos（`ci/conan/profiles/ohos-aarch64`）
- 构建机: x86_64 runner（交叉编译；`qemu-aarch64` 用户态）
- 状态: built（conan-verify G1-G4 PASS）

## 源码
- URL: https://ibiblio.org/pub/Linux/utils/compress/lbrate-1.1.tar.gz（ibiblio/Sunsite Linux 存档，作者发布站点）
- sha256（发布字节，curl 所得）: `ec73e07fa6c38752e0665fe00105b3c6c84bbac06654bb192651bf29a8577dd9`
- 解码后裸 tar 的 sha256（conan requests 下载器所得，**不登记**）: `66f8e87c9245f275b6e47e85bb7235deb1e0fe2c022fc084ad9853ae7e87ddb5`
- 内容: 18 个文件——`main.c` `readrle.c` `readhuff.c` `readlzw.c` `readlzh.c`（共 2099 行 C）+ 4 个头文件、Makefile、mkinstalldirs、`lbrate.1`、README/NEWS/TODO/ChangeLog/COPYING、`lzhuf-post.txt`

## 编译步骤

```bash
# 手工打通（构建副本 /root/tmp/builds/lbrate-1.1.work）
make CC=/data/service/hnp/bin/clang          # CFLAGS 沿用上游 -O2 -Wall
file lbrate   # ELF 64-bit LSB pie executable, ARM aarch64, interpreter /lib/ld-musl-aarch64.so.1

# 配方（conanfile.py build()）
make -j1 lbrate CC=<tools.build:compiler_executables.c>
# package(): bin/lbrate、share/man/man1/lbrate.1、licenses/COPYING（copy，不走上游 make install）
```

五个源文件在 OHOS clang 15 `-O2 -Wall` 下**零 warning、零 error**。任务书预判的三个雷点逐一核对：

| 预判风险 | 实测 | 处置 |
|---|---|---|
| `getopt.h`/POSIX 头兼容 | `main.c` 用 `<getopt.h>` 的 `getopt/optind/opterr/optopt`、`<utime.h>` 的 `utime()`、`gmtime/mktime`；OHOS musl 全部提供 | 无需改动；R2（未知选项 → optopt）与 OHOS-2（utime/mktime）用例实测覆盖 |
| Makefile 写死 `CC=gcc` `CFLAGS=-O2 -Wall` | 确认写死 | make 命令行变量优先于 makefile 赋值 → `make CC=<profile 编译器>`，**无需补丁**（R33：编译器取自 conf，不读 shell 变量） |
| 现代 Clang 揪出旧式 C warning | `-Wall` 下 0 条 | 无需处理 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-verify G1: `conanfile.py 缺少: export_sources() 方法 / 补丁应用调用` | G1 固定要求 export_sources + apply_conandata_patches，无补丁也不例外 | 补 `export_conandata_patches` / `apply_conandata_patches`（无补丁时为 no-op） |
| 2 | conan-verify G2: `sha256 hash failed for 'lbrate-1.1.tar.gz'`（Provided ec73e07f…, Computed 66f8e87c…） | ibiblio 按 Accept-Encoding 协商 Content-Encoding：curl/urllib → `x-gzip`，requests（conan）→ `gzip`；requests 透明解码落裸 tar，且 conan 对 `gzip` 豁免尺寸校验，于是不报 Transfer interrupted 而在 sha256 处失败。知识引擎命中 E299（分层诊断），同课题已有 `DRAFT-conan-downloader-xgzip-content-encoding`（x-gzip→传输中断症状）与 `E561-draft-4FE2`（诊断框架） | conandata 登记**发布字节** hash（= CI `build_and_test.sh` 预下载 curl 落盘并改写 file:// 的字节层）；`source()` 先 `get()`，失败回退 `urllib.request.urlopen`（不发送/不解码 Accept-Encoding）+ `check_sha256` + `unzip`。沉淀新草稿 `knowledge/drafts/E562-draft-BF48` |
| 3 | 本机无法执行交付的动态 OHOS 二进制 | x86 runner 缺 `/lib/ld-musl-aarch64.so.1`，qemu binfmt-P 下报 `Could not open '/lib/ld-musl-aarch64.so.1'` | test_package：非 aarch64 主机上运行期用例如实报 SKIP（不计通过），aarch64 主机探测失败即硬失败；本地功能验证改用**同源 .o 静态重链副本**在 qemu 下实跑（见下） |
| 4 | prescan critical `PSCAN-HMDFS-001`（Makefile:45 `ln -s`） | 仅在 `tgz` 分发目标里，构建只跑 `make lbrate` 不触发 | 误报，无需处理 |

## 源码修改

无补丁（`patches/` 为空，conandata 无 `patches` 键）。

## 依赖版本

无第三方依赖（只用 libc）。W0：`requires` 为空；制品仓 search API `lbrate/*` 返回 `{"results":[]}`，无同版本冲突。

## 上游测试清点（R51）

| 项 | 结果 | 证据 |
|---|---|---|
| tests/ 目录数 | 0 | tarball 18 个文件，无子目录 |
| 测试数据 | 0 | 无 `.lbr` / `.?q?` / `.?z?` / `.?y?` 样本 |
| make check/test 目标 | 0 | Makefile 目标仅 all/installdirs/install/uninstall/clean/tgz |
| ctest/pytest 注册数 | 0 | 无 CMake/Python |

上游 N = 0，N′ = 0（确认的 0，不是 UNKNOWN）。由 test_package 补真实功能测试。

## 验证结果

### test_package（`test_package/test_lbrate.py`，12 项）

脚本现场构造规范 LBR 归档：目录扇区 + stored 成员 `HELLO.TXT`（CRC-16/XMODEM，创建/修改日期）+
squeezed 成员 `SQUEEZE.TQT`（内嵌原名 `SQUEEZE.TXT`；编码器是 readhuff.c/readrle.c 的逆过程：
0x90 RLE + Huffman，LSB-first 位流，EOF=256）。

| ID | 用例 | 类别 |
|---|---|---|
| OHOS-1 | 交付二进制 ELF 契约：EM_AARCH64 + ET_DYN(PIE) + PT_INTERP=`/lib/ld-musl-aarch64.so.1` | **鸿蒙特有** |
| R1 | `-h` 输出 `lbrate 1.1` 横幅，rc=0 | 功能 |
| R2 | `-z` 未知选项 → `option `z' not recognised`，rc=1（getopt/optopt） | 功能 |
| R3 | `-l` 列出两成员、大小 128、日期 `2001-06-15 12:34` / `2000-02-29 08:00` | 功能 |
| R4 | 通配符 `sq*` 仅选中 squeezed 成员 | 功能 |
| R5 | `-t` 两成员 CRC 通过 | 功能 |
| R6 | 损坏归档 `-t` → `bad CRC`，rc=1 | 负向 |
| R7 | stored 成员逐字节一致（128 字节记录，^Z 填充） | 功能 |
| R8 | squeezed 成员 Huffman+RLE 解码并改名为 `squeeze.txt`，内容逐字节一致 | 功能 |
| OHOS-2a | TZ=UTC0 下 utime() 还原修改日期：mtime 精确等于期望 epoch（含闰日） | **鸿蒙特有** |
| OHOS-2b | `-c` 还原创建日期：mtime 精确等于期望 epoch | **鸿蒙特有** |
| R9 | `-n` 原样导出压缩成员 `squeeze.tqt`，字节一致 | 功能 |

鸿蒙特有测试 N = 2（OHOS-1 交付物 ELF/加载器契约；OHOS-2 OHOS musl `mktime`/TZ 语义 + 文件系统 `utime()` 时间戳还原，2a/2b 两断言）。

### 实测结果（如实区分三种执行形态）

1. **conan-verify G2 / finish W3（交付产物，x86 runner）**：OHOS-1 **PASS**；其余 11 项 **SKIP**
   （`host x86_64 cannot execute the aarch64 OHOS binary (probe: 255)`）。skip 不计为通过。
2. **同源 .o 静态重链副本，qemu-aarch64 实跑**：11/11 运行期用例 **PASS**
   ```bash
   cd /root/tmp/builds/lbrate-1.1.work && make CC=/data/service/hnp/bin/clang
   /data/service/hnp/bin/clang -O2 -Wall -static -o /root/tmp/lbrate-static main.o readrle.o readhuff.o readlzw.o readlzh.o
   python3 test_package/test_lbrate.py --bin /root/tmp/lbrate-static --workdir /root/tmp/lbrate-qemu-run --runtime-only
   # → lbrate test_package: passed=11 failed=0 skipped=0
   ```
   注意：这**不等于交付产物已实跑**——静态副本与交付物同源同编译参数，但链接方式不同（静态 musl
   vs 动态 `/lib/ld-musl-aarch64.so.1`），且运行在 x86 主机文件系统上，不是 OHOS 文件系统。
3. **CI（aarch64 OHOS 设备）**：交付的动态二进制在此首次实跑全部 12 项；aarch64 上探测失败为硬失败，不会 skip。

### 门禁
- conan-verify: G1/G2/G3/G4 PASS（L2/L4/L5 已执行）；G2 无预下载，日志出现
  `retrying with urllib to keep the published bytes` 后 source() 通过（urllib 回退路径实证）
- finish W3（`ci/conan/build_and_test.sh`）: exit_code=0；L0/KC/JC/L1a/L1b/L1e/L5 均 `[ok]`。
  W3 走了 CI 预下载：`[ok] lbrate-1.1.tar.gz (29KB) via mirror 1` → file://，落盘文件
  sha256 = `ec73e07f…`（= conandata 登记值），`get()` 直接通过、未触发回退（预下载路径实证）
- lang-preflight: `c`（make，源文件 5 个，主体 100%）

## 注意事项
- `source()` 的 urllib 回退只在 `get()` 失败时触发；CI 预下载成功时 file:// 字节即发布字节，直接通过。
- 上游 `read_file_header()` 首项把合成的 16 位值 `ungetc()` 回流（实际压回 0x00 而非第二字节），
  由于随后只检查"首项名为空"而恰好无害；属上游既有行为，未改动。
- 仓库存量：bsdgames-nonfree 2.17 / fortune 9708 / mp3info 0.8.5a 同为 ibiblio 源，登记的是解码后 hash，
  与 CI 预下载字节层相反，已写入 E562 草稿请主编复核（本 PR 不改他人归档）。
---

**编译结束**: 2026-09-25 13:29
**最终状态**: built
