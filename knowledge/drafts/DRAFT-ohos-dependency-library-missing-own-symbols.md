# DRAFT-ohos-dependency-library-missing-own-symbols — 依赖制品自身不实现其 API 符号

> Contributor: 7F2B / Status: **DRAFT** / Updated: 2026-09-16 / Severity: 3 (high)
> Prospect ID: `DRAFT-ohos-dependency-library-missing-own-symbols`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `E524` | 图谱 | `SYS_PREFIX` 注入污染 + 依赖缺失，同样表现为 `C compiler cannot create executables` | E524 的报错源是**环境污染/依赖缺失**；**本条是依赖制品自身符号未实现**。实测 E524 全文 `gettext`=0 / `libintl`=0 / `undefined reference`=0 |
| `DRAFT-lld-shlib-undefined-host-contract` | 草稿 | lld 的 `--no-allow-shlib-undefined` **契约本身** | 那条讲 lld 通用语义；**本条讲"依赖库空壳"这一具体成因 + configure 的误导性包装**。实测该草稿 `libintl`=0 / `桩`=0 / `不实现`=0 |
| `E531` | 图谱 | musl 缺 glibc 风格 `qsort_r`，以 shim 修复 | 那是 **libc 缺函数**需补实现；本条是**第三方制品不实现自己的 API**，处置是弃用/换提供者 |

**全库查证**：对 `libintl` × 未定义、`空壳库`、`桩库`、`不实现.*符号`、
`nm -D -u` 等组合关键词 grep —— 除上表（机制均不同）外**命中 0 条**专讲此机制的条目。

## Scope（何时用）

任何**链接"空壳/桩库"制品**的 autotools / CMake 项目。典型是 NLS 相关
（`libintl` / `gettext`），或任何只导出桩符号的兼容库。

在 OHOS 上被 **`--no-allow-shlib-undefined`**（lld 默认）放大：

| 链接器 | 对未定义符号的态度 | 后果 |
|---|---|---|
| GNU ld（glibc 生态常见）| 默认**允许** | "链得上，运行才炸" |
| **lld（OHOS）** | **默认拒绝** | **链接期直接报错**（暴露更早，但报错被 configure 包装）|

## Symptom

### 表象（误导性）

```console
configure: error: in `/path/to/build':
configure: error: C compiler cannot create executables
```

报错**指向 C 编译器**，极易误诊为工具链/环境问题。

### 真相（在 config.log 里）

```console
configure:3943: /data/service/hnp/bin/clang -O3 -I.../libin.../include \
    -I.../crack.../include -DNDEBUG -L.../libin.../lib -L.../crack.../lib \
    conftest.c -lintl -lcrack >&5
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: gettext
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: dgettext
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: bindtextdomain
...
clang-15: error: linker command failed with exit code 1
```

> ⚠️ 关键：**不要只看 configure 的包装报错**。真正的失败是**链接期**的
> `undefined reference`，而非 conftest 本身的编译错误。

## Root Cause

ohpcd 的 `libintl/0.26.1` 里，`libintl.so.8` 把 `gettext` / `dgettext` /
`dcgettext` / `ngettext` / `dngettext` / `dcngettext` / `bindtextdomain` /
`textdomain` / `bind_textdomain_codeset` **全部列为未定义符号** —— 即该库
**自身不提供**这些实现（空壳/桩库制品）。

实测判据：

```console
$ nm -D -u libintl.so.8 | grep -E "gettext|bindtextdomain"
                 U bind_textdomain_codeset
                 U bindtextdomain
                 U dcgettext
                 U dgettext
                 U gettext
                 U ngettext
$ nm -D --defined-only libintl.so.8 | grep gettext
（无输出 → 确认未实现）
```

**与"依赖缺失"的关键区别**：库**存在**、头也**存在**，"装了依赖"这步**是成功的**，
问题**延后到链接期**才暴露。

## Recommended Solution

### 主方案（priority 1）— 弃用该依赖，或关掉对应功能

**先判断该依赖是否真的需要**：

1. **若项目本可用开关关掉该功能**（如 NLS 用 `--disable-nls`）→
   **直接移除该依赖**。不要为了"凑齐依赖表"引入一个链接即失败的库。

   实测 pwquality 1.4.5 即如此：

   ```python
   tc.configure_args.append("--disable-nls")   # 本就关掉 NLS
   # 不再写 self.requires("libintl/...")
   ```

   移除后 configure **立即通过**。

2. **若功能确为必需** → 须先修复该依赖制品（补实现或换上游版本），
   发布到制品仓后再引入。

**无论哪条路都必须**：

- 用 `nm -D` 验证依赖库确实**定义**了它声称提供的符号；
- 遇到 `C compiler cannot create executables` 时**先查 `config.log`**，
  不要盲调工具链。

### 回退方案（priority 2）— 换真正的提供者

若功能不可关闭且确实需要这些符号，必须换一个**真正实现**它们的提供者，并让
`-L` 指向它。

**禁止**用 `-Wl,--allow-shlib-undefined` 之类放宽链接——那只是把错误推到**运行期**
（dlopen/调用时符号找不到），在 OHOS 上表现为难以定位的运行时崩溃。

### 禁止做法

- ❌ 见到 `C compiler cannot create executables` 就换编译器/调工具链/改 SDK
  ——根因常在 `config.log` 的 `undefined reference`，与编译器无关；
- ❌ 放宽未定义符号以"通过链接"——病灶被掩盖到运行期，可能 CI 全绿而真机崩溃。

## 实测证据（2026-09-16，pwquality 1.4.5 适配）

| 阶段 | 结果 |
|---|---|
| 初版（`requires("libintl/0.26.1")` + `AutotoolsDeps`）| `ld.lld: undefined reference ... gettext/dgettext/bindtextdomain`，被包装成 `C compiler cannot create executables` |
| 依赖库符号检查 | `nm -D -u libintl.so.8` 列出 9 个未定义符号；`--defined-only` 下**无一**为已定义 |
| 处置 | 本构建本就 `--disable-nls`，故**移除 libintl 依赖** |
| 修复后 | configure 通过；`conan create` 后续到 exit=0、consumer API PASS |
| 排查要点 | 只看 configure 报错会误判为工具链问题；`config.log` 中才是真相 |

## 测试覆盖边界

本条处理"**依赖制品不实现自身 API 符号**"。区分相邻情形：

- `SYS_PREFIX` 注入污染 / 依赖真缺失导致同类报错 → `E524`；
- lld 的 `--no-allow-shlib-undefined` 契约语义本身 → `DRAFT-lld-shlib-undefined-host-contract`；
- libc 缺 glibc 风格函数需补 shim → `E531`。

## 关联条目

- 相似：`E524`（同表象、不同根因）
- 差异：见上方差异化定位表
