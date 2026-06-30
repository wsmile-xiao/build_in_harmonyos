# superfile 1.5.0 适配笔记

## 编译环境
- 构建系统: Go (非传统构建系统)
- 编译日期: 2026-06-05
- 编译器: Go 1.25.5 (需要手动安装和签名)
- 状态: built

## 编译步骤

由于 superfile 是 Go 项目，使用非传统构建流程：

1. 初始化编译环境：`ohc-run.py init-build superfile 1.5.0 --url=file:///data/storage/el2/base/cache/superfile-1.5.0.tar.gz`
2. 手动下载并安装 Go 1.25.5（因为项目依赖要求 Go >= 1.25.0）
3. 对 Go 工具链进行 ELF 签名（鸿蒙系统要求）
4. 编译命令：
   ```bash
   export PATH=~/usr/local/go-1.25.5/bin:$PATH
   export GOPROXY=https://goproxy.cn,https://goproxy.io,direct
   CGO_ENABLED=0 go build -ldflags "-s -w" -trimpath -o $TEST_PREFIX$DEFAULT_PREFIX/bin/spf
   ```
5. 对生成的二进制文件进行 ELF 签名

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 源码下载超时 | 网络环境无法访问 GitHub | 使用 git clone 从国内镜像下载 |
| 2 | Go 版本不兼容（1.24 vs 1.25） | 项目依赖 `go-zoxide` 要求 Go >= 1.25.0 | 从 golang.google.cn 镜像下载 Go 1.25.5 并安装 |
| 3 | Go 工具链无法执行 | 鸿蒙系统要求 ELF 签名 | 使用 `ohc-run.py sign-elf` 对所有 Go 工具链文件签名 |

## 源码修改

无源码修改，仅使用 Go 原始编译命令。

## 依赖版本

- Go 1.25.5 (编译依赖)
- Go 模块依赖（通过 go.mod 管理）：
  - github.com/charmbracelet/bubbletea v1.3.10
  - github.com/lazysegtree/go-zoxide v0.1.0 (要求 Go >= 1.25.0)
  - 等其他依赖（详见 go.mod）

## 验证结果

```bash
$TEST_PREFIX$DEFAULT_PREFIX/bin/spf -v
superfile version v1.5.0

# 文件类型
file $TEST_PREFIX$DEFAULT_PREFIX/bin/spf
/data/storage/el2/base/cache/test-install-superfile-1.5.0/storage/Users/currentUser/usr/local/bin/spf: ELF executable, 64-bit LSB arm64, static, BuildID=..., stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| spf (二进制) | 15M | 静态编译的 superfile 可执行文件 |

## 注意事项

1. **Go 版本依赖**：superfile 1.5.0 及其依赖要求 Go >= 1.25.0，需要从镜像手动下载并安装
2. **ELF 签名**：Go 工具链和编译产物都需要 ELF 签名才能在鸿蒙系统上执行
3. **Go 代理**：建议设置 `GOPROXY=https://goproxy.cn,https://goproxy.io,direct` 加速依赖下载
4. **静态编译**：使用 `CGO_ENABLED=0` 进行静态编译，产物无外部依赖
---

**编译结束**: 2026-06-05 14:31
**最终状态**: built
