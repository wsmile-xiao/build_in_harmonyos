# changetrack — 配置文件变更监控工具

## 基本信息

| 项目 | 值 |
|------|-----|
| 名称 | changetrack |
| 版本 | 4.7 |
| 许可证 | GPL-2.0+ |
| 语言 | Perl（纯脚本，无编译） |
| 构建系统 | makefile（仅 test/install 两 target） |
| 描述 | Monitors changes to configuration files and keeps revision history |

## 编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 4.7 | built | 2026-09-07 |

## 功能概述

- 监控配置文件列表（`~/.changetrackrc` 或 `-c` 指定），定时（通常 crontab）运行
- 检测文件内容/权限/属主变化，输出人可读变更日志（`.history`）与统计（`.statistics`）
- `-e` 生成 ed 脚本（依赖 GNU `diff -e`），可回放修改
- 配合 RCS 套件（co/ci/rcs）保存任意历史版本供恢复；`-r` 可禁用 RCS 仅保留监控/日志

## OHOS 适配

- 纯 Perl 脚本，无 configure/编译步骤；shebang 修改：`#!/usr/bin/perl` → `#!/usr/bin/env perl`（鸿蒙 `/usr/bin/perl` 不存在）
- 运行期依赖 PATH 中的 perl（>=5，核心模块即可）与 GNU diffutils 的 `diff`：
  **toybox 0.8.12 的 diff 不支持 `-e`**，必须保证 GNU diffutils 先于 toybox（CI profile buildenv PATH 已前置设备 GNU 用户态目录）
- RCS 套件经 conan 依赖 `rcs/5.10.1` 提供（bindirs 进入消费方 PATH）；RCS 检查需要非空 LOGNAME
- 上游 `make test` 为环境检查（which perl + perl 模块 + `rcs -V`），接入 rcs 后 7/7 通过
- 上游 `make install` 硬编码 `/usr/local`、`/etc`，不可直接使用，由 conanfile.py 手工打包
  （bin + man + 示例 conf）

## 依赖关系

- conan 依赖：rcs/5.10.1（版本存储后端，运行期调用 co/ci/rcs）
- 运行依赖（PATH 解析）：perl（设备工具链用户态自带）、GNU diffutils（archives/d/diffutils，设备工具链用户态自带）
- 无编译依赖

## 参考资料

- 主页：http://changetrack.sf.net （SourceForge 仅发布到 4.5）
- 4.7 权威发布物：Debian pool `changetrack_4.7.orig.tar.gz`（与 `changetrack_4.7-11.dsc` 一致）
