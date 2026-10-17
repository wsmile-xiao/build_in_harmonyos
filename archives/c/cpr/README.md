# cpr

cpr (C++ Requests) 是一个基于 libcurl 的 C++17 HTTP 客户端库，是 Python
Requests 的精神移植，提供简洁的 `cpr::Get` / `cpr::Post` / `cpr::Session` API。

## HarmonyOS PC adaptation

- 基于官方 1.14.2 源码构建，C++17，CMake >= 3.18。
- 依赖 `curl/8.15.0`（传递 `openssl/3.5.6.1`、`zlib/1.3.1.1`，均作为直接依赖声明
  以保证 generate() 能取到真实 package_folder）。
- 使用系统 curl/OpenSSL 后端（`CPR_USE_SYSTEM_CURL=ON`、`CPR_FORCE_OPENSSL_BACKEND=ON`），
  不构建 cpr 内置的 FetchContent curl。
- 上游测试（34 个 gtest 可执行文件、581 个用例）在真机完整执行：googletest v1.14.0
  与 mongoose 7.7 通过 conandata 本地暂存并用 `FETCHCONTENT_SOURCE_DIR_*` 接入，
  configure 阶段不访问 GitHub；`ctest --output-on-failure` 全量运行并输出
  `HMBS_UPSTREAM_TEST_RESULT` 标记。
- OHOS 强制代码签名：构建出的测试可执行文件与共享库在运行/打包前用
  llvm-objcopy + binary-sign-tool 签名。

## Consumer verification

Conan 消费者测试（test_package）启动一个本地 HTTP 服务，通过 `cpr::Get` 发起真实
请求，校验 HTTP 200 状态码与响应体内容，实质覆盖 cpr API 与 libcurl 后端
（R34：非空壳测试）。

## Reference

- https://github.com/libcpr/cpr
- https://docs.libcpr.dev/
