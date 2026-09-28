# E-DRAFT: STB 风格单头文件库 test_package 必须定义实现宏才能链接

- **触发实例**：lib_fts 1.2.8 适配（2026-09-27，任务 pc2-36，分支 feat/lib_fts-1.2.8）
- **错误签名**：`ld.lld: error: undefined symbol: fts::fuzzy_match_simple(char const*, char const*)`
- **类别**：headers, conan, packaging, testing
- **严重度**：2（链接阶段确定性失败，修复模式固定）

## 症状

```text
clang++ ... -isystem .../p/include -c test.cpp  # 编译通过（声明可见）
ld.lld: error: undefined symbol: fts::fuzzy_match_simple(char const*, char const*)
>>> referenced by test.cpp
ld.lld: error: undefined symbol: fts::fuzzy_match(char const*, char const*, int&)
clang-15: error: linker command failed with exit code 1
ERROR: lib_fts/1.2.8@ohpcd/stable (test package): Error in build() method
```

## 根因

STB 风格单头文件库（`fts_fuzzy_match.h`、`stb_image.h` 等）把完整实现包在
`#ifdef XXX_IMPLEMENTATION` 块内。仅 `#include` 时只有 namespace/函数声明可见；
不定义实现宏则链接期 `undefined symbol`。上游官方测试源 `tests/fuzzy_match/fts_fuzzy_match_test.cpp`
第 10 行正是 `#define FTS_FUZZY_MATCH_IMPLEMENTATION` 后再 include，即同一用法。

## 修复

```cpp
#define FTS_FUZZY_MATCH_IMPLEMENTATION   // 必须在 include 之前
#include <fts_fuzzy_match.h>
```

宏内是 static 函数，单翻译单元实例化即可，不会重复定义；consumer 与 test_package
各自定义互不影响。非平台宏，无需 patch（R8 无涉）。

## 验证

```bash
conan create archives/l/lib_fts/1.2.8 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# test_package 两个可执行编译链接运行通过，16 断言全 PASS
```

## 适用边界 / 反例

- ✅ 适用：所有 STB 风格单头文件库的 test_package / 消费者用例。
- ❌ 反例：常规头文件实现分离的库（无实现宏概念），定义宏反而无意义；编译报
  重复定义的库不应加宏 —— 先核对头文件是否用 `#ifdef XXX_IMPLEMENTATION` 守卫。