# amass 4.2.0 适配笔记

## 编译环境
- 构建系统: custom (Go项目)
- 编译日期: 2026-06-11
- 编译器: Go 1.26.4 (go build)
- 目标架构: linux/arm64 (aarch64)
- 状态: built

## 编译步骤

amass 是 OWASP 开源网络资产发现工具，Go 语言项目，不使用 autotools/cmake/meson 等传统构建系统。

1. 通过 Go module proxy (GOPROXY=https://goproxy.cn,direct) 下载源码
2. 创建 tarball 并使用 ohc-run.py init-build 初始化
3. 自动化 build 步骤在 Step3 configure 阶段因依赖解析 git fetch 超时而失败（网络受限）
4. 切换到模式B（手动编译），使用 Go 直接构建:
   ```bash
   cd /data/storage/el2/base/cache/builds/amass-4.2.0.work
   GOPROXY=https://goproxy.cn,direct CGO_ENABLED=0 GOOS=linux GOARCH=arm64 \
     go build -trimpath -ldflags="-s -w" -o amass ./cmd/amass/
   ```
5. 安装到 DESTDIR 和 DEFAULT_PREFIX
6. 使用 ohc-run.py package 和 finish 完成

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 找不到 URL | amass 不在软件注册表中 | 手动通过 go mod download 下载源码并创建 tarball，使用 --url 参数初始化 |
| 2 | build 步骤在 configure 阶段崩溃 | 依赖解析器尝试 git fetch --depth=1 超时（30s），GitHub 网络不可达 | 切换到模式B，手动使用 Go 编译 |
| 3 | G4 档案完整性 FAIL | manifest.yaml 缺少 `build_system:` 顶层字段（模板生成了嵌套格式） | 添加 `build_system: custom` 顶层字段 |
| 4 | G2 功能可用性 WARNING | `amass --version` 输出不在标准格式（返回 v4.2.0 而非标准 --version 输出） | 已接受为 WARNING，不影响最终结果 |
| 5 | G3 可移植性 WARNING | 静态编译无 RPATH 和签名 | CGO_ENABLED=0 静态编译无需 RPATH；Go ELF 不含签名 |

## 源码修改

无补丁。amass 是纯 Go 项目，CGO_ENABLED=0 静态编译无需任何源码修改。

## 依赖版本

- Go 1.26.4 (harmonybrew)
- GOPROXY=https://goproxy.cn,direct (中国镜像)
- 无 C/C++ 依赖

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/bin/amass -version
v4.2.0

$ file /storage/Users/currentUser/usr/local/bin/amass
ELF executable, 64-bit LSB arm64, static, BuildID=d0b352190c943f0ec62c299a8098d7114b77b61e, stripped

$ verify-build 结果: PASS (G1✅ G2⚠️ G3⚠️ G4✅)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| amass-4.2.0-ohos-aarch64.tar.gz | 35321KB | 预编译包（静态编译） |
| amass-4.2.0-ohos-aarch64-debug.tar.gz | 77KB | debug symbols 包 |

## 注意事项

- amass 是 Go 项目，必须使用 `go build` 而非 autotools/cmake/meson
- 必须使用 GOPROXY=https://goproxy.cn,direct 以在中国大陆下载 Go 依赖
- CGO_ENABLED=0 生成纯静态 ELF，无需系统 C 库依赖
- Go 生成的 ELF 没有 RPATH，但不影响运行（静态链接）
- Go ELF 不含代码签名，需要后续通过 sign-elf 步骤添加（如需要）
---
**编译结束**: 2026-06-11 06:31
**最终状态**: built
---

**编译结束**: 2026-06-11 06:37
**最终状态**: built
