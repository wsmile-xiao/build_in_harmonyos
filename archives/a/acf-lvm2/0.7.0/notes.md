# acf-lvm2 0.7.0 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-08-12
- 编译器: 无需编译（纯 Lua 脚本 + HTML 模板分发模块）
- 状态: built

## 编译步骤

acf-lvm2 是 Alpine Configuration Framework 的 lvm2 管理模块，纯 Lua + LSP 模板，
Makefile 为安装型（无编译目标）：

```bash
make                      # 空目标 (all:)，校验 Makefile 语法
make install DESTDIR=$TEST_PREFIX   # 复制 lvm2* 到 <prefix>/usr/share/acf/app/lvm2/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 自动 URL 搜索失败 | 引擎未收录 acf-lvm2 | web 搜索定位官方源：gitlab.alpinelinux.org/acf/acf-lvm2 |
| 2 | gitlab.alpinelinux.org 下载失败 (HTTP 418) | 构建网络拦截 gitlab.alpinelinux.org | 改用 Alpine 官方 distfiles 镜像（acf-core/acf-mdadm/acf-db 同款方案） |
| 3 | init-build 双轨复制失败 (Operation not permitted) | 源码含符号链接 `lvm2-status-html.lsp -> ../status-html.lsp`（指向包外），HMDFS 下 os.link 硬链接失败、copy2 跟随链接目标不存在 | 手动 `cp -rP` 保留符号链接创建 .work 后重跑 |

## 源码修改

无补丁（纯脚本分发模块，无需平台适配）。

## 依赖版本

- acf-core/0.24.1（运行时框架依赖：mvc.lua 调度、acf.fs/acf.format）

## 验证结果

- make: 空目标正常（rc=0）
- make install DESTDIR staging: 6 个文件安装成功
- 安装布局: usr/share/acf/app/lvm2/（controller/model/menu/roles/lsp）

## 交付物

纯 Lua 模块（无二进制）：
- lvm2-controller.lua / lvm2-model.lua / lvm2.menu / lvm2.roles / lvm2-details-html.lsp / lvm2-status-html.lsp

## 注意事项

- R38 判断: 产物仅 Lua 脚本 + HTML 模板，无 bin/ 可执行文件 → 无需 commands.json
- R26 判断: acf-lvm2 非系统同名库，无静态链接需求
- 符号链接 `lvm2-status-html.lsp -> ../status-html.lsp` 指向 acf-core 提供的公共视图，属上游设计
---

**编译结束**: 2026-08-12 15:37
**最终状态**: built
