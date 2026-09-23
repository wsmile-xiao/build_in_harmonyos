# E-draft: coin3 4.0.7 — CMake4/Boost shim + gl4es 消费侧 + 未知平台 SONAME

## 问题
1. CMake 4.x 移除 FindBoost.cmake，且 conan boost/1.90.0 包未提供 BoostConfig.cmake，
   导致 `find_package(Boost REQUIRED)` 直接失败（"Could not find a package configuration
   file provided by Boost"）。
2. OHOS 无桌面 GL 立即模式符号（sysroot libGLv4.so 不导出 glBegin/glEnd/glColor3f/
   glVertex3f/glTexCoord2f），依赖桌面 GL 固定管线的库（如 Open Inventor 系 coin3）
   链接时 undefined reference；gl4es 可提供 libGL.so，但其 GL/EGL 头引用 X11/Xlib.h
   （OHOS 无 X11），直接注入 include 会编译失败。
3. CMake 不识别 HarmonyOS 平台（无 Platform/HarmonyOS 模块）时
   CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG 为空 → 产物缺 DT_SONAME →
   W3/L5 soname_gate_failed。

## 根因
- CMake 4.x 移除 FindBoost；conan boost 二进制包无 cmake config 文件。
- OHOS 图形栈只有 EGL+GLES3.2，无桌面 GL 兼容配置；gl4es 头文件假设 X11 存在。
- CMake 平台模块缺失导致 -soname 链接标志未初始化。

## 方案
1. generate() 生成最小 BoostConfig.cmake shim：Boost::boost INTERFACE IMPORTED +
   Boost_INCLUDE_DIRS，cache_variables["Boost_DIR"] 指向生成目录。
2. `self.requires("gl4es/1.1.6", headers=False)` + generate() 里
   `self.dependencies["gl4es"].cpp_info.includedirs = []`，OPENGL_*_LIBRARY 指向
   gl4es libGL.so，GL/EGL 头用 OHOS sysroot；运行期设 LIBGL_GLES=/system/lib64/
   libGLESv3.so、LIBGL_EGL=/system/lib64/libEGL.so，LD_LIBRARY_PATH 前插包 lib。
3. cache_variables 注入 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` 与
   `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` 为 `-Wl,-soname,`。

## 验证
- coin3 4.0.7：conan-verify G0-G4+L2/L4/L5 全 PASS；CoinTests 327/327 通过；
  W3 build_and_test.sh 100% pass（L0/L1/L4/L5 全过）；test_package 消费者
  场景图写回验证 exit 0。

## 适用边界
- CMake ≥ 4.0 + conan boost 头文件用途的库；OHOS 上依赖桌面 GL 固定管线的库；
  CMake 未知平台（HarmonyOS）且需 SONAME 的共享库配方。
- 反例：CMake < 4 仍有 FindBoost 时无需 shim；库自带 BoostConfig 时不需要；
  GLES 原生库不需要 gl4es；平台模块已存在时不需注入 soname 标志。

## 关系
- similar_to: E096（cmake-cxx-standard，同为 cache_variables 配置手法）、
  E537（SONAME 门禁，但根因是绝对路径 DT_NEEDED）、E298（test_package 运行时
  VirtualRunEnv）、E092（CMake 未知平台检测）、gl4es/1.1.6 归档（提供方）。
- prerequisite_of: 后续 CMake4 + boost 头文件库、OHOS 桌面 GL 兼容库适配。
