# E434 — OHOS /bin/sh 对 SIGHUP 以 WIFEXITED(129) 退出而非 WIFSIGNALED：编译期子进程 shell 覆盖修复

## 错误特征
- 上游测试 `SubprocessTest.InterruptChildWithSigHup` 失败：`Expected equality of these values: ExitInterrupted Which is: 130 / subproc->Finish() Which is: 129`
- 子进程 `kill -HUP $$` 后 waitpid 显示 `WIFEXITED(129)`（128+SIGHUP 作为退出码）而非 `WIFSIGNALED(SIGHUP)`

## 触发条件
- 构建系统/工具：ninja（或任意经硬编码 `/bin/sh -c` 派生子进程并依赖 WIFSIGNALED 中断检测的工具）
- 阶段：testing/runtime
- 平台：HarmonyOS PC（OHOS aarch64），/bin/sh 为 toybox 系（musl aarch64）

## 根因分析
OHOS 设备 `/bin/sh` 收到 SIGHUP 时以 `exit(128+1)=129` 正常退出（WIFEXITED），
而非被信号杀死（WIFSIGNALED）。ninja `ParseExitStatus` 仅对 WIFSIGNALED(SIGHUP) 映射
`ExitInterrupted`(130)，故返回 129 ≠ 130。POSIX 信号语义 shell
（`/data/service/hnp/bin/bash`，构建 profile 的 CONFIG_SHELL/SHELL 指向路径）实测
`WIFSIGNALED(SIGHUP)` 正确。ninja 子进程 shell 硬编码于 `src/subprocess-posix.cc:132`
（`{ "/bin/sh", "-c", command, NULL }`），无运行时环境覆盖项。

## 解决方案

### 推荐方案
编译期子进程 shell 覆盖（subprocess-shell-compile-override）：
```bash
# 补丁：subprocess-posix.cc 硬编码 /bin/sh → 编译期宏 NINJA_SUBPROCESS_SHELL（默认 /bin/sh）
# 补丁：CMakeLists.txt 新增 NINJA_SUBPROCESS_SHELL cache 变量并注入 libninja 编译定义
cmake . -DNINJA_SUBPROCESS_SHELL=/data/service/hnp/bin/bash
cmake --build . --target ninja_test -j2
./ninja_test --gtest_filter=SubprocessTest.InterruptChildWithSigHup   # PASSED 130==ExitInterrupted
```
默认值 `/bin/sh` 保持其他平台行为不变，仅 OHOS 配方显式传入 bash 路径。

### 禁止做法
- ❌ 补丁内直接用 `#ifdef __OHOS__` 硬编码平台差异（违反 R8/PF5 平台宏禁令）
- ❌ 修改上游测试断言或用超时观察把 WIFEXITED(129) 伪写为通过

## 验证
```bash
# 补丁前：InterruptChildWithSigHup FAILED（130 vs 129）；全量 407/411
# 补丁后：InterruptChildWithSigHup PASSED；全量 408/411（99.3%），408/433（94.2%）
# C probe（fork+execl /bin/sh + kill(SIGHUP)+waitpid）：WIFEXITED code=0 => NOT WIFSIGNALED
# C probe（fork+execl bash + kill(SIGHUP)+waitpid）：WIFSIGNALED sig=1 => meets
```

## 适用边界
- 适用：通过硬编码 /bin/sh 派生子进程并依赖 SIGHUP 中断语义的 C/C++ 构建工具与测试（OHOS）
- 反例：纯 Linux 环境 /bin/sh 具备 POSIX 信号语义，无需覆盖；升级 /bin/sh 行为的场景不适用

## 查重差异
- exact_duplicate: false（index/doc/kv/drafts 无 SIGHUP-WIFSIGNALED 错误模式条目）
- causal_duplicate: false（E051 是 SIGSYS 未实现 syscall 信号，E043 是 toybox ash bashism/BASH_SOURCE，均不同根因）
- trigger_overlap: 低（E043/E051 同属 OHOS shell/信号域但错误面不同）
- combination_novelty: true —— "OHOS /bin/sh SIGHUP 信号语义缺失 + 编译期子进程 shell 覆盖" 为组合新知识
- boundary_novelty: true —— 适用范围=依赖子进程信号语义的构建工具；反例=纯 Linux

## 关联条目
- similar_to: E043（OHOS shell 语义差异族）、E051（OHOS 信号行为族）
- caused_by: E043（toybox 系 shell 行为差异）
- prerequisite_of: ninja 上游测试套件在 OHOS 全量通过