# subfinder homebrew 适配笔记

## 编译环境
- 构建系统: custom (Go)
- 编译日期: 2026-06-03
- 编译器: clang/clang++ (CGO_ENABLED=1)
- Go版本: go1.26.3 linux/arm64
- 状态: published

## 编译步骤

1. init-build: `python3 ohc-run.py init-build subfinder homebrew --url=https://github.com/projectdiscovery/subfinder/archive/refs/tags/v2.14.0.tar.gz --no-download`
   - GitHub直连下载失败(SSL超时)，通过 gh-proxy.com 镜像手动下载 v2.14.0.tar.gz
2. 修改 manifest.yaml: system=custom, build_system=go, 添加 go_entrypoint 和 go_ldflags
3. Go编译:
   ```bash
   CGO_ENABLED=1 GOOS=linux GOARCH=arm64 GOPROXY=https://goproxy.cn,direct ~/usr/local/go1263/bin/go build \
     -ldflags="-s -w -X github.com/projectdiscovery/subfinder/v2/pkg/runner.version=v2.14.0" \
     -o subfinder ./cmd/subfinder/
   ```
4. DESTDIR staging: `cp subfinder $TEST_PREFIX/$DEFAULT_PREFIX/bin/subfinder`
5. 本地安装: `cp subfinder $DEFAULT_PREFIX/bin/subfinder`
6. ELF签名: `python3 ohc-run.py sign-elf`
7. 验证: `~/usr/local/bin/subfinder --version` → v2.14.0
8. verify-build → PASS (G1-G4)
9. package: subfinder-homebrew-ohos-aarch64.tar.gz (29701KB)
10. finish: built → published

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub SSL下载超时 | 网络限制，无法直连github.com | 使用 gh-proxy.com 镜像手动下载，然后 --no-download 传入 |
| 2 | init-build 默认识别为 autotools | Go项目无 configure/make | 手动修改 manifest.yaml: system=custom, build_system=go |
| 3 | G0 干净构建验证失败 | G0 试图运行 ./configure（Go项目没有） | 已手动验证通过，Go项目无需configure |

## 源码修改

无源码修改。版本注入通过 -ldflags 实现，不修改源文件。

## 依赖版本

- Go: 1.26.3 (~/usr/local/go1263/bin/go)
- CGO_ENABLED=1, 动态链接 musl (/lib/ld-musl-aarch64.so.1)
- GOPROXY=https://goproxy.cn,direct (中国镜像加速)

## 验证结果

```bash
$ ~/usr/local/bin/subfinder --version
[INF] Current Version: v2.14.0
[INF] Subfinder Config Directory: /data/storage/el2/base/haps/entry/files/subfinder
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| subfinder-homebrew-ohos-aarch64.tar.gz | 29701KB | 预编译包(ELF已签名) |
| subfinder (binary) | 30408969 bytes (~30MB) | ELF arm64 动态链接 |

## 注意事项

- subfinder 是 Go 项目，使用 custom 构建系统，不走 configure/make 流程
- 版本常量在 pkg/runner/banners.go 中定义，通过 ldflags -X 注入
- GOPROXY 使用 goproxy.cn 镜像加速依赖下载
- GitHub 网络受限，需要使用代理镜像下载源码
---

**编译结束**: 2026-06-03 10:28
**最终状态**: built
---

**编译结束**: 2026-06-03 10:29
**最终状态**: published
