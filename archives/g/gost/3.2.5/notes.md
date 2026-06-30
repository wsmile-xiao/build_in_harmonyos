# gost 3.2.5 适配笔记

## 编译环境
- 构建系统: go
- 编译日期: 2026-06-17
- 编译器: go1.26.4 linux/arm64
- 状态: built

## 编译步骤

gost 是 Go 语言项目，不使用传统的 configure/make 流程。

1. 下载源码: https://github.com/go-gost/gost/archive/refs/tags/v3.2.5.tar.gz
2. 解压到 `/data/storage/el2/base/cache/builds/gost-3.2.5.work`
3. 编译命令:
   ```bash
   GOARCH=arm64 GOOS=linux CGO_ENABLED=0 go build --ldflags="-s -w" -v -o bin/gost ./cmd/gost/
   ```
4. 安装到 staging 目录 (DESTDIR 模式):
   ```bash
   mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
   cp bin/gost $TEST_PREFIX/$DEFAULT_PREFIX/bin/gost
   ```
5. 安装到本地 DEFAULT_PREFIX:
   ```bash
   mkdir -p $DEFAULT_PREFIX/bin
   cp bin/gost $DEFAULT_PREFIX/bin/gost
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 检测构建系统为 autotools | Go 项目无 configure/Makefile 标准格式 | 手动编译，使用 go build |
| 2 | 搜索 URL 未找到 gost 3.2.5 | v3.x 在 go-gost/gost 仓库（非 ginuerzh/gost） | 手动指定 URL 参数 |

## 源码修改

无源码修改，Go 项目原生支持 linux/arm64 平台。

## 依赖版本

- go/1.26.4 (编译器)

## 验证结果

```bash
$ gost -V
gost 3.2.5 (go1.26.4 linux/arm64)

$ file bin/gost
ELF 64-bit LSB executable, ARM aarch64, version 1 (SYSV), statically linked, stripped
```

## 交付物

| 文件 | 说明 |
|------|------|
| gost-3.2.5-ohos-aarch64.tar.gz | 预编译包 |

## 注意事项

- gost v3.x 仓库地址为 go-gost/gost（不是 ginuerzh/gost，后者为 v2.x）
- CGO_ENABLED=0 确保静态链接，无外部依赖
- --ldflags="-s -w" 用于 strip 符号信息减小体积
---

**编译结束**: 2026-06-17 06:03
**最终状态**: published
