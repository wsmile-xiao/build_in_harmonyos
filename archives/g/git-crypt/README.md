# git-crypt

git-crypt 是一个透明的 Git 文件加密工具，允许在 Git 仓库中加密文件，只有授权用户才能解密查看内容。

## 功能概述

- **透明加密**: 在 Git 工作流中自动加密/解密文件
- **基于 GPG**: 使用 GPG 密钥进行加密，支持多用户协作
- **对称加密**: 支持对称密钥模式，简化密钥管理
- **文件过滤**: 通过 .gitattributes 配置需要加密的文件

## OHOS 适配

### 适配要点

- git-crypt 使用简单的 Makefile 构建系统，无需 configure 步骤
- 依赖 OpenSSL 库和 Git，需要确保这些依赖已安装
- 编译时使用 `make ENABLE_MANPAGE=no` 跳过手册页生成（需要额外工具）
- G0 干净构建验证可能遇到 Python subprocess 平台限制，需手动验证二进制格式

### 已知问题

- 暂无

### 与 Linux 的差异

- 编译流程与 Linux 基本一致
- 需要确保 OpenSSL 和 Git 的鸿蒙版本已安装

## 依赖关系

### 编译依赖

- OpenSSL (开发包)
- Git

### 运行依赖

- OpenSSL
- Git
- GPG (用于密钥管理)

## 参考资料

- 官方网站: https://www.agwa.name/projects/git-crypt/
- GitHub 仓库: https://github.com/AGWA/git-crypt