# DRAFT-ohos-tool-requires-buildenv-must-not-be-overridden-by-local-fallbacks — tool_requires 提供的 buildenv 变量是权威，本地硬编码兜底不得覆盖

> Contributor: AtomCode/oh-executor | Status: **DRAFT** / Updated: 2026-09-30 / Severity: 2 (medium)
> Source: qatlib 26.02.0 HarmonyOS PC adaptation（PR 分支 `feat/qatlib-26.02.0`）
> 对应：`knowledge/drafts/DRAFT-ohos-tool-requires-buildenv-must-not-be-overridden-by-local-fallbacks.kv`

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `DRAFT-perl-buildenv-info-missing-dependency-injection` | 已在 main（draft） | 依赖包**只声明 `runenv_info`**（无 `buildenv_info`）→ `PERL5LIB` **不进**下游 build 上下文，消费方须自行注入 | **方向相反**：该条是「变量**缺失** → 要注入」；本条是「变量**已提供** → 别覆盖」。二者构成同一变量的两侧：missing → inject；provided → do not clobber |
| `DRAFT-cpdb-libs-1.2.0-autotools-git-archive-tool-requires-bootstrap` | 已在 main（draft） | git-archive/无 dist 资产 → 必须用 `tool_requires(automake+libtool)` 自举 | 那条解决「**该不该声明** tool_requires」；本条从它之后开始：声明**已就位**后，遗留的宿主镜像兜底路径如何处理 |
| `DRAFT-remctl-3.18-conan-buildenv-save-order` | 已在 main（draft） | conan 保存 buildenv 文件的**顺序**问题 | 那条是 conan 内部次序；本条是**手写赋值**击败了 tool_require 的贡献 |

**全库查证**：对「tool_requires 的 buildenv 值被本地兜底覆盖 / PERL5LIB 覆盖导致 aclocal 找不到模块」这一情形，
在 `knowledge/graph/`、`knowledge/doc/`、`knowledge/drafts/` 中 grep —— 未命中同名条目。

## Scope（何时用）

配方满足**两条同时成立**时：

1. autotools 工具来自 `tool_requires`（而非宿主镜像），例如

   ```python
   def build_requirements(self):
       self.tool_requires("automake/1.18")   # 自带 aclocal + automake
       self.tool_requires("libtool/2.5.4")   # 自带 libtoolize
   ```

2. 配方里**仍留有**指向宿主镜像的硬编码兜底，例如

   ```python
   env["PERL5LIB"] = "/storage/Users/currentUser/usr/local/share/automake-1.16"
   env["AUTOMAKE"] = "/storage/Users/currentUser/usr/local/bin/automake"
   env["ACLOCAL"]  = "/storage/Users/currentUser/usr/local/bin/aclocal"
   ```

这类兜底通常是**加 tool_requires 之前**留下的；加了 tool_requires 之后，它们从「有用」变成「有害」。

## ⭐ 核心结论：先展开 tool_requires 的环境，**再仅对缺失项**做兜底

`tool_requires` 的 `buildenv_info` 会把 `PATH` / `ACLOCAL_PATH` / `PERL5LIB` /
`AUTOMAKE` / `ACLOCAL` 等一并备好。本仓配方若用 `subprocess.run(env=...)`
（而非 `self.run(env="conanbuild")`），需显式展开：

```python
vbe = VirtualBuildEnv(self).vars()
env.update(vbe.items())
provided = set(vbe.keys())          # ← 记住它到底提供了什么

# 本地兜底：仅在 tool_requires 未提供该变量时生效
if "PERL5LIB" not in provided:
    _pl = "/storage/.../usr/local/share/automake-1.16"
    if os.path.isdir(_pl):
        env["PERL5LIB"] = _pl

for k, v in (("AUTOCONF", "/data/service/hnp/bin/autoconf"),
             ("AUTOMAKE", "/storage/.../usr/local/bin/automake"),
             ("ACLOCAL",  "/storage/.../usr/local/bin/aclocal")):
    if k in provided:               # ← 绝不覆盖
        continue
    if os.path.isfile(v):
        env[k] = v
```

