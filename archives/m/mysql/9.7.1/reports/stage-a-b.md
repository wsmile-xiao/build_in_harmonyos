# MySQL 9.7.1 HarmonyOS PC 阶段A/B 证据

## 阶段A：源码编译

- 分支：`feat/mysql-9.7.1`
- 构建树：`$HOME/tmp/builds/mysql-9.7.1.build-server`
- 配置：OHOS/aarch64，clang 15，`WITHOUT_SERVER=OFF`，`WITH_ROUTER=OFF`，`WITH_NDB=OFF`，`WITH_GROUP_REPLICATION=OFF`
- make 命令：`make -j4`
- 最终结果：成功，日志 `server-make-r15.log`
- 关键产物：
  - `runtime_output_directory/mysqld`：链接成功，约 210 MB
  - `runtime_output_directory/mysql`
  - `runtime_output_directory/mysqladmin`
  - `runtime_output_directory/mysqldump`
- 补丁：0001-0067；干净 tar 树按 `conandata.yml` 顺序应用后与 `.work` 树 diff 为 0。
  - **2026-09-15 追加**：服务端运行期补丁 0068（`fil0fil.cc`）、0069（`my_fallocator.cc`）、
    0070（`socket_connection.cc`）；三者均在干净 `.orig` 基线上验证可干净应用、应用结果与参考树一致。

### 阶段A遇到并修复的问题

1. group_replication 的 `rpc/rpc.h` 在 OHOS sysroot 不存在，使用官方可选项 `WITH_GROUP_REPLICATION=OFF`。
2. `gen_lex_hash`、`gen_lex_token`、`gen_keyword_list`、`protoc` 等宿主生成器不在 PATH，改为 target-file/能力探测路径。
3. OHOS libcxx 的 `<ranges>` 为裁剪 stub，替换服务端 `std::ranges`/`std::views` 用法。
4. clang 15 CRTP concepts 在不完整派生类上误判，按既有补丁手法对 `collection_interface.h`、`iterator_interface.h` 放宽 clang<17 约束。
5. OHOS 无 `pthread_setaffinity_np`/`SYS_gettid`，新增 capability probe，跳过 InnoDB 可选 CPU affinity/priority 优化。
6. OHOS libc++ 不支持 `stringstream::view()` 与聚合体 P0960 的 `construct_at` 路径，分别改用 `str()` 与显式构造函数。

## 阶段B：conan create

第一次 `conan create`：主包 cmake 配置失败，原因是 server 新增 try_run 缓存缺失：
- `HAVE_FALLOC_PUNCH_HOLE_AND_KEEP_SIZE_EXITCODE`
- `HAVE___BUILTIN_FFS_EXITCODE`

已补入配方。第二次 `conan create`：主包构建和 package 成功，package 目录包含 `bin/mysqld`、`bin/mysqladmin`、`bin/mysqldump`、`lib/libmysqlclient.a`、`include/mysql.h`；但 test_package 编译因原配方 `package_info()` 未声明 `cpp_info.libs` 而找不到 `mysql.h`，已修复 package_info 暴露 `mysqlclient`、include dirs、依赖和 system libs。

### 本地生命周期测试

使用 build-server 的可执行产物执行：

- `mysqld --initialize-insecure`：rc=0。
- 正常启动：失败。OHOS 文件系统对 InnoDB 的 `posix_fallocate()`/`fallocate()` 返回 errno 13（EPERM），日志出现 `MY-012144`、`MY-012579`；随后 InnoDB 未能打开已有隐式 undo 表空间，尝试创建 `undo_001`/`undo_002` 时报告 `MY-013039 ... already exists`。
- `--innodb-extend-and-initialize=OFF`：未解决。
- `--innodb-force-recovery=6`：可越过 undo 初始化，但 OHOS 对 Unix socket bind 返回 `MY-010270 Operation not permitted`；换用户目录仍相同。TCP 方式也未能启动，因为服务端仍尝试绑定 socket。
- 因此 `mysqladmin ping`/`shutdown` 尚未能取得全 0；该问题是运行时沙箱/文件系统能力阻塞，不是链接失败。

## 当前结论

阶段A 编译完成；阶段B 主包构建完成，但 test_package 的 69 用例和 mysqld 生命周期测试被上述两个 OHOS 运行时限制阻塞。未伪造通过率。
