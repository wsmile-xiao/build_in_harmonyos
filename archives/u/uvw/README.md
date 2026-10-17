# uvw

uvw 是一个 header-only、事件驱动、轻量易用的 libuv 现代 C++ 封装库。
自 3.x 起同时支持编译为静态库，本适配采用其默认的 header-only 形态。

## 功能概述

- **libuv C++ 封装**：用优雅的 C++ API 隐藏 libuv 的 C 风格接口（handle / request / loop / emitter 模型）
- **Header-only**：只需包含 `uvw.hpp` 或 `uvw/*.hpp`，无需编译库本体
- **事件驱动**：基于发射器（emitter）的类型安全事件回调
- **双模式**：header-only 与可编译静态库两种用法（见上游 `BUILD_UVW_LIBS` 选项）

## OHOS 适配

### 特性

- **Header-only 配方**：`package_type = "header-library"`，`package_id` 清零
- **依赖 Conan libuv**：`requires libuv/1.52.1`（制品仓已发布版本；上游名义绑定 1.48.0，见 notes.md 说明）
- **上游测试全量接入**：`BUILD_TESTING=ON` + `FIND_LIBUV=ON` + `FIND_GTEST_PACKAGE=ON`，
  用 Conan 的 libuv 与 gtest 替代上游默认的 FetchContent 网络拉取，`build()` 内运行完整 ctest 套件
- **平台规避**：`CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`（E092 规避）；
  OHOS 下 `CMAKE_HAVE_LIBC_PTHREAD=True`（libc 内建 pthread，避免 `-lpthreads` 误探测）

### 已知问题

- 上游 `BUILD_DNS_TEST` 默认 OFF（需外网 DNS），本适配保持 OFF，不纳入测试面
- 消费者需链接 libuv（`libuv::libuv`），header-only 形态下由配方 `cpp_info.requires` 透传

### 与 Linux 的差异

- 需设置 `CMAKE_SYSTEM_NAME=Linux` 规避 CMake 对 OHOS 平台未知问题
- 上游测试默认用 FetchContent 从 GitHub 拉取 googletest 与 libuv；
  本适配一律改用制品仓 Conan 包（`gtest/1.17.0` + `libuv/1.52.1`），并显式关闭 `FETCH_LIBUV`

## 使用方式

```cmake
# CMakeLists.txt
find_package(uvw REQUIRED CONFIG)
find_package(libuv REQUIRED CONFIG)

add_executable(my_app main.cpp)
target_link_libraries(my_app PRIVATE uvw::uvw libuv::libuv)
target_compile_features(my_app PRIVATE cxx_std_17)
```

```cpp
#include <uvw.hpp>

int main() {
    auto loop = uvw::loop::create();
    auto timer = loop->resource<uvw::timer_handle>();
    timer->on<uvw::timer_event>([](const uvw::timer_event &, uvw::timer_handle &) {});
    timer->start(uvw::timer_handle::time{5}, uvw::timer_handle::time{0});
    loop->run();
    return 0;
}
```

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [3.4.0](./3.4.0/) | built | 2026-09-19 |

## 参考资料

- GitHub: https://github.com/skypjack/uvw
- Conan Center: https://conan.io/center/recipes/uvw
