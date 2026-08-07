# lice5 5.3.0 适配笔记

## 编译环境
- 构建系统: 无（纯脚本资源包）
- 编译日期: 2026-07-19（首次创建 Conan 配方）
- 编译器: 不适用
- 状态: built

## 软件说明

LiCe 是为 ircII 和 EPIC IRC 客户端设计的功能增强脚本。它通过提供丰富的
功能（用户列表、频道管理、DCCLIST、自动忽略、主题等）极大地改善了这些
IRC 客户端的可用性。

lice5 是该脚本的 Debian 打包版本，适用于 epic5 IRC 客户端。

## 源码结构

源码 tarball 解压后包含以下目录：
- `lice/` — 主脚本文件（约 100 个 lice.* 脚本，包括 lice.epic5 主入口）
- `help/user/` — 用户帮助文档
- `logos/` — ASCII 艺术 logo（5 个）
- `pics/` — ASCII 艺术图片（约 50 个）
- `themes/` — 主题文件（约 22 个）
- `userhelp/` — ULW（User List Window）帮助文档

## 适配步骤

```bash
# 1. 下载源码（conan source 自动完成）
# 2. 无需编译，直接复制脚本文件到包目录
# 3. 安装到 share/lice5/ 下，保持目录结构
```

## 适配决策

| # | 决策 | 原因 |
|---|------|------|
| 1 | package_type = "application" | 仓库中纯脚本包的标准做法（参考 chruby、zsh-autopair） |
| 2 | settings = ("os", "arch") | 无需 compiler/build_type（无编译） |
| 3 | package_id 调用 self.info.clear() | 纯脚本包，所有配置下内容完全相同 |
| 4 | 脚本安装到 share/lice5/ | 非 bin/（脚本由 epic5 加载，不是直接执行的命令） |
| 5 | 无 commands.json | R38：lice5 不是命令行工具，无可执行入口 |
| 6 | 无 patches | 源码无需修改即可使用 |

## 平台兼容性

- 无 C/C++ 代码，无 ELF 二进制
- 脚本由 epic5 解释执行，与底层平台无关
- 无 shebang 需要改写（脚本不直接执行）
- R26（静态链接）不适用

## 验证结果

```bash
# test_package: 验证脚本文件存在性和完整性
# - 检查 lice/lice.epic5 主脚本存在
# - 检查 themes/ 目录非空
# - 检查 help/user/ 目录非空
# - 统计脚本文件总数
```

## 依赖

- epic5 (>= 1.1.2) — 运行时依赖（非编译依赖）

---

**适配完成**: 2026-07-19
**最终状态**: built
**conanfile.py 创建日期**: 2026-07-19
