# spawn 1.6.6 配方与验证说明

## 包名与上游

- 比赛包名/目录：`spawn/1.6.6`。
- 上游项目：`spawn-fcgi 1.6.6`。
- 官方源码：`https://www.lighttpd.net/download/spawn-fcgi-1.6.6.tar.gz`。
- SHA256：`4ffe2e9763cf71ca52c3d642a7bfe20d6be292ba0f2ec07a5900c3110d0e5a85`。

## 上游测试审计

`spawn-fcgi-1.6.6.tar.gz` 解包后没有 `tests/` 或 `test/` 目录，也没有 CTest、pytest、shell 测试或测试程序。顶层 `meson.build` 只定义编译检查、`spawn-fcgi` executable 和 man page 安装，没有 `test()`、`subdir('tests')` 或 check/test target。因此上游测试统计真实为：用例 0、断言 0、执行 0。配方不会调用或虚构上游测试通过数。

## 构建

- 构建系统：Meson。
- 无外部依赖，只需要 libc/socket API。
- `MesonToolchain` 生成 native file；若 `ar` 缺失，从 profile 的 clang 路径推导同目录 `llvm-ar`。
- 安装产物：`bin/spawn-fcgi` 与 `share/man/man1/spawn-fcgi.1`。

## 消费者测试

`test_package/` 编译一个最小 FastCGI 后端 `fcgi_backend.c`，并真实执行已安装的 `bin/spawn-fcgi`：

1. `spawn-fcgi -v` 必须输出 `spawn-fcgi v1.6.6`。
2. `spawn-fcgi -h` 必须输出 usage/help。
3. 在 `127.0.0.1` 私有临时端口上以 `spawn-fcgi -n` 启动真实监听 socket。
4. Python 客户端建立 TCP 连接并发送 `FCGI_BEGIN_REQUEST`、`FCGI_PARAMS`、`FCGI_STDIN`。
5. 后端必须解析 begin-request 的 responder role、params 与 STDIN 终止记录，并返回 `FCGI_STDOUT`/`FCGI_END_REQUEST`。
6. 客户端必须读到 `spawn-fcgi-ok`，后端进程必须以 0 退出。

真实断言总数：7。消费者侧标记仅在全部断言通过后记为通过；失败时保留实际通过数并让 `conan create` 失败。

## 机器证据标记

- 上游：`HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",...}`。
- 测试包：`HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"discovered":7,...}`，以 OpenDesk 实际日志为准。
- 同时输出兼容标记：`UPSTREAM_TEST_RESULT total=0 ...` 与 `TEST_PACKAGE_RESULT total=7 ...`。

## 真机验证状态

状态：PASS。OpenDesk job：`20260924-152616-62681f-spawn-create1`。

验证命令：

```text
conan create pkg -pr:b=/storage/Users/currentUser/test/build_in_harmonyos/ci/conan/profiles/ohos-aarch64 -pr:h=/storage/Users/currentUser/test/build_in_harmonyos/ci/conan/profiles/ohos-aarch64 --build=missing
CREATE_EXIT=0
```

实际消费者测试输出：

```text
CHECK-OK: version
CHECK-OK: help
CHECK-OK: tcp_listen
CHECK-OK: fastcgi_end_request
CHECK-OK: fastcgi_response
CHECK-OK: fastcgi_stdout
CHECK-OK: backend_exit_zero
TEST_PACKAGE_RESULT total=7 passed=7 failed=0
```

上游无测试，因此 `HMBS_UPSTREAM_TEST_RESULT` 的真实状态为 `no_tests`，发现/执行/通过均为 0；没有把消费者测试冒充为上游测试。完整机器标记见 `RESULT.md`。
