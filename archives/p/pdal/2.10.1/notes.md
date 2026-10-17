# pdal 2.10.1 适配笔记

## 概述

PDAL (Point Data Abstraction Library) 2.10.1 —— 点云数据处理的 C++ 库
（"GDAL for point cloud data"）。核心产物：`libpdalcpp.so` 共享库 + `pdal`
命令行工具（含 pdal-config）。

- 上游：https://github.com/PDAL/PDAL
- 源码 tarball：108 MB（git 仓库全量 213 MB），C++17，CMake 构建
- 构建：HarmonyOS PC aarch64 原生（host==target），clang 15.0.4 / libc++ / musl
- 语言预检：cpp（源文件 962 个，C++ 主体 99%）

## 依赖（W0 实测制品仓确认）

直接依赖（conanfile requires，版本与 ohpcd 制品仓实际发布对齐）：

| 依赖 | 版本 | 说明 |
|------|------|------|
| gdal | 3.9.2.3 | 必需，光栅/矢量支持（pdal 要求 >=3.8） |
| libcurl | 8.5.0 | arbiter HTTP/IO 层 |
| libgeotiff | 1.7.4 | 必需（LAS GeoTIFF keys） |
| libtiff | 4.7.2 | 见下文"libtiff 补充说明" |
| proj | 9.3.1.1 | 坐标系变换 |
| zlib | 1.3.1.1 | 压缩 |
| libxml2 | 2.15.3 | 可选 reader/writer（保留开启） |
| xz | 5.6.2 | LZMA（本仓制品仓名为 xz，CCI 叫 xz_utils） |

传递依赖由 conan 自动解析（libjpeg-turbo、geos、libspatialite、sqlite 等
随 gdal/libgeotiff 链拉取，全部命中制品仓预编译包，无源码构建）。

## 构建选项裁剪清单

核心库 + 默认 reader/writer 保留；以下全部 OFF：

- 全部可选 plugin：CPD/DRACO/ICEBRIDGE/HDF/MATLAB/NITF/OPENSCENEGRAPH/
  PGPOINTCLOUD/RIVLIB/RDBLIB/MBIO/FBX/TEASER/TILEDB/TRAJECTORY/E57/ARROW/SPZ
- WITH_ZSTD=OFF（zstd 在制品仓有 1.5.6/1.5.7，但按任务范围裁剪）
- WITH_TESTS=OFF（上游单测需要 149 MB test/data 夹具树 + pdal_test 运行器）
- WITH_BACKTRACE=OFF、WITH_GCS=OFF（Google Cloud Storage）、WITH_COMPLETION=OFF
- BUILD_DOCS=OFF、BUILD_TOOLS_LASDUMP=OFF、BUILD_TOOLS_NITFWRAP=OFF
- CMAKE_DISABLE_FIND_PACKAGE_{Libexecinfo,Libunwind,OpenSSL}=ON

## 补丁（3 个）

1. `0001-cmake-conan-rpath.patch`（来自 CCI）：删除上游自定义 rpath 模块，
   RPATH 交给 Conan 管理。
2. `0002-avoid-openssl-relink.patch`（来自 CCI）：arbiter 不再重复链接
   CURL 传递发现的 OpenSSL。
3. `0003-geotiff-config-target.patch`（本仓自研）：`GEOTIFF_INCLUDE_DIR`/
   `GEOTIFF_LIBRARY`（上游 FindGeoTIFF 模块变量）在 CMakeDeps CONFIG 模式
   下不存在 → 改用 `GeoTIFF_INCLUDE_DIRS` 变量 + `GeoTIFF::geotiff` 目标，
   并显式链接 `libtiff::libtiff`（libgeotiff 公共头 xtiffio.h 包含
   <tiffio.h>，而制品仓 libgeotiff 包未聚合 libtiff include 目录）。
   注意：行号基于 0001 应用后（0001 删一行导致 -1 偏移）。

## 踩坑记录（新错误模式，已报知识草稿）

### 坑 1：dimbuilder 构建时运行失败（Error loading libc++_shared.so）

PDAL 用 `dimbuilder`（构建时生成的代码生成器）在 cmake --build 期间运行
生成 `Dimension.hpp`。OHOS loader 没有默认的 libc++_shared.so 搜索路径，
报 `Error loading shared library libc++_shared.so: (needed by bin/dimbuilder)`
+ 大量 symbol not found。

