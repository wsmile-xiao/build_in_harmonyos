# slang - S-Lang 库

## 软件概述

S-Lang 是一个强大的解释型脚本语言库，由 John E. Davis 开发。它提供了丰富的内置函数和数据类型，支持数组、关联数组、结构体等高级数据结构，以及正则表达式、字符串处理、数学运算等功能。S-Lang 库被广泛应用于科学计算、文本处理、系统管理等领域。

### 主要功能

1. **解释型语言引擎**：
   - 完整的脚本语言解释器
   - 支持变量、函数、控制流、异常处理
   - 丰富的内置函数库

2. **数据结构**：
   - 数组和关联数组
   - 结构体
   - 列表
   - 类型系统

3. **模块系统**：
   - PCRE 正则表达式支持
   - PNG 图像处理
   - ZLIB 压缩
   - Base64 编码
   - CSV 解析
   - JSON 处理
   - Socket 网络通信
   - 统计函数
   - 终端 I/O

4. **slsh - S-Lang Shell**：
   - 交互式脚本解释器
   - 支持脚本文件执行
   - 模块加载机制

### 应用场景

- 科学计算
- 文本处理
- 系统管理脚本
- 配置文件解析
- 嵌入式脚本引擎

## 版本信息

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 2.3.3 | ❌ failed | 2026-07-18 | 首次适配 |

## 依赖关系

无外部依赖，仅需系统库：
- libm（数学库）
- libdl（动态链接）
- libpthread（线程）

## 编译产物

### 2.3.3 版本

**库文件**：
- `lib/libslang.so` - 共享库
- `lib/libslang.a` - 静态库

**头文件**：
- `include/slang/slang.h` - 主头文件

**可执行文件**：
- `bin/slsh` - S-Lang Shell 解释器

## 使用方法

### CMake 集成

```cmake
find_package(slang REQUIRED)
target_link_libraries(your_target slang::slang)
```

### 手动编译示例

```c
#include <slang/slang.h>

int main(void) {
    SLang_init_all();
    /* ... */
    return 0;
}
```

编译命令：
```bash
clang -o test_slang test_slang.c -I/path/to/include -L/path/to/lib -lslang
```

## 质量门禁状态

### 2.3.3 版本

| 门禁 | 状态 | 说明 |
|------|------|------|
| G0: 干净构建 | ⏳ 等待 | 等待官方 CI 验证 |
| G1: 二进制完整性 | ⏳ 等待 | 等待官方 CI 验证 |
| G2: 功能可用性 | ⏳ 等待 | 等待官方 CI 验证 |
| G3: 可移植性 | ⏳ 等待 | 等待官方 CI 验证 |
| G4: 档案完整性 | ⏳ 等待 | 等待官方 CI 验证 |

## 相关资源

- **官方网站**：https://www.jedsoft.org/slang/
- **源码下载**：https://www.jedsoft.org/releases/slang/
- **文档**：https://www.jedsoft.org/slang/doc/

## 更新历史

- **2026-07-18**: 首次适配 2.3.3 版本
- **2022-08-05**: 上游发布 v2.3.3

---

**维护者**: openharmony-compile-agent
**最后更新**: 2026-07-18