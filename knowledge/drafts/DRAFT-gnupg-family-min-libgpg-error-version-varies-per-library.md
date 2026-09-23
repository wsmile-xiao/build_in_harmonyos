# DRAFT-gnupg-family-min-libgpg-error-version-varies-per-library — GnuPG 家族各库对 libgpg-error 的最低要求不同，且声明变量名有两套

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-12
> **Severity**: 🟡 medium | **Category**: dependency / autotools / gnupg / versioning

> **收录标准说明**（2026-09-12 按评审反馈瘦身）：只保留**非直觉**的部分 ——
> ① 各库下限差异的实测数据；② **两套变量名导致的漏检**。
> 已删除"不要按同族推断"一类常识性论述及其 fallback。

## 相关既有条目

| 既有条目 | 关系 |
|---------|------|
| **`DRAFT-libksba-1.6.7.1-gnupg-family-autotools-version-mapping`** | 讲 GnuPG 家族移植的**四类坑**（版本映射 / `config.guess`+musl / `gpgrt-config` / `gl` 目录边界），**未涉及"各库最低依赖版本要求不同"**（实测交叉过滤命中 **0**）→ 本条为其补充 |

> 查重（2026-09-12）：`NEED_GPG_ERROR_VERSION` / `NEED_LIBASSUAN_VERSION` / 「最低版本逐库」命中 **各 0**。

## 版本表（实测，逐个读 `configure.ac`）

| 库 | 声明变量 | 最低要求 | 行 |
|----|---------|---------|----|
| **gnupg 2.5.22** | `NEED_GPGRT_VERSION` | **1.56** | `:60` |
| **libksba 1.8.1** | `NEED_GPG_ERROR_VERSION` | **1.28** | `:61` |
| **pinentry 1.3.3** | `NEED_GPG_ERROR_VERSION` | **1.16** | `:239` |
| pinentry 1.3.3 | `NEED_LIBASSUAN_VERSION` | 2.1.0 | `:256` |

## ⚠️ 核心：两套变量名

```
gnupg    : NEED_GPGRT_VERSION        ← 注意是 GPGRT
libksba  : NEED_GPG_ERROR_VERSION
pinentry : NEED_GPG_ERROR_VERSION
```

二者最终都喂给**同一个** `AM_PATH_GPG_ERROR` 宏。因此：

```bash
grep NEED_GPG_ERROR_VERSION      # ✗ 完全漏掉 gnupg 的 1.56
```

而漏掉的恰好是**全族最高要求** → 依赖版本定得过低 → configure 阶段硬失败：

```
*** (at least version 1.56 is required.)
```

反向的代价同样存在：若以最高要求（1.56）为全族基准，则本可用现存 **1.55** 的
libksba / pinentry 也被迫等待新版本发布。

## 方案

```bash
# 两套变量名都要搜（缺一会漏检）
grep -nE 'NEED_(GPG_ERROR|GPGRT|LIBASSUAN)_VERSION' configure.ac
```

与仓库现状比对，只对**确实不满足**的库补新版本依赖：

| 库 | 最低要求 | ohpcd 现状 | 是否需要新版本 |
|----|---------|-----------|--------------|
| gnupg 2.5.22 | **1.56** | 1.55 | ✅ 需要（1.61）|
| libksba 1.8.1 | 1.28 | 1.55 | ❌ 不需要 |
| pinentry 1.3.3 | 1.16 | 1.55 | ❌ 不需要 |

**记录口径**：把该表写进适配方案，后续维护者无需再逐个推断。

## 禁止

- ❌ **只 grep `NEED_GPG_ERROR_VERSION`** —— gnupg 用的是 `NEED_GPGRT_VERSION`，
  只搜前者会**完全漏掉** gnupg 的 1.56（全族最高要求）→ configure 硬失败
- ❌ **按"同族统一版本"推断** —— 实测下限差异极大（1.16 / 1.28 / 1.56），
  以最高要求为全族基准会让本可满足的库也被迫等待新版本发布

## 实证

- **libksba/1.8.1（PR #9637）+ pinentry/1.3.3（PR #9638）**：三档最低要求实测如版本表；
  → libksba 与 pinentry **用 ohpcd 现存的 `libgpg-error/1.55` 即满足**，
  只有 **gnupg 需要 1.61**（前置由 PR #9612 承担）。两库实测 `conan create` EXIT=0。
