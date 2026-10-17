# libfreesrp

## 简介
libfreesrp 是 myriadrf 维护的 FreeSRP SDR（软件定义无线电）硬件客户端库，
基于 libusb-1.0 与 FreeSRP 板载 FX3/FPGA 通过用户态 USB 通信，提供设备枚举、
寄存器/参数读写（TX/RX LO 频率、采样率、带宽、增益、FIR 等）与流式 I/O 接口，
随库附带 freesrp-ctl（参数控制）与 freesrp-io（收发流）两个示例工具。

## 上游信息
- 仓库：https://github.com/myriadrf/libfreesrp
- 标签：`0.3.0`（commit 541e7bbfeff04f0a5759f12a2d2ae427f58e97cd）
- 协议：GPL-3.0-or-later
- 文档：https://github.com/myriadrf/libfreesrp/blob/master/README.md

## OHOS 适配
- C++11 + CMake（HarmonyOS PC aarch64 原生交叉编译，clang 15）
- 依赖：libusb/1.0.27（运行时链接）、boost/1.91.0.1.3（仅示例工具 header-only 组件）
- 产物：`libfreesrp.so.0`（含 .so 符号链接）+ `bin/freesrp-ctl` + `bin/freesrp-io`
- CMake 目标：`freesrp::freesrp`；pkg-config 名 `libfreesrp`
- libusb 定位与 boost 头文件注入通过配方 generate() 的 CMake cache 变量与
  conf cxxflags 完成，零源码补丁
- test_package 消费者测试 7 项断言（协议常量、异常派生、流式输出、
  list_connected() 无硬件安全路径），全部离线可跑

## 已知限制
- 实际硬件功能（设备连接、参数读写、收发流）需真实 FreeSRP 硬件 +
  libusb 用户态 USB 访问权限；无硬件环境下 `FreeSRP::list_connected()`
  返回空列表或抛 `ConnectionError`，属预期行为（E051 类平台限制）。

## 已发布版本
- 0.3.0
