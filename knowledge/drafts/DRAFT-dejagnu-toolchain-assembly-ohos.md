# DRAFT-dejagnu-toolchain-assembly-ohos — OHOS 上装配 DejaGNU 上游测试套件的完整清单

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-11
> **Severity**: 🟡 medium | **Category**: testing / dejagnu / tcl / expect / toolchain

## 相关既有条目（同族差异化定位）

本条目与 **E272**（arm-none-eabi-binutils DejaGNU 交叉工具链测试迁移）同族，但覆盖
面不同，**非重复条目**：

| 维度 | E272（已收录）| 本条目（增量）|
|------|--------------|--------------|
| expect spawn 噪音 | ✅ `-nottyinit` 包装 | 引用（步骤 7）|
| libc `tmpfile()` EACCES | ✅ LD_PRELOAD shim | 不涉及 |
| **tcl/expect 版本链** | ❌ 未覆盖 | ✅ `TCL_LIBRARY` 必须等于 expect 编译版本 |
| **GNU readelf vs eu-readelf** | ❌ 未覆盖 | ✅ 套件用 `-wi` 简写，eu-readelf 不支持 |
| **被测工具源码硬编码 /tmp** | ❌ 未覆盖 | ✅ 环境变量无效，需改源码或 shim |
| **config.guess HarmonyOS** | 间接 | ✅ 引用 E007 并给出插入位置 |
| **TEST_EXECS 补全** | ❌ 未覆盖 | ✅ 从 FAIL/UNSUPPORTED 反推缺哪些输入目标 |
| **整体装配顺序** | 局部 | ✅ 按依赖顺序的完整 checklist |

另与 **E354**（Redis Tcl 套件）同族：E354 强调二进制需先签名 + 经 sh 调用 launcher，
本条目将其作为可选步骤纳入。

> 查证（2026-09-11）：`tclsh8.6`、`TCL_LIBRARY` 命中 E272/E280/E354；`expect 5.45.4`
> 仅 E272；`-wi` / `eu-readelf` / `TEST_EXECS` 命中 **0 条**——版本链、readelf 替换、
> 输入补全三面为空白。

## Scope（何时用）

在 OHOS 上运行 **DejaGNU（runtest）驱动的上游测试套件**时使用。典型报错：

```
ERROR: unable to find expect in the PATH
Tcl_Init failed: Can't find a usable init.tcl
version conflict for package "Tcl": have 8.6.14, need exactly 8.6.16
ERROR: Running config.guess produced bogus build triplet
Unknown DWARF debug section `i'          # eu-readelf 不支持 readelf -wi
runtest: inaccessible or not found      # make 规则里调裸名 runtest
```

## 装配清单（按依赖顺序，每步可单独验证）

### 1. runtest + expect
装 `dejagnu` 与 `expect`；`expect -v` 应输出 `expect version 5.45.4`。
`runtest` 报 `unable to find expect in the PATH` 即此步未完成。

### 2. tcl 版本对齐（**最易踩**）
expect 是**编译期绑定 tcl 版本**的扩展，其 `init.tcl` 会执行
`package require -exact Tcl <编译版本>`。因此：

```sh
# 定位 expect 运行时实际需要的 tcl 版本（看报错里的 "have X, need exactly Y"）
# 然后 TCL_LIBRARY 指向【等于 Y】的那个 tcl 包的 lib/tcl8.6
export TCL_LIBRARY=<tcl-8.6.14>/lib/tcl8.6
```

⚠️ **不是版本越新越好**。实证：ohpcd 同时有 tcl 8.6.14 与 8.6.16，expect/5.45.4
编译自 **8.6.14**，指向 8.6.16 会报 `have 8.6.14, need exactly 8.6.16` 反向冲突。

### 3. GNU readelf 替换 eu-readelf
套件脚本大量使用 **GNU readelf 专有简写 `-wi`**（= `--debug-dump=info`）；
elfutils 的 eu-readelf 会报 `Unknown DWARF debug section 'i'`。
把 PATH 中的裸名 `readelf` 指向 binutils 的 GNU readelf。

### 4. config.guess OHOS 识别（E007 应用）
OHOS `uname -s` 返回 **HarmonyOS**（非 Linux），旧版 config.guess 匹配不到任何分支，
且会在 HMDFS 写 dummy.c 失败。插入位置：**uname 初判之后、Linux 编译检测之前**
（必须在 `set_cc_for_build` 写 dummy.c 前 exit）：

```sh
case $UNAME_MACHINE:$UNAME_SYSTEM in
    aarch64:*|aarch64_be:*)
	echo ${UNAME_MACHINE}-unknown-linux-ohos
	exit ;;
