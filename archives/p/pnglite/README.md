pnglite is a lightweight C library for reading and writing non-interlaced PNG images through files or caller-provided IO callbacks.

## 功能概述

- 读取和写入 8 位或 16 位灰度、真彩色及带 Alpha 的 PNG 图像
- 支持文件 IO 与自定义回调 IO
- 使用 zlib 进行 IDAT 数据压缩与解压
- 校验 PNG chunk CRC，并实现 PNG 五种 scanline 反滤波算法

## OHOS 适配

- 使用 OHOS Clang 构建 AArch64 静态库 `libpnglite.a`
- 将上游私有相对 zlib 头路径修正为标准公开头 `<zlib.h>`
- 修复写入 IDAT 时未按 `compressBound()` 分配缓冲区的越界问题
- 修复 PNG 大端字段中高字节有符号左移的未定义行为
- 消费者测试覆盖 HarmonyOS 的 `__OHOS__` 平台宏、AArch64 与 zlib 编码路径

## 依赖关系

- zlib/1.3.1

## 参考资料

- https://sourceforge.net/projects/pnglite/
- https://sourceforge.net/projects/pnglite/files/pnglite/0.1.17/
