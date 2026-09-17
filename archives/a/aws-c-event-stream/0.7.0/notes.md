# aws-c-event-stream 0.7.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-17（接续修复）
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

使用 CMAKE_PREFIX_PATH 模式（非 CMakeDeps）：
```bash
conan create archives/a/aws-c-event-stream/0.7.0/conanfile.py \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 上游测试（R51）

上游 tests/CMakeLists.txt（commit 66cafb1d）注册 45 个用例：
21 add_test_case（unit）+ 24 add_net_test_case（net，ENABLE_NET_TESTS 默认开启）。

BUILD_TESTING=ON 后在 conan build() 内运行：
`cd build/tests && ctest --output-on-failure` → **45/45 passed**（含全部
net 用例，OHOS loopback socket 可用）。

**关键陷阱：OHOS 动态链接器按进程 cwd 解析相对 DT_NEEDED。**
测试驱动 NEEDED `../libaws-c-event-stream.so`（相对可执行文件目录），
但 OHOS loader 以 cwd 为基准——从 build/ 根跑 ctest 会报
"Error loading shared library ../libaws-c-event-stream.so"。
必须在 build/tests 目录内运行 ctest。

HMBS 证据链：build() 输出 HMBS_UPSTREAM_TEST_RESULT（passed 45/45）
并将 upstream_test_result.json 打包进 res/；test_package 读 res/ 重发
标记并输出 HMBS_TEST_PACKAGE_RESULT（4/4 冒烟）。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Threads::Threads target not found | aws-lc 的 crypto-targets.cmake 引用 Threads::Threads，但 find_package(Threads) 未在 find_package(aws-c-common) 前调用 | 添加 0001-CMakeLists-Threads.patch，在 project() 后立即 find_package(Threads REQUIRED) |
| 2 | CI G0e 白名单拦截（.branch_init 等） | CI worker checkout-pr 步骤的标记文件进入 git index；旧基点分支的 .gitignore 缺忽略规则 | main 已合入 .gitignore 规则（2b00f4bdc），worker checkout main 后自带，PR 无需改动 |
| 3 | reporter 报 "Conan test_package: 失败"（CI 实际 PASSED） | 新框架 reporter 解析 HMBS_TEST_PACKAGE_RESULT/HMBS_UPSTREAM_TEST_RESULT 标记，无标记=失败；旧配方 BUILD_TESTING=OFF 无上游测试证据 | build() 内跑 ctest 45/45 + 双标记输出（本笔记"上游测试"节） |
| 4 | 测试驱动运行报 symbol not found | OHOS loader 按 cwd 解析相对 NEEDED（../libaws-c-event-stream.so），从 build 根运行时解析错误 | ctest 必须在 build/tests 目录内运行（cd tests && ctest） |

## 依赖版本
- aws-c-common/0.14.3
- aws-c-io/0.27.5
- aws-checksums/0.2.10
- aws-c-cal/0.9.15
- aws-lc/5.4.0

## 注意事项
- 使用 CMAKE_PREFIX_PATH 而非 CMakeDeps，以保留 AWS::target 名称和 CMAKE_MODULE_PATH
- aws-c-cal 和 aws-lc 需显式声明为依赖，因为 AWS CRT recipes 不声明 cpp_info.requires
- 动态链接 (BUILD_SHARED_LIBS=ON)
---

**编译结束**: 2026-09-17 12:55
**最终状态**: built（上游 45/45 + 消费侧冒烟 4/4 通过）
