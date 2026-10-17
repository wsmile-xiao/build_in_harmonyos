# perceptualdiff 2.1 适配笔记

## 编译环境
- 构建系统: CMake（上游 CMakeLists.txt）
- 编译日期: 2026-09-21
- 编译器: clang/clang++ 15.0.4（OHOS，libc++，C++17）
- CMake: 4.1.2 / 本机 profile `ohos-aarch64`（os=OHOS 6.0, arch=armv8, Release）
- 状态: built

## 上游概况
- 仓库: https://github.com/myint/perceptualdiff （tag `v2.1`）
- 构成: `pdiff` 小库（lpyramid/rgba_image/metric）+ `perceptualdiff` 命令行工具 + `test/run_tests.bash` 回归脚本
- 图像 IO 全部经 FreeImage（`rgba_image.cpp` 是唯一 FreeImage 使用点）
- FreeImage 在制品仓有成品包 `freeimage/3.18.0`（armv8/OHOS 6.0/clang15/libc++/shared，含全部内置编解码器）→ **不需要重写 IO 后端**

## 源码变更
仅 1 个补丁：`0001-cmake-ohos-conan-adaptation.patch`（CMakeLists.txt，4 处改动）

1. **cmake_minimum_required 前移并抬版本**：上游第 1 行是 `project()`、第 3 行才是
   `cmake_minimum_required(VERSION 2.4)`。CMake 4.1.2 直接拒绝：
   `Compatibility with CMake < 3.5 has been removed from CMake`。改为文件首行
   `cmake_minimum_required(VERSION 3.5)`（同时消除 “should be called prior to project()” 警告）。
2. **尊重外部 CMAKE_BUILD_TYPE**：上游硬写 `set(CMAKE_BUILD_TYPE Debug)`，会把 Conan 传入的
   Release 覆盖成 Debug（实测编译行出现 `-g`）。改为 `if(NOT CMAKE_BUILD_TYPE)` 包裹，
   保留上游默认行为且不再覆盖外部设定。
3. **FreeImage 走 Conan imported target**：`find_package(FreeImage)` 在本环境命中 CMakeDeps 生成的
   `freeimage-config.cmake`（CONFIG 模式），该 config 只声明 imported target
   `freeimage::freeimage`，**不会**定义上游依赖的 `FREEIMAGE_INCLUDE_DIRS`/`FREEIMAGE_LIBRARIES`
   变量 → 编译期 `fatal error: 'FreeImage.h' file not found`。补丁增加
   `if(TARGET freeimage::freeimage)` 分支：命中则把 `FREEIMAGE_LIBRARIES` 指向该 target，
   否则退回原 `include_directories(${FREEIMAGE_INCLUDE_DIRS})` 路径（非 Conan 环境行为不变）。
   同时把依赖同时挂到 `pdiff` 与 `perceptualdiff`（上游只挂了可执行文件，
   但 `pdiff` 的 `rgba_image.cpp` 才是真正 include FreeImage 的地方）。
4. **安装规则补全库与头文件**：上游只有 `install(TARGETS perceptualdiff DESTINATION bin)`。
   追加 `install(TARGETS pdiff ARCHIVE DESTINATION lib)` 与
   `install(FILES exceptions.h lpyramid.h metric.h rgba_image.h DESTINATION include/perceptualdiff)`，
   使包可作为库被消费（README 的 “Usage as a library” 形态：`#include <perceptualdiff/metric.h>`）。

补丁纪律验证：`git apply --check` 通过；在 tar 解压的干净 `.orig` 树上应用后与 `.work` 树
`diff = 0`；conandata.yml 的 patches 声明与 patches/ 目录一致。

## 编译步骤
```bash
conan create . --build=missing -pr:h=default -pr:b=default
```
配方内部：`CMakeToolchain` + `CMakeDeps` + `VirtualRunEnv` → `cmake.configure()` → `cmake.build()`
→ 上游回归脚本 → `cmake.install()`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Compatibility with CMake < 3.5 has been removed` | CMake 4.1.2 不再接受 `cmake_minimum_required(VERSION 2.4)` | 补丁 0001：抬到 3.5 并前移到 `project()` 之前 |
| 2 | 编译期 `'FreeImage.h' file not found` | CONFIG 模式命中 CMakeDeps 的 `freeimage-config.cmake`，上游用的 `FREEIMAGE_INCLUDE_DIRS` 变量不存在 | 补丁 0001：改用 `freeimage::freeimage` imported target 并同时挂到 pdiff |
| 3 | Release 构建仍带 `-g` | 上游 `set(CMAKE_BUILD_TYPE Debug)` 覆盖 Conan 传入值 | 补丁 0001：条件化该赋值 |
| 4 | 回归脚本报 `perceptualdiff must be built and exist in the repository root or the "build" directory` | `test/run_tests.bash` 只查找 `../build`、`..`、`../obj*`，Conan 构建目录在缓存区 | build() 中先把产物复制到 `<source>/build/`，再以 `env="conanrun"` 运行脚本 |
| 5 | 直接运行二进制报 `Error loading shared library libfreeimage.so.3` | 产物无 RPATH，运行时需依赖库路径 | 配方 `VirtualRunEnv` 生成 `conanrun.sh`；`self.run(..., env="conanrun")` 注入 `LD_LIBRARY_PATH` |

## 上游测试实测（OHOS aarch64 本机）
`bash test/run_tests.bash`（脚本为 `bash -eux`，任一断言失败即非零退出）：

```
*** testing executable binary ../build/perceptualdiff
*** all 7 tests passed
OpenMP status: enabled
perceptualdiff 2.1
Usage: perceptualdiff image1 image2
diff.png
Warning: option/file "--fake-option" ignored
...
PASS: Images are binary identical
OK
```

- 结果：`rc = 0`，26/26 全通过（7 个图像对回归 + 19 个 CLI 行为断言）
- 未修改上游任何测试文件
- OpenMP 实际启用（`OpenMP status: enabled`），命中 SDK 自带 libomp 5.0（`-fopenmp=libomp`）

## 依赖版本
- freeimage/3.18.0（制品仓成品包，shared，含 PNG/TIFF/JPEG 等内置编解码器）

## 交付物（package）
| 文件 | 说明 |
|------|------|
| `bin/perceptualdiff` | 命令行工具 |
| `lib/libpdiff.a` | 静态库（pdiff） |
| `include/perceptualdiff/*.h` | 公共头（exceptions.h / lpyramid.h / metric.h / rgba_image.h） |
| `licenses/LICENSE` | GPL-2.0-or-later |

## 注意事项
- 上游 `add_test(run_tests.bash, "${PROJECT_SOURCE_DIR}/test/run_tests.bash")` 参数写法有误
  （逗号 + 未拆分参数），`ctest` 无法直接驱动；因而回归套件在配方 `build()` 中直接以脚本方式调用，
  这是上游测试的**原生入口**（README 与 `.travis.yml` 同样直接跑该脚本），未修改上游文件。
- `pdiff` 为静态库，消费者链接时由 CMakeDeps 的传递依赖自动带上 `freeimage`。
