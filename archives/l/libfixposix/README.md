# libfixposix — POSIX 函数的薄封装库

libfixposix 提供 119 个 `lfp_*` API 覆盖 errno、fcntl、unistd、select、socket、spawn、signal、string、stdlib mman dirent resource/stat diredire=file操作等环境变量管理、strerror、syslog 等 POSIX 子系统的封装，使这些 API 在 OpenHarmony 上的行为更加一致和可预测， 并提供更好的错误处理。

默认值。

## 主要特性

- 共享库 (`.so`)，为主交付形式
- C 语言 API， `lfp_*` 命名空间
- pkg-config 元数据支持 (`libfixposix.pc`)
- 仅依赖 libc.so（系统库)
- 21 个头文件 (`lfp.h`, `lfp/*.h`)

- 提供 `O_CLOEXEC` 支持（兼容性增强)

- 提供 `O_NONBLOCK` 支持的可移植接口

- 提供 `lfp_strerror()` 的增强版错误描述函数

- 提供 `lfp_clearenv()` / `lfp_get_environ()` 羑lfp_set_environ()` 瑊环境管理
- 提供 `lfp_spawn` / `lfp_spawnp()` 及 spawn 屟action 础流= 进程创建

- 提供 `lfp_select()` 的 `timespec` 超时版本

- 提供 `lfp_pipe()` 的 CLOEXEC 稡式

- 提供 `lfp_pread()` / `lfp_pwrite()` 定位 I/O

- 提供 `lfp_truncate()` / `lfp_ftruncate()` 文件截断
- 提供 `lfp_mkstemp()` / `lfp_mkostemp()` 安全临时文件创建

- 提供 `lfp_strndup()` / `lfp_strnlen()` 安全字符串操作
- 提供 `lfp_parse_memsize()` 内存大小解析

- 提供 `lfp_accept()` / `lfp_socket()` 瑊 socket 操作

- 提供 `lfp_clock_gettime()` / `lfp_clock_settime()` — 时间操作
- 提供 `lfp_getrlimit()` / `lfp_setrlimit()` — 资源限制
- 提供 `lfp_syslog()` / `lfp_openlog()` / `lfp_closelog()` — 系统日志
- 提供 `lfp_sendfile()` — 零拷文件发送
- 提供 `lfp_opendir()` / `lfp_readdir()` — 目录操作
- 提供 `lfp_wifexited()` / `lfp_wexitstatus()` 等 — 退出状态检查
- 提供 `lfp_sig_dfl()` / `lfp_sig_ign()` / `lfp_sig_hold()` — 信号常量
- 提供 `lfp_mmap()` / `lfp_munmap()` — 内存映射

- 提供 `lfp_ptsname()` — 伪终端名获取
- 提供 `lfp_getpath()` — PATH 琜索

- 提供 `lfp_buildinfo()` — 构建信息

- 提供 `lfp_nice_k()` — nice 剀值安全版本
- 提供 `lfp_is_fd_open()` — fd 开放检查
- 提供 `lfp_isreg()` / `lfp_isdir()` / `lfp_ischr()` 等 — 文件类型判断
- 提供 `lfp_tty_attach()` / `lfp_tty_fattach()` — tty 连接
- 提供 `lfp_getpeereid()` — 对端凭据获取
- 提供 `lfd_fd_set()` / `lfd_fd_clr()` / `lfp_fd_zero()` / `lfp_fd_isset()` — fd_set 操作

- 提供 `lfp_cmsg_*()` — 辅助数据消息操作

- 提供 `lfp_log_mask()` / `lfp_log_upto()` / `lfp_setlogmask()` — 日志掩码操作
- 提供 `lfp_wcoredump()` / `lfp_wifsignaled()` / `lfp_wifstopped()` / `lfp_wstopsig()` / `lfp_wtermsig()` — wait 状态宏
## OpenHarmony 适配

- 平台: OpenHarmony (AArch64)
- 编译器: clang/clang++ (LLVM 15.0.4)
- 需要 autoreconf -fi 生成构建系统（原始 tarball 不包含 configure)
- 需要 3 个平台适配补丁 (config.guess, config.sub, configure)
- make 必须用 -j1（HMDFS 不支持 mkfifo)
- CONFIG_SHELL=bash 运行 configure 避免 toybox sh 兼容性问题
- configure mktemp 径径需修改为 $TMPDIR（HMDFS 权限限制）
- 无上游测试套件 (make check 无目标， TOTAL=0)
- 已通过 34 项功能测试验证可用性

- pkg-config 元数据正确
 已安装

- 已知问题: 头文件守卫冲突 (`lfp_strerror` 声明被隐藏)
- 依赖: 仅 libc.so (系统库)

- 安装前缀: `/storage/Users/currentUser/usr/local`

## 使用场景

- 适用于需要跨平台 POSIX 兼容性的 C/C++ 项目
- 可作为其他库的依赖（如网络库需要 socket 适配)
- 可用于增强文件描述符的可移植性(如 `O_CLOEXEC`, `O_NONBLOCK`)
- 可用于进程创建和管理(如 shell  需要 spawn)
- 可用于安全环境变量操作(如 `clearenv`)

- 可用于系统日志功能

- 可用于定时器和时间管理
- 可用于伪终端(pty) 管理

## 注意事项

- HMDFS 限制: mktemp -d 在当前目录创建的目录权限受限（umask 077 生效但 chmod 不生效），需使用 $TMPDIR 路径
- make 必须用 -j1 (jobserver mkfifo 在 HMDFS 上不支持)
- 源码需 autoreconf -fi 才能生成 configure (原始 tarball 不包含)
- 使用 CONFIG_SHELL=bash 避免 toybox sh 兼容性问题
- 头文件 `lfp/string.h` 和 `lfp/strerror.h` 存在守卫冲突（都使用 `_LFP_STRING_H_`), 编译时 `lfp_strerror()` 会产生隐式声明警告