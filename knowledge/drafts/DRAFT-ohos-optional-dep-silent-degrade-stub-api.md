# DRAFT-ohos-optional-dep-silent-degrade-stub-api — 可选依赖缺失致 configure 静默降级、部分 API 变桩

> Contributor: D8A1 / Status: **DRAFT** / Updated: 2026-09-16 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-optional-dep-silent-degrade-stub-api`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `E550`（多编码后端图像库）| 图谱/草稿 | 多**可选后端**的 CMake 交叉适配组合方案（逐后端 find 缓存变量预设）| 那条讲"如何把多个可选后端**接线**起来"（CMake 侧配置手法）；**本条讲"可选依赖缺失时的降级语义与测试划界"**，与构建手法无关。实测 E550 全文 `xmlsec`=0 / `桩`=0 / `签名`=0 / `PKG_CHECK_MODULES`=0 |
| `DRAFT-ohos-dependency-library-missing-own-symbols` | 本轮 pwquality 草稿 | 依赖**库存在**但自身 API 符号未实现（空壳库）| 那是"符号空壳、链接期暴露"；**本条是功能分支在编译期被整体裁掉**，构建成功且桩可链接 |
| `DRAFT-ohos-perl-noncore-runtime-dep-requires-vs-recommends` | 本轮 perl-io-async 草稿 | Perl 侧 `requires` vs `recommends` 的档位语义 | 同属"依赖档位"家族，但那是 **Perl 模块文件缺失**（`@INC` 找不到）；**本条是 autotools 的 `PKG_CHECK_MODULES` 分支语义**，表现为**API 变桩**而非 import 失败 |

**全库查证**：对 `xmlsec1`、`USE_XMLSEC`、`签名.*桩`、`PKG_CHECK_MODULES.*AC_MSG_ERROR`、
`可选依赖.*(桩|降级|不可用)` 等关键词，在 `knowledge/index.tsv`、
`knowledge/graph/index.tsv`、`knowledge/graph/*.kv`、`knowledge/doc/*.md`、
`knowledge/drafts/*.kv`、`knowledge/drafts/*.md` 中 grep —— 除上表（机制均不同）
外**命中 0 条**专讲此机制的条目。

## Scope（何时用）

任何用 `PKG_CHECK_MODULES` / `AC_ARG_WITH` / `AC_ARG_ENABLE` 把依赖做成**可选**的
autotools 项目。典型是"核心功能必需 + 增强功能可选"的库（加密/签名/压缩/硬件加速
等可选后端）。

**在适配场景下尤其突出**：可选依赖常**未发布到制品仓**，于是被动落入降级分支。
**这不是适配缺陷，但必须显式申报其边界。**

## Symptom

### 表象：一切正常（这正是危险之处）

```console
checking for xmlsec1... no
...
configure: exit 0        ← 构建成功
make: exit 0
```

configure 与 make **退出码均为 0**，绿灯掩盖了功能缺失。

### 真相：一整块 API 变成了桩

库仍能构建、多数功能可用，但**签名相关能力完全不存在**。实测 libpskc 2.6.14：

| API | 降级后行为 |
|---|---|
| `pskc_sign_x509` | **桩**（返回错误）|
| `pskc_verify_x509crt` | **桩**（返回错误）|

调用方拿到的是**运行时错误码**，而非链接错误 —— 定位成本远高于链接期失败。

## Root Cause

`libpskc/configure.ac` 把可选依赖写成：

```sh
PKG_CHECK_MODULES(XMLSEC, xmlsec1$xmlsecengine, [xmlsec=yes], [xmlsec=no])
```

**第三参是"找到"的成功分支，没有 `AC_MSG_ERROR`** —— 于是依赖缺失时 configure
**不失败**，而是把 `xmlsec=no` 记入条件；随后：

```sh
if test "$xmlsec" != "no" ; then
  AC_DEFINE(USE_XMLSEC, 1, [Define to 1 if you want to use xmlsec.])
fi
```

`AC_DEFINE(USE_XMLSEC, ...)` **被整个跳过**，源码中由该宏守卫的实现随之被裁掉，
剩下返回错误的桩。

### 与「硬依赖」的关键对比（同一文件内）

| 依赖 | 写法 | 缺失后果 |
|---|---|---|
| `libxml2` | `PKG_CHECK_MODULES(XML2, libxml-2.0,, [AC_MSG_ERROR([Cannot find libxml2])])` | **configure 直接失败**（不会产生"看似成功实则残缺"的产物）|
| `xmlsec1` | `PKG_CHECK_MODULES(XMLSEC, xmlsec1..., [xmlsec=yes], [xmlsec=no])` | **静默降级**，API 变桩 |

判据一句话：**看第三参是 `AC_MSG_ERROR` 还是成功/失败分支**。

## Recommended Solution

### 主方案（priority 1）— 定性 → 文档显式化 → 测试划界

1. **定性**：读 `configure.ac` 判定该依赖是 optional（无 `AC_MSG_ERROR`）。
   **若是 optional，不得为了"消除告警"去强行补一个未发布的依赖**——那会偏离上游
   设计意图。
2. **文档显式化**：在 `notes.md` 与 `manifest.yaml`（`dependencies.optional`）写明
   「该依赖缺失 → 该分支被裁 → **这些具体符号**变桩」，而不是笼统说"功能降级"。
3. **测试划界**：消费者测试**只覆盖降级后仍可用的 API**，并在**代码注释 +
   MANIFEST.yml** 中显式写出"刻意不覆盖 X/Y（需 Z，未发布）"。

配方内可加**构建期自检**：探测到降级已发生时输出 warning 说明受影响面 ——
让每次构建都留下一行可追溯的边界声明：

```python
if downgraded:
    self.output.warning(
        "<dep> unavailable -> <feature> APIs are stubs; "
        "consumer tests intentionally cover only the rest")
```

### 回退方案（priority 2）— 发布该可选依赖以恢复全量覆盖

若消费方**确实需要**该能力（例如上游测试套件要求全量 API），须先把该可选依赖适配并
发布到制品仓，再以 `requires()` 引入，使 configure 走"找到"分支。
代价：依赖链变长、引入上游本可省去的构建负担 —— **仅在确有需求时做**。

### 禁止做法

- ❌ 为缺失的可选依赖**伪造桩实现**——与真库行为不一致会产生**虚假通过**；
- ❌ 把可选依赖**硬改成 `AC_MSG_ERROR`** —— 修改上游语义，让本可成功的构建变失败；
- ❌ 消费者测试**照抄上游全量 API 清单**而不核对可用性 —— 会假定覆盖全量；
- ❌ 因功能降级就**直接删除断言** —— 会让"能力缺失"与"验证通过"无差别（R51）。

## 实测证据（2026-09-16，libpskc 2.6.14 适配）

| 项 | 结果 |
|---|---|
| libxml2（硬依赖）| `AC_MSG_ERROR([Cannot find libxml2])`，ohpcd 已发布 → 正常走通 |
| xmlsec1（可选）| `[xmlsec=yes]/[xmlsec=no]`，**未发布** → 降级 `xmlsec=no` |
| `USE_XMLSEC` | 未定义（`AC_DEFINE` 被跳过）|
| 受影响 API | `pskc_sign_x509` / `pskc_verify_x509crt` 变桩 |
| 构建结果 | configure/make **均 exit 0**（绿灯掩盖功能缺失）|
| 处置 | notes/manifest 显式记录受影响符号；消费者测试覆盖解析/访问器/序列化/校验，并**显式标注**刻意不覆盖签名入口 |
| 消费者测试实测 | 通过（`pskc_parse_from_memory` + `pskc_output` 真实往返 + 错误路径）|

## 测试覆盖边界

本条处理"**可选依赖缺失的降级语义**"。区分相邻情形：

- 依赖**库存在但符号空壳** → `DRAFT-ohos-dependency-library-missing-own-symbols`；
- Perl 侧模块缺失（`@INC`）→ `DRAFT-ohos-perl-noncore-runtime-dep-requires-vs-recommends`；
- 多可选后端如何**接线**（构建手法）→ `E550`；
- 硬依赖缺失 → `E241` / `E305` 族（configure 直接失败，无本条问题）。

## 关联条目

- 相似：`DRAFT-ohos-perl-noncore-runtime-dep-requires-vs-recommends`（依赖档位语义族）
- 差异：见上方差异化定位表
