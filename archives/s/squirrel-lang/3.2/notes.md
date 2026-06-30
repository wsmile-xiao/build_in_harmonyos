# squirrel-lang 3.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-11
- 编译器: clang/clang++ 15.0.4
- 状态: published

## 编译步骤

1. 下载源码：SSL证书问题，用 `curl -fsSLk` 手动下载 tar.gz 到 `~/tmp/builds/squirrel-lang-3.2.tar.gz`
2. init-build：`python3 $SKILL_ROOT/scripts/ohc-run.py init-build squirrel-lang 3.2 --url=... --no-download`
   - 源码解压后嵌套在 `squirrel3` 子目录，脚本自动提升到 `.work` 根目录
   - init-build 完成后检测到嵌套目录并自动处理
3. 源码包缺少 `squirrel-config.cmake.in`（CMakeLists.txt 第84行引用但文件不存在），手动创建：
   ```cmake
   @PACKAGE_INIT@
   include("${CMAKE_CURRENT_LIST_DIR}/squirrel-targets.cmake")
   check_required_components(squirrel)
   ```
4. CMake configure（out-of-source build）：
   ```
   cd build && cmake .. \
     -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
     -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
     -DCMAKE_C_FLAGS="-fPIC -O2" \
     -DCMAKE_CXX_FLAGS="-fPIC -O2 -fno-rtti -fno-exceptions" \
     -DCMAKE_POLICY_VERSION_MINIMUM=3.5
   ```
5. CMake 版本兼容性：CMake 4.x 不再支持 cmake_minimum_required < 3.5，
   需要 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 绕过限制
6. `make -j2` 编译成功，生成 sq/sq_static 二进制和 squirrel/sqstdlib 共享+静态库
7. `make install DESTDIR=$TEST_PREFIX` staging 安装到隔离目录
8. patchelf 修复共享库 SONAME 问题（CMake 构建时的已知问题）：
   - sq 的 NEEDED 引用 `../lib/libsqstdlib.so` 和 `../lib/libsquirrel.so`（构建时相对路径）
   - libsqstdlib.so 的 NEEDED 引用 `../lib/libsquirrel.so`
   - 修复：`patchelf --replace-needed ../lib/libsqstdlib.so libsqstdlib.so` + `--set-rpath`
9. ELF 签名（sign-elf）使修复后的 sq 和共享库可在 OpenHarmony 上执行
10. `make install`（不带 DESTDIR）安装到 `$DEFAULT_PREFIX`，模拟用户部署
11. 功能验证：sq_static 和 sq 均可执行脚本，13 项功能测试全部通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败，init-build下载失败 | 平台SSL根证书过期 | `curl -fsSLk` 手动下载，`--no-download` 绕过init-build下载步骤 |
| 2 | squirrel-config.cmake.in 缺失 | 源码包不完整，CMakeLists.txt引用了不存在文件 | 手动创建该模板文件，track-edit 记录追踪 |
| 3 | cmake_minimum_required(VERSION 3.4) 版本限制 | CMake 4.x 移除了 <3.5 的兼容性 | `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 绕过 |
| 4 | sq 共享库 NEEDED 引用 ../lib/ 相对路径 | CMake 将构建输出目录设为 ../lib/，SONAME含相对路径 | patchelf --replace-needed 修复SONAME + --set-rpath 设置 RUNPATH |
| 5 | DISABLE_DYNAMIC 导致 CMake alias bug | sq/CMakeLists.txt 中 squirrel::interpreter_static alias 引用 sq 而非 sq_static | 构建全部（动态+静态），用 patchelf 修复动态版本 |
| 6 | patchelf 修改本地安装文件后 Operation not permitted | 已ELF签名的文件不允许被再次修改 | 先在 staging 区修复，再手动 cp 到本地 prefix |
| 7 | make install 后 sq 被 rebuild | patchelf 改了文件时间戳，cmake 重新链接 | 从 staging 区直接复制修复后的文件 |

## 源码修改

- **新增文件**: squirrel-config.cmake.in（CMake package config 模板）
  - 路径: 源码根目录
  - 内容: `@PACKAGE_INIT@` + `include("squirrel-targets.cmake")` + `check_required_components(squirrel)`
  - 补丁: 0001-squirrel-config.cmake.in.patch

## 依赖版本

- 无外部依赖
- libc++_shared.so（系统 musl 提供）
- libc.so（系统 musl 提供）

## 验证结果

13 项功能测试全部通过，详见 reports/test-report.md

核心验证摘要：
- sq_static -v → "Squirrel 3.2 stable (64 bits)"
- sq -v → "Squirrel 3.2 stable (64 bits)"（需 LD_LIBRARY_PATH）
- 基础脚本、数学运算、递归函数、类与对象、数组、哈希表、
  字符串操作、数学标准库、闭包、异常处理、字节码编译 → 全部 PASS

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/sq | 27KB | 动态链接解释器（需 LD_LIBRARY_PATH） |
| bin/sq_static | 342KB | 静态链接解释器（自包含，推荐） |
| lib/libsquirrel.so | 338KB | squirrel 核心共享库 |
| lib/libsquirrel_static.a | 437KB | squirrel 核心静态库 |
| lib/libsqstdlib.so | 84KB | 标准库共享库 |
| lib/libsqstdlib_static.a | 102KB | 标准库静态库 |
| include/*.h | 8个 | 头文件（squirrel.h, sqconfig.h, sqstdaux.h 等） |
| lib/cmake/squirrel/ | cmake config | CMake 查找模块 |

## 注意事项

- sq_static（静态链接）推荐用于 OpenHarmony 平台，无需额外库依赖
- sq（动态链接）需要 `LD_LIBRARY_PATH` 或 RUNPATH 正确指向 `$PREFIX/lib`
- CMake 4.x 需要 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 参数
- 共享库 SONAME 含相对路径 `../lib/` 是 CMake 构建时已知问题，需 post-build patchelf 修复
- 源码包缺少 squirrel-config.cmake.in 文件（上游遗漏）

---

**编译结束**: 2026-06-11
**最终状态**: published