# DRAFT-bifrost-1.3.5-gate-shared-lib-nonpic-static-dep

上游 CMake 无条件构建共享库、其静态依赖归档非 PIC 时，aarch64 链接失败；
消费侧按 `BUILD_SHARED_LIBS` 门控共享库为可迁移解。

## 错误特征
```
Linking CXX shared library src/libbifrost.so
ld.lld: error: relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol 'z_errmsg'; recompile with -fPIC
ld.lld: error: relocation R_AARCH64_ADD_ABS_LO12_NC cannot be used against symbol 'z_errmsg'; recompile with -fPIC
clang-15: error: linker command failed with exit code 1
```
（conan create 构建阶段，bifrost 1.3.5 的 src/libbifrost.so 链接）

## 根因
上游 `src/CMakeLists.txt` **无条件** `add_library(bifrost_dynamic SHARED ...)`，并将其
`target_link_libraries` 到 `${ZLIB_LIBRARIES}`；registry 中 zlib/1.3.1 仅提供**非 PIC** 的
静态 `libz.a`（本地包目录只有 libz.a，无 libz.so）。aarch64 下把静态归档中的全局数据符号
（`z_errmsg`）编入共享库，必须位置无关代码，非 PIC 归档直接触发 relocation 错误。
依赖包无法在本地重建/替换时（registry 制品形态固定），依赖侧修复不可行，需消费侧处理。

## 修复
补丁 `src/CMakeLists.txt`：把 `add_library(bifrost_dynamic SHARED ...)`、其
`set_target_properties`、`target_link_libraries`、`install(TARGETS bifrost_dynamic ...)`
全部移入 `if(BUILD_SHARED_LIBS)` 分支；默认（`shared=OFF`）时 `target_link_libraries(Bifrost
bifrost_static)`，包不自带 `.so`，保留 shared 选项语义供显式开启。

```cmake
if(BUILD_SHARED_LIBS)
    add_library(bifrost_dynamic SHARED ${sources} ${headers})
    set_target_properties(bifrost_dynamic PROPERTIES OUTPUT_NAME "bifrost")
    target_include_directories(bifrost_dynamic PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
    target_link_libraries(bifrost_dynamic ${CMAKE_THREAD_LIBS_INIT})
    target_link_libraries(bifrost_dynamic ${ZLIB_LIBRARIES})
    target_link_libraries(Bifrost bifrost_dynamic)
    install(TARGETS bifrost_dynamic DESTINATION lib)
else()
    target_link_libraries(Bifrost bifrost_static)
endif()
```

## 实例
bifrost 1.3.5：`patches/0002-src-CMakeLists.txt.patch`；验证：`conan create` G2 通过、
test_package 消费者测试 ctest 1/1 Passed、`Bifrost --version`（L2 smoke）OK、L5 产物完整性 PASS。

## 边界与反例
- 适用：上游无条件构建共享库 + 静态归档依赖非 PIC + 依赖侧不可重编（registry 制品固定）。
- 反例/不适用：依赖可重建时优先依赖侧 `-fPIC`（E005/E541）或 test_package PIC 探针（E539）；
  纯头文件/纯静态项目不触发；x86-64 无此 relocation 限制。

## 关系
- similar_to: E005（-fPIC relocation）、E539（zlib PIC 探针）、E541（zlib static PIC 归档）、
  E288（BUILD_SHARED_LIBS 单目标）
- caused_by: registry 依赖静态归档非 PIC（zlib/1.3.1 仅 libz.a）
