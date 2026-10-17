# roundup

POSIX shell 单元测试运行器：执行 roundup(5) 测试计划（任意 POSIX shell 编写的
test plan），逐用例沙箱隔离运行，输出 PASS/FAIL 与汇总，失败用例附 `set -x` 轨迹。

- 上游: https://github.com/bmizerany/roundup
- 本仓适配版本: 0.0.6（HarmonyOS PC / OHOS aarch64）
- 产物: 单文件 CLI 工具 `bin/roundup`（纯 shell，无编译产物、无动态库依赖）
- 运行时要求: /bin/sh（OHOS 为 mksh R59）、toybox/coreutils applets
