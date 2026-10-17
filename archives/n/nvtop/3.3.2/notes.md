# nytop 3.3.2 OHOS 适配笔记

nytop 是 nvtop 3.3.2 的归档别名（用户原始输入为 "nytop"，对应 Syllo/nvtop 3.3.2）。
主要支持 NVIDIA/AMD/Intel/Apple/Qualcomm/Mali 等多种 GPU 厂商。

## OHOS 适配要点

- **构建系统**：CMake 3.18+ （上游 `project(nvtop VERSION 3.3.2 LANGUAGES C CXX)`）
- **依赖**：ncurses/6.5@ohpcd/stable（终端 TUI 库）
- **GPU 厂商栈**：OHOS 没有 NVIDIA/AMD/Intel/Mali 等驱动栈，因此通过 CMake 选项关闭所有 GPU_SUPPORT_*，只编译 TUI + 进程监控核心代码
- **编译器**：clang-15（OHOS 标准工具链），完全支持 nvtop 的 C11 代码
- **运行时**：通过 /proc /sys 读取进程信息，与 OHOS 兼容

## 关键 CMake 选项

所有 `*_SUPPORT=OFF`：
- NVIDIA_SUPPORT, AMDGPU_SUPPORT, INTEL_SUPPORT, APPLE_SUPPORT
- MSM_SUPPORT, PANFROST_SUPPORT, PANTHOR_SUPPORT
- ASCEND_SUPPORT, V3D_SUPPORT, TPU_SUPPORT
- ROCKCHIP_SUPPORT, METAX_SUPPORT, ENFLAME_SUPPORT

## 验证结果

- conan create: pass
- conan-verify G0-G4 + L2/L4/L5: pass
- test_package 烟雾测试 (`nvtop --version`): pass

## 备注

- nvtop 源码 GitHub 上游: https://github.com/Syllo/nvtop
- 3.3.2 是 2024-07 上游 release
- 制品仓发布名: `nvtop/3.3.2@ohpcd/stable`
---

**编译结束**: 2026-09-06 20:51
**最终状态**: built
