# plptools 1.0.26 适配笔记

- 构建环境：HarmonyOS PC aarch64，clang 15，Conan 2；2026-10-01。
- 源码：官方 `plptools-1.0.26.tar.gz`，SHA-256 `5a7faf45e268a5717d0b4e79ba8648983fba1d3629923b371e5ee3dbc80f2a58`。
- 依赖：readline/8.3 及其 ncurses 传递依赖。使用发布包已有的 configure；显式 build/host 三元组，避免执行未签名的 configure 探测程序。
- 上游 `AX_LIB_READLINE` 的交叉编译分支将版本检测写死为失败；配方先读取 Conan 提供的 `readline.h`，确认 `RL_READLINE_VERSION >= 0x0403` 后才预置 `ax_cv_lib_readline_version_ok=yes`。
- ncpd 上游使用 `pthread_cancel`；目标机缺此接口。补丁把两个工作线程改为合作式退出、唤醒和 join。上游原生源码其余部分不改。
- 可选 FUSE 组件不交付：已发布 libfuse/2.9.9 的静态库引用目标机没有的 `pthread_cancel`、`pthread_setcancelstate`，上游 `plpfuse` 也使用缺失的 `rindex`。未伪造取消接口或声称挂载可用。
- 上游 `make check` 没有注册 `TESTS` / `check_PROGRAMS`，计为 0/0。安装后 `ncpd`、`plpftp`、`plpprintd`、`sisinstall` 均在目标机执行 `--version`，4/4 通过。上游 `sisinstall` 自报 0.1，不等同于发布包 1.0.26。
- 没有 EPOC/Psion 串口硬件，协议通信尚未做端到端测试。
- 冻结输入事务 `plptools-w3-20260930T173000Z` 为 `W3_PASS`，12/12 阶段收据通过，日志 SHA-256 `2f0056d3f2d366590fe09b59b9c12ba92e4e509bc22f71de9128d72948bd048e`。
