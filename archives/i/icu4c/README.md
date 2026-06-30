# ICU4C - International Components for Unicode

ICU 是一套成熟的、广泛使用的 C/C++ 和 Java 库，为软件应用程序提供 Unicode 和全球化支持。

## 描述

ICU 提供以下功能：
- Unicode 字符集处理
- 文本处理（双向文本、断词、断行等）
- 国际化（locale 数据、时区、日历等）
- 字符编码转换
- 正则表达式
- 数字格式化、货币格式化
- 消息格式化
- 字符串比较和搜索

## 版本信息

当前版本：78
Unicode 版本：17.0
发布日期：2026-04-28

## 编译信息

- 构建系统：autotools
- 编译器：clang
- 平台：HarmonyOS aarch64

### 特殊编译参数

ICU 在 HarmonyOS 上需要静态编译模式：
- `--disable-shared` - 禁用动态库
- `--enable-static` - 启用静态库
- `--with-data-packaging=static` - 数据嵌入静态库

这是由于 HarmonyOS 动态链接器对 ICU 的 stubdata 共享库有特殊限制。

## 依赖

无外部依赖。

## 许可证

ICU 采用 Unicode/ICU 许可证，这是一种宽松的开源许可证，类似于 MIT/BSD。

## 相关链接

- 官网：http://icu-project.org/
- GitHub：https://github.com/unicode-org/icu
- Unicode：https://home.unicode.org/