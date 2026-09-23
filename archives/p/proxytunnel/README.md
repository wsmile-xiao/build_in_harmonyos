# proxytunnel

**通过 HTTPS 代理建立通用隧道**的命令行工具（v1.13.0，纯 C 单一可执行文件，适配 OpenHarmony PC / aarch64 / musl）

proxytunnel 用 HTTP CONNECT 方法穿过代理服务器建立隧道，支持：

- **代理认证** — Basic（`-P user:pass`）、NTLM（`-N`）、凭据文件（`-F`）
- **SSL/TLS 加密** — 与目标端加密（`-e`）、与代理加密（`-E`）、与远端代理加密（`-X`），可指定客户端证书（`-c`/`-k`）、CA（`-C`）、禁用 SNI（`-I`）
- **多级代理** — 本地代理 + 远端代理链（`-p` + `-r`）
- **运行模式** — inetd（`-i`）、standalone 守护（`-a [addr:]port`）

典型用途：让不支持代理认证的程序（如 ssh/cvs）穿过 HTTPS 代理，例如
`ssh -o ProxyCommand="proxytunnel -p proxy:8080 -P user:pass -d sshhost:22" user@sshhost`。

## 构建

- 构建系统：GNU Makefile（无 configure；CC/CFLAGS/LDFLAGS 命令行注入交叉工具链与 OpenSSL 路径）
- 源码：https://github.com/proxytunnel/proxytunnel （tag v1.13.0，sha256 `1b1ae363…849e9`）
- 许可证：GPL-2.0（见 tarball 内 LICENSE.txt）
- 依赖：仅 openssl/3.5.6.1（conan 静态链接，提供 -e/-E/-X 加密）
- 零源码补丁

## OHOS 适配

- **零补丁**：上游对 Linux/musl 兼容良好（strlcpy/strlcat/readpassphrase/setproctitle 均自带实现）
- Makefile 的 pkg-config 探测回退逻辑用命令行 LDFLAGS 接管，显式链接 conan openssl 静态库
- `make install` 的 man 页生成依赖 asciidoc+xmlto（CI 无此工具链），打包仅安装单一二进制
- 产物：`bin/proxytunnel`（aarch64 PIE + GNU_RELRO）

## 验证

test_package 共 8 项断言（全部通过）：`-V` 版本横幅、`--help` 用法、本地 mock 代理上的真实 CONNECT 隧道（请求格式 + 双向数据转发回环）、`-e` SSL_connect 路径（证明 libssl 真实链接）、连接拒绝错误路径。

## 已知限制

- 上游无测试套件（Makefile 无 check 目标），验证以消费者功能测试为准
- man 页未随包分发（构建需 asciidoc+xmlto），用法经 `--help` 获取
