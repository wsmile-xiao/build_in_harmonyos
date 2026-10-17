# p8-platform 2.1.0 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-08-07
- 编译器: clang/clang++ 15.0.4
- 状态: built (conan-verify passed, CI upload pending)

## 源码
- 上游: Pulse-Eight/platform (p8-platform-2.1.0 tag)
- URL: https://github.com/Pulse-Eight/platform/archive/refs/tags/p8-platform-2.1.0.tar.gz
- SHA256: 88711f1b949285867538a0b2e4189532778e1515325dfa1851eae9d18b6affd9

## 编译步骤

1. 下载源码 (init-build 自动下载)
2. CMake 配置:
   ```bash
   cmake .. -DCMAKE_POLICY_VERSION_MINIMUM=3.5
   ```
   - 需要 CMAKE_POLICY_VERSION_MINIMUM=3.5 (上游 cmake_minimum_required 2.8.9 与 CMake 4.x 不兼容)
   - 需要 CMAKE_SYSTEM_NAME=Linux (E092: CMake 不识别 HarmonyOS 平台)

3. 编译:
   ```bash
   make -j2
   ```

4. 安装 (staging):
   ```bash
   make install DESTDIR=$TEST_PREFIX
   ```

## 补丁

### 0001-src-util-StringUtils.cpp.patch
- 问题: std::ptr_fun 在 C++17 中已移除 (profile 使用 compiler.cppstd=17)
- 修复: 将 `::not1(::ptr_fun(isspace_c))` 替换为 lambda `[](unsigned char c) { return !isspace_c(c); }`
- 影响行: StringUtils::TrimLeft 和 StringUtils::TrimRight

## Conan 配方

- conanfile.py: CMakeToolchain, BUILD_SHARED_LIBS=OFF (static), CMAKE_SYSTEM_NAME=Linux
- conandata.yml: 官方 GitHub tar.gz URL + sha256
- test_package: 调用 StringUtils::ToUpper, Trim, EqualsNoCase (R34 实质测试)
- 依赖: 无 (仅系统 pthread)

## 验证结果

- conan-verify G2 (conan create): PASS
- conan-verify G3 (R26 系统同名库隔离): PASS
- conan-verify G4 (产物完整性): PASS
- W3 本地 CI 模拟: PASS
- test_package: PASS (3 assertions: ToUpper, Trim, EqualsNoCase)

## 交付物

| 文件 | 说明 |
|------|------|
| libp8-platform.a | 静态库 |
| include/p8-platform/ | 头文件目录 (os.h, posix/, sockets/, threads/, util/) |
| lib/pkgconfig/p8-platform.pc | pkg-config 配置 |
| lib/p8-platform/p8-platform-config.cmake | CMake 配置 |

---

**编译结束**: 2026-08-07 07:45
**最终状态**: built
