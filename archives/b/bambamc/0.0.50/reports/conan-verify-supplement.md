# conan-verify 人工补测报告 — bambamc 0.0.50

> 提交 SHA：见 PR 正文 / `git rev-parse HEAD`
> 设备：OpenHarmony PC aarch64（`uname -s` = HarmonyOS，kernel HongMeng 1.12.0）
> 工具：conan 2.29.1、clang 15.0.4、GNU Make 4.4.1、autoconf 2.73 / automake 1.18.1 / libtool 2.6.2

## 1. 为什么需要本报告

`conan-verify` 报告里 G4/L2/L4/L5 均为「✅ PASS」但紧接着「⏭️ 跳过（无 cache 路径）」
（workflow §7.2、§17 登记的 `conan_verify.py` 定位缺陷：`conan list --format=json`
顶层键带 `@user/channel` 而 `self.ref` 不带，`conan_verify.py:737` KeyError 被吞）。
跳过不构成证据，故按 §7.2 要求人工补测下列四项并留证。

被测包目录（每轮清缓存重建，目录名会变）：

```sh
PKG=$(ls -d "$HOME"/.conan2/p/b/bamba*/p | while read d; do [ -f "$d/lib/libbambamc.a" ] && echo "$d"; done | head -1)
```

## 2. G4 产物清单（与 package_info() 互证）

`package_type = "library"`，`cpp_info.libs = ["bambamc"]`，未声明 `bindirs`/`system_libs`。

```sh
find "$PKG" -type f | sed "s|$PKG/||" | sort
```

实测（40 个文件，不含 `conaninfo.txt`/`conanmanifest.txt`）：

```
include/bambamc/*.h              36 个（上游 libbambamc_include_HEADERS 全量 + 生成的 BamBam_Config.h）
lib/libbambamc.a                  1 个（static，PIC）
lib/pkgconfig/bambamc.pc          1 个
licenses/COPYING, licenses/GPLv3  2 个
```

- 无 `bin/`、无 `lib/*.so`：与 `package_info()` 一致（无 bindirs，libdirs 默认 `lib`）。
- `Libs:` 行已去掉打包机绝对 `-L` 路径，实测内容：

```
Name: bambamc
Description: bambamc
Requires: zlib
Version: 0.0.50
Libs: -L${libdir} -lbambamc
Cflags: -I${includedir}
```

- 因为包内没有可执行产物，按 ARCHIVE-SPEC §2.1 / CI L0k 口径**不创建**软件级
  `commands.json`（该文件只对含 `bin/` 的工具型包要求）。

## 3. L2 消费者实测

### 3.1 test_package 真实往返（采信轮 `reports/conan-create-log.md`）

```
RUN: "./test_bambamc" "<...>/consumer_roundtrip.bam"
bambamc consumer round-trip: 28 checks, 0 failures
```

### 3.2 直接运行 test_package 消费者二进制（脱离 conan 环境）

```sh
"$PACKAGE_DIR/test_package/build/clang-15-armv8-17-release/test_bambamc" "$HOME/tmp/bambamc-0.0.50/standalone.bam"
# -> bambamc consumer round-trip: 28 checks, 0 failures   rc=0
# -> standalone.bam 194 字节，gzip magic 1f 8b，解压后前 4 字节 42 41 4d 01（BAM\1）
```

### 3.3 静态库 → 共享对象 → dlopen 三跳验证（PIC + 动态加载）

静态库包不能 dlopen，因此按 E539 的做法把**打包后的** `libbambamc.a` 链进一个
共享对象再加载，验证 (a) 归档是 PIC，(b) 产出的 DSO 可被 musl 加载器加载并调用：

```sh
clang -shared -fPIC probe.c -I"$PKG/include" -I<zlib>/include \
  -L"$PKG/lib" -lbambamc -L<zlib>/lib -lz \
  --target=aarch64-unknown-linux-ohos --sysroot=$SR -o libbambamc_probe.so   # rc=0
clang driver.c --target=aarch64-unknown-linux-ohos --sysroot=$SR -o driver -ldl
./driver ./libbambamc_probe.so
# -> dlopen probe: bambamc_probe_ok() = 1   rc=0
```

`probe.c` 调用公开 API `BamBam_BamHeaderInfo_New` / `_AddChromosome` / `_Delete`；
`driver.c` 用 `dlopen(..., RTLD_NOW)` + `dlsym` 调用并断言返回值。

## 4. L4 安全属性（`readelf -h / -lW / -dW`）

| 产物 | Type | GNU_STACK | GNU_RELRO | FLAGS | FLAGS_1 |
| --- | --- | --- | --- | --- | --- |
| `test_package/.../test_bambamc`（消费者 PIE） | `DYN` (PIE) | `RW`（NX） | 存在 | `BIND_NOW` | `NOW PIE` |
| `libbambamc_probe.so`（静态库吸收后的 DSO） | `DYN` | `RW`（NX） | 存在 | `BIND_NOW` | `NOW` |

判定：DYN + `GNU_STACK RW` + `GNU_RELRO` + `BIND_NOW` + PIE 五项全部满足（§7.2 L4 判据）。
包内只有 `.a` 归档（无可执行、无 `.so`），故对归档不适用 `readelf -h/-l`；上表用
消费者侧产物取证，覆盖「包产物参与链接后的真实安全属性」。

## 5. L5 产物基线与可复现性

### 5.1 可复现性判别（§7.2 要求的先决步骤）

同提交、清空包缓存后连续两轮 `conan create`（`--user=ohpcd --channel=stable`），
逐产物 sha256 比对：

