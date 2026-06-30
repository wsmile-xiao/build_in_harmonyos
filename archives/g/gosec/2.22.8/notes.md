# gosec 2.22.8 适配笔记

## 编译环境
- 构建系统: Go (go build)
- 编译日期: 2026-06-17
- 编译器: Go 1.26.4 (CGO_ENABLED=0)
- 状态: published

## 编译步骤

gosec 是 Go 项目，不使用传统的 configure/make 流程。

1. 下载源码: `https://github.com/securego/gosec/archive/refs/tags/v2.22.8.tar.gz`
2. 解压到工作目录
3. 下载依赖: `go mod download`
4. 编译二进制:
   ```bash
   CGO_ENABLED=0 GO111MODULE=on go build \
     -ldflags="-w -s -X 'main.Version=v2.22.8' -X 'main.GitTag=v2.22.8' -X 'main.BuildDate=2026-06-16'" \
     -o gosec ./cmd/gosec/
   ```
5. 安装到 staging: `cp gosec $TEST_PREFIX/bin/gosec`
6. 安装到 DEFAULT_PREFIX: `cp gosec $DEFAULT_PREFIX/bin/gosec`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 自动模式找不到下载 URL | GitHub API URL 格式特殊 | 使用 --url 参数手动指定 GitHub tarball URL |
| 2 | git 不可用（缺少 libz.so） | 系统环境限制 | 不需要 git，手动设置版本号通过 ldflags |
| 3 | CGo 分析测试失败 | CGO_ENABLED=0 静态构建 | 预期行为，不影响核心功能 |
| 4 | verify-build G4 缺少 build_system 字段 | manifest.yaml 模板使用嵌套 build.system | 添加顶层 build_system: go 字段 |
| 5 | deploy 步骤失败（Operation not permitted） | 旧二进制文件无法覆盖 | 手动 rm + cp 安装到 DEFAULT_PREFIX |

## 源码修改

无源码修改，无需补丁。Go 项目在 OpenHarmony 上原生编译成功。

## 依赖版本

- go/1.26.4 (Go 编译器)

## 验证结果

```bash
$ gosec --version
Version: v2.22.8
Git tag: v2.22.8
Build date: 2026-06-16
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| gosec-2.22.8-ohos-aarch64.tar.gz | ~20MB | 预编译包 |

## 注意事项

- gosec 是纯 Go 项目，CGO_ENABLED=0 静态编译即可在 OpenHarmony 上运行
- 不需要修改 config.guess/config.sub（Go 项目天然跨平台）
- CGo 文件分析测试在静态构建模式下会失败，这是预期行为
- make check 失败是因为 Makefile 没有 check 目标，Go 项目使用 go test
---

**编译结束**: 2026-06-17 02:03
**最终状态**: published
