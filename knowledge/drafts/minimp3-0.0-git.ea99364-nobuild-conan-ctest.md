# 无构建系统 header/源混合单文件库的 Conan 化：amalgamated 单 TU + 上游 shell 测试 CTest 化

> Draft: `DRAFT-MINIMP3-NOBUILD-CONAN-CTEST`
> Stem: `minimp3-0.0-git.ea99364-nobuild-conan-ctest` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-MINIMP3-NOBUILD-CONAN-CTEST
- **状态**: pending-editor-review
- **类别**: conan|testing|build-system
- **触发工具**: conan|clang|cmake|ctest
- **阶段**: packaging|testing
- **严重度**: 2
- **来源**: minimp3 0.0-git.ea99364 适配 PR !14508（j669539，2026-10-03）

## 问题特征（两个陷阱）

一类单文件 C/C++ 库（minimp3、stb 系列、MurmurHash3 等）有两个共同点：

1. **上游不提供任何构建系统**——仓库里没有 CMakeLists.txt / Makefile /
   configure，只有 .travis.yml 或 scripts/build.sh 之类的演示脚本；
2. **header/源混合形态**——实现代码在 `#ifdef XXX_IMPLEMENTATION`
   宏守卫内，与声明同处一个头文件（minimp3.h 76KB + minimp3_ex.h 50KB）。

直接按"header-only 库"的直觉用 INTERFACE 库打包会踩坑：

```
消费者链接: undefined reference to `mp3dec_ex_open'
```

根因：`minimp3_ex.h` 声明了 **14 个非 static 公共函数**
（`mp3dec_load_buf` / `mp3dec_ex_open` / `mp3dec_detect_buf` / …），
INTERFACE 包不编译任何 TU，这些符号无处生成。

同时上游测试是 shell for-循环：

```sh
# 上游 scripts/test.sh
for i in vectors/*.bit; do
    $APP $i ${i%.*}.pcm    # 解码并逐样本比对参考 PCM（PSNR 合规）
done
```

不迁移的话这些测试**完全不会**在 Conan 生命周期内执行——CI L1 拿不到
任何测试执行痕迹，等于"适配了但没验证"。

## 解法（零源码补丁）

conanfile.py 的 build() 用 `conan.tools.files.save()` 生成两个文件：

**① amalgamated 单 TU（minimp3.c）：**

```c
#define MINIMP3_IMPLEMENTATION
#include "minimp3_ex.h"
```

**② 薄 CMakeLists.txt：**

```cmake
add_library(minimp3 minimp3.c)
target_include_directories(minimp3 PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
# 上游测试驱动原样编译（自带 main，独立 TU，仅链 libm）
add_executable(minimp3_upstream_test minimp3_test.c)
target_link_libraries(minimp3_upstream_test PRIVATE m)

enable_testing()
# shell for-循环 → 每向量一条 CTest 用例（参数与上游脚本逐字一致）
file(GLOB MINIMP3_VECTORS "vectors/*.bit")
foreach(vec IN LISTS MINIMP3_VECTORS)
    get_filename_component(name ${vec} NAME_WE)
    add_test(NAME upstream_vector_${name}
             COMMAND minimp3_upstream_test ${vec} vectors/${name}.pcm
             WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR})
endforeach()

install(TARGETS minimp3 ARCHIVE DESTINATION lib LIBRARY DESTINATION lib)
install(FILES minimp3.h minimp3_ex.h DESTINATION include)
```

build() 末尾 `cmake.test()` 全量真跑 → conan create 日志留下
`x/x tests passed` 行，CI L1a/L1b/L1c 三检全过。

消费者侧：链接 `minimp3::minimp3`，**禁止**再定义
`MINIMP3_IMPLEMENTATION`（符号已在库内）。

## 坑：conan 2.29 的 cmake.test(cli_args=...)

`cli_args` 拼在 `cmake --build` 命令行上，**不是** ctest 参数。传
ctest 专属参数（如 `--output-on-failure`）→ cmake 打印 usage →
`ConanException: Error 1 while executing`。正确姿势：裸 `cmake.test()`，
需要失败详情时设 `CTEST_OUTPUT_ON_FAILURE=1` 环境变量。

## 实证（PR !14508，OHOS aarch64，clang 15.0.4）

```
86/86 #86 upstream_mode6_stream ... Passed   （1 selftest 72 断言
                                               + 83 向量 PSNR 比对
                                               + 2 模式抽样，全部真跑）
100% tests passed, 0 tests failed out of 86

1/1 test_minimp3 ... Passed （消费者 25 断言：合成静音帧解码/截断/契约）
```

上游测试驱动 `minimp3_test.c` **零修改**——只做组织形式迁移
（shell 循环 → CTest 注册，命令行参数逐字一致）。

## 适用面与推广价值

- 同形态库清单：stb_image/stb_truetype 系、MurmurHash3、
  miniaudio、sqlite amalgamation 类、一切"单头文件 +
  XXX_IMPLEMENTATION 宏"形态的库
- 无向量测试的同类库可复用"合成最小合法输入"手法
  （minimp3 用 `0xFF 0xFB 0x90 0x00` 帧头 + 全零 payload 的
  MPEG1 L3 静音帧，417 字节，无音频文件即可验证解码核心）
- 先例参照：archives/m/MurmurHash3/0.0.1（hancho 被替换，
  同款 save() 打法）

## 降级方案（fallback）

真 header-only INTERFACE 包：只拷 `.h` 到 include/，
`cpp_info.includedirs=["include"]`——但必须文档强制消费者在恰好一个
TU 里定义实现宏，把链接义务转嫁给每个下游，仅作下策。
