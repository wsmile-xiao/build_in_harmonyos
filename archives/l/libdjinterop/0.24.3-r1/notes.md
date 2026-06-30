# libdjinterop 0.24.3-r1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-01 (验证更新: 2026-06-02)
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: published

## 编译步骤

1. 下载源码: 从 GitHub xsco/libdjinterop 0.24.3 tag 下载
2. 安装预编译依赖: zlib 1.3.1, sqlite3 3.49.1 (cmd-pkgs)
3. 修改 CMakeLists.txt:
   - 移除 `-Werror` 编译选项 (OHOS 平台无害警告会导致构建失败)
   - 用 `BUILD_TESTING` 条件守卫包裹测试代码 (Boost pthread_setcancelstate 不可用)
   - 将 pkg-config 生成条件从 `if(UNIX)` 改为 `if(UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")`
4. cmake configure:
   ```bash
   cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
     -DCMAKE_BUILD_TYPE=Release \
     -DBUILD_SHARED_LIBS=OFF \
     -DSYSTEM_SQLITE=ON \
     -DCMAKE_C_COMPILER=clang \
     -DCMAKE_CXX_COMPILER=clang++ \
     -DCMAKE_C_FLAGS="-fPIC -O2" \
     -DCMAKE_CXX_FLAGS="-fPIC -O2" \
     -DBUILD_TESTING=OFF \
     -DBUILD_DOC=OFF
   ```
5. make -j2 → 编译成功 (libdjinterop.a 静态库)
6. make install DESTDIR=$TEST_PREFIX → staging 安装

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake 找不到 ZLIB | PKG_CONFIG_PATH 未包含 ~/usr/local/lib/pkgconfig | 安装 zlib 1.3.1 预编译包 + 设置 PKG_CONFIG_PATH |
| 2 | cmake 找不到 SQLite3 | 未安装 sqlite3 预编译包 | 安装 sqlite3 3.49.1 预编译包 |
| 3 | Boost 测试编译失败: pthread_setcancelstate 未声明 | OHOS musl 不支持 pthread_setcancelstate | 用 BUILD_TESTING 条件守卫禁用测试编译 |
| 4 | -Werror 导致编译失败 | OHOS 平台可能触发无害警告 | 移除 -Werror 编译选项 |
| 5 | pkg-config 文件不生成 | CMake 将 HarmonyOS 不识别为 UNIX | 修改条件为 `UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS"` |

## 源码修改

- CMakeLists.txt: 3处修改 (详见 patches/0001-CMakeLists.txt.patch)

## 依赖版本

- zlib 1.3.1 (预编译包)
- sqlite3 3.49.1 (预编译包)

## 2026-06-02 功能验证结果

### 质量门禁
- G0: ✅ PASS (手动验证, cmake 项目)
- G1-G4: ✅ PASS (verify-build 全部通过)

### C++ API 测试
- ✅ Header includes: 14 个头文件正确包含
- ✅ create_temporary_database(schema_2_20_2): 创建数据库成功
- ✅ db.tracks(): 返回空列表 (新数据库)
- ✅ db.schema_version(): 返回 schema 版本
- ✅ db.uuid(): 返回 UUID
- ✅ semantic_version{1,2,3}: 结构体初始化正常
- ✅ 链接完整性: pkg-config --libs djinterop 正确

### pkg-config 测试
- ✅ --modversion: 0.24.3
- ✅ --libs: -L~/usr/local/lib -ldjinterop -lz -lsqlite3
- ✅ --cflags: -I~/usr/local/include

### 预编译包
- libdjinterop-0.24.3-r1-ohos-aarch64.tar.gz (14.2MB, 含静态库+头文件+cmake配置+pkgconfig)
- 内容: 45+ 文件 (include/djinterop/*.hpp, lib/libdjinterop.a, lib/pkgconfig/djinterop.pc, lib/cmake/DjInterop/*)

### 上库判定: ✅ 符合要求

### 补丁名称修复
- manifest.yaml 中 patches_applied 从 `0001-cmake-ohos-adaptations.patch` 修正为 `0001-CMakeLists.txt.patch` (与实际文件名一致)

## 注意事项

- 编译为静态库 (BUILD_SHARED_LIBS=OFF)，用户链接时需 `-std=c++20 -lz -lsqlite3`
- 单元测试依赖 Boost，在 OHOS 上因 pthread_setcancelstate 缺失而无法编译
- CMake 检测系统为 HarmonyOS (未知平台)，部分 UNIX 条件判断需额外适配
- 用户代码需设置 `TMPDIR=$HOME/tmp` 避免 /tmp 只读问题
---