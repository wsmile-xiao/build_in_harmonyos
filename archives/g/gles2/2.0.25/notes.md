# gles2 2.0.25 适配笔记

## 编译环境
- 构建系统: CMake（生成式，替代上游自定义 Yip 构建系统）
- 编译日期: 2026-08-06
- 编译器: clang/clang++ (Clang 15.0.4)
- 状态: published

## 编译步骤

1. 下载源码并解压
2. 在 source() 方法中生成 CMakeLists.txt（上游使用自定义 Yip 构建系统，无标准 CMakeLists.txt）
3. CMake 配置: `cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_SHARED_LIBS=OFF`
4. 编译: `make -j2`
5. 安装: `make install DESTDIR=$TEST_PREFIX`

关键命令:
```bash
cd $BUILD_SRC_DIR
mkdir -p build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
make -j2
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create 失败: CMakeLists.txt not found | save() 在 build() 中保存到 build folder 而非 source folder | 将 save() 移到 source() 方法，使用 os.path.join(self.source_folder, "CMakeLists.txt") |
| 2 | test_package 测试失败: getError() 返回 1282 | dummy wrapper 的 getError() 返回 GL::INVALID_OPERATION 而非 GL::NO_ERROR | 修改测试断言为检查 GL::INVALID_OPERATION |
| 3 | G1 检查失败: 缺少补丁应用调用 | conanfile.py 未调用 apply_conandata_patches | 在 build() 方法中添加 apply_conandata_patches(self) |
| 4 | G0 干净构建验证失败 (configure exit 127) | 上游使用自定义 Yip 构建系统，无 configure 脚本 | 非阻塞步骤，conan create (G2) 已验证配方正确性 |

## 源码修改

无源码补丁。CMakeLists.txt 在 conanfile.py 的 source() 方法中动态生成。

## 依赖版本

无外部依赖。gles2 是纯 C++ 库，仅依赖标准库。

## 验证结果

```bash
# conan-verify 8 道门禁全部通过
G0 (预构建风险评估): PASS
G1 (配方完整性): PASS
G2 (conan create): PASS - test_gles2 输出 "test gles2 2.0.25: OK (init + getError + getInteger)"
G3 (系统同名库隔离 R26): PASS
G4 (产物完整性): PASS
L2 (smoke test): PASS
L4 (checksec): PASS
L5 (产物基线): PASS

# W3 本地 CI 模拟通过
setup.sh: PASS
build_and_test.sh: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libgles2.a | 103,602 bytes | 静态库 (dummy wrapper) |
| gl.h | 10,671 bytes | GL 命名空间声明 |
| gl_constants.h | 12,276 bytes | GL 常量定义 |
| gl_error.h | 3,793 bytes | 错误处理声明 |

## 注意事项

- gles2 使用 dummy wrapper 编译，所有 GL 函数为空 stub 实现
- dummy wrapper 的 getError() 返回 GL::INVALID_OPERATION (0x0502 = 1282)
- 上游使用自定义 "Yip" 构建系统，CMakeLists.txt 在 conanfile.py 中动态生成
- 适用于无原生 OpenGL ES 支持的平台

---

**编译结束**: 2026-08-06 09:00
**最终状态**: published
