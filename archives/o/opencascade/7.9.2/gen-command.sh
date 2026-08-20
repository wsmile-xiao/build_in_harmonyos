#!/bin/bash
set -euo pipefail
# opencascade 7.9.2 构建 cmake 定义（参照 7.9.3 的 gen-command.sh 适配逻辑移植）
#
# 说明：7.9.2 由 conanfile.py 的 CMakeToolchain 汇总以下变量，清单如下——
# 重生成/排查时照这个核对，别凭 conanfile.py 反推，漏一个 flag 就静默少一项能力。

# 模块开关（沿用 7.9.3 已评审方案）
BUILD_MODULE_FoundationClasses=ON
BUILD_MODULE_ModelingData=ON
BUILD_MODULE_ModelingAlgorithms=ON
BUILD_MODULE_ApplicationFramework=ON
BUILD_MODULE_DataExchange=ON
BUILD_MODULE_Visualization=OFF
BUILD_MODULE_Draw=OFF
BUILD_MODULE_DETools=OFF

# 依赖全关（WebGL/XLib 等桌面/Windows 图形栈，鸿蒙不适用）
USE_OPENGL=OFF
USE_GLES2=OFF
USE_XLIB=OFF
USE_VTK=OFF
USE_TK=OFF
USE_TCL=OFF
USE_D3D=OFF
USE_OPENVR=OFF
USE_FREEIMAGE=OFF
USE_FFMPEG=OFF
USE_FREETYPE=OFF
USE_DRACO=OFF
USE_TBB=OFF
USE_RAPIDJSON=OFF
USE_EIGEN=OFF

# 安装/构建布局
CMAKE_INSTALL_LIBDIR=lib
INSTALL_DIR_INCLUDE=include/opencascade
BUILD_DOC_Overview=OFF
INSTALL_TEST_CASES=OFF
INSTALL_SAMPLES=OFF
# 动态库（shared），与 options.shared 联动
BUILD_LIBRARY_TYPE={shared:Shared|Static}
