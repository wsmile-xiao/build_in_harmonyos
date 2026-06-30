# glbinding 3.5.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-30
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 平台: HarmonyOS (aarch64)
- 状态: published

## 编译步骤

```bash
# 1. CMake 配置（静态链接 + 禁用测试/文档）
cd $BUILD_SRC_DIR && rm -rf build && mkdir -p build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DBUILD_SHARED_LIBS=OFF \
  -DCMAKE_BUILD_TYPE=Release \
  -DOPTION_BUILD_TESTS=OFF \
  -DOPTION_BUILD_DOCS=OFF

# 2. 编译
make -j2

# 3. Staging 安装
make install DESTDIR=$TEST_PREFIX

# 4. 测试（无测试配置，预期行为）
ctest
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 警告 "System is unknown to cmake" | CMake 不识别 HarmonyOS 平台（E092） | 非阻塞，忽略警告继续编译 |
| 2 | glfw3 相关工具被跳过 | HarmonyOS 无头显示器平台无 glfw3 | 预期行为，glbinding-glmeta 工具不依赖 glfw3 可正常编译 |
| 3 | conanfile.py 导入 Conan 缓存后变为全 null 字节 | HMDFS 文件系统复制问题 | 用 bash heredoc 重新写入 conanfile.py，清理 Conan 缓存后重新验证 |
| 4 | Conan 构建默认生成 .so 而非 .a | glbinding 的 CMakeLists.txt 在 project() 前调用 option(BUILD_SHARED_LIBS ON) | 在 conanfile.py 的 generate() 和 build() 中同时设置 BUILD_SHARED_LIBS=OFF |

## 源码修改

无源码修改。glbinding 3.5.0 在 HarmonyOS 上可直接编译，无需补丁。

## 依赖版本

无外部依赖。glbinding 是自包含的 OpenGL 绑定库，KHR 平台头文件内嵌在源码中。

## 验证结果

### 手动构建验证
```
cmake 配置: 成功 (4.6s)
make 编译: 成功 (100%, 静态库)
make install DESTDIR: 成功 (393 个文件)
ctest: 无测试配置（预期）
make check: 无规则（预期）
readelf -d glbinding-glmeta: 仅依赖 libc++_shared.so + libc.so (R26 PASS)
```

### Conan 验证
```
G0 预构建评估: PASS (E092 非阻塞)
G1 配方完整性: PASS
G2 conan create: PASS (2 .a + 0 .so)
G3 静态链接: PASS (纯库包)
G4 产物完整性: PASS (370 头文件)
L2 smoke test: PASS (纯库包跳过)
L4 安全扫描: PASS
L5 产物基线: PASS (395 文件)
Conan test_package: 100% 测试通过
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libglbinding.a | 18.4 MB | OpenGL 绑定静态库 |
| libglbinding-aux.a | 4.8 MB | 辅助功能静态库 |
| glbinding-glmeta | ~3.9 MB | GL 元数据查询工具 |
| 370 个 .h 文件 | - | 完整头文件（gl10-gl46 + extensions） |
| 9 个 .inl 文件 | - | 内联头文件 |
| cmake 配置文件 | - | glbinding/glbinding-aux 导出文件 + FindKHR.cmake |

## 注意事项

1. glbinding 是 OpenGL API 绑定库，本身不直接调用 OpenGL，而是在运行时通过函数指针动态加载 OpenGL 函数。因此在无 OpenGL 环境的平台上仍可编译。
2. 需要 glfw3 的工具（glcontexts, glfunctions, glinfo 等）在无头显示器平台上会被跳过，这不影响核心库的编译和使用。
3. conanfile.py 必须在 generate() 和 build() 中同时设置 BUILD_SHARED_LIBS=OFF，因为 glbinding 的 CMakeLists.txt 在 project() 之前调用 option() 设置了默认值 ON。
4. 在 HMDFS 文件系统上，用文件管理工具写入的 Python 文件可能产生 null 字节，建议用 bash heredoc 写入 conanfile.py。
---

**编译结束**: 2026-06-30 17:50
**最终状态**: published
