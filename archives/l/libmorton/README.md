# libmorton

C++ header-only 库，用于高效编解码 2D/3D 坐标的 Morton code（Z-order curve）。

## 基本信息

- 官方仓库: https://github.com/Forceflow/libmorton
- 许可证: MIT
- 构建系统: CMake（INTERFACE 目标 + CMake config + pkg-config 导出）
- 依赖: 仅标准 C++ 头文件，零运行时依赖
- 语言标准: C++11

## OpenHarmony 适配状态

| 版本 | 状态 | 日期 |
| --- | --- | --- |
| [0.2.12](./0.2.12/) | bootstrap（骨架已建立，待 adapt） | 2026-08-31 |

适配要点：header-only 库，`conan create` 无需编译产物，通过 test_package
消费者测试验证编码/解码往返正确性。上游 tag v0.2.12 对应 commit
`7923faa88d7e564020b2d5d408bf8c186ecbe363`。

## 参考

- 官方 tag: https://github.com/Forceflow/libmorton/releases/tag/v0.2.12