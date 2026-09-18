# libforensic1394

libforensic1394 是一个通过 IEEE 1394（"FireWire"）接口对本机内存进行实时取证的 C 库。
它利用 FireWire 的 DMA 能力：先向对端设备呈现一个 SBP-2 单元目录，再直接读写对端物理内存，
常用于冷启动内存获取与数字取证工具链。

- 上游官网: <https://freddie.witherden.org/tools/libforensic1394/>
- 源码仓库: <https://github.com/FreddieWitherden/libforensic1394>
- 许可证: LGPL-3.0-or-later
- 最新发布: 0.2（2010-10-05；master 分支此后无新版本标签）

## 功能概述

- 支持 Linux 2.6.22+ 的 "Juju" 协议栈（`/dev/fw*` + firewire-cdev ioctl 用户态接口）
- 支持 Mac OS X 的 IOKit 后端（`src/macosx/iokit.c`，本仓库不构建该分支）
- 呈现 SBP-2 单元目录以获得对目标机的物理内存访问
- 提供面向批量传输的向量化 API（`forensic1394_read_device_v` / `write_device_v`）
- 提供纯 Python（ctypes）绑定，随源码 `python/` 目录分发

对外 API 仅 24 个函数 + 1 个结果枚举，核心流程为：

```c
bus = forensic1394_alloc();
forensic1394_enable_sbp2(bus);          /* 需要本地 Juju 节点 */
dev = forensic1394_get_devices(bus, NULL, NULL);
forensic1394_open_device(dev[0]);
forensic1394_read_device(dev[0], addr, 512, data);
forensic1394_close_device(dev[0]);
forensic1394_destroy(bus);
```

## OHOS 适配

本库在 OHOS 上走 Linux/Juju 后端，适配点是**平台识别**而非功能移植：

| 事项 | 结论 |
|------|------|
| 构建系统 | CMake（上游 2.8 起），配方用 `CMakeToolchain` + `CMAKE_POLICY_VERSION_MINIMUM=3.5` 兼容 CMake 4 |
| 平台分支 | OHOS 上 `CMAKE_SYSTEM_NAME=HarmonyOS`，需把上游 `MATCHES "Linux"` 扩为同时匹配 HarmonyOS（补丁 0001，1 行） |
| firewire 用户态接口 | OHOS SDK sysroot 自带 `linux/firewire-cdev.h`（`FW_CDEV_VERSION 3`）与 `linux/firewire-constants.h`，后端零改动编译 |
| 内核能力 | 运行期依赖 Juju 栈（`/dev/fw*` 与 `/sys/bus/firewire/...`）；无控制器时 `get_devices` 返回空列表、`enable_sbp2` 返回 `IO_ERROR`，属上游文档行为 |
| 依赖 | 无第三方依赖（仅 libc：`glob`/`poll`/`ioctl`），无 `tool_requires` |
| 已知差异 | 无（未发现需要 stub 的平台接口） |

## 依赖关系

- 编译依赖：无（只需 C 工具链与 CMake）
- 运行依赖：Linux 内核 Juju FireWire 栈；普通用户访问需要设备节点权限
- 下游依赖示例：取证工具链（如 bulk_extractor 系）可按需引用 `libforensic1394/0.2`

## 参考资料

- 项目主页与论文：<https://freddie.witherden.org/tools/libforensic1394/>
- FireWire Juju 迁移说明：<https://ieee1394.wiki.kernel.org/index.php/Juju_Migration>
- 同类适配先例（Juju 后端在 OHOS 编译）：`archives/l/libdc1394/2.2.7`

## 版本索引

见 [manifest.yaml](manifest.yaml)。
