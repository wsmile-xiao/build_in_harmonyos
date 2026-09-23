# jsonifier 0.9.97 适配笔记

## 编译环境
- 构建系统: cmake（header-only INTERFACE 库，配方以 Conan 打包头文件）
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4（OHOS SDK 26.0.0.18，aarch64）/ 对照 clang-22.1.8（registry 包）
- 状态: built

## 源码信息
- 上游官方源（GitHub tag v0.9.97，commit abbaacab60b3e39563c87829486015234e19a37c）
- SHA-256: 859a90731c5623e4cb4200bfa7b5dcb32d75f019147b06f73b7ecc0eec31b231
- 许可证: MIT

## 编译步骤
1. `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=jsonifier/*`
   （配方 source() 拉取官方 tag tarball，build() 应用 9 个适配补丁，package() 打包头）
2. test_package：`clang++ -std=c++2b test_jsonifier.cpp` → 运行 → ALL TESTS PASSED

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | aarch64 下编译含 x86 指令集位 38（AVX/LZCNT/BMI）走 immintrin.h 报 "only meant to be used on x86 and x64" | 上游 tar 内 JsonifierCPUInstructions.hpp 提交值按 x86 主机生成 | 补丁改为 8（NEON） |
| 2 | Config.hpp PREFETCH 对 clang 无条件 `#include <xmmintrin.h>` | 上游仅处理 Apple arm64 | 补丁增加 `__aarch64__`/`_M_ARM64` 分支用 `__builtin_prefetch` |
| 3 | `<memory_resource>` 头缺失 | OHOS libcxx-ohos（clang-15 SDK）未提供该头 | Allocator.hpp 加 `__has_include` 守卫 |
| 4 | `<source_location>` 头缺失 | 同上（仅 experimental/memory_resource 存在） | 新增 Compat/SourceLocation.hpp shim（API 等价），Error/Hash/Reflection 改引 shim |
| 5 | char_traits 部分特化歧义 | aarch64 char 默认 unsigned：uint8_type 概念对纯 char 成立，与 not_uint8_t 特化重叠 | uint8_type 特化加 `requires (!std::same_as<unwrap_t<T>, char>)` |
| 6 | `map_simd_t` 别名报 missing typename | clang-15 对 P0634 支持不足 | 补显式 typename |
| 7 | test_package 触发 clang-15 前端 IRGen 段错误（Error.hpp constructError） | OHOS SDK clang-15 前端 bug；clang-22 编译运行正常 | 消费者验证路径用 parse/serialize（二者在 clang-15 下编译运行通过） |

## 上游已知缺陷（非本次适配引入，双工具链复现）
- validateJson 数字路径：0.9.97 的 `validate_impl<Number>::impl` 中 `consumeSign()` 对无符号数字（如 `1`、`[1]`）返回 false → 校验失败；与 OHOS/NEON 无关（parseJson 数字正常）。
- std::map 序列化：`serializeJson(map)` 输出缺尾部 `}`（`[{"a":1,...,"c":3]`），clang-15 与 clang-22 一致复现。
- 上游测试库本体无独立 TEST_CASE：Tests/ 为基准程序（Json-Performance），依赖 FetchContent 拉取 glaze/simdjson/BenchmarkSuite，CI 离线环境不可构建（详见测试台账 #7）。

## 依赖版本
- 无第三方运行时依赖（header-only）
- 构建期：conan（OHOS 适配版）、OHOS SDK clang-15 / 对照 clang/22.1.8

## 验证结果
```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=jsonifier/*
# → build 通过、test_package 编译运行：
#   serializeJson ok: [1,2,3]
#   parseJson(map) ok: size=3
#   vector roundtrip ok
#   parseJson(vector) ok
#   ALL TESTS PASSED
```

## HarmonyOS 专项测试（test_package/test_ohos_specific.cpp）
真实编译运行（`clang++ -std=c++2b -O1`，OHOS SDK clang-15 aarch64），13/13 断言通过、退出码 0：
- NEON SIMD 路径较大多层文档（对象数组）解析与序列化
- UTF-8 中文解析及序列化-解析往返
- int64 最大值 / uint64 最大值 / double 最小正正规数(DBL_MIN)、最小次正规数(denorm_min)、最大次正规数 / double 最大值解析
- 双层嵌套数组解析与往返
- 空输入拒绝（false-positive 防护）
日志：`$HOME/tmp/jsonifier-uptests/ohos-special-r04.log`（13 行 PASS，Total failures: 0，SHA-256=2c5581eed80e4e3ba762476431d47d2b87cf7d593158b0476d98d9d30e237a27）

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | header-only 配方（source/build 应用补丁、package 打包头、cpp_info） |
| conandata.yml | 官方 URL + SHA-256 + 9 个补丁声明 |
| patches/*.patch | OHOS aarch64 适配补丁（指令集/prefetch/头缺失/char_traits/typename） |
| test_package/ | 消费者验证（编译运行，R34 非空壳） |
| manifest.yaml | 版本级元数据 + 知识沉淀 |

## 注意事项
- 上游要求 C++23（CMakeLists CMAKE_CXX_STANDARD 23）；OHOS clang-15 仅接受 `-std=c++2b`，配方 cxxflags 用 c++2b。
- 知识库四范围查重与路径判断见知识候选台账（任务 #10）。
---

**编译结束**: 2026-09-06 01:49
**最终状态**: built
