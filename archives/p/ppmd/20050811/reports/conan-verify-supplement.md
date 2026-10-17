# conan-verify 人工补测报告 — ppmd 20050811（application 包）

`package_type="application"`（纯可执行包，无 lib/）：conan-verify 的门禁本轮全部
**实跑**（G4/L2/L4/L5 = 4/4，跳过 = 0/4，Verdict PASS，见
`conan-verify-report.md`）。本补测按 application 包口径补齐产物级实证，
并记录 L4 一处门禁解析误报的 readelf 反证。

数据来源：干净采信轮（2026-09-21T17:15，清缓存四步 + DB 两表为空后
`conan create`），安装树
`/storage/Users/currentUser/.conan2/p/b/ppmde7fd27d158892/p`
（来源：conan-create.log `Package folder` 行）。

## 1. G4 产物清单 ↔ package_info()

| package_info() 声明 | 安装树实物 |
|---|---|
| `bindirs=["bin"]`、`libs=[]` | `bin/ppmd`（55744 B，唯一产物）；无 lib/、无 include/ ✓ |

## 2. L2 平台真实运行（消费者实证）

- conan-create.log:169 `RUN: bash .../test_package/test.sh`（conanrun 环境，
  `ppmd` 即安装树 bin/ppmd）。
- conan-create.log:194 **`TOTAL: 23  PASS: 23  FAIL: 0`** —— 23 项断言全 PASS：
  `--version/-h` 退出 0、无参用法错误 255、文本（含开关矩阵 -o16/-o2/-r1/-r2）
  与二进制文件通往返逐字节一致、档案头 canonical 布局（magic `8f af ac 84`
  小端 + 偏移 16 原文件名 + 体积收缩）、非静默 bpb 统计行、`-f`/`-d`/通配符、
  损坏/截断档案优雅拒绝（非零退出、无 SIGSEGV）。
- L2 门禁自身探针：`ppmd --version → Fast PPMII compressor for textual data,
  variant I, Sep 21 2026`（rc=0）✓。

## 3. L4 静态安全实证（llvm-readelf，`/data/service/hnp/bin/llvm-readelf`）

| 项 | 门禁输出 | readelf 实证 |
|---|---|---|
| 文件类型/架构 | — | `Type: DYN`（PIE）、`Machine: AArch64` ✓ |
| PIE | PIE=enabled ✓ | `FLAGS_1: NOW PIE` ✓ |
| RELRO | RELRO=full ✓ | `FLAGS: BIND_NOW`（+ GNU_RELRO 段）✓ |
| NX | ⚠️ NX=disabled | **`GNU_STACK ... RW`（无 E 位）→ NX 已启用，门禁解析误报**（GNU_STACK 行下一行是 NOTE 段，误读其标志列，同 planarity 家族形态） |
| STACK_CANARY | not found | 编译未启用 `-fstack-protector`（OHOS 默认），非产物缺陷 |

结论：L4 的 1 条"安全警告"为 NX 项解析误报，readelf 逐字段反证如上；
PIE/RELRO/NX 三项真实状态全部达标。

## 4. L5 产物基线（两条稳定聚合 sha256）

```
76fcdea0012d087a24521a13159b23032f202175cb0d0557d0498c50c2ef45f0  bin/ppmd
c66990c720bee078fee1c04dbc7035293b34b3cad9cf507aba8d9b44a9468a3d  conanmanifest.txt
```

交叉验证：`bin/ppmd` 的 sha256 与纯净源码树 + 6 补丁链（`patch -p1` 逐个
apply）+ `make CXX=clang++ CXXFLAGS="-O2" -j1` 的本地构建**逐字节一致**
（确定性构建，无路径/时间戳渗入）。

## 5. 取数命令（可复现）

```sh
PKG_CACHE="$HOME/.conan2/p/b/ppmde7fd27d158892/p"
ls -l "$PKG_CACHE/bin"
/data/service/hnp/bin/llvm-readelf -h "$PKG_CACHE/bin/ppmd" | grep -E "Type|Machine"
/data/service/hnp/bin/llvm-readelf -lW "$PKG_CACHE/bin/ppmd" | grep -E "GNU_STACK|INTERP"
/data/service/hnp/bin/llvm-readelf -dW "$PKG_CACHE/bin/ppmd" | head -8
shasum -a 256 "$PKG_CACHE/bin/ppmd" "$PKG_CACHE/conanmanifest.txt"
grep -n "RUN:\|Apply patch\|TOTAL:" archives/p/ppmd/20050811/reports/conan-create.log
```
