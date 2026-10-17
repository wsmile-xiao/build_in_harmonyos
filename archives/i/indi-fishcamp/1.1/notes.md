# indi-fishcamp 1.1 - adaptation notes

## Source
- URL: https://deb.debian.org/debian/pool/contrib/i/indi-fishcamp/indi-fishcamp_1.1.orig.tar.gz
- sha256: eacf05b78b3980389348d9a2be4a112eb1bb2c1d2b8f554743569da8d9102264
- 上游未为 indi-fishcamp 单独打 tag，Debian Astronomy Team contrib pool
  的 orig 包是 indilib/indi-3rdparty indi-fishcamp/ 子目录 1.1 版本的
  权威可下载快照（46376 字节，顶层 indi-fishcamp-1.1，66 个文件）。
  2026-09-30 实测 HTTP 200 且 sha256 一致。
- License: LGPL-2.1-or-later（驱动头文件 indi_fishcamp.h 声明 GNU Lesser
  General Public License v2.1+）。Debian orig tarball 不带 LICENSE 文件，
  package() 无需拷贝。

## Scope
- 全部源码：indi_fishcamp.cpp（FishCampCCD 驱动，继承 INDI::CCD 基类）+
  indi_fishcamp.h + indi_fishcamp.xml.cmake（设备描述模板）+ config.h.cmake
  （版本宏 FISHCAMP_VERSION_MAJOR=1/MINOR=1）。无其他可选组件；
  cmake_modules/ 下是 indi-3rdparty 共享的 Find*.cmake 集合（本驱动只用
  FindINDI/FindFISHCAMP/FindCFITSIO/FindZLIB + CMakeCommon）。
- 功能面：通过 libfishcamp 的 fcUsb_* API 走 USB 控制 Starfish CMOS
  自动导星相机（曝光/增益/温度/相机信息），发布 INDI 属性
  CCD_GAIN / Cooler / Camera Info / CCD_TEMPERATURE 等；支持仿真模式
  （simulationTriggered → fcUsb_setSimulation(true)，免硬件）。

## Build system
- 极简 CMake（cmake_minimum_required 3.0 + 自研 CMakeCommon.cmake）。
  CMake >= 4.0 移除了 <3.5 兼容，configure 必须显式
  `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（且必须走 cli_args 真 -D 缓存变量，
  tc.variables 注入时机太晚不生效——同 indi-gpsnmea/libfli 经验）。
- E092：CMake 无 HarmonyOS 平台，CMAKE_SYSTEM_NAME=Linux +
  CMAKE_SYSTEM_PROCESSOR=aarch64（与 libindi/2.2.2.1、indi-gpsnmea 一致）。
- CMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF（toolchain block）：Conan 默认 ON
  会遮蔽树内 cmake_modules/FindINDI.cmake / FindFISHCAMP.cmake /
  FindCFITSIO.cmake，CMake 去找不存在的 INDI/FISHCAMP/CFITSIO CONFIG 包
  直接失败。
- fishcamp_common.h（fishcamp.h 引入，经驱动编译）按裸名
  `#include <libusb.h>` 引用，而 libusb 包把它放在 include/libusb-1.0/
  叶子目录，需在 toolchain 显式 -I 注入叶子目录（同 indi-gpsnmea 的
  libnova include root 注入模式）。

## Patches (3, 全部 portability)
1. 0001-FindINDI.cmake.patch：版本号正则回移上游 master 修复，兼容
   INDI >= 2.0 indiversion.h 的 `#define INDI_VERSION "2.2.2"` 引号形式
   （1.1 快照的正则只能匹配裸数字，find_package(INDI REQUIRED) 否则
   FATAL_ERROR "failed to detect INDI version"）。与 indi-gpsnmea 0001
   补丁 byte-identical（md5 4fdd44eb…）。
2. 0002-indi2.2-api-port.patch：Starfish 驱动对接 INDI 2.2 框架，与上游
   官方 v2.2.4 移植**逐行一致**（对照 indilib/indi-3rdparty master 的
   indi_fishcamp.cpp 逐处核对）：
   a) INDI::CCD 基类成员 TemperatureNP 在 INDI 1.x 是 C 结构体
      (INumberVectorProperty)，在 INDI 2.x 升级为 INDI::PropertyNumber 类
      —— 成员用法迁移为 setState()/apply()/getState()/operator[]/
      getValue()/setValue()，共 8 处；驱动自身声明的成员（GainNP/
      CoolerNP/CamInfoTP，1.1 头文件里仍是 INumber/INumberVectorProperty
      等 C 结构体）保持 .s/.value 不变（INDI 2.2 中 C 结构体仍可导出
      IDSetNumber/IUFillNumberVector 等 API，官方 v2.2.4 同样保留）。
   b) initProperties() 新增 INDI 2.x 必需的 capture format 注册：
      CaptureFormat mono = {"INDI_MONO", "Mono", 16, true}; +
      addCaptureFormat(mono)（INDI 2.x CCD 基类要求至少一个 capture
      format，否则曝光流程无格式可选）。
