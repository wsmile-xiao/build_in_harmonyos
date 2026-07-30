# gsan 5.0.0 OpenHarmony PC 适配困难分析报告

## 1. 问题概述

gsan 5.0.0 是一个用于扫描 TLS 证书 Subject Alternative Name（SAN）的 Python 命令行工具。上游源码可以在常规桌面 Python 环境中运行，但直接纳入 OpenHarmony PC 三方库包图时存在运行时依赖不可获得、命令行入口依赖外部框架以及测试覆盖缺失等问题。

本报告针对 gsan 5.0.0 的部分适配困难进行根因分析，记录已尝试方案、验证结果和最终适配方案。

## 2. 根因分析

### 2.1 运行时依赖不在当前 OpenHarmony 包图中

上游 `pyproject.toml` 声明以下运行时依赖：

- `typer`
- `rich`
- `pyasn1`
- `cryptography`
- `pyOpenSSL`

仓库当前 Conan 配方中没有上述 Python 运行时库的可用依赖链。继续在配方中通过 pip 安装会引入以下问题：

1. 构建过程依赖外网和 PyPI 服务，不符合自包含的 OpenHarmony 包构建要求。
2. `cryptography` 可能进一步触发 Rust 或本地扩展构建，增加 OpenHarmony 交叉编译复杂度。
3. `pyOpenSSL` 和 `pyasn1` 只被用于证书读取和 SAN 解码，实际使用范围较小，依赖成本明显高于功能本身。

### 2.2 CLI 入口依赖 Typer

上游通过 Typer 定义命令行参数、帮助信息和选项。当前包图没有 Typer，因此即使核心 Python 代码被安装，`gsan` 命令入口仍无法启动。

### 2.3 上游没有正式测试用例

对 `gsan-5.0.0.tar.gz` 进行源码检查后，未发现 `tests/` 目录、pytest 测试、unittest 测试或其他自动化测试入口。没有测试基线会导致适配后无法证明 SAN 解析、端口解析和失败处理行为保持正确。

## 3. 已尝试方案及结果

### 方案一：直接保留上游第三方依赖

- **做法**：在 Conan 配方中安装 `typer`、`rich`、`pyasn1`、`cryptography` 和 `pyOpenSSL`。
- **结果**：当前 OpenHarmony Conan 包图无法提供完整依赖链；构建会依赖 pip 和网络，也无法保证 `cryptography` 的本地扩展在目标平台可用。
- **结论**：不采用。

### 方案二：只替换 CLI 框架

- **做法**：将 Typer 替换为 `argparse`，保留 `pyOpenSSL` 和 `pyasn1`。
- **结果**：命令行可以脱离 Typer 启动，但证书获取和 SAN 解码仍然依赖包图中不存在的第三方库。
- **结论**：不能解决根本问题。

### 方案三：使用 Python 标准库完成完整替代

- **做法**：
  - 使用 `argparse` 替代 Typer。
  - 使用标准输出替代 Rich 输出和进度显示。
  - 使用 `ssl.SSLSocket.getpeercert()` 获取证书 SAN 字典。
  - 从证书字典的 `subjectAltName` 字段直接解析 DNS 和 IP 地址。
  - 使用 `ipaddress` 标准化 IP 地址。
  - 将运行时依赖列表置为空，并保留原有扫描、清洗和 JSON 输出逻辑。
- **结果**：适配后的程序不再依赖上述五个第三方运行时库，可以通过 Conan 配方自包含打包。
- **结论**：采用该方案。

## 4. 最终适配方案

1. 增加 `0001-use-python-stdlib.patch`，集中记录对上游源码的最小修改。
2. Conan 配方将 Python 模块安装到 `lib/gsan`，并生成 `bin/gsan` 启动脚本。
3. `package_info()` 导出 `PATH` 和 `PYTHONPATH`，方便消费者直接调用 CLI 和导入模块。
4. 增加 `--version` 参数，方便包安装后的版本确认。
5. 对默认端口、显式端口、方括号 IPv6 地址进行统一解析。
6. 增加离线证书夹具和消费者测试，避免测试依赖公网证书服务。

## 5. 验证证据

### 构建和打包

- Conan 配方检查：通过。
- 补丁检查：`git apply --check` 通过。
- 本地 Conan 离线构建：通过。
- package step：通过，成功生成 Python 模块、许可证文件和 `gsan` 启动脚本。
- test_package：通过。

### 测试结果

新增 10 个断言，全部通过：

1. 从证书夹具中提取 DNS SAN。
2. 从证书夹具中提取 IP SAN。
3. 清理通配符和 `www.` 前缀并去重。
4. 解析显式主机名端口。
5. 使用默认 443 端口。
6. 解析方括号 IPv6 地址。
7. 验证 `--version` 输出。
8. 验证 `--help` 输出。
9. 验证连接失败不会导致 CLI 崩溃。
10. 验证 JSON 输出中的失败域名列表。

测试结果：`10/10（100%）`。

## 6. 结论和复用价值

该问题不是单个 API 的临时修补，而是“Python 工具三方依赖不可获得”这一类 OpenHarmony 适配问题的代表。报告给出了从依赖盘点、替代方案比较到标准库落地和离线验证的完整方法，可复用于其他纯 Python CLI 工具的 OpenHarmony 适配。