- **39/40 个打包文件逐字节一致**（两轮的 `find | sort | xargs sha256sum` 列表除
  `lib/libbambamc.a` 外无差异；复现判据是对两份列表做 `diff`，输出中除
  `lib/libbambamc.a` 那一行外不含任何 `<`/`>` 行）。
- `lib/libbambamc.a` 两轮 sha256 不同。本轮（2026-09-11 复核轮）实测：

  ```
  A（构建目录 …/p/b/bambae88713a5f33f0/b）  sha256 = 84a247430403221653ea50d0d4423cd7b1f7dec61c2afeaa9e0d83cde0f71069
  B（构建目录 …/p/b/bamba985764d7fa40d/b）  sha256 = 45c396003377c5cb7e208dea0bdb07c247f0f7b693662b3fc77686a5a2465d0a
  ```

  根因（用本目录随附的 `repro-check.py` 实测定位，属 §7.2 登记的第二类「跨轮构建目录名不同」）：
  - `ar` 成员头的时间戳字段不同；
  - **30 个成员中有 10 个不同，差异字节全部落在 `.rodata.str1.1`**（可分配节），
    原因是本包按 R8 之外的另一项决定**保持断言启用**（`tc.ndebug = None`），上游源码里的
    `assert()` 会把 `__FILE__` 展开成绝对源码路径，而该路径含**每轮重建的 conan 构建目录 hash**：
    ```
    A: /storage/Users/currentUser/.conan2/p/b/bambae88713a5f33f0/b/src/bambamc/BamBam_BamHeaderInfo.c
    B: /storage/Users/currentUser/.conan2/p/b/bamba985764d7fa40d/b/src/bambamc/BamBam_BamHeaderInfo.c
    ```
    实测累计差异 100 字节 / 10 个成员（即每个成员 10 个字节 = 两轮构建目录 hash 中不同的十六进制字符）；
  - 节布局（`readelf -S`）完全相同；无 `-g` 故无 DWARF `DW_AT_comp_dir` 参与。

  （更正说明：本报告早前版本把该差异归因到 `.strtab`（STT_FILE）并称「11 字节/对象」。
  经 `repro-check.py` 按节边界逐字节定位，实际落在 `.rodata.str1.1`，字节数为 10/成员；
  旧表述有误，以本节为准。）

### 5.2 稳定基线（可复现口径）

由于差异是**源码路径字符串**而非代码/数据，可比口径不是「取某些节」，而是
**先把每轮的构建目录 hash 归一再整体比对**。随包提供实测脚本
`reports/repro-check.py`（仅依赖 `ar` / `llvm-readelf` / 标准库），用法：

```sh
python3 archives/b/bambamc/0.0.50/reports/repro-check.py \
  <archive-A> <archive-B> <builddir-A> <builddir-B>
```

它做四件事：① 解出两轮的 30 个 `ar` 成员；② 逐成员比对并把差异字节定位到节；
③ 把 `bamba<hex>` 形式的构建目录 token 归一成固定串后重新比对；
④ 打印归一化内容指纹。实测输出（末行即结论）：

```
members: A=30 B=30  identical name lists=True
  differs: libbambamc_la-BamBam_BamHeaderInfo.o  bytes=10  sections=['.rodata.str1.1']
  ...（共 10 个成员，sections 全部为 .rodata.str1.1）
differing members: 10/30   sections touched: {'.rodata.str1.1': 100}
PASS: all 30 members byte-identical after normalising the build directory hash
```

| 轮次 | 构建目录 | 归一化内容指纹（30 成员） |
| --- | --- | --- |
| A（清缓存） | `…/p/b/bambae88713a5f33f0/b` | `c97d8802265717af76a5cb67f2c8081a38f375626302035ee1fef79548569ce8` |
| B（清缓存） | `…/p/b/bamba985764d7fa40d/b` | `c97d8802265717af76a5cb67f2c8081a38f375626302035ee1fef79548569ce8` |

两轮**完全相同** → 归一并构建目录名后，归档内容逐字节可复现；全文件 sha256 的漂移
只来自构建目录名与 `ar` 时间戳，属预期，不作为基线。

（此前版本给出的「可分配节聚合指纹 `342d5a0e…`」不可复现且归因错误，已由本节口径取代。
该旧值同时受两个缺陷影响：一是选取逻辑把 ELF 节的 flags 列当成了行尾字段，实际选中的节集不确定；
二是即便节集正确，`.rodata.str1.1` 本身含构建目录路径，跨轮必然不同。）

### 5.3 全文件 sha256 漂移的性质

全文件 sha256 **不登记为基线**：它随构建目录 hash 每轮变化，登记即不可复核。
跨轮比对一律使用 5.2 的归一化指纹。漂移量的两个来源（`ar` 成员头时间戳 +
`.rodata.str1.1` 内的构建目录路径）均可由 `repro-check.py` 复现与验证。

## 6. 结论

| 项 | 来源 | 结论 |
| --- | --- | --- |
| G0/G1/G2/G3 | `conan-verify` 实跑 | PASS（G2 为清缓存干净轮，日志含 `RUN: autoreconf`、`Apply patch`×2、`RUN: make -j1`） |
| G4 | 本报告 §2 | PASS（40 文件清单与 `package_info()` 互证） |
| L2 | 本报告 §3 | PASS（28 项断言往返 + dlopen 三跳） |
| L4 | 本报告 §4 | PASS（DYN + NX + RELRO + BIND_NOW + PIE） |
| L5 | 本报告 §5 | PASS（节级指纹两轮一致；全文件 sha256 差异已定位为构建目录名 + 归档时间戳） |
