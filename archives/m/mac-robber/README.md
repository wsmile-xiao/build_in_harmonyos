# mac-robber — OpenHarmony 编译档案

## 软件简介
mac-robber 是数字取证工具，从已挂载文件系统的已分配文件中收集元数据（Modified/Access/Change 时间），输出 'time machine' (body file) 格式到 STDOUT，供 The Sleuth Kit 的 mactime 工具生成文件活动时间线。

## OHOS 适配要点
- 单文件 C 程序（369 行），仅依赖 POSIX 标准库（sys/stat.h, dirent.h, unistd.h），无任何 Linux/BSD 专有字段或 API
- Makefile 硬编码 CC=gcc 和 -static，但提供 linux_notstatic 目标（非静态 + -D_FILE_OFFSET_BITS=64）；CC 可命令行覆盖，无需 Makefile 补丁
- 唯一 musl 兼容缺口：MAXNAMLEN 宏（BSD/glibc 扩展，musl 未定义），用 1 个 3 行源码补丁 fallback 为 256

## 依赖关系
- 无运行时依赖（仅 POSIX 标准库）
- 编译器从 Conan conf `tools.build:compiler_executables` 动态获取（OHOS clang）

## 上游测试
- 上游正式测试为 0（无 tests/ 目录、无 check/test Makefile 目标、无 TESTS/check_PROGRAMS）
- 详见 test_package/MANIFEST.yml 的完整审计

## 参考资料
- [mac-robber 官方主页](https://sleuthkit.org/mac-robber/)
- [mac-robber SourceForge](https://sourceforge.net/projects/mac-robber/)
- [mac-robber GitHub (作者迁移的 autotools 版)](https://github.com/sleuthkit/mac-robber)
