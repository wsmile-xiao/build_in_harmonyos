# zps

`zps` 是一个小而专的**僵尸进程（zombie / defunct process）列表与回收工具**：
扫描 `/proc` 列出进程并标出 `Z` 状态，再把信号发给僵尸进程的父进程完成回收。

## 功能概述

- `zps`（无参数）— 只列出僵尸进程；`-a` 列出全部用户态进程
- `-r` / `--reap` — 回收僵尸：向僵尸父进程发送信号（默认 `SIGTERM`）
- `-s <sig>` / `--signal` — 指定信号（`9` / `15` / `SIGTERM` / `term` 等写法均可）；必须与 `-r`/`-p` 同用
- `-p` / `--prompt` — 交互式选择要回收的僵尸（编号，支持管道输入）
- `-q` / `--quiet` — 静默回收（stdout/stderr 丢弃）
- `-n` / `--no-color` — 关闭 ANSI 颜色（非 TTY 时自动关闭）
- `-v` / `-h` — 版本 / 帮助

输出为 `PID PPID STATE NAME COMMAND` 五列，僵尸行以红色高亮（TTY 下）。

## OHOS 适配

| 项目 | 结论 |
|------|------|
| 源码补丁 | **0**（`patches: {}`）——`/proc` 扫描、`stat`/`cmdline` 解析、`kill()` 在 HarmonyOS 上原生可用 |
| 构建 | conan `CMakeToolchain` + `ci/conan/profiles/ohos-aarch64`；`os=OHOS` → `CMAKE_SYSTEM_NAME=HarmonyOS`（本机 OHOS 定制 cmake 仅告警并继续，不阻塞） |
| 产物 | 单一可执行文件 `bin/zps`（aarch64-linux-ohos / musl），`DT_NEEDED` 仅系统 `libc.so`，无 RPATH |
| 打包 | `settings.os == "OHOS"` 时对 `bin/` 下 ELF 重新自签名（剥旧 `.codesign` + `binary-sign-tool -selfSign 1`）并恢复 `0755` 执行位 |
| 已知差异 | 上游覆盖率步骤依赖 GNU 工具链（`gcc`/`gcov`），OHOS 不可复现 → 报告标记 NA；`/proc/<pid>` 对他用户进程多为 `Permission denied`，工具静默跳过（预期行为） |

## 依赖关系

- 编译依赖：**无**（纯 POSIX C；conan 配方零 `requires`）
- 运行依赖：仅系统 `libc.so`

## 上游测试

- 入口 `scripts/test.sh`（GitHub Actions `ci.yml` 调用），bash `&&` 链冒烟测试，无用例注册表
- 实机复现脚本：`2.0.0/run_upstream_tests.sh`（阶段 A 原样跑上游脚本；阶段 B 逐用例复算）
- 实机结果：17 项 = 12 通过 / 0 失败 / 3 跳过（上游链短路）/ 2 不适用（无 gcov、未启用 codecov）；
  另有 2 条**补全用例**（`-r -s CHLD`、`-r -s 9|15|SIGTERM|term`）通过。详见 `2.0.0/reports/`。

## 参考资料

- 上游仓库：<https://github.com/orhun/zps>
- 上游手册：`man/zps.1`
- 版本：2.0.0（2024-01-19，GPL-3.0-only）
