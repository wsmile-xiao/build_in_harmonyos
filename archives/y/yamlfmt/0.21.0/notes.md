# yamlfmt 0.21.0 适配笔记

## 基本信息
- 软件: yamlfmt
- 版本: 0.21.0
- 构建系统: custom (Go 语言项目)
- 编译日期: 2026-06-15

## 编译过程

### 环境设置
- Go: 1.26.0（必须使用 Go 1.26.0+，Go 1.24.x 在 HMDFS 上 linker mmap 失败）
- GOROOT: /storage/Users/currentUser/usr/local/go1.26/go
- CGO_ENABLED: 0（纯 Go 编译，不需要 C 链接器）
- GOPROXY: https://goproxy.cn,direct（使用国内代理加速模块下载）

### 构建命令
```bash
go build -ldflags="-X main.version=0.21.0" -o yamlfmt ./cmd/yamlfmt
```

### 关键问题与解决

1. **[E081] Go linker mmap 失败**: Go 1.24.x 的 linker 在 HMDFS 上使用 mmap 创建输出文件失败（permission denied），Go 1.26.0 的 linker 修复了这个问题（输出 "Copied OK"）
2. **[E082] Go toolchain 自动下载**: go.mod 中的 `toolchain go1.24.8` 导致 Go 自动下载 1.24.8（签名问题），需要删除此行并设置 `GOTOOLCHAIN=local`
3. **[E083] Go test 签名**: 测试二进制也需要 ELF 签名，使用 `go test -c` + manual signing + execution
4. **ELF 签名**: Go 编译的二进制文件需要在 HarmonyOS 上 ELF 签名后才能执行

### 测试结果
- 核心包测试: PASS
- Basic formatter 测试: PASS
- Command 测试: PASS
- Collections 测试: PASS
- 部分测试包需要 ELF 签名才能运行

## 知识图谱引用
- E081: Go linker mmap on HMDFS → permission denied (使用 Go 1.26.0+)
- E082: Go toolchain directive causes auto-download of unsigned binary (删除 toolchain 行, GOTOOLCHAIN=local)
- E083: Go test binaries need ELF signing on HarmonyOS (go test -c + sign-elf + manual execution)

## 依赖
- go/1.26.0

## 安装验证
- `yamlfmt --version` → yamlfmt 0.21.0
- `echo 'key:   value' | yamlfmt -in` → `key: value`（格式化功能正常）
---

**编译结束**: 2026-06-15 22:29
**最终状态**: built
