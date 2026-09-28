# libconfigini

INI 格式配置文件解析库（纯 C 实现）。

- 上游仓库: https://github.com/taneryilmaz/libconfigini
- 版本: 22d700ab76 (commit 22d700ab76a9d6dd9492da244a7fddc6970c7809, 2016-07-16)
- 许可证: BSD-3-Clause
- 构建系统: 纯 Makefile（无 configure 脚本）

## 适配要点

- 无第三方依赖，仅 libc（stdio/stdlib/string/ctype/errno）+ sys/cdefs.h。
- 配方（archives/l/libconfigini/22d700ab76/conanfile.py）使用 Conan Makefile 驱动：
  补丁 0001 将上游 Makefile 的 `CC = gcc` 改为 `CC ?=`、`CFLAGS =` 改为 `CFLAGS ?=`，
  并让归档步骤使用 `$(AR)`，使 OHOS clang/llvm-ar 工具链生效（R33）。
- 上游测试入口: `make test`（tests/test.c，Test1~Test4 共 4 个用户测试函数，
  构建为单个 test 可执行并实际运行）。
- 鸿蒙专项测试与消费者测试见 test_package/（test.c + test_ohos.c）。
