# tgt — Linux SCSI target framework

- 名称：tgt
- 版本：1.0.85
- 上游：<https://github.com/fujita/tgt>
- 许可证：GPL-2.0-only
- 构建系统：纯递归 Makefile（无 configure / autotools / cmake）
- 类型：命令行工具（`tgtd`、`tgtadm`、`tgtimg`，另含 `tgt-admin`、`tgt-setup-lun` 脚本）

## 说明

tgt（Linux target framework）让 Linux 系统通过网络 SCSI 传输对外提供 SCSI 设备：

- iSCSI（SCSI over IP）
- iSER（iSCSI over RDMA，需 `ISCSI_RDMA=1`）

支持的后端存储包括普通文件、块设备、Ceph/RBD（`CEPH_RBD=1`）与 GlusterFS（`GLFS_BD=1`）。
本适配使用上游默认特性开关，只启用纯用户态的 iSCSI + 文件/块设备后端。

## 安装产物

| 文件 | 说明 |
|------|------|
| `bin/tgtd` | iSCSI/SMC 目标端守护进程 |
| `bin/tgtadm` | 目标/LUN/ACL 管理工具（通过 unix socket 与 tgtd 通信） |
| `bin/tgtimg` | 磁带/光盘镜像文件工具 |
| `bin/tgt-admin` | Perl 配置驱动脚本（需 Config::General） |
| `bin/tgt-setup-lun` | LUN 快速配置脚本 |

## HarmonyOS PC 适配要点

1. **构建范围**：只构建 `usr`（C 程序）与 `scripts` 两个子树。`doc` 需要 xsltproc + docbook XSL，
   `conf` 安装到 `/etc`，都不纳入 Conan 包布局。
2. **`__WORDSIZE`**：glibc 专有宏，musl 未定义。`util.h` 的 `BITS_PER_LONG` 与 `tgtd.h` 的数组
   长度改为 `(8 * sizeof(unsigned long))`。
3. **`pthread_cancel`**：musl 系 C 库不提供。`bs_thread` 的线程关闭改为协作式——
   `struct bs_thread_info` 增加 `stop` 字段，关闭时置位 + `pthread_cond_broadcast` + `pthread_join`，
   工作线程排空队列后自行退出（语义上比中途取消更安全）。
4. **`open_memstream` 时序（关键崩溃）**：POSIX 规定 memstream 的缓冲区指针与长度只在 `fflush`/
   `fclose` 后发布。musl 严格遵守，`tgtadm` 在 flush 前读到的 `b->size` 恒为 0，于是
   `req->len = sizeof(*req) + 0`，请求体为空；`tgtd` 侧 `mtask->req_buf` 为 NULL，
   `tgt_target_create()` 在校验字符前解引用 `targetname` 直接 SIGSEGV。
   修复：`concat_buf_finish()` 显式 `fflush`，`ipc_mgmt_req()` 先 finish 再取长度，
   并在 `tgt_target_create()` 中把空指针判断提到字符校验之前。
5. **clang 告警**：`.c` 中未使用的 `static inline`（`bs_sheepdog.c`）在 clang 下告警、
   gcc 不告警；上游开启了 `-Werror`，故补 `-Wno-unused-function`。
6. **`execute_work()`** 补 `void` 原型以满足 `-Wstrict-prototypes`。

## 依赖

默认特性开关下无第三方 Conan 依赖：仅需要 libc、`libpthread`、`libdl`。
`libaio` 后端因 OHOS sysroot 无 `<libaio.h>` 被上游 Makefile 自动跳过。

## 测试

上游唯一的自动化测试入口是 `scripts/tgt-core-test`（bash 脚本），它硬编码 `HOME=/d/01`、
依赖 `ps -ef` 自动拉起 tgtd、默认使用 `/var/run/tgtd/socket`，在 OHOS 上均不可用。
`test_package/ohos_specific_test.sh` 将其移植为鸿蒙消费者用例（私有 IPC socket、
显式起停 tgtd、工作目录可指定），34 项断言全部真实执行。

详见 `1.0.85/notes.md` 与 `1.0.85/test_package/MANIFEST.yml`。
