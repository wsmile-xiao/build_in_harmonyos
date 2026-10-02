# bozohttpd 20260503

- 上游：NetBSD `src/libexec/httpd`，对应 pkgsrc distfile `bozohttpd-20260503.tar.bz2`。
- 构建：GNU make 使用上游可移植 `Makefile.boot`；NetBSD blocklist 与 Lua 按该 Makefile 的默认配置关闭。
- 移植补丁：将上游 NetBSD printf 扩展 `%qd` 改为标准 `%lld`；OHOS libc 不支持 `%qd`，会导致 HTTP `Content-Length` 为空。
- TLS：默认使用仓库已有 `openssl/3.0.21` 静态库；Conan 选项 `with_ssl=False` 可移除 TLS 和 OpenSSL 依赖。
- 安装：`bin/bozohttpd`、`bin/httpd` 与 man8 手册。
- 测试：`test_package` 保留并逐项执行上游 20 个测试（17 个简单请求/响应、1 个 CGI、2 个大文件 Range 续传）；另有 12 条消费者断言，其中 4 条检查 AArch64 ELF，8 条检查版本输出和 loopback HTTP 响应。夹具作为 Base64 文本纳入仓库，在临时目录按原字节还原（包括上游隐藏文件 `.bzremap`），不会改写输入或预期响应。CI 目标不可运行时会明确失败，避免跳过功能测试。
