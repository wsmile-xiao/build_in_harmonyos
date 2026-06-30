# github-mcp-server 1.2.0 编译笔记

## 基本信息
- 软件: github-mcp-server
- 版本: 1.2.0
- 构建系统: Go (go build)
- 构建模式: manual (Mode B)
- 架构: aarch64 (arm64)
- 日期: 2026-06-10

## 编译过程
- 源码获取: 通过 Go module proxy (goproxy.cn) 下载 github.com/github/github-mcp-server@v1.2.0
- 编译命令: `CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -ldflags "-X main.version=1.2.0 -X main.commit=v1.2.0" -o github-mcp-server ./cmd/github-mcp-server/`
- 附加二进制: mcpcurl (`CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -o mcpcurl ./cmd/mcpcurl/`)
- 安装方式: DESTDIR 模式 (`DESTDIR=$TEST_PREFIX`)
- Strip: 已 strip，减小体积 (24MB→17MB 主二进制)

## 关键决策
- GitHub 无法直接访问，使用 goproxy.cn 中国镜像获取 Go module 源码
- 选择 v1.2.0 (最新稳定版本)
- CGO_ENABLED=0 静态编译，无外部 C 库依赖
- 编译两个二进制: github-mcp-server (主程序) + mcpcurl (辅助工具)

## 遇到的问题及解决
1. **GitHub 连接超时**: github.com 443端口无法连接 → 使用 goproxy.cn Go模块代理解决
2. **init-build URL自动搜索失败**: ohc search_url 不支持自定义GitHub组织 → 手动创建构建上下文文件

## 质量门禁结果
- G0: ⚠️ 无原始tarball（Go模块方式获取源码）
- G1: ✅ 二进制完整性通过
- G2: ✅ 功能可用性通过 (1 ⚠️)
- G3: ✅ 可移植性通过
- G4: ✅ 档案完整性通过 (1 ⚠️)

## 产出文件
- github-mcp-server: 17MB ELF arm64 static binary
- mcpcurl: 4.4MB ELF arm64 static binary
- github-mcp-server-1.2.0-ohos-aarch64.tar.gz: 22MB
---

**编译结束**: 2026-06-10 14:18
**最终状态**: built
