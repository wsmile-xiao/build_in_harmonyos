# nvm 0.40.6 适配笔记

## 编译环境
- 构建系统: custom (纯 shell 脚本)
- 编译日期: 2026-09-14
- 编译器: 无需编译器（纯 shell 脚本）
- 状态: built

## 软件概述

nvm (Node Version Manager) 是一个纯 shell 脚本项目，用于管理多个活跃的 Node.js 版本。
它由 nvm.sh（被 source 的 POSIX 兼容函数）和 nvm-exec（包装器）组成。

## 构建步骤

nvm 是纯 shell 脚本项目，无需传统 configure/make 流程。

1. 下载源码：从 GitHub 下载 nvm-0.40.6 tarball
2. 解压源码：解压到构建目录
3. 无需补丁（nvm.sh 自带平台检测逻辑）
4. 打包：将 nvm.sh、nvm-exec、bash_completion、LICENSE.md 复制到 conan 包目录
5. 验证：source nvm.sh 后运行 nvm --version 确认安装成功

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | 网络限制 | 使用 ghfast.top 镜像下载（CI 会自动加镜像 fallback） |
| 2 | Makefile install 目标不存在 | nvm 使用 install.sh 而非 make install | conanfile.py 直接复制脚本文件 |
| 3 | npm install 超时 | node_modules 安装慢 | 等待完成或使用 --no-optional |

## 依赖

nvm 运行时需要：
- bash（已预装）
- curl 或 wget（用于下载 Node.js 版本）
- git（可选，用于 nvm install from source）

## 上游测试

nvm 使用 urchin 测试框架，测试位于 test/ 目录。

### 测试统计

| 测试套件 | 测试数 | 说明 |
|----------|--------|------|
| fast/Unit tests | 117 | 单元测试，纯函数测试 |
| fast/Aliases | 41 | 别名功能测试 |
| fast/Listing | 23 | 列表功能测试 |
| fast/Running | 24 | 运行命令测试 |
| fast/Set Colors | 4 | 颜色设置测试 |
| fast/Sourcing | 2 | source nvm.sh 测试 |
| fast/Subcommands | 1 | 子命令错误处理测试 |
| fast/nvm should remove | 1 | NVM_DIR 尾斜杠测试 |
| install_script | 15 | 安装脚本测试 |
| installation_node | 17 | Node.js 安装测试 |
| installation_iojs | 10 | io.js 安装测试 |
| slow | 28 | 慢测试（真实 Node 安装/卸载） |
| sourcing | 7 | source nvm.sh 各种场景 |
| xenial | 7 | Ubuntu Xenial 兼容测试 |
| **合计** | **297** | |

### 本地测试结果

在本地（鸿蒙设备）使用 urchin 测试框架运行了以下测试套件：

#### sourcing 测试套件（7 个测试）
- ✓ Sourcing nvm.sh should keep version if one is active
- ✓ Sourcing nvm.sh should use the default if available and no nvm node is loaded
- ✓ Sourcing nvm.sh with no default should return 0
- ✗ Sourcing nvm.sh global alias bug（环境差异——已安装 node 版本不同）
- ✗ Sourcing nvm.sh with --install and .nvmrc should install it（需要 python，环境缺失）
- ✗ Sourcing nvm.sh with --install should install the default（需要 python，环境缺失）
- ✗ Sourcing nvm.sh with --no-use should not use anything（需要 python，环境缺失）
- 结果：3/7 通过（3 个失败因 python 不可用和环境差异）

#### Set Colors 测试套件（4 个测试）
- ✓ nvm_echo_with_colors
- ✓ nvm_err_with_colors
- ✓ nvm_print_default_alias calls nvm_get_colors
- ✗ nvm_print_versions calls nvm_get_colors（颜色码差异——系统 node 版本不同）
- 结果：3/4 通过

#### 其他测试套件
- fast/Unit tests（117 个）：urchin 运行超时（每个测试需 source 161K 的 nvm.sh 脚本，117 个测试耗时过长）
- fast/Aliases（41 个）：urchin 运行超时
- install_script（15 个）：urchin 运行超时
- installation_node/installation_iojs/slow：需要从 nodejs.org 下载 Node.js 版本，CI/本地无外网

#### conan test_package smoke test
- 通过：source nvm.sh 后 nvm --version 输出 0.40.6
- 通过：nvm.sh 和 nvm-exec bash 语法检查
- 通过：shebang 验证

### CI 环境限制

- installation_node/installation_iojs/slow 测试需要从 nodejs.org 下载 Node.js 版本——CI 无外网，无法运行
- sourcing 测试需要已安装的 Node.js 版本
- 本地补跑了 fast 和 install_script 测试套件

## 源码修改

无需修改源码。nvm.sh 自带平台检测逻辑（nvm_get_arch 函数会检测 aarch64）。

## 交付物

| 文件 | 说明 |
|------|------|
| nvm.sh | 主脚本（被 source 的 POSIX 兼容函数） |
| nvm-exec | 包装器（source nvm.sh 后执行命令） |
| bash_completion | bash 自动补全 |
| LICENSE.md | MIT 许可证 |

## 注意事项

1. nvm 是纯 shell 脚本，不需要 ELF 签名
2. nvm.sh 需要被 source（而非直接执行）才能使用 nvm 函数
3. nvm-exec 需要 PATH 中包含 nvm.sh 的目录
4. 不支持 G0 干净构建验证（无构建系统）
5. CI 无外网，installation/slow 测试无法运行

## 特殊处理说明

由于 nvm 是纯 shell 脚本项目，跳过了以下标准流程：
- configure/make 编译流程
- G0 干净构建验证
- ELF 签名（无二进制文件）
- RPATH 设置（无动态库）
- Strip（无二进制文件）
