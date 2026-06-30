# docker 29.5.3 编译笔记

## 项目信息
- **软件**: docker (docker/cli)
- **版本**: 29.5.3
- **构建系统**: Go (Makefile)
- **目标平台**: HarmonyOS NEXT (musl libc, aarch64)

## 编译环境
- **Go**: go1.25.0 linux/arm64 (从 dl.google.com 下载，签名后可用)
- **GOROOT**: /storage/Users/currentUser/tmp/golang/go1.25
- **GOOS**: linux
- **GOARCH**: arm64
- **CGO_ENABLED**: 0 (静态编译)
- **TMPDIR**: /data/storage/el2/base/haps/entry/temp (避免 /tmp 只读问题)

## 源码修改

### 1. go.mod 创建
- 源码仓库使用 `vendor.mod` 而非 `go.mod`（因为使用 CalVer 而非 SemVer）
- 需要复制 `vendor.mod` 为 `go.mod` 以支持 Go module 模式编译
- 同时复制 `vendor.sum` 为 `go.sum`

### 2. go.mod Go 版本调整
- 原始 vendor.mod 指定 `go 1.25.0` 和 `tool` 指令
- 修改: 删除 `tool golang.org/x/mod/modfile // for module compatibility check` 行（Go 1.22 不支持该指令）
- 保持 `go 1.25.0` 版本声明（需要 Go >= 1.23 以满足 vendor 依赖）

## 编译命令
```bash
GOROOT=/storage/Users/currentUser/tmp/golang/go1.25
PATH=$GOROOT/bin:$PATH
export GOOS=linux GOARCH=arm64 CGO_ENABLED=0
export TMPDIR=/data/storage/el2/base/haps/entry/temp
export GOTOOLCHAIN=local DISABLE_WARN_OUTSIDE_CONTAINER=1
export GIT_DISCOVERY_ACROSS_FILESYSTEM=1

go build -mod=vendor -o build/docker \
  -tags 'grpcnotrace' \
  -ldflags '-X "github.com/docker/cli/cli/version.GitCommit=29.5.3" -X "github.com/docker/cli/cli/version.BuildTime=2026-06-17T04:00:00Z" -X "github.com/docker/cli/cli/version.Version=29.5.3"' \
  github.com/docker/cli/cmd/docker
```

## 安装
```bash
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
cp build/docker $TEST_PREFIX/$DEFAULT_PREFIX/bin/docker
cp build/docker $TEST_PREFIX/$DEFAULT_PREFIX/bin/docker-cli
```

## 签名验证
- 所有 ELF 二进制必须使用 binary-sign-tool 或 ohc-run.py sign-elf 签名
- 签名后 docker --version 正常输出: `Docker version 29.5.3, build 29.5.3`

## 验证结果
- ✅ 编译成功
- ✅ 二进制签名后可执行
- ✅ docker --version 输出正确版本号

## 注意事项
1. Go 1.22.10 不足以编译此版本（vendor 依赖要求 Go >= 1.23）
2. 需要下载 Go 1.25.0 并签名后才能使用
3. TMPDIR 必须设置为可写目录（/tmp 在 HarmonyOS 上只读）
4. go.mod 和 go.sum 需从 vendor.mod 和 vendor.sum 复制创建
