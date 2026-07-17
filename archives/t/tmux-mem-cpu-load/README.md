# tmux-mem-cpu-load

CPU, RAM, and load monitor for use with tmux.

## 版本
- 3.8.3

## 描述
tmux-mem-cpu-load 是一个用于 tmux 状态栏的 CPU、内存和负载监控工具。

## 上游
- https://github.com/thewtex/tmux-mem-cpu-load

## 适配说明
- 添加 OHOS/HarmonyOS 平台检测，复用 Linux 源码路径
- 编译通过，test_package 消费者测试通过（上游 21 个 CTest 测试因交叉编译限制无法在构建机执行）