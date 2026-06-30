# squirrel-lang

**描述**: 高级、命令式、面向对象的编程语言

**许可证**: MIT

**版本**: 3.2 stable

## 简介

Squirrel 是一款高级、命令式、面向对象的编程语言，设计为轻量级脚本语言，
适用于对体积、内存带宽和实时性有严格要求的应用场景（如游戏引擎）。

## 语言特性

- 轻量级且可嵌入
- 面向对象（类、继承）
- 函数式编程支持（一等函数、闭包）
- 弱引用与委托机制
- 尾递归优化
- 异常处理（try/catch/throw）
- 协程（cooperative multi-threading）
- 垃圾回收

## OpenHarmony 编译信息

| 项目 | 说明 |
|------|------|
| 构建系统 | CMake |
| 编译器 | clang/clang++ 15.0.4 |
| 依赖 | 无外部依赖 |
| 二进制 | sq（动态）、sq_static（静态） |
| 库文件 | libsquirrel.so, libsquirrel_static.a, libsqstdlib.so, libsqstdlib_static.a |
| 头文件 | squirrel.h, sqconfig.h, sqstdaux.h, sqstdio.h, sqstdblob.h, sqstdmath.h, sqstdstring.h, sqstdsystem.h |

## 注意事项

- sq_static（静态链接）推荐用于 OpenHarmony 平台，无需额外库依赖
- sq（动态链接）需要 LD_LIBRARY_PATH 或 RUNPATH 指向 `$PREFIX/lib`
- 源码包缺少 squirrel-config.cmake.in，需补丁添加
- CMake 4.x 需要 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`