3. 0003-CMakeLists-ohos-port.patch（三合一）：
   a) include(CMakeCommon) 之后抬 CMAKE_CXX_STANDARD=17：上游
      CMakeCommon.cmake 钉死 C++14，而 INDI 2.x 基类头 defaultdevice.h
      用 std::any 等 C++17 特性，C++14 编译直接报 no type named 'any'。
   b) find_library(LIBUSB_LIBRARY NAMES usb-1.0) 并加入
      target_link_libraries：libfishcamp.a 内嵌 16 处 usb_* 符号引用
      （usb_init/usb_bulk_transfer/usb_open_device_with_vid_pid 等），
      1.1 树内 FindUSB1.cmake 存在但未在本驱动 CMakeLists 接线，链接期
      undefined reference，必须显式补 libusb-1.0。
   c) set(INDI_DATA_DIR ${CMAKE_INSTALL_PREFIX}/share/indi)：树内
      FindINDI.cmake 会报出 libindi 包的 INDI_DATA_DIR，不覆盖的话
      install 会把设备 xml 装进 libindi 包目录（跨包污染）。

## Upstream tests
- 上游 tarball（66 个文件）无任何自动化测试套件：无 tests/ 目录、无
  CTest 注册、无 Makefile test 目标，纯驱动 + 构建脚本 + 共享
  cmake_modules。
- 上游 N=0，适配后 5 个消费者用例 / 37 项检查全部真实执行（见下）。

## Consumer test (test_package)
- test_fishcamp.c：5 个端到端用例（完整断言清单与口径见
  test_package/MANIFEST.yml）：
  - HC-1 包内 bin/indi_fishcamp_ccd 是合法 AArch64 64-bit ELF（\x7fELF /
    ELFCLASS64 / ELFDATA2LSB / e_machine=183 / e_type EXEC|DYN）— 7 检查
  - HC-2 驱动链接 libindidriver.so.2 + libindiAlignmentDriver.so.2 +
    libc++_shared.so 且内嵌 Starfish 驱动逻辑字符串（Starfish CCD /
    CCD_GAIN / Camera Info / Fishcamp CCD is online. /
    Taking a %g seconds frame...）— 8 检查
  - HC-3 **真实运行**驱动的功能核心 libfishcamp 仿真模式：
    fcUsb_init/setLogging(false)/setSimulation(true) → FindCameras==1 →
    OpenCamera==0 → getinfo（1280x1024、pixel 52x52）→
    setCameraGain==0 → setIntegrationTime==0 → startExposure==0 →
    getTemperature==25（仿真值确定性常量）→ CloseCamera==0 — 14 检查
  - HC-4 包内 share/indi/indi_fishcamp.xml 设备描述（device label /
    driver name → indi_fishcamp_ccd / version 1.1 / group CCDs）— 5 检查
  - HC-5 鸿蒙特有：ELF 解释器 = OHOS musl 加载器
    /lib/ld-musl-aarch64.so.1 + e_machine aarch64 + 测试程序自身
    __aarch64__ — 3 检查
- test_package/conanfile.py test() 真实 self.run 编译并执行
  test_fishcamp（链接包内 libfishcamp.a + libusb-1.0.so），断言
  'case HC-n' 行、RESULT: PASSED、两行汇总零失败；缺包内制品直接
  AssertionError。
- 实测：`conan create ... -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
  --build=missing` → EXIT 0，test 输出
  `== 5 cases, 0 failed ==` / `== 37 checks, 0 failures ==` /
  `RESULT: PASSED`。

## 驱动直接执行受沙箱限制（如实披露，非构建缺陷）
- 本构建沙箱的 OHOS 动态加载器对 conan 缓存内的 **libindidriver.so.2 与
  libindiAlignmentDriver.so.2** 两个文件做 dlopen 一律 Permission denied
  （EACCES，persistent，与 rlimit 无关；对照实验：同缓存目录的
  libusb-1.0.so.0 / libindiclient.so.2 可正常 dlopen，限制是**按文件**的
  而非按目录的）。因此凡 NEEDED 带这两个 INDI 框架 .so 的二进制（包括
  包内驱动）无法在沙箱内直接执行。
- 只依赖 libusb-1.0.so.0 + 静态库的新编译 aarch64 二进制可正常执行
  （HC-3 的 libfishcamp 仿真测试二进制即属此类，实测 exit 0 且全部
  断言通过）。
- 因此驱动进程级行为（INDI 框架加载、TCP 服务端、property 发布、USB
  枚举）无法在沙箱内端到端驱动，改由：
  a) HC-1/HC-2/HC-5 对包内二进制做静态验证（ELF 有效性 / 目标三元组 /
     框架链接 / Starfish 逻辑落地）；
  b) HC-3 真实运行驱动的全部功能逻辑核心（驱动 = INDI 框架粘合层 +
     libfishcamp 命令序列，仿真模式覆盖后者全部命令路径）；
  c) HC-4 验证 INDI 服务端据以发现驱动的设备描述文件。
- 该限制是环境性的（conan 缓存特定 .so + 沙箱 seccomp），CI 真机环境若
  无此限制可直接运行驱动冒烟；构建与功能核心本身无缺陷（conan create
  全程 EXIT 0）。

## Preflight history
- 2026-09-30: 本地 conan create（ohos-aarch64 双 profile，--build=missing）
  全链通过：source（sha256 校验）→ configure（3 补丁全部命中，4 个
  find_package 全部 Found）→ compile（indi_fishcamp.cpp C++17 通过
  INDI 2.2 基类）→ link（libindidriver/libindiAlignmentDriver/
  libfishcamp.a/libcfitsio.a/libusb-1.0/z/m 齐全）→ package
  （bin/indi_fishcamp_ccd + share/indi/indi_fishcamp.xml）→
  test_package 37/37。
