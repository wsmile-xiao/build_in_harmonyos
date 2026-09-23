# clunk 1.3.261 适配笔记

## 上游与源码

- CLUNK 是实时 3D（双耳）声音生成 C++ 库，1.3.261 发布于 2014-09-29。
- 源码：`https://downloads.sourceforge.net/project/clunk/clunk-1.3.261.tar.bz2`
  （sha256 `1b15ce35…5e8b24b7`，70 个文件，含 CMakeLists.txt + SCons 双构建）。
- 许可证：LICENSE 文件为 LGPL-2.1（FreshPorts 同标注 LGPL21）。
- 构建系统：CMake（`cmake_minimum_required(VERSION 2.6)`，`find_package(SDL)` 即 SDL 1.2）。

## 依赖

- 唯一外部依赖是 SDL 1.2 API。OHOS 无原生 SDL1，采用 `sdl12-compat/1.2.68`
 （dxx-rebirth 0.6 同方案），legacy FindSDL 通过 `SDL_INCLUDE_DIR` /
  `SDL_LIBRARY` 缓存变量指向该包，不探测宿主文件系统。
- 本库默认静态（`BUILD_SHARED_LIBS=OFF`，`shared=False`）；`shared=True` 时同样构建。

## 补丁（平台无关，不含平台宏）

`patches/0001-cmake-ohos-compat.patch`：

1. `cmake_minimum_required` 2.6 → 3.5（现代 CMake 兼容，leela-zero 同类补丁先例）。
2. 新增 `CMAKE_CXX_STANDARD 11`（与上游 master 一致）：源码含 `throw()` 异常声明
   与 `std::auto_ptr`，C++17 已移除，必须 C++11/14 才能编译。
3. `add_library(clunk SHARED` → `add_library(clunk`，由 `BUILD_SHARED_LIBS` 控制动静。
4. 新增 `VERSION 1.3.261 / SOVERSION 1`，补齐 DT_SONAME（CI L5a 门禁要求）。

生成头安装路径（配方内修复，不走补丁）：`configure_file(... clunk/config.h.in
  .../clunk/config.h)` 生成路径带 `clunk/` 子目录，但 `PUBLIC_HEADERS` 误写为
  `${CMAKE_CURRENT_BINARY_DIR}/config.h`（缺 `clunk/`），导致真机
  `install(FILES ...)` 报 `file INSTALL cannot find .../build/Release/config.h`。
  配方 `build()` 在 `apply_conandata_patches` 后调用幂等 `_fix_cmake_config_path()`，
  对 `CMakeLists.txt` 做字符串替换为 `${CMAKE_CURRENT_BINARY_DIR}/clunk/config.h`
  （与 `_fix_pow10f_sources` 同模式，对 hunk 行号偏移免疫）。
  不走补丁的原因：独立 0003 与折叠进 0001 的两轮补丁均因真机 BSD patch 严格按行号
  匹配（`hunk doesn't match at line 57 / actual: buffer.h`）而应用失败，故改用
  配方运行时修复。扁平安装后仍落到 `include/clunk/config.h`，与
  `#include <clunk/config.h>` 一致。

`patches/0002-pow10f-portability.patch`（真机 `pow10f` 未声明修复）：

- `pow10f()` 是 GNU 扩展，HarmonyOS/musl 真机 clang 报
  `use of undeclared identifier 'pow10f'`（`clunk/hrtf.cpp:65` 唯一调用处）。
- 不采用 `#ifndef pow10f` 宏回退（函数符号非宏，该守卫测不出缺失）；
  直接把调用点重写为等价 C99 `powf(10.0f, x)`，并补 `<math.h>`；
  `source.cpp` 中只定义不调用的兼容块直接删除；不重定义 C99 `log2f`。
- 配方 `build()` 在 `apply_conandata_patches` 后另有幂等 `_fix_pow10f_sources`
  兜底：即使补丁未导出/未应用，也把残留 `pow10f(` 重写为 `powf(10.0f, `，
  已打补丁的树不受影响。

## 上游测试接入（真机实测口径）

上游盘点（test.cpp 约 150 行 + test_c.c）：

| 上游用例 | 形态 | 结论 |
|---|---|---|
| `./clunk-test f` | MDCT 参考实现 vs FFT 实现对比，打印双方数据 | ✅ 接入：确定性、无头、可判读 |
| `./clunk-test t` | FFT 正/逆变换 roundtrip，打印频谱与残差 | ✅ 接入：确定性、无头、可判读 |
| `./clunk-test` 默认 | SDL 音频播放 helicopter.wav 约 7 秒，无断言 | ❌ 排除：需物理声卡，无断言 |
| `./clunk-test bm/bf` | 百万级 MDCT/FFT 计时循环，无判定 | ❌ 排除：纯计时，无通过性判定 |
| test_c.c | C API 音频播放 demo，无断言，CMake 不构建 | ❌ 排除：需声卡，非构建产物 |

- 防"静默通过"：两 modes 均要求退出码 0 **且**输出 ≥200 字符 **且**含预期段落
 （f 含 `reference:`/`fft based:`，t 含逗号数值行），否则判失败并阻断构建。
- 配方 `build()` 运行后打印 `HMBS_UPSTREAM_TEST_RESULT`（discovered=2），结果同时
  落盘 `build_folder/upstream_test_result.json` 并随包发布到 `res/`；
  `test_package` 重传该标记，防 Conan 缓存跳过 build() 导致标记丢失。

## test_package（2 个真实消费者用例）

`test_clunk.cpp`：① FFT roundtrip（频谱能量 >0 且逆变换最大残差 <1e-3）；
② `clunk::Buffer`（编译进 lib 的方法：alloc/fill/copy/dump，断言尺寸与内容）。
`test()` 运行二进制（非零退出即失败）后打印 `HMBS_TEST_PACKAGE_RESULT`
（discovered=2/passedCount=2），并重传上游标记。

## 产物

- 共享：`libclunk.so.1.3.261` + `libclunk.so.1`（SONAME）+ `libclunk.so`；
  静态：`libclunk.a`。头文件到 `include/clunk/`（含生成的 `config.h`）。
- 配方额外安装最小 `lib/cmake/clunk/clunk-config.cmake`
 （`clunk::clunk` UNKNOWN IMPORTED），因上游不自带 CMake config。


## 2026-09-09 test_package 头文件缺失修复

- 真机 test_package 失败： buffer.h:23 fatal error clunk/types.h file not found。
- 根因：上游 PUBLIC_HEADERS 未收录 types.h 等以 clunk/ 前缀被引用的头文件，且 install(FILES) 会把 backend/sdl/backend.h 扁平化。
- 修复：配方 _fix_cmake_config_path 改用 install(DIRECTORY clunk/ ... FILES_MATCHING *.h) + 单独安装生成的 config.h；package() 新增 _fixup_package_headers 兜底拷贝全部 *.h（keep_path 保留子目录）及生成的 config.h。
