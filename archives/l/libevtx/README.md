# libevtx

访问 Windows XML 事件日志（EVTX）格式的 C 库。

## 简介

libevtx 解析 Windows Event Log（.evtx）文件，提供记录枚举、时间/事件 ID/通道/计算机名/用户信息读取，以及 XML 导出能力。随包构建两个终端工具：

- **evtxinfo**：显示 EVTX 文件版本、记录数与恢复记录数等信息
- **evtxexport**：导出 EVTX 记录（文本/XML 格式）

## 官网

https://github.com/libyal/libevtx

## 许可证

LGPL-3.0-or-later

## 编译信息

| 版本 | 状态 | 编译日期 | 构建系统 | 补丁数 |
|------|------|----------|----------|--------|
| 20251118 | building | 2026-09-15 | autotools | 0 |

### 平台适配要点

| 问题编号 | 说明 | 解决方案 |
|----------|------|----------|
| E007 | GNU config.guess 不识别 HarmonyOS | conanfile.py 内联补丁 config.guess/config.sub |
| E011 | HMDFS 下 umask 077 导致临时目录不可写 | configure/config.status 内 umask 077 改 022 |

## 依赖

无外部依赖。内部捆绑 libyal 系列子库（libcerror、libcdata、libbfio、libfvalue 等）随包编译。
