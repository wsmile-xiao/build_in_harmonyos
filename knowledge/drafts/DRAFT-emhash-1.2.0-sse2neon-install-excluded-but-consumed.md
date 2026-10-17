# DRAFT-emhash-1.2.0-sse2neon-install-excluded-but-consumed

> Draft: DRAFT-emhash-1.2.0-sse2neon-install-excluded-but-consumed
> 来源: emhash 1.2.0 适配（R01, executor pc2-31, 2026-09-22）
> 状态: 草稿（待审核 promote）

## 错误特征

```text
In file included from test_ohos.cpp:
include/emilib/emihmap4.hpp:43:10: fatal error: 'sse2neon.h' file not found
#include <sse2neon.h>
```

## 触发条件

- 构建系统: cmake（header-only）或任意使用 emilib 系头文件的消费者
- 阶段: 消费者编译（aarch64/OHOS）
- 前提: 库的业务头（如 emilib/emihmap4.hpp、emihset3.hpp）在 aarch64 上无条件下
  `#include <sse2neon.h>`（SSE2→NEON 转译），但官方 CMakeLists install 用
  `PATTERN "sse2neon.h" EXCLUDE` 将该转译头排除出安装；套用官方 CMake install 的
  产物缺此头，消费者在 aarch64 编译即失败

## 根因分析

emhash v1.2.0 官方 CMakeLists.txt 明确 `install(DIRECTORY include/ DESTINATION
${CMAKE_INSTALL_INCLUDEDIR} PATTERN "sse2neon.h" EXCLUDE)`——上游认为 sse2neon.h 是
第三方 shim 不应污染用户 include 根目录。但 emilib/*.hpp 在编译期无条件 include 它
（x86 与 aarch64 同路径），官方 CMake install 产物在 aarch64 上自相矛盾：业务头需要
该头、installed 包却不含。官方自带 conanfile.py 的 package() 反而显式拷贝
sse2neon.h 到 include/——印证该头必须随包分发。

## 推荐方案

**方法**: sse2neon-install-excluded-but-consumed

**说明**: header-only conan 配方 package() 显式拷贝 sse2neon.h（或其他被 CMake
install 排除的转译/兼容头）到 include/，与官方 conanfile.py 的 package() 行为一致；
消费者测试必须实际编译运行以验证 aarch64 路径。仅当业务头条件编译（仅 x86 才
include 该头）时无需补拷。

**验证/命令**:
```bash
# 确认业务头无条件下 include 被排除头
grep -rn "sse2neon" include/emilib/*.hpp
# 配方 package() 补拷后，消费者 aarch64 编译运行
clang++ -std=c++17 -I<install>/include test_ohos.cpp -o test_ohos && ./test_ohos
```

## 关键词

sse2neon, emilib, SSE2, NEON, aarch64, install EXCLUDE, header-only, conan, 转译头