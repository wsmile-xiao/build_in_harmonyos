# libdrm - Direct Rendering Manager Library

## 简介
libdrm 是 Direct Rendering Manager (DRM) 的用户空间库，为 Linux/OpenHarmony 系统提供对图形硬件的直接访问接口。它是 Mesa/OpenGL 的底层依赖。

## 功能
- 提供 DRM 设备的访问接口
- 支持多种 GPU 驱动：
  - AMDGPU (AMD 显卡)
  - Radeon (AMD 旧显卡)
  - Nouveau (NVIDIA 显卡)
  - Freedreno (Qualcomm Adreno)
  - Etnaviv ( Vivante GPU)
  - VC4 (Broadcom VideoCore IV)

## 编译版本
- 2.4.133 (2026-04-30)

## 安装
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libdrm 2.4.133
```

## 使用
```bash
# pkg-config 验证
pkg-config --modversion libdrm

# 编译时链接
pkg-config --cflags --libs libdrm
```

## 依赖
- 无外部依赖（仅依赖系统库）

## 许可证
MIT License

## 更多信息
- 官方网站: https://dri.freedesktop.org/wiki/
- 源码: https://gitlab.freedesktop.org/mesa/drm