# ostra

## 简介
Ostra 是一个本地服务器与监控平台仓库。本档案先把 `components/ostra-sysctl` 组件做成 Conan 包：
它是一个 C17 的只读系统监控工具，输出人类可读摘要或 JSON。

## OHOS 适配
- 构建系统：CMake
- 产物：`ostra-sysctl` 可执行文件
- 外部依赖：无
- 风险：实现读取 `/proc`、`/sys`、`sysinfo`、`getloadavg` 等 Linux 接口，HarmonyOS 真机运行时可用性待确认

## 依赖
- 无编译依赖
- 无运行时依赖（除系统接口）

## 功能验证
```bash
ostra-sysctl --help
ostra-sysctl --json
```

## 参考
- 仓库: https://github.com/tej-1916/ostra
- 组件: `components/ostra-sysctl`
