#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name opencascade --version 7.9.3 --build-system cmake --cmake-toolchain conan --test-lang cpp --sign-so --libs TKernel,TKMath,TKG2d,TKG3d,TKGeomBase,TKBRep,TKGeomAlgo,TKTopAlgo,TKPrim,TKBO,TKBool,TKHLR,TKFillet,TKOffset,TKFeat,TKMesh,TKXMesh,TKShHealing,TKCDF,TKLCAF,TKCAF,TKBinL,TKXmlL,TKBin,TKXml,TKStdL,TKStd,TKTObj,TKBinTObj,TKXmlTObj,TKVCAF,TKDE,TKXSBase,TKDESTEP,TKDEIGES,TKDESTL,TKDEVRML,TKDECascade,TKDEOBJ,TKDEGLTF,TKDEPLY,TKXCAF,TKXmlXCAF,TKBinXCAF,TKRWMesh --include-dirs include,include/opencascade --source-url https://github.com/Open-Cascade-SAS/OCCT/archive/refs/tags/V7_9_3.tar.gz --sha256 5ecf094ec6b12d5413dfb851d8c3590c354058aee556e32e408bdfbf8c357d57 --cmake-def BUILD_MODULE_FoundationClasses=ON --cmake-def BUILD_MODULE_ModelingData=ON --cmake-def BUILD_MODULE_ModelingAlgorithms=ON --cmake-def BUILD_MODULE_ApplicationFramework=ON --cmake-def BUILD_MODULE_DataExchange=ON --cmake-def BUILD_MODULE_Visualization=OFF --cmake-def BUILD_MODULE_Draw=OFF --cmake-def BUILD_MODULE_DETools=OFF --cmake-def USE_OPENGL=OFF --cmake-def USE_GLES2=OFF --cmake-def USE_XLIB=OFF --cmake-def USE_VTK=OFF --cmake-def USE_TK=OFF --cmake-def USE_TCL=OFF --cmake-def USE_D3D=OFF --cmake-def USE_OPENVR=OFF --cmake-def USE_FREEIMAGE=OFF --cmake-def USE_FFMPEG=OFF --cmake-def USE_FREETYPE=OFF --cmake-def USE_DRACO=OFF --cmake-def USE_TBB=OFF --cmake-def USE_RAPIDJSON=OFF --cmake-def USE_EIGEN=OFF --cmake-def 'BUILD_LIBRARY_TYPE={shared:Shared|Static}' --cmake-def BUILD_DOC_Overview=OFF --cmake-def INSTALL_TEST_CASES=OFF --cmake-def INSTALL_DIR_INCLUDE=include/opencascade --cmake-def INSTALL_SAMPLES=OFF --out <输出根目录>
