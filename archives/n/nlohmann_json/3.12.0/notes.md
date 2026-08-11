# nlohmann_json 3.12.0 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出动态库供链接与 dlopen（具体库名由 collect_libs 自动收集）。

## 关键适配
- 无特殊适配：上游源码直接可用鸿蒙 PC 原生工具链构建。

## 关键适配
- `--header-only`：`package_type = "header-library"` + `package_id` 恒定
  （`self.info.clear()`）。不这么做的话 `shared`/`fPIC` 会进 package_id，
  同一份**逐字节相同**的头文件按编译器/架构排列组合出一堆二进制，
  消费方设置稍有不同就报 `Missing binary`。实测 package_id 为
  `da39a3ee5e6b4b0d3255bfef95601890afd80709`（空哈希）—— 一份头文件全世界共用一个包。
- `--include-dirs include`：头装在 `include/nlohmann/`，下游写
  `#include <nlohmann/json.hpp>`。
- `-DJSON_BuildTests=OFF`：上游单测要额外的测试数据仓，与本包无关。

## 状态
built —— 真机 `conan create -pr ohos-native --update` rc=0（2026-08-10 21:51）。

### 真机证据
test_package **22 条真实断言全通过**，分五组：版本宏（证明装进来的确是 3.12.0
而非设备上别处的旧头）、解析与类型、序列化往返、错误处理（坏输入必须抛而不是
悄悄给空对象）、二进制格式 CBOR/MessagePack（含 UTF-8 多字节往返）。

header-only 包的 test_package 没有 `.so` 可 dlopen，「能加载」这种弱判据在这里
根本不存在；它要防的是另一类问题 —— 装了但下游 include 不到、版本宏与实际内容
对不上。所以断言里既验行为，也验布局与版本。

### 布局
```
include/nlohmann/*.hpp
share/cmake/nlohmann_json/     ← 注意在 share 下，不是常见的 lib/cmake
share/pkgconfig/
```
