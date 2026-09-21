# jattach 2.2 适配笔记

## 编译环境

- 构建系统: makefile（上游顶层 Makefile，无 configure）
- 编译日期: 2026-09-20
- 编译器: OHOS SDK clang 15.0.4（`$HOME/.harmonybrew/opt/ohos-sdk@26.0.0.18/native/llvm/bin/clang`）
- 目标: aarch64-linux-ohos（设备本机编译），Conan profile `ohos-aarch64`
- 依赖: 无（纯 C + POSIX，W0 通过；`build.dependencies: []`）

## 编译步骤

上游无 configure/cmake，直接使用项目 Makefile：

```bash
cd jattach-2.2.work        # 上游 tag tarball 解压后的源码树
make -j1 CC="$CC"          # 产出 build/jattach
```

Conan 配方中等价实现：`build()` 从 `tools.build:compiler_executables:c` 取
编译器（R33，不依赖裸 shell 变量），在 source 目录执行 `make -j1 CC=<clang>`。

上游无测试套件（见下），无需 `make check`。

## 上游测试清点（R51 第一步，证据）

- 2.2 tag tarball 共 11 个文件：`.gitignore`、`LICENSE`、`Makefile`、`README.md`、
  `jattach.spec`、`src/posix/{jattach.c,jattach_hotspot.c,jattach_openj9.c,psutil.c,psutil.h}`、
  `src/windows/jattach.c`；无 `tests/`、无 `test_*` 目标。
- `make -n check` 输出：`make: *** No rule to make target 'check'.  Stop.`（N=0）。
- 故上游测试通过率不适用；本适配以 `test_package/` 消费者测试补足（18 断言，全部通过）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 设备无法直连 `github.com`（curl 12s 超时） | 设备出网策略限制 | 改用 GitHub 官方 tar 入口 `codeload.github.com`（仓库内 274 个既有配方同源），下载与 sha256 校验均通过 |
| 2 | 设备 `/tmp` 只读（erofs, ro），jattach 默认 tmp 路径不可写 | HarmonyOS PC /tmp 为只读镜像 | 使用上游支持的 `JATTACH_PATH` 环境变量重定向触发文件与 socket 目录；正常 JVM 场景走 `/proc/<pid>/root/tmp` |
| 3 | shell 会话内无法创建 AF_UNIX 路径 socket（bind EPERM） | HMMAC 对非应用进程的限制（socketpair/abstract socket 可用，路径 socket 被拒） | 与 jattach 无关（attach socket 由目标 JVM 创建）；测试改用可复现的触发/信号路径断言，正路径限制如实记录 |
| 4 | SysV 信号量调用被内核以 SIGSYS 终止 | 平台 seccomp 策略禁止 `semget/semop` | 仅 OpenJ9 attach 路径使用信号量；HarmonyOS 无 JVM 运行环境，该路径不可达，如实记录为平台限制，不引入无意义补丁 |

## 源码修改

无。上游 2.2 源码在 OHOS clang 15 下零修改编译通过：

- `src/posix/psutil.c` 的 `#ifdef __linux__` 分支在 OHOS 生效
  （`__linux__` 与 `__NR_setns` 均已定义，`setns` 容器支持保留）；
- `<sys/ipc.h>`、`<sys/sem.h>`、`flock(2)`、`getline`、`stpncpy` 均由 OHOS musl
  提供（仅信号量在运行期被 seccomp 拦截）。

`patches/` 目录为空，`conandata.yml` 声明 `patches: {}`。

## 依赖版本

无第三方依赖。仅系统 libc（musl）与内核接口（/proc、socket、signal）。

## 验证结果

```text
$ make -j1 CC=<clang>                       # rc=0
$ build/jattach                             # 用法横幅 + rc=1（预期）
jattach 2.2 built on Sep 20 2026
Usage: jattach <pid> <cmd> [args ...]

$ build/jattach abc properties              # rc=1
abc is not a valid process ID

$ build/jattach 99999999 properties         # rc=1
Process 99999999 not found

$ JATTACH_PATH=<writable-dir> build/jattach <live-dummy-pid> properties   # rc=1
Could not start attach mechanism: No such file or directory
# 期间观测到 .attach_pid<PID> 触发文件被创建/清理，目标进程收到 SIGQUIT（exit 128+3）

$ bash test_package/test_jattach.sh         # 18/18 PASS
```

- test_package 消费者测试：18 断言全过（`build_and_test.sh` L1 系门禁所验证）。
- conan-verify G0–G4：见 `reports/conan-verify-report.md`（由工具生成）。

## 知识库复用（W5）

本次限制均命中既有知识，未产生新错误模式（无需新增草稿）：

- **E002**（/tmp 只读 erofs）→ 解释 JATTACH_PATH 的必要性；
- **E461**（OHOS 拒绝 AF_UNIX 文件 socket bind：HMDFS EPERM、/tmp EROFS、
  /dev/shm EACCES；abstract socket 可用）→ 解释 attach 正路径不可本机复现；
- **E246**（HarmonyOS seccomp 以 SIGSYS 终止受限 syscall）与 SysV IPC 草稿
  （`DRAFT-ohos-sysv-shmget-sigsys`）→ 解释 OpenJ9 路径不可用。

## 平台限制（如实记录，非适配缺陷）

1. **attach 正路径无法本机复现**：jattach 连接的是 JVM 自己创建的
   `/tmp/.java_pid<PID>`（或 JATTACH_PATH 下）Unix socket。HarmonyOS
   HMMAC 拒绝非应用进程创建路径 socket（`bind: EPERM`；abstract socket 与
   socketpair 可用），因此设备 shell 会话内无法搭建模拟 JVM 监听端；
   “Connected to remote JVM → JVM response code = 0” 流程未能在本机实测。
2. **OpenJ9 路径不可用**：该路径经 `semget/semop` 通知 JVM，内核对该
   syscall 返回 SIGSYS（core dumped），在 HarmonyOS 上不可用；HarmonyOS
   当前无 JVM 运行环境，该分支实际不可达。
3. HotSpot 主路径的功能断言（/proc 解析、触发文件、SIGQUIT、错误退出）
   均在 test_package 中真实执行并通过。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/jattach` | 35200 字节，aarch64 musl PIE ELF，命令入口见软件级 `commands.json` |
| `licenses/LICENSE` | Apache-2.0 许可证原文 |

## 注意事项

- 目标 JVM 的 attach socket 目录与运行用户权限需一致；跨用户/容器场景可用
  `JATTACH_PATH` 显式指定可写目录。
- 设备 `/tmp` 只读，`JATTACH_PATH` 在 HarmonyOS PC 上通常是必需品。

**编译结束**: 2026-09-20
**最终状态**: built
