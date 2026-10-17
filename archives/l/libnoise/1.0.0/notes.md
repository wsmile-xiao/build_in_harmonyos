# libnoise 1.0.0 适配笔记

## 编译环境
- 构建系统: cmake（配方自带 CMakeLists.txt；上游为手写递归 Makefile + libtool）
- 编译日期: 2026-09-18
- 编译器: clang/clang++（OHOS SDK，/data/service/hnp/bin）
- 状态: built

## 上游信息
- 软件: libnoise（Jason Bevins 的可移植相干噪声生成 C++ 库）
- 版本: 1.0.0（上游最后一个发布版，发布于 2007-04；libnoise.sourceforge.net 至今未再发版）
- 官方源: https://downloads.sourceforge.net/project/libnoise/libnoise%20sources/1.0.0/libnoisesrc-1.0.0.zip
- sha256: 34ed402f43f30ce5e39812642c9533c11082cd2bc092341c65160f5c743be95b（1,667,748 字节）
  - 与 FreeBSD ports audio/libnoise 的 distinfo 完全一致（交叉校验来源：freshports.org/audio/libnoise）
- 许可证: LGPL-2.1（COPYING.txt）
- 语言: 纯 C++（35 个 .cpp + 头文件）；R47 语言预检经 runtime 副本实跑通过（detected=cpp，
  milestone=lang_checked 草稿），无绑定目录误判问题

## 上游测试清单（R51 第一步：清点，附证据）

上游 1.0.0 **没有任何测试**，清点证据如下：

1. 源码 zip 全量清单（unzip -l）：仅 COPYING.txt、doc/、include/、lib/、noise 工程文件
   （src/、Makefile、INSTALL、libnoise.dsp/.dsw/.ncb/.opt/.plg、noise.aps）与 win32/（Debug/Release
   MSVC 工程输出）；grep -i "test|example|demo" 无任何命中；
2. 顶层 Makefile 目标集合：all/clean/install（doc src include lib），无 check/test 目标；
   src/Makefile 目标：libnoise.so.0.3 / libnoise.a / libnoise.la / clean，同样无测试目标；
3. 无 tests/ 目录、无 CTest enable_testing()/add_test()、无任何测试框架文件；
4. 上游文档站（libnoise.sourceforge.net）的教程与示例均为网页文字，不随源码 zip 交付、不可运行。

结论：上游可运行测试入口为 0，通过率记 0/0；验证由 test_package 消费者程序承担（16 断言）。

## 编译步骤

```sh
# 1. 下载并校验官方源码（sha256 见上），解压得到 COPYING.txt 与 noise/
# 2. conan create：配方 source() 用 get(strip_root=False) 取源码
#    （zip 顶层两个条目，单根剥离会失败）
# 3. 配方导出的 CMakeLists.txt 按 noise/src/Sources 的同一 35 个翻译单元
#    add_library(noise)，include 目录指向 noise/src
# 4. CMakeToolchain 注入 OHOS 工具链；BUILD_SHARED_LIBS 由 Conan shared 选项决定
# 5. cmake.install()：库到 lib/，头文件按上游布局装到 include/noise/
#    （noise/*.h、noise/module/、noise/model/），COPYING.txt 装到 licenses/
```

配方自带 CMakeLists 的原因：上游 Makefile 的编译规则硬编码
`$(LIBTOOL) --mode=compile $(CXX) ...`，OHOS 构建环境没有 libtool；CMake 版本编译
完全相同的源文件集合，不修改任何上游文件，也不需要补丁。

预验证：35 个 .cpp 已在设备上用 OHOS clang 以 -std=c++17 逐个编译通过（0 失败），
证明源码零修改即可编译；该探针为探索性验证，正式结论以 conan create 为准。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游构建依赖 libtool，OHOS 环境无此工具 | 2007 年手写 Makefile 用 `$(LIBTOOL) --mode=compile/link` | 配方导出自带 CMakeLists.txt 编译同一源文件集合，零源码修改 |
| 2 | conan get(strip_root=True) 会失败 | 源码 zip 顶层有 COPYING.txt 与 noise/ 两个条目（非单根归档） | source() 用 strip_root=False，CMakeLists 用 noise/ 前缀寻址 |
| 3 | 官方下载链接 404 | 主页残留 2007 年 prdownloads 旧链接，实际路径在 `libnoise sources/1.0.0/` 子目录 | 经 SourceForge 文件树定位真实路径；FreeBSD distinfo 交叉校验哈希一致 |
| 4 | install(DIRECTORY) 把 noise/src/win32/（MSVC resource.h）装进 include/noise/win32/，上游 include/Makefile 不装它 | *.h 通配未排除 MSVC 资源头 | CMakeLists 增加 REGEX "/win32$" EXCLUDE，制品 45→44 头；staging 验证确认 |
| 5 | 第 2 轮起 conan-verify L5 产物基线对比 FAIL（+0 -1 ~0） | 首轮基线含 win32/resource.h，排除后制品合法减少 1 个文件 | 按 L5 既定口径删除 reports/baseline.json 重立基线（语义等同首轮），差异原因即问题 4 的已审修复，非制品回归 |

## 源码修改

无。零补丁（patches_applied: []），上游源文件零修改；构建方式变化由配方导出的
CMakeLists.txt 承载，属配方文件而非源码补丁。

## 依赖版本

无外部依赖（纯 C++ 标准库）。W0 报告：dependencies={}、version_occupancy=missing（未占用）。

## 验证结果

```bash
# conan create（含 test_package）——结果见版本目录 reports/
# 消费者程序输出（W3 实跑）：
# libnoise consumer test: 16 checks, 0 failures
```

消费者测试覆盖面（16 断言）：Perlin 确定性/有限性/相干性、参数设置生效、Billow 与
RidgedMulti、ScaleBias 模块图精确算术（source*scale+bias 的 IEEE 一致性）、
ExceptionNoModule 契约、Sphere/Cylinder/Plane/Line 四个 model 类、LatLonToXYZ 单位球性质。

## OHOS 平台适配要点

- libnoise 是纯算法库，不接触平台 API（无 sysroot 头文件依赖、无 dlopen/线程/文件 IO），
  OHOS 上无需任何平台分支；
- 库名 "noise" 不是系统同名库（OHOS /lib 无 libnoise），无 R26 静态化强制；Conan 默认
  static（shared=False），shared=True 时以 VERSION 0.3 / SOVERSION 0 复刻上游 soname 链
  （libnoise.so.0.3，SONAME libnoise.so.0）；
- 头文件安装布局复刻上游 `<prefix>/include/noise/`，消费者按 `#include <noise/noise.h>` 使用。

## 注意事项

- 上游 1.0.0 后社区维护有限（第三方 fork 各自加 CMake/修复），本包严格以官方 1.0.0
  发布源为准，不引入任何 fork 内容；
- 上游无测试是上游事实而非适配缩减；PR 表格按 0/0 披露，鸿蒙特有测试行即消费者程序；
- 文档目录 doc/（Doxygen HTML）随包体积较大且不参与构建，Conan 包不安装它，
  与上游"文档独立交付"惯例一致。
