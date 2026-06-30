# dbmate 2.33.0 编译笔记

## 基本信息
- **软件**: dbmate — Go database migration tool
- **版本**: 2.33.0
- **Homebrew**: #737 (4292 installs)
- **源码**: https://github.com/amacneil/dbmate (tag v2.33.0)
- **编译日期**: 2026-06-01

## 编译环境
- **Go 版本**: 1.26.3 (arm64 linux)
- **编译命令**: `CGO_ENABLED=0 GOOS=linux GOARCH=arm64 GOPROXY=https://goproxy.cn,direct go build -ldflags="-s -w" -o $DEFAULT_PREFIX/bin/dbmate .`
- **安装前缀**: ~/usr/local (DEFAULT_PREFIX)
- **GOPATH**: ~/go1263

## 编译过程

### Step 1: 获取源码
从 GitHub API 下载 dbmate v2.33.0 tarball。init-build 脚本的 URL 搜索无法找到 GitHub 源码（只找到 Savannah 假 URL），因此手动下载。

### Step 2: 依赖下载
`go mod download` 通过 goproxy.cn 成功下载所有依赖。

### Step 3: 编译
使用 Go 1.26.3 静态编译（CGO_ENABLED=0），ldflags="-s -w" 去除符号表和调试信息。

**注意事项**:
- Go 1.26.0 有 corrupted runtime source 问题，必须使用 1.26.3
- dbmate 是纯 Go 项目，无需 configure/make 步骤
- `main_cgo.go` 文件存在但 CGO_ENABLED=0 时自动忽略

### Step 4: 安装与验证
- 二进制已签名（ELF签名），可正常执行
- `dbmate --version` 输出: `dbmate version 2.33.0`
- 产物大小: ~28MB (strip 后)

### Step 5: 打包
使用 ohc-run.py package 制作预编译包。

## 知识提取
- **L3 本版**: Go 工具编译使用 CGO_ENABLED=0 + ldflags="-s -w" 静态编译模式
- **L2 模式**: Go 工具不需要 configure/make，直接 `go build` 即可
- **L1 平台**: Go 1.26.0 有 corrupted runtime source，必须用 1.26.3

---

**编译结束**: 2026-06-01
**最终状态**: built
---

**编译结束**: 2026-06-01 20:34
**最终状态**: built
