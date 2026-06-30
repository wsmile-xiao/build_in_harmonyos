# Notes — scw 2.56.1

## 编译环境
- 平台: OpenHarmony (aarch64)
- Go: 1.26.4 (harmonybrew)
- CGO_ENABLED=0 (静态编译)
- GOPROXY: https://goproxy.cn,direct

## 编译步骤
1. 源码已存在于本地 /data/storage/el2/base/cache/builds/scw-2.56.1.work
2. 使用 `go build` 编译:
   ```
   CGO_ENABLED=0 GOPROXY=https://goproxy.cn,direct \
   go build -ldflags="-s -w -X main.Version=2.56.1" -o scw ./cmd/scw/
   ```
3. Staging: cp scw $TEST_PREFIX/$DEFAULT_PREFIX/bin/
4. 安装: cp scw $DEFAULT_PREFIX/bin/
5. 验证: scw version → Version 2.56.1

## 特殊说明
- 这是Go项目，不是autotools项目，无需configure/make
- GitHub下载需要使用国内镜像 (ghfast.top) + SSL bypass
- scw --version 无效，正确命令是 `scw version`
- 编译产物为静态可执行文件 (CGO_ENABLED=0)，无需外部库依赖
- 已strip (-s -w)，最终二进制约50MB

## 编译结束
**最终状态**: built