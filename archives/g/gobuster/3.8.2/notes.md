# gobuster 3.8.2 适配笔记

## 编译环境
- 构建系统: Go modules (custom)
- 编译日期: 2026-06-10
- 编译器: Go 1.24.3 (手动安装)
- 状态: failed

## 编译步骤

### 1. 初始化
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build gobuster 3.8.2 --url=https://api.github.com/repos/OJ/gobuster/tarball/v3.8.2
```

### 2. Go 工具链安装
系统未预装 Go 工具链，手动下载并安装 Go 1.24.3：
```bash
cd /storage/Users/currentUser/tmp
curl -fsSL https://dl.google.com/go/go1.24.3.linux-arm64.tar.gz -o go1.24.3.linux-arm64.tar.gz
tar -xzf go1.24.3.linux-arm64.tar.gz
# 签名所有 Go 二进制文件以符合鸿蒙 ELF 签名要求
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf /storage/Users/currentUser/tmp/go/bin/go
find /storage/Users/currentUser/tmp/go -type f -executable -name "*" | while read f; do python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf "$f" 2>/dev/null || true; done
```

### 3. 源码修改
修改 go.mod 降低 Go 版本要求（从 1.25 到 1.24）：
```go
module github.com/OJ/gobuster/v3

go 1.24  # 原为 1.25
```

### 4. 编译尝试
```bash
export PATH=/storage/Users/currentUser/tmp/go/bin:$PATH
export GOPATH=/storage/Users/currentUser/tmp/gopath
export CGO_ENABLED=0
export TMPDIR=/storage/Users/currentUser/tmp
export GOCACHE=/storage/Users/currentUser/tmp/go-cache
cd /storage/Users/currentUser/tmp/builds/gobuster-3.8.2.work
go mod download  # 成功
go build -v -o /storage/Users/currentUser/tmp/gobuster .  # 失败
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 系统缺少 Go 工具链 | 鸿蒙系统未预装 Go | 手动下载并安装 Go 1.24.3 |
| 2 | Go 可执行文件权限被拒绝 | 鸿蒙系统要求 ELF 签名 | 使用 ohc-run.py sign-elf 签名所有 Go 工具链二进制文件 |
| 3 | go.mod 要求 Go 1.25 | 源码指定 Go 1.25，但只安装了 1.24.3 | 修改 go.mod 降低版本要求到 1.24 |
| 4 | Go 链接器权限失败 | 鸿蒙系统限制内存映射操作 | **无法解决** - Go 链接器在创建输出文件时需要 mmap 等内存映射操作，被鸿蒙系统安全机制阻止 |

## 根本原因

Go 工具链的链接器（`pkg/tool/linux_arm64/link`）在生成可执行文件时使用内存映射（mmap）等系统调用来创建和写入输出文件。鸿蒙系统的安全机制（可能是 SELinux 或 HMDFS 限制）阻止了这些操作，导致链接器报错：

```
/storage/Users/currentUser/tmp/go/pkg/tool/linux_arm64/link: mapping output file failed: permission denied
```

尝试过的解决方案：
1. ✅ 签名所有 Go 工具链二进制文件
2. ✅ 设置 TMPDIR 环境变量
3. ✅ 设置 GOCACHE 环境变量
4. ✅ 尝试不同的 CGO_ENABLED 设置（0 和 1）
5. ✅ 尝试不同的输出目录
6. ❌ 所有尝试均失败，错误信息相同

**结论**：鸿蒙系统当前的系统调用限制与 Go 工具链的链接器不兼容，无法使用标准 Go 工具链编译 Go 项目。需要等待鸿蒙系统更新或 Go 工具链提供针对鸿蒙系统的适配版本。

## 源码修改

- go.mod: 将 Go 版本要求从 1.25 降低到 1.24

## 依赖版本

- Go: 1.24.3 (手动安装)
- 依赖包: 通过 go mod download 自动下载

## 验证结果

```bash
# 编译失败，无法验证
go build -v -o /storage/Users/currentUser/tmp/gobuster .
# 输出：mapping output file failed: permission denied
```

## 交付物

无（编译失败）

## 注意事项

1. **鸿蒙系统限制**：Go 工具链链接器需要内存映射操作，与鸿蒙系统安全机制冲突
2. **未来可能性**：需要等待以下任一解决方案：
   - 鸿蒙系统更新，放宽内存映射限制
   - Go 工具链提供鸿蒙系统适配版本
   - 使用交叉编译方式（在其他平台编译好 ARM64 二进制文件后传输）
3. **临时方案**：可以考虑从 gobuster 的 GitHub Releases 页面下载预编译的 ARM64 二进制文件
---

**编译结束**: 2026-06-11 11:46
**最终状态**: failed
