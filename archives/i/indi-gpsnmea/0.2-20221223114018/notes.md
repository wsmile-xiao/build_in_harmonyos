# indi-gpsnmea 0.2-20221223114018 - adaptation notes

## Source
- URL: https://deb.debian.org/debian/pool/main/i/indi-gpsnmea/indi-gpsnmea_0.2+20221223114018.orig.tar.gz
- sha256: 7b6fb70c408bf5b0241aecb3527109bae6d4094921ba3fd0677f4c936d06a503
- 上游未为 indi-gpsnmea 单独打 tag，Debian orig 包是 indilib/indi-3rdparty
  indi-gpsnmea/ 子目录的权威可下载快照（时间戳 2022-12-23 11:40:18 = git 提交时刻）。
  conan 版本号把 '+' 规范化为 '-'。
- License: GPL-2.0-or-later（驱动头文件声明；树内 minmea 为 WTFPL）。
  Debian orig tarball 不带 LICENSE 文件，package() 无需拷贝。

## Scope
- 全部源码：gpsnmea_driver.cpp + 树内 minmea.c/h（WTFPL 解析器，上游
  CMakeLists 直接 add_executable(indi_gpsnmea gpsnmea_driver.cpp minmea.c)
  编进驱动）。无其他可选组件。

## Build system
- 极简 CMake（cmake_minimum_required 3.0 + 自研 CMakeCommon.cmake）。
  CMake >= 4.0 移除了 <3.5 兼容，configure 必须显式
  `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（且必须走 cli_args 真 -D 缓存变量，
  tc.variables 注入时机太晚不生效——同 libfli 经验）。
- E092：CMake 无 HarmonyOS 平台，CMAKE_SYSTEM_NAME=Linux +
  CMAKE_SYSTEM_PROCESSOR=aarch64（与 libindi/2.2.2.1、libfli 一致）。
- CMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF（toolchain block）：Conan 默认 ON
  会遮蔽树内 cmake_modules/FindINDI.cmake / FindNova.cmake，CMake 去找
  不存在的 INDI/Nova CONFIG 包直接失败。
- FindNova 只报叶子目录 include/libnova 为 NOVA_INCLUDE_DIR，而驱动按
  <libnova/julian_day.h> 引用，需在 toolchain 显式 -I 注入 include root
  （同 libfli 的 libusb-1.0 include 修复模式）。

## Patches (3, 全部 portability)
1. 0001-FindINDI.cmake.patch：版本号正则回移上游 master 修复，兼容
   INDI >= 2.0 indiversion.h 的 `#define INDI_VERSION "2.2.2"` 引号形式
   （2022 快照的正则只能匹配裸数字，find_package(INDI REQUIRED) 否则
   FATAL_ERROR "failed to detect INDI version"）。与 libfli 0001 补丁
   byte-identical。
2. 0002-OHOS-indi2.2-gpsapi.patch：
   a) setSystemTime()：上游在 `__GNU_LIBRARY__` 之外的 `#else` 分支直接
      调用非标准 stime(3)，而 musl 系 libc（含 OHOS）无 stime 符号；改为
      在**该 `#else` 分支**直接用标准 clock_settime(CLOCK_REALTIME)
      （POSIX 接口，glibc 与 musl 均可用），保持上游
      `__linux__` / `__GNU_LIBRARY__` 条件结构不变，不新增任何平台
      条件编译宏（符合 R8）。
   b) 上游快照（对应 INDI 1.x）引用的 INDI::GPS 基类成员 LocationN/TimeT
      在 INDI 2.2 改名为 LocationNP/TimeTP（基类加 P 后缀成员），逐处
      更新 8 处，否则编译期 undefined member。
3. 0003-CMakeLists-cxx17.patch：上游 CMakeCommon.cmake 钉死 C++14，而
   INDI 2.x 基类头 defaultdevice.h 用 std::any 等 C++17 特性，C++14 下
   报 no type named 'any' in namespace 'std'。include(CMakeCommon) 后
   抬 CMAKE_CXX_STANDARD=17（只改本包，不动公共 CMakeCommon）。

