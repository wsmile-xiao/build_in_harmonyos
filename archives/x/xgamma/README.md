# xgamma

xgamma 是 X Window System 的 gamma/亮度调节命令行工具：通过
XFree86-VidModeExtension 查询（不带 gamma 参数时）或设置指定屏幕的
红/绿/蓝 gamma 值。本仓库提供其在 HarmonyOS PC (aarch64) 上的 Conan 配方。

## 官网

https://gitlab.freedesktop.org/xorg/app/xgamma

## 许可证

MIT

## 特性

- `-gamma f.f` 同时设置 R/G/B；`-rgamma` / `-ggamma` / `-bgamma` 分量独立设置
- 不带 gamma 参数时为**只读查询**，打印当前 `-> Red / Green / Blue` 后退出
- gamma 取值域 `[0.1, 10.0]`（源码 `GAMMA_MIN` / `GAMMA_MAX`）越界即拒绝
- `-display` / `-screen` 指定目标；`-quiet` 抑制数值输出
- `-version` / `-help` 无需 X server 即可运行（供无头验证）

## 编译信息

| 版本 | 状态 | 编译日期 | 构建系统 | 补丁数 |
|------|------|----------|----------|--------|
| 1.0.8 | built | 2026-09-24 | autotools | 0 |

## 已知平台问题

- 完整运行需要 X server 且服务端提供 XFree86-VidModeExtension 2.0+；
  无头环境（CI / 真机无 X）下仅能验证命令行解析与取值域校验等不连服务的分支。
- 设置 gamma 是**改动显示服务器状态**的副作用操作，验证脚本刻意不触达该路径
  （详见 `1.0.8/notes.md` 的安全说明）。
