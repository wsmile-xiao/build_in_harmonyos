# yank 1.3.0 适配笔记

## 任务来源

- 平台任务 contrib-12257（开源鸿蒙PC专项积分赛），分支 `feat/yank-1.3.0`，2026-09-20 认领
- 上游：https://github.com/mptre/yank （1713 stars，非 fork，tag v1.3.0 实拉核验存在）
- 语言实测（R47 lang-preflight）：C（单源文件 yank.c，100%）

## 选库核验（§3.2 否决线）

1. 他人已移植：main 档案与同源反查均无；制品仓无 yank（设备实测）
2. 语言/构建生态：C 单文件直接编译
3. 难度定级：A（零依赖零补丁）

## 上游测试清点（R51）

- 上游无测试套件（全仓 6 个条目：yank.c/Makefile/README/CHANGELOG/LICENSE/yank.1）
- 验证由 test_package 承担（3 项断言）

## 平台适配要点

- **BSD Makefile 不可用**：`${.CURDIR}` 语法 GNU make 无法解析；`install -s` 的 strip 产物被平台执行策略拒绝（yices 实证）→ 配方直接编译
- **YANKCMD 默认 xsel 平台不存在**：保留上游默认（仅影响无显式命令的调用；yank 支持环境变量覆盖）
## 平台适配要点

- **BSD Makefile 不可用**：`${.CURDIR}` 语法 GNU make 无法解析；`install -s` 的 strip 产物被平台执行策略拒绝（yices 实证）→ 配方直接编译
- **YANKCMD 默认 xsel 平台不存在**：保留上游默认（仅影响无显式命令的调用；yank 支持环境变量覆盖）
- **LD_LIBRARY_PATH 盾**
- **交互式 CLI 的测试陷阱（实证）**：yank UI 模式忽略 SIGTERM（toybox timeout 默认 TERM 杀不死，必须 -s KILL）；musl regcomp 把 `[` 当字面量（非法正则用例不成立，已改未知选项用例）；worker 会话有控制终端时 /dev/tty 可打开、UI 会真等按键——测试只走 UI 之前的探针路径

## 编译结束

设备实机验证（2026-09-20）：conan-verify G0-G4+L2/L4/L5 全 PASS（RC=0）；CI 同源闸门 L0/L1/L4/L5 全 pass、Pass rate 100%；test_package 3 项断言全过
