# plptools

plptools 提供通过串口连接 EPOC/Psion 设备的命令行工具。本配方适配官方 1.0.26 发布包的 `ncpd`、`plpftp`、`plpprintd` 和 `sisinstall`。

## HarmonyOS PC 适配

配方使用官方发布包中生成好的 Autotools 脚本，依赖 Conan 提供的 readline。目标机不允许运行未签名的 configure 探测程序；因此显式设置 build/host 三元组，并用依赖头文件的 `RL_READLINE_VERSION` 校验后预置 `ax_cv_lib_readline_version_ok`。ncpd 原来的 `pthread_cancel` 停线程方式在目标机不可用，移植补丁改为停止标志、信号唤醒和 `pthread_join`，没有伪造线程取消接口。

可选的 `plpfuse` 未交付：已发布的 libfuse 2 静态库引用目标机缺失的 `pthread_cancel`、`pthread_setcancelstate`，上游该组件还使用缺失的 `rindex`；跳过可选 FUSE 构建而不声明它可用。上游无注册测试；安装后的四个核心程序均在目标机执行 `--version`。串口硬件和文件系统挂载功能尚未验证。

[上游发布包](https://github.com/plptools/plptools/releases/tag/v1.0.26)
