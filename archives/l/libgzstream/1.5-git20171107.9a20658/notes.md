# libgzstream 1.5-git20171107.9a20658 适配笔记

## 上游与版本

- 上游仓库：`https://github.com/kanedo/gzstream`
- 固定提交：`9a20658673492c41fd9726d439cdea7f96235e84`
- 源码 SHA-256：`148eecd6a372269ef58525349c775f0fe7e03be39e462bc576053fa771eb221f`
- 上游 `version` 文件声明基础版本为 1.5；归档版本附加 Git 日期及短提交号。
- 许可证：LGPL-2.1-or-later。

## 依赖预检

唯一库依赖为 `zlib/1.3.1`。已通过 `conan download --only-recipe` 和
OHOS aarch64 profile 的 `conan install --build=never` 验证制品仓配方及二进制可用。

## 上游测试清点（R51）

固定提交没有 `tests/` 子目录或第三方测试框架。顶层 Makefile 的 `test` 目标注册并
实际执行 2 个端到端互操作用例：

1. `test_gzip` 使用 `ogzstream` 压缩 `COPYING.LIB`，再由标准 `gunzip` 解压并与原文比对。
2. 标准 `gzip` 压缩同一文件，`test_gunzip` 使用 `igzstream` 解压并与原文比对。

主机原始 `make test` 实测 2/2 通过。移植配方编译同一份上游测试源并执行等价命令，
没有修改上游测试源码、断言或通过条件；OHOS aarch64 执行结果为 2/2 通过。

## HarmonyOS 适配

上游 Makefile 使用 `CPPFLAGS=-I. -O`。源码根目录同时存在无扩展名文件 `version`；
libc++ 的标准头包含 `<version>` 时，`-I.` 会优先选中上游文本文件并导致语法错误。
配方不修改上游源码，而是将源码目录作为 `-idirafter` 搜索路径：标准库头优先解析，
上游的 `#include <gzstream.h>` 仍可正常命中。

上游只构建 `libgzstream.a`，配方保持静态产物。`gzstream.h` 公开包含 `zlib.h`，所以
Conan 依赖声明启用 zlib 头文件和库的传递。

## 测试结果

- 上游测试：2/2 通过。
- 新增 HarmonyOS 特有消费者测试：1/1 通过，共 5 个真实断言。
- 总用例：3/3 通过；无跳过、无豁免、无上游测试修改。

新增测试由 `test_package/test_libgzstream.cpp` 提供，在 OHOS 编译期校验 `__OHOS__`，
并从已安装 Conan 包链接 `libgzstream.a` 与 zlib，运行时验证输出流、gzip 魔数、输入流、
二进制内容和文件生命周期。

## 交付物

- `include/gzstream.h`
- `lib/libgzstream.a`
- `licenses/COPYING.LIB`

本软件仅交付库和头文件，不包含命令行工具，因此不需要软件级 `commands.json`。
---

**编译结束**: 2026-09-15 01:55
**最终状态**: built
