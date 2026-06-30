# apko 1.2.17 适配笔记

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

2. 编译release版本:
   ```
   go build -trimpath -ldflags "-buildid= -X sigs.k8s.io/release-utils/version.gitVersion=1.2.17 -X sigs.k8s.io/release-utils/version.gitCommit=unknown -X sigs.k8s.io/release-utils/version.gitTreeState=clean -X sigs.k8s.io/release-utils/version.buildDate=2026-06-17" -o apko ./
   ```

3. 编译debug版本:
   ```
   go build -ldflags "-buildid= -X sigs.k8s.io/release-utils/version.gitVersion=1.2.17 -X sigs.k8s.io/release-utils/version.gitCommit=unknown -X sigs.k8s.io/release-utils/version.gitTreeState=clean -X sigs.k8s.io/release-utils/version.buildDate=2026-06-17" -o apko-debug ./
   ```

4. 签名:
   ```
   binary-sign-tool sign -selfSign 1 -inFile apko -outFile .../bin/apko -signAlg SHA256withECDSA
   binary-sign-tool sign -selfSign 1 -inFile apko-debug -outFile .../bin/apko-debug -signAlg SHA256withECDSA
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | go.mod requires Go >= 1.26.0, local Go is 1.22.10 | apko项目依赖新版Go | 使用已安装的Go 1.26.3 SDK (/storage/Users/currentUser/sdk/go1.26.3/go) |
| 2 | Go自动下载toolchain失败(permission denied) | HarmonyOS上下载的ELF未签名不可执行 | 使用本地已安装的Go 1.26.3 SDK, GOTOOLCHAIN=local |
| 3 | 依赖chainguard.dev/sdk需要Go >= 1.26.0 | 依赖版本要求新版Go | 使用Go 1.26.3满足依赖要求 |
| 4 | binary-sign-tool签名失败 | 签名输出文件路径需要权限 | 使用-selfSign 1模式签名 |

## 依赖版本

- Go: 1.26.3 (linux/arm64)
- 目标: HarmonyOS NEXT (musl libc, aarch64)
- CGO_ENABLED=0 (纯Go静态编译)

## 验证结果

```bash
$ apko version
GitVersion:    1.2.17
GitCommit:     unknown
GitTreeState:  clean
BuildDate:     2026-06-17
GoVersion:     go1.26.3
Compiler:      gc
Platform:      linux/arm64
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| apko | 38MB | release版本 (static, arm64) |
| apko-debug | 38MB | debug版本 (static, arm64, not stripped) |

## 注意事项

- apko是Chainguard的APK-based OCI image builder，纯Go项目
- CGO_ENABLED=0编译，不依赖musl libc，纯静态二进制
- 版本信息通过ldflags注入sigs.k8s.io/release-utils/version包
