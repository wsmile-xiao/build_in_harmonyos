# librttopo 1.1.0 编译笔记

## 编译信息
- 编译日期: 2026-07-29
- 构建系统: CMake（原 autotools，因 OHOS 缺 aclocal 改用 CMake）
- 编译类型: 静态库

## 编译过程
1. 下载源码: https://sources.voidlinux.org/librttopo-1.1.0/librttopo-1.1.0.tar.gz
   - sha256: 2e2fcabb48193a712a6c76ac9a9be2a53f82e32f91a2bc834d9f1b4fa9cd879f
   - 上游 gitlab.com/rttopo/librttopo 返回 403，改用 voidlinux 镜像
2. 依赖: GEOS 3.13.0（通过 Conan CMakeDeps 注入 GEOS::geos_c）
3. CMake 配置:
   - `-DCMAKE_BUILD_TYPE=Release`
   - `-DBUILD_SHARED_LIBS=OFF`（静态库，避免动态库加载问题）
4. 适配关键:
   - 注入 CMakeLists.txt 替换不可用的 autotools
   - 生成 rttopo_config.h（HAVE_ISFINITE、RTGEOM_GEOS_VERSION=31300、RTGEOM_DEBUG_LEVEL=0）
   - 从 librttopo_geom.h.in 生成 librttopo_geom.h（@SRID_MAX@=999999、@SRID_USR_MAX@=918999）
5. 编译: cmake --build 成功，生成 librttopo.a (757KB)

## 验证测试
- conan create 成功（OHOS aarch64）
- test_package 通过（实质单元测试，增强版）:
  - librttopo version: 1.1.0
  - RTCTX initialized
  - Empty POINT constructed, type=1
  - POINT SRID after set: 3857
  - Empty LINESTRING constructed
  - is_collection(POINT)=0, is_collection(LINESTRING)=0
  - POINT(3 4) area=0.000000
  - POINT WKT: POINT(3 4)
  - LINESTRING(0 0, 0 2) length=2.000000
  - LINESTRING WKT: LINESTRING(0 0,0 2)
  - PASS: librttopo API unit tests - context, geometry construction, SRID, area/length, WKT

## 产物
- lib/librttopo.a (757 KB)
- include/librttopo.h
- include/librttopo_geom.h

## 上游测试通过率
- librttopo 上游无测试套件（已查证：无 test 目录、3 个 Makefile.am 均无 TESTS/check_PROGRAMS、configure.ac 无 make check 配置、docker/build-test 仅为 Docker 构建环境）
- 适配后 test_package 为实质单元测试，覆盖：context 初始化（rtgeom_init）、带坐标几何构造（rtpoint_construct/rtline_construct/ptarray_construct/ptarray_set_point4d）、SRID 往返（rtgeom_set_srid/rtgeom_get_srid）、面积/长度计算（rtgeom_area/rtgeom_length）、WKT 输出（rtgeom_to_wkt）、几何类型判断（rtgeom_is_collection）、bbox 操作（rtgeom_needs_bbox/rtgeom_add_bbox/rtgeom_get_bbox），全部通过

---
**编译结束**: 2026-07-29
**最终状态**: built（本地验证通过，待 CI upload 后更新为 published）
