# E081: Go link mmap 失败（HMDFS 不支持）

## 问题描述

Go 工具链的链接器在创建输出文件时使用 `mmap` 系统调用，HMDFS 文件系统不支持此操作，导致所有 Go 项目无法在本地编译。

## 错误信息

```
# github.com/cockroachdb/pebble/v2/cmd/pebble
/storage/Users/currentUser/usr/local/go/pkg/tool/linux_arm64/link: mapping output file failed: permission denied
```

## 根因分析

Go 的链接器 (`pkg/tool/linux_arm64/link`) 内部使用 mmap 来映射输出文件，这是 Go 编译器的核心设计。HMDFS 文件系统不支持 mmap 操作，这是平台限制，无法绕过。

## 受影响范围

- 所有 Go 项目
- 所有构建模式（exe, c-archive, c-shared, shared, plugin）
- 所有链接模式（internal, external）

## 解决方案

### 方案 A：交叉编译（推荐）

在 Linux x86_64 主机上编译 linux/arm64 版本：

```bash
# 设置目标平台
export GOOS=linux
export GOARCH=arm64

# 编译
go build -o pebble-linux-arm64 ./cmd/pebble

# 或者一步到位
GOOS=linux GOARCH=arm64 go build -o pebble ./cmd/pebble
```

然后将编译好的二进制传输到鸿蒙设备，签名后即可使用。

### 方案 B：Docker 容器

在有可用 tmpfs 的 Docker 容器中编译：

```bash
docker run --rm -v $(pwd):/src -w /src golang:1.23 go build ./cmd/pebble
```

### 方案 C：预编译包

从 cmd-pkgs 下载预编译的 Go 二进制包。

## 验证方法

```bash
# 尝试编译（预期失败）
go build ./cmd/pebble

# 应输出：
# link: mapping output file failed: permission denied
```

## 注意事项

1. Go 工具链本身也需要签名才能执行
2. Go 1.23+ 版本支持更好的交叉编译体验
3. 编译产物需要使用 `ohc-run.py sign-elf` 签名

## 相关案例

- pebble v2.1.5 编译失败（2026-05-21）
- 所有 Go 项目编译失败

## 分类

- 类别: platform_limitation
- 优先级: P1（阻塞所有 Go 项目）
- 标签: Go, HMDFS, mmap