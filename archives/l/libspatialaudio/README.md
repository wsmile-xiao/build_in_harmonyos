# libspatialaudio

开源、实时、跨平台的 C++ 空间音频编码/解码/渲染库，支持 Ambisonics（HOA，ACN/SN3D）、音频对象、直接扬声器馈送与双耳渲染。

## 主要功能

- **Ambisonics**：HOA 编解码（最高三阶），含心理声学优化（旋转、变焦、衰减）
- **Object-based Audio**：3D 空间中音源的编码与定位
- **Speaker Rendering**：扬声器流解码头路由到目标扬声器布局（5.1/7.1 等）
- **Binaural Rendering**：基于 HRTF 的双耳渲染（MIT HRTF 内建，支持 SOFA 文件）

## 依赖关系

- 编译依赖：CMake（构建系统）、C++14 编译器（harmonyos clang）
- 第三方依赖：无强制依赖；`MySofa` 为可选（`find_package(MySofa QUIET)`），未安装时自动降级为内建 MIT HRTF
- 运行时依赖：libc / libc++_shared / libm（OHOS 系统库）

## 许可证

LGPL-2.1-or-later（含 Proprietary 例外条款）

## OHOS 适配

- 构建系统：CMake，`CMAKE_SYSTEM_NAME` 为 HarmonyOS（OHOS 平台无 CMake platform module，按未知平台处理，编译器为 harmonyos clang 目标 aarch64-unknown-linux-ohos）
- 构建选项：`HAVE_MIT_HRTF=ON` 内建 MIT HRTF；`BUILD_SHARED_LIBS` 由 Conan `options.shared` 控制
- 已知差异：OHOS CMake 未生成 SONAME（未知平台模块），运行时以 `DT_NEEDED`/`RPATH` 校验链接一致性
- 上游测试：`tests/` 目录 4 个独立用例（CTest 注册），全量通过

## 参考资料

- 上游仓库：<https://github.com/videolabs/libspatialaudio>
- 空间音频规范：Google Spatial Audio RFC / IETF Ambisonics