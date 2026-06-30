# wireguard-go 0.0.20250522 适配笔记

## 编译环境
- 构建系统: makefile (Go项目)
- 编译日期: 2026-06-17
- 编译器: go 1.26.4 (Go编译器)
- 状态: built

## 编译步骤

1. 从 GitHub 下载源码: https://github.com/WireGuard/wireguard-go/archive/refs/tags/0.0.20250522.tar.gz
2. 解压源码到工作目录
3. `make wireguard-go` — 使用 Go 编译器构建 (`go build -v -o wireguard-go`)
4. `make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX` — DESTDIR 模式安装
5. `make test` — 运行测试（全部通过）
6. `make install PREFIX=$DEFAULT_PREFIX` — 本地安装验证

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ohc-run.py自动URL搜索失败 | wireguard-go版本号格式特殊（0.0.20250522），搜索引擎未匹配 | 手动指定 --url=https://github.com/WireGuard/wireguard-go/archive/refs/tags/0.0.20250522.tar.gz |
| 2 | SSL证书问题导致下载失败 | 蒙系统缺少CA证书 | 安装CA证书: python3 install-ca-certs.py + 设置CURL_CA_BUNDLE |
| 3 | make install DESTDIR模式路径不匹配 | Makefile默认PREFIX=/usr，脚本期望PREFIX=$DEFAULT_PREFIX | 手动 make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX |
| 4 | G0 clean-verify configure失败 | Go项目无configure脚本，G0验证流程不适配 | 平台限制，已手动验证通过 |

## 依赖版本

- Go 1.26.4 (linux/arm64)
- golang.org/x/crypto v0.37.0
- golang.org/x/net v0.39.0
- golang.org/x/sys v0.32.0
- gvisor.dev/gvisor v0.0.0-20250503011706-39ed1f5ac29c

## 验证结果

```bash
$ wireguard-go --version
wireguard-go v0.0.20250522

Userspace WireGuard daemon for linux-arm64.
```

所有测试通过:
```
ok  golang.zx2c4.com/wireguard      0.110s
ok  golang.zx2c4.com/wireguard/conn  0.051s
ok  golang.zx2c4.com/wireguard/device  0.830s
ok  golang.zx2c4.com/wireguard/ratelimiter  0.031s
ok  golang.zx2c4.com/wireguard/replay  0.029s
ok  golang.zx2c4.com/wireguard/tai64n  0.021s
ok  golang.zx2c4.com/wireguard/tun  1.417s
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| wireguard-go-0.0.20250522-ohos-aarch64.tar.gz | 3.4MB | 预编译包(stripped) |
| wireguard-go-0.0.20250522-ohos-aarch64-debug.tar.gz | 1.5MB | 预编译包(含调试符号) |

## 注意事项

- wireguard-go是纯Go项目，无configure步骤，直接使用`go build`编译
- Go项目生成的是静态链接二进制，无需额外库依赖
- G0 clean-verify对Go项目不适配（无configure脚本），需手动验证
- Makefile的PREFIX默认值是/usr，安装时需明确指定PREFIX=$DEFAULT_PREFIX
- GitHub的tag格式是`0.0.20250522`（无v前缀）
---

**编译结束**: 2026-06-17 22:42
**最终状态**: built
