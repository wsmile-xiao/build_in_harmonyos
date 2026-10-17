# Open CASCADE Technology (OCCT)

工业级**三维几何内核**——CAD 软件的核心引擎。做实体建模、布尔运算（两个零件求交/相减）、
以及 STEP/IGES/STL/VRML/glTF/OBJ/PLY 等 CAD 数据格式的读写。

- 上游：https://dev.opencascade.org/  （源码 https://github.com/Open-Cascade-SAS/OCCT）
- 许可证：LGPL-2.1-only-with-exception

## 鸿蒙 PC 适配范围

**已启用**：几何内核 + 数据交换
`FoundationClasses`、`ModelingData`、`ModelingAlgorithms`、`ApplicationFramework`、`DataExchange`

**未启用**：`Visualization`、`Draw`、`DETools`，以及 OpenGL/GLES/XLib/VTK/TK/TCL/D3D/OpenVR

未启用的部分依赖桌面图形栈或 Windows 专有 API，在鸿蒙 PC 上不适用。
需要可视化的消费方（如 cadquery-ocp 的完整功能）还需要 VTK，目前不具备条件。
