# PostgreSQL 16.10 — 适配笔记（OHOS PC aarch64）

## 当前状态

构建完成，上游测试通过（regress 216/217、isolation 116/116、ecpg 64/64），
消费者用例真实运行通过，配方验证通过（conan build / export-pkg / test_package）。

## 任务与分支

- task_id: postgresql-16.10-r01-pc1-33-20260916T064737Z
- worktree: /storage/Users/currentUser/junshi_liu/worktrees/postgresql-16.10
- branch: feat/postgresql-16.10（自 origin/main 6cd6193fda 创建，唯一专用 worktree）
- 官方源码: https://ftp.postgresql.org/pub/source/v16.10/postgresql-16.10.tar.bz2
- sha256: de8485f4ce9c32e3ddfeef0b7c261eed1cecb54c9bcd170e437ff454cb292b42（与官方 .sha256 交叉验证一致）

## 与 18.3 配方的继承与偏离（W0b 记录）

继承 18.3（archives/p/postgresql/18.3）已验证结论：`--build=aarch64-linux-ohos`
原生构建、`--without-icu/readline/zlib/openssl` 零外部依赖、`make install
use_install_sh=yes`、configure 后改写 `src/Makefile.global` 注入
`LDFLAGS_EX = -Wl,-rpath,'$$ORIGIN/../lib'`、`tc.extra_defines`（非只读 defines）
注入语义能力宏。

16.10 的偏离点（补丁 14 文件，git diff 从 18.3 语义重生成并针对 16.10 源码重写）：

1. **config.sub 缺 ohos 识别（16.10 独有，18.3 自带支持）**：16.10 内置 config.sub
   不识别 aarch64-linux-ohos → 补丁内给 `config/config.sub` 三处列表加
   `ohos*`/`linux-ohos*`（gnu|android 表、zephyr 尾部表、linux-ohos 内核-OS 组合表）。
   验证：`./config/config.sub aarch64-linux-ohos` → `aarch64-unknown-linux-ohos`。
2. **umask 077→022 内嵌补丁（18.3 是配方 build() 动态 replace）**：16.10 因
   config.sub 也必须改，autoconf 脚本修复统一内嵌补丁（configure + config.guess），
   配方 build() 不再重复 replace（避免找不到旧串报错）。根因：config.status 内
   `(umask 077 && mktemp -d "./confXXXXXX")` 在 hmdfs 上建 `drwx--S---` 目录
   （chmod 无效，E046），`subs1.awk` 写入 Permission denied（E011/E052/E060 同族）。
3. **HAVE_BROKEN_SHMGET 守卫补全（本次新增，18.3 补丁亦含但首版 16.10 重写遗漏）**：
   除 IpcMemoryDetach/IpcMemoryDelete 外，还必须守卫 `InternalIpcMemoryCreate`
   （返回 static fake header）、`PGSharedMemoryAttach`（SHMSTATE_ENOENT）、
   `PGSharedMemoryIsInUse`（false）。根因：OHOS 上 shmget 实测返回 **EACCES
   (errno=13)** 而非 SIGSYS——PG16 `PGSharedMemoryCreate` 的 `for(;;)` 探测循环把
   EACCES 归类 SHMSTATE_FOREIGN 后递增 key 无限重试，`postgres --check`/initdb
   85% CPU 自旋无日志。缺守卫时服务器完全无法启动（消费者用例因此卡住）。
4. **HAVE_BROKEN_FALLOCATE（16.10 新发现，E523 同根因的数据库层解法）**：
   hmdfs 上 `posix_fallocate` 返回 EACCES，PG16 `FileFallocate` 只对
   EINVAL/EOPNOTSUPP 回退 FileZero → 48 个 regress 测试首轮失败。补丁把
   EACCES/EPERM 加入回退集合 → 216/217。
5. **getpwuid fallback 位置变化（16.10 特有）**：18.3 补丁改 fe-auth.c；16.10 的
   libpq 客户端路径使用 `pg_get_user_name()`（src/port/thread.c），守卫加在该函数
   （username.c 的 get_user_name 同样守卫）。

## 构建流程（手动复验，与配方一致）

```bash
export TMPDIR=$HOME/tmp; umask 022
../postgresql-16.10/configure --prefix=$HOME/usr/local/pg1610 \
  --without-icu --without-readline --without-zlib --without-openssl \
  --build=aarch64-linux-ohos \
  CPPFLAGS="-DHAVE_BROKEN_SHMGET -DHAVE_BROKEN_SHM_OPEN -DHAVE_BROKEN_GETPWUID -DHAVE_BROKEN_UMASK -DHAVE_NO_UNIX_SOCKETS -DHAVE_BROKEN_FALLOCATE -D_GNU_SOURCE"
make -j8 && make install use_install_sh=yes
```

配方（conanfile.py）经 `tc.extra_defines` 注入同一宏集（仅 OHOS），Linux 下守卫代码编译剔除（R8 语义宏）。

## 验证结果

- conan build / export-pkg：PASS（二进制 d3c23669… 注册缓存）
- test_package：PASS（PQlibVersion()=160010 major=16 断言 + pg_config --version = PostgreSQL 16.10）
- 消费者用例 reports/consumer/consumer_pg.c：仅公开 libpq API 编译链接，连接真实
  postgres 服务（initdb + pg_ctl + TCP 127.0.0.1:55432）执行 `SELECT 1,'harmonyos'`
  并核验结果，exit 0（编译/链接/调用/运行全链真实）
- 上游测试：regress 216/217（唯一失败 opr_sanity = OHOS ELF 签名阻止 .so 加载，
  已知平台限制，同 18.3 基线）、isolation 116/116、ecpg 64/64；TAP 103 未实例化
  （配方未启用 --enable-tap-tests，恢复条件见 reports/test-report.md §5）
- 双口径：全量 396/472 (83.9%)；当前配置可执行集合 396/397 (99.7%)

## 依赖说明

无 conan 依赖：configure 显式 --without-icu/readline/zlib/openssl，tzdata 内嵌源码树发布，
manifest dependencies 为空列表（与 18.3 修正后一致）。

## 知识候选（路径 B）

reports/knowledge-candidate-ledger.md：C1（config.sub ohos 移植+umask 内嵌）、
C2（shmget EACCES 自旋+守卫跳过）、C3（fallocate EACCES 回退 FileZero）三个候选
均为部分覆盖+新增差异 → new_draft，草稿对落 knowledge/drafts/：
DRAFT-postgresql-config-sub-ohos-triplet、DRAFT-postgresql-sysv-shmget-eacces-spin、
DRAFT-postgresql-fallocate-eacces-filezero（.md/.kv 各一）。

---

**编译结束**: 2026-09-16 ｜ **最终状态**: built
