# Mini-XML (mxml)

## 软件介绍

Mini-XML 是一个小型的 XML 库，用于在应用程序中读取和写入 XML 及 XML-like 数据文件，无需依赖大型非标准库。

**官方网站**: https://www.msweet.org/mxml/
**源码仓库**: https://github.com/michaelrsweet/mxml

## 功能特性

- 读取 UTF-8 和 UTF-16 编码的 XML 文件和字符串，写入 UTF-8 编码
- 数据存储在链表树结构中，保留 XML 数据层次结构
- SAX（流式）读取 XML 文件和字符串，最小化内存使用
- 支持任意元素名称、属性和属性值，仅受可用内存限制
- 支持"叶"节点中的整数、实数、不透明和文本数据类型
- 提供创建和管理数据树的函数
- "查找"和"遍历"函数，轻松定位和导航数据树
- 支持自定义字符串内存管理函数

## 版本信息

**当前版本**: 4.0.4
**发布日期**: 2025-01-19

### v4.0.4 更新内容

- 添加 Linux 特定构建文件，删除未使用的 long long 配置测试
- 文档修复
- 修复 NULL 选项指针时报告错误的问题
- 修复一些编译器警告
- 修复 MingW 上的安装问题

## HarmonyOS 编译说明

### 编译状态

✅ 已成功编译并通过测试

### 构建系统

autotools (configure + make)

### 补丁文件

编译需要应用以下 3 个平台适配补丁：

1. **0001-config.guess.patch** - 添加 __OHOS__ LIBC 检测和 HarmonyOS 系统识别
2. **0002-config.sub.patch** - 添加 ohos-linux 三元组验证
3. **0003-configure.patch** - 修改 umask 077 为 umask 000（HMDFS 权限问题）

### 编译依赖

无外部依赖，仅需：
- C99 兼容编译器 (clang)
- make 程序
- pthread 库

### 编译产物

- **libmxml4.a** - 静态库
- **libmxml4.so.2** - 动态库
- **mxml.h** - 头文件
- **mxml4.pc** - pkg-config 文件

### 安装验证

```bash
pkg-config --modversion mxml4  # 输出: 4.0.4
pkg-config --cflags mxml4      # 输出: -I<prefix>/include/libmxml4
pkg-config --libs mxml4        # 输出: -L<prefix>/lib -lmxml4
```

### 测试结果

所有测试通过：
- Stdio file test passed ✅
- String test passed ✅
- File descriptor test passed ✅

## 许可证

Apache License 2.0

## 参考

- E007: config.guess HarmonyOS 识别问题
- E072: config.sub 三元组验证问题
- E011: HMDFS umask 权限限制问题