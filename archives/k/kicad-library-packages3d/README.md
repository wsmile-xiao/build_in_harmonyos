# kicad-library-packages3d

KiCad 官方 3D 元件模型库：PCB 设计 3D 视图所需的电子元器件三维模型。

## 功能概述

- 上游仓库按封装族组织（105 个 `.3dshapes` 目录平铺于根目录），收录与
  KiCad 官方原理图符号库、封装库一一对应的元器件 3D 模型：
  - **`.step`** — ISO 10303-21 机械 CAD 模型，供 KiCad Pcbnew/封装编辑器
    3D 视图渲染，并可导入 FreeCAD/OpenSCAD 等 MCAD 软件做装配与外壳设计。
- **KiCad 10 起上游移除了全部 VRML（.wrl）模型**，10.0.5 归档仅含 7245 个
  .step 文件（另含 48 个辅助文件如 CREDITS.md；Ubuntu 再打包归档已移除
  不参与安装的 .fcstd 源文件）。
- 模型是可选资源：不安装不影响原理图与 PCB 布局功能，安装后可在 3D 视图
  中可视化元器件外观与整板装配效果。

## OHOS 适配

模型文件是平台无关数据资源，无需补丁或编译。Conan 包将全部 `.3dshapes`
家族目录安装到 `share/kicad/3dmodels/`（与上游 CMake 安装目录及 KiCad
标准数据路径一致），通过 `cpp_info.resdirs` 暴露资源目录，`runenv_info`
定义 `KICAD3D_MODEL_DIR` 环境变量。配方在 `build()` 阶段核对家族目录数、
目录名集合摘要与 .step/辅助文件计数，防止下载内容或目录结构静默漂移；
消费者测试全量校验包内 .step 文件 ISO-10303-21 头/尾结构。

## 依赖关系

无编译依赖和运行时依赖（EDA 应用侧消费时由 kicad 主程序解析）。

## 参考资料

- 上游仓库：https://gitlab.com/kicad/libraries/kicad-packages3D
- KiCad 官网：https://www.kicad.org/
