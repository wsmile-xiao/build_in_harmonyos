# radioclk 1.0.pristine — 适配笔记

## 概况

- 上游：Jonathan A. Buzzard 的 radioclkd，解码 DCF77/MSF/WWVB 无线电报时信号，
  通过串口 modem-status 线（DCD/CTS/DSR）接收，把时间写入 SysV 共享内存段，
  供 ntpd 的 SHM reference clock 驱动消费。
- 上游主页 `http://www.buzzard.org.uk/jonathan/radioclock.html` 已停泊，
  Debian 的 watch 文件同样判定无可用上游。取 Debian pool 的
  `radioclk_1.0.pristine.orig.tar.gz`（pristine，无 Debian 补丁），
  SHA256 实测复核：`8C63F60ECA6CC5F2999B5CE55E7DD5CFE65812FB3DDBB33E8206AC7E659CF74C`。
  仓库同类先例：cgvg、unzoo、libbrahe、unalz。
- 版本号 `1.0.pristine` 直接沿用 Debian 版本串（上游唯一版本就是 1.0）。

## W0 依赖结论

- 依赖数量：0（仅 libc）
- 已满足依赖：libc（musl）全部覆盖——termios ioctl（TIOCMGET/TIOCMSET）、
  SysV shm（shmget/shmat/shmdt）、syslog、sched、paths.h（_PATH_VARRUN）
- 缺失依赖：无
- 是否需要拆分依赖适配：否
- 阻塞点：无

## W1 源码/构建分析

- 单翻译单元 C 程序：`radioclkd.c`（~1063 行）链接为 `radioclkd`。
  `refclock_shm.c` 是给 ntp 发行版的替换文件，本包不构建。
- 上游 Makefile：`CC = /usr/bin/gcc`（`=` 赋值，可被 make 命令行覆盖）；
  `install` 目标硬编码 `/usr/bin/install`（OHOS 缺失，知识库 E098）和
  `/sbin` 布局——安装逻辑改由配方 `package()` 完成。
- 无 configure、无 config.guess/config.sub 问题（E007/E072 不适用）。
- 上游无测试套件（0 用例）；test_package 用 5 组共 10 断言验证安装后二进制。

## 可移植性修改（source() 内 replace_in_file，非 patch 文件）

1. 删除 `#include<termio.h>`——musl 无此遗留头文件；文件内无任何
   termio 符号使用，纯死包含。
2. 增加 `#ifndef TIOCMIWAIT` / `#define TIOCMIWAIT 0x5452`——
   TIOCMIWAIT 是 x86 侧 ioctl 号，aarch64 走 asm-generic 头文件不含它，
   编译会失败。运行期若内核串口驱动拒绝该 ioctl，
   `WaitOnSerialChange()` 返回 -1，上游 README 文档化的 `-p` 轮询模式
   是降级路径。0x5452 为该 ioctl 的历史 Linux 值。

## 版本/命名一致性

- 目录：`archives/r/radioclk/1.0.pristine/`
- 配方：`radioclk/1.0.pristine`
- test_package：`package: radioclk/1.0.pristine`
- 分支：`feat/radioclk-1.0.pristine-codex`

## 环境备注（非本包问题）

- 本轮创建 worktree 时发现 origin/main HEAD 含文件名带 `\r\r` 的非法路径
  `archives/g/gama/2.29/patches/0002-dataparser-ungated.patch\r\r`（Windows
  无法检出），worktree 用 `--no-checkout` + sparse-checkout 排除该单文件后
  正常建立。该问题属上游仓库，不在本包修改边界内，仅记录。
- origin/main 上 `archives/l/libXext/`（大写 X）与 `archives/l/libxext/`
  并存，Windows 大小写不敏感文件系统上检出必然表现为两个 M；同样仅记录。

## 下一步（真机 / shadow CI，待空闲窗口）

### r1（2026-10-02 17:23，真机 shadow CI）

| 项 | r1 |
|---|---|
| job 名 / run 目录 | radioclk-1.0.pristine-20261002 / ohos-test-runs/codex-1.0.pristine-radioclk-1.0.pristine-20261002-conan-20261002-172349-38268 |
| 排队等待秒数 | 0（锁空闲） |
| exit code | 1 |
| L0 / L1 / L2 / L4 / L5 | — / fail: conan create failed / skip: not run / skip: not run / skip: not run |
| 本轮报错原文 | `TypeError: get() got an unexpected keyword argument '1.0.pristine'`（source() 内） |
| 根因 | conandata.yml 的 sources 写成了版本嵌套结构 `{"1.0.pristine": {url, sha256}}`，而配方按仓库约定用 `get(self, **self.conan_data["sources"])` 直接展开，版本键被当成 kwarg |
| 解法 | conandata.yml 去掉版本嵌套层，sources 直接是 url/sha256（与 aa3d/fathom 等先例一致） |

另：stderr 有 `ci/conan/build_and_test.sh:164: permission denied: git`（设备无 git，
非阻塞，构建流程继续）；传输阶段曾误把本机 reports/ 生成物打进 tar，已在设备端
删除后核对文件清单再启动（自检模板 2.3 要求）。

### r2（2026-10-02 17:26，真机 shadow CI）

| 项 | r2 |
|---|---|
| exit code | 1 |
| L1 / L2 / L4 / L5 | fail: conan create failed / skip / skip / skip |
| 本轮报错原文 | `radioclkd.c:541:15: error: use of undeclared identifier 'TIOCM_CTS'`（共 19 个 TIOCM_CD/TIOCM_CTS/TIOCM_DSR/TIOCMGET/TIOCMSET undeclared）+ `warning: call to undeclared function 'ioctl'` |
| 根因 | r1 静态分析误判 `<termio.h>` 为纯死包含直接删除；实际上游靠 glibc 头文件链从该头间接获得 TIOCM_* modem 线宏，musl 把这些宏放在 `<termios.h>`，ioctl() 原型在 `<sys/ioctl.h>` |
| 解法 | `#include<termio.h>` 替换为 `#include<termios.h>` + `#include<sys/ioctl.h>`（知识草稿已同步修正） |
| 附带 | clang 提示 `abs()` 收到 long 参数建议 `labs()`——仅 warning，非门禁阻塞，保留上游原样 |

### r3（2026-10-02 17:31，真机 shadow CI）✅ 全绿

| 项 | r3 |
|---|---|
| run 目录 | ohos-test-runs/codex-1.0.pristine-radioclk-1.0.pristine-20261002-conan-20261002-173146-41167 |
| 排队等待秒数 | 0 |
| exit code | 0 |
| L0 / L1 / L2 / L4 / L5 | pass / pass: test_package executed / pass: radioclkd --version OK / pass: no patches / pass: bin/ has content |
| 上游测试 | 0/0（上游无测试套件，R51 清单在 test_package/MANIFEST.yml） |
| test_package | `test_radioclk: all 5 assertion groups passed`（5 组 10 断言） |
| L1e | `[ok] L1e: Negative test confirmed — test genuinely depends on radioclk` |
| 结论 | Build Summary 1/1，Pass rate 100%，全部门禁 pass |

```sh
# 隔离 job
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex \
  --job radioclk-1.0.pristine \
  --package archives/r/radioclk/1.0.pristine \
  --repo-source <existing-repo>

# runner
sh "$HOME/ohos-users/codex/radioclk-1.0.pristine/run-conan-heavy.sh"
```

重点记录：L0–L5 结果、conan create 退出码、test_package 5 组断言结果、
`radioclkd --version` 在真机的实际输出。
