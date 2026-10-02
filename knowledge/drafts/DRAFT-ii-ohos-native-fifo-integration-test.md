# 【知识库扩展】feat(ii): 2.0 适配 HarmonyOS PC

## 问题

Suckless `ii` 2.0 使用 POSIX socket 与 FIFO 实现 IRC 客户端，没有上游测试套件或 Makefile `test` 目标。部分 HarmonyOS PC 服务环境中，运行 UID 没有 passwd 记录，原版程序会在解析参数前因 `getpwuid()` 失败退出。

## 适用范围

HarmonyOS PC 上以 POSIX socket、`mkfifo` 和文件系统 FIFO 为核心接口，且缺少自动化测试的 C 命令行程序；运行环境可能限制 socket/FIFO 创建并缺少 passwd 条目。

## 验证方法

通过 Conan 补丁在 `getpwuid()` 无记录时提供默认 nick `ii` 和有效 `HOME`（缺失或非绝对路径时使用 `/tmp`）；在 HarmonyOS PC 启动目标二进制并传入未知选项，验证 fallback 后的原生启动、usage 输出与退出状态。已知 CI 沙箱禁止测试绑定 TCP/UNIX 域套接字及创建 FIFO，因此不在该环境模拟 IRC/FIFO 会话。交叉编译场景通过 Conan `can_run()` 跳过目标程序运行测试。

## 经验

针对无 passwd 服务 UID 的环境，在上游行为周围增加最小 fallback 补丁；若目标沙箱同时拒绝 socket/FIFO 创建，则保留可执行文件启动与 usage 冒烟检查。该检查不覆盖 IRC/FIFO 会话。

## 来源

- 上游：<https://git.suckless.org/ii>
- 适配版本：`ii/2.0`
- PR：<https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/13685>
- 实现提交：`ae2ea3a9dfa030c7933795bae60c57ad6fce1279`
