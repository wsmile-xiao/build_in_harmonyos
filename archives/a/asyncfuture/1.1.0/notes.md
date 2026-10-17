# asyncfuture 1.1.0 适配笔记

## 编译环境
- 构建系统: cmake（header-only INTERFACE 库，无编译步骤）
- 编译日期: 2026-09-24
- 编译器: clang 15.0.4（OHOS aarch64）
- 状态: published

## 编译步骤

库本体为 header-only（asyncfuture.h），上游 CMakeLists 定义 INTERFACE target，无 configure/make 步骤。

1. 上游测试套件构建（ENABLE_TESTING=ON，Qt 6.11.1 OHOS 版）：
   `cmake <src> -DENABLE_TESTING=ON -DCMAKE_PREFIX_PATH=<qtbase>/lib/cmake;<qtdeclarative>/lib/cmake && cmake --build . --target asyncfutureunittests -j4`
2. 运行上游套件（QT_QPA_PLATFORM=offscreen）：Spec 53 + BugTests 20 + Example 13 + SampleCode 3 + Cookbook 3，全部通过（92 行 PASS，0 FAIL/SKIP；独立用户用例 82 个全过）。
3. 鸿蒙专项测试：clang++ -std=c++17 编译 ohos-test（deferred/observe/combine/cancel 断言），运行退出码 0，全部通过。
4. conan create（test_package 消费者 + 上游套件复跑）：EXIT 0，test_asyncfuture: ALL CHECKS PASSED + 上游 92 全过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连不可达 | 执行端网络仅镜像可达 | 下载经 ghfast.top 镜像取官方 tag 源码，SHA-256 与官方一致（conandata 保持官方 github.com URL） |
| 2 | 消费者测试挂起 | test_asyncfuture 未运行事件循环，QTimer 信号不下发 | test() 前用 QEventLoop + singleShot 泵事件循环，信号 future 正常完成 |
| 3 | conan create (make 生成器) 超预算 | test_package 30 目标单线程编译 | -c tools.cmake.cmaketoolchain:generator=Ninja 并行编译提速 |

## 源码修改

无（header-only 库，未修改任何上游源码；patches/ 为空）。

## 依赖版本

- qtbase/6.11.1（transitive_headers/libs）
- qtdeclarative/6.11.1（仅 test_package 上游套件需要 Qml/Quick/QuickTest）

## 验证结果

```bash
QT_QPA_PLATFORM=offscreen ./asyncfutureunittests   # exit 0, 92 PASS / 0 FAIL
QT_QPA_PLATFORM=offscreen ./ohos-test_asyncfuture   # exit 0, 4 断言全过
conan create . ... # exit 0, test_asyncfuture ALL CHECKS PASSED + 上游套件全过
```

## 交付物

- archives/a/asyncfuture/1.1.0/conanfile.py（header-only 配方 + asyncfutureConfig.cmake）
- archives/a/asyncfuture/1.1.0/conandata.yml（官方 tag v1.1.0 URL + SHA-256）
- archives/a/asyncfuture/1.1.0/test_package/（消费者测试 + MANIFEST）
- archives/a/asyncfuture/1.1.0/reports/test-report.md（上游测试双口径台账）
- archives/a/asyncfuture/1.1.0/reports/upstream-test-full.log / ohos-test.log

## 注意事项

- 消费者需 qtbase/6.11.1（Qt 头/库传递依赖）；上游测试需 qtdeclarative/6.11.1。
- 本库为纯库（无 CLI），不生成 commands.json。
---

**编译结束**: 2026-09-24 06:03
**最终状态**: built
