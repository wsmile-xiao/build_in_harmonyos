# E568（草稿）: CI worker 开放式空管道 stdin 使交互型被测程序 fgets() 永久阻塞，测试挂死到 buildbot 14400s 超时

## 基本信息
- **严重度**: 2
- **类别**: test-harness, ci, stdin-blocking, process-environment
- **作者**: choose-mirror 2.137 适配子任务
- **来源 PR**: #9740（构建 #45140）
- **来源 commit**: (待提交后回填)

## 错误特征
```
^======== Testing the package: Executing test ======$
.*RUN: "\./<test-binary>"
.*<被测程序启动后的前几行输出>          # 如 CAPB backup align
# 之后无任何输出，直到 buildbot:
command timed out: 14400 seconds without output
program finished with exit code 1
```
特征：**编译/链接全绿**，test() 启动后仅输出几行（如 cdebconf CAPB 握手）即
沉默，无 FAIL 也无退出，整条流水线耗满 14400s 被 buildbot 强杀。

## 根因分析
被测程序是交互型状态机（choose-mirror 经 cdebconf passthrough frontend，
`debconfclient_new → debconf_capb → debconf_version` 后在 talk() 的
`fgets()` 等待 frontend 回复）。测试进程的 **stdin 是什么，决定结局**：

| 环境 | stdin 状态 | fgets() 行为 | 结果 |
|------|-----------|-------------|------|
| 本地 OHOS 开发机 shell | 已关闭/EOF | 立即返回 EOF | SIGSEGV(139)，测试通过 |
| CI buildbot worker (PTY: False) | **打开的空管道** | **永久阻塞** | 挂死 → 14400s 超时击杀 |

即测试结论依赖父进程 stdin 的偶然状态——**环境依赖型测试**。本地通过、
CI 失败，且 CI 侧连失败原因都归为"未知"（无错误输出可归因）。

## 推荐方案
**方法**: child-stdin-devnull-plus-sigalrm-bounded-wait

**说明**: 测试 harness 必须自己把子进程 stdin 与环境解耦，不依赖父进程：
1. **fork 后子进程 `open("/dev/null")` + `dup2(z, 0)`** 再 exec——确定性 EOF，
   本地与 CI 行为完全一致（fgets 立即 EOF，状态机走完已知路径）；
2. **父进程 wait 用 SIGALRM 有界等待**（`sigaction(SIGALRM)` + `alarm(30)` +
   `waitpid(WNOHANG)` 轮询），超时 SIGKILL 子进程——即使将来出现未知阻塞源，
   测试也最多 30s 失败，绝不挂死整条 CI 流水线；
3. 断言真实状态机里程碑（VERSION 2 / REGISTER ... / GET ... / SET ...）+
   ELF 字节扫描静态链接符号（防 stub 假通过）。

```c
/* 子进程 */
int z = open("/dev/null", O_RDONLY);
if (z >= 0) dup2(z, 0);
execl(bin, bin, "-n", (char *)0);
/* 父进程等待 */
sigaction(SIGALRM, &sa, &old); alarm(TEST_TIMEOUT);
for (;;) { r = waitpid(pid, &st, WNOHANG); /* ... + g_timed_out 检查 */ }
```

**验证/命令**:
```
# 复现 CI 条件：stdin 接打开的空管道跑 test_package（修复前会挂死）
sleep infinity | conan test <profile> archives/c/<pkg>/<ver> test_package/   # 修复前: 超时
# 修复后: stdin 无关，/dev/null 模拟也能过
conan test <profile> archives/c/<pkg>/<ver> test_package/ < /dev/null
```

## 关键词
stdin 阻塞, fgets 挂死, 空管道, buildbot 超时, 14400s, PTY False, 交互型程序,
cdebconf passthrough, debconf frontend, 环境依赖型测试, 本地通过 CI 失败,
test_package 挂死, SIGALRM 有界等待, dup2 /dev/null, conan test()

## 实测记录（choose-mirror 2.137, PR #9740 构建 #45140）
- 修复前（stdin 未解耦）：本地 30/30 通过（exit 139）；CI #45140 输出
  "CAPB backup align" 后沉默 14400s 被 kill，exit 1
- 修复后（/dev/null + SIGALRM 30s）：本地通过；CI stdin 状态不再影响结果
- 触发条件：被测二进制读 stdin 且无数据时不主动退出（交互状态机典型）

## 变体 2：CI 遗留 fd ≥ 3 静默改道 debconf 协议输出（构建 #47903, CI-007）
stdin 修复后同一 PR 的下一次构建换了 worker（CI-020 → CI-007），失败形态变化：
编译全绿，test() 第一行 transcript 都没有（`FAIL: transcript missing 'VERSION 2'`，
零字节输出后 exit 139）。

根因：cdebconf 客户端库的 fd 约定——`debconfclient_new()`（debconfclient.c:96-112）
做 `fdopen(3, "a")` 作为协议通道，并在 `DEBCONF_REDIR` 未设时
`dup2(DEBCONF_OLD_STDOUT_FD=5, 1)`。若 CI runner 给测试进程**泄漏了打开的 fd 3**
（buildbot 沙箱差异，worker 间不一致），协议输出全部改道进 fd 3，stdout 管道上一
个字节都没有；CI-020/本地 fd 3 未泄漏，走 `client->out = stdout` 回退所以正常。

修复（不回退 stdin/SIGALRM 修复）：harness `main()` 开头清扫 fd ≥ 3
（`sysconf(_SC_OPEN_MAX)` 上限 4096 兜底），对 Run 1 的 fork 子进程与 Run 2 的
popen 均生效，使客户端确定性地回退到 stdout。

复现/验证命令（fd 3+5 重定向到文件模拟泄漏）：
```
test_cm_old <bin> 3>leak3.out 5>leak5.out   # 旧: FAIL missing 'VERSION 2'，leak3.out 有 792B transcript
test_cm_new <bin> 3>leak3.out 5>leak5.out   # 新: PASS，leak3.out 0 字节
```

---
*与 E074 的区分：E074 是 make -j jobserver FIFO 并行挂死；本条是单进程测试
harness 的 stdin 继承问题，修复点在被测程序的 spawn 方式而非构建系统。*
