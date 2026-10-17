# libnop

> Native Object Protocols —— 头文件式的 C++ 序列化 / RPC 框架（Google）。

## 简介

libnop 用注解驱动的方式把 C++ 类型序列化成与平台无关的字节流：

- `NOP_STRUCTURE(Type, member...)` 注解自定义类型（含私有成员），`NOP_EXTERNAL_STRUCTURE`
  注解无法修改的类型（如 `struct tm`）；
- `nop::Serializer<StreamWriter<...>>` / `nop::Deserializer<StreamReader<...>>` 负责
  写入与读回，支持整型、字符串、容器、枚举、`Optional`、`Variant`、`Handle`、`Result`；
- `nop/rpc/` 在其上提供简易 RPC 接口绑定与分发。

库本身是纯头文件（`include/nop/**`），无第三方依赖。

## OHOS 适配要点

- **纯头文件、无依赖**：`package_type="header-library"`、`no_copy_source=True`、
  `package_id()` 清空二进制设置；只安装 `include/nop/**` 与 `licenses/LICENSE`。
  `copy()` 的 `dst` 必须用 `package_folder` 下的**绝对路径**，否则包为空。
- **上游 GoogleTest 套件（315 用例）在真机运行**：配方用
  `test_requires("gtest/1.17.0")` + `test_requires("gmock/1.17.0")`，并以变量注入方式
  对接上游 Makefile（`GTEST_INCLUDE` / `GTEST_LIB` / `CC` / `CXX`）。
- 两个必改的构建变量：上游 `HOST_CXXFLAGS := -std=c++14` 与 gtest 1.17 的 C++17 要求冲突
  → 覆盖为 `-std=c++17`；上游 `-Werror` 对第三方 gtest 头过于严格 → 保留 `-Wextra`。
- `test_requires` 的包目录要用 `self.dependencies["gtest"]` 获取（不在
  `self.dependencies.build` 中）。
- 版本命名：平台版本 `0.0-git20211103.35e800d` 是 Debian 源包
  `0.0~git20211103.35e800d` 的 Conan 形式（`~` 不能出现在版本里）。

## 依赖

无（测试期依赖 gtest/gmock，仅 `test_requires`，不进包依赖）。

## 使用

```cmake
find_package(libnop CONFIG REQUIRED)
target_link_libraries(app PRIVATE libnop::libnop)
```

```cpp
#include <nop/serializer.h>
#include <nop/structure.h>
#include <nop/utility/stream_reader.h>
#include <nop/utility/stream_writer.h>

struct Point {
  int x{0};
  int y{0};
  NOP_STRUCTURE(Point, x, y);
};

nop::Serializer<nop::StreamWriter<std::stringstream>> serializer;
serializer.Write(Point{1, 2});

nop::Deserializer<nop::StreamReader<std::stringstream>> deserializer{serializer.writer().stream().str()};
Point out;
deserializer.Read(&out);      // out.x == 1, out.y == 2
```

## 功能验证

```sh
conan create archives/l/libnop/0.0-git20211103.35e800d -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# rc=0
# 上游 gtest 套件：315 passed / 0 failed（真机）
# 消费者：ctest 1/1，8/8 断言
```
