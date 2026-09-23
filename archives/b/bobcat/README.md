# Bobcat

Bobcat（"Brokken's Own Base Classes And Templates"）是 Frank B. Brokken 开发的 C++ 通用类库，以单一共享库/静态库形式提供约 130 个类，覆盖 C++ 服务端与工具开发常用基础设施。

## 功能概述

- 子进程管理：Process/Fork/Pipe/Redirector（fork+exec、管道、I/O 重定向）
- 命令行：Arg/ArgConfig 参数解析（含 getopt_long 封装）、历史与单键输入
- 配置文件：ConfigFile（rc 风格注释/指令解析）、CSV 表格
- 流与缓冲：IFdStream/OFdStream（fd 流）、mmap 流、过滤与多路缓冲、Logbuf 日志
- 套接字：SocketBase/ServerSocket/ClientSocket/LocalSocket 系（inet + unix 域）
- 时间：DateTime（解析/格式化/时区）、std::chrono 封装（ClockBase 系列）
- 并发/IPC：Semaphore、Selector、共享内存映射、Flock
- 其他：Pattern（正则）、BigInt（SSL 类，light 构建不含）、Hash 表、TypeConverter、Glob、User/Stat 文件属性等

## OHOS 适配

- 上游以自有构建工具 **icmake** 驱动（`./build light`），OHOS 设备与 CI 均无 icmake；
  Conan 配方以 Python 精确复刻 light 构建语义（等价编译/链接命令行，见 6.14.00/conanfile.py 与 notes.md）。
- 上游需要 **C++20**；配方按 profile/设置以 `--std=c++20` 编译。
- **light 构建**（上游文档一等模式）：CLASSES 全部 128 类，零第三方依赖；
  OpenSSL/Readline/X11/Milter 类由上游 light 模式排除（OHOS 制品仓暂无 openssl/readline 二进制）。
- 平台兼容性补丁见 `6.14.00/patches/`（POSIX strerror_r、typename 补齐、
  C++23 clock_cast 替换、libc++ 时长类型差异、迭代器 category 修正、裸 mode_t/STDxx_FILENO 头补齐、裸 bind 全局限定）。

## 依赖关系

- light 构建：无第三方库依赖（仅标准 C++ 与 POSIX 系统 API）
- 完整构建（上游 `./build libraries all`）另需 openssl、readline、X11、libmilter（当前不适配）

## 参考资料

- 上游仓库：https://gitlab.com/fbb-git/bobcat
- 上游主页：https://fbb-git.gitlab.io/bobcat/
- Debian 源码包（本归档源码来源，权威镜像）：https://deb.debian.org/debian/pool/main/b/bobcat/
