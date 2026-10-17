# librtpi

Real-Time Priority Inheritance Library。在 pthread 之上提供功能正确的
优先级继承（PI）互斥锁与条件变量：与 glibc pthread 相比，librtpi 保证
**基于优先级的唤醒顺序**（而非 glibc condvar 的时间有序唤醒组），面向
实时（RT）应用。实现方式为直接使用 Linux PI futex 系统调用
（`FUTEX_LOCK_PI`/`FUTEX_UNLOCK_PI`/`FUTEX_WAIT_REQUEUE_PI`/
`FUTEX_CMP_REQUEUE_PI`）自行实现 PI，不依赖 libc 的 pthread PI mutex，
因此 musl 平台同样可编译。

- 上游主库：<https://gitlab.com/linux-rt/librtpi>（备份镜像
  github.com/linux-rt/librtpi）
- 许可证：LGPL-2.1-only
- 语言：C（含 C++ 绑定头 `rtpi/mutex.hpp`、`rtpi/condition_variable.hpp`）
- 交付物：`librtpi.a` / `librtpi.so.1` + 4 个头文件（纯库，无命令行工具）

## OHOS 适配要点

- 上游为 autotools 构建（tarball 仅含 `configure.ac`），OHOS 真机/CI 镜像
  无 autoconf/automake/libtool，配方用导出的最小 CMakeLists.txt 包装构建。
- OHOS musl libc 无 pthread 取消族符号（E127），配方在 OHOS 上强制上游的
  `--disable-cancellation` 配置（glibc-tests 有对应分支）。
- 功能依赖目标内核实现 PI futex 系统调用；test_package 阶段 2/3 为运行时
  探针（失败打印 errno，如 ENOSYS = 内核未实现）。

## 版本

| 版本 | 状态 | 备注 |
|------|------|------|
| 1.0.0 | built | 真机实测通过（2026-09-19）；mutex PI API 可用，condvar API 因 HongMeng 内核未实现 PI 重排队 futex 运行期返回 ENOSYS |
