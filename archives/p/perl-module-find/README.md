# perl-module-find

Module::Find — Find and use installed modules in a (sub)category.

## 简介

Module::Find 让你按类别查找和使用 Perl 模块，非常适合自动发现驱动或插件模块。支持区分查找直接子模块或递归查找所有子模块。

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 0.17 | published | 2026-06-18 |

## 主要功能

- `findsubmod` — 查找直接子模块
- `findallmod` — 递归查找所有子模块
- `usesub` — 加载并使用直接子模块
- `useall` — 递归加载所有子模块
- `setmoduledirs` — 自定义模块搜索路径
- `followsymlinks/ignoresymlinks` — 符号链接跟随控制

## 鸿蒙平台适配

- 纯 Perl 模块，无需 C 编译器，开箱即用
- 无 XS/C 代码，不存在 SELinux/HMDFS 权限限制
- taint 模式下需通过 `-I` 参数指定安装路径
- Perl 5.42.0 完全兼容
