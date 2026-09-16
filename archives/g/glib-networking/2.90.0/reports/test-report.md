# glib-networking 2.90.0 测试报告

## HarmonyOS 专项测试 + 消费者验证（test_package/test_tls_backend.c）

消费者用例：`test_tls_backend`，模拟业务上层 TLS 客户端组件，仅通过 GLib 公开
TLS API（`g_tls_backend_get_default` / `g_tls_backend_supports_tls` /
`g_tls_client_connection_new` / `g_tls_connection_handshake` / GSocket API）
和 glib-networking 安装产物（`lib/gio/modules/libgioopenssl.so` GIO 模块，运行时
经 GIO_EXTRA_MODULES 加载）使用本库，不引用私有头文件或内部符号。

### 构建命令
```
cd archives/g/glib-networking/2.90.0/test_package
conan test . glib-networking/2.90.0 \
  -pr:h=<profile> -pr:b=<profile> -o 'glib-networking/*:shared=True'
```
- cwd：archives/g/glib-networking/2.90.0/test_package
- 退出码：0（10 passed, 0 failed）

### 运行输出（关键证据）
```
backend type: GTlsBackendOpenssl
PASS: g_tls_backend_get_default() returns non-NULL
PASS: backend supports TLS
PASS: backend exposes a certificate type
PASS: created server GSocket
PASS: server socket bound
PASS: server socket listening
PASS: client socket connected
PASS: server accepted the client connection
PASS: created GTlsClientConnection through real backend
GTlsClientConnection type: GTlsClientConnectionOpenssl
PASS: handshake returned a backend TLS error (real module code path)
TLS handshake error (expected for non-TLS peer): Error reading data from TLS socket: wrong version number
RESULT: 10 passed, 0 failed
```

### 验证的公开 API 与可观察结果
| 公开 API | 可观察结果 |
|----------|-----------|
| g_tls_backend_get_default() | 返回 GTlsBackendOpenssl（非 GDummyTlsBackend）|
| g_tls_backend_supports_tls() | true |
| g_tls_backend_get_certificate_type() | 有效 GType |
| g_tls_client_connection_new() | 创建 GTlsClientConnectionOpenssl |
| g_tls_connection_handshake() | 对非 TLS 对端返回真实后端错误（wrong version number），证明 openssl 模块代码路径执行 |

### GDummy 对照记录
未安装 glib-networking 模块时，g_tls_backend_get_default() 返回 GDummyTlsBackend
（空实现）——即 libsoup3 http2 上游测试 35 项注册后 0 执行（`if(!tls_available)
return 0;`）的根因。加载本库 gioopenssl 模块后返回 GTlsBackendOpenssl，TLS 可用。

### 上游测试
见 notes.md「上游测试完整枚举台账」：80/98（81.6%）源码口径、80/80（100%）
当前配置可执行集合通过率；4 个 meson test 条目 122 项次全部 ok、0 fail，
testlog 见 conan build 目录 meson-logs/testlog.txt。