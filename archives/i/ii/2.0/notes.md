# ii 2.0 适配记录

- 上游：`https://git.suckless.org/ii`，tag `2.0`，提交 `236114cf1fa4754da6679f68f01b5ab39553fe7c`。
- 源码包：`https://dl.suckless.org/tools/ii-2.0.tar.gz`，SHA-256 `4f67afcd208c07939b88aadbf21497a702ad0a07f9b5a6ce861f9f39ffe5425b`。
- 构建系统为 POSIX Makefile；使用 Conan `AutotoolsToolchain` 生成的编译环境，关闭并行构建，调用上游 `install` 规则将可执行文件、手册和文档装入包目录。
- ii 是独立命令行程序，无 Conan 依赖。上游没有测试目标；HarmonyOS PC CI worker 禁止测试进程绑定 loopback TCP/UNIX 域套接字，也拒绝 `mkfifo()`（`EPERM`），运行 UID 无 passwd 记录。Conan 补丁在 `getpwuid()` 失败时采用 nick `ii` 与有效 `HOME`（否则 `/tmp`），使程序仍可启动。当前原生测试只验证 fallback 后目标二进制可启动、输出 usage 并退出；不模拟 IRC/FIFO 会话。CI 已验证补丁应用、编译、打包及 CLI 检查通过；去除 FIFO 调用后的重跑在 shell 阶段遇 `fork failed: out of memory`，未执行构建。本地 Windows 环境没有 OHOS Conan profile/工具链。
