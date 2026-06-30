# audit — Linux Audit Framework (Userspace)

## 简介

Linux Audit System 的用户空间工具和库，提供系统审计能力，包括审计规则管理、日志收集、日志搜索和报告生成。

## 功能概述

- **auditctl**: 管理审计规则（添加、删除、列出）
- **auditd**: 审计守护进程，负责收集和记录审计事件
- **aureport**: 生成审计摘要报告
- **ausearch**: 搜索审计日志
- **augenrules**: 加载审计规则文件
- **aulast / aulastlog**: 基于审计日志的登录记录查看
- **ausyscall**: 系统调用名称与编号转换
- **libaudit**: 审计库，提供与内核审计子系统通信的 API
- **libauparse**: 审计日志解析库
- **audispd-***: 审计事件分发器插件

## OHOS 适配

### 平台信息
- 目标平台: HarmonyOS, HongMeng Kernel 1.12.0, aarch64
- Triplet: aarch64-unknown-linux-ohos
- 编译器: clang (内置 __OHOS__ 宏)

### 适配要点
1. **utmpx 不可用**: OHOS 不提供 utmpx 系列函数（setutxent, getutxent 等），但提供 utmp 系列。需用 `#define` 将 utmpx 函数映射到 utmp 函数。
2. **secure_getenv 不可用**: OHOS 不实现 secure_getenv()，需提供 fallback 实现（直接调用 getenv）。
3. **pthread_cancel 不可用**: OHOS 的 bionic libc 不实现 pthread_cancel()，需用 pthread_kill(t, 0) 作为 no-op 替代（flush 线程在 shutdown 时会自行退出）。
4. **sockaddr_storage 重定义**: linux/socket.h 与 sys/socket.h 冲突导致 sockaddr_storage 重定义，需在 __OHOS__ 下定义 _UAPI_LINUX_SOCKET_H 防止冲突。
5. **config.guess 识别**: 需修改 config.guess 添加 HarmonyOS 到 UNAME_SYSTEM 和 aarch64 case。
6. **umask 077 问题**: configure 脚本中 mktemp -d 配合 umask 077 会创建不可写目录，需去除。
7. **--without-go 不被识别**: configure 不识别 --without-go 选项，但可忽略（不影响编译）。

### 已知限制
- auditctl/auditd 需要 root 权限和 audit netlink socket 支持，在非 root 环境下无法运行
- augenrules 使用 /tmp 作为临时目录，OHOS 的 /tmp 为只读文件系统，需设置 TMPDIR 环境变量
- make check 中的 lookup_test 在 aarch64 平台上会失败（i386 系统调用表测试不适用于该架构）

## 依赖关系

- 编译依赖: autotools (autoconf, automake, libtool), gcc/clang
- 运行依赖: 无外部库依赖（使用标准 libc）

## 参考资料

- 官网: https://github.com/linux-audit/audit-userspace
- 文档: https://people.redhat.com/sgrubb/audit/
