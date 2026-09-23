# PostgreSQL — 开源对象-关系数据库系统

PostgreSQL 是功能强大的开源对象-关系数据库管理系统（ORDBMS），历经 30 余年活跃开发，以可靠性、数据完整性和正确性著称。本归档将其完整发行版（服务端 + 客户端工具 + libpq 客户端库）适配到 HarmonyOS PC（arm64）平台。

## 功能概述

- **服务端**：postgres（数据库服务器）、initdb（初始化数据目录）、pg_ctl（服务控制）、pg_controldata、pg_resetwal、pg_combinebackup、pg_createsubscriber 等
- **客户端工具**：psql（命令行客户端）、pg_dump / pg_dumpall / pg_restore（备份恢复）、pg_basebackup、pg_receivewal、pg_upgrade、pgbench（基准测试）等 35 个可执行文件
- **客户端库**：libpq（C API，psycopg2 等驱动的底层依赖）、libecpg（嵌入式 SQL）、libpgtypes、libecpg_compat
- **服务端编程接口**：libpq-fe.h / libpq-events.h（客户端）、src/include/postgresql/internal（服务端内部头文件）、pgxs 扩展构建系统

## OHOS 适配要点

本包通过 `18.3/patches/0001-ohos-platform-adaptation.patch`（11 个源文件，`__OHOS__` 守卫）完成平台适配：

1. **SysV 共享内存不可用**：shmget/shmat/shmdt/shmctl syscall 均返回 SIGSYS（未实现）→ 跳过 SysV 段创建，依赖 mmap-based DSM
2. **shm_open 检测与实际行为不一致**：configure 探测成功但实际调用触发 SIGSYS → 条件编译强制 DSM_IMPL_MMAP
3. **hmdfs 文件系统限制**：目录所有权检查放宽到 group 匹配；权限检查仅验证 owner rwx；mkdir 产生的异常 S-bit 通过后续 chmod 修正
4. **getpwuid 失败 fallback**：用户不在 /etc/passwd 时回退使用数字 UID
5. **Unix-domain socket 不支持**（bind 返回 EPERM）→ DEFAULT_PGSOCKET_DIR 置空，仅使用 TCP/IP 连接
6. **configure umask 077 修复**：hmdfs 上 autoconf 临时目录不可写 → sed 替换为 umask 022
7. **install shim 兼容**：PATH 首位的本机 install 包装脚本不支持分离参数形式（`install -c -m 755 src dst`）→ 安装阶段使用 PG 自带 config/install-sh（`make install use_install_sh=yes`）
8. **平台构建声明**：显式 `--build=aarch64-linux-ohos`（PG 18.3 自带 config.sub 已支持该 triplet），跳过无法识别 OHOS 的 config.guess

## 依赖关系

### 编译依赖
- 无（历史验证过的最小配置：`--without-icu --without-readline --without-zlib --without-openssl`，零外部 Conan 依赖）

### 运行时
- libc.so（系统 musl libc）
- OHOS ELF 签名机制下，服务端加载扩展 .so（如 utf8_and_uhc.so）需要签名（已知平台限制，见版本级 notes.md）

## 参考资料

- 官网：https://www.postgresql.org
- 源码：https://ftp.postgresql.org/pub/source/v18.3/postgresql-18.3.tar.bz2
- 许可证：PostgreSQL Licence（类 BSD/MIT，见包内 licenses/COPYRIGHT）
- 手动构建历史：版本目录 build.sh / notes.md（2026-06-12，commit 149f3b650）
