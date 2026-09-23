# DRAFT-hsts-g_uri_get_port-null-guard

## 问题

上游 libsoup 3.6.5 tests/hsts-test.c 与 tests/hsts-db-test.c 的
`rewrite_message_uri()` 对 `g_uri_get_port(https_uri)` 无条件调用。OHOS 无
glib-networking（GIO 回退 GDummyTlsBackend，supports_tls=0）时
`tls_available=FALSE`，测试 main() 不创建 https server，`https_uri` 保持 NULL。
glib 2.84 对 `g_uri_get_port(NULL)` 触发 `GLib-FATAL-CRITICAL assertion
'uri != NULL' failed` → SIGTRAP（exit 133），hsts(25)+hsts-db(3)=28 项进程级
崩溃、全部无法运行。

## 根因

上游测试调用缺陷（非 libsoup 库代码问题）：在 TLS 后端不可用环境下对可能为
NULL 的 GUri 调用 g_uri_get_port，与 glib 2.84 断言语义不兼容，属测试迁移补丁范畴。

## 方案（最小改动，只改 tests/hsts-test.c 与 tests/hsts-db-test.c）

定位调用点（hsts-test.c:151/153、hsts-db-test.c:106/108），按 glib 2.84 语义
判空守卫，不得传入 NULL：

```c
else if (soup_uri_is_https (soup_message_get_uri (msg)))
    /* R11 测试迁移（glib 2.84 语义）：TLS 后端不可用时 https_uri 为 NULL，
     * 直接 g_uri_get_port(NULL) 触发 'uri != NULL' 断言 SIGTRAP。判空：
     * uri 有效才取端口，否则保持消息 URI 原样。测试语义不变。 */
    new_uri = https_uri != NULL
        ? soup_uri_copy (soup_message_get_uri (msg), SOUP_URI_PORT,
                         g_uri_get_port (https_uri), SOUP_URI_NONE)
        : g_uri_ref (soup_message_get_uri (msg));
```

每处修改原因相同（同一 NULL 传入缺陷）；http 分支不动；https 分支在无 TLS 后端
时保持原 URI（本就不会实际发出请求）。

## 验证

- 补丁后 `-Dtests=true` 重建，`./hsts-test -p /hsts/<name>` 逐项实跑 28 项：
  - 不再 SIGTRAP（exit 133 消失）；
  - hsts-test 25 项中 4 项通过（insecure-sts、idna-addresses、get-domains、
    get-policies，纯 http/纯 enforcer API，无 TLS 依赖）；
  - 其余 https 依赖项统一首错 `Could not connect to localhost: Connection
    refused (g-io-error-quark, 39)`——阻塞归属=平台 GIO TLS 后端缺失
    （glib-networking 未打包），恢复条件=具备 TLS 后端的 CI/设备上重跑；
  - hsts-db-test 3 项同属 https 依赖阻塞。
- 全量 meson test：33 项注册，28 OK / 3 FAIL（hsts-test、hsts-db-test、
  unix-socket-test=AF_UNIX EPERM）/ 2 SKIP（http2/ssl，上游显式 skip）。

## 适用边界 / 反例

- 适用：glib 2.84+ 环境下对可能为 NULL 的 GUri 调用 g_uri_get_port 的上游测试；
  无 GIO TLS 后端（GDummyTlsBackend）的 OHOS/受限环境。
- 反例：有 glib-networking 的环境 https_uri 非空，不触发断言，无需迁移。

## 查重关系

- caused_by: DRAFT-libsoup3-r3-glib-shared-recipe-fix（同库 R11 适配；发布形态
  修复与测试迁移为两独立草稿）
- similar_to: E259（assert 相关，机制不同）、E040（NULL 指针系，机制不同）
- 七轴查重：exact/causal=false；trigger/solution=partial（仅"NULL/断言"关键字
  交叠）；combination/boundary/test_migration=true → **new_draft（路径 B）**

## 适用库

libsoup3/3.6.5-r3（archives/l/libsoup3/3.6.5-r3/patches/0001-hsts-g_uri_get_port-null-guard.patch）