esac
```

### 5. 被测工具源码硬编码 /tmp
⚠️ **仅 export TMPDIR 无效**（E002 只对"遵守 TMPDIR 的脚本"有效）。若工具 C 源码
硬编码 `"/tmp/"`（如 dwz 的 `make_temp_file()`），必须改源码：

```c
const char *tmpdir = getenv ("TMPDIR");
if (tmpdir == NULL || tmpdir[0] == '\0') tmpdir = "/tmp/";
```

或注入 LD_PRELOAD shim（运行库变体见 DRAFT-ohos-otmpfile-tmpdir-shim）。

### 6. TEST_EXECS 补全
先跑一次 runtest，**从 FAIL/UNSUPPORTED 列表反推**缺哪些测试输入目标，逐个
`make <target>`。注意：
- 有些目标由 `runtest lib/*.exp` 生成 → 需 `runtest` 在 PATH（否则 `Error 127`）；
- C++ 目标要传 `CXX=`，仅 `CC=` 不够；
- `make` 的 staleness 判断可能不触发重建，先 `rm -f` 再核对时间戳。

### 7. spawn 噪音消除（E272）
用 `DEJAGNU=<global.exp>` 加载 site 配置，包装 `spawn` 注入 `-nottyinit`。

### 8.（可选）二进制签名
若目标二进制被拒执行，按 E354 先 `binary-sign-tool sign`。

## 环境装配（一次性）

```sh
export PATH=<dejagnu>/bin:<expect>/bin:<tcl8.6>/bin:<gcc>/bin:$PATH
export TCL_LIBRARY=<tcl8.6>/lib/tcl8.6        # 与 expect 同版本！
export LD_LIBRARY_PATH=<elfutils>/lib:<zstd>/lib:<fts>/lib:<obstack>/lib:$LD_LIBRARY_PATH
export DEJAGNU=<abs>/dejagnu-global.exp        # 加载 site-stty-fix.exp
export TMPDIR=<writable-dir>
cd <builddir> && runtest --tool=<tool> -srcdir <src>/testsuite/
```

先跑单用例（`version.exp`）确认环境通了，再全量。

## 备选（fallback）

`environment-limit-inventory`：确实不可解的项逐条如实声明，**不伪造通过率、不整体
填 N/A**，其余用例继续全量执行。已知结构上不可通过的族：

| 族 | 根因 | 复现 |
|----|------|------|
| hardlink 类 | OHOS HMDFS 不支持硬链接 | `touch a && ln a b` → `Operation not permitted` |
| 压缩类 | OHOS objcopy 无 `LLVM_ENABLE_ZLIB` | `objcopy: error: LLVM was not compiled with LLVM_ENABLE_ZLIB` |

## 禁止

- ❌ **只 export TMPDIR 就认为解决 /tmp 失败**：源码硬编码时环境变量无效。
- ❌ **TCL_LIBRARY 指向最高版本 tcl**：必须等于 expect 编译版本。
- ❌ **readelf 指向 eu-readelf**：套件用 GNU 专有 `-wi`，会造成大面积假失败。

## 实证

- **dwz/0.16（PR #9459）**：DejaGNU 上游 testsuite 通过率 **0/62 → 48/62**。
  剩余 6 个失败中 3 个是 HMDFS 硬链接、1 个是 objcopy 无 ZLIB、2 个是 dwz-for-test
  自身行为差异——均环境硬限制。
- 配套：DWARF5 索引节降级见
  DRAFT-dwarf5-index-sections-toolchain-unsupported。
