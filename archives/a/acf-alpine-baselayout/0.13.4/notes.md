# acf-alpine-baselayout 0.13.4 适配笔记

## 1. 软件概要
- Alpine Configuration Framework（ACF）的 alpine-baselayout 应用模块，
  Web 方式管理系统主机名/网络接口/cron/健康检查/syslog/rc/密码等。
- 纯 Lua 项目：顶层 Makefile 将 Lua controller/model、HTML 视图（.lsp）、
  菜单（.menu）和角色（.roles）复制到 `share/acf/app/alpine-baselayout`，
  无 C 编译，`make all` 为空操作，`make install DESTDIR=...` 仅复制文件。
- 上游官方源（aports APKBUILD 同款 tag）：
  `https://gitlab.alpinelinux.org/acf/acf-alpine-baselayout/-/archive/v0.13.4/acf-alpine-baselayout-v0.13.4.tar.gz`
  构建网络对 gitlab.alpinelinux.org 返回 418，改用 Alpine distfiles 官方镜像
  `https://distfiles.alpinelinux.org/distfiles/v3.24/acf-alpine-baselayout-v0.13.4.tar.gz`
  （与 acf-db/acf-core 先例一致），SHA256 与 gitlab 官方 tarball 完全一致：
  `c15acb4cda985a3530e70e1df898be940a507dd8d0a83b234d62dfd1d44eac82`

## 2. 编译说明
- 无 configure 脚本；config.mk 硬编码 `prefix=/usr`、`appdir=${datadir}/acf/app`。
- `make -j1 all`：`all:` 为空目标，验证 Makefile 语法。
- `make install DESTDIR=<pkg>`：安装到 `<pkg>/usr/share/acf/app/alpine-baselayout`，
  共 46 个文件 + 9 个 .lsp 符号链接（指向框架级视图，保持上游结构原样）。
- **无平台补丁**：Makefile install 只用 `mkdir -p` + `cp -a`，
  不依赖 OHOS 缺失的 coreutils `install` 命令（对比 acf-core 需要 bin/Makefile 补丁）。

## 3. 外部 Lua 模块依赖分析（R18 流程）
acf-alpine-baselayout 运行时 require 的外部模块：

| 模块 | 出现次数 | 提供方 | 处理 |
|------|----------|--------|------|
| `acf.fs` | 10 | acf-core 包 share/acf/lib | acf-core/0.24.1 依赖覆盖 |
| `modelfunctions` | 8 | acf-core 包 share/acf/lib | 同上 |
| `acf.format` | 6 | acf-core 包 share/acf/lib | 同上 |
| `posix` | 5 | luaposix（lua 5.4 兼容版未发布） | 运行时由 ACF 运行环境提供；本配方不声明 |
| `acf.validator` / `acf.processinfo` / `acf.date` | 各 1-2 | acf-core 包 share/acf/lib | acf-core 依赖覆盖 |
| `alpine-baselayout/interfaces-definitions` | 1 | 本包内文件 | 包内相对引用 |

**结论**：框架级模块（acf.*、modelfunctions）由 acf-core 包提供，配方声明
`self.requires("acf-core/0.24.1")`（与已合入的 acf-db/0.24.1 写法一致）。
posix 等系统级 Lua 模块由目标平台的 ACF 运行环境提供，不属于本包构建依赖。

## 4. 上游测试
- 上游**无测试套件**：Makefile 无 `check`/`test` 目标；源码无 test/ 目录；
  aports acf-alpine-baselayout APKBUILD 与 acf-core/acf-db 同家族，未声明测试。
- 上游用例数记录为 0，验证采用自建消费者测试（详见 test_package/ 与 reports/）。

## 5. 运行约束
- 本应用模块由 acf-core 框架（mvc.lua）dispatch，独立运行需完整 ACF 运行环境
  （含 posix/subprocess 等系统 Lua 模块），故消费者测试以
  包完整性 + Lua 5.4 语法校验 + 角色/菜单内容验证为准（同 acf-db 先例）。

## 6. 状态
- 编译：成功；消费者测试：通过；conan-verify：见 reports/conan-verify-report.md。
---

**编译结束**: 2026-08-12 22:13
**最终状态**: built
