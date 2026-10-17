# notes.md — devil 1.8.0.40.g6f3d5e9b

## 版本映射

`1.8.0.40.g6f3d5e9b` = `git describe` `1.8.0-40-g6f3d5e9b` 的点分形式：
tag `v1.8.0`（commit a2d9193f）之后正好 40 个提交，固定 commit
`6f3d5e9bc5d173f56060fc8e14bed35c8edcfdcc`（2021-08-29，合并 PR #91
jasper-callback-types-fix）。源码归档为 GitHub commit tarball（codeload 端点，
与 github.com/archive 字节一致），SHA256 已在设备侧经安全下载器校验固定
（conandata.yml）。

## 构建形态

- CMake 工程（archive 内 `DevIL/` 子目录）；conan 布局把源码解压到 `src/DevIL`，
  source folder 即工程根。
- 共享库 `libIL.so.1` / `libILU.so.1`（上游默认 BUILD_SHARED_LIBS=ON，
  SOVERSION=1）。注意上游 `src-ILU/CMakeLists.txt` 硬编码
  `add_library(ILU SHARED ...)`，因此静态构建需要额外上游改造，本配方不做。
- 依赖（全部来自制品仓）：zlib/1.3.2、libpng/1.6.58.2（shared）、libjpeg/10
  （static，fPIC=True）。TIFF/Jasper/MNG/LCMS2/OpenEXR/NVTT/Squish 保持上游
  可选探测，未找到即 IL_NO_* 禁用（tiff/mng/nvtt 仓内无配方）。

## OHOS 关键适配

1. **CMake 4 兼容**：上游 `cmake_minimum_required(2.6/2.8)` 被设备 CMake 4.1.2
   拒绝，传 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（leptonica/1.87.0 同法，已验证）。
2. **剔除 src-ILUT**（patches/0001）：`src-ILUT/CMakeLists.txt` 对
   OpenGL/GLUT `find_package(... REQUIRED)`，OHOS 无桌面 GL，configure 必挂；
   补丁注释掉顶层 `add_subdirectory(src-ILUT)`，IL/ILU 不受影响。ilut.h 不再安装
   （与未构建 ILUT 一致；上游 UnitTest.cpp 仅 `#include <IL/ilut.h>` 取声明，
   编译期走源码树 include，不链接 ILUT）。
3. **C++17**：`register` 存储类说明符在 C++17 非法（patches/0002，
   src-IL/src/il_manip.cpp）。
4. **PNG/JPEG 接线**：使用上游自己支持的"custom location"机制
   （`IL_PNG_LIB`/`IL_JPEG_LIB`=ON + `PNG_INCLUDE_DIRS`/`PNG_LIBRARIES`、
   `JPEG_INCLUDE_DIRS`/`JPEG_LIBRARIES`，见 src-IL/CMakeLists.txt 注释），
   跳过宿主 find_package 探测，直接以绝对路径链接 Conan 制品库，行为确定。
5. **CMAKE_SYSTEM_NAME=Linux**：不设时 CMake 回退 generic 平台模块，静默丢失
   SOVERSION/SONAME 处理（libIL.so 无 DT_SONAME、消费者记相对 DT_NEEDED 无法
   加载）；设为 Linux 恢复标准 soname/版本化命名。
6. **ELF 签名（关键）**：OHOS 动态加载器拒绝未签名的共享库/可执行文件
   （报 "Error loading shared library ..."，与路径无关——LD_LIBRARY_PATH、
   RUNPATH、cwd 均无效，实测定律）。配方在 build() 后对构建树
   `libIL.so.1`/`libILU.so.1`、两个上游测试可执行文件，在 package() 后对包内
   全部 `*.so*` 用 `binary-sign-tool sign -selfSign 1` 自签（libpng/1.6.58.2
   同一约定）；test_package 的 test_devil 在执行前同样签名。
7. **上游测试接线**（patches/0003）：上游 `test/UnitTest/CMakeLists.txt` 的
   include 接线是死的（`${cppunit_INCLUDE_DIRECTORIES}` 无人生成；
   `${DevIL_SOURCE_DIR}/../include` 指向工程外）——官方测试入口在原样状态下
   编译不过。补丁只修这两行接线，不动任何测试断言。cppunit 以
   `test_requires("cppunit/1.15.1")` 接入（ohpcd 制品仓有 ohos-aarch64
   精确匹配二进制），不进 devil 的消费者闭包。

## 上游测试（真实运行，非 NOT_RUN）

官方入口 `.travis.yml`（仓库根）：`cmake DevIL && make all UnitTest benchmark`。

- **UnitTest**（cppunit 断言套件，9 个活动测试）：build() 中构建并执行，
  PASS = cppunit `OK (9)` 且退出码 0。上游用例硬编码 Windows 相对路径
  （`.\Data\Logo.png` 等），POSIX 下是单个字面文件名——运行目录按这些字面名
  物化指向上游测试数据的文件即可，不改测试代码。测试落盘文件
  （`.\results\*.bmp`）同为字面名，困在运行目录内。
- **benchmark**（官方入口的一部分）：build() 中对上游测试图
  `test/UnitTest/Data/Logo.png` 跑 20 次 ilLoadImage；benchmark.c 恒返回 0，
  故错误栈非空即失败。上游自带的 `data/DevIL_logo.jpg` 在该 commit 是 0 字节
  文件（喂给 libjpeg 会触发 DevIL 错误路径的 double-destroy 上游缺陷），不使用。
- **ctest**：上游 `ENABLE_TESTING()` 但全树零 `add_test()`，`ctest -N` 为 0。
- **format_test 等 9 个测试目录**：上游 test/CMakeLists.txt 中全部注释
  （"TODO"），无目标，不接线。

## 已验证（预检 + 权威 CI）

- 预检：`conan create`（显式 ohos-aarch64 双 profile）设备端全绿。
- **权威 CI PASS**（2026-09-10，候选 d1e20501e8）：
  `CI_PACKAGES=archives/d/devil/1.8.0.40.g6f3d5e9b CONAN_PROFILE=ohos-aarch64
  ci/conan/build_and_test.sh`，CI_EXIT=0；L0/L1/L1e/L4/L5=pass，L2=skip
  （纯库）；Summary 1 success / 0 failed。CI 内 conan create 重建并真实执行
  上游两测试目标（cppunit `OK (9)`、benchmark 错误栈为空），L1e 破坏性反向
  验证通过。日志：设备 `<run>/logs/ci/`。
- cppunit/1.15.1 用 ohpcd 制品仓 ohos-aarch64 精确匹配二进制
  （test_requires，不进消费者闭包）。
- 加载器签名行为实测：未签名 libIL.so.1 在 LD_LIBRARY_PATH/RUNPATH/cwd
  三种方式下均拒载；自签后立即恢复加载（最小 C/C++ 消费者对照验证）。
- 补丁 0003 说明：src-IL/CMakeLists.txt 内含 project(DevIL) 会全局覆写
  `DevIL_SOURCE_DIR`（cache 变量），上游 `${DevIL_SOURCE_DIR}/../include`
  借此恰好解析到 src/DevIL/include（勿"顺手修正"为不带 `..` 的路径，
  那样反而指到 src-IL/include；首版补丁犯过此错，已收回）。

## 后续增强（未进首个候选）

- jasper/4.2.9（本 pin 恰为 Jasper 4.x 兼容修复，`IL_JASPER_LIB` 机制同 PNG/JPEG）、
  openexr、lcms2、libsquish；tiff/mng/nvtt 需先有配方。
