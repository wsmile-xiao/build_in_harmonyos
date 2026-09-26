# zpaq 7.15 application 包人工补测（G4 / L2 / L4 / L5）

zpaq 是 `package_type = "application"` 的纯可执行包。`conan-verify` 报告
（`conan-verify-report.md`）里 G4 报 `⚠️ 无法找到程序包 ID`，L2/L4/L5 随之报
`⏭️ 跳过（无 cache 路径）`，但工具对这几项**同时**打印 `✅ PASS`。

按本仓既有口径（见 `archives/b/bti/034/reports/conan-verify-supplement.md`）：
**并存时以「跳过」为准**，视为 **SKIPPED（未执行）**，不计入通过。
本文件是对这四项的人工补测逐字记录。

- 补测对象：`conan create archives/z/zpaq/7.15`（profile `ci/conan/profiles/ohos-aarch64`）
  产出的 `bin/zpaq`（`-pr:h` / `-pr:b` 同 profile，`--build=missing`）
- 补测日期：2026-09-25
- 包目录定位：`~/.conan2/p/b/zpaq*/p`（Conan 2 缓存分片目录名不固定，
  **写死目录名下一轮即不可复核**，故以下一律记录绝对路径）

---

## G4 产物完整性 —— SKIPPED → 人工 PASS

`find . -type f | sort`（第 3 轮包目录）：

```
./bin/zpaq
./conaninfo.txt
./conanmanifest.txt
./licenses/COPYING
```

| 判据 | 结果 |
|------|------|
| 产物数量 | 4 项（2 项包内制品 + 2 项 Conan 元数据） |
| 可执行产物 | `bin/zpaq`（唯一） |
| 许可证正文 | `licenses/COPYING` ✅（Unlicense；`libzpaq.cpp` 内嵌 divsufsort 片段为 MIT） |
| `lib/` / `include/` | 不存在 |

与 `conanfile.py` 互证：`package()` 只 `copy` 了 `zpaq` → `bin/` 与
`COPYING` → `licenses/`；`package_info()` 声明
`bindirs=["bin"]`、`includedirs=[]`、`libdirs=[]`、`cpp_info.libs=[]`。
**产物集合与声明一致。**

## L4 安全属性 —— SKIPPED → 人工 PASS（对 `bin/zpaq`）

```
$ llvm-readelf -hW bin/zpaq | grep -E "Class|Type|Machine"
  Class:   ELF64
  Type:    DYN (Shared object file)
  Machine: AArch64

$ llvm-readelf -lW bin/zpaq | grep -E "GNU_STACK|GNU_RELRO"
  GNU_RELRO  0x08e900 … 0x0040a0 0x004700 R  0x1
  GNU_STACK  0x000000 … 0x000000 0x000000 RW 0x0

$ llvm-readelf -dW bin/zpaq | grep -E "NEEDED|FLAGS|RPATH|RUNPATH"
  0x0000000000000001 (NEEDED)  Shared library: [libc.so]
  0x000000000000001e (FLAGS)   BIND_NOW
  0x000000006ffffffb (FLAGS_1) NOW PIE
```

| 判据 | 结果 |
|------|------|
| PIE（`ET_DYN`） | ✅ `Type: DYN (Shared object file)` + `FLAGS_1: NOW PIE` |
| 栈不可执行 | ✅ `GNU_STACK … RW`（无 `E` 位） |
| 重定位只读 | ✅ 存在 `GNU_RELRO` 段 |
| 立即绑定 | ✅ `FLAGS: BIND_NOW`（无 lazy binding） |
| 无意外依赖 | ✅ `DT_NEEDED` 仅 `libc.so`；无 `RPATH` / `RUNPATH` |

`file` 佐证：`ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)`。
`libc++` 已由 `-static-libstdc++` 静态烘焙，因此不存在
`libc++_shared.so`（链接器脚本）的 musl 加载失败问题 —— 这正是本包
`DT_NEEDED` 只有 `libc.so` 的原因。

## L2 消费者实测 —— SKIPPED → 人工 PASS（在**安装出来的制品**上执行）

三组独立证据，全部使用包内 `bin/zpaq`（不是构建目录里的临时产物）：

1. **裸执行**（不给任何 `LD_LIBRARY_PATH` / `conanrun` 帮助）：
   ```
   $ <pkg>/bin/zpaq
   zpaq v7.15 journaling archiver, compiled Sep 25 2026
   Usage: zpaq command archive[.zpaq] files... -options...
   ```
   二进制可被 musl 加载器直接拉起（`DT_NEEDED` 只有 `libc.so`）。
