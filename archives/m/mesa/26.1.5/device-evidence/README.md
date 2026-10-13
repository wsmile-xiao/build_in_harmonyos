# 真机验证证据（DAYU200 · rule12）

- **设备**：润和 DAYU200-RK3568
- **系统**：OpenHarmony 6.0.0.47（API20，aarch64，64 位）
- **序列号**：`450100445634303332018f3e7d2dba00`
- **执行方式**：`bash automation/device_runner.sh run mesa_e2e <payload> 'sh ./run_on_device.sh'`

## 文件说明

本目录**只存放源码与证据，不存放预编译二进制**（遵循项目文件规范 R19：
"PR 中禁止包含预编译的 .so/.a/二进制文件，所有产物必须由 CI 从源码构建"）。
设备用例二进制由 `build_device_test.sh` 从 `consumer.c` 现场构建。

| 文件 | 说明 |
|------|------|
| `_device_evidence.json` | 执行器采集的证据（设备序列号、系统版本、退出码 0） |
| `device_run.txt` | 设备侧完整控制台输出（消费者端到端用例的真实结果） |
| `consumer.c` | 消费者用例源码（仅用 EGL/GLESv2 公共入口，可独立复核） |
| `build_device_test.sh` | 由 `consumer.c` 构建设备用例的**可复现**脚本 |
| `run_on_device.sh` | 设备侧启动脚本（busybox sh，无 awk/curl/python 依赖） |

## 被验证产物的可复核标识

真机日志 `device_run.txt` 中被执行的那个可执行文件，其身份由以下数值锚定
（二进制本身不入库，可由 `build_device_test.sh` 从本目录源码重建后比对）：

| 项目 | 数值 |
|------|------|
| 文件 | `mesa_device_e2e`（aarch64，`RUNPATH=$ORIGIN`） |
| 字节数 | `21312` |
| SHA-256 | `d0d14e0625a9e9d7281816418c363c336f81f0e8c6a1c1d21850e640fe981d3b` |

`run_on_device.sh` 在执行前会打印实际二进制的 `sha256sum` 与字节数，
便于与上表逐字比对，从而把"设备日志"与"仓库内源码"重新绑定。

## 执行命令（与 `_device_evidence.json` 的 `command` 字段一致）

```
cd /data/local/tmp/ohpc_test/mesa_e2e && sh ./run_on_device.sh
```

## 结论

消费者端到端用例在真机上 **ALL PASS（0 failure）**：EGL 1.5 初始化成功，
离屏 pbuffer + GLES2 渲染三角形，`glReadPixels` 回读得到
**2016 个绿色三角形像素 / 2080 个红色清屏像素**，
`GL_RENDERER = llvmpipe (LLVM 20.1.0, 128 bits)`，
`GL_VERSION = OpenGL ES 3.2 Mesa 26.1.5`。

> 日志中的 `kmsro: driver missing` / `failed to create dri2 screen` 属**预期行为**：
> 无 DRM master 时 Mesa 自动回退到 surfaceless + llvmpipe 软件光栅化路径，
> 用例正是在该路径上完成渲染与回读。
