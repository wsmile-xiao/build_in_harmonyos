# hub 2.14.2 适配笔记

## 编译环境
- 构建系统: go (Go modules)
- 编译日期: 2026-06-05
- 编译器: go 1.24.2
- 状态: built

## 编译步骤

1. 下载源码: `curl -L -k -o hub-2.14.2.tar.gz https://github.com/mislav/hub/archive/refs/tags/v2.14.2.tar.gz`
2. 解压: `tar -xzf downloads/hub-2.14.2.tar.gz -C ~/tmp/builds/`
3. 初始化: `ohc-run.py init-build hub 2.14.2 --url=file:///...`
4. 编译命令:
   ```bash
   export GOROOT=/storage/Users/currentUser/usr/local/go
   export GOTOOLCHAIN=local
   export GOCACHE=/data/storage/el2/base/cache/go-cache-hub
   export GOPROXY=https://goproxy.cn,direct
   go build -a -ldflags "-X github.com/github/hub/version.Version=2.14.2" -o bin/hub .
   ```
5. 安装: `cp bin/hub $DESTDIR/$PREFIX/bin/`
6. 签名: `ohc-run.py sign-elf`
7. 打包: `ohc-run.py package hub 2.14.2`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | GitHub API 证书问题 | 使用 curl -k 手动下载 |
| 2 | Go 版本不匹配错误 (go1.23.6 vs go1.24.2) | GOROOT 设置错误导致使用旧版本工具 | 设置 GOROOT=/storage/Users/currentUser/usr/local/go |
| 3 | vendor 目录预编译包版本不匹配 | vendor 用 go1.23.6 编译 | 删除 vendor 目录，使用 go mod download |
| 4 | GOPROXY 网络超时 | proxy.golang.org 访问慢 | 使用 GOPROXY=https://goproxy.cn,direct |
| 5 | 链接器权限错误 | SELinux/安全限制 | 设置 TMPDIR=/data/storage/el2/base/cache |

## 源码修改

无补丁，直接使用原始源码编译。

## 依赖版本

- go 1.24.2
- git 2.45.2 (运行时依赖)

## 验证结果

```bash
$ hub version
git version 2.45.2
hub version 2.14.2
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| hub-2.14.2-ohos-aarch64.tar.gz | 7.5MB | 预编译包 (stripped) |
| hub-2.14.2-ohos-aarch64-debug.tar.gz | 3.4MB | 调试符号包 |

## 注意事项

1. **Go 版本问题**: 系统中存在多个 Go 安装 (go, go122, go1263)，必须显式设置 GOROOT 指向正确的 go 1.24.2 目录
2. **GOTOOLCHAIN**: 必须设置为 `local` 防止 Go 自动下载其他版本工具链
3. **网络依赖**: hub 需要下载 Go 依赖，建议使用国内镜像 goproxy.cn
4. **运行时依赖**: hub 依赖 git 命令，需要确保 git 已安装

## 知识沉淀

### Go 项目编译要点 (L2)
- Go 项目需要正确设置 GOROOT，避免使用旧版本工具
- GOTOOLCHAIN=local 可防止自动工具链切换
- 使用 GOPROXY 国内镜像解决网络问题
- vendor 目录可能包含旧版本预编译包，需要清理后重新下载
---

**编译结束**: 2026-06-05 11:32
**最终状态**: built
