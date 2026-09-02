# concurrencpp 0.1.7 适配笔记

## 编译环境
- 构建系统: cmake (CMakeLists.txt, C++20)
- 编译日期: 2026-09-02
- 编译器: clang/clang++ (15.0.4, aarch64-linux-ohos / OHOS armv8)
- 状态: published (conan-verify 全门禁通过, 制品已本地验证)

## 编译步骤

1. `python3 scripts/ohc-run.py init-build concurrencpp 0.1.7 --url=https://github.com/David-Haim/concurrencpp/archive/refs/tags/v.0.1.7.tar.gz --tar tar.gz` — 下载并解压官方源码 (sha256 049f3e83ad1828e0b8b518652de1a3160d5849fdff03d521d0a5af0167338e89)
2. `python3 scripts/ohc-run.py lang-preflight concurrencpp 0.1.7 --src $BUILD_SRC_DIR` — 语言预检通过 (detected=cpp, cmake)
3. `cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=20 -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX ..` — 配置; `cmake --build . -j4` 编译出 libconcurrencpp.a
4. `cmake -S test -B build-test ..` + `cmake --build` — 26 个 CTest 测试目标全部编译; `ctest` 25/26 + timer_tests 后台完整运行 (上游固定 5 分钟 sleep), 全部通过
5. `cmake --install . --prefix $TEST_PREFIX` — staging 安装验证 (libconcurrencpp.a + 头文件 + CMake config)
6. `python3 scripts/ohc-run.py conan-init concurrencpp 0.1.7` — 生成配方; 重写为 CMake 模板 (init-build 误判 autotools)
7. `python3 scripts/ohc-run.py conan-verify concurrencpp 0.1.7` — G0-G4 + L2/L4/L5 全门禁 PASS
8. `python3 scripts/ohc-run.py finish concurrencpp 0.1.7 published` — W2 结构 + R36 依赖 + W3 本地 CI 模拟通过, .ci-result.json 生成
9. HarmonyOS 专项测试: `clang++ -std=c++20 -I<conan include> harmonyos_concurrency_test.cpp libconcurrencpp.a -pthread` 编译并运行 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 误判构建系统为 autotools | URL 推断不适用于 CMake 项目 | conan-init 后手动重写 conanfile.py 为 CMake 模板 |
| 2 | conan-verify G2 失败: test_package 找不到 concurrencpp/concurrencpp.h | 上游把头文件安装到 include/concurrencpp-0.1.7/ 子目录, INSTALL_INTERFACE 未导出 include 路径 | conanfile.py package_info 显式声明 `cpp_info.includedirs = ["include/concurrencpp-0.1.7"]` |
| 3 | test_package 编译失败: 'this' argument to 'get' has type 'const result<int>' | `const auto result` 导致对 const result 调用非 const get() | 去掉 const 声明 |
| 4 | W3 L0d stub_test_method 门禁失败 | test_package test() 用 cmake.test() 无 self.run | test() 改为直接 `self.run(...test_concurrencpp...)` 执行二进制 |
| 5 | W3 JC 垃圾文件拦截 (full 模式扫整仓) | 分支未 commit 时 JC 回退 full 模式, 命中其他库历史垃圾 (flatcv/goaccess 等) | 清理本库构建残留后提交干净改动, JC 走 incremental 模式只查本库 diff |

## 源码修改

无补丁 (patches/ 为空)。concurrencpp 源码零修改, 仅配方层适配。

## 依赖版本

- 无第三方 conan 依赖 (requirements 为空); 仅系统 Threads + librt
- 工具链: clang 15.0.4 / CMake 4.1.2 / conan 2.29.1 (OHOS 适配版) / Python 3.12.9

## 验证结果

```bash
# 上游测试: 26 CTest 目标, 150 独立用例 (add_step), 全量通过率 150/150 = 100%
# HarmonyOS 专项: [OHOS] concurrencpp parallel sum=36 unique_threads=8 coroutine_sum=42 -> PASS
# conan create (ohos-aarch64 profile): PASS, 全部 8 门禁通过
# W3 本地 CI 模拟: setup.sh + build_and_test.sh PASS
# 证据日志: ~/ohpcd-evidence/concurrencpp-0.1.7/ (source_audit/adaptation_validation 等, 含 SHA-256)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake/C++20 配方 (静态库, Threads 依赖) |
| conandata.yml | 官方源码 URL + sha256 |
| test_package/ | 消费者测试 (真实调用 runtime/thread_executor/result) |
| harmonyos-test/harmonyos_concurrency_test.cpp | HarmonyOS 专项测试 (并行求和 + 协程 + 线程 ID) |
| reports/test-ledger.md + test-report.md | 上游测试台账与报告 |

## 注意事项

- 上游 CMakeLists 把头文件装在 include/concurrencpp-0.1.7/ 子目录, 消费者 include 需通过配方 includedirs 声明
- timer_tests 的 test_many_timers 固定 sleep 5 分钟 (上游设计), 全量测试需延长观察窗口
- TSAN 测试集默认关闭 (ENABLE_THREAD_SANITIZER=OFF, 上游默认), 不计入独立用例
---

**编译结束**: 2026-09-02 03:57
**最终状态**: published