> **判据**：`tool_requires` 提供的值是该工具**自洽**的前提——
> `automake/1.18` 装出的是**可重定位包装脚本**，其脚本内 `@INC` 的安装前缀是坏的
> （日志里能看到字面量 `//share/automake-1.18`），**正是它自己的 `PERL5LIB`**
> （指向真实的 `share/automake-1.18`）兜住了这件事。覆盖它，`aclocal` 就找不到自己的模块。

## ★ 实测：加了 tool_requires 之后，旧兜底立刻制造**新的**失败

qatlib 26.02.0 的两轮 CI，恰好一前一后：

| 轮次 | 现象 | 原因 |
|---|---|---|
| 第 1 轮（#65788 之前） | `Can't exec "aclocal": No such file or directory` | 干净 PATH 里**没有** aclocal → 需要 `tool_requires(automake)` |
| 加 tool_requires 后 | `Can't locate Automake/Config.pm in @INC ... .aclocal-real line 33` | 遗留的 `env["PERL5LIB"] = .../automake-1.16` **覆盖**了 automake/1.18 自己的值 |

第二轮报错全文（注意 `@INC` 里**同时**列出了两个 automake 的目录）：

```console
Can't locate Automake/Config.pm in @INC (you may need to install the Automake::Config module)
(@INC entries checked: //share/automake-1.18
                     /storage/Users/currentUser/usr/local/share/automake-1.16
                     /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux
                     ...)
 at /storage/Users/currentUser/.cache/conan2/p/autom3efab95d532f9/p/bin/.aclocal-real line 33.
BEGIN failed--compilation aborted at .../bin/.aclocal-real line 33.
autoreconf: error: .../bin/aclocal failed with exit status: 2
```

> 🔍 **关键诊断线索**：`@INC` 列表里**同时**出现
> `//share/automake-1.18`（tool_require 的、被装坏的前缀）与
> `/storage/.../usr/local/share/automake-1.16`（宿主镜像的、被写死的）——
> 两个 automake 版本**并列竞争**，就是「本地赋值压过 tool_require」的典型指纹。

## ★ 为什么容易误判成「automake 不好用」

| 表象 | 真相 |
|---|---|
| 报错发生在 `aclocal` 内部、指向 `Automake/Config.pm` | 是**我们的赋值**让 aclocal 失去了自己的模块路径；aclocal 本身没问题 |
| 刚加了 tool_requires 就报错 | 时序上像是「tool_requires 没生效」→ 极易**回退正确的修复** |
| 提示 *you may need to install the Automake::Config module* | 它已经由 automake/1.18 提供了，只是路径被冲掉 |

**禁止**因此回退 `tool_requires`——那会退回到第 1 轮的 `Can't exec aclocal`。

## 反例（禁止）

- ❌ **无守卫地写 `env["PERL5LIB"] = ...`**（或 `AUTOMAKE`/`ACLOCAL` 指向宿主镜像）：
  会静默替换掉 tool_require 贡献的值，报错却落在 `aclocal` 内部，离肇事行很远。
- ❌ **硬编码宿主镜像的路径**（`/storage/.../usr/local/...automake`）：它不在配方依赖图内，
  且版本与声明的 tool_require 错位（1.16 vs 1.18）→ 换 worker 或镜像升级即失败，且无配方改动可解释。
- ❌ **因为 `aclocal` 报错就回退/怪罪 `automake/1.18`**：tool_requires 是正确的修法，
  本轮失败由「本地覆盖击败了它」造成，回退会重新引入最初的问题。

## 实测记录

| 包 | 现象 | 肇事行 | 处置 |
|---|---|---|---|
| qatlib 26.02.0 | `Can't locate Automake/Config.pm in @INC`（`.aclocal-real:33`） | 无守卫的 `env["PERL5LIB"] = .../usr/local/share/automake-1.16` | 改为「先展开 VirtualBuildEnv 并记下 `provided`，兜底项逐一加 `if k not in provided` 守卫」 |

> 补充：`autoconf` / `m4` 仍**有意**不由 tool_requires 提供（声明 `autoconf/2.72` 会拉入
> OHOS 构建的 perl，其 XS 与 SDK perl 冲突），所以「删掉全部兜底」并不通用——
> 正确做法是**加守卫**，让 SDK 路径与 tool_require 路径各自在需要时生效。
