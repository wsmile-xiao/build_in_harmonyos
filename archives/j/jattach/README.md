# jattach

JVM Dynamic Attach 工具（jmap + jstack + jcmd + jinfo 合一的单文件命令行程序）。

- 上游：https://github.com/jattach/jattach
- 许可：Apache-2.0
- 构建系统：Makefile（纯 C，无第三方依赖）
- 适配版本：2.2（HarmonyOS PC / aarch64，ohos-sdk clang 15）

## 命令

```bash
jattach <pid> load <.so-path> { true | false } [ options ]
jattach <pid> properties
jattach <pid> agentProperties
jattach <pid> datadump
jattach <pid> threaddump
jattach <pid> dumpheap [ file ]
jattach <pid> inspectheap
jattach <pid> setflag <flag> <value>
jattach <pid> printflag <flag>
jattach <pid> jcmd <command> [args ...]
```

## 适配说明

- 源码零修改：鸿蒙 OHOS clang 15 定义了 `__linux__`/`__NR_setns` 且提供
  `<sys/sem.h>`，`src/posix/psutil.c` 的 Linux 分支与 OpenJ9 代码路径可原样编译。
- 上游无测试套件（N=0），本适配新增 `test_package/` 消费者测试（18 断言）。
- HarmonyOS 对非应用进程限制 AF_UNIX 路径 socket 创建（HMMAC，EPERM），
  且 SysV 信号量被 seccomp 拦截（SIGSYS）；依赖 JVM 侧 attach socket 的
  “Connected to remote JVM” 正路径无法在本机复现，详见版本目录 `notes.md`。
