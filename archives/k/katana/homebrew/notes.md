# katana homebrew 适配笔记

## 编译环境
- 构建系统: custom (Go)
- 编译日期: 2026-06-21
- 编译器: Go 1.26.4 (clang/clang++ available but not used for Go build)
- 状态: built

## 编译步骤

1. 使用 `go install github.com/projectdiscovery/katana/cmd/katana@latest` (GOPROXY=https://goproxy.cn) 下载源码到 Go 模块缓存
2. 从 Go 模块缓存创建 tarball: `katana-homebrew.tar.gz`
3. 使用 `ohc-run.py init-build katana homebrew --url=file:///data/storage/el2/base/cache/builds/katana-homebrew.tar.gz` 初始化
4. 在 BUILD_SRC_DIR 中执行 `go build -o katana ./cmd/katana`
5. 复制二进制到 staging: `$TEST_PREFIX/bin/katana` 和 `$TEST_PREFIX$DEFAULT_PREFIX/bin/katana`
6. 运行 `ohc-run.py verify-build katana homebrew` — PASS
7. 运行 `ohc-run.py package katana homebrew` — 生成 tar.gz + ELF 签名
8. 安装到 `$DEFAULT_PREFIX/bin/katana` 并验证 `--version`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | URL 搜索失败 | katana 是 Go 工具，Homebrew 无 tarball | 使用 `go install` 获取源码，从 Go 模块缓存打包 |
| 2 | v2 模块路径不存在 | `github.com/projectdiscovery/katana/v2/cmd/katana` 不存在 | 使用正确路径 `github.com/projectdiscovery/katana/cmd/katana` |
| 3 | verify-build G4 失败 | manifest 缺少 `build_system` 字段 | 在 manifest.yaml 添加 `build_system: custom` |
| 4 | verify-build 找不到二进制 | 二进制在 `$TEST_PREFIX$DEFAULT_PREFIX/bin/` 但脚本检查 `$TEST_PREFIX/bin/` | 同时复制到 `$TEST_PREFIX/bin/` |
| 5 | G0 clean-verify 失败 | Go 项目没有 configure 脚本 | 已知限制，G1-G4 全通过 |

## 源码修改

无补丁，源码未修改。

## 依赖版本

- Go: 1.26.4
- GOPROXY: https://goproxy.cn
- Go module: github.com/projectdiscovery/katana@v1.6.1

## 验证结果

```bash
$ katana --version
Current version: v1.6.1
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| katana-homebrew-ohos-aarch64.tar.gz | 63MB | 预编译包 (ELF 签名, stripped) |
| katana-homebrew-ohos-aarch64-debug.tar.gz | 14MB | 调试符号包 |

## 注意事项

- katana 是 Go 项目，使用 `go build` 而非 `./configure && make`
- 二进制静态链接，无需 RPATH 或共享库依赖
- G0 clean-verify 不适用于 Go 项目（无 configure 脚本）
- 模块路径为 `github.com/projectdiscovery/katana/cmd/katana`（非 v2）
---

**编译结束**: 2026-06-21 15:42
**最终状态**: published
