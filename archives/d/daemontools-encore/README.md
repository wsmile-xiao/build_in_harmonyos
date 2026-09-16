# daemontools-encore

daemontools-encore 是 Bruce Guenter 维护的 D. J. Bernstein daemontools 增强分支：一套在 UNIX 上启动、监管、控制和记录常驻服务的命令行工具集，保持与 daemontools 的向后兼容，并在原版基础上加入 `svup`、`envini`、`setuser` 等新工具与 `svstat` once 标志、`envdir` 前缀、`softlimit` 限额重置等增强。

## 功能概述

包内交付 20 个可执行文件（`bin/`）与 19 个手册页（`share/man/man8/`）：

| 分组 | 工具 | 说明 |
|------|------|------|
| 监管核心 | `supervise` `svscan` `svscanboot` | 启动并监管服务；`supervise` 负责重启与状态上报，`svscan` 监管一整个服务目录 |
| 服务控制 | `svc` `svok` `svstat` `svup` | 向被监管服务发送信号、查询是否在监管中、打印状态、判断是否处于 up |
| 日志 | `multilog` `tai64n` `tai64nlocal` `readproctitle` | 读取并过滤日志、自动轮转、打 TAI64N 时间戳并本地化 |
| 身份与环境 | `envdir` `envini` `envuidgid` `setuidgid` `setuser` | 从目录/INI 文件构造环境变量，按账号设置 UID/GID 后执行子进程 |
| 进程与资源 | `fghack` `pgrphack` `softlimit` `setlock` | 阻止守护进程脱离前台、阻止新建进程组、设置资源上限、文件锁下执行 |

## OHOS 适配要点

- **DJB 风格构建，无 configure**：上游 README 明确「调整 conf-* 文件后 `make`，再在 conf-bin/conf-man 首行写安装目录后 `make install`」。配方按这个文档化接口写 `conf-cc` / `conf-ld`（取自 Conan 工具链的 clang 与 flags）和 `conf-bin` / `conf-man`（指向包内 `bin/`、`share/man/`），构建与安装都交给上游 `make programs man` 与 `make install`，不修改构建脚本。
- **不能使用 `make clean`**：TARGETS 清单同时包含 `man` 与 `targets`，而 OHOS 的 HMDFS 大小写不敏感（`MAN` 与 `man` 是同一 inode），clean 会删除发行版自带的 MAN 安装清单和 TARGETS，随后 `make install` 报 `No rule to make target 'MAN'`。改用 `make -B`（全量重建、不删除文件）。
- **安装目录模式**：上游 `installer` 用 `mkdir(man8, 0700)` 建目录、随后 `chmod(0755)`；HMDFS 保留创建时的模式且 chmod 不再生效，目录停在 2700 且属主映射为共享属主，`installer` 自己写文件都得到 `access denied`。配方按 MAN 清单预建目录（组可写），走 `installer` 已实现的 EEXIST 分支。
- **上游 install 缺陷（已打补丁）**：1.11 的 MAN 清单要求安装 `setuser.8`，但该版本既不随包提供、`man` 目标也不生成（生成的是 `setuidgid.8`），所以未修补时任何平台 `make install` 都失败。补丁 `patches/0001-MAN-optional-setuser.patch` 使用 `installer` 自带的 `?` 可选前缀标记该行。
- **FIFO 策略限制（已知功能缺口）**：HarmonyOS 拒绝用户进程创建 FIFO（`mkfifo(2)`、`mknod(2) S_IFIFO` 均返回 EPERM，AF_UNIX bind 同样被拒），`supervise` 因此无法建立 `supervise/control` 控制通道并以 `supervise: fatal: unable to read supervise/control: file does not exist` 退出。其余 19 个工具（含 `multilog`、`svstat`、`svc`、`svok` 的客户端语义）在设备上正常工作。

## 依赖关系

### 编译依赖

无。上游逻辑是自包含 C 源码，仅依赖 libc（唯一的外部工具是 `ar` / `ranlib`，由 OHOS profile 的 PATH 提供）。

### 运行依赖

无（仅 libc）。

## 上游测试

上游回归套件在 `rts.tests/`：`make rts` 把 `rts.tests/*.sh` 拼成一个脚本运行、再与 `rts.tests/*.exp` 的输出比对，共 21 个用例。其中 9 个 `supervise`/`svscan` 用例依赖 `supervise` 的控制 FIFO，在设备上被上述 FIFO 策略阻断；其余 12 个用例（envdir、envini、envuidgid、fghack、matchtest、multilog、nonexistent、pgrphack、readproctitle、setlock、softlimit、tai64n）全部通过。逐用例证据见版本目录 `reports/upstream-test.log.md` 与 `reports/upstream-tests.md`。

## 参考资料

- 官网：<https://untroubled.org/daemontools-encore/>
- 源码仓库：<https://github.com/bruceg/daemontools-encore>
- 上游 README / MAN / BIN 清单随发行版 tarball 提供
