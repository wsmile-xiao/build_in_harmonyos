# nlohmann_json (JSON for Modern C++)

## 简介
单头文件的 C++ JSON 库，提供解析、序列化、STL 风格的容器接口，
以及 CBOR / MessagePack / BSON 等二进制格式。**纯头文件，无需链接。**

## 基本信息
- 官网: https://json.nlohmann.me/
- 源码: https://github.com/nlohmann/json/releases
- 许可证: MIT
- 构建系统: cmake（仅用于装头文件与 CMake config）
- 依赖: 无

## 已编译版本

| 版本 | package_id | 状态 | 日期 |
|---|---|---|---|
| 3.12.0 | `da39a3ee…`（恒定） | built（真机 22 条断言通过） | 2026-08-10 |
| 3.1.1 | `da39a3ee…`（恒定） | built（真机 22 条断言通过） | 2026-08-11 |

> **为什么保留 3.1.1**：qiskit-aer 钉 `find_package(nlohmann_json 3.1.1 EXACT)`。
> 用 3.12.0 编出来的 aer 能构建、能 import、能跑简单线路，但自带测试套件里
> **196 个**噪声模型用例全废（`Invalid noise_params JSON: not an object.`）——
> aer 把自定义 pybind11 caster 塞在 `namespace std` 里，而 nlohmann_json 在
> 3.2/3.9/3.11 改过 ADL 解析规则。**新项目用 3.12.0，钉旧版的消费方用 3.1.1。**
>
> 注意布局差异：3.1.1 的 CMake config 在 `lib/cmake/`，3.12.0 在 `share/cmake/`。

> package_id 是**恒定的空哈希**：纯头文件不因编译器/架构而异，一个包全世界共用。
> 这不是偷懒 —— 若按 `shared`/`fPIC`/编译器排列组合出多个 package_id，
> 内容完全相同却互不匹配，消费方设置稍有不同就报 `Missing binary`。

## 消费方式

```bash
conan install --requires=nlohmann_json/3.12.0 -pr ohos-native
```

```cpp
#include <nlohmann/json.hpp>
using json = nlohmann::json;
```

CMake 侧目标名 `nlohmann_json::nlohmann_json`。

## 布局提示

CMake config 装在 **`share/cmake/nlohmann_json/`**（不是常见的 `lib/cmake/`），
pkgconfig 在 `share/pkgconfig/`。用 `find_package(nlohmann_json)` 时若手工设
`CMAKE_PREFIX_PATH`，注意这一点。

## 消费方

- **qiskit-aer**：`-DDISABLE_CONAN=ON` 路径下 `find_package(nlohmann_json 3.1.1)`。
