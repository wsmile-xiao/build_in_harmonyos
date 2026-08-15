# accel-config

Intel DSA/IAA 硬件加速器配置工具与用户态库（libaccel-config）。

- 上游仓库：https://github.com/intel/idxd-config
- 语言：C
- 构建系统：Autotools（configure.ac + Makefile.am + autogen.sh）
- 许可证：GPL-2.0（libaccel-config 为 LGPL-2.1）

## 内容

| 产物 | 说明 |
|------|------|
| libaccel-config | DSA/IAA 设备配置用户态共享库（SONAME libaccel-config.so.1） |
| accel-config CLI | 设备/工作组/队列/引擎配置命令行工具 |
| 头文件 | accel-config/libaccel_config.h |
| pkg-config | libaccel-config.pc（Version 4.1.9） |

## 适配说明（路径 B 知识库扩展）

- 可移植层（纯用户态）：JSON 配置解析、util 工具层、只读 API
- Linux 专有层（可编译、无设备不可验证）：sysfs 枚举/属性、bind/unbind、
  /dev/dsa、IDXD_SCMD_* ioctl 状态码
- 硬件强依赖：上游测试全部需要真实 DSA/IAA（本机无硬件，记录为
  hardware-unrunnable，未伪造通过）
- 安全验证：ACCFG_SYSFS_ROOT 环境变量注入 sysfs 根（默认 /sys），
  通过仓库外 mock sysfs 树验证只读枚举；test_package 消费者测试调用只读 API

## 版本

- 4.1.9（当前）
