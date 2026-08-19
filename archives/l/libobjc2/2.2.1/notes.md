# libobjc2 2.2.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-19
- 编译器: clang/clang++ (clang 15.0.4, aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 1. 下载源码 (GitHub 不可达, 使用 codeload.github.com)
curl -fsSL -o libobjc2-2.2.1.tar.gz \
  "https://codeload.github.com/gnustep/libobjc2/tar.gz/refs/tags/v2.2.1"

# 2. 下载 robin-map (FetchContent 依赖, 同样使用 codeload)
curl -fsSL -o robin-map-1.2.1.tar.gz \
  "https://codeload.github.com/Tessil/robin-map/tar.gz/refs/tags/v1.2.1"

# 3. CMake 配置 + 编译
mkdir Build && cd Build
cmake .. -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release \
  -DFETCHCONTENT_SOURCE_DIR_ROBINMAP=/path/to/robin-map-1.2.1 \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DTESTS=ON
make -j4          # 100% 编译成功, 产出 libobjc.so
make install DESTDIR=$TEST_PREFIX   # staging 隔离安装

# 4. 测试
ctest             # 190 用例, 180 通过 (94.7%)
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 不可达, 源码下载失败 | 网络限制 | 改用 codeload.github.com |
| 2 | cmake FetchContent 拉取 robin-map 失败 | GitHub 不可达 | 本地下载 robin-map v1.2.1, FETCHCONTENT_SOURCE_DIR_ROBINMAP 指向本地 |
| 3 | robin-map CMakeLists 版本过旧报错 | cmake_minimum_required(VERSION 2.8) 与 CMake 4.x 不兼容 | -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 4 | conan get() 报 BadZipFile | codeload URL 无 .tar.gz 后缀, 无法识别格式 | conandata.yml sources 增加 filename 字段 |
| 5 | 10 个 C++ 异常互操作测试失败 | 鸿蒙 libunwind 未实现 _Unwind_Resume() | 平台限制, 记录到 test-report; 库核心功能全部通过 |
| 6 | W3 L0k 门禁误报 commands_json_r38 | conanfile.py package_info() 声明 bindirs=["bin"] | 移除 bindirs 声明 (纯库无 bin 产物) |

## 源码修改

无源码补丁 (patches/ 为空)。适配逻辑全部在 conanfile.py 配方中:
- CMake 构建 (替换 autotools 模板)
- robin-map vendored 下载与 FETCHCONTENT 指向
- CMAKE_POLICY_VERSION_MINIMUM 处理

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| tsl-robin-map | 1.2.1 | vendored (codeload) |

## 验证结果

```bash
$ ctest
95% tests passed, 9 tests failed out of 190
Total Test time (real) = 21.37 sec
# 失败: ObjCXXEHInterop 系列 8 例 + CXXExceptions 1 例 (鸿蒙 libunwind 平台限制)

$ conan-verify libobjc2 2.2.1
✅ G0-G4 + L2/L4/L5 全部通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方 (含 robin-map vendored 处理) |
| conandata.yml | 源码 URL + sha256 + robin-map 信息 |
| test_package/ | 消费者测试 (L1) + MANIFEST.yml 上游 190 用例声明 |
| reports/test-report.md | 测试报告 (180/190 通过) |

## 注意事项

1. 本库为 GNUstep 生态依赖链最底层 (libobjc2 → gnustep-make → gnustep-base → ...)
2. 鸿蒙 libunwind 的 _Unwind_Resume 限制会影响上层 gnustep 的 C++ 异常相关功能
3. 上游版本号 2.2.1 的 SONAME 为 libobjc.so, 库名在 cpp_info.libs 中为 "objc"
---

**编译结束**: 2026-08-19 09:58
**最终状态**: built
