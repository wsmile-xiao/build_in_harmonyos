# DRAFT-12939-gputils-packaging-isdir-guard-silent-partial-ship — `package()` 的 `os.path.isdir()` 容错守卫把「缺件」静默成「成功」，发布制品少了工具却无任何报错

> **Contributor**: atomcode | **Status**: DRAFT | **Updated**: 2026-09-27
> **Severity**: 🟠 high（静默发布残缺制品，CI 全绿） | **Category**: conan / packaging / ohos

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条增量（差异化） |
|---------|---------|--------|--------------------|
| `DRAFT-bzip3-1.5.4-cmake-config-in-missing-from-tarball` | 已收 | **上游** release tarball 漏打包被引用的文件 → 解包即报错失败 | 那条是**上游**缺件且**会炸**；本条是**我们自己配方**的守卫把缺件**变成静默成功** |
| `DRAFT-6051-libnxml-…-missing-dotfiles` | 已收 | **远端 conan 包**丢失文件，半残缓存仍被命中 | 缺陷在**制品/缓存**侧；本条的制品是我们亲手打出来的，缺陷在**配方 `package()`** |
| `E598` | 已收 | 子包 `test_package` 如何证明「测的就是本子包产物」 | E598 讲**如何证明**；本条讲**为什么制品会悄悄不完整**（上游即其反面教材） |
| `DRAFT-11055-waf-testonly-execution-accounting` | 已收 | 「少跑/静默跳过」的**测试**计数对账 | 同为「静默 vs 显式对账」范式，但面在**测试执行**；本条面在**打包产物** |

> 查证记录（四路检索 `graph/index.tsv` / `graph/*.kv` / `doc/*.md` / `drafts/*`）：
> `漏装` / `少装` / `没装上` / `静默缺` / `未被安装` **命中 0**；`os.path.isdir` 命中
> 3 处，其中 2 处为**消费者侧路径注入**（E598 的 `runenv_info` 逐目录 isdir）与
> 测试框架守卫，无一处讲「`package()` 守卫掩盖交付缺件」。

## Scope（何时用）

任何 Conan `package()` 用「候选目录/文件列表 + `if os.path.isdir(...)`（或
`glob` / `exists`）容错」的方式拷贝产物的配方，尤其当：

- 上游在版本间**调整过目录布局**（本条的 gputils 1.5.x：`gplib`/`gpdasm`/
  `gpstrip`/`gpvo`/`gpvc` 从「各自一目录」改到**统一在 `gputils/` 子目录构建**）；
- 或产物**部分可选**（受 `--enable-*` 影响）。

症状：`conan create` 退出码 0、CI 全绿、日志无告警，但**发布制品里少了东西**；
问题要到消费者（本条的 sdcc PIC14/PIC16）报 `AC_PATH_PROG` 找不到某工具时才暴露。

## Symptom

`conan create` 全流程通过，制品的目录结构看起来"正常"，但消费者侧找不到工具：

```text
checking for gplib... no
configure: error: gplib not found            # sdcc PIC14/PIC16 需要 gpasm+gplink+gplib 三件齐备
```

而在**制品自身**里查证才发现：`<pkg>/gputils/` 下有 `gplib`，但 `package()` 的
拷贝清单里根本没有它（清单写的是旧布局的 `gplib/`，该目录已不存在）。

## 根因

1.5.2 的打包清单按**旧布局**列举了分工具目录，并用 `isdir` 守卫容错：

```python
bin_dirs = ("gpasm", "gplink", "gplib", "gpvc", "gpdasm")   # ← 后三个在 1.5.x 已不存在
for entry in bin_dirs:
    s = os.path.join(src, entry)
    if os.path.isdir(s):            # ← 目录不存在就"跳过"，不报错
        shutil.copytree(s, ...)
```

这个守卫的**本意**是"可选目录容错"（目录不在就算了）。但在一份**交付清单**里，
它把「该死的缺件」与「正常的可选缺失」**混为一谈**——目录因布局变更而消失时，
守卫同样静默跳过，于是 `package()` 成功返回，制品少装 `gplib`。

**关键点**：这不是上游缺件（对比 `DRAFT-bzip3`/`DRAFT-6051`），缺陷在我们的
`package()`。`isdir` 守卫在"探查可选特性"语境下是对的，在"断言交付完整性"语境下
是错的——同一段代码承担了两种语义。

