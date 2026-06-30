# tinyxml

TinyXml 是一个简单、小巧的 C++ XML 解析器，可以轻松集成到其他程序中。

## 版本

2.6.2

## 描述

TinyXml 是一个简单的 C++ XML 解析器。它解析 XML 文档，并从中构建文档对象模型（DOM），可以读取、修改和保存。

## 许可证

Zlib 许可证

## 构建系统

简单 Makefile（无 configure）

## 依赖

无依赖

## 产品

- **库**: libtinyxml（静态库）
- **测试程序**: xmltest

## 使用方法

```cpp
#include "tinyxml.h"

TiXmlDocument doc("demo.xml");
doc.LoadFile();
```

## 头文件

- `tinyxml.h` - 主头文件，包含所有类定义
- `tinystr.h` - 字符串工具类

## 编译说明

- 使用简单 Makefile，无标准 configure/install 目标
- 需要手动安装库文件和头文件
- 支持 STL 编译（设置 `TINYXML_USE_STL=YES`）

## 安装

```bash
# 编译
make

# 创建静态库
ar rc libtinyxml.a tinyxml.o tinyxmlparser.o tinyxmlerror.o tinystr.o
ranlib libtinyxml.a

# 手动安装
cp libtinyxml.a /usr/local/lib/
cp tinyxml.h tinystr.h /usr/local/include/
```

## 测试

运行测试程序验证功能：

```bash
xmltest
```

测试结果：109 个测试全部通过

## 功能特性

- ✅ XML 文档解析和生成
- ✅ DOM 树遍历和操作
- ✅ UTF-8 编码支持
- ✅ 属性读写
- ✅ 注释处理
- ✅ CDATA 支持
- ✅ 错误处理和位置追踪

## 注意事项

1. 本版本使用简单 Makefile，无 configure 脚本
2. 无标准 install 目标，需手动安装
3. 默认不使用 STL，可通过编译选项启用
4. 编译时有 7 个编码相关警告（不影响功能）