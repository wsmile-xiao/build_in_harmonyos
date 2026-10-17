# aliyun 3.4.8 适配笔记

## 软件简介

Alibaba Cloud CLI（阿里云命令行工具），Go 语言项目。
源码: https://github.com/aliyun/aliyun-cli (tag v3.4.8, 2026-07-17)

## 编译环境

- 构建系统: custom (Go 项目, `go build`)，非 autotools/cmake
- 编译日期: 2026-08-08
- 编译器: Go 1.26.5 (harmonybrew 安装, 自动签名) / 配方 bootstrap Go 1.23.8
- 目标架构: aarch64 (arm64), CGO_ENABLED=0 纯静态
- GOPROXY: https://goproxy.cn,direct
- 状态: published

## 编译步骤

1. 环境准备：系统无 Go 工具链，且用户目录 (hmdfs) 下 ELF 需 `.codesign` 签名才能执行
   （python3 可执行因其带 .codesign 段；官方 go 二进制无签名被 Seccomp EACCES 拦截）
2. 安装 harmonybrew 包管理器 → `brew install go ohos-sdk`（go 构建管道自动签名）
3. `go mod download` 下载依赖（goproxy.cn）
4. 子模块 `aliyun-openapi-meta` 为 git submodule，GitHub release tarball 不含其内容，
   需单独拉取（固定 commit 2563691c22229a0b493606e11166b95896707095）
5. 构建命令:
   ```bash
   go build -trimpath -ldflags "-s -w -X 'github.com/aliyun/aliyun-cli/v3/cli.Version=3.4.8'" \
     -o out/aliyun main/main.go
   ```
   ⚠️ 版本变量路径带 `/v3/`：`github.com/aliyun/aliyun-cli/v3/cli.Version`（不含 /v3/ 时输出 0.0.1）
6. 验证: `aliyun --version` → "Alibaba Cloud Command Line Interface Version 3.4.8"

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 系统无 Go 工具链 | 环境未预装 go | harmonybrew `brew install go`（带 OHOS 签名补丁） |
| 2 | go 二进制 Permission denied | hmdfs 下无 .codesign 段 ELF 被 Seccomp 拦截 | 用 harmonybrew 已签名 go；配方 bootstrap go1.23.8 时 `_sign_go_sdk_if_ohos` |
| 3 | `no required module provides ...aliyun-openapi-meta` | git 子模块不在 release tarball | conandata.yml 声明 submodule 固定 commit tarball，source() 额外 get |
| 4 | 版本号显示 0.0.1 | ldflags -X 路径缺少 /v3/ | 用 `github.com/aliyun/aliyun-cli/v3/cli.Version` |
| 5 | Go linker 输出 Permission denied (HMDFS) | mmap 输出文件在 hmdfs 失败（先例 argo P3） | link-out 目录放 ext2 路径 OHOS_GO_WORKDIR |
| 6 | 上游测试部分失败 | chmod 权限位断言 (E046 hmdfs chmod 不生效) / os-arch 检查 / mmap 相关 | 平台限制，记录不阻塞；核心 cli 测试通过 |

## 测试验证

- `aliyun --version` → 3.4.8 ✅
- `aliyun help` → 子命令列表正常 ✅
- `go test ./cli/...` → 通过（cli 包 ok）
- 平台限制失败（不阻塞）: cli/upgrade TestCopyFile、cli/plugin TestCopyDirTree_preservesFilePerm
  （期望 0755/0600 chmod 在 hmdfs 不生效）、cliext 若干 os-arch 检查用例

## 依赖版本

- Go 1.23.8（go.mod: go 1.23.0, toolchain go1.23.8）
- GOPROXY=https://goproxy.cn,direct
- 无 C/C++ 依赖（CGO_ENABLED=0 纯静态）

## 交付物

- conanfile.py: Go 项目配方（package_type=application, cpp_info.bindirs=["bin"]）
- conandata.yml: 主源码 sha256 + submodule 固定 commit
- test_package/: test.sh 实质测试（aliyun --version 断言 3.4.8 + help）
- commands.json: 软件级命令声明（R38, type=tool）
---

**编译结束**: 2026-08-08 00:51
**最终状态**: published
