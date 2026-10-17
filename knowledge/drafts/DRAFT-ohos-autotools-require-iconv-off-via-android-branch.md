# autotools 包可借上游自带的 `*-linux-android*` 分支让 OHOS 落入「全 UTF-8、免 iconv」路径

## 现象

OHOS 上适配 autotools 工程时，`configure` 阶段报 iconv 相关硬失败：

```
checking for iconv... no
configure: error: You need iconv
```

或构建通过但**运行期**失败：

```
Error relocating …/glib-compile-resources: libiconv …: symbol not found
```

实测案例：`archives/g/gnupg/2.4.9/notes.md`（main 上未交付的旧版本）记录的正是
**libiconv 运行时链接失败**；gnupg 2.5.22（PR #9613）用下述办法规避后交付。

## 根因

许多 autotools 工程用「目标系统分支」决定是否需要 iconv。gnupg 2.5.22 的 `configure.ac`：

```sh
:663  require_iconv=yes          # 默认要求 iconv
:666  have_android_system=no
...
      *-linux-android*)
          have_android_system=yes
          # Android is fully utf-8 and we do not want to use iconv to
          # keeps things simple
          require_iconv=no       # ← 关键：关掉 iconv 强依赖
          build_wks_tools=no
...
:1262 if test "$require_iconv" = yes; then   → AM_ICONV / 依赖 libiconv
:2034 if test "$require_iconv" = yes; then   → 同上（第二处）
```

问题在于 **`*-linux-ohos*` 不在任何分支里**，于是落到默认值 `require_iconv=yes`，
从而强行依赖 libiconv。代价：

1. 需额外引入/适配 `libiconv` 依赖；
2. 即便构建通过，运行期仍可能报 `libiconv` 符号重定位失败（与预编译产物 RUNPATH 问题叠加）。

而 OHOS 与 Android 同属「系统层全 UTF-8」实现，**本就不需要 iconv 做编码转换**。

## 修复方案

在 `configure`（或 `configure.ac`）的系统分支里，把 `*-linux-ohos*` 与
`*-linux-android*` 并列，使 OHOS **继承该分支的既有决策**：

**情形 A —— 仓库直接提交 `configure`**（无 autoreconf 需求，gnupg 属此类）：

```diff
-    *-linux-android*)
+    *-linux-android* | *-linux-ohos* | *-unknown-linux-gnu*)
         have_android_system=yes
         require_iconv=no
         build_wks_tools=no
```

**情形 B —— 能跑 `autoreconf`**：改 `configure.ac` 同一处，再 `autoreconf -fi`。

> ⚠️ **前提**：必须已确保 `config.sub` 能识别 `*-linux-ohos*`（否则根本进不了这个分支）。
> 识别层见 **E007 / E268**；识别层与策略层是两件事，缺一不可。

**回退方案**：若该工程确实用 iconv 做编码转换（文本转码类工具），不能关掉时，则正经
引入 `libiconv` 依赖，并保证其 lib 目录进入 `LD_LIBRARY_PATH`（避免烘焙 RUNPATH 失效）。

## 实测效果

| 项 | 结果 |
|---|---|
| gnupg 2.4.9（main，未交付） | libiconv 运行时链接失败 |
| gnupg 2.5.22（PR #9613，0003-configure.patch） | 走 android 分支，**未引入 libiconv**；上游套件 70/70 = 100%（规范口径） |

该补丁同时把 `configure` 内两处 `umask 077` 改为 `022`（HMDFS 上 `mktemp -d` 权限异常，
另有既有条目录入）。

## 与既有条目的差异

- **E007 / E268 / DRAFT-autotools-config-sub-silent-ohos-triplet**：讲
  **config.sub/config.guess 的三元组识别**（`Kernel 'linux' not known to work with
  OS 'ohos'`、白名单加 `linux-ohos*`）。本条**不重复**该层。
- 本条补的是识别**之后**的策略：三元组被正确识别为 `*-linux-ohos*` 后，
  在 **os 分支**里并入 android，借上游已有的 `require_iconv=no` 关掉 iconv 强依赖。
- 实测全库检索 **`require_iconv` 命中 0**，属空白。
- 与 libksba 同族草稿（`DRAFT-libksba-1.6.7.1-gnupg-family-autotools-version-mapping`）
  无重叠：那篇讲 gpgrt-config / 版本映射 / gl 边界，未涉及 iconv 开关。

## 检测方法（预扫描）

源码 `configure` / `configure.ac` 中出现以下组合即应预警本条：

- `require_iconv`（或 `AM_ICONV`）**且** 分支表里无 `linux-ohos`
- `have_android_system=yes` 与 `require_iconv=no` 成对出现在 android 分支
