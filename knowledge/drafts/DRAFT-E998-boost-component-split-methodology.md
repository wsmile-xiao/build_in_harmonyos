# E998: boost 组件包拆分方法论（路径 B 素材）

> Draft: DRAFT-E998-boost-component-split-methodology
> 来源：boost1.84-math/1.84.0 适配（PR #8441），2026-09-05
> 适用：boost 1.84 系列全部组件拆分包（math/atomic/wave/url/contract 等）

## 为什么需要方法论

boost 完整包在 OHOS 只能手动编译（b2 SHELL 执行机制不兼容，E068/E099），
体积大（头文件树 244MB）且带 zlib 依赖。下游只需单组件时，按官方
Jamfile.v2 定义裁剪为独立组件包是通用需求——但每个组件的源清单、
include 路径、依赖、测试形态都不同，需要一套可复用的四步法。

## 组件包拆分四步法

### ① 裁剪依据：读官方 Jamfile.v2

`libs/<comp>/build/Jamfile.v2` 是组件源文件清单的唯一权威。例如 math：

- `C99_SOURCES`（21 函数名）→ boost_math_c99 / c99f / c99l
- `TR1_SOURCES`（21 函数名）→ boost_math_tr1 / tr1f / tr1l
- 每函数名 3 个变体文件（无后缀=double、`f`=float、`l`=long double）
- 42 × 3 = 126 文件，与磁盘逐一核对无缺失

### ② 配方模板：复用完整包底稿骨架

boost/<ver> 完整包的 conanfile.py 已验证可用的骨架：

- `_compile_lib()`：逐文件 clang++ 编译 + llvm-ar rcs 归档
- cxxflags：`-std=c++17 -stdlib=libc++ -fPIC -I<boost_root>
  -DBOOST_ALL_NO_LIB -DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`
- **组件特有**：`-I libs/<comp>/src`（Jamfile 的 `<include>` 等价物，
  tr1 源文件以 `#include <pch.hpp>` 引入同目录头）
- package()：完整 boost/ 头文件树 + 组件库（下游与其他组件包共存）

### ③ 依赖裁剪：grep 源码引用

| 组件 | 源码引用 zlib/iostreams | requirements |
|------|------------------------|--------------|
| math | 无 | 空 |
| iostreams | zlib | zlib/1.3.1 |

底稿 boost 完整包的 zlib 依赖来自 iostreams——组件裁剪后必须重新判定，
不能照抄底稿。

### ④ 测试选型：绕开 boost_unit_test_framework

上游测试优先选**不依赖编译库的形态**：

- math 的 `libs/math/test/test_tr1.c` 是**纯 C** 测试（`__cplusplus` 未
  定义时走 `tr1_c_macros.ipp` 展开全局宏）——必须 `clang -std=c99` 编译
  （clang++ 按 C++ 处理会报 undeclared identifier）；库内 C++ 异常要求
  链接行追加 `-lc++`
- test_package 三层覆盖：header-only API（constants/gcd/quaternion）+
  编译库 C 接口（beta/erf/cbrt）+ CMake 组件消费链路
  （find_package(X REQUIRED CONFIG COMPONENTS ...)）

### 命名与命名空间

- 包名：`boost<版本前缀>-<组件>`（如 boost1.84-math），先例 qt5-qt3d/
  openssl-4，与完整包 boost/<ver> 互不冲突
- CMake：独立 `cmake_file_name`（BoostMath）与组件命名空间
  （BoostMath::tr1），避免与完整包的 Boost:: 冲突，可共存

## 实例

boost1.84-math 1.84.0（PR #8441）：126 源文件 → 6 静态库 + 头文件树，
无第三方依赖，上游 test_tr1.c 普通模式 538 断言 100% 通过，test_package
10 组 API 断言全过。

## 推广价值

同一会话/同一批次的 boost1.84 系列组件包（math/atomic/wave/url/
contract 等）均可按此流程流水线化：裁剪依据 → 底稿骨架 → 依赖重判 →
测试选型 → 命名规范。单组件是孤立适配；四步法是可跨组件复用的方法论。

## 降级方案（fallback）

- 组件测试全部依赖 unit_test_framework（无独立 main 测试）→ 从
  `libs/<comp>/example/` 取示例程序编译运行，或退化为 test_package 自写
  断言（PR 正文如实说明上游测试形态限制）
- 组件为 header-only（Jamfile.v2 无 SOURCES）→ 跳过编译，只装完整
  boost/ 头文件树（参照完整包 boost_headers 组件定义）

## 跨组件独立验证

| 组件 | 会话 | 四步法应用 | 验证结果 |
|------|------|-----------|---------|
| boost1.84-math | 本 PR !8441 | 126 源文件→6 库 + test_tr1.c 双模式 | CI #40551/#40565 绿；普通模式 538/538 |
| boost1.84-system | 并行会话 | 单 TU（error_code.cpp）+ 94 个 lightweight_test | 独立实操，同底稿骨架同测试选型逻辑 |

system 组件的独立实操证明四步法非 math 孤立经验：裁剪依据（Jamfile
单 TU 核对）、底稿骨架（same approach as boost/1.84.0）、测试选型
（lightweight_test 绕开 b2）三要素完全一致。

## 证据链

- 完整实现：archives/b/boost1.84-math/1.84.0/conanfile.py（PR !8441）
- CI 构建：#40536（首轮网络抖动）/ #40551 / #40565（全绿）
- 根因底稿：archives/b/boost/1.85.0/notes.md（b2 SHELL 失败机制）
