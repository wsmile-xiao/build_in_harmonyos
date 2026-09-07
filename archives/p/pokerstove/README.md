# pokerstove 1.1 — OpenHarmony 编译记录

## 基本信息
- 软件: pokerstove
- 版本: 1.1（上游 tag v1.1, 2023-10-28）
- 构建系统: cmake (>=3.0 要求；cmake 4.x 需 CMAKE_POLICY_VERSION_MINIMUM=3.5)
- 目标: ohos-aarch64 (clang 15, libc++)
- 上游: https://github.com/andrewprock/pokerstove

## 软件简介
C++ 德州扑克手牌评估库：
- **peval**: 手牌评估核心库（Card/CardSet 解析、Holdem/Omaha/Stud 等多种评估器）
- **penum**: 对局枚举库（CardDistribution、ShowdownEnumerator 权益计算）
- **ps-eval / ps-colex / ps-lut**: 命令行工具（权益计算、colex 索引、查找表生成）

## 编译指导
```bash
conan install --requires=boost/1.84.0 -g CMakeToolchain -g CMakeDeps \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
cmake -S . -B build -DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_BUILD_TYPE=Release
cmake --build build -j4 && (cd build && ctest)
```
注意：conan profile 必须用绝对路径（conan cache 有旧同名 profile 残留会按名字优先解析）。

## 补丁清单
- `0001-CMakeLists.txt.patch`：根 CMakeLists.txt 增加 HarmonyOS
  守卫的 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE` 全局 define（E127：OHOS musl 无
  pthread_setcancelstate；conan boost/1.84.0 只把该宏传播给链接 Boost 目标的
  程序，peval/penum 库源码仅 include boost 头不链接，宏传播不到）

## 已知限制
- 捆绑 googletest 1.14.0 随库一并构建（上游无条件 add_subdirectory），但不入包
- `ps-eval <单手>` 全枚举模式在本机约 110s（1.78B 次评估，算法固有开销）
- BUILD_PYTHON 默认 OFF，本适配保持 OFF（未适配 Python 桥接）

## 功能验证
```bash
$ ps-eval --game h AcAs Kh4d --board 5c8s9h
The hand AcAs has 97.6768 % equity (959 8 0 0)
The hand Kh4d has 2.32323 % equity (15 8 0 0)

$ ctest   # 捆绑 googletest 套件
100% tests passed, 0 tests failed out of 3
```
AcAs 对随机手牌权益 85.2037%（与上游文档经典值一致）。
