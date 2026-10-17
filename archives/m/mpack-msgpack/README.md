# MPack (MessagePack)

> C encoder/decoder for the MessagePack serialization format

## 简介

MPack 是一个用 C 语言实现的 MessagePack 序列化格式的编码器和解码器（ludocode/mpack）。它简单易用、对不可信数据安全、轻量级（适合嵌入式），并且有详尽的文档。

MPack 核心包含一个带缓冲的读取器和写入器，以及一个树形解析器，可将数据解码为动态类型节点树。辅助函数可以读取预期类型的值、处理文件、自动增长缓冲区或分配字符串、检查 UTF-8 编码等。

MPack 的设计是将源码直接嵌入到项目中使用（amalgamation 方式），但本配方将其编译为静态库以便通过 Conan 管理。

> **注意**：本包（mpack-msgpack）与仓库中已有的 mpack/1.6（MIME 邮件打包工具）是完全不同的软件，仅名称相似。

## OHOS 适配要点

- MPack 源码包不包含构建库的 CMakeLists.txt（仅包含测试用构建系统），需在 conanfile.py 的 build() 中生成
- 无外部依赖，纯 C 库，交叉编译友好
- 使用 Conan CMakeToolchain 自动处理 OHOS 交叉编译工具链（R33）

## 依赖

无外部依赖。MPack 是纯 C 库，甚至不强制依赖 libc。

## 功能验证

```bash
# 编译并运行消费者测试
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 参考

- [官方文档](https://ludocode.github.io/mpack/)
- [源码仓库](https://github.com/ludocode/mpack)
