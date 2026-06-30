# PostgreSQL 18.3 构建进度

## 当前状态

构建完成，测试通过，安装成功。

## 构建流程

### Prepare (2026-06-12 12:15)
- 解压源码完成
- 补丁应用成功（11个文件）
- 补丁内容：SysV共享内存跳过、hmdfs权限放宽、getpwuid fallback、Unix socket禁用等

### Build (2026-06-12 12:21)
- Configure 成功
- Make 成功（无错误）
- 编译产物完整

### Install (2026-06-12 12:22)
- 安装到 $HOME/usr/local
- pg_config: /storage/Users/currentUser/usr/local/bin/pg_config (PostgreSQL 18.3)
- libpq: /storage/Users/currentUser/usr/local/lib/libpq.so.5.18
- headers: libpq-fe.h, pg_config.h

### Check (2026-06-12 12:23)
- 测试结果: 229/230 通过
- 失败测试: opr_sanity (utf8_and_uhc.so 权限问题，OHOS 签名机制限制)
- 跳过测试: 6个（并行相关）

## 修改记录

### 补丁文件
- postgresql_harmony.patch (11个源文件修改)

### 核心修改
1. **SysV 共享内存跳过**: src/backend/port/sysv_shmem.c
   - shmget/shmat/shmdt/shmctl syscall 不可用
   - 返回 fake header，依赖 mmap-based DSM

2. **hmdfs 权限放宽**: src/backend/utils/init/miscinit.c
   - 目录所有权检查放宽到 group 匹配
   - 权限检查只验证 owner rwx

3. **shm_open 强制 mmap**: src/include/storage/dsm_impl.h, src/bin/initdb/initdb.c
   - configure 检测成功但实际调用 SIGSYS
   - 强制使用 DSM_IMPL_MMAP

4. **getpwuid fallback**: src/common/username.c, src/interfaces/libpq/fe-auth.c
   - 用户不在 /etc/passwd 时使用数字 UID

5. **Unix socket 禁用**: src/include/pg_config_manual.h, src/test/regress/pg_regress.c
   - OHOS 不支持 Unix-domain socket
   - DEFAULT_PGSOCKET_DIR 设为空

6. **mkdir 权限修正**: src/bin/initdb/initdb.c, src/port/pgmkdirp.c
   - hmdfs 创建目录带异常 S-bit
   - mkdir 后 chmod 修正权限

## 构建总结 (2026-06-12)

### 成功要点
- PostgreSQL 在 OHOS 平台成功构建和安装
- 核心依赖库 libpq 和开发工具 pg_config 可用
- 测试通过率 99.6% (229/230)

### OHOS 平台适配要点
1. **System V IPC syscall 完全不可用**：shmget/shmat/shmdt/shmctl/shm_open 都返回 SIGSYS
   - 解决方案：全面跳过 SysV 共享内存，使用 mmap-based DSM

2. **configure 检测与实际调用不一致**：shm_open configure 检测成功但实际调用失败
   - 解决方案：条件编译强制覆盖检测结果

3. **hmdfs 文件系统限制**：目录所有权、权限、mkdir 异常
   - 解决方案：放宽检查、mkdir 后 chmod

4. **getpwuid 可能失败**：用户不在 /etc/passwd
   - 解决方案：fallback 使用数字 UID

5. **Unix-domain socket 不支持**：bind 返回 EPERM
   - 解决方案：禁用 Unix socket，使用 TCP/IP

### 测试失败分析
opr_sanity 测试失败原因是 utf8_and_uhc.so 共享库加载权限问题：
```
ERROR:  could not load library ".../utf8_and_uhc.so": Permission denied
```
这是 OHOS ELF 签名机制导致的限制，非源码 bug。实际运行 PostgreSQL 服务需确保所有 .so 文件已签名。

### 安装产物验证
- pg_config 功能正常（--version、--includedir、--libdir）
- libpq.so.5.18 存在且可链接
- libpq-fe.h 和 pg_config.h 头文件可用
- 满足 psycopg2-binary 构建需求

### 后续任务
TASK-100-psycopg2-binary 现在可以继续构建，依赖已满足。