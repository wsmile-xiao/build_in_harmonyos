# directx-headers

Official DirectX headers available under an open source license.

## 简介

Microsoft DirectX-Headers 是 Microsoft DirectX API 的开源头文件库，提供：
- DirectX 12 (D3D12) 头文件
- DXCore 头文件
- WSL/Linux 平台的 Windows API 桥接头文件

## 特性

- 纯头文件库，无运行时依赖
- 提供静态库：libDirectX-Guids.a, libd3dx12-format-properties.a
- 支持 WSL/Linux 平台的跨平台使用

## 编译信息

- 构建系统：meson
- License：MIT
- 最新版本：1.619.1

## 安装

使用 cmd-pkgs 预编译包：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- directx-headers 1.619.1
```

## 使用示例

```cpp
#include <directx/d3d12.h>
#include <dxguids/dxguids.h>

// 使用 DirectX 12 API
```

## 版本历史

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 1.619.1 | built | 2026-06-08 |

## 相关链接

- 官方仓库：https://github.com/microsoft/DirectX-Headers
- MIT License