# kicad-demos

KiCad 官方演示工程集合：原理图、PCB 布局、仿真工程与 Python 脚本示例。

## 功能概述

- 18 个官方演示工程：复杂层次原理图（complex_hierarchy）、多通道混音器
  （multichannel）、视频板（video）、VME FPGA 板（vme-wren）、Jetson AGX
  Thor 载板（jetson-agx-thor-baseboard）、树莓派 CM5 最小系统
  （cm5_minima）、电子管放大器（ecc83）等。
- SPICE 仿真工程子集（simulation/：放大器、Class-D、电源、IBIS 模型等）。
- KiCad Python API 脚本示例（python_scripts_examples/）。

## OHOS 适配

演示工程是平台无关数据资源，无需补丁或编译（上游 CMakeLists 仅
install(DIRECTORY)）。Conan 包把 711 个工程文件安装到
`share/kicad/demos/`，通过 `cpp_info.resdirs` 暴露资源目录，
`runenv_info` 定义 `KICAD_DEMOS_DIR` 环境变量。消费者测试用自研
s-expression 解析器全量解析包内 .kicad_pcb/.kicad_sch 头部并校验
.kicad_pro JSON 结构。

## 依赖关系

无编译依赖和运行时依赖（EDA 应用侧消费时由 kicad 主程序解析）。

## 参考资料

- KiCad 源码仓库（含 demos 目录）：https://gitlab.com/kicad/code/kicad
- GitHub 镜像：https://github.com/KiCad/kicad
- KiCad 官网：https://www.kicad.org/
