# packaging — libeio 1.0

v3.0 Conan 配方模式（R19/R20）：产物即 `conan create` 生成的 Conan 包
（libeio/1.0@ohpcd/stable，ohos-aarch64 profile），经 CI release 流水线
`conan upload` 发布到 ohpcd 制品仓，不再手动维护 tar.gz 制品入库。

本目录在适配机上另保有打包验证产物（不入库，根 .gitignore 排除 *.tar.gz）：
`packaging/libeio-1.0-ohos-aarch64.tar.gz`（含 libeio.so.1.0.0 / libeio.a /
eio.h 头文件）与 -debug 符号包，用于本机分发验证；包内容与测试证据见
../reports/test-report.md。

产物清单（make install 相对 $DEFAULT_PREFIX）：

| 文件 | 说明 |
|------|------|
| include/eio.h | 公开头文件 |
| lib/libeio.so.1.0.0 (+ .so.1 / .so 符号链接) | 动态库 |
| lib/libeio.a | 静态库 |
| lib/libeio.la | libtool 元数据 |

链接标志：`-leio`。