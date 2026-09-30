# words-de

`words-de` packages German spelling dictionaries for use as read-only word-list resources.

## 功能概述

- `ngerman`：标准/新拼写词表，合并德国、德国地区与瑞士补充词表。
- `german`：与 `ngerman` 内容相同的 Aspell 兼容别名。
- `ogerman`：旧拼写词表。
- Conan run environment 提供 `WORDS_DE_FILE` 和 `WORDS_DE_OLD_FILE`。

## HarmonyOS 适配

本包只包含 UTF-8 数据文件，不生成依赖处理器架构的二进制，也不依赖目标系统上的 Aspell。配方在构建机解码上游 prezip v1/v2 词表并完成字符集转换。消费者测试已在 HarmonyOS PC x86_64 模拟器运行；同时交叉编译了 OHOS armv8 消费者程序。

## 依赖

无 Conan 编译依赖。运行时只需读取随包安装的 `share/dict` 文件。

## 参考

- [GNU Aspell 德语词库目录](https://ftp.gnu.org/gnu/aspell/dict/)
- [GNU Aspell 项目](https://aspell.net/)
