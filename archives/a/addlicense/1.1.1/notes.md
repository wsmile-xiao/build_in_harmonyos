# addlicense 1.1.1 适配笔记

## 编译环境
- 构建系统: Go (1.26.4)
- 编译日期: 2026-06-08
- 编译器: Go (CGO_ENABLED=0, 静态编译)
- 状态: published

## 编译步骤

1. 下载源码：从 GOPROXY=https://goproxy.cn,direct 获取源码 zip
2. 解压并重构源码目录（goproxy.cn zip有嵌套目录结构）
3. 编译命令：
```bash
cd $BUILD_SRC_DIR
PATH=~/.harmonybrew/bin:$PATH CGO_ENABLED=0 GOPROXY=https://goproxy.cn,direct go build -ldflags="-s -w" -o addlicense .
```
4. 安装到 staging 目录和本地 ~/usr/local

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | v1.1.2不存在 | GitHub仓库只有v1.0.0/v1.1.0/v1.1.1/v1.2.0 | 使用v1.1.1（最新1.1.x版本） |
| 2 | gh.idayer.com下载失败 | SSL证书验证失败 | 使用goproxy.cn获取源码 |
| 3 | goproxy.cn zip有嵌套目录 | Go模块缓存格式 | 重构：移动文件到work目录根 |

## 依赖版本

- Go 1.26.4 (harmonybrew)

## 验证结果

```bash
$ ~/usr/local/bin/addlicense --help
Usage: addlicense [flags] pattern [pattern ...]

The program ensures source code files have copyright license headers
by scanning directory patterns recursively.

Flags:
  -c string     copyright holder (default "Google LLC")
  -check        check only mode
  -f string     license file
  -l string     license type: apache, bsd, mit, mpl (default "apache")
  -s            Include SPDX identifier in license header
  -v            verbose mode
  -y string     copyright year(s) (default "2026")
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| addlicense-1.1.1-ohos-aarch64.tar.gz | 3.3MB | 预编译包(ELF arm64 静态) |

## 注意事项

- 无需补丁，Go项目直接编译
- CGO_ENABLED=0确保纯静态编译，无需动态库依赖
- addlicense是纯Go项目，不使用configure/make构建系统
---
**编译结束**: 2026-06-08 22:09
**最终状态**: published