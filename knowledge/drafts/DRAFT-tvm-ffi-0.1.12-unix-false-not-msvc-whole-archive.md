# DRAFT-tvm-ffi-0.1.12-unix-false-not-msvc-whole-archive
> stock CMake未知HarmonyOS致UNIX为假时改用NOT MSVC守卫注入whole-archive保留静态注册
## 问题特征（真实日志片段/标记）
- 动态链路期：`TVMFFIErrorMoveFromRaised: symbol not found` + `Error relocating`，tvm_ffi_tests无法解析刚构建的同目录.so。
- RPATH与LD_LIBRARY_PATH修复后指纹逐行不变，证伪加载器假设。
- 改静态链路后可运行但成簇失败：`93% tests passed, 27 tests failed out of 387`，`The following tests FAILED:`，失败集中Reflection.AutoInit、StructuralEqualHash、FindAccessPaths等依赖testing.cc字符串查表注册项，另有tvm_ffi_tests SEGFAULT。
- 平台守卫失效：追加`if(UNIX AND NOT APPLE)` whole-archive后12:30与12:06两轮`discovered=387 passed=360 failed=27`名单耗时字节级一致，预检日志明示`System is unknown to cmake, create: Platform/HarmonyOS`。
- 离线化触发：`fatal: unable to access 'https://github.com/google/googletest.git/': Failed to connect to github.com:443 after 65450 ms: Could not connect to server`，上游AddGoogleTest.cmake经FetchContent三次git clone中断，上游0/0/0。
- 修复后：`HMBS_UPSTREAM_TEST_RESULT={"discovered": 389, "executed": 387, "passed": 387, "failed": 0, "skipped": 2}`加2项上游DISABLED gaps，`HMBS_TEST_PACKAGE_RESULT={"discovered": 6, "passedCount": 6}`。
## 根因
- stock CMake 4.4.3无Platform/HarmonyOS模块，`CMAKE_SYSTEM_NAME=HarmonyOS`下`UNIX`变量未置位，向CMake注入的`if(UNIX AND NOT APPLE)`条件块恒为假，`--whole-archive`被静默跳过。
- 测试链路改STATIC后归档默认丢弃无符号引用的.o，`src/ffi/testing/testing.cc`与`container.cc`内`TVM_FFI_STATIC_INIT_BLOCK`字符串查表注册被静默丢弃，仅依赖注册的27项失败，360项纯头文件用例不受影响。
- 上游`FetchContent_Declare(googletest GIT_REPOSITORY https://github.com/google/googletest.git GIT_TAG v1.14.0)`写死github克隆，预检worker无直连必然失败，与编译链接层无关。
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. `archives/t/tvm-ffi/0.1.12/conanfile.py`内弃用手写.patch，改三次`replace_in_file(strict=True)`：`tvm_ffi_testing`由SHARED改STATIC、测试改链`tvm_ffi_static`、注入`if(NOT MSVC)`块以`LINKER:--whole-archive`同时拉入`tvm_ffi_static`与`tvm_ffi_testing`再`--no-whole-archive`；注释说明NOT MSVC仅因本配方限Linux/OHOS clang。
2. `conandata.yml`新增googletest条目v1.17.0 tarball有序列表（gh-proxy在前官方在后，sha256复用gtest/1.17.0.1同值），移除不可对齐上游的patches段。
3. `conanfile.py::source()`新增`_vendor_googletest()`拉取校验到googletest-src并打OHOS TMPDIR补丁；`generate()`置`tc.cache_variables[FETCHCONTENT_SOURCE_DIR_GOOGLETEST]`指向vendored源码使上游零修改跳过clone，另置`INSTALL_GTEST=OFF`/`INSTALL_GMOCK=OFF`关闭测试依赖安装规则。
4. 保持`-j1`串行、`-O1 -DNDEBUG -g0`全局与测试目标`-O0 -g0`削峰、分阶段串行构建、`ctest -j1 --timeout 120`与`ctest -N`双源计数口径不变；`notes.md`/`manifest.yaml`同步记录。
## 禁止策略
- 禁止保留`if(UNIX AND NOT APPLE)`守卫或仅用`$ORIGIN` RUNPATH与`LD_LIBRARY_PATH`处理静态注册丢失：两轮字节级一致失败已证伪，残留仍为`93% tests passed, 27 tests failed out of 387`。
- 禁止保留FetchContent github直连无回退：无直连worker必现`Failed to connect to github.com:443`中断，不得跳过测试或删除断言凑数。
## 与相近条目的边界（查重）
- 不同于通用RPATH/LD_LIBRARY_PATH运行时解析条目：本条目经两轮真机字节级一致失败证伪加载器手段后才转静态链路，判据是flag生效至少应改变部分结果。
- 不同于通用ctest解析条目：387/389双源计数与DISABLED gaps处理属配套审计，本条目核心是平台守卫致链接flag静默失效。
- 不同于补齐缺失apply_conandata_patches条目：本条目在补丁生效（NEEDED仅libc）后仍27失败，病因在归档丢弃注册而非补丁未应用。
## 适用判断
- 当stock CMake报`System is unknown to cmake`且配方向CMake注入平台相关条件块，同修复进真机后结果零变化怀疑flag未生效时适用本条目，改用`if(NOT MSVC)`。
- 当上游把测试二进制与被测共享库放同一构建输出目录且动态链接、目标平台加载器连续两轮无法解析同目录.so，且失败集中在依赖测试辅助库字符串查表注册的子集时适用静态加whole-archive。
- 当CMake项目经FetchContent写死GIT_REPOSITORY拉取googletest且worker无github直连时复用vendored tarball加FETCHCONTENT_SOURCE_DIR离线化模式。