**修复**：conanfile generate() 里通过
`clang++ -print-file-name=libc++_shared.so`（编译器路径取自 profile 的
`tools.build:compiler_executables`）定位 SDK 运行时库目录，将其 prepend 到
build scope 的 `LD_LIBRARY_PATH`（`save_script("conanbuild_loader_path")`）。

### 坑 2：LD_LIBRARY_PATH 污染破坏 SDK lld（反向坑）

第一版修复把**所有 conan 依赖的 libdir** 也加进了 LD_LIBRARY_PATH，结果
CMake 编译器检测失败：SDK 的 lld 通过 RUNPATH 找 SDK 自带的
libxml2.so.16，LD_LIBRARY_PATH 抢先命中 conan 的 libxml2 包（版本符号不
匹配）→ `Error relocating lld: xmlFreeDoc: symbol not found`。

**修复**：LD_LIBRARY_PATH 只加 SDK libc++ 运行时目录，不加任何 conan 依赖
libdir。（教训：对 OHOS，LD_LIBRARY_PATH 的作用域要最小化。）

### 坑 3：test_package 运行时同样找不到 libc++_shared.so

conanrun 环境只覆盖 conan 依赖 libdir。测试可执行文件链接的 libc++_shared.so
需要 `/system/lib64`（系统自带 libc++_shared.so）。

**修复**：test_package/conanfile.py generate() 里
`Environment().prepend_path("LD_LIBRARY_PATH", "/system/lib64")` +
`save_script("system_run_env")`，test() 用
`env=["conanrun", "system_run_env"]` 运行（同 archives/a/avahi-ui/0.8 先例）。

### 坑 4：上游安装的 PDALConfig 与 CMakeDeps 冲突

上游 cmake install 会在包里放 `lib/cmake/PDAL/`（导出目标名 `pdalcpp`），
与 CMakeDeps 生成的 `PDALConfig.cmake`（目标 `pdal::pdal`）同名冲突。

**修复**：package() 里 rmdir `lib/cmake` 与 `lib/pkgconfig`（同 CCI 做法）；
消费者统一用 `pdal::pdal`。头文件包含根为 `include/`（布局
`include/pdal/io/...`），消费者引用用 `<pdal/io/BufferReader.hpp>`（注意与
上游源码内部 `<io/BufferReader.hpp>` 不同）。

## 测试

### 上游测试（未跑，说明原因）

上游单测（test/unit + pdal_test 二进制）需要 `test/data` 夹具树（149 MB，
含 autzen/lanie 数据集，部分还依赖网络下载）。packaged build 关闭了
WITH_TESTS，按 SKILL"非 100% 需说明"规则记录：上游 ctest 套件 0 跑
（exempted），替代验证为 test_package 实质 API 测试。

### test_package（实质测试，3/3 通过）

程序化生成 5 个点（X/Y/Z 维度注册，BufferReader 模式——同上游
LasWriterTest::auto_offset 的官方用法）→ LasWriter 写 LAS 文件 →
LasReader 读回 → 校验：
- 点数往返：5/5 ✓
- 坐标往返最大误差：0.000098（auto offset/scale 下精度优良）✓
- pdal::Config::fullVersionString() 非空 ✓

LAS 写读往返走的是真实 IO 链路（含 laszip 库内压缩路径、LAS 头解析），
能实际暴露 ABI/链接/运行时问题。

## 复现

```bash
cd archives/p/pdal/2.10.1
python3 -c "
from conans.conan import run
import sys, os
sys.argv = ['conan', 'create', '.', '--user=ohpcd', '--channel=stable',
            '-pr:h=' + os.path.expanduser('~/.conan2/profiles/ohos-aarch64'),
            '-pr:b=' + os.path.expanduser('~/.conan2/profiles/ohos-aarch64'),
            '--build=missing']
try: run()
except SystemExit: pass"
```

构建超时预算：`pdal/2.10.1 14400s`（ci/config/build_timeouts.txt 已登记，
W3 与 CI 同源）。
---

**编译结束**: 2026-09-03 01:23
**最终状态**: built
