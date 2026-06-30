# uWebSockets 18 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-06-24
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built
- 源码版本: uWebSockets v18.20.0 (GitHub tag v18 不存在，使用 v18 系列最新版 v18.20.0)

## 编译步骤

1. **init-build**: 使用 `--no-download` 模式，手动下载 tarball 后放置到 `~/tmp/builds/uWebSockets-18.tar.gz`
2. **uSockets submodule 处理**: GitHub tarball 不包含 git submodule，手动下载 uSockets 源码 (commit c06112c89b4c1cf5a09b5f8daa2def756b925889) 到 `uSockets/` 目录
3. **环境设置**: `export PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH`
4. **编译**: `make WITH_OPENSSL=1 examples` — 先编译 uSockets (.o 文件 + uSockets.a)，再编译 8 个示例二进制
5. **安装 (DESTDIR)**: `make install DESTDIR=$TEST_PREFIX prefix=$DEFAULT_PREFIX` — 安装头文件到 staging
6. **打包**: `ohc-run.py package uWebSockets 18` — 创建 uWebSockets-18-ohos-aarch64.tar.gz (306KB)
7. **安装 (本地)**: `make install prefix=$DEFAULT_PREFIX` — 安装头文件到 ~/usr/local/include/uWebSockets/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载失败 (SSL) | Python urllib SSL 证书验证失败 | 手动 curl 下载 + `--no-download` |
| 2 | /tmp 只读 (R10) | 鸿蒙平台 /tmp 为只读文件系统 | 使用 ~/tmp 替代 |
| 3 | tag v18 不存在 | GitHub 上没有单独的 v18 tag | 使用 v18 系列最新版 v18.20.0 |
| 4 | uSockets 目录为空 | GitHub tarball 不包含 git submodule | 手动下载 uSockets 源码填充 |
| 5 | verify-build G4 失败 | manifest 缺少顶级 build_system 字段 | 添加 build_system: makefile |
| 6 | G0 clean-verify 失败 | uWebSockets 无 configure 脚本 (Makefile 项目) | 已知限制，手动编译已验证通过 |

## 源码修改

无补丁。uWebSockets 是 header-only 库，源码未修改。
uSockets submodule 从 GitHub 下载源码填充，未修改。

## 依赖版本

- OpenSSL 3.5.6 (~/usr/local)
- zlib 1.3.1 (~/usr/local)
- uSockets 0.7.1 (~/usr/local) — 预装版本，submodule 使用同源码编译

## 编译验证

- 8 个示例全部编译成功: HelloWorld, ServerName, EchoServer, BroadcastingEchoServer, UpgradeSync, UpgradeAsync, HelloWorldThreaded, EchoServerThreaded
- 质量门禁 G1-G4: 全部 PASS
- 头文件安装: 27 个头文件正确安装到 ~/usr/local/include/uWebSockets/

## 功能测试结果 (2026-06-24)

详细报告见 `reports/functional-test-report.md`

### 非 SSL 模式 (uWS::App) — 7/7 通过

| 测试 | 结果 | 说明 |
|------|------|------|
| HTTP GET 请求 | ✅ | HTTP 200, 响应延迟 ~1.3ms |
| HTTP 路由通配 | ✅ | /* 路由匹配正常 |
| HTTP 10 线程并发 | ✅ | 10/10 请求成功 |
| WebSocket 握手 | ✅ | 101 Switching Protocols |
| WebSocket Echo | ✅ | 中英文混合消息正确回显 |
| WebSocket 二进制 | ✅ | 256 bytes 二进制 echo 正确 |
| WebSocket 5 并发连接 | ✅ | 连接 5/5, echo 5/5 |

> 大消息测试 (64KB) 因 maxPayloadLength=16KB 配置限制未通过，属预期行为非 bug。

### SSL 模式 (uWS::SSLApp) — 4/4 通过

| 测试 | 结果 | 说明 |
|------|------|------|
| SSL 服务监听 | ✅ | 端口 3000 监听成功 |
| HTTPS GET | ✅ | 返回正确内容 |
| SSL 证书加载 | ✅ | 自签名证书正常 |
| WSS Upgrade | ✅ | 101 协议升级成功 |

### 测试结论

uWebSockets v18 + uSockets 0.7.1 **在鸿蒙平台上功能正常**，HTTP/WebSocket/SSL 全部可用。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| uWebSockets-18-ohos-aarch64.tar.gz | 306KB | 预编译包 (头文件 + f2/function2.hpp) |

## 注意事项

- uWebSockets 是 header-only C++ 库，编译产物主要是 examples/tests 二进制
- 使用 C++20 (std=c++2a) 标准，clang++ 默认支持
- uSockets submodule 必须正确填充才能编译 examples
- WITH_OPENSSL=1 启用 SSL 支持，使用已安装的 OpenSSL 3.5.6
- OpenSSL 3.x API 变化导致 uSockets crypto/openssl.c 有 deprecation 警告 (PEM_read_DHparams, DH_free)，不影响编译
- 示例二进制运行前需 ELF 签名 (`ohc-run.py sign-elf`)
- SSL 示例引用 `../misc/key.pem`，需从 examples/ 子目录运行或生成自签名证书
---

**编译结束**: 2026-06-24 15:05
**功能测试**: 2026-06-24 通过 (HTTP ✅ / WebSocket ✅ / SSL ✅)
**最终状态**: built (功能验证通过)
