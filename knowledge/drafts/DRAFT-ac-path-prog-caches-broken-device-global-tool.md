# DRAFT-ac-path-prog-caches-broken-device-global-tool：AC_PATH_PROG 缓存设备全局目录的坏 glib-mkenums（shebang 硬编码 /usr/bin/perl → Error 126）——钉环境变量是根治点

> Contributor: GoliWie | Status: Draft | Updated: 2026-09-27
> Source: libido3 13.10.0 适配（触发于 CI round 9 的 glib-mkenums 探测失败）
> 对应：`knowledge/drafts/DRAFT-ac-path-prog-caches-broken-device-global-tool.kv`

## 现象

configure 阶段看似正常，make 期在生成枚举文件时突然失败：

```text
checking for glib-mkenums... /data/service/hnp/bin/glib-mkenums
...
/data/service/hnp/bin/bash: /data/service/hnp/bin/glib-mkenums:
/usr/bin/perl: bad interpreter: No such file or directory
make: *** [idotypebuiltins.h] Error 126
```

*迷惑点*："No such file or directory" 指向的是**解释器** `/usr/bin/perl`，不是脚本本身；设备上 perl 存在（`/data/service/hnp/bin/perl`），只是包装脚本的 shebang 写死了不存在的 `/usr/bin/perl`。事后把依赖包的 bin 目录 prepend 进 PATH 也无效——configure 已经把坏工具缓存进 Makefile 规则。

## 根因（三重组合，L1 平台保证复发面）

1. **设备全局工具目录遮蔽**：`/data/service/hnp/bin`（hnp 包管理安装面）位于 PATH 前部，内含 glib-mkenums 等脚本工具。
2. **shebang 硬编码解释器**：包装脚本首行 `#! /usr/bin/perl`，而设备解释器实际在 hnp 路径；exec 对缺失解释器报 ENOENT（"bad interpreter"）。
3. **AC_PATH_PROG 缓存动力学**：configure 在全局目录先命中即缓存进生成的 Makefile；make 期枚举规则执行缓存路径才爆 Error 126——"配置绿、构建红"的时序陷阱。

## 影响面

任何在 OHOS 设备上跑 autotools configure 并以 AC_PATH_PROG 探测脚本工具的项目：glib-mkenums、gdbus-codegen、glib-compile-resources、glib-genmarshal 等；GNOME/glib 家族几乎全覆盖。

## 修复范式

*首选：钉环境变量*（rec：pin-tool-env-var-ac-path-prog）。AC_PATH_PROG 类宏 honour 预设环境变量——generate() 里探测依赖包内真实脚本并钉死：

```python
env.define("GLIB_MKENUMS", <glib 包内 bin/glib-mkenums 绝对路径>)
# 同族：GDBUS_CODEGEN / GLIB_COMPILE_RESOURCES / GLIB_GENMARSHAL
# 同时把 dep bin 目录加进构建 PATH（make 期兜底）
```

实落参考：`archives/l/libido3/13.10.0/conanfile.py` 的 `_find_glib_mkenums` 与 generate() 内 GLIB_MKENUMS 钉定段（本条知识即出自该 run）。

*备选（fallback：fixed-name-shim-dir-first-on-path）*：为脚本工具建固定名 shim 目录（内容 `exec 真实脚本`）prepend 到 PATH。诚实权衡：只管住 PATH 解析面，对不查 PATH 的 configure 片段无效；每工具逐一建 shim，维护面更大。

*禁止项*：

- 删除/改写设备全局 `/data/service/hnp/bin` 下的工具——污染全局状态、不可复现、连带同机其他任务；
- 只调 PATH 顺序而不钉环境变量——AC_PATH_PROG 缓存首个命中，hnp 目录先于 conan env prepend 生效时仍命中坏工具，make 期 Error 126 复现。

## 验证（设备新 shell 可复跑，全只读）

```sh
p=$(command -v glib-mkenums); echo "resolved=$p"
# 实测：resolved=/data/service/hnp/bin/glib-mkenums
head -1 "$p"
# 实测输出：#! /usr/bin/perl
command -v perl
# 实测输出：/data/service/hnp/bin/perl ← 设备有 perl，坏的是 shebang 路径
glib-mkenums --version 2>&1; echo "rc=$?"
# 实测输出：sh: /data/service/hnp/bin/glib-mkenums: No such file or directory
```

修复方向验证：GLIB_MKENUMS 钉到 conan glib 包内真实脚本后重新 configure，config.log 中 `checking for glib-mkenums` 应解析到包内路径。

## 查重与关系

graph 概念级近邻（`-E` 修正检索后如实列入）：

- **E443**（Autotools bootstrap 闭包）：trigger_tool 同含 glib-genmarshal|glib-mkenums；机理面是 HMFS cross-UID 拒绝直接 shebang 执行 + 安装期 prefix 重定位，失效机理与来源均不同；其 fallback（工具变量直指固定解释器+包内脚本）与本条 rec 同族。E443 已列 ACLOCAL/AUTOMAKE 等变量但未列 GLIB_MKENUMS。
- **E527**（gtk broadway + glib 工具 native 包装，meson 场景）：同为"glib 构建期脚本工具在 OHOS 不可直接执行"族，未覆盖 AC_PATH_PROG 缓存/遮蔽面。
- **E348**：pkg-config 工具面，仅语境相邻。
- drafts 近邻：DRAFT-buildtime-tool-dep-blocks-adaptation-scan-ac-path-tool（开工前扫描面）。

本条独立价值：**AC_PATH_PROG 缓存动力学 + 设备全局 hnp 目录遮蔽 + shebang 硬编码解释器**三者的具体组合，以及 GLIB_MKENUMS 这一具体预设变量落点（"configure 缓存坏工具后 make 期才爆"的时序陷阱）。

相关：E443、E527、E405（posix_spawn 不搜 PATH）、E002（TMPDIR 重定向——环境钉法族）；原则 P-ENV-001。
