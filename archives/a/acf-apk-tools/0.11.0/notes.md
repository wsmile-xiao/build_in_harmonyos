# acf-apk-tools 0.11.0 适配笔记

## 编译环境
- 构建系统: makefile（单一递归 Makefile, 纯 Lua 无 C 编译）
- 编译日期: 2026-08-13
- 编译器: clang/clang++（未使用, 纯 Lua 模块）
- 状态: built

## 编译步骤

acf-apk-tools 是 Alpine Configuration Framework 的 apk-tools（Alpine 包管理器）管理模块。
纯 Lua 实现, 无 C 源码, 无 configure 脚本。

1. `make -C <src> -j1 all` — Makefile 的 `all:` 目标为空操作, 仅验证 Makefile 语法
2. `make -C <src> install DESTDIR=<pkg> -j1` — 复制 apk-controller.lua, apk-model.lua,
   apk.menu, apk.roles + 5 个 HTML 视图模板 (.lsp) 到 `<pkg>/usr/share/acf/app/apk-tools/`

config.mk 定义 `prefix=/usr`, `appdir=${datadir}/acf/app` (即 `usr/share/acf/app`).

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitLab 418 拦截 Conan/urllib 下载器 | gitlab.alpinelinux.org 对非 curl UA 反爬虫 | 先用 curl 下载 tarball，再按 sha256 预置 conan 源码缓存 `core.sources:download_cache` |
| 2 | conan-init 生成 autotools 模板 | ohc 对 makefile 软件猜测为 autotools | 参照 acf-nsd 0.0.1 recipe 重写为纯 Lua makefile 配方（make all + make install DESTDIR） |

## 源码修改

无补丁。acf-apk-tools 的 Makefile 仅用 `cp -a` 复制文件（与 acf-nsd 相同）。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| acf-core | 0.24.1 | 运行时框架依赖 (mvc.lua dispatch) |

## 验证结果

```
conan create archives/a/acf-apk-tools/0.11.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
→ test_package: PASS=20 FAIL=0
  ✅ file exists: apk-controller.lua / apk-model.lua / apk.menu / apk.roles
  ✅ file exists: apk-available-html.lsp / apk-details-html.lsp / apk-expert-html.lsp / apk-loaded-html.lsp
  ✅ non-empty: 8 files
  ✅ controller has expected content / model has apk-tools integration
  ✅ lua syntax OK: apk-controller.lua / apk-model.lua (luac 可用时)

conan-verify: G0-G4 + L2/L4/L5 all PASS
```

## 注意事项

- 纯 Lua 模块, 无二进制产物, 无 commands.json（R38 不适用）
- 上游无测试套件（aports `options="!check" # no test suite`）, test_package 采用自建功能测试
- apk-dependent-html.lsp / apk-toplevel-html.lsp 与 apk-available-html.lsp 内容相同（上游预期行为, 软链接在解包时被物化为普通文件）
- 运行时还需 lua-posix 与 apk-tools（aports depends），由 OS 镜像提供，不在 conan 依赖链内
---

**编译结束**: 2026-08-13 12:50
**最终状态**: built
