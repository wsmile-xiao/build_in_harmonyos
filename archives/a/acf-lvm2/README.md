# acf-lvm2

Alpine Configuration Framework（ACF）的 LVM2 管理模块 —— 基于 Web 的 LVM（逻辑卷管理）管理界面。

## 简介

- 上游仓库：https://gitlab.alpinelinux.org/acf/acf-lvm2
- 构建系统：Makefile（纯 Lua 脚本 + HTML 模板分发模块，无 C 编译）
- 产物：`lvm2-controller.lua` / `lvm2-model.lua` / `lvm2.menu` / `lvm2.roles` / `lvm2-details-html.lsp` / `lvm2-status-html.lsp`
- 安装布局：`/usr/share/acf/app/lvm2/`

## OpenHarmony 适配说明

- 纯脚本分发模块，无编译、无平台适配补丁
- 运行时依赖 `acf-core`（mvc.lua 调度、acf.fs/acf.format）
- 源码获取：Alpine 官方 distfiles 镜像（`distfiles.alpinelinux.org`，gitlab.alpinelinux.org 在构建网络被 418 拦截）
