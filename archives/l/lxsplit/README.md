# lxsplit

lxSplit 是一个命令行文件分割/合并工具，可将大文件按指定大小分割成多个片段（无压缩），并能将分割后的片段合并恢复为原始文件。它与 HJSplit 完全兼容。

## 功能概述

- **分割**: `lxsplit -s <file> <size>` 按指定大小分割文件
- **合并**: `lxsplit -j <file>.001` 合并分割片段为原始文件
- 支持大文件（>= 4GB，LFS）
- 大小单位支持 M（兆字节）、k（千字节）、b（字节）

## OHOS 适配要点

- **构建系统**: 简单 GNU Makefile（非 autotools），无 configure 脚本
- **编译器**: OHOS clang（通过 Conan profile `tools.build:compiler_executables` 提供）
- **补丁**: 零补丁，上游 Makefile 接受 `CC=` 覆盖，OHOS clang 直接可用
- **交叉编译**: 上游 Makefile 注释称不适合交叉编译（编译期运行 `mkuoff_t` 生成 `uoff_t.h`），但 OHOS build=host=aarch64，helper 原生运行，无问题
- **LFS**: Makefile 已内置 `-D_LARGEFILE_SOURCE -D_LARGEFILE64_SOURCE -D_FILE_OFFSET_BITS=64`
- **许可证**: GPL-2.0-or-later
- **测试**: 上游无 make check 目标，功能验证在 test_package 中通过 split→join→cmp 端到端测试完成

## 依赖关系

- **编译依赖**: 无（纯 C 程序，仅依赖系统 musl libc）
- **运行依赖**: musl libc（系统自带）

## 源码结构

| 文件 | 说明 |
|------|------|
| main.c | 主程序入口、参数解析、帮助输出 |
| split.c | 文件分割逻辑 |
| merge.c | 文件合并逻辑 |
| func.c | 路径处理等辅助函数 |
| mkuoff_t.c | 编译期 helper，生成 uoff_t.h（探测 off_t/long 大小） |
| config.h | 版本宏、LFS 配置、类型定义 |

## 参考资料

- 官方主页: https://lxsplit.sourceforge.net/
- 源码下载: https://downloads.sourceforge.net/project/lxsplit/lxsplit/0.2.4/lxsplit-0.2.4.tar.gz
- 许可证: GNU GPL v2 或更高版本
