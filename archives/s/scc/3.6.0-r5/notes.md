# scc 3.6.0-r5 适配笔记

## 编译环境
- 构建系统: custom (Go项目)
- 编译日期: 2026-06-04
- 编译器: Go 1.24.2 (静态编译, CGO_ENABLED=0)
- 状态: published

## 编译步骤

1. 初始化: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build scc 3.6.0-r5 --url=https://github.com/boyter/scc/archive/refs/tags/v3.6.0.tar.gz`
2. 手动修正源码目录: 脚本误将 examples/language 提升为源码，需手动恢复正确结构
3. 修改 go.mod: 将 `go 1.25.2` 改为 `go 1.24`（适配本地 Go 版本）
4. 删除 vendor 目录: vendor 中预编译包版本不匹配 (go1.23.6 vs go1.24.2)
5. 设置 GOROOT: `export GOROOT=$HOME/usr/local/go`（修正默认 GOROOT）
6. 设置 GOPROXY: `export GOPROXY=https://goproxy.cn,direct`
7. 设置 GOTOOLCHAIN: `export GOTOOLCHAIN=local`
8. 编译: `CGO_ENABLED=0 go build -v -o scc .`
9. DESTDIR安装: 手动复制 scc 到 TEST_PREFIX/DEFAULT_PREFIX/bin/
10. 本地安装: 复制 scc 到 DEFAULT_PREFIX/bin/
11. ELF签名: `ohc-run.py sign-elf`
12. Package: `ohc-run.py package scc 3.6.0-r5`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 嵌套源码提升错误 | init-build 将 examples/language 提升为源码目录 | 手动删除错误目录，重新从 tarball 提取正确源码 |
| 2 | CMakeLists.txt 误检测 | 项目根目录有测试用的 CMakeLists.txt | 手动识别为 Go 项目，跳过 cmake |
| 3 | go.mod 版本不兼容 | go.mod 要求 go 1.25.2，本地只有 1.24.2 | 修改 go.mod: `go 1.25.2` → `go 1.24` |
| 4 | vendor 版本冲突 | vendor 预编译包为 go1.23.6 | 删除 vendor 目录，使用 go mod download |
| 5 | GOROOT 错误 | GOROOT 默认设为 ~/usr/local（安装前缀），非 Go root | 手动设置 GOROOT=$HOME/usr/local/go |
| 6 | verify-build install_prefix | DESTDIR 模式下二进制在 TEST_PREFIX/DEFAULT_PREFIX/bin | 使用 --install-prefix 参数修正路径 |

## 源码修改

- go.mod: 修改 `go 1.25.2` → `go 1.24`
- 删除 vendor/ 目录（使用 go mod download 替代）

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| go | 1.24.2 | Go 工具链，位于 ~/usr/local/go |

## 验证结果

```bash
$ scc --version
scc version 3.6.0
```

verify-build: PASS (G1-G4)
- G1: ✅1 二进制完整性
- G2: ⚠️1 功能可用性 (--version 通过但签名检测)
- G3: ✅1 ⚠️1 可移植性 (静态编译无RPATH需要)
- G4: ✅0 档案完整性

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| scc-3.6.0-r5-ohos-aarch64.tar.gz | 4605KB | 预编译包 (stripped, ELF signed) |
| scc-3.6.0-r5-ohos-aarch64-debug.tar.gz | 1943KB | 调试符号包 |

## 注意事项

- scc 是 Go 项目，不支持 cmake/autotools 构建系统，需手动使用 `go build`
- CGO_ENABLED=0 确保静态编译，无需外部 C 库依赖
- GOROOT 必须正确设置为 ~/usr/local/go，否则会出现版本冲突错误
- 下载 GitHub tarball 需使用镜像 (ghfast.top)，直连超时
---

**编译结束**: 2026-06-04 11:35
**最终状态**: published
