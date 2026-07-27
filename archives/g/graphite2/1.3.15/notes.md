# graphite2 1.3.15 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-15
- 编译器: clang/clang++ (LLVM 15.0.4)
- 状态: built

## 编译步骤

```bash
# 1. CMake Configure
cmake -S . -B build \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DBUILD_TESTING=ON

# 2. Build
cmake --build build -j2

# 3. Install
cmake --install build --prefix $DEFAULT_PREFIX --strip
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake HarmonyOS 平台未知 | CMake 不认识 HarmonyOS 作为目标平台 | 使用 Conan CMakeToolchain 自动处理 |
| 2 | gr2fonttest 运行时找不到符号 | binary 链接了相对路径 ../src/libgraphite2.so | 使用 patchelf 修复 RPATH，或从 build 目录运行 |
| 3 | test_package 链接失败 | graphite2 静态库是 C++，test 是 C 程序 | 添加 target_link_libraries(test_graphite2 c++) |
| 4 | 6 个测试因 fontTools 缺失失败 | fontTools Python 包未安装，为平台限制 | 缺失 fontTools 不影响核心功能 |

## 依赖版本

无外部运行时依赖（仅使用 C/C++ 标准库）

## 验证结果

```bash
$ ctest --output-on-failure
# 93% tests passed, 6 tests failed (missing fontTools, platform limitation)

$ conan create . --build=missing
# G0-G4 all PASS
```

## 注意事项

- graphite2 是字体渲染库，同时提供 gr2fonttest 命令行工具
- 已创建 commands.json 声明命令行工具
- 6 个测试因 fontTools 缺失失败（平台限制，不阻塞）
- 首次运行 gr2fonttest 需触发 HarmonyOS 安全弹窗确认

---

**编译结束**: 2026-07-15 16:32
**最终状态**: built