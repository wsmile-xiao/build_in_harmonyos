# lunasvg 3.5.0 适配笔记

## 编译环境
- 构建系统: cmake (官方 v3.5.0 tag, CMakeLists.txt, LANGUAGES CXX)
- 编译日期: 2026-09-16
- 编译器: clang/clang++ 15.0.4 (aarch64-linux-ohos), libc++
- 状态: published

## 编译步骤

```bash
# 官方源码 (GitHub sammycage/lunasvg v3.5.0 tag)
# SHA-256: 1abf1472ee6c4d19797916e8cc3c2e4b628e0d81178ffac60bdb0d457e32c690

cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local -DCMAKE_BUILD_TYPE=Release \
         -DBUILD_SHARED_LIBS=OFF -DLUNASVG_BUILD_EXAMPLES=ON
make -j2            # liblunasvg.a + libplutovg.a + examples/svg2png
make install DESTDIR=...   # 头文件 + 静态库 + CMake config + pkg-config

# Conan 配方验证 (8 道门禁全过)
python3 scripts/ohc-run.py conan-verify lunasvg 3.5.0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连下载超时 | 执行端网络无法直连 github.com | 经 ghfast.top 镜像传输官方归档(仅本地传输,conandata.yml 保持官方 HTTPS URL);镜像注入由 conan-verify E017 机制自动临时处理并恢复 |
| 2 | conan-init 生成 autotools 配方 | 工具按 URL 猜测构建系统为 autotools,实为 CMake | 重写 conanfile.py 为 CMake 模板(CMakeToolchain, USE_SYSTEM_PLUTOVG=OFF, LUNASVG_BUILD_EXAMPLES=OFF, package_info 双 lib) |
| 3 | conandata.yml sha256 为占位符 | 模板未填充 | 填入实测 SHA-256 1abf1472… |
| 4 | G2 失败:Cannot determine link language for test_lunasvg | 测试源 test.c 为 C 扩展名而工程仅启用 CXX | 重命名 test.cpp |
| 5 | G2 失败:center pixel rgba=(0,0,255,255) | plutovg 表面为 BGRA 小端字节序(byte0=B),断言按 RGBA 写 | 修正断言注释与通道映射(byte[2]=R) |

## 源码修改

无补丁文件(lunasvg 官方源码在 OHOS 上零修改直接编译通过)。patches/ 为空。

## 依赖版本

- 无外部 Conan 依赖;plutovg 1.3.x 作为 submodule 内嵌(USE_SYSTEM_PLUTOVG=OFF)
- CMake 4.1.2 / make 4.4.1 / clang 15.0.4

## 验证结果

- conan-verify: G0-G4 + L2/L4/L5 全 PASS
- 消费者验证 (test_package): 1/1 PASS (loadFromData + renderToBitmap + 中心像素断言)
- 鸿蒙专项测试 (reports/ohos-svg-test.cpp): transform/gradient/text 3 断言全 PASS,退出码 0

## 上游测试台账

官方 v3.5.0 tag 源码**无任何独立上游测试声明**:无 tests/ 目录、无 CTest 注册
(enable_testing/add_test 均无)、无 Meson 测试注册、无 TEST_CASE/gtest 宏。
source_declared_total=0, configured_executable_total=0, executed_passed_total=0。
样例 examples/svg2png.cpp 与 plutovg/examples/smiley.c 已运行/核验,按规则不计入
上游用例。完整台账见 reports/test-report.md。

## 注意事项

- lunasvg 静态链接时需同时链接 libplutovg.a(lunasvg.a 引用 plutovg 符号),
  conanfile.py package_info 已同时声明两个 lib。
- 系统 CMake 不识别 HarmonyOS 平台时提示 "System is unknown to cmake",但不影响
  构建(conan profile 提供完整工具链,CMAKE_SYSTEM_NAME 映射由 OHOS 适配版 conan 处理)。
---

**编译结束**: 2026-09-16 21:55
**最终状态**: published
