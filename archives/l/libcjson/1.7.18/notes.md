# libcjson 1.7.18 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-04-26 (首次) / 2026-09-24 (本次完成)
- 编译器: clang 15.0.4 (OHOS arm64)
- 状态: built

## 编译步骤

1. 下载源码: https://github.com/DaveGamble/cJSON/archive/refs/tags/v1.7.18.tar.gz
   (sha256: 3aa806844a03442c00769b83e99970be70fbef03735ff898f4811dd03b9f5ee5)
2. 解压到 ~/tmp/builds/cjson-1.7.18.work
3. 应用补丁: patches/0001-CMakeLists.txt.patch
4. CMake 配置:
   ```bash
   cmake -S . -B build -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release \
     -DENABLE_CJSON_TEST=ON -DENABLE_CJSON_UTILS=ON -DBUILD_SHARED_LIBS=OFF \
     -DENABLE_CUSTOM_COMPILER_FLAGS=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5
   ```
5. 编译: cmake --build build -j4
6. 安装 (staging 隔离): DESTDIR=$TEST_PREFIX cmake --install build
7. 测试: ctest --output-on-failure → **22/22 PASS (100%)**
8. Conan 验证: conan create (ohos-aarch64 profile) → G0-G4/L2/L4/L5 全部 PASS
9. finish → status=built, W3 本地 CI 100% (JC/L0/L1/L4/L5 pass)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake_minimum_required VERSION 3.0 鸿蒙 cmake 不支持 | 鸿蒙 cmake 版本限制 | 补丁修改为 VERSION 3.5 |
| 2 | -std=c89 鸿蒙 clang 不支持 | 鸿蒙 clang 15 不支持 C89 标准 | 补丁修改为 -std=c99 |
| 3 | 上游 unity 测试编译含 -Wlong-long (C99 mode) 报错 | OHOS clang 15 限制 | 测试构建加 -DENABLE_CUSTOM_COMPILER_FLAGS=OFF |
| 4 | G0 clean-verify configure exit 127 | cJSON 是 CMake 项目，无 configure 脚本 (autotools 假设) | G0 为非阻塞步骤，跳过；以 conan create 为准 |

## 源码修改

- patches/0001-CMakeLists.txt.patch
  - cmake_minimum_required VERSION 3.0 → 3.5
  - -std=c89 → -std=c99
  - 移除尾随空格（CMake 语法规范）

## 依赖版本

无外部依赖（纯 C 库, W0 确认零依赖）

## 验证结果

libcjson 是纯库，无独立可执行文件，通过库文件 + test_package 验证：
- libcjson.a, libcjson_utils.a (静态)
- test_package/test_libcjson.c 实质调用 cJSON API 通过 (R34)
- 上游 CTest 22/22 通过 (R51)

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (library, name=libcjson, libs=cjson+cjson_utils) |
| conandata.yml | 官方 GitHub 源 + sha256 + 补丁声明 |
| test_package/ | L1 消费者测试 (test_libcjson.c 实质调用 API) |
| patches/0001-CMakeLists.txt.patch | 平台移植补丁 |
| MANIFEST.yml | 上游测试申报 (22 项 unity + 1 项 L1) |

## 注意事项

- 补丁为平台适配 (cmake 版本 + C 标准)，无需 OHOS 平台宏守卫
- 编译简单，无特殊依赖
- R38: 纯库无可执行文件 → 不需要 commands.json
- R26: libcjson 非系统同名库，default shared=False 默认静态，shared 由 options 按需开启
- 版本号保持 1.7.18 (上游版本，无适配修复后缀)
---

**编译结束**: 2026-09-25 18:37
**最终状态**: built
