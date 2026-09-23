# libad9361-iio 0.3 适配笔记

## 编译环境
- 构建系统: cmake（C 语言项目，CTest 测试套件）
- 编译日期: 2026-09-17
- 编译器: clang 15（OHOS aarch64）
- 状态: built

## 编译步骤
1. 上游核验：github.com/analogdevicesinc/libad9361-iio tag v0.3；codeload tarball
   sha256=1dc35dd9…8dc90598（任务版本 0.3，配方/目录/分支一致）。
2. W0：硬依赖 libiio（上游 find_library(iio)/find_path(iio.h)）；制品仓已发布
   libiio/0.25（0.26 未上传），配方 requirements 声明 libiio/0.25。
3. 源码预检：CMakeLists.txt 为 2.8.12 老基线；test/ 注册 5 项 add_test。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake_minimum_required(VERSION 2.8.12) 过老 | Conan 工具链/依赖生成器需要 CMake 3.x 语义 | 构建期 replace_in_file 提升至 3.15（源内修改，direvent umask 同款方式） |
| 2 | 上游裸 find_library(iio)/find_path(iio.h) 找不到依赖 | libiio 由 Conan 管理，不在系统路径 | generate() 将 libiio 包的 lib/include 绝对路径注入 CMake 变量 LIBIIO_LIBRARIES / LIBIIO_INCLUDEDIR（libcoap 注入 cunit 同款先例） |
| 3 | 静态库 ad9361.a 引用 iio 符号，消费者链接不到 | CMake LINK_PRIVATE 不传播 | package_info 设 cpp_info.requires=["libiio::libiio"] 传播依赖 |

## 上游测试四维账本
- 上游静态声明总数：**5**（test/CMakeLists.txt add_test 逐项统计）
- 实际执行：**2**（FilterDesignerTest、GenerateRatesTest —— 均为纯软件算法测试，
  配方 build() 内以 ctest -R 真实执行，任一失败构建失败）
- 未执行分类数：**3**（逐项说明，均为硬件测试：FilterDesignerHardwareTest 需
  真实 AD9361 板卡；FMComms5SyncTest 需双 FMComms5 板卡相位同步硬件环境；
  AutoRateTest（auto_rate_test_hw.c）直接操作真实 AD9361 设备——OHOS PC 无
  此类硬件，无法执行，非用例本身失败）
- 通过/失败/跳过（可执行子集）：2 通过 / 0 失败；硬件 3 项按平台限制跳过
- 新增消费者测试：1 个程序（test_package/test_libad9361.c，调用设备无关纯计算
  API ad9361_calculate_rf_clock_chain(25MHz)，3 项断言：返回 0、链首速率≥基带、
  6 级时钟链单调非增；任一失败退出码 1）

## 路径 A/B 判断
路径 A（基础适配）。判断依据：适配问题（老 cmake 基线、裸 find 注入、静态库
符号传播）均为常规手段与既有先例（libcoap 的 cunit 注入）复用，无新的跨仓库
可复用知识增量，不满足路径 B 证据门槛。
