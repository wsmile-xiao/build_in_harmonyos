# nerdfetch 8.5.5 适配笔记

## 基本信息

- **库名称**：nerdfetch
- **版本**：8.5.5
- **上游仓库**：https://github.com/ThatOneCalculator/NerdFetch
- **许可证**：MIT
- **类型**：POSIX shell 单文件 CLI 工具
- **分支**：feat/nerdfetch-8.5.5 → nerdfetch-8.5.5

## 上游结构

上游源码根目录仅包含以下文件：
- LICENSE
- README.md
- nerdfetch（主程序，单 POSIX shell 脚本）

没有 Makefile、configure、CMakeLists.txt、test/ 目录或其他构建系统。

## 适配方案

路径 A 候选（普通基础适配），最终以官方审核为准。

### conanfile.py

- `package_type = "application"`（纯脚本应用，非库）
- 无需编译：直接下载源码包，将 `nerdfetch` 复制到 `package_folder/bin/`
- 确保可执行权限
- 不新增第三方 Conan 依赖

### test_package（smoke 测试）

1. `sh -n nerdfetch` — POSIX shell 语法检查
2. 执行 `nerdfetch -e` — 退出码 0、输出非空
3. 如输出包含当前用户名，额外断言

## 依赖

- 无第三方 Conan 依赖
- 仅使用系统基础环境：/bin/sh、uname、cat、sed、awk、printf、hostname、whoami、wc、/proc、/etc/os-release

## 路径结论

路径 A 候选，最终以官方审核为准。
---

**编译结束**: 2026-07-27 20:12
**最终状态**: built

## 关闭
