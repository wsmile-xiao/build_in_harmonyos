# utf8.h 0.0-git20260825.7e403ccc3f 适配笔记（HarmonyOS PC · header-only + CTest）

## 定位
- 单头文件 UTF-8 字符串库（Unlicense），产出仅 `include/utf8.h`，无库产物。

## 源
- 上游无 release tag（唯一 tag 为 pre-ai），按 commit 固定：
  https://github.com/sheredom/utf8.h/archive/7e403ccc3f3cb848d061cac352ee26e54f27c934.tar.gz
- sha256: 5569cad674045d5b1d0e98daf9a9bbd53b2371af296dd18e41a95c32a632fec9
- commit 7e403ccc（2026-08-25，GitHub API 核实），版本串 0.0-git20260825.7e403ccc3f。

## W0/W0b
- preflight_check.sh：无依赖声明，通过（header-only，零第三方依赖）。
- 本仓库无同软件历史归档；recipe-search 命中的是本次自身骨架。
- lang-preflight：task=cpp，detected=cpp（utf8.h 单头，C/C++ 双支持），通过。

## 上游测试（R51 四维账本）
- N_static（原子用例）：487 —— utest 框架运行时报告 "487 test cases ran"。
- N_registered（CTest 目标）：8 —— utf8_test / utf8_no_malloc_test /
  utf8_address_test / utf8_no_malloc_address_test / utf8_undefined_test /
  utf8_no_malloc_undefined_test / utf8_thread_test / utf8_no_malloc_thread_test
  （后六个为 ASan/UBSan/TSan 变体，由 CMakeLists 的 sanitizer 探针按平台可用性注册）。
- N_executed：8/8 —— 真机 ctest：`100% tests passed, 0 tests failed out of 8`。
- N_consumer：1（test_package/test.c，10 个断言）。
- 口径说明：487 是 utest 原子用例数（一个 CTest 目标内含全部用例），不能与 8 个
  CTest 目标数混算；CTest 目标数为构建注册层，两者分别列明。

## 构建要点
1. header-only：`package_type="header-library"` + `package_id()` 清空 + package() 只装
   include/utf8.h 与 licenses/{LICENSE,README.md}。
2. 上游测试集成：`options = {"run_upstream_tests": [True, False]}`，build() 内
   `cmake.configure(build_script_folder=<src>/test)` → `cmake.build()` → `cmake.test()`
   （cross_building 时只编译不运行），CI 与真机同路径执行上游套件。
3. `generate()` 注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（上游 test/CMakeLists 声明 3.15，
   CMake 4.x 下的通用兼容开关）并 `user_presets_path = False`。

## 消费者测试（test_package/test.c，R34）
直接以 clang 编译被测头文件并断言真实行为，10 个断言：
- `utf8len("héllo")==5`（码点数；6 字节）与 `utf8len(U+1F600)==1`（4 字节）
  —— 真机实测确认 utf8len 按**码点**计数（源码 `length++` 在码点循环内），
  初版按字节数写断言导致 2 例失败，修正后通过。
- `utf8codepoint` 逐码点迭代 5 次、解码 U+1F600、返回指针正确推进。
- `utf8cat`/`utf8ncmp` 拼接与比较、`utf8valid` 接受合法/拒绝截断、`utf8dup` 复制。

## 状态
built —— conan-verify G1/G2/G3/G4 全过、消费者 10/10 通过（见 reports/）。
---

**编译结束**: 2026-09-09 13:06
**最终状态**: built
