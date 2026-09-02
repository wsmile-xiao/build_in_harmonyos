# Test Report — libsoup3 3.6.5-r2

- 日期: 2026-09-02
- 平台: HarmonyOS PC (aarch64, musl, clang 15.0.4)
- 构建系统: meson (conan 2.29.1, profile ohos-aarch64)

## 1. conan create（配方验证）

```
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig
python3 -c "from conans.conan import run; import sys; sys.argv=['conan','create','.','--user=ohpcd','--channel=stable','-pr:h=$HOME/.conan2/profiles/ohos-aarch64','-pr:b=$HOME/.conan2/profiles/ohos-aarch64','--build=missing']; run()"
```

结果: **成功**

- G2 干净构建: PASS（conan-verify 全部门禁 G0/G1/G2/G3/G4 + L2/L4/L5 通过）
- test_package L1: PASS（真实 API 冒烟）
  - `test libsoup3 3.6.5-r2: OK (host=example.com, session+message ok)`
  - W3 本地 CI 模拟（build_and_test.sh）: 1/1 通过，Pass rate 100.0%
  - L1e 破坏性反向验证（R34）: 确认 test 真实依赖 libsoup3
- `.ci-result.json`: exit_code=0

## 2. 上游测试套件（meson test，本次实测补齐 -r1 未记录部分）

上游 libsoup 3.6.5 自带 38 个测试用例（tests/meson.build: 32 基础 +
brotli-decompressor/auth/connection/range/proxy 等 6 个条件用例）。
本次在 conan build 目录以 `-Dtests=true` + conan 生成的 native 文件重新
配置构建（builddir-tests），逐个运行 33 个可编译测试二进制：

- **33 个可编译可运行 / 30 PASS / 3 FAIL，通过率 90.9%**

PASS（30）: cache, chunk-io, coding, context, continue, cookies, date,
forms, header-parsing, http2, http2-body-stream, logger, misc, multipart,
multithread, no-ssl, ntlm, redirect, request-body, samesite, server,
server-auth, session, sniffing, ssl, streaming, timeout, tld, uri-parsing,
websocket

FAIL（3，均为 OHOS 平台限制，非代码缺陷）:

| 测试 | 现象 | 根因（实测验证） |
|------|------|------|
| hsts-test | `/hsts/case-insensitive-header` GLib-FATAL-CRITICAL: g_uri_get_port: assertion 'uri != NULL' | OHOS 无 glib-networking，GIO 回退 GDummyTlsBackend（运行日志实证 `Found default implementation dummy (GDummyTlsBackend) for 'gio-tls-backend'`），tls_available=FALSE → https_uri 未初始化 → g_uri_get_port(NULL) 崩溃。与配方 tls_check=false 同因 |
| hsts-db-test | `/hsts-db/basic` 同款断言崩溃 | 同上 TLS 后端缺失根因 |
| unix-socket-test | `Unable to create server: Could not import existing socket: Protocol not available` | OHOS 安全策略禁止 AF_UNIX bind（EPERM）——本机 Python `socket(AF_UNIX).bind()` 独立复现同错，而 `socket(AF_INET).bind(("127.0.0.1",0))` 成功；平台限制 |

豁免（5 个未编译，有 meson 条件分支佐证）:

- `brotli-decompressor`: brotli 特性禁用（上游 `if brotlidec_dep.found()` 不成立）
- `auth`/`connection`/`range`/`proxy`: 需外部 Apache httpd（上游 `if have_apache` 分支，OHOS 无）

## 3. 新增鸿蒙特有测试

test_package/test.c 真实 API 冒烟（soup_message_new + soup_session_new +
GUri host 解析，3 项断言）: **1/1 通过（100%）**

## 4. 结论

- 编译状态: 通过（built；conan-verify PASS + W3 本地 CI 通过，upload 待 PR 合并后 release 流水线完成）
- 上游测试通过率: 30/33 可编译用例 = **90.9%**（3 FAIL 均 OHOS 平台限制:
  TLS 后端缺失 ×2、AF_UNIX bind EPERM ×1；5 个豁免用例有 meson 条件分支论证）
- 新增测试通过率: 1/1 = 100%
