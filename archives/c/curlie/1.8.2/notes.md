# curlie 1.8.2 适配笔记

## 编译环境
- 构建系统: custom (Go项目)
- 编译日期: 2026-06-17
- 编译器: Go 1.26.4
- 状态: built

## 编译步骤

curlie 是一个Go项目，没有传统的 configure/make 构建系统。
使用 Go 编译命令直接构建：

```bash
cd /data/storage/el2/base/cache/builds/curlie-1.8.2.work
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -o curlie .
```

安装到 staging 目录：
```bash
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
cp curlie $TEST_PREFIX/$DEFAULT_PREFIX/bin/curlie
chmod 755 $TEST_PREFIX/$DEFAULT_PREFIX/bin/curlie
```

安装到本地 prefix：
```bash
mkdir -p $DEFAULT_PREFIX/bin
cp curlie $DEFAULT_PREFIX/bin/curlie
chmod 755 $DEFAULT_PREFIX/bin/curlie
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ohc-run.py 自动模式检测构建系统为unknown | curlie是Go项目，无configure/make | 手动使用go build编译 |

## 依赖版本

- Go 1.26.4 (go version go1.26.4 linux/arm64)

## 验证结果

```bash
$DEFAULT_PREFIX/bin/curlie --version
curl 8.8.0 (HarmonyOS) libcurl/8.8.0 OpenSSL/1.1.1w zlib/1.3.1
```

curlie 是 curl 的前端封装，--version 显示底层 curl 的版本信息。

## 注意事项

- Go项目不需要configure/make，直接使用go build
- CGO_ENABLED=0 禁用CGO以生成纯Go静态链接二进制
- 生成的二进制为静态链接，无动态库依赖
---

**编译结束**: 2026-06-17 23:02
**最终状态**: published
