# libgzstream 1.5-git20171107.9a20658 — HarmonyOS PC 编译记录

## 基本信息

- 软件：libgzstream
- 版本：1.5-git20171107.9a20658
- 构建系统：Makefile（配方使用等价的直接编译流程）
- 目标平台：HarmonyOS PC / OHOS aarch64
- 依赖：zlib/1.3.1

## 适配说明

libgzstream 是基于 zlib 的 C++ iostream 封装。上游源码根目录包含名为
`version` 的无扩展名文件；如果沿用 Makefile 的 `-I.`，新版 libc++ 包含标准头
`<version>` 时会误命中该文件。配方使用 `-idirafter <source>` 保留上游
`#include <gzstream.h>` 的解析能力，同时确保标准库头优先。

构建产物保持上游静态库形态：`lib/libgzstream.a`、`include/gzstream.h` 和
LGPL-2.1-or-later 许可证文本。上游 2 项 gzip 互操作测试及新增 1 项 HarmonyOS
消费者测试均由 `conan create` 实际执行。
