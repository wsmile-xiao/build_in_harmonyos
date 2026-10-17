# meson wrap-git 依赖版本不满足 registry：vendored subproject + nodownload 组合

## 错误特征

两类失败交替出现：

```
# 网络侧（wrap-git 下载）：
Subproject 'simdutf' is buildable: NO    # CI 无外网，wrap 下载失败
# 版本侧（想用 conan 包满足）：
meson.build: ERROR: Dependency "simdutf" version >=6.2.0 is required but found 6.0.3
```

## 根因

上游用 `subprojects/<name>.wrap`（wrap-git）管理子依赖，meson 的解析顺序是：
系统/registry dependency() → 不满足则 subproject() fallback → wrap 下载源码。
CI 无外网 + registry 版本落后 = 两头堵。但官方 release tarball 常把
`subprojects/<name>/` 完整源码（含 meson.build）预置在包内——meson 的 subproject
fallback 会直接使用这棵本地树，**不需要网络**。

## 解法（vte/0.84.1 实证）

1. `tc.project_options["wrap_mode"] = "nodownload"`——禁止任何 wrap 下载尝试；
2. requirements() **不声明**该依赖（registry 版本不满足，声明反而制造版本冲突图）；
3. 让 meson 的 dependency() → subproject() fallback 走 tarball 内 vendored 树。

验证：simdutf 8.2.0（tarball 内）零网络构建成功，simdutf 源码进入最终产物
（`subprojects/simdutf/` 编译目标正常出现在 ninja 计划 15/236）。

## 红线

- 先确认 tarball 真的预置了 `subprojects/<name>/` 源码目录（`tar -tf | grep subprojects`），
  只有 `.wrap` 文件没有源码时本方案不成立。
- nodownload 下如果 meson 仍尝试解析 wrap-git（revision 锁定），需要 patch 移除
  wrap 的 revision 字段或整个 .wrap（vte 未触发，GNOME 其他包可能触发）。
- 下游若显式 requires 了旧版本 registry 包，会把 vendored 构建顶掉——保持不声明。
