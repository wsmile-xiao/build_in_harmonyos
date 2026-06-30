# robin-map 1.4.1 编译笔记

## 软件信息
- **名称**: robin-map
- **版本**: 1.4.1
- **描述**: C++17 header-only哈希映射库（基于robin-hood hashing）
- **下载源**: https://github.com/Tessil/robin-map/archive/refs/tags/v1.4.1.tar.gz
- **构建系统**: cmake
- **库类型**: header-only（纯头文件库）

## 编译过程

### Header-only库特点
robin-map是header-only库，不需要编译，只需要安装头文件和cmake配置文件：
- `include/tsl/robin_map.h` - 主要头文件
- `include/tsl/robin_set.h` - set版本
- `include/tsl/robin_hash.h` - 哈希实现
- `include/tsl/robin_growth_policy.h` - 增长策略
- `share/cmake/tsl-robin-map/*.cmake` - cmake配置文件

### 编译参数
```bash
cmake -B build -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local -DTSL_ROBIN_MAP_ENABLE_INSTALL=ON
cmake --install build --prefix=/storage/Users/currentUser/usr/local DESTDIR=/storage/Users/currentUser/test-install-robin-map-1.4.1
```

### 无需特殊适配
- Header-only库天然跨平台兼容
- 不需要处理平台差异
- 不需要ELF签名（无二进制文件）

---

**编译开始**: 2026-05-21 15:47
**编译结束**: 2026-05-21 15:48
**最终状态**: published
**产物**: robin-map-1.4.1-ohos-aarch64.tar.gz (133KB)

## 使用说明

在CMake项目中使用：
```cmake
find_package(tsl-robin-map REQUIRED)
target_link_libraries(your_target PRIVATE tsl::robin_map)
```

在C++代码中使用：
```cpp
#include <tsl/robin_map.h>

tsl::robin_map<std::string, int> map;
map["key"] = 42;
```