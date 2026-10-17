# DRAFT：musl 无 glibc 扩展 `fcloseall()`——改 `fflush(NULL)` 并审语义差

> Contributor: CIW | Status: Draft | Updated: 2026-09-21
> Source: fontopia 2.0 适配（PR #11672，`patches/0001-musl-fcloseall-to-fflush.patch`）
> 同 stem 知识文件：`DRAFT-fontopia-2.0-musl-missing-fcloseall-fflush.patch.kv`

## 错误特征

OHOS（musl）上**链接期**失败：

```
undefined symbol: fcloseall
```

（编译期通常只是 `implicit declaration` 的 warning，容易漏看——所以"能编译"不等于"能链接"。）

## 根因分析

`fcloseall()` 是 **glibc 扩展**（关闭所有已打开流），POSIX/ISO C 都没有它，**musl 不提供**。
上游代码直接调用，于是在 OHOS 上链接失败。

## 推荐方案

**方法**: replace-fcloseall-with-fflush-null-and-audit-semantics

```c
- fcloseall();
+ fflush(NULL);   /* 刷新所有流 */
```

**先审调用点意图**：
- 只为**落盘/刷新缓冲**（退出路径最常见）⇒ `fflush(NULL)` 语义等价，可直接替换 ✅
- 确实要**关闭**所有流（释放 fd）⇒ `fflush(NULL)` **不够**，需显式逐个 `fclose` 或在补丁内自实现 `fcloseall`

补丁只改调用点，不动上游其它代码；补丁描述写明"musl 无 glibc 扩展"。

## 适用范围与反例

- **适用**：任何调用 glibc 扩展 `fcloseall()` 的 C/C++ 程序在 musl/OHOS 构建时。
- **判据**：**链接期** `undefined symbol: fcloseall`（不是缺头文件）。
- **反例/边界**：
  - `fflush(NULL)` ≠ `fcloseall()`：前者**不关闭**流 —— 若原意是释放 fd，替换后会有泄漏；
  - 不得用 `#define fcloseall fflush` 掩盖语义差；
  - 可推及同族 glibc-only stdio 扩展（`__fsetlocking`、GNU `fmemopen` 语义差异等）——按签名分别处理，勿混为一条。

## 验证证据（fontopia 2.0 / PR #11672）

- 上游调用 `fcloseall()` → OHOS/musl：`undefined symbol: fcloseall`；
- 补丁 `0001-musl-fcloseall-to-fflush.patch` → `fflush(NULL)`（该调用点语义为"退出前刷新"）；
- 消费者测试（驱动已安装 `fontopia` 二进制，**4 断言**）全部通过。

## 与既有条目的差异（查重结论）

- **KB 全库 grep `fcloseall` 零命中**（`knowledge/doc/*` 与 `knowledge/drafts/*`，2026-09-21 实测）⇒ 无条目覆盖本签名与解法。
- 仓库配方归档内有**同族先例**：`gnudos 2.0` 采用同一改法（但未沉淀为 KB 条目）→ 本条目把这个先例正式入库。
- 与 E011（configure 内 umask 077）、E386（getcwd 诊断）无关——那两条是 fontopia 另外两个问题的 hit，不属于本条。
