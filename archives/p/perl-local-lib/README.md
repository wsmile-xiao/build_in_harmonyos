# perl-local-lib

## 软件描述

local::lib - Create and use a local lib/ directory for Perl modules.

纯 Perl 模块，用于创建和管理本地 Perl 模块安装目录，无需系统级权限。

## 版本列表

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 2.000029-r0 | built | 2026-06-13 | 纯 Perl 模块，无二进制依赖 |

## 特性说明

- **类型**：纯 Perl 模块（Pure Perl）
- **构建系统**：perl Makefile.PL
- **依赖**：无外部依赖，仅需 Perl 环境
- **产物**：Perl 模块文件（.pm/.pod）

## 使用场景

1. 用户级 Perl 模块安装
2. 避免系统级权限需求
3. 创建隔离的 Perl 环境
4. 配合其他 Perl 模块管理本地依赖路径

## 验证状态

- ✅ 功能测试通过（2026-06-15）
- ✅ 质量门禁 G1-G4 通过
- ✅ 平台兼容性验证完成
- ✅ 适合上库发布

## 编译注意事项

1. 使用 `PREFIX` 参数指定安装路径
2. 无 `make check` 测试目标
3. 无二进制可执行文件（纯 Perl）
4. DESTDIR 模式正常工作