2. **完整消费者契约**（`test_package/test.sh` 直接对包内二进制执行，
   `TMPDIR` 指向可写目录）：
   ```
   [PASS] T1 no-arg invocation prints the zpaq v7.15 banner and usage
   [PASS] T2 add+extract round trip is byte-identical for both payload members
   [PASS] T3 second add() created a second journal version (2 versions)
   [PASS] T4 -until 1 restores the v1 revision byte-exactly
   [PASS] T5 listing accounts for cross-version fragment dedup
   [PASS] T5b second add() re-added only the changed member
   [PASS] T6 missing archive is diagnosed and reported as rc=2
   RESULT: 7/7 checks passed
   ```
3. **独立单文件往返**（另起目录、另一压缩级别，不依赖 test.sh）：
   ```
   $ <pkg>/bin/zpaq add m2.zpaq f.txt -method 2   # rc=0
   $ <pkg>/bin/zpaq x m2.zpaq -to out            # rc=0
   $ cmp f.txt out/f.txt                          # L2C-ROUNDTRIP-OK
   ```

> 本包的 L2 不能用 `bin --version` 判据：zpaq 7.15 没有 `--version` / `--help`
> 开关（未知参数一律打印横幅 + 用法并 `exit 1`）。详见 notes.md 与知识草稿
> `zpaq-7.15-no-version-flag-smoke-gate`。

## L5 产物基线 —— SKIPPED → 人工 PASS（两轮独立清缓存构建）

方法：`conan remove "zpaq/*" -c` 清空本地缓存后重新 `conan create`，
两轮各取完整包目录逐字节比对（第 2 轮结果先快照到工作目录**之外**，
再执行第 3 轮，避免清缓存把对照物一并删除）。

| 产物 | 第 2 轮 | 第 3 轮 | 比对 |
|------|---------|---------|------|
| `bin/zpaq`（sha256） | `6deadaa3cf14dfd3eb78719c778ec6b20a828f1726841d8cbd2353a14303a3a5` | 同左 | ✅ 逐字节一致 |
| `licenses/COPYING`（sha256） | `927b5feda84f7a7f2063998b124829182967f54b954db2c3569e8bd07958bf07` | 同左 | ✅ 逐字节一致 |
| `conaninfo.txt` | — | — | ✅ 逐字节一致 |
| `conanmanifest.txt` | `1790325741`（首行） | `1790325782` | ⚠️ 仅首行**打包时间戳**不同，其余一致 |

补充：第 1 轮构建（在另一包目录）产出的 `bin/zpaq` sha256 同样是
`6deadaa3…03a3a5`，即**三轮构建的二进制完全一致**。

结论：本包满足「可复现子集逐字节一致」的基线判据；唯一差异项
`conanmanifest.txt` 的首行是 Conan 打包时间戳（Unix 秒），跨轮必然漂移，
属已知预期，不构成复现性缺陷。

---

## 附注：工具报告的 G1/G3 中「R26 通过」对本包不适用

`conan-verify-report.md` 的 G1 段有一行
`✅ R26: 系统同名库静态链接配置存在`，G3 段随之写「无系统同名库冲突（R26 通过）」。
本包是 `package_type = "application"`、**零外部依赖**、配方里没有任何静态链接配置
（无 `BUILD_SHARED_LIBS`、无 `cpp_info` 库声明）——该行是工具按配方里的
`-static-libstdc++` 字符串**误命中**。

因此本包「无系统同名库冲突」的真实依据不是 R26，而是：
`package_info()` 的 `libs=[] / includedirs=[] / libdirs=[]`，且 `DT_NEEDED` 仅
`libc.so`（见上文 §L4）。`manifest.yaml` 的 `levels.G1/G3` 已按此加注。

## 小结

| 门禁 | conan-verify 工具结论 | 真实状态 | 证据来源 |
|------|----------------------|----------|----------|
| G0 | PASS | PASS | 构建系统识别（零依赖包，无预查询） |
| G1 | PASS | PASS | 配方结构 12 项 |
| G2 | PASS | PASS | `conan create` 成功（`conan-create.log`） |
| G3 | PASS | PASS | 无 `lib/`，无系统同名库冲突 |
| G4 | `✅ PASS` + `⚠️ 无法找到程序包 ID` | **SKIPPED**（工具未执行）→ 人工 PASS | 本文件 §G4 |
| L2 | `✅ PASS` + `⏭️ 跳过` | **SKIPPED**（工具未执行）→ 人工 PASS | 本文件 §L2 |
| L4 | `✅ PASS` + `⏭️ 跳过` | **SKIPPED**（工具未执行）→ 人工 PASS | 本文件 §L4 |
| L5 | `✅ PASS` + `⏭️ 跳过` | **SKIPPED**（工具未执行）→ 人工 PASS | 本文件 §L5 |

即：`conan-verify` 实际执行并通过的是 **G0-G3**；G4/L2/L4/L5 四项由本文件的人工
补测覆盖，`manifest.yaml` 的 `validation.conan_verify` 已按此口径记录为
`partial`，不把跳过项折算成通过。
