# reptyr 0.10.0 适配笔记

## 编译环境
- 构建系统: 普通 Makefile（`override CFLAGS := -MD -Wall -Werror -D_GNU_SOURCE -g $(CFLAGS)`；按 `uname -s` 选 `platform/linux/*` 或 `platform/freebsd/*`）
- 编译日期: 2026-09-27
- 编译器: OHOS SDK clang 15.0.4（`~/.harmonybrew/opt/ohos-sdk@26.0.0.18/native/llvm/bin`）
- 目标平台: HarmonyOS PC / aarch64-linux-ohos（HongMeng Kernel 1.12.0，HAD-W32）
- 上游源码（GitHub 官方 tarball 端点 codeload）:
  <https://codeload.github.com/nelhage/reptyr/tar.gz/refs/tags/reptyr-0.10.0>
  - sha256 = `c6ffbc34a511ac00d072219bda30699e51f2f4eb483cbae9e32e981d49e8b380`（与 github.com/archive 端点字节一致，已实测校验）
- Conan profile: `ohos-aarch64-device`（本机图像；CI 使用仓库 profile）

## 编译步骤
1. `get()` 下载官方 tag 归档；`apply_conandata_patches()` 应用 2 个可移植性补丁
2. `make CC=<conan conf clang> -j1`（R9/R33）：全部 5 个目标文件编译并链接出 `reptyr`
3. `package()` 显式拷贝 `bin/reptyr`、`share/man/man1/reptyr.1`、
   `share/man/fr/man1/reptyr.1`（由 `reptyr.fr.1` 重命名）、
   `share/bash-completion/completions/reptyr.bash`、`licenses/COPYING`
   （上游 `install` 目标依赖 `install(1)`，OHOS 无此命令，改为 conan copy）
4. `conan create` 内 test_package：`sh test_reptyr.sh` 18/18 PASS

## 上游测试清点（R51 申报表）

| 检查项 | 命令 | 结果 |
|---|---|---|
| 测试目录 | 解压树 `test/` | 存在：basic.py、tty-steal.py、util.py、victim.c、matrix.sh、requirements.txt |
| 测试入口 | `grep -n '^test:' Makefile` | `test: reptyr test/victim` → `$(PYTHON_CMD) test/basic.py` + `test/tty-steal.py`（2 个用例） |
| 测试依赖 | `cat test/requirements.txt` | `pexpect`、`python-prctl>1.6`（prctl 仅 tty-steal.py 可选分支；缺失时提示后继续） |
| check 目标 | `make check` | 上游无 check 目标（matrix.sh 只做 32/64 位构建矩阵，仍以 make test 为入口） |
| 真机执行 | `python3 test/basic.py`、`python3 test/tty-steal.py`（pexpect 4.9.0） | **2 个用例全部失败**，均在 preflight `PTRACE_ATTACH` 处 EPERM（平台边界，见下） |

**结论**：上游共 2 个用例（N=2），在 OHOS 真机上 0 通过、2 失败——失败原因不是适配缺陷，
而是 OHOS 内核对非特权进程禁用 ptrace（下节完整证据）。按 R51 如实申报，并由
`test_package/test_reptyr.sh` 补 18 条消费侧功能断言（覆盖平台可用行为面）。

## 平台能力边界：OHOS 禁止非特权进程使用 ptrace（本任务核心发现）

自建最小探针（源码与输出见 `reports/ptrace-capability-probe.txt`）在本机（同一 SSH 会话、
同一 UID）实测：

| 场景 | 结果 |
|---|---|
| 父进程 `PTRACE_ATTACH` 直接子进程 | `-1 / EPERM` |
| 父进程 `PTRACE_SEIZE` 直接子进程 | `-1 / EPERM` |
| 祖父 `PTRACE_ATTACH` 孙进程 | `-1 / EPERM` |
| 子进程自身 `PTRACE_TRACEME` | `-1 / EPERM` |
| `process_vm_readv` 读取子进程内存 | `-1 / EPERM` |
| victim `prctl(PR_SET_PTRACER, PR_SET_PTRACER_ANY)` | `EINVAL`（内核未实现） |

佐证：探针进程 `/proc/self/status` 显示 `Seccomp: 2`（filter 模式）、`Seccomp_filters: 1`，
`CapEff=0x2a`（无 CAP_SYS_PTRACE）；内核提供 `/proc/sys/kernel/yama/pdebug_scope`，
但读取返回 ENOSYS（策略接口未开放）。

