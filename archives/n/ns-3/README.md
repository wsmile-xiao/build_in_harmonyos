# ns-3

ns-3 是 nsnam 社区开发的离散事件网络仿真器（Discrete-Event Network Simulator），
用于网络协议与系统的研究与教学。核心特性：事件调度内核（core）、节点/信道/设备抽象
（network）、丰富的协议栈模块（internet/applications/wifi/lte 等）与可视化/统计工具。

- 官方主页: https://www.nsnam.org/
- 上游仓库: https://github.com/nsnam/ns-3-dev-git
- 许可证: GPL-2.0-only
- 构建系统: CMake（自 3.4x 起 waf 已废弃，需 CMake ≥ 3.25）

## 本仓适配

| 版本 | 状态 | 说明 |
|------|------|------|
| 3.48 | conan 配方 | 模块裁剪 core+network+point-to-point（C++20）；可选依赖（GSL/GTK3/SQLite/Eigen/libxml2）与 Python 绑定全部关闭；4 个补丁适配 HarmonyOS：Clang 最低版本 17→15、C++ 标准门槛 23→20、write_lock 平台判定、Ipv6Address operator<=> 兼容 libc++15；并补 SONAME 链接标志修正共享库 DT_NEEDED |

## 适配要点

- 编译目标最小化：`NS3_ENABLED_MODULES=core;network;point-to-point`（依赖闭包自动递归补全，含 stats）
- C++20：ns-3 3.48 源码需 C++20，顶层门槛为 C++23，补丁降门槛并覆盖 profile 的 `cppstd=17`
- 零外部 conan 依赖：ns-3 的可选依赖均为 QUIET 查找、缺省自动禁用
- 共享库 SONAME：显式补链接标志，修正 HarmonyOS 下 DT_NEEDED 记绝对路径导致的重复加载
- test_package 冒烟：2 节点 point-to-point 链路实际送达 1 个 100 字节数据包