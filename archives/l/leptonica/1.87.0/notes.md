# leptonica 1.87.0 适配笔记

## 编译环境

- 构建系统: cmake（因 autogen.sh 失败，libtoolize 脚本 shebang 路径问题）
- 编译日期: 2026-07-09
- 编译器: clang 15.0.4 / clang++
- Conan 版本: 2.29.1
- Python 版本: 3.12.9
- 状态: published

## Conan 配方构建

通过 `conan create` 驱动 CMake 构建，配方为 `conanfile.py`。

### 构建配置

```python
# conanfile.py generate() 关键配置
tc.variables["BUILD_SHARED_LIBS"] = False          # 静态库
tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"  # 兼容旧版 cmake_minimum_required
tc.variables["BUILD_PROG"] = False                 # 不编译工具程序
tc.variables["CMAKE_DISABLE_FIND_PACKAGE_PNG"] = True
tc.variables["CMAKE_DISABLE_FIND_PACKAGE_JPEG"] = True
tc.variables["CMAKE_DISABLE_FIND_PACKAGE_TIFF"] = True
tc.variables["CMAKE_DISABLE_FIND_PACKAGE_GIF"] = True
tc.variables["CMAKE_DISABLE_FIND_PACKAGE_WebP"] = True
tc.variables["CMAKE_DISABLE_FIND_PACKAGE_OpenJPEG"] = True
```

### 依赖关系

| 依赖 | 版本 | Channel | 说明 |
|------|------|---------|------|
| zlib | 1.3.1 | @ohpcd/stable | 唯一 Conan 依赖 |

> PNG/JPEG/TIFF/GIF/WebP/OpenJPEG 均通过 `CMAKE_DISABLE_FIND_PACKAGE_*` 禁用，不作为依赖。

### 构建命令

```bash
# 构建 @ohpcd/stable channel 包
conan create archives/l/leptonica/1.87.0/ --user=ohpcd --channel=stable \
  -pr:b=default -pr:h=default --build=missing

# CI 验证
CI_PACKAGES="archives/l/leptonica/1.87.0" zsh ci/conan/build_and_test.sh
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autogen.sh 失败 | libtoolize 脚本 shebang 路径错误（期望 /storage/Users/currentUser/usr/local/bin/bash，实际在 /data/service/hnp/bin/bash） | 改用 cmake 构建系统（源码包含 CMakeLists.txt） |
| 2 | cmake 警告 "System is unknown" | 鸿蒙系统不在 cmake 已知平台列表中 | 忽略警告，cmake 仍能正常工作 |
| 3 | JPEG 符号未定义链接错误 | 系统存在 libjpeg 但 leptonica 链接时找不到完整符号 | 通过 CMAKE_DISABLE_FIND_PACKAGE_JPEG 禁用 JPEG 支持 |

## 源码修改

无补丁，使用 cmake 构建系统替代 autotools。

## CI 验证结果（2026-07-09，Python 3.12.9 + Conan 2.29.1）

| 门禁 | 结果 | 详情 |
|------|------|------|
| L0 | PASS | L0i ok (zlib 在制品仓)，L0j ok (首次发布)，L0k ok (库无需 commands.json) |
| L1 | PASS | test_leptonica Passed, `leptonica version: leptonica-1.87.0` |
| L1e | PASS | 破坏性反向验证 — 移除 lib/include 后测试失败，确认真实依赖 |
| L2 | SKIP | 纯库软件无 bin/ |
| L4 | PASS | 无补丁 |
| L5 | PASS | lib/ 有内容 |

## 交付物

| 文件 | 说明 |
|------|------|
| libleptonica.a | 静态库（主库） |
| lept.pc | pkg-config 文件 |
| LeptonicaConfig.cmake | cmake 配置文件 |
| leptonica/*.h | 头文件（约 40 个） |

## 注意事项

1. **构建系统**: 使用 cmake 构建，autotools 失败
2. **纯库软件**: 无可执行二进制文件，CI L2 smoke test 跳过
3. **可选依赖全部禁用**: PNG/JPEG/TIFF/GIF/WebP/OpenJPEG 均通过 CMAKE_DISABLE_FIND_PACKAGE_* 禁用，仅链接 zlib
4. **静态库**: 生成静态库 libleptonica.a

---

**编译结束**: 2026-07-09
**最终状态**: published
**Conan 引用**: `leptonica/1.87.0@ohpcd/stable`