**影响**：reptyr 的核心附加功能（`reptyr PID` / `-T` / `-s`）在 OHOS 上被系统策略阻断，
任何用户态补丁都无法绕过；`-l` / `-L` 的 pty 管理功能不受影响。上游 2 个 E2E 用例因此失败，
属平台边界而非适配缺陷；已如实记入 `reports/test-report.md` 与 PR 正文「已知限制」。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make` 后链接失败（platform 目标缺失） | Makefile 用 `UNAME_S := $(shell uname -s)` 匹配 `Linux`；OHOS 返回 `HarmonyOS`，linux 后端目标未被编译 | 补丁 0001：`ifeq ($(UNAME_S),Linux)` → `ifneq ($(filter $(UNAME_S),Linux HarmonyOS),)`（纯平台识别，无平台宏；E007 家族的手写 Makefile 变体） |
| 2 | `error: redefinition of 'struct sockaddr_storage'`（-Werror 下直接失败） | `platform/linux/linux.h` 先经 `<linux/net.h>` 引入 `<linux/socket.h>`（定义 kernel 侧 sockaddr_storage），随后 `<sys/socket.h>`（musl）再次定义 | 补丁 0002：在包含 linux 头文件期间用 `#if defined(__linux__) && !defined(__GLIBC__)` 守卫把 kernel 侧结构改名（E091 同类处置，accel-ppp 先例形态；glibc 不受影响） |
| 3 | `make install` 不可用 | 上游安装规则调用 `install(1)`；OHOS 无此命令 | conanfile `package()` 显式 `copy()` 安装产物（不依赖系统 install） |
| 4 | 上游测试全部失败 | OHOS 非特权进程 ptrace 被拒 EPERM（见上节） | 如实记录平台边界；test_package 覆盖可用行为面（pty 分配、参数校验、错误报告） |

## 源码修改

`patches/` 两个补丁，均为可移植性修复，都不注入平台宏（R8/PF5）：

1. `0001-Makefile.patch` — HarmonyOS 走 Linux 后端分支（+1/-1 行）
2. `0002-platform-linux-linux.h.patch` — sockaddr_storage 重定义守卫（+10 行）

## 依赖版本

无。W0 依赖检查：`requires` 为空；源码仅链接系统 libc；上游构建无 pkg-config 依赖
（`PKG_CONFIG` 仅用于可选的 bash-completion 安装目录探测，install 目标已被 conan package 替代）。

## 验证结果

```text
# 本机手工构建（OHOS SDK clang 15.0.4，aarch64 设备原生）
make → rc=0；产物 ./reptyr (ELF aarch64)，./reptyr -v → "This is reptyr version 0.10.0."

# 手工功能验证（真实执行）
reptyr -h / -v                      → rc=0，输出符合上游
reptyr（缺 pid）                     → rc=1，"No pid specified to attach"
reptyr notanumber                   → rc=1，"Invalid pid: must be integer"
reptyr 999999999                    → rc=1，"Unable to attach ...: No such process"
reptyr -l </dev/null                → 打印 "Opened a new pty: /dev/pts/N"（pty 分配可用）
reptyr -L sh -c 'echo marker'       → 子进程 stdout 经新 pty 回传，REPTYR_PTY 指向字符设备
reptyr <任意真实 pid>               → rc=1，"Permission denied"（平台 ptrace 边界，见上）

# 上游测试（真机）
python3 test/basic.py     → FAIL（preflight PTRACE_ATTACH EPERM）
python3 test/tty-steal.py → FAIL（同一边界）

# test_package（sh test_reptyr.sh）
18/18 PASS（见 test_package/MANIFEST.yml；conan create 日志与 reports/test-report.md）
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/reptyr | 主程序（aarch64 ELF） |
| share/man/man1/reptyr.1 | man 手册（英文） |
| share/man/fr/man1/reptyr.1 | man 手册（法文） |
| share/bash-completion/completions/reptyr.bash | bash 补全 |

## 注意事项

- 产物为可执行命令，已在软件级 `archives/r/reptyr/commands.json` 声明（R38）。
- **核心功能受平台边界限制**：OHOS 对非特权进程禁用 ptrace（ATTACH/SEIZE/TRACEME 全 EPERM，
  `process_vm_readv` 同拒，进程带 seccomp 过滤器），`reptyr PID` / `-T` / `-s` 无法在该平台使用；
  `-l` / `-L` 的 pty 管理能力正常。复现命令与证据见 `reports/ptrace-capability-probe.txt`。
- 上游测试需 pexpect（已用私有 `--target` 安装到任务目录，未污染共享 venv），
  `python-prctl` 在 OHOS 上不可用但 tty-steal.py 会优雅跳过该可选分支。
- `reptyr -l` 在 stdin 为 EOF（如 `</dev/null`）时会忙等（上游对 `read()==0` 未处理），
  自动化中请带超时/看护进程（本次测试在断言后用 kill 收尾）。

---
**编译结束**: 2026-09-27
**最终状态**: built
