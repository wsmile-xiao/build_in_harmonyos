# sqlfmt 2025.01.30 适配笔记

## 编译环境
- 构建系统: custom（Go项目，使用go build）
- 编译日期: 2026-06-10
- 编译器: Go 1.25.7 (goenv)
- 状态: failed

## 编译步骤

### 1. 源码准备
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build sqlfmt 2025.01.30 \
  --url=https://api.github.com/repos/gsiems/sqlfmt/tarball/v2025.01.30
```
- SSL证书验证导致脚本下载失败，手动用curl -k下载到 ~/tmp/builds/
- init-build脚本检测到已有tarball后自动继续

### 2. 源码分析
- sqlfmt是纯Go项目，go.mod要求 `go 1.20`
- 无Makefile、configure脚本，使用 `go build` 编译
- 项目结构: cmd/sqlfmt.go (主入口), dialect/, env/, formatter/, parser/

### 3. Go编译失败 - HMDFS mmap限制

**所有尝试均失败：**

```bash
# 尝试1: 直接编译
GOTOOLCHAIN=local CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o sqlfmt ./cmd/sqlfmt.go
# 错误：link: mapping output file failed: permission denied

# 尝试2: CGO_ENABLED=1 + 外部链接器
CGO_ENABLED=1 go build -ldflags="-linkmode=external -extld=clang" -o sqlfmt ./cmd/sqlfmt.go
# 同样错误

# 尝试3: go install
CGO_ENABLED=0 go install -trimpath -ldflags="-s -w" ./cmd/sqlfmt.go
# 同样错误

# 尝试4: 设置GOTMPDIR/GOCACHE指向不同路径
export GOTMPDIR=~/tmp/go-tmp export GOCACHE=~/tmp/go-cache
# 同样错误

# 尝试5: 不同Go版本 (1.24.4和1.25.7)
# 同样错误

# 尝试6: -o /dev/stdout 管道输出
# 同样错误（linker在内部仍使用mmap写临时文件）

# 尝试7: toolexec wrapper
# 同样错误（wrapper只是透传，linker内部mmap无法绕过）
```

**根因分析：**
- Go linker (cmd/link) 使用 mmap() syscall 创建输出ELF文件
- OpenHarmony HMDFS文件系统不支持 mmap() 的 MAP_SHARED + PROT_WRITE 组合
- 这是平台级限制，所有Go版本（1.24.4, 1.25.7）均受影响
- 与 mongocli 1.55.0 编译记录中的问题描述一致

### 4. 预编译二进制搜索
- GitHub releases v2025.01.30: 无预编译资产（只有源码tarball/zipball）
- 无官方linux/arm64预编译二进制可用

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 状态 |
|---|------|------|----------|------|
| 1 | init-build SSL下载失败 | OpenHarmony CA证书验证失败 | 手动curl -k下载 + init-build --no-download → 用已有tarball | ✅ 已解决 |
| 2 | Go linker mmap输出文件失败 | HMDFS不支持mmap MAP_SHARED+PROT_WRITE | 无解决方案 - 平台限制 | ❌ 未解决 |
| 3 | 无官方预编译二进制 | 项目只提供源码 | 无法替代 | ❌ 未解决 |

## 源码修改

无。编译失败，未修改源码。

## 依赖版本

| 软件 | 版本 | 说明 |
|------|------|------|
| Go | 1.25.7 | goenv安装，GOTOOLCHAIN=local可用 |
| Go | 1.24.4 | goenv安装，同样linker失败 |

## 验证结果

编译失败，无产物。无法验证。

## 注意事项

1. **Go linker mmap限制**：这是OpenHarmony HMDFS的已知平台限制。所有Go项目在HMDFS上无法通过 `go build` 产生可执行文件。需要HMDFS升级支持mmap或Go linker适配OpenHarmony。
2. **与mongocli相同问题**：mongocli 1.55.0编译时遇到相同问题，最终使用了MongoDB官方预编译二进制。sqlfmt没有类似替代方案。
3. **建议**：等待(1) HMDFS支持Go linker mmap 或 (2) sqlfmt项目提供linux/arm64预编译二进制 或 (3) 使用可支持mmap的文件系统构建Go项目。---

**编译结束**: 2026-06-10 12:11
**最终状态**: failed
---

**编译结束**: 2026-06-10 22:21
**最终状态**: failed
