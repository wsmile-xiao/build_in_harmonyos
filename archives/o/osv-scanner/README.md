# osv-scanner

> 漏洞扫描工具，扫描项目依赖并对照 [OSV 数据库](https://osv.dev) 检测已知安全漏洞。

## 基本信息

| 项 | 值 |
|---|---|
| 官网 | https://github.com/google/osv-scanner |
| 许可证 | Apache-2.0 |
| 构建系统 | Go (custom) |
| 分类 | utility (安全工具) |

## 功能概述

osv-scanner 是 Google 开源的安全工具，用于扫描项目的依赖锁文件（lockfile）、清单文件（manifest）和容器镜像，将发现的依赖版本与 OSV (Open Source Vulnerabilities) 数据库比对，报告已知安全漏洞。

### 核心命令

| 命令 | 说明 |
|------|------|
| `osv-scanner scan source` | 扫描源码目录中的依赖锁文件 |
| `osv-scanner scan image` | 扫描容器镜像中的依赖 |
| `osv-scanner fix` | 扫描并建议漏洞修复方案 |

### 支持的生态系统

- **npm** (package-lock.json)
- **Maven** (pom.xml)
- **Go** (go.mod)
- **PyPI** (requirements.txt)
- **Cargo** (Cargo.lock)
- **NuGet** (.csproj/.sln)
- **RubyGems** (Gemfile.lock)
- 以及更多

### 输出格式

table (默认) · JSON · Markdown · SARIF 2.1.0 · CycloneDX 1.4/1.5 · SPDX 2.3 · HTML

## OHOS 平台适配

### 构建方式

Go 项目，使用 `go build` 编译。非传统的 autotools/cmake 构建系统。

关键编译参数：
- `CGO_ENABLED=0` — 纯 Go 编译，无 C 依赖
- `GOOS=linux GOARCH=arm64` — 目标平台
- `go build -toolexec wrapper.sh` — OHOS fallocate 绕过

### OHOS 平台适配要点

1. **Go 工具链签名**：OHOS 要求所有 ELF 二进制包含签名段。Go 工具链内部工具（compile/link/asm 等）位于 `GOROOT/pkg/tool/linux_arm64/`，需逐一用 `binary-sign-tool` 签名。

2. **fallocate 绕过**：Go 链接器使用 `fallocate()` 预分配输出文件空间，HMDFS/tmpfs 返回 EACCES 导致链接失败。解决方案：创建 toolexec 包装器，将链接器输出重定向到 `/dev/shm`（支持 fallocate），链接完成后再复制回原路径。

3. **二进制签名**：编译出的 osv-scanner 和 osv-reporter 必须用 `binary-sign-tool sign --selfSign` 签名才能执行。

### 交付物

| 二进制 | 说明 |
|--------|------|
| `osv-scanner` | 主扫描程序 |
| `osv-reporter` | GitHub Action 报告生成器（实验性） |

## 版本列表

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 2.1.0 | built | 2026-07-02 | conan-verify 8/8 PASS, 功能测试 28/28 PASS |

## 相关文档

- [版本级编译笔记](2.1.0/notes.md) — 详细编译步骤、问题与解决方案
- [Conan 配方](2.1.0/conanfile.py) — Conan 构建配方
- [功能测试报告](2.1.0/reports/functional-test-report.md) — 28 项功能测试结果
- [Conan 验证报告](2.1.0/reports/conan-verify-report.md) — 8 道门禁验证结果
