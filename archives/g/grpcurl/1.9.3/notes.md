# grpcurl 1.9.3 适配笔记

## 编译环境
- 构建系统: Go (纯 Go 语言项目，非 C/C++)
- 编译日期: 2026-06-01
- Go 版本: go1.22.10 linux/arm64
- 编译器: Go（CGO_ENABLED=0，静态编译）
- 状态: built（编译成功）

## 编译步骤

### Step 1: 初始化
- 下载 grpcurl v1.9.3 源码: https://github.com/fullstorydev/grpcurl/archive/refs/tags/v1.9.3.tar.gz
- SHA256: bb555087f279af156159c86d4d3d5dd3f2991129e4cd6b09114e6851a679340d
- 源码已解压到 ~/tmp/builds/grpcurl-1.9.3.work/

### Step 2: 编译
- grpcurl 是纯 Go 项目（go.mod + Makefile + cmd/grpcurl/）
- Homebrew 公式指定: `go build *std_go_args(ldflags: "-s -w -X main.version=#{version}") ./cmd/grpcurl`
- 编译命令:
  ```bash
  CGO_ENABLED=0 GOOS=linux GOARCH=arm64 \
  go build -ldflags "-s -w -X main.version=1.9.3" \
  -o grpcurl ./cmd/grpcurl/
  ```
- 使用 Go 1.22.10（避免 Go 1.23+ DIT ARM64 汇编问题）

### Step 3: 签名（关键挑战）

**尝试 1: CGO_ENABLED=1 + buildmode=pie（PIE/DYN 二进制）**
- 编译成功，产出 PIE/DYN 类型 ELF
- `binary-sign-tool -selfSign 1` 签名成功但**损坏了 TLS program header**
  - TLS header p_filesz 从 0x0 变为 0x9c8bd0（等于 .text 段大小）
  - TLS header p_memsz 从 0x10 变为 0x9c8be0
  - 导致运行时 SIGSEGV (exit code 139)
- 手动修补 TLS header 后仍然无法在 HMDFS 上执行（"Operation not permitted")
- **结论**: PIE/DYN 类型 Go 二进制签名后被 binary-sign-tool 损坏，不可用

**尝试 2: CGO_ENABLED=0（静态二进制，EXEC 类型）**
- 编译成功，产出 EXEC 类型 ELF（与 ~/usr/local/bin/go 结构相同）
- `binary-sign-tool -selfSign 1` 签名成功且**程序头部完好**
  - EXEC 类型只有 6 个 program headers（无 TLS、无 INTERP、无 DYNAMIC）
  - 签名后仅移动 section headers 位置，不影响运行
- 安装到 ~/usr/local/bin/ 后成功执行 ✅
- **结论**: 静态 Go 二进制（EXEC 类型）可以正常签名并执行

### Step 4: 安装验证
```bash
# 安装到本地（模拟用户部署）
cp grpcurl ~/usr/local/bin/grpcurl

# 验证
~/usr/local/bin/grpcurl --version
# → grpcurl 1.9.3 ✅

~/usr/local/bin/grpcurl --help
# → 正常输出帮助信息 ✅
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go 1.23+ DIT 汇编错误 | Go runtime 使用 ARM64 DIT MSR 指令 | 使用 Go 1.22.10 ✅ |
| 2 | PIE/DYN 二进制签名后 SIGSEGV | binary-sign-tool 损坏 TLS program header | 改用 CGO_ENABLED=0 静态编译 ✅ |
| 3 | HMDFS 不允许覆盖/修改已存在二进制 | HMDFS 安全机制 | rm -f 后再 cp ✅ |
| 4 | 之前认为 EXEC 类型不能签名 | 之前的错误认知 | 实际上 EXEC 类型可以成功签名并执行 ✅ |
| 5 | Go 工具版本不匹配 | GOROOT 包含 1.23.6 工具但 go 是 1.24.2 | 使用 GOROOT=~/usr/local/go122 ✅ |

## 关键发现（知识更新）

1. **修正之前错误认知**: `binary-sign-tool -selfSign 1` 可以签名 EXEC 类型 ELF，之前认为不能签名是错误的。实际上 EXEC 类型（如 go 二进制）可以正常签名并执行。
2. **binary-sign-tool 损坏 TLS header**: 当签名 PIE/DYN 类型 Go 二进制时，binary-sign-tool 会损坏 TLS program header 的 p_filesz 和 p_memsz，导致运行时崩溃。
3. **Go 静态编译策略**: 对于 HMDFS 平台，Go 项目应使用 CGO_ENABLED=0 静态编译（EXEC 类型），而非 PIE/DYN 类型，以避免签名损坏问题。
4. **Go 版本选择**: Go 1.22.x 无 DIT ARM64 汇编问题，适用于 OpenHarmony ARM64 平台。
5. **HMDFS 覆盖限制**: 不能直接覆盖已存在的二进制文件，需要先 rm -f 再 cp。

## 源码修改
无（未修改源码，纯 Go 编译）

## 依赖版本
- Go 1.22.10 (~/usr/local/go122)
- grpcurl 源码 v1.9.3

## 验证结果
```bash
~/usr/local/bin/grpcurl --version → grpcurl 1.9.3 ✅
~/usr/local/bin/grpcurl --help → 正常输出 ✅
file ~/usr/local/bin/grpcurl → ELF executable, 64-bit LSB arm64, static, stripped ✅
```---

**编译结束**: 2026-06-01 18:41
**最终状态**: published
---

**编译结束**: 2026-08-10 01:45
**最终状态**: published
