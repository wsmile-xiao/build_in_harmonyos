# terraform-local homebrew — 编译笔记

## 基本信息
- 软件: terraform-local (tflocal)
- 版本: 0.26.0 (homebrew/main branch)
- 来源: https://github.com/localstack/terraform-local
- 类型: Python 脚本（非 Go 工具）
- 描述: Thin wrapper around terraform CLI for use with LocalStack

## 编译过程

### Step 1: init-build
- 从 GitHub 下载源码 tarball
- 源码解压到 $BUILD_SRC_DIR

### Step 2: 依赖安装
terraform-local 是 Python 项目，依赖以下 Python 包：
- localstack-client 2.11
- python-hcl2 8.1.2
- boto3 1.43.34
- botocore 1.43.34
- s3transfer 0.9.0
- jmespath 1.1.0
- lark 1.3.1
- regex 2026.5.9
- packaging (已安装)
- python-dateutil (已安装)
- urllib3 (已安装)
- six (已安装)

**注意**: pip 因 SSL 证书问题无法使用，采用手动下载 wheel 并解压到 site-packages 的方式安装。
regex 的 C 扩展 (.so) 需要 ELF 签名才能在 OpenHarmony 上执行。

### Step 3: 源码修改
- 修改 bin/tflocal 的 shebang: `#!/usr/bin/env python` → `#!/usr/bin/env python3`
- 原因: 系统 `python` 指向 Python 3.9，而依赖安装在 Python 3.14 环境下

### Step 4: 安装
- 复制 tflocal 到 staging 目录 ($TEST_PREFIX/$DEFAULT_PREFIX/bin/)
- 复制 tflocal 到本地安装目录 ($DEFAULT_PREFIX/bin/)

### Step 5: 验证
- tflocal --version: terraform-local v0.26.0 + Terraform v1.15.6 on linux_arm64
- tflocal --help: 正常显示 terraform 帮助信息

### Step 6: 打包
- 使用 ohc-run.py package 创建预编译包
- 产物: terraform-local-homebrew-ohos-aarch64.tar.gz (29KB)

## 关键发现
1. terraform-local 是 Python 项目，不是 Go 项目（与任务描述不符）
2. pip 在当前环境因 SSL 证书问题不可用，需手动下载 wheel 安装
3. regex C 扩展需要 ELF 签名
4. shebang 需要从 `python` 改为 `python3`
5. tflocal 依赖 terraform CLI 运行，已安装 terraform 1.15.6

## 最终状态
- 编译状态: published
- 预编译包: ✅ terraform-local-homebrew-ohos-aarch64.tar.gz
- 验证: ✅ tflocal --version 正常工作
---

**编译结束**: 2026-06-21 17:11
**最终状态**: published
