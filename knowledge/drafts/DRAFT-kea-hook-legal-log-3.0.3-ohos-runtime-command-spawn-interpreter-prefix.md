# DRAFT-kea-hook-legal-log-3.0.3: OHOS 内核拒 shebang execve 的运行时层——fork+execve 型命令 spawn 经 /bin/sh 路由

- **条目 ID**: `DRAFT-kea-hook-legal-log-3.0.3-ohos-runtime-command-spawn-interpreter-prefix`
- **严重度**: 2（🟡 中等）
- **类别**: cxx, runtime, spawn, shell, gtest, portability, ohos
- **触发工具/阶段**: cxx | conan | gtest — test / runtime
- **来源**: kea-hook-legal-log 3.0.3 适配（feat/kea-hook-legal-log-3.0.3，OHOS PC aarch64）
- **路径**: Path B（知识库扩展）
- **关联**: [[DRAFT-kea-hook-ping-check-3.0.3-ohos-configure-script-execve]]（configure 期同源问题的三层修法；本条目是其运行时层补充）

## 症状

kea-hook-legal-log 3.0.3 的 `dhcp-forensic-log-tests` 套件在 OHOS 真机上，
RotatingFileTest 的 prerotateActions / postrotateActions / prerotateAndPostrotateActions
三用例 FAIL：`waitForFile` 等到超时，脚本副作用文件（`<日志名>-prerotate-completed`）
始终不出现——而上游测试就是靠这些文件的存在性断言「轮转脚本确实执行了」。

## 根因

1. **内核层**（与 configure 期草稿同源）：OHOS PC 内核在 execve 系统调用层拒绝
   带 shebang 的脚本执行，与文件可执行位无关；`sh 脚本` 能跑，直接 execve 脚本
   路径报 EACCES。
2. **运行时 spawn 形态**：`RotatingFile::rotateFiles()` 把用户配置的
   prerotate/postrotate 命令交给 `ProcessSpawn`（`src/lib/asiolink/
   process_spawn.cc`）：`ProcessSpawnImpl::spawn()` = fork + **execve** +
   `_exit(EXIT_FAILURE)`，**没有任何 shell 回退**。命令是脚本时，OHOS 上子进程
   execve 立即失败并 `_exit`；父进程是 ASYNC 模式，不感知失败。上游测试的
   `forensic_prerotate_test.sh` / `forensic_postrotate_test.sh`（`#!/bin/sh` +
   `cp "${1}" "${1}-prerotate-completed"`）正是脚本。
3. **与 configure 期问题的关键差异**：configure 期有 meson 的 `run_command` /
   `configure_file(command:)` 间接层，可以改脚本变量或命令数组；运行时 spawn
   的调用点在上游 C++ 源码里，修复必须落在拥有 spawn 的那段代码上，且要用
   编译期守卫保住 glibc/Linux（上游 CI 环境）的原有路径。

## 最小复现

```cpp
// src/hooks/dhcp/forensic_log/rotating_file.cc（rotateFiles，轮转触发时）
if (!prerotate_.empty()) {
    ProcessArgs args;
    args.push_back(getFileName());
    ProcessSpawn process(ProcessSpawn::ASYNC, prerotate_, args);  // 直接 execve 脚本
    process.spawn(true);
}
```

OHOS 真机上 gtest 三用例必 FAIL（脚本副作用文件不出现）；glibc/Linux 上正常。

## 已试过的失败方案

1. 只给脚本 chmod +x：与执行位无关，无效（同 configure 期结论）。
2. 在测试夹具层绕过（不跑 spawn 用例）：等于裁剪上游用例，不可接受。

## 解决方案

在拥有 spawn 的代码里，用 musl-Linux 编译期守卫把命令经 `/bin/sh` 路由：

```cpp
if (!prerotate_.empty()) {
    ProcessArgs args;
#if defined(__linux__) && !defined(__GLIBC__)
    args.push_back(prerotate_);       // 脚本路径成为 $1，原 argv 语义不变
    args.push_back(getFileName());
    ProcessSpawn process(ProcessSpawn::ASYNC, "/bin/sh", args);
#else
    args.push_back(getFileName());    // glibc/Linux 保留原直接 execve 路径
    ProcessSpawn process(ProcessSpawn::ASYNC, prerotate_, args);
#endif
    process.spawn(true);
}
```

要点：

- **命令本身压入参数**：`/bin/sh <脚本> <原参数...>` 使脚本内 `$1` 与直接
  execve 完全一致（本插件的测试脚本用 `${1}` 取轮转文件名，语义逐字节保持）。
- **守卫用 `!__GLIBC__` 而非平台宏**：musl 系 Linux 才走 sh 路由，glibc/Linux
  （上游 CI）保留直接 execve——非脚本的可执行命令（ELF 二进制）在那里照常工作；
  与家族头文件冲突补丁（0002）的守卫约定一致，平台宏守卫 pending 合规。
- **改完 grep 全树其余 spawn 点**：`ProcessSpawn` 在 asiolink 库内被多处使用，
  本插件的适配面只有 rotating_file 的 prerotate/postrotate 两处；同形态调用
  可能藏在相邻组件，声明补丁完成前先扫净。
- **用上游真实执行脚本的用例验收**：三个 spawn 用例的副作用文件断言本身就是
  验证（waitForFile 成功 = sh 路由生效），无需另写测试。

## 验证

kea-hook-legal-log 3.0.3 真机：补丁 0005 应用后 `meson test
dhcp-forensic-log-tests dhcp-forensic-log-libloadtests` 两套件全绿（rotating_file
19 例含 3 个 spawn 用例全 PASSED，脚本副作用文件按时出现）；glibc/Linux 分支
未受扰动（守卫外路径逐字节保持上游原样）。
