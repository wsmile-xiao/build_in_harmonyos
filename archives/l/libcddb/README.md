# libcddb

CDDB 服务器访问库

- Version: 1.3.2
- License: LGPL-2.1+
- Homepage: https://sourceforge.net/projects/libcddb/

## 功能概述

libcddb 是一个 C library，用于访问 freedb.org CDDB 服务器。支持:
- Disc ID 计算（标准和扩展）
- CDDB 服务器查询（query/read/search/album/sites）
- 本地缓存管理
- 字符集转换（通过 iconv）
- 连接管理（CDDBP/HTTP/代理协议）

同时提供命令行工具 cddb_query，用于测试和调试。

## 编译状态

- ✅ 已在 OpenHarmony 平台编译成功
- 状态: published
- 构建系统: autotools
- 编译器: clang/clang++
- 质量门禁: G0-G4 全部通过
- API 功能测试: 12/12 通过
- make check: 2/5 通过（核心本地功能通过，网络相关测试因离线环境预期失败）
- 依赖: libiconv（打包中包含）
- **补丁: 2 个**（精简后，原 4 个；删除了 settings.sh 和 version.h 的生成文件 patch，违反 R6 铁律）

## 上游 Bug

- ⚠️ cddb_log.h header guard 拼写错误 (`CDDB_LOH_H` vs `CDDB_LOG_H`)，编译产生警告但不影响功能
