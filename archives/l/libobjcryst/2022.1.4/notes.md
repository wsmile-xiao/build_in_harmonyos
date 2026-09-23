# libobjcryst 2022.1.4 适配笔记

## 上游

- 名称：libobjcryst（ObjCryst++ 面向对象晶体学 C++ 库，diffpy 重打包，去 GUI，内嵌 cctbx/newmat 所需源码）
- 版本：2022.1.4（tag v2022.1.4，2022-12-03，commit e8d36ac73a750a17078c21b947480d4312c83083）
- 仓库：https://github.com/diffpy/libobjcryst
- 源码包：https://github.com/diffpy/libobjcryst/archive/refs/tags/v2022.1.4.tar.gz
- sha256：ce49897e15ef0d37be2df1d42cedbb387ff3c8830a3094cc91512f0de38d1745（1372381 字节，376 文件，139 个 .cpp）
- 许可证：GPL-2.0-only（LICENSE.txt 为 GPL v2）
- 构建系统：SCons（SConstruct + src/SConscript*），C++11，要求 boost 头文件
- 上游测试：无 CTest/make check/tests 套件；README 指定 examples/testlib.cpp 为安装校验程序，作 2 检查合成上游套件（详见 test_package/MANIFEST.yml upstream_test_audit）

## 适配方案（路径 A 基础适配）

- 绕开 SCons：真机/CI 均无 scons 二进制，dxx-rebirth 的 pip 安装方案增加网络抖动点；
  采用 libe57format 直接编译先例，用 Conan conf 提供的 OHOS clang++ 直接编译
  上游 TU 集合（R33 合规，不用裸 ${CC}）。
- TU 集合与上游 SConscript 语义一致：ObjCryst 4 目录 glob + version.cpp、
  cctbx 6 组 glob（shared-cctbx 分支关闭，用内嵌源码）、newmat 14 文件显式列表
  （排除自带 main 的 test_exc.cpp）。
- version.h 缺失于 codeload 包：按 SConscript.version 的 substitution 公式，
  用静态 2022.1.4 值从 version.tpl 生成（major 2022/minor 1/micro 4/patch 0，
  VERSION 整数 2022001004000，date 2022-12-03，commit e8d36ac）。
- 头文件安装与上游 install-include 一致：ObjCryst 三目录 + Quirks 过滤后集合 +
  version.h，置于 include/ObjCryst/ 下；cctbx/newmat 头仅构建期使用。
- 依赖：boost/1.91.0.1.1（纯头文件用法，-DBOOST_ALL_NO_LIB，仓库内已有归档、
  abiword 插件注明已发布）。
- 默认静态（shared=False）；shared=True 时产出 libObjCryst.so 并走
  binary-sign-tool 自签名（tolerant，缺工具则跳过）。
- 平台判断遵守 R32（`in ("Linux", "OHOS")`）；补丁目录为空（无需 OHOS 补丁，
  纯 POSIX C++，无平台宏）。

## 测试

- 上游：无原生套件，build() 编译运行 README 指定的 examples/testlib.cpp（修正弧度+六角角度后）作 2 检查合成套件（fcc-create、CIF 解析），断言非空输出+CIF 阶段证据+尾部 works! 行，输出 HMBS_UPSTREAM_TEST_RESULT status passed/discovered=2（数字来自真实二进制输出，缺证据即失败）。
- test_package：test.cpp 7 个 CHECK（FCC 晶格/空间群 2、CIF 建晶 2、版本宏 3），
  二进制退出码 + HMBS_TEST_PACKAGE_RESULT 双证据；MANIFEST assertion_count=7。
  消费者不用 CMake（CMake 4.x 在真机无法识别 OHOS clang，
  test_package configure 报 System unknown/Configuring incomplete），
  改用 Conan conf 的 clang++ 直接编译单个 test.cpp
 （libe57format 3.3.0 已合入先例），单进程无并行内存峰值。
- 证伪计划（真机轮）：确认参照输出非空；必要时用 exit 1 桩验证 harness 能抓失败；
  区分通过与静默跳过。

## 风险

- boost 版本若在制品仓未发布，真机 L0i 会拦截，届时按实际已发布版本改 pin。
- cctbx 内嵌源码量较大，真机编译时间可能较长；2026-09-18 两轮真机预检均在
  compile 阶段报 `tar (child): Cannot fork: Out of memory`（stdout 为空，
  上游测试 0/0/0），即受限 worker 内存耗尽连 fork 都失败。应对（只降内存
  峰值，不碰 TU 集合与测试口径）：Release 优化从上游 "fast" 的 -O3 降一档
  到 -O2（保留 -ffast-math/-DNDEBUG），主包逐 TU 串行编译（单进程峰值），
  test_package 显式 `cmake.build(cli_args=["-j1"])`（oclgrind/26.03.1 与
  wxWidgets 低内存先例）。
