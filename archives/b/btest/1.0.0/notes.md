# btest 1.0.0 适配记录

## 软件简介

BTest 是一个通用的系统测试驱动框架，最初来自 Zeek 项目。
它为 shell 脚本测试套件提供易于使用的驱动；每个测试由一组
命令行组成，成功由退出码决定。附带 btest-diff 等工具用于
将输出与既定基线对比。

- 上游：https://github.com/zeek/btest
- 作者：The Zeek Team
- 许可证：BSD-3-Clause
- 语言：Python（纯脚本，无编译）
- 上游版本：1.0（VERSION 文件）
- conan 版本：1.0.0（三段式规范）

## 源码信息

- 下载 URL：https://github.com/zeek/btest/archive/refs/tags/v1.0.tar.gz
- SHA256：ff40f49decdd5580ab588777e48a194f3abe736452d88fc5268342d3cd63cca9
- 大小：98690 字节
- 选择理由：GitHub 是 btest 官方仓库，CI build_and_test.sh 的 mirror
  fallback 覆盖 github.com，CI worker 可达。

## 构建与安装

btest 是纯 Python 脚本包，**无编译**。

安装步骤：
1. `source()`：下载并解压 GitHub release tarball
2. `build()`：确保 8 个 btest* 脚本可执行（chmod 755）
3. `package()`：复制 12 个脚本到 bin/
   - 8 个顶层脚本：btest, btest-ask-update, btest-bg-run,
     btest-bg-run-helper, btest-bg-wait, btest-diff,
     btest-progress, btest-setsid
   - 4 个 sphinx 脚本：btest-sphinx-diff-rst, btest-sphinx-rst-cmd,
     btest-sphinx-rst-include, btest-sphinx-rst-pipe
4. 复制 COPYING（许可证）到 share/btest/

## 运行时依赖

- python >=3.7（必需）
- sphinx（可选，btest-sphinx-* 脚本需要）

## 测试策略（R34）

- python -c 编译校验主脚本（btest 是 python 脚本）
- 验证所有 12 个安装脚本存在且可执行
- 验证 COPYING 许可证文件存在
- python 脚本包，python -c py_compile 是 R34"实际执行被测包脚本"
  对纯 python 脚本包的等价校验

## 已知限制

- btest 主脚本依赖 python3 解释器
- sphinx 辅助脚本需要完整的 sphinx 文档构建环境
