# UTF8-CPP

UTF8-CPP 是一个 C++ 可移植 UTF-8 编解码库，提供高效、安全、易用的 UTF-8 字符串操作接口。

## 功能概述

- **UTF-8 编解码**：UTF-8 与 UTF-16/UTF-32 互转
- **字符迭代**：UTF-8 字符串迭代器，按字符而非字节遍历
- **字符串校验**：检测无效 UTF-8 序列
- **无效序列替换**：将无效字节替换为指定字符
- **字符长度计算**：计算 UTF-8 字符串的字符数（非字节数）
- **低层接口**：直接操作字节序列的 unchecked 接口

## OHOS 适配

### 特性
- **Header-only 库**：无需编译二进制，只需安装头文件
- **CMake INTERFACE library**：通过 CMake 安装头文件和配置文件
- **无依赖**：不依赖任何第三方库

### 已知问题
- 无已知问题

### 与 Linux 的差异
- 需设置 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64` 规避鸿蒙平台未知问题

## 使用方式

```cmake
# CMakeLists.txt
find_package(utf8cpp REQUIRED)
target_link_libraries(my_app PRIVATE utf8cpp::utf8cpp)
```

```cpp
#include <utf8cpp/utf8.h>
#include <string>
#include <vector>

int main() {
    std::string u8str = "你好";
    // 计算字符数（非字节数）
    auto char_count = utf8::distance(u8str.begin(), u8str.end());
    // 转换为 UTF-32
    std::vector<uint32_t> u32str;
    utf8::utf8to32(u8str.begin(), u8str.end(), std::back_inserter(u32str));
    return 0;
}
```

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [4.1.1](./4.1.1/) | built | 2026-07-14 |

## 参考资料

- GitHub: https://github.com/nemtrif/utfcpp