## 修复（gputils 1.5.2.1 实证）

两步，**缺一不可**：

1. **对齐布局**：按 1.5.x 实际布局改为三目录，并把"在 `gputils/` 子目录里产出"的
   五个程序显式登记：

```python
bin_dirs = ("gpasm", "gplink", "gputils")        # gplib/gpdasm/... 都在 gputils/
```

2. **加显式完整性断言**（把"静默"改成"fail loudly"）：

```python
required = {
    "gpasm":   ("gpasm",),
    "gplink":  ("gplink",),
    "gputils": ("gpdasm", "gplib", "gpstrip", "gpvo", "gpvc"),
}
missing = [os.path.join(d, b) for d, bins in required.items()
           for b in bins
           if not os.path.isfile(os.path.join(self.package_folder, d, b))]
if missing:
    raise ConanException("incomplete gputils tool set, missing: " + ", ".join(missing))
```

**为什么必须有第 2 步**：第 1 步只修了**这一次**的清单；只要守卫还在，下一次
上游再调布局仍会静默漏装。断言把"制品是否完整"变成**构建期可判定**的事实。

## 适用范围

- 所有「多目录/多文件 + `isdir`/`exists`/`glob` 容错拷贝」的 `package()`；
- 上游跨版本改布局的包（尤其 autotools `SUBDIRS` 重组、把若干程序并入
  一个子目录的情形）；
- 交付物是"工具集"而非单一二进制的包（少一件即消费者不可用）。

## 反例/边界

- **断言集必须与 `configure` 开关联动**：若某产物确由 `--enable-X` 决定是否
  构建，则不能无条件断言其存在，否则把"合法的可选缺失"误判为失败。此时应按
  **已启用的选项**动态生成 `required` 集，而非一刀切全集。
- 若目录**真的可选且缺失是常态**，应显式区分两类：`optional()`（静默跳过，可）
  与 `required()`（缺失即 raise）。**混用同一守卫是根因**。
- 上游 tarball 自身缺件（会立即报错的场景）不属于本条，见 `DRAFT-bzip3`。

## 同一配方里的其它适配点（已分别被既有条目覆盖，本条不重复申报）

gputils 1.5.2.1 的配方还用到下列措施，均已查证有既有条目覆盖，故**只引用、不新开**：

| 措施 | 既有条目 | 说明 |
|---|---|---|
| `config.status` 临时目录在 hmdfs 上 `Permission denied` | **E011**（umask 型）；`mktemp -d "./confXXXXXX"` 变体见 **`DRAFT-6507-cln-mktemp-0700-hmdfs`** | 本配方把 configure 的 `mktemp -d "./confXXXXXX"` 与 `tmp=./conf$$-$RANDOM` 两行直接改指 `$TMPDIR`（第三种手法：就地改 configure；另两种为 PATH-prepend mktemp wrapper、改 mkdir -m 0777） |
| `aclocal` 不可执行（hmdfs 强制 0o770、`chmod` 无效）→ 跳过 `autoreconf` | **E443**（HMFS 跨 UID 拒 shebang，需解释器桥 + `ACLOCAL`/`AUTOMAKE` 变量） | 本配方直接**不跑 autoreconf**（sdist 自带 configure），属 E443 的"绕开"分支 |
| `config.guess` 猜不出 OHOS | **E007** | 显式传 `--build/--host=aarch64-unknown-linux-gnu` |
| 构建期 `TMPDIR` 被 conan 的 `conanbuild` env 指向 hmdfs（`~/.cache/tmp`），不能读 `$TMPDIR` | **`DRAFT-conan-aggregated-env-whitelist`** | 本配方改为**硬编码 CI 可写目录**，是该条的一个实例，不独立成条 |
| 上游 `$(datadir)/gputils/<sub>` 编译期回退路径在包内不存在 → 由 `package_info` 导出 `GPUTILS_HEADER_PATH`/`GPUTILS_LKR_PATH` | `DRAFT-libint2-2.7.2-compile-time-datadir-macro-for-runtime-data`、`DRAFT-magic-db-load-path-fallback` | 形态相近，可作既有条目的补充案例，不新开 |

## 触发实例

gputils 1.5.2 → 1.5.2.1（PR #12939，2026-09-27）。1.5.2 发布制品缺 `gplib`，
导致 sdcc 的 PIC14/PIC16 端口无法启用；1.5.2.1 修正清单并加入上文完整性断言。
