# DRAFT-libgtop-makeinfo-missing — autotools 库 doc/ 手册生成依赖 makeinfo，CI 无 texinfo 时注入 MAKEINFO=true

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-09
> **Severity**: 🟡 medium | **Category**: autotools / makeinfo / texinfo / build / OHOS

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| （无） | — | — | index.tsv 查证：`makeinfo` 命中 0 条、`texinfo` 命中 0 条、`.texi` 命中 0 条——全新增 |

## Scope（何时用）

在 OHOS/CI 环境（无 texinfo 包）编译任何 **autotools** 构建且
`doc/` 目录含 `.texi` 源文件的软件时，若出现：

- `make[3]: *** [doc/libgtop2.info] Error 127`（makeinfo: command not found）；
- `missing: line 81: makeinfo: command not found`（autoconf missing 包装脚本）；
- 已确认 texinfo 不存在且手册非交付物（库/头文件/.pc 才是）。

## Symptom

```text
MAKEINFO <path>/doc/libgtop2.info
<path>/missing: line 81: makeinfo: command not found
WARNING: 'makeinfo' is missing on your system.
make[3]: *** [Makefile:503: <path>/doc/libgtop2.info] Error 127
```

## Root Cause

automake 生成的 Makefile 用 `$(MAKEINFO)`（configure 检测为
`MAKEINFO=${MAKEINFO-"${am_missing_run}makeinfo"}`）生成 `doc/*.info`。
makeinfo 缺失时 configure 回退 `missing` 包装脚本，而 missing 对被包装的
不存在命令返回 127 → make 以 Error 127 整体失败，即使 .info 不是运行交付物。

## Solution

配方 generate() 注入 `MAKEINFO=true`（参考
archives/l/libgtop/2.41.3/conanfile.py）：

```python
tc.configure_args.append("MAKEINFO=true")
```

configure 收到显式 MAKEINFO 后不再回退 missing 脚本，make 直接执行
`true libgtop2.info`（空操作无输出），跳过手册生成；.texi/.info 不影响
库编译、头文件安装与 pkg-config 文件。

## Verification

```bash
cd archives/l/libgtop/2.41.3
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 全绿（注入前 doc/ 处 Error 127 失败）
```

## 适用边界 / 反例

- 若手册是交付物（如 gtk-doc 完整文档库），应 tool_requires texinfo 真正
  生成，而非跳过；
- makeinfo 仅为 .texi→.info 转换，docs 的 .html 生成走 gtk-doc 单独路径，
  不受影响。

## 关系字段

- similar_to: 无
- caused_by: OHOS/CI 无 texinfo 包 + automake missing 回退
- conflicts_with: 无