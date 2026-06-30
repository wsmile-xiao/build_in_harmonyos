# ghq 1.10.1 — 适配笔记

## 编译信息

- **软件**: ghq (Git repository manager)
- **版本**: 1.10.1
- **源码**: https://github.com/x-motemen/ghq/archive/refs/tags/v1.10.1.tar.gz
- **构建系统**: Go (custom)
- **编译日期**: 2026-06-01

## 编译过程

### 环境要求
- **Go 版本**: 需要 Go >= 1.26.0（go.mod 指定 go 1.26.0）
- 系统自带 Go 1.24.2 不满足要求
- Go 1.26.0 有已知 bug（runtime/traceexp.go duplicate declarations），不可用
- **使用 Go 1.26.3**（从 /data/storage/el2/base/cache/go1.26.3.linux-arm64.tar.gz 安装）

### 编译命令
```bash
export CGO_ENABLED=0 GOOS=linux GOARCH=arm64 GOTOOLCHAIN=local GOPROXY=https://goproxy.cn,direct
export PATH=/storage/Users/currentUser/usr/local/go1263/bin:$PATH
go build -ldflags="-s -w" -o /data/storage/el2/base/cache/ghq-bin .
```

### 关键问题及解决

1. **Go 1.26.0 腐化**: runtime/traceexp.go 有重复声明 (`unsafeTraceExpWriter redeclared`)，导致编译失败。使用 Go 1.26.3 解决。

2. **ELF 签名**: HarmonyOS 要求所有 ELF 二进制必须签名才能执行。需要签名：
   - Go 1.26.3 的 `bin/go` 和 `bin/gofmt`
   - Go 1.26.3 的 `pkg/tool/linux_arm64/` 下所有 8 个工具（compile, asm, link 等）
   - ghq 编译产物本身
   - go test 生成的测试二进制

3. **HMDFS 限制**: 不能用 `cp` 覆盖已有文件（Operation not permitted）。需要先 `rm -f` 再 `cp`。

4. **Go linker mmap**: 输出文件必须在 hmfs 文件系统上（/data/storage/el2/base/cache/），不能在 HMDFS 上。

5. **测试运行**: `go test` 生成的测试二进制需要 ELF 签名后才能执行。使用 `go test -c` 编译 + `sign-elf` 签名 + 手动执行的方式绕过。

### 测试结果
- 主包测试: PASS（所有 TestVCSBackend 子测试、TestCvsDummyBackend、TestBranchOptionIgnoredErrors）
- cmdutil 包: PASS（TestRun, TestRunInDir, TestRunSilently）
- logger 包: PASS（TestLog with_color/without_color）

## 安装验证
```
$ ghq --version
ghq version 1.10.1 (rev:HEAD)
```
---

**编译结束**: 2026-06-01 18:41
**最终状态**: published
