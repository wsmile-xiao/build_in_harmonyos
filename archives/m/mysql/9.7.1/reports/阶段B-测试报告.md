# MySQL 9.7.1 OHOS 适配 —— 阶段B测试报告

> **更新（2026-09-15）**：本报告第 3、4 节"mysqld 生命周期无法完成"的结论已被推翻。
> 根因（HMDFS 文件名/目录大小写折叠 + 沙箱 fallocate / unix-socket 限制）已由 PR 补丁 0068
> （`patches/0068-ohos-runtime-sandbox-fixes.patch`）修复：`mysqld --initialize-insecure →
> 启动 → mysqladmin ping → shutdown` 全流程在 OHOS 上一次通过，上游
> `testclients/mysql_client_test`（315 项）真实执行 307 通过。
> 详见 `reports/上游测试-testclients执行报告.md`。

日期：2026-09-10
目标：mysqld + client 工具（mysql/mysqladmin/mysqldump）功能验证

## 一、构建验证（conan create）

- `conan create archives/m/mysql/9.7.1 -pr:h=default -pr:b=default --build=missing`
  - profile: OHOS armv8 clang15（签名与 mysql-client/9.7.1 完全一致）
  - 依赖：openssl/3.5.6.1.1、zlib/1.3.1、ncurses/6.4（本地缓存，`Already installed`）
  - 结果：主包 build + package 成功
    - `bin/mysqld`（约210MB）
    - `bin/mysql`、`bin/mysqladmin`、`bin/mysqldump`、`bin/comp_err` 等全部安装
    - `lib/libmysqlclient.a`、`lib/libmysqlservices.a`
    - `include/mysql.h` 等头文件
- 失败记录：首次 create 因 `cmake.configure` 缺 try_run 缓存（HAVE_FALLOC_PUNCH_HOLE_AND_KEEP_SIZE/HAVE___BUILTIN_FFS 未配）失败 → conanfile.py 补齐后通过。随后发现 test_package 引用 `mysql::mysql` 但 server 版 recipe `package_info` 未暴露 `libs`，导致 CMakeDeps 生成的目标无 include/lib 路径；已按 client 版补全 `cpp_info.libs`、`requires`、`system_libs`。

## 二、client 库 69 用例回归（test_package 同步自 mysql-client/9.7.1）

- 使用已安装 package 的 `lib/libmysqlclient.a` + openssl/zlib/ncurses 静态库直接链接，无服务器运行依赖。
- 结果：**69/69 全部通过，退出码 0**（详见 `test-package-output.txt`）。

## 三、mysqld 生命周期测试（OHOS 运行时限制，如实记录）

执行序列：`mysqld --initialize-insecure` → 后台启动 → `mysqladmin ping` → `mysqladmin shutdown`

| 步骤 | 结果 | 说明 |
|------|------|------|
| mysqld --initialize-insecure | 退出码 0 | datadir 初始化成功（undo_001/002、mysql.ibd、ibdata1 均生成） |
| mysqld 正常启动 | 失败 | InnoDB 启动 `create UNDO` 判断异常（见下） |
| mysqladmin ping / shutdown | 无法执行 | 依赖上一步启动成功 |

### 启动失败原因（已定位到 InnoDB 层）

1. **OHOS seccomp 拦截 fallocate syscall（EPERM, errno 13）**。
   - 初始化日志中大量：
     `[ERROR] [MY-012144] [InnoDB] posix_fallocate(): Failed to preallocate data for file ... error number 13`
     `[Warning] [MY-012579] fallocate(...FALLOC_FL_PUNCH_HOLE...) returned errno: 13`
   - 尝试 `--innodb-extend-and-initialize=OFF` 无法消除（undo/mysql.ibd 创建路径不受该变量控制）。
   - fallocate 落下 EPERM 导致 InnoDB DD（mysql.ibd）内部 undo 表空间注册不完整；正常启动时 `srv_undo_tablespaces_open()` 无法在 fil 系统中找到已存在的 undo_001/002，转入 `srv_undo_tablespaces_create()`，与磁盘文件冲突：
     `[ERROR] [MY-013039] [InnoDB] Can't create UNDO tablespace innodb_undo_00X since './undo_00X' already exists.`

2. **OHOS 沙箱禁止 unix socket bind（EPERM）**。
   - 使用 `--innodb-force-recovery=6` 绕过 InnoDB 启动问题后，服务推进到 socket 阶段，但：
     `[ERROR] [MY-010270] [Server] Can't start server : Bind on unix socket: Operation not permitted`
   - 尝试不同 socket 路径（builds / 用户目录）均相同；改用 TCP+`--skip-socket` 时服务端仍尝试绑定 socket 后中止。

结论：mysqld 二进制本身可启动、可执行（`mysqld --version` OK、datadir 初始化成功、InnoDB 逻辑可推进到 bind 阶段），但 OHOS 运行环境（seccomp fallocate/socket 限制）使"完整生命周期测试"无法在本机完成。这是**运行时宿主限制**，非编译/链接缺陷。建议：在不受限的 Linux/OHOS 真机上完成该测试；或将本报告作为受限记录提交。

## 四、阶段B 结论

- 编译、打包、client 库回归：通过（69/69）。
- mysqld 生命周期：受 OHOS seccomp 限制阻塞，已定位根因并记录证据。