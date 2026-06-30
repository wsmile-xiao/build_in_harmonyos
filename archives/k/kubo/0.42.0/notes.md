# kubo 0.42.0 适配笔记

## 编译环境
- 构建系统: custom (Go build)
- 编译日期: 2026-06-17
- 编译器: Go 1.26.3 (from /storage/Users/currentUser/sdk/go1.26.3/go)
- Go工具链: GOTOOLCHAIN=local
- 状态: built

## 编译步骤

1. 设置编译环境变量:
   ```
   export GOROOT=/storage/Users/currentUser/sdk/go1.26.3/go
   export GOPATH=/storage/Users/currentUser/tmp/gopath
   export GOCACHE=/data/storage/el2/base/haps/entry/files/go-build
   export GOOS=linux GOARCH=arm64
   export CGO_ENABLED=0
   export TMPDIR=/data/storage/el2/base/haps/entry/temp
   export GOTOOLCHAIN=local
   ```

2. 修改go.mod将Go版本从1.26.4降级为1.26.3:
   ```
   go mod edit -go=1.26.3 -toolchain=none
   ```

3. 编译release版本:
   ```
   go build -trimpath -ldflags "-X github.com/ipfs/kubo.CurrentCommit=v0.42.0 -X github.com/ipfs/kubo.taggedRelease=true -X github.com/ipfs/kubo.buildOrigin=github.com/ipfs/kubo -buildid=" -o ipfs ./cmd/ipfs
   ```

4. 编译debug版本:
   ```
   go build -ldflags "-X github.com/ipfs/kubo.CurrentCommit=v0.42.0 -X github.com/ipfs/kubo.taggedRelease=true -X github.com/ipfs/kubo.buildOrigin=github.com/ipfs/kubo -buildid=" -o ipfs-debug ./cmd/ipfs
   ```

5. 签名:
   ```
   binary-sign-tool sign -selfSign 1 -inFile ipfs -outFile .../bin/ipfs -signAlg SHA256withECDSA
   binary-sign-tool sign -selfSign 1 -inFile ipfs-debug -outFile .../bin/ipfs-debug -signAlg SHA256withECDSA
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | go.mod requires Go >= 1.26.4 | kubo项目需要Go 1.26.4 | 使用go mod edit降级为1.26.3(我们有的版本) |
| 2 | Go自动下载toolchain失败 | HarmonyOS上下载的ELF未签名不可执行 | 使用本地Go 1.26.3 SDK, GOTOOLCHAIN=local |
| 3 | kubo构建系统使用gmake | HarmonyOS无gmake | 直接使用go build代替make |
| 4 | 版本信息注入路径 | kubo使用github.com/ipfs/kubo包 | 通过ldflags注入CurrentCommit/taggedRelease/buildOrigin |

## 源码修改

- go.mod: 将 `go 1.26.4` 降级为 `go 1.26.3`，添加 `toolchain=none`

## 依赖版本

- Go: 1.26.3 (linux/arm64)
- 目标: HarmonyOS NEXT (musl libc, aarch64)
- CGO_ENABLED=0 (纯Go静态编译)

## 验证结果

```bash
$ ipfs version
ipfs version 0.42.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ipfs | 83MB | release版本 (static, arm64) |
| ipfs-debug | 84MB | debug版本 (static, arm64, not stripped) |

## 注意事项

- kubo是IPFS的Go实现，项目较复杂，依赖链很长
- 输出二进制名称为ipfs（不是kubo）
- CGO_ENABLED=0编译，不依赖musl libc
- 版本信息通过ldflags注入github.com/ipfs/kubo包
