# libmicrodns

DNS-SD/mDNS 协议库，提供轻量级的 DNS 服务发现功能（VideoLAN 出品，VLC 的网络服务发现组件）。

## 功能
- mDNS (Multicast DNS) 支持
- DNS-SD (DNS Service Discovery) 支持
- 轻量级 C99 实现，适合嵌入式环境

## 依赖
- 无（POSIX/OHOS 目标零外部依赖）
- Windows 目标需系统库 ws2_32、iphlpapi

## 适配状态
- 版本: 0.2.0
- 状态: built（真机 shadow CI 待执行）
- 构建系统: meson
- 补丁: 0 个（无源码修改）
- 上游测试: 1/1（meson test，历史真机实测）

## 关键发现
- meson 构建系统需要完整路径设置编译器/ar 环境变量（配方经 profile compiler_executables + machine file 注入覆盖）
- 适配版 conan 将 os=OHOS 映射为 meson system `harmonyos`；上游 meson.build 仅特判 Windows，本库无需平台补丁
- OHOS 设备上需强制 `-fuse-ld=ld.lld`（lld 通用驱动依赖 libxml2.so.16，不在动态链接器搜索路径）
