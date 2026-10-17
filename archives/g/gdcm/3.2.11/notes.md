# gdcm 3.2.11 适配笔记

## 概述
- 上游：https://github.com/malaterre/GDCM tag v3.2.11（DICOM 医学影像库，中重件）
- 构建：CMake（ohos.toolchain.cmake + 裸 cmake 路线，同 expat/glfw 配方模式 ML-0035）
- 依赖：zlib/1.3.1.1、expat/2.8.4（制品仓）；openjpeg/charls/jpeg8/12/16/md5/uuid/socketxx 用上游内嵌 Utilities 源码（依赖链最短原则）
- 形态：静态库（GDCM_BUILD_SHARED_LIBS=OFF）+ CLI 工具（gdcmdump/gdcmconv/gdcmscu/gdcminfo 等）

## OHOS 适配要点（踩坑记录）

### 1. llvm-ranlib 缺失（SDK 布局坑）
- 现象：`make` 阶段 `Error running link command: no such file or directory`，静态库链接失败
- 根因：ohos.toolchain.cmake 强制 `CMAKE_RANLIB=<SDK>/llvm/bin/llvm-ranlib`，但本机 SDK 的 llvm/bin 只装了 llvm-ar/llvm-nm/llvm-objcopy，没有 llvm-ranlib；SDK 目录只读无法补软链
- 修复：conanfile build() 在 configure 后扫描 build 树所有 link.txt，把 `<SDK>/llvm/bin/llvm-ranlib` 重写为 `/data/service/hnp/bin/llvm-ranlib`（同版本 15.0.4，实测可用）。CI 环境若 SDK 自带 ranlib 则 fixup 自动跳过（幂等）

### 2. GDCM_USE_SYSTEM_EXPAT 时 expat.h 找不到（上游漏配）
- 现象：`Utilities/gdcm_expat.h:20: fatal error: 'expat.h' file not found`
- 根因：顶层 CMakeLists 对 ZLIB 有 `include_directories(${ZLIB_INCLUDE_DIR})` 但对 EXPAT 漏了同等处理——gdcmIOD 的 gdcmTableReader.cxx 用 `#include <expat.h>`（经 gdcm_expat.h 宏分派）但 include path 从未加入
- 修复：patch 0001 在 Source/InformationObjectDefinition/CMakeLists.txt 的 gdcmIOD include 段补 `include_directories(${EXPAT_INCLUDE_DIRS})`

### 3. TestRescaler2 失败：plain char 符号性（平台差异实锤）
- 现象：TestRescaler2 Case11/12 断言失败（min2>max2）
- 根因：测试模板 `TestRescaler2Func<char,char>` 假设 plain char 是 signed（x86 Linux 语义）；OHOS arm64 SDK 下 `std::numeric_limits<char>::min() == 0`（unsigned char 语义，AAPCS 实现）——(char)(min+i) 输入回绕 + (char)(...) 输出再回绕，序列非单调。探针实测：`is_signed<char> == 0`
- 修复：patch 0002 把 Case11/12 的输入输出类型改为 `signed char`（正是 INT8 PixelFormat 的本意），并补 `TypeToPixelFormat<signed char>` 特化。修后 16 个 Case 全过（探针 failed=0）
- 平台真理：C++ 标准中 plain char 的符号性是实现定义（CHAR_MIN 可为 0）；arm64 平台移植时对 char 做算术/范围假设的代码必须显式用 signed char/unsigned char

### 4. conan 依赖重定向（裸 cmake 路线的代价）
- gdcm 的 find_package(ZLIB) 会抢到 sysroot 的 libz.so——需显式传 `-DZLIB_INCLUDE_DIR/-DZLIB_LIBRARY`、`-DEXPAT_INCLUDE_DIR/-DEXPAT_LIBRARY` 指向 conan 依赖包
- 测试二进制运行时 NEEDED libexpat.so + libc++_shared.so：LD_LIBRARY_PATH 需含 conan expat libdir + `SDK/llvm/lib/aarch64-linux-ohos`（libc++_shared.so 的实际位置——不是 llvm/lib 顶层）；继承系统默认 LD_LIBRARY_PATH 会加载缺符号的 libc++ 变体

### 5. 上游测试口径（rule4 申报）
- 上游默认 tarball 形态（GDCM_BUILD_TESTING=ON，无 gdcmData 数据集——tarball 内 Testing/Data 为空目录；无 DCMTK/dicom3tools 外部工具——GDCM_TEST_DCMTK 默认 OFF）注册 **200 项** ctest
- 豁免 7 项（全部硬编码外网 DICOM 服务器 www.dicomserver.co.uk / 51.75.171.41:11112 的真实网络往返测试，沙箱无出站 DICOM 端口）：
  1. TestEcho（CEcho 到 www.dicomserver.co.uk:11112）
  2. TestFind（CFind 到外网服务器）
  3. TestFindPatientRootQuery（外网 CFind）
  4. TestFindStudyRootQuery（外网 CFind）
  5. TestSCUValidation（连 51.75.171.41 的 SCU 校验）
  6. gdcmscu-echo-dicomserver（外网 echo 集成）
  7. gdcmscu-find-dicomserver（外网 find 集成）
- 本地实测：**193/193 全过（100%）**（conan create 内嵌 ctest，签名后本机执行）
- test_package：字典查询/Attribute 往返/PixelData 条目/Reader-Writer 链接验证，运行输出 "ALL OK"

## 构建产物
- 库：libgdcm{Common,DICT,DSED,IOD,MSFF,MEXD,charls,jpeg8,jpeg12,jpeg16,md5,openjp2,uuid}.a + libsocketxx.a
- 工具：gdcmdump、gdcmconv、gdcminfo、gdcmraw、gdcmscu、gdcmimg、gdcmjson、gdcmtar 等（commands.json 声明）
- 头文件：include/gdcm-3.2/（376 个 .h + 16 个 .txx）

## B/C 判定素材（医学影像适配）
- 平台差异诊断：plain char 符号性在医学影像像素类型（INT8/UINT8 分派）上的真实影响 + 定位方法（探针探 numeric_limits）
- 构建系统组合：ohos.toolchain 强制 RANLIB 与 SDK 布局不一致的通用修法（link.txt 重写，幂等）
- 适用面：所有 arm64 OHOS 上做 C++ 库适配的任务都可能遇到（char 符号性）；SDK 工具缺件是环境级问题
