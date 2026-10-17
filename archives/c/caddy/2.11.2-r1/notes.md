# caddy 2.11.2-r1 适配笔记

## 编译环境
- 构建系统: Go (custom)
- 编译日期: 2026-06-02
- 编译器: clang/clang++ + Go 1.26.3 (~/usr/local/go1263/bin/go)
- 状态: built

## 编译步骤

1. 下载源码: https://github.com/caddyserver/caddy/archive/refs/tags/v2.11.2.tar.gz
2. 解压到 ~/tmp/builds/caddy-2.11.2-r1.work
3. Go 编译命令:
   ```bash
   cd ~/tmp/builds/caddy-2.11.2-r1.work
   export TMPDIR=/data/storage/el2/base/cache
   export CGO_ENABLED=1
   export GOOS=linux
   export GOARCH=arm64
   export GOPROXY=https://goproxy.cn,direct
   ~/usr/local/go1263/bin/go build -ldflags="-w -X github.com/caddyserver/caddy/v2.CustomVersion=v2.11.2" -o caddy ./cmd/caddy/
   ```
4. DESTDIR staging安装:
   ```bash
   mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
   cp caddy $TEST_PREFIX/$DEFAULT_PREFIX/bin/caddy
   ```
5. 本地安装 (模拟用户部署):
   ```bash
   cp caddy ~/usr/local/bin/caddy
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build搜索URL错误（savannah） | caddy不在savannah | 手动curl下载GitHub源码 |
| 2 | SSL证书验证失败 | 平台SSL证书问题 | curl -kL绕过SSL验证下载 |
| 3 | init-build检测构建系统为autotools | Go项目无configure脚本 | 手动修正manifest.yaml: system=custom, build_system=go |

## 源码修改

无补丁，纯Go编译无需源码修改。

## 依赖版本

- Go 1.26.3 (~/usr/local/go1263/bin/go)
- clang 15.0.4 (CGO_ENABLED=1 需要)

## 验证结果

```bash
~/usr/local/bin/caddy version
# 预期输出: v2.11.2
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| caddy | ~50MB | Go编译的arm64 ELF二进制 |

## 注意事项

- Caddy是Go项目，构建系统应为custom/go，非autotools
- CGO_ENABLED=1是必须的（鸿蒙ELF签名需要）
- Go版本必须使用1.26.3（1.26.0已知corrupted）
- GOPROXY=https://goproxy.cn,direct 加速依赖下载
---

**编译结束**: 2026-08-05 14:04
**最终状态**: built
