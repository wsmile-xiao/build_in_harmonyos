# DRAFT-conan2-cmakedeps-transitive-include-strip — Conan 2 CMakeDeps 消费端传递依赖 include 置空，test_package 编译报 boost 头文件 not found

> **Contributor**: ningyu | **Status**: DRAFT | **Updated**: 2026-09-03
> **Severity**: blocking (2) | **Category**: conan / cmake / packaging / c++-libraries
> **Audience**: 所有公共头传递 include 第三方库（尤其 boost）头文件的 Conan 2 library 配方作者

## 触发（trigger）

pokerstove/1.1 OHOS PC aarch64 适配：peval/penum 静态库的公共头
`pokerstove/peval/CardSet.h` → `Suit.h` → `#include <boost/operators.hpp>`，
依赖 ohpcd boost/1.84.0（cpp_info.include 只声明在 `boost_headers` 组件上）。
test_package 走 CMakeDeps 流：`find_package(pokerstove REQUIRED)` +
`target_link_libraries(test_package pokerstove::pokerstove)`。

## 症状（symptom）

主包（pokerstove 自身）构建打包全部成功，test_package 编译却报：

```
In file included from .../include/pokerstove/peval/CardSet.h:13:
.../include/pokerstove/peval/Suit.h:9:10: fatal error: 'boost/operators.hpp' file not found
```

生成目录 `test_package/build/<generators>/Boost-<arch>-data.cmake` 中：

```
set(boost_INCLUDE_DIRS_RELEASE )                      # 空！
set(boost_Boost_headers_INCLUDE_DIRS_RELEASE )        # 空！
```

而主包构建的 generators 里同名文件（boost 是直接依赖时）：

```
set(boost_INCLUDE_DIRS_RELEASE "${boost_PACKAGE_FOLDER_RELEASE}/include")
```

## 机制（root cause）

Conan 2.29.1 CMakeDeps 按依赖在**消费配方图中的位置**生成配置：

1. 只对消费配方（test_package）**直接 requires** 的包生成完整
   `*-data.cmake`（include dirs、lib dirs、组件属性全套）。
2. 对经由 pokerstove 传递引入的 boost，消费端生成的数据文件 include 变量
   被置空（`set(boost_INCLUDE_DIRS_RELEASE )`），仅 `pokerstove-Target-release.cmake`
   的 `INTERFACE_LINK_LIBRARIES` 里保留了 `boost::boost` 链接目标名。
3. 于是 `Boost::headers` 的 `INTERFACE_INCLUDE_DIRECTORIES` 为空，
   `-isystem` 只有 pokerstove 自己的 include，boost 头找不到。
4. **主包为何不报错**：pokerstove 构建时 boost 是它的直接依赖，
   CMakeToolchain 在 `conan_toolchain.cmake` 里
   `list(PREPEND CMAKE_INCLUDE_PATH "<boost包>/include" ...)` 兜底注入，
   上游 CMakeLists 又有 `include_directories(${Boost_INCLUDE_DIR})`——两路兜底
   掩盖了传播缺失，形成"主包过、测试挂"的隐蔽差异。
5. `self.requires("boost/1.84.0", visible=True)` **实测无效**：visible 只影响
   依赖关系/链接传播（graph 中保留节点），不改变 CMakeDeps 对传递依赖
   include 的裁剪行为。

## 修复（resolution）

test_package/conanfile.py 显式声明传递依赖：

```python
def requirements(self):
    self.requires(self.tested_reference_str)
    self.requires("boost/1.84.0")   # 公共头传递 include → 消费端显式声明
```

boost 成为 test_package 的直接依赖 → CMakeDeps 生成完整含 include 的配置
→ 编译链接通过。这是 CCI 生态消费"带 boost 公共头的库"的常规写法。

验证（conan create 内置 test_package 三层）：

```
1/1 Test #1: pokerstove_consumer_test .........   Passed    0.03 sec
[PASS] ps-eval equity output verified: AcAs 97.6768% / Kh4d 2.32323%
[PASS] ps-colex canonical colex table verified: 169 hands, AcAd=312, Kc4d=116
```

## 反模式（anti-patterns）

- ❌ test_package 里设 `CPATH`/`CMAKE_INCLUDE_PATH` 环境变量兜底——骗过编译器
  但破坏声明式依赖语义，干净 CI 复现失败。
- ❌ 只加 `visible=True` 就以为修好了（实测 include 仍为空）。
- ❌ 把 boost 头 copy 进自己包的 include/——制品膨胀且版本漂移。

## 关联

- similar_to: E216/E221/E283/E307（Conan 依赖传播家族）
- 姊妹问题：PkgConfigDeps 流的 .pc Requires 静默截断（见
  DRAFT-conan-shared-pkgconfig-requires-drop，audclient 案例static/shared
  包场景）——同一族"传递依赖属性向下游裁剪"在不同生成器上的两种表现。
