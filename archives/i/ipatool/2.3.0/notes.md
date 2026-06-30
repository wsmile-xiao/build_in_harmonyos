# ipatool 2.3.0 适配笔记

## 编译环境
- 构建系统: go (Go modules)
- 编译日期: 2026-06-08
- 编译器: go 1.24.2
- 状态: built

## 编译步骤

1. 下载源码: `curl -L -o ipatool-v2.3.0.tar.gz "https://api.github.com/repos/majd/ipatool/tarball/v2.3.0"`
2. 解压: `tar -xzf ipatool-v2.3.0.tar.gz -C ~/tmp/builds/`
3. 编译命令:
   ```bash
   export GOROOT=/storage/Users/currentUser/usr/local/go
   export GOTOOLCHAIN=local
   export GOPROXY=https://goproxy.cn,direct
   export GOCACHE=/data/storage/el2/base/cache/go-cache-ipatool
   export TMPDIR=/data/storage/el2/base/cache
   go build -ldflags="-X github.com/majd/ipatool/v2/cmd.version=2.3.0" -o ipatool .
   ```
4. 签名: `ohc-run.py sign-elf ipatool`
5. 安装: `cp ipatool ~/usr/local/bin/`
6. 打包: `tar -czvf ipatool-2.3.0-ohos-aarch64.tar.gz`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Savannah SSL 证书验证失败 | Savannah 站点证书问题 | 改用 GitHub 源码 |
| 2 | Go runtime write barrier 错误 | GOROOT 设置错误 | 设置 GOROOT=/storage/Users/currentUser/usr/local/go |
| 3 | 链接器权限错误 | TMPDIR 路径权限问题 | 设置 TMPDIR=/data/storage/el2/base/cache |
| 4 | 版本号显示 "dev" | ldflags 参数名错误 | 使用 -X github.com/majd/ipatool/v2/cmd.version=2.3.0 |

## 源码修改

无补丁，直接使用原始源码编译。

## 依赖版本

- go 1.24.2

## 验证结果

```bash
$ ipatool --version
ipatool version 2.3.0

$ ipatool --help
A cli tool for interacting with Apple's ipa files

Usage:
  ipatool [command]

Available Commands:
  auth                 Authenticate with the App Store
  download             Download (encrypted) iOS app packages from the App Store
  search               Search for iOS apps available on the App Store
  ...
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ipatool-2.3.0-ohos-aarch64.tar.gz | 14.4MB | 预编译包 |
| ipatool (二进制) | 14.4MB | ELF executable, 64-bit LSB arm64 |

## 注意事项

1. **Go 版本问题**: 必须显式设置 GOROOT=/storage/Users/currentUser/usr/local/go，否则会使用错误的 Go 版本导致 runtime 错误
2. **GOTOOLCHAIN**: 必须设置为 `local` 防止 Go 自动下载其他版本工具链
3. **网络依赖**: 需要下载 Go 依赖，建议使用国内镜像 goproxy.cn
4. **签名**: 编译后必须使用 ohc-run.py sign-elf 签名才能在鸿蒙系统上执行

## 知识沉淀

### Go 项目编译要点 (L2)
- Go 项目需要正确设置 GOROOT=/storage/Users/currentUser/usr/local/go
- GOTOOLCHAIN=local 可防止自动工具链切换
- 使用 GOPROXY=https://goproxy.cn,direct 解决网络问题
- 版本号通过 -ldflags 设置: -X {module}/cmd.version={version}
- Savannah 等国外站点可能无法访问，优先使用 GitHub 源码

---

**编译结束**: 2026-06-08 17:33
**最终状态**: built