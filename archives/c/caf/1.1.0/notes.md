# caf 1.1.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-06
- 编译器: clang/clang++ (aarch64-unknown-linux-ohos, clang 15.0.4)
- 状态: built

## 编译步骤

```bash
# 1. 下载官方 1.1.0 归档（GitHub 直连不可达，经 gh-proxy.com 镜像获取官方字节）
#    sha256 9febd85d3a4f50dac760592043028a36bea62bba50c3ee2fc1eace954dd8ae27
#    （与 gitcode gh_mirrors/ac/actor-framework tag 1.1.0 的 git archive 对比一致，
#      CMakeLists.txt 与官方 tag 完全一致，HEAD 97e03500422f0ac48e35fee510d570e16b43a65e）

# 2. 生成 OHOS toolchain + 解析依赖 openssl/3.5.6.1（ohpcd 制品仓已有预编译包）
conan install . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -of=... --build=missing

# 3. CMake 配置 + 构建（静态库 + 全部测试可执行文件）
cmake -S actor-framework-1.1.0 -B bld -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE=.../conan_toolchain.cmake -DCMAKE_BUILD_TYPE=Release \
  -DCAF_ENABLE_TESTING=ON -DCAF_ENABLE_EXAMPLES=OFF -DBUILD_SHARED_LIBS=OFF \
  -DCAF_ENABLE_OPENSSL_MODULE=ON -DCAF_ENABLE_NET_MODULE=ON
ninja -j20 libcaf_core caf-core-test caf-io-test caf-net-test caf-openssl-test caf-test-test

# 4. 运行上游测试（CTest 注册 230 项全部通过）
./libcaf_core/caf-core-test -n      # Suites: 188/188  Checks: 10036/10036  passed
./libcaf_io/caf-io-test -n          # Suites: 8/8      Checks: 265/265      passed
./libcaf_net/caf-net-test -n        # Suites: 29/29    Checks: 852/852      passed
./libcaf_test/caf-test-test -n      # Suites: 5/5      Checks: 421/421      passed
./libcaf_openssl/caf-openssl-test -n # Suites: 0/0（openssl 模块无独立用户用例）

# 5. conan create（W3 自包含验证 + test_package 消费者运行）
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
#    test_caf 输出: CAF 64 ping result: pong:hello  (exit 0)
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub/codeload 直连超时，官方归档不可下载 | 执行机网络无法直连 github.com | conandata.yml 官方源后追加 gh-proxy.com/mirror.ghproxy/kkgithub 镜像 fallback；本地经 gh-proxy.com 取官方字节并核验 SHA-256 |
| 2 | `actor_system created without calling caf::init_global_meta_objects<>() before` (FATAL, exit 134) | CAF 1.x 要求创建 actor_system 前初始化全局 meta objects 表 | 消费者/test_package 入口调用 `caf::core::init_global_meta_objects()`（含头文件 caf/init_global_meta_objects.hpp） |
| 3 | `blocking_response_handle::receive` 编译报 static_assert "OnValue must return void" | CAF 1.1 的 receive OnValue/OnError 回调签名必须返回 void，不能返回结果值 | 改为 lambda 捕获引用写入结果变量，错误经 caf::error 捕获 |
| 4 | `sys.spawn(typed_impl, ...)` 报 infer_handle_from_class 无 type（SFINAE 失败） | 仅包含 caf/typed_actor.hpp 时 typed_event_based_actor 为前向声明，is_base_of 无法求值 | 补包含 `caf/typed_event_based_actor.hpp` |
| 5 | 测试进程在 `sys.await_all_actors_done()` 挂起 | 事件型 actor（计数器）永不退出，running count 不为 0 | 显式对每个 actor `send_exit(user_shutdown)` 后再 await |
| 6 | conanfile build() 用 `cmake.build(build_tool_args=["--target", ...])` 报错 | CMake.build 的 target 应通过 `target=` 关键字传入，不能塞进 build_tool_args | 简化为一并 `cmake.build()`（CAF_ENABLE_TESTING=ON 时默认构建全部测试目标），生成器固定 Ninja |

## 源码修改

无补丁（patches/ 为空）。CAF 1.1.0 在 OHOS clang15 + libc++ 下原生构建通过，未修改任何上游源码。

## 依赖版本

- openssl/3.5.6.1（ohpcd 制品仓预编译，供 caf_net/caf_openssl 模块链接）

## 验证结果

- 上游测试（CTest 注册 230 项）全部通过：230/230 suites、11574/11574 checks
- 源码声明口径：237 个 .test.cpp 文件、TEST() 798 + SCENARIO() 242 = 1040 个用户测试声明
- OHOS 专项测试（tests/ohos_smoke.cpp）：8 actor × 200 轮消息往返，计数器 1600/1600 一致，PASSED (exit 0)
- test_package 消费者验证：CAF 64 ping result: pong:hello (exit 0)

## 注意事项

- CAF 1.x 的 typed actor spawn、receive 回调签名与 0.19 系列差异较大，消费者代码需按 1.1 API 编写
- 本机为 aarch64 + OHOS 工具链，conan 以同 profile 作为 build/host，can_run 为真，测试可实际执行
- 归档不含补丁，CI 可完全复现（官方源 + sha256 + 镜像 fallback）
---

**编译结束**: 2026-09-06 05:19
**最终状态**: built
