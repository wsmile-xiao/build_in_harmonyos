# ViSP

## 简介
ViSP (Visual Servoing Platform) 是一个跨平台的 C++ 库，用于视觉跟踪和视觉伺服。它提供了多种视觉跟踪算法、相机标定工具和机器人视觉控制功能。

## OHOS 适配
- 需强制设置 SONAME 解决库名相对路径问题（补丁）
- 需添加 CMAKE_POSITION_INDEPENDENT_CODE=ON 解决 PIC 链接错误
- 需手动设置 AARCH64=ON 强制架构检测
- 使用 libc++ 编译和链接

## 依赖
- OpenMP
- 内置第三方库（AprilTag、pugixml、catch2）

## 功能验证
```bash
visp-compute-apriltag-poses --help
visp-calibrate-camera --help
```

## 参考
- 官方网站: https://visp.inria.fr
- 文档: https://visp.inria.fr/doc