## Upstream tests
- 上游 tarball（70 个文件）无任何自动化测试套件：无 tests/ 目录、无
  CTest 注册、无 Makefile test 目标；唯一沾 test 字样的
  indi-gpsnmea.spec 是 Debian 打包描述文件，非可执行测试。
- 上游 N=0，适配后 5 个消费者用例 / 54 项检查全部真实执行（见下）。

## Consumer test (test_package)
- test_gpsnmea.c：5 个端到端用例（完整断言清单与口径见
  test_package/MANIFEST.yml）：
  - HC-1 包内驱动是合法 AArch64 64-bit ELF（\x7fELF / ELFCLASS64 /
    ELFDATA2LSB / e_machine=183 / e_type EXEC|DYN）— 7 检查
  - HC-2 驱动链接 libindidriver.so.2 + libc++_shared.so 且内嵌 GPS 逻辑
    字符串（GPS NMEA / GPS_STATUS / GPS_FIX / Fix Mode / Connection）— 8 检查
  - HC-3 NMEA 0183 解析行为：重编译 test_package 内冻结的 minmea.c
    （与驱动内嵌同一份源码），用 RMC/GGA/GSA/GLL/ZDA 5 条已知有效句
    + 坏校验和 + 未知句 2 条非法输入驱动全部解析 API，断言精确值
    （RMC 时间 12:35:19、日期 23/03/1994、lat 48.11730、lon 11.51667、
    UNIX epoch 764426119；GGA fix_quality 1 / 8 星 / 海拔 545.4m /
    西经负号 -121.97236；GSA A/3D；GLL A；ZDA 16:00:47 2012-02-14 +00:00；
    坏校验和被拒、未知句判 INVALID、talker 'GP'）— 31 检查
  - HC-4 包内 share/indi/indi_gpsnmea.xml 设备描述（device label /
    driver name / version 0.2 / group Auxiliary）— 5 检查
  - HC-5 鸿蒙特有：ELF 解释器 = OHOS musl 加载器
    /lib/ld-musl-aarch64.so.1 + e_machine aarch64 + 测试程序自身
    __aarch64__ — 3 检查
- conanfile.py test() 真实 self.run 编译并执行，断言 'case HC-n'
  行、RESULT: PASSED、两行汇总零失败；缺包内制品直接 AssertionError。
- 实测：`conan create ... -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
  --build=missing` → EXIT 0，test 输出
  `== 5 cases, 0 failed ==` / `== 54 checks, 0 failures ==` /
  `RESULT: PASSED`。

## 驱动直接执行受沙箱限制（如实披露，非构建缺陷）
- 本构建沙箱的 OHOS 动态加载器无法对 conan 缓存目录内的框架 .so
  （libindidriver.so.2）做 PROT_EXEC mmap（persistent EPERM，与 rlimit
  无关）：对照实验中仅依赖 libc 的新编译 aarch64 二进制可正常执行
  （hello world 运行成功），凡 NEEDED 带 conan 缓存 .so 的二进制均
  被 loader 拒绝。
- 因此驱动进程级行为（TCP 连接 192.168.1.1:50000、NMEA 接收、INDI
  property 发布、系统时钟同步）无法在沙箱内端到端驱动，改由：
  a) HC-1/HC-2/HC-5 对包内二进制做静态验证（ELF 有效性 / 目标三元组 /
     框架链接 / GPS 逻辑落地）；
  b) HC-3 真实运行驱动的同款 NMEA 解析核心（minmea 就是驱动的全部
     功能逻辑，驱动其余部分是 INDI 框架粘合层）；
  c) HC-4 验证 INDI 服务端据以发现驱动的设备描述文件。
- 该限制是环境性的（conan 缓存路径 + 沙箱 seccomp），CI 真机环境若
  无此限制可直接运行驱动冒烟；构建与解析逻辑本身无缺陷（conan
  create 全程 EXIT 0）。

## Preflight history
- 2026-09-30: 本地 conan create（ohos-aarch64 双 profile，--build=missing）
  全链通过：configure（3 补丁全部命中）→ compile（gpsnmea_driver.cpp
  C++17 通过 INDI 2.2 基类）→ link（libindidriver/libnova/zlib/pthread
  齐全）→ package（bin/indi_gpsnmea + share/indi/indi_gpsnmea.xml）→
  test_package 54/54。
