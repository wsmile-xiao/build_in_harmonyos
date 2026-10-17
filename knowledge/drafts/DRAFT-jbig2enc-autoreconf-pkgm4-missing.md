# E6404：autoreconf 无 pkg.m4 → PKG_CHECK_MODULES 未定义

## 错误特征

```
autoreconf: running: aclocal ...
autoreconf: configure.ac:123: warning: possibly undefined macro: PKG_CHECK_MODULES
autoreconf: If this token is legitimate, ... run aclocal with -I
configure: PKG_CHECK_MODULES(...): command not found
```

本地全绿、CI 一挂（本地 aclocal 目录有 pkg.m4 残留，CI 干净环境没有）。

## 根因

`PKG_CHECK_MODULES` 宏定义在 **pkg.m4**（pkg-config 工具链文件），不属于 automake/libtool。OHOS autotools 工具链不带，aclocal 搜索路径无果即生成失败。

## 解法（见 .kv solution 代码）

1. `tool_requires` 补 `pkgconf/3.0.5`（share/aclocal/pkg.m4 权威来源）
2. build() 把 pkg.m4 拷入源码树 `m4/`（aclocal 默认搜索位）
3. `autoreconf -fi` 后宏可拾取；configure 阶段 `PKG_CONFIG_PATH` 指 conan PkgConfigDeps generators

## 降级方案

无 pkgconf 包：静态 pkg.m4 随 PR 分发（license 宽松）解出到 m4/。

## 同族坑（同一 PR 三连）

- **E074**：HMDFS 上 make jobserver fifo EPERM → `make -j1` 规避
- **umask 077→022**：kexec-tools 2.0.32 先例（HMDFS mktemp setgid 拒写）

## 实证

PR #12103 jbig2enc 0.32（leptonica 1.85.0 六格式链消费验证）。
