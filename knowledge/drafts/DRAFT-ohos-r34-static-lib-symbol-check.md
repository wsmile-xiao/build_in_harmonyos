# DRAFT-ohos-r34-static-lib-symbol-check — test_package R34 校验静态库依赖时改验静态链接符号

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-02
> **Severity**: 🟡 medium | **Category**: test_package / R34 / static-library / ELF

## 相关既有条目（同族差异化定位）

本 skill 与既有"链接/共享库"类条目共享 ELF/链接背景，但拦截面是 **R34 test_package
校验口径**（静态库依赖如何验证已链接），与既有条目（都是编译/运行时报错）非重复；
申报路径 B 时以此差异化定位为准。

| 既有条目 | 收录状态 | 同族点 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **E028**（shared library conflict） | 正式收录 | 共享库冲突 | 非本题——那是运行时冲突；本条目是 test_package 校验口径 |
| **E073**（.so symlink/cannot load） | 正式收录 | 共享库加载 | 非本题——加载期；本条目是静态库依赖的**校验**方式 |
| **E139**（GMP shared/static） | 正式收录 | 静态/共享选择 | 同族"静态 vs 动态"背景，但解决的是库选择；本条目解决**验证**时"DT_NEEDED 无静态库名"的坑 |
| **asterisk-pgsql（PR #7331）** | main 已收录配方 | 同 asterisk 变体，R34 校验 cdr_pgsql.so 引用 `libpq`（动态库） | 本条目新增 **静态库依赖的 R34 校验口径**（pgsql 用动态 libpq，DT_NEEDED 有库名，没踩此坑） |

> index.tsv 查证（2026-09-02）：`DT_NEEDED` 命中 0 条、`静态库符号` 命中 0 条、
> `libsybdb` 命中 0 条——无正面撞车；`E139` 仅同族静态/动态背景。

## Scope（何时用）

在写/改 test_package R34 校验时，若目标 package 的依赖是**静态库**（conan 包
`shared=False`，或只有 `.a`，如 freetds/1.4.23 的 `libsybdb.a`）：

- 依赖是动态库时：`DT_NEEDED`（readelf -d）里有 `libpq.so` 等库名，按库名校验即可；
- 依赖是静态库时：静态库被**并入 .so**，`DT_NEEDED` 里只有 `libc.so` 等系统库——
  按"库名"校验必然 FAIL，即使模块确实已链接该依赖。

典型实例：asterisk-tds（cdr_tds.so/cel_tds.so 静态链接 FreeTDS）。

## Symptom

```text
# 首次校验（照抄 pgsql 的"检查 libpq 字符串"方式，只把字符串换成 libsybdb）
FAIL: cdr_tds.so does not reference libsybdb

# 实际模块已链接 FreeTDS——
# llvm-readelf -d cdr_tds.so → NEEDED 只有 libc.so
# llvm-readelf -Ws cdr_tds.so → 有 dbinit / tdsdbopen（FreeTDS 符号已并入）
```

## Root Cause

1. `test_package` R34 常用"扫 `.so` 字节找 DT_NEEDED 库名"来证明依赖已链接——
   这只适用于**动态**依赖（动态库以 `NEEDED` 记录在 ELF 动态段）；
2. 静态库（`.a`）在链接期被 `ld` 抽取对象**并入**目标 `.so`，动态段只保留
   尚未解析的系统动态库（libc 等）——依赖库名不会出现在 `DT_NEEDED`；
3. 因此按"库名"校验静态库依赖必然 FAIL；正确证据是**静态库导出的符号**
   （如 FreeTDS 的 `dbinit`/`tdsdbopen`）出现在 `.dynstr`/`.strtab` 中。

## Recommended Solution

**主方案：R34 校验按依赖类型分口径。**

- 动态库依赖：检查 `DT_NEEDED` 库名（扫 `.so` 字节中的 `libxxx.so` 字符串，
  或本地用 `llvm-readelf -d`）；
- 静态库依赖：检查**静态库导出符号**出现在 `.so` 的 `.dynstr`/`.strtab`
  （扫原始字节中的符号名，如 `dbinit`、`tdsdbopen`）——这是"模块真实链接了
  该依赖"的证据。

```python
# test_asterisk_tds.py 核心
blob = open(os.path.join(mods, "cdr_tds.so"), "rb").read()
if b"dbinit" not in blob or b"tdsdbopen" not in blob:
    raise SystemExit("FAIL: no statically-linked FreeTDS symbols")
```

**回退方案**：源码级字节扫描若不可靠（符号被 strip），改用
`/data/service/hnp/bin/llvm-readelf -Ws <mod> | grep <symbol>` 检查 `.dynsym`
（本地可跑；CI 沙箱无 readelf 时退回字节扫描）。

## 单库实证

| 库 | 角色 | 结果 |
|----|------|------|
| **asterisk-tds/22.10.1** | 主验证（本 PR） | ✅ 首次按库名（libsybdb）校验 FAIL；改为静态符号（dbinit/tdsdbopen）校验后 conan create 全流程通过 |

## 测试覆盖边界

- 静态符号校验是 **R34 真实产物校验**：既验证模块存在、又验证 ELF shared object，
  还验证依赖符号已并入——不因静态库而放松为"文件存在即可"；
- 声明通过率时：以 conan create 全流程（含 test_package R34 校验通过）为实证；
  tds 模块无专属上游测试，按 rule 1.2 如实声明"上游无测试"（非跳过）。
