# miruo — KLab 终端交互流量监控工具

miruo 是 KLab 开发的终端交互流量监控 CLI（tcpdump 类工具）：用 libpcap
抓取 telnet/SSH 等终端流量，统计终端窗口尺寸（终端协商的 NAWS 窗口）与
网络吞吐的关系，主要用于测量远程终端的响应性能。C 语言，autotools 构建，
产物为单一 `miruo` 二进制。

## 功能概述

- 基于 libpcap 的终端流量监控，默认监听所有接口（可用 `-i` 指定）
- 统计终端窗口尺寸变化与吞吐（键入响应延迟视角）
- `-t` 指定监控时长（秒），超时后打印统计
- `-V` 打印版本，`-h` 打印用法
- 运行需要 root 权限（raw socket 抓包）

## OHOS 适配要点

- **补丁 0001（E011）**：configure 创建 config.status 临时目录的
  `umask 077` → `umask 022`。HMDFS 强制目录 setgid，`umask 077 &&
  mktemp -d` 产生属主不可写的 `drwx--S---` 目录，config.status 无法创建
  subs1.awk 报 "can't create ./confXXXX/subs1.awk: Permission denied"
- **AC_PROG_CC 不探测 clang（无需 patch）**：autoconf 2.67 的探测列表
  只有 gcc/cc/cl.exe；profile 的 `tools.build:compiler_executables` 经
  AutotoolsToolchain 生成 `CC=clang`，configure 直接采用
- **sbin → bin 重定向（无需 patch）**：上游 `sbin_PROGRAMS` 装到 sbin/，
  配方用 `--sbindir=${prefix}/bin` 重定向到 conan 惯例的 bin/
- **make -j1（E074）**：HMDFS 上并行 make 触发 jobserver fifo EPERM
- **/proc/self/statm**：miruo 运行时读自身内存，HarmonyOS PC 已验证可读
- **上游打包缺陷（不 patch）**：0.9.6b tag 的 configure 未重新生成，
  内嵌版本串仍是 0.9.6a，`miruo -V` 输出 "miruo version 0.9.6a"

## 源码

- 上游仓库：https://github.com/KLab/miruo
- 本次使用：0.9.6b tag tarball
  （sha256 `0b31a5bde5b0e92a245611a8e671cec3d330686316691daeb1de76360d2fa5f1`）
- 许可证：GPL-3.0-or-later
- 依赖：libpcap（conan 包 libpcap/1.10.6，静态链入）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.9.6b | built | 2026-09-20，1 补丁（E011），上游测试 0，OHOS 专项测试 9 断言 |
