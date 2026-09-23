# hfsm2 beta73 适配笔记

## 库概况
- 上游：https://github.com/andrew-gresyk/HFSM2（header-only C++14 分层状态机库）
- 版本：上游 tag `Beta73`；归档/Conan 版本 `beta73`（Conan 2 强制 name/version 全小写 slug，L0m-5 门禁一致）
- 源码：官方 GitHub archive `Beta73.tar.gz`，SHA-256 `2afa6c2341f9cd48d739ed5556db6c99e67c5299a9f013b88d4be1c192a993eb`（与官方 URL 计算的哈希一致）
- tag commit: c91d4e573760b6650cd7239c9e234478ca8c2d50

## 适配要点
1. **header-only 打包**：无编译产物，package 仅分发 `include/hfsm2/*`（42 个文件：machine.hpp、machine_dev.hpp、detail/）。无第三方依赖、无系统同名库、无 configure/make 入口。
2. **aarch64 char 符号性**：OHOS aarch64 上 `char` 默认为 unsigned，上游 `test/test_debug.cpp` 存在对 `-2` 等负值的 C++11 窄化（`-Wc++11-narrowing`）。编译上游测试时加 `-fsigned-char` 对齐上游 x86 有符号 char 语义；**不改上游源码**，仅构建标志。
3. **Catch2 单头文件**：上游 test/main.cpp `#define CATCH_CONFIG_MAIN`（唯一实现 TU）；`test/*.cpp` + `test/shared/*.cpp` 编译进单一 `hfsm2_test` 可执行（等效上游 CMake project(hfsm2_test)）。
4. **Conan 版本 slug**：上游 tag 大写 `Beta73` → 配方/归档版本 `beta73`（Conan 2 与 CI L0m-5 均强制全小写 slug）。conandata.yml 的 URL 仍指向官方 `Beta73` 标签。

## 测试台账（双口径）
- 上游：17 个独立 TEST_CASE（14 FSM.* + 3 Shared.*），全部编译进 `hfsm2_test` 并注册（`--list-tests` = 17），实际运行 **17/17 PASS（35691 assertions）**，exit 0。
- 全量通过率：17/17 = 100%（源码声明 17 = 当前配置可执行 17 = 实际通过 17，无双口径差异）。
- test_package 消费者测试：`test_hfsm2`（API 冒烟，cycles=3 断言）+ `test_hfsm2_ohos`（鸿蒙专项：entry guard 首次拒绝/二次放行 + Orthogonal + changeTo 链，entryGuardHits=2、transitions=2 断言），均 PASS。
- 逐入口台账详见 `test_package/MANIFEST.yml` 与 `reports/`。

## 版本一致性说明
- 归档目录 `archives/h/hfsm2/beta73`（小写 slug，满足 L0m-5）
- 分支 `feat/hfsm2-Beta73`（任务头 source_branch，保留上游 tag 大小写）
---

**编译结束**: 2026-09-05 06:19
**最终状态**: published
