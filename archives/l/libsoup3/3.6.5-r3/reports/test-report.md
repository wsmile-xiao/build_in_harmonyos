# libsoup3 3.6.5-r3 上游测试双口径台账（R11）

## 运行环境

- worktree: /storage/Users/currentUser/junshi_liu/worktrees/pc3-12-libsoup3-3.6.5
- branch: fix/libsoup3-3.6.5-r3
- build: /storage/Users/currentUser/.conan2/p/b/libso2bca687fa0e6d/b/builddir（conan create 产物，-Dtests=true 复验构建）
- 工具链: clang 15.0.4 (aarch64-linux-ohos, OHOS 6.0)
- glib: /2.84.0.1.1 (shared) + libpsl/0.21.5.1 + libnghttp2/1.70.0 + sqlite3/3.49.1 + zlib/1.3.1.1
- TMPDIR=/storage/Users/currentUser/tmp（/tmp 只读）
- TLS: GDummyTlsBackend 可用（supports_tls=0，无 glib-networking 包），AF_UNIX bind EPERM（OHOS 安全策略）

## 双口径统计（R11 补丁后）

| 口径 | 数量 | 说明 |
|---|---|---|
| source_declared_total | 33 | meson test 注册的独立可执行用例数（tests/meson.build 声明） |
| configured_executable_total | 33 | 当前 OHOS 配置实际构建出的测试二进制 |
| executed_passed_total | 28 | 补丁后实跑通过 28 个二进制（含 380 个子用例 subtest） |
| failed | 3 | hsts-test、hsts-db-test（无 TLS 后端连接拒绝）、unix-socket-test（AF_UNIX EPERM） |
| skipped | 2 | http2-test、ssl-test（无 glib-networking TLS 后端） |
| 通过率（二进制） | 28/33 = 84.8% | 不含 SKIP |

meson test 汇总：`Ok: 28  Fail: 3  Skipped: 2`

## hsts/hsts-db 28 项逐项实跑（R11 核心，补丁后）

补丁前：`g_uri_get_port(NULL)` → GLib-FATAL-CRITICAL 'uri != NULL' → SIGTRAP exit 133（进程直接崩溃）。
补丁后（判空守卫）：不再 SIGTRAP；进程正常运行，逐项结果如下（命令：`./hsts-test -p /hsts/<name>`，LD_LIBRARY_PATH 含 glib/libpsl/libnghttp2/usr-local/lib）：

| # | 用例 | exit | 结果 | 说明 |
|---|---|---|---|---|
| 1 | /hsts/case-insensitive-header | 134 | 阻塞 | https server 无 TLS 后端，连接拒绝 |
| 2 | /hsts/basic | 134 | 阻塞 | 同上 |
| 3 | /hsts/expire | 134 | 阻塞 | 同上 |
| 4 | /hsts/delete | 1 | 未通过 | 同上 |
| 5 | /hsts/replace | 134 | 阻塞 | 同上 |
| 6 | /hsts/update | 134 | 阻塞 | 同上 |
| 7 | /hsts/set_and_delete | 134 | 阻塞 | 同上 |
| 8 | /hsts/no_hsts_header | 134 | 阻塞 | 同上 |
| 9 | /hsts/persistency | 134 | 阻塞 | 同上 |
| 10 | /hsts/subdomains | 134 | 阻塞 | 同上 |
| 11 | /hsts/superdomain | 134 | 阻塞 | 同上 |
| 12 | /hsts/multiple-headers | 134 | 阻塞 | 同上 |
| 13 | /hsts/insecure-sts | 0 | ✅ 通过 | 纯 http，无 TLS 依赖 |
| 14 | /hsts/missing-values | 1 | 未通过 | https 依赖 |
| 15 | /hsts/invalid-values | 1 | 未通过 | https 依赖 |
| 16 | /hsts/extra-values | 134 | 阻塞 | https 依赖 |
| 17 | /hsts/duplicated-directives | 1 | 未通过 | https 依赖 |
| 18 | /hsts/case-insensitive-directives | 134 | 阻塞 | https 依赖 |
| 19 | /hsts/optional-quotations | 134 | 阻塞 | https 依赖 |
| 20 | /hsts/ip-address | 1 | 未通过 | https 依赖 |
| 21 | /hsts/utf8-address | 134 | 阻塞 | https 依赖 |
| 22 | /hsts/session-policy | 1 | 未通过 | https 依赖 |
| 23 | /hsts/idna-addresses | 0 | ✅ 通过 | 纯 enforcer API，无网络 |
| 24 | /hsts/get-domains | 0 | ✅ 通过 | 纯 enforcer API |
| 25 | /hsts/get-policies | 0 | ✅ 通过 | 纯 enforcer API |
| 26 | /hsts-db/basic | 134 | 阻塞 | https 依赖 |
| 27 | /hsts-db/subdomains | 134 | 阻塞 | https 依赖 |
| 28 | /hsts-db/large-max-age | 134 | 阻塞 | https 依赖 |

