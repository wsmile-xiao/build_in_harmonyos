# jeolib-miallib 1.1.7 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-10-11
- 编译器: clang 15.0.4（OHOS SDK，aarch64-linux-ohos 真机目标）
- Profile: ci/conan/profiles/ohos-aarch64
- 状态: built（W3 finish 待 shapelib/1.5.0 发布后复跑）

## 编译步骤

```bash
conan create archives/j/jeolib-miallib/1.1.7 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

- 库本体 + test_package（create_image/histo1d/erode4/dilate4 实测）全绿。
- conan-verify G0/G1/G2/G3/G4 + L2/L4/L5 全绿（reports/conan-verify-report.md）。

## 依赖

zlib/1.3.1.1、gdal/3.9.2.3、libtiff/4.7.2（libgeotiff 传递约束）、libgeotiff/1.7.4、
proj/9.3.1.1、fftw/3.3.11、gsl/2.7、shapelib/1.5.0（**首次引入，需其 PR 先合入发布**）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `W_MSB` 未定义编译错误 | miallib.h 用 glibc 专有宏 `__WORDSIZE` 判定指针宽度，OHOS musl 未定义 | patch 0002：用 `__LP64__/_LP64/架构宏` 探测（portability） |
| 2 | `tiffio.h` 找不到 | 上游 find_package(TIFF) 后只链接不 include（系统级构建时头文件恰好在 /usr/include） | patch 0001：补 `include_directories(${TIFF_INCLUDE_DIRS})` |
| 3 | FFTW 用 pkg_search_module(fftw3)，conan 构建时 PKG_CONFIG_PATH 不含依赖 .pc | pkg-config 查询不可用 | patch 0001：改 find_path/find_library |
| 4 | GSL: `${GSL_LIBRARIES}` 为空（CMakeDeps 变量名为包名小写） | 变量名不匹配且裸 -lgsl 缺 -L | patch 0001：find_path/find_library 显式链接 gsl+gslcblas |
| 5 | 链接错误：大量 `__kmpc_*` 未定义 | 上游在 if/else 之外无条件 `set(CMAKE_C_FLAGS -fopenmp)`，而 OHOS 设备默认无 libomp 运行时 | patch 0001：该行受 `if(PROCESS_IN_PARALLEL)` 保护；配方设 PROCESS_IN_PARALLEL=OFF（串行） |
| 6 | projection.c 编译不过 | 使用 PROJ4 遗留 API（proj_api.h/pj_init/pj_transform），PROJ≥6 已移除；上游注释自认 "Need to be adapted for PROJ > 6.0" | patch 0001：从 SOURCES 移除 projection.c（经查全树无任何调用方，仅 projection.c/miallib_proj.h 自引用） |
| 7 | 安装后消费者找不到 miallib.h | 上游 MIALLIB_H 安装列表遗漏主头文件 miallib.h，且 config_miallib.h 未安装 | patch 0001：安装列表补齐两者 |

## 语言判定（R47 边界说明）

- lang-preflight 自动判定 mixed（依据 swig/ 目录 12 个 Python SWIG 绑定文件与 setup.py）。
- 人工复核：core/c 105 个 C 文件为主体（≈90%），setup.py 仅为可选 SWIG Python 绑定的打包脚本，
  conan 流程不构建 swig/。按 R47「辅助绑定不计主体」判定为 C 库，继续适配。

## 上游测试（R51 三步法）

- 上游 tarball 未提供任何测试套件/ctest 注册（无 tests/ 目录、无 CTestTestfile），
  N=0 可运行上游用例；以 test_package L1 消费者实测替代（PASS）。

## 源码修改

- patches/0001-cmake-find-deps-and-drop-legacy-proj4.patch（CMakeLists.txt，见上表 2/3/4/6/7）
- patches/0002-fix-wordsize-for-musl.patch（core/c/miallib.h，见上表 1）

## 遗留事项

- shapelib/1.5.0 尚未发布到 ohpcd 制品仓 → W3 finish 的 L0i 门禁阻塞（R36 拓扑顺序）。
  shapelib PR 合入并由发布流水线上传后，复跑 `finish jeolib-miallib 1.1.7`。
- OpenMP：真机默认无 libomp.so，故串行构建（PROCESS_IN_PARALLEL=OFF）；
  clang 15 SDK 提供 libomp.a，后续如需并行可再评估。

---
**编译结束**: 2026-10-11
**最终状态**: built