hsts-test 25 项：4 通过 / 21 阻塞或未通过；hsts-db-test 3 项：3 阻塞。

### 阻塞首错（统一首错，逐项相同）

```
ERROR:../tests/hsts-test.c:133:session_get_uri: assertion failed (error == NULL):
       Could not connect to localhost: Connection refused (g-io-error-quark, 39)
```

根因：OHOS 无 GIO TLS 后端（glib-networking 未打包，GDummyTlsBackend supports_tls=0），
tls_available=FALSE → main() 不创建 https server → https_uri 保持 NULL → https 用例
（session_get_uri("https://localhost/...")）连接被拒。这是平台级 TLS 后端缺失，
非 libsoup 库代码问题；恢复条件：具备 GIO TLS 后端的 CI/设备上同一 -Dtests=true
构建即可连接 127.0.0.1 本地测试服务并跑通（上游原测试即依赖真实 TLS server）。

注：这些 https 用例在补丁前是进程级 SIGTRAP 崩溃（exit 133），28 项全部无法运行；
补丁后 25 项中的 4 项纯逻辑/纯 http 用例可实际运行并通过，其余 https 依赖项阻塞
归属为平台 TLS 后端缺失（未执行进程崩溃，未伪造通过）。

## 其他测试（R11 全量复验）

28 个通过二进制及其 subtest（样例）：cache 7、chunk-io 1、coding 11、continue 12、
cookies 14、date 66、header-parsing 8、logger 6、multipart 4、no-ssl 1、multithread 8、
redirect 29、ntlm 13、request-body 18、samesite 16、streaming 4、server 16、tld 2、
sniffing 38、misc 18、context 1、uri-parsing 4、session 6、forms 5、timeout 2、
server-auth 12、websocket 55、http2-body-stream 3 —— 合计 380 subtest 全部通过。

skipped 2：http2-test、ssl-test —— 与 hsts 同源：无 glib-networking TLS 后端，
上游测试自身 SOUP_TEST_SKIP_IF_NO_TLS 跳过（这些是上游显式 skip，非崩溃）。

failed 1（非 hsts）：unix-socket-test exit 1 —— OHOS 安全策略禁止 AF_UNIX bind
（EPERM），R02 台账同款平台限制（上游本身环境允许）。

## 运行命令（可复现）

```bash
cd /storage/Users/currentUser/.conan2/p/b/libso2bca687fa0e6d/b
export LD_LIBRARY_PATH=<glib>/lib:<libpsl>/lib:<libnghttp2>/lib:/storage/Users/currentUser/usr/local/lib
meson test -C builddir --timeout-multiplier 8     # 全量 33 项
cd builddir/tests && ./hsts-test -p /hsts/<name>  # 28 项逐项
```

完整 stdout/stderr 日志与逐项台账：reports/hsts-runs/（含 hsts-test.c / hsts-db-test.c
补丁前后对照、sha256 见 